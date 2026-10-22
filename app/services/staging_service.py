import os
import json
from datetime import datetime
import gspread
from app.services.gsheets_service import get_client, sanitize_sheet_value, write_daily_report
from app.services.drive_service import get_drive_service, create_monthly_sheet
from app.models.config_store import (
    get_staging_folder_id,
    get_staging_sheet_url,
    update_staging_sheet_url,
    get_airport_config
)

DEFAULT_TEMPLATE_ID = "1-NfvG7t8uhp7NPKygxv_oSDsmzP1GlajIRvkGXKjwuk"

def get_all_form_field_names():
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
    field_names = []
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
            for step in schema.get('steps', []):
                for sec in step.get('sections', []):
                    for field in sec.get('fields', []):
                        if field['name'] not in field_names:
                            field_names.append(field['name'])
    except Exception as e:
        print(f"Error loading form_schema in staging_service: {e}")
    return field_names

def get_staging_headers():
    control_headers = [
        'REPORT_ID',
        'STATUS',
        'CATATAN_GM',
        'TANGGAL_LAPORAN',
        'SUBMITTED_BY',
        'TIMESTAMP_SUBMIT',
        'TIMESTAMP_UPDATE'
    ]
    return control_headers + get_all_form_field_names()

def get_or_create_staging_sheet(airport_code):
    """
    Membuka atau secara otomatis membuat spreadsheet staging khusus untuk bandara terkait di folder STAGING.
    Mengembalikan instance Worksheet 'STAGING_DATA'.
    """
    airport_code = airport_code.upper()
    folder_id = get_staging_folder_id()
    sheet_url = get_staging_sheet_url(airport_code)
    client = get_client()

    spreadsheet = None
    if sheet_url:
        try:
            spreadsheet = client.open_by_url(sheet_url)
        except Exception as e:
            print(f"Warning: URL staging sheet {airport_code} tidak valid atau tidak bisa dibuka: {e}")
            spreadsheet = None

    if not spreadsheet:
        # Cek apakah file STAGING_{airport_code} sudah ada di folder Drive
        drive_svc = get_drive_service()
        file_name = f"STAGING_{airport_code}"
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        try:
            res = drive_svc.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, webViewLink, modifiedTime)',
                orderBy='modifiedTime desc'
            ).execute()
            files = res.get('files', [])
            if files:
                best_file = None
                for cand in files:
                    try:
                        cand_url = cand.get('webViewLink') or f"https://docs.google.com/spreadsheets/d/{cand['id']}/edit"
                        cand_ss = client.open_by_url(cand_url)
                        cand_ws = cand_ss.worksheet('STAGING_DATA')
                        if len(cand_ws.get_all_values()) > 1:
                            best_file = (cand_url, cand_ss)
                            break
                    except Exception:
                        continue

                if best_file:
                    sheet_url, spreadsheet = best_file
                else:
                    sheet_url = files[0].get('webViewLink') or f"https://docs.google.com/spreadsheets/d/{files[0]['id']}/edit"
                    spreadsheet = client.open_by_url(sheet_url)
                update_staging_sheet_url(airport_code, sheet_url)
        except Exception as drive_err:
            print(f"Warning saat mencari staging sheet {airport_code} di Drive: {drive_err}")

    if not spreadsheet:
        # Buat file spreadsheet baru di folder STAGING
        file_name = f"STAGING_{airport_code}"
        print(f"Membuat file spreadsheet baru '{file_name}' di folder {folder_id}...")
        drive_svc = get_drive_service()
        new_url = None
        
        # Opsi 1: Coba buat via Drive API secara langsung
        try:
            file_metadata = {
                'name': file_name,
                'parents': [folder_id],
                'mimeType': 'application/vnd.google-apps.spreadsheet'
            }
            new_file = drive_svc.files().create(body=file_metadata, fields='id, webViewLink').execute()
            new_url = new_file.get('webViewLink') or f"https://docs.google.com/spreadsheets/d/{new_file['id']}/edit"
        except Exception as create_err:
            print(f"Gagal buat spreadsheet via Drive API: {create_err}. Mencoba via template Apps Script proxy...")
            try:
                new_url = create_monthly_sheet(file_name, folder_id, DEFAULT_TEMPLATE_ID)
            except Exception as proxy_err:
                raise Exception(f"Gagal membuat staging sheet {file_name}: {proxy_err}")

        if not new_url:
            raise Exception(f"Gagal mendapatkan URL spreadsheet staging untuk {airport_code}")

        sheet_url = new_url
        update_staging_sheet_url(airport_code, sheet_url)
        spreadsheet = client.open_by_url(sheet_url)

    # Pastikan tab STAGING_DATA ada dan memiliki header lengkap
    try:
        worksheet = spreadsheet.worksheet('STAGING_DATA')
    except gspread.WorksheetNotFound:
        # Jika sheet1 masih bernama 'Sheet1' atau belum bernama 'STAGING_DATA', kita siapkan
        sheet1 = spreadsheet.sheet1
        try:
            sheet1.update_title('STAGING_DATA')
            worksheet = sheet1
        except Exception:
            worksheet = spreadsheet.add_worksheet(title='STAGING_DATA', rows=100, cols=100)

    # Inisialisasi header baris 1 jika masih kosong
    headers = get_staging_headers()
    first_row = worksheet.row_values(1)
    if not first_row or first_row[0] != 'REPORT_ID':
        sanitized_headers = [sanitize_sheet_value(h) for h in headers]
        worksheet.update(values=[sanitized_headers], range_name='A1')

    return worksheet

def save_report_to_staging(airport_code, form_data, user_name, report_id=None):
    """
    Menyimpan atau memperbarui data laporan di spreadsheet staging bandara terkait.
    Jika laporan sudah ada (misal sedang revisi), data diperbarui dan status kembali ke PENDING_GM.
    """
    airport_code = airport_code.upper()
    worksheet = get_or_create_staging_sheet(airport_code)
    headers = get_staging_headers()
    all_rows = worksheet.get_all_values()
    
    tanggal = form_data.get('TANGGAL', datetime.now().strftime('%Y-%m-%d'))
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Cari index baris jika report_id diberikan atau jika sudah ada laporan di tanggal yang sama
    target_row_index = -1
    existing_submit_time = now_str
    
    if report_id:
        for idx, row in enumerate(all_rows):
            if idx > 0 and len(row) > 0 and row[0].strip() == report_id.strip():
                target_row_index = idx + 1 # 1-based index
                existing_submit_time = row[5] if len(row) > 5 and row[5] else now_str
                break
    else:
        # Cari berdasarkan tanggal jika belum di-approve
        for idx, row in enumerate(all_rows):
            if idx > 0 and len(row) > 3 and row[3].strip() == tanggal.strip():
                # Ditemukan laporan untuk tanggal ini
                target_row_index = idx + 1
                report_id = row[0].strip()
                existing_submit_time = row[5] if len(row) > 5 and row[5] else now_str
                break

    if not report_id:
        clean_date = tanggal.replace('-', '')
        report_id = f"REP-{airport_code}-{clean_date}"

    # Susun baris data sesuai urutan header
    row_values = []
    for h in headers:
        if h == 'REPORT_ID':
            row_values.append(report_id)
        elif h == 'STATUS':
            row_values.append('PENDING_GM')
        elif h == 'CATATAN_GM':
            row_values.append('') # Dikosongkan kembali setelah staff memperbaiki
        elif h == 'TANGGAL_LAPORAN':
            row_values.append(tanggal)
        elif h == 'SUBMITTED_BY':
            row_values.append(user_name)
        elif h == 'TIMESTAMP_SUBMIT':
            row_values.append(existing_submit_time)
        elif h == 'TIMESTAMP_UPDATE':
            row_values.append(now_str)
        else:
            row_values.append(form_data.get(h, ''))

    sanitized_row = [sanitize_sheet_value(v) for v in row_values]

    if target_row_index != -1:
        # Update baris yang sudah ada
        worksheet.update(values=[sanitized_row], range_name=f"A{target_row_index}")
        action = "updated"
    else:
        # Tambah baris baru
        worksheet.append_row(sanitized_row)
        action = "created"

    return {
        "success": True,
        "action": action,
        "report_id": report_id,
        "status": "PENDING_GM",
        "tanggal": tanggal
    }

def get_staging_reports(airport_code):
    """
    Mengambil seluruh laporan di spreadsheet staging bandara terkait.
    Mengembalikan daftar dict laporan.
    """
    airport_code = airport_code.upper()
    try:
        worksheet = get_or_create_staging_sheet(airport_code)
    except Exception as e:
        print(f"Error opening staging sheet for {airport_code}: {e}")
        return []

    all_rows = worksheet.get_all_values()
    if len(all_rows) <= 1:
        return []

    headers = all_rows[0]
    reports = []
    
    # Iterasi dari bawah ke atas (laporan terbaru di atas)
    for row_idx in range(len(all_rows) - 1, 0, -1):
        row = all_rows[row_idx]
        if not row or not any(row):
            continue

        row_dict = {}
        for col_idx, h in enumerate(headers):
            val = row[col_idx] if col_idx < len(row) else ''
            row_dict[h] = val

        reports.append({
            "report_id": row_dict.get('REPORT_ID', ''),
            "status": row_dict.get('STATUS', 'PENDING_GM'),
            "catatan_gm": row_dict.get('CATATAN_GM', ''),
            "tanggal": row_dict.get('TANGGAL_LAPORAN', row_dict.get('TANGGAL', '')),
            "submitted_by": row_dict.get('SUBMITTED_BY', ''),
            "timestamp_submit": row_dict.get('TIMESTAMP_SUBMIT', ''),
            "timestamp_update": row_dict.get('TIMESTAMP_UPDATE', ''),
            "pci_runway": row_dict.get('RUNWAY_PCI', '-'),
            "kondisi_runway": row_dict.get('RUNWAY_KONDISI', '-'),
            "data": row_dict
        })

    return reports

def get_staging_report_by_id(airport_code, report_id):
    """
    Mengambil 1 laporan spesifik berdasarkan REPORT_ID.
    """
    reports = get_staging_reports(airport_code)
    for rep in reports:
        if rep['report_id'] == report_id:
            return rep
    return None

def gm_request_revision(airport_code, report_id, notes):
    """
    GM memberikan catatan koreksi.
    Status diubah menjadi REVISI, dan catatan disimpan.
    """
    airport_code = airport_code.upper()
    worksheet = get_or_create_staging_sheet(airport_code)
    all_rows = worksheet.get_all_values()
    
    target_idx = -1
    for idx, row in enumerate(all_rows):
        if idx > 0 and len(row) > 0 and row[0].strip() == report_id.strip():
            target_idx = idx + 1
            break

    if target_idx == -1:
        raise Exception(f"Laporan {report_id} tidak ditemukan di staging {airport_code}.")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Kolom B adalah STATUS (2), Kolom C adalah CATATAN_GM (3), Kolom G adalah TIMESTAMP_UPDATE (7)
    worksheet.update_acell(f"B{target_idx}", sanitize_sheet_value("REVISI"))
    worksheet.update_acell(f"C{target_idx}", sanitize_sheet_value(notes))
    worksheet.update_acell(f"G{target_idx}", sanitize_sheet_value(now_str))

    return {
        "success": True,
        "report_id": report_id,
        "status": "REVISI",
        "notes": notes
    }

def gm_approve_report(airport_code, report_id):
    """
    GM menyetujui laporan:
    1. Ambil data laporan dari staging.
    2. Masukkan ke Google Spreadsheet Produksi resmi (DATABASE_REKAP & tab harian).
    3. Hapus baris data dari spreadsheet staging.
    """
    airport_code = airport_code.upper()
    worksheet = get_or_create_staging_sheet(airport_code)
    all_rows = worksheet.get_all_values()

    target_idx = -1
    target_row = None
    for idx, row in enumerate(all_rows):
        if idx > 0 and len(row) > 0 and row[0].strip() == report_id.strip():
            target_idx = idx + 1
            target_row = row
            break

    if target_idx == -1 or not target_row:
        raise Exception(f"Laporan {report_id} tidak ditemukan di staging {airport_code}.")

    headers = all_rows[0]
    form_data = {}
    for col_idx, h in enumerate(headers):
        val = target_row[col_idx] if col_idx < len(target_row) else ''
        form_data[h] = val

    # Dapatkan URL spreadsheet produksi yang saat ini berjalan untuk cabang ini
    airport_conf = get_airport_config(airport_code)
    prod_sheet_url = airport_conf.get('sheet_url')
    if not prod_sheet_url:
        raise Exception(f"Spreadsheet Produksi aktif untuk bandara {airport_code} belum dikonfigurasi oleh Admin.")

    # 1. Eksekusi suntik data ke Spreadsheet Produksi Utama
    write_daily_report(prod_sheet_url, form_data)

    # 2. Hapus baris data dari Spreadsheet Staging
    worksheet.delete_rows(target_idx)

    return {
        "success": True,
        "report_id": report_id,
        "message": f"Laporan {report_id} berhasil disetujui, dipindahkan ke Spreadsheet Utama, dan dihapus dari Staging.",
        "form_data": form_data
    }

def delete_staging_report(airport_code, report_id):
    """
    Menghapus laporan pengajuan dari spreadsheet staging (misal laporan duplikat atau ditolak).
    """
    airport_code = airport_code.upper()
    worksheet = get_or_create_staging_sheet(airport_code)
    all_rows = worksheet.get_all_values()

    target_idx = -1
    for idx, row in enumerate(all_rows):
        if idx > 0 and len(row) > 0 and row[0].strip() == report_id.strip():
            target_idx = idx + 1
            break

    if target_idx == -1:
        raise Exception(f"Laporan {report_id} tidak ditemukan di staging {airport_code}.")

    worksheet.delete_rows(target_idx)

    # Bersihkan notifikasi terkait laporan ini dari notifications.json
    try:
        from app.services.notification_service import delete_notifications_by_report_id
        delete_notifications_by_report_id(airport_code, report_id)
    except Exception as e:
        print(f"Warning deleting notifications for report {report_id}: {e}")

    return {
        "success": True,
        "report_id": report_id,
        "message": f"Laporan {report_id} berhasil dihapus dari Staging."
    }
