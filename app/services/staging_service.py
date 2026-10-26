import os
import json
import threading
import time
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
_staging_lock = threading.Lock()

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
    core_form_fields = [
        'SAPAAN',
        'TANGGAL',
        'PENERIMA_1',
        'PENERIMA_2',
        'PENERIMA_3',
        'PENERIMA_4',
        'KANTOR_CABANG'
    ]
    all_fields = get_all_form_field_names()
    other_fields = [f for f in all_fields if f not in core_form_fields and f not in control_headers]
    return control_headers + core_form_fields + other_fields

def get_or_create_staging_sheet(airport_code):
    """
    Membuka spreadsheet staging khusus untuk bandara terkait di folder STAGING.
    Prinsip konsistensi: Setiap bandara HANYA memiliki 1 file spreadsheet staging (STAGING_{airport_code}).
    Sistem TIDAK AKAN PERNAH membuat file baru jika file sudah ada di folder Drive atau di konfigurasi.
    Mengembalikan instance Worksheet 'STAGING_DATA'.
    """
    airport_code = airport_code.upper()
    folder_id = get_staging_folder_id()
    sheet_url = get_staging_sheet_url(airport_code)
    client = get_client()

    with _staging_lock:
        spreadsheet = None

        # 1. Buka melalui sheet_url yang tersimpan di config jika ada (dengan retry jika kendala jaringan)
        if sheet_url:
            for attempt in range(3):
                try:
                    spreadsheet = client.open_by_url(sheet_url)
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(1)
                    else:
                        print(f"Warning: URL staging sheet {airport_code} ({sheet_url}) gagal dibuka: {e}")
                        spreadsheet = None

        # Jika spreadsheet berhasil dibuka, periksa dan bersihkan file duplikat berlebih di folder Drive
        if spreadsheet:
            try:
                drive_svc = get_drive_service()
                file_name = f"STAGING_{airport_code}"
                query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
                res = drive_svc.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
                drive_files = res.get('files', [])
                current_id = spreadsheet.id
                if len(drive_files) > 1:
                    for f in drive_files:
                        if f['id'] != current_id:
                            try:
                                drive_svc.files().update(fileId=f['id'], removeParents=folder_id).execute()
                                print(f"Otomatis melepaskan duplikasi file staging {f['name']} ({f['id']}) dari folder.")
                            except Exception as unl_e:
                                print(f"Warning melepaskan duplikat: {unl_e}")
            except Exception as dup_check_err:
                pass

        # 2. Jika tidak ada di config atau URL gagal dibuka, cari file fisik di folder Drive
        if not spreadsheet:
            drive_svc = get_drive_service()
            file_name = f"STAGING_{airport_code}"
            query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
            try:
                res = drive_svc.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, webViewLink, createdTime)',
                    orderBy='createdTime asc'
                ).execute()
                files = res.get('files', [])
                if files:
                    # Ambil file pertama yang sah
                    target_file = files[0]
                    target_url = target_file.get('webViewLink') or f"https://docs.google.com/spreadsheets/d/{target_file['id']}/edit"
                    for attempt in range(3):
                        try:
                            spreadsheet = client.open_by_url(target_url)
                            sheet_url = target_url
                            update_staging_sheet_url(airport_code, sheet_url)
                            break
                        except Exception as open_err:
                            if attempt < 2:
                                time.sleep(1)
                            else:
                                raise Exception(f"Gagal membuka spreadsheet staging {file_name} ({target_url}): {open_err}")

                    # Jika ditemukan file duplikat berlebih dari masa lalu, lepaskan (unlink) dari folder
                    if len(files) > 1:
                        for dup in files[1:]:
                            try:
                                drive_svc.files().update(fileId=dup['id'], removeParents=folder_id).execute()
                                print(f"Otomatis melepaskan duplikasi file staging {dup['name']} ({dup['id']})")
                            except Exception:
                                pass
            except Exception as drive_err:
                if not spreadsheet:
                    raise Exception(f"Kesalahan saat mencari staging sheet {airport_code} di Google Drive: {drive_err}")

        # 3. HANYA JIKA BENAR-BENAR BELUM ADA FILE DI GOOGLE DRIVE (folder kosong):
        if not spreadsheet:
            file_name = f"STAGING_{airport_code}"
            print(f"Membuat 1 file spreadsheet staging baru '{file_name}' di folder {folder_id}...")
            drive_svc = get_drive_service()
            new_url = None
            
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

        # 4. Pastikan tab STAGING_DATA ada dan memiliki header lengkap
        try:
            worksheet = spreadsheet.worksheet('STAGING_DATA')
        except gspread.WorksheetNotFound:
            sheet1 = spreadsheet.sheet1
            try:
                sheet1.update_title('STAGING_DATA')
                worksheet = sheet1
            except Exception:
                worksheet = spreadsheet.add_worksheet(title='STAGING_DATA', rows=100, cols=100)

        # Inisialisasi header baris 1 dan sinkronisasi otomatis jika kolom berubah
        headers = get_staging_headers()
        try:
            sync_staging_sheet_headers_and_data(worksheet, headers)
        except Exception as sync_err:
            print(f"Warning saat sinkronisasi staging headers {airport_code}: {sync_err}")

        return worksheet

def sync_staging_sheet_headers_and_data(worksheet, current_headers):
    """
    Memastikan row 1 di worksheet staging selalu sinkron dengan get_staging_headers().
    Jika baris header lama berbeda dari current_headers, migrasikan data baris yang ada
    secara dinamis berdasarkan NAMA HEADER (bukan index posisi), agar urutan kolom
    tidak tergeser dan data tetap utuh.
    """
    try:
        all_rows = worksheet.get_all_values()
    except Exception as e:
        print(f"Error reading rows for staging sync: {e}")
        return

    sanitized_headers = [sanitize_sheet_value(h) for h in current_headers]
    if not all_rows or not all_rows[0] or str(all_rows[0][0]).strip() != 'REPORT_ID':
        worksheet.update(values=[sanitized_headers], range_name='A1')
        return

    first_row = all_rows[0]
    import re
    date_regex = r'^\d{4}-\d{2}-\d{2}$'
    is_date = lambda s: bool(re.match(date_regex, str(s).strip()))

    need_update = (first_row != current_headers)
    old_headers = first_row
    new_rows = []

    for r in all_rows[1:]:
        if not r or not any(r):
            continue
        row_dict = {}
        for i, h in enumerate(old_headers):
            if i < len(r):
                row_dict[h] = r[i]

        # Self-healing jika TANGGAL dan SAPAAN tertukar
        val_tgl = str(row_dict.get('TANGGAL', '')).strip()
        val_sap = str(row_dict.get('SAPAAN', '')).strip()
        if is_date(val_sap) and not is_date(val_tgl):
            row_dict['TANGGAL'] = val_sap
            row_dict['SAPAAN'] = val_tgl
            need_update = True

        # Self-healing jika TANGGAL_LAPORAN kosong atau bukan tanggal
        if not is_date(row_dict.get('TANGGAL_LAPORAN', '')) and is_date(row_dict.get('TANGGAL', '')):
            row_dict['TANGGAL_LAPORAN'] = row_dict['TANGGAL']
            need_update = True

        migrated_row = [row_dict.get(h, '') for h in current_headers]
        new_rows.append(migrated_row)

    if need_update:
        full_table = [sanitized_headers]
        for r in new_rows:
            full_table.append([sanitize_sheet_value(v) for v in r])
        worksheet.update(values=full_table, range_name='A1')
        print(f"Berhasil menyinkronkan {len(current_headers)} header dan {len(new_rows)} baris data di staging sheet.")

def parse_submitted_by(raw_val, airport_code=None):
    """
    Mem-parsing teks SUBMITTED_BY untuk mendapatkan nama dan username pengirim.
    Format yang didukung:
    1. 'Nama Lengkap (@username)' atau 'Nama Lengkap (username)'
    2. Jika hanya nama atau username saja, coba lookup ke user_store.
    Mengembalikan tuple: (clean_name, clean_username)
    """
    if not raw_val:
        return "", ""
    raw_str = str(raw_val).strip()
    
    # Cek pola Nama (@username) atau Nama (username) atau Nama [username]
    import re
    m = re.search(r'^(.*?)\s*[\(\[]@?\s*([a-zA-Z0-9_]+)\s*[\)\]]?$', raw_str)
    if m:
        c_name = m.group(1).rstrip(' ([@').strip()
        c_uname = m.group(2).strip().lower()
        return c_name, c_uname
        
    # Jika tidak ada pola kurung, coba cari di user_store berdasarkan kecocokan nama atau username
    try:
        from app.models.airport_profiles import USERS
        for u in USERS.values():
            if airport_code and u.get('airport') and u.get('airport').upper() != str(airport_code).upper():
                continue
            if u.get('role') != 'staff':
                continue
            if u.get('name', '').strip().lower() == raw_str.lower() or u.get('username', '').strip().lower() == raw_str.lower():
                return u.get('name', raw_str), u.get('username')
    except Exception as e:
        print(f"Warning lookup user in parse_submitted_by: {e}")

    return raw_str, ""

def save_report_to_staging(airport_code, form_data, user_name, report_id=None, user_username=None):
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

    # Defensive check jika TANGGAL dan SAPAAN tertukar di form_data
    import re
    date_regex = r'^\d{4}-\d{2}-\d{2}$'
    val_tgl = str(form_data.get('TANGGAL', '')).strip()
    val_sap = str(form_data.get('SAPAAN', '')).strip()
    if re.match(date_regex, val_sap) and not re.match(date_regex, val_tgl):
        form_data['TANGGAL'] = val_sap
        form_data['SAPAAN'] = val_tgl
        tanggal = val_sap
    elif re.match(date_regex, val_tgl):
        tanggal = val_tgl

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

    # Format nilai yang disimpan pada kolom SUBMITTED_BY
    if user_username:
        clean_u = str(user_username).strip().lower()
        if f"@{clean_u}" not in str(user_name):
            stored_submitted_by = f"{user_name} (@{clean_u})"
        else:
            stored_submitted_by = user_name
    else:
        stored_submitted_by = user_name

    # Susun baris data sesuai urutan header
    row_values = []
    for h in headers:
        if h == 'REPORT_ID':
            row_values.append(report_id)
        elif h == 'STATUS':
            row_values.append('PENDING_DH')
        elif h in ('CATATAN_GM', 'CATATAN_DH'):
            row_values.append('') # Dikosongkan kembali setelah staff memperbaiki
        elif h == 'TANGGAL_LAPORAN':
            row_values.append(tanggal)
        elif h == 'SUBMITTED_BY':
            row_values.append(stored_submitted_by)
        elif h == 'SUBMITTED_BY_USERNAME':
            row_values.append(user_username or '')
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
        "status": "PENDING_DH",
        "tanggal": tanggal,
        "submitted_by": user_name,
        "submitted_by_username": user_username or ""
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

        raw_status = row_dict.get('STATUS', 'PENDING_DH')
        display_status = 'PENDING_DH' if raw_status == 'PENDING_GM' else raw_status
        catatan_val = row_dict.get('CATATAN_DH') or row_dict.get('CATATAN_GM', '')

        # Self-healing jika TANGGAL dan SAPAAN tertukar di row_dict
        import re
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        val_tgl = str(row_dict.get('TANGGAL', '')).strip()
        val_sap = str(row_dict.get('SAPAAN', '')).strip()
        val_tgl_lap = str(row_dict.get('TANGGAL_LAPORAN', '')).strip()

        if re.match(date_pattern, val_sap) and not re.match(date_pattern, val_tgl):
            row_dict['TANGGAL'] = val_sap
            row_dict['SAPAAN'] = val_tgl
            val_tgl = val_sap

        real_date = val_tgl if re.match(date_pattern, val_tgl) else (val_tgl_lap if re.match(date_pattern, val_tgl_lap) else '')

        raw_sub = row_dict.get('SUBMITTED_BY', '')
        sub_name, sub_uname = parse_submitted_by(raw_sub, airport_code)
        if not sub_uname and row_dict.get('SUBMITTED_BY_USERNAME'):
            sub_uname = row_dict.get('SUBMITTED_BY_USERNAME').strip().lower()

        reports.append({
            "report_id": row_dict.get('REPORT_ID', ''),
            "status": display_status,
            "catatan_gm": catatan_val,
            "catatan_dh": catatan_val,
            "tanggal": real_date or row_dict.get('TANGGAL_LAPORAN', row_dict.get('TANGGAL', '')),
            "submitted_by": sub_name or raw_sub,
            "submitted_by_username": sub_uname or "",
            "submitted_by_raw": raw_sub,
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

def update_staging_report_by_dh(airport_code, report_id, updated_form_data, dh_name=None, dh_username=None):
    """
    Department Head mengoreksi secara mandiri data laporan di spreadsheet staging.
    Memperbarui nilai form fields namun mempertahankan data asli pelapor (SUBMITTED_BY & TIMESTAMP_SUBMIT).
    Status laporan dipastikan tetap/kembali ke PENDING_DH.
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
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Buat dict data baris lama
    old_data = {}
    for col_idx, h in enumerate(headers):
        val = target_row[col_idx] if col_idx < len(target_row) else ''
        old_data[h] = val

    # Merge updated_form_data ke data lama
    merged_data = dict(old_data)
    for k, v in updated_form_data.items():
        if k not in ('REPORT_ID', 'TIMESTAMP_SUBMIT', 'SUBMITTED_BY', 'SUBMITTED_BY_USERNAME'):
            merged_data[k] = v

    # Set metadata koreksi
    merged_data['STATUS'] = 'PENDING_DH'
    merged_data['TIMESTAMP_UPDATE'] = now_str
    
    # Simpan catatan bahwa telah dikoreksi mandiri oleh DH
    dh_label = dh_name or 'Department Head'
    merged_data['CATATAN_DH'] = f"Dikoreksi mandiri oleh DH ({dh_label})"
    if 'CATATAN_GM' in headers:
        merged_data['CATATAN_GM'] = merged_data['CATATAN_DH']

    # Susun ulang baris sesuai urutan headers
    new_row_values = []
    for h in headers:
        new_row_values.append(merged_data.get(h, ''))

    sanitized_row = [sanitize_sheet_value(v) for v in new_row_values]
    worksheet.update(values=[sanitized_row], range_name=f"A{target_idx}")

    return {
        "success": True,
        "report_id": report_id,
        "status": "PENDING_DH",
        "timestamp_update": now_str,
        "updated_data": merged_data
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

    # Defensive self-healing untuk TANGGAL & SAPAAN
    import re
    date_regex = r'^\d{4}-\d{2}-\d{2}$'
    raw_tanggal = str(form_data.get('TANGGAL', '')).strip()
    if not re.match(date_regex, raw_tanggal):
        # 1. Cek apakah tertukar dengan SAPAAN
        if re.match(date_regex, str(form_data.get('SAPAAN', '')).strip()):
            real_date = str(form_data['SAPAAN']).strip()
            form_data['SAPAAN'] = raw_tanggal
            form_data['TANGGAL'] = real_date
        # 2. Cek TANGGAL_LAPORAN
        elif re.match(date_regex, str(form_data.get('TANGGAL_LAPORAN', '')).strip()):
            form_data['TANGGAL'] = str(form_data['TANGGAL_LAPORAN']).strip()
        # 3. Cek report_id (misal REP-LOP-20261116)
        else:
            m = re.search(r'(\d{4})(\d{2})(\d{2})', str(report_id))
            if m:
                form_data['TANGGAL'] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    raw_sub = form_data.get('SUBMITTED_BY', '')
    sub_name, sub_uname = parse_submitted_by(raw_sub, airport_code)
    if not sub_uname and form_data.get('SUBMITTED_BY_USERNAME'):
        sub_uname = form_data.get('SUBMITTED_BY_USERNAME').strip().lower()
    form_data['_submitted_by_name'] = sub_name or raw_sub
    form_data['_submitted_by_username'] = sub_uname or ''

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
