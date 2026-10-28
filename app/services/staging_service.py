import json
import re
from datetime import datetime
from app.models.db import get_db
from app.services.gsheets_service import write_daily_report
from app.models.config_store import get_airport_config

def parse_submitted_by(raw_val, airport_code=None):
    """
    Mem-parsing teks SUBMITTED_BY untuk mendapatkan nama dan username pengirim.
    Format yang didukung:
    1. 'Nama Lengkap (@username)' atau 'Nama Lengkap (username)'
    2. Lookup ke user_store jika hanya salah satu.
    Mengembalikan tuple: (clean_name, clean_username)
    """
    if not raw_val:
        return "", ""
    raw_str = str(raw_val).strip()
    
    m = re.search(r'^(.*?)\s*[\(\[]@?\s*([a-zA-Z0-9_]+)\s*[\)\]]?$', raw_str)
    if m:
        c_name = m.group(1).rstrip(' ([@').strip()
        c_uname = m.group(2).strip().lower()
        return c_name, c_uname
        
    try:
        from app.models.user_store import get_all_users
        users = get_all_users()
        for u in users:
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
    Menyimpan atau memperbarui data laporan di tabel SQLite staging_reports (Lokal, 0 HIT API Google).
    Jika laporan sudah ada (misal sedang revisi), data diperbarui dan status kembali ke PENDING_DH.
    """
    airport_code = str(airport_code).upper().strip()
    tanggal = form_data.get('TANGGAL', datetime.now().strftime('%Y-%m-%d'))
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Defensive check jika TANGGAL dan SAPAAN tertukar di form_data
    date_regex = r'^\d{4}-\d{2}-\d{2}$'
    val_tgl = str(form_data.get('TANGGAL', '')).strip()
    val_sap = str(form_data.get('SAPAAN', '')).strip()
    if re.match(date_regex, val_sap) and not re.match(date_regex, val_tgl):
        form_data['TANGGAL'] = val_sap
        form_data['SAPAAN'] = val_tgl
        tanggal = val_sap
    elif re.match(date_regex, val_tgl):
        tanggal = val_tgl

    clean_date = tanggal.replace('-', '')
    if not report_id:
        # Cek apakah sudah ada laporan untuk bandara & tanggal ini di SQLite
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT report_id, timestamp_submit FROM staging_reports 
            WHERE UPPER(airport_code) = ? AND tanggal = ?;
            """, (airport_code, tanggal))
            existing_row = cursor.fetchone()
            if existing_row:
                report_id = existing_row['report_id']
                existing_submit_time = existing_row['timestamp_submit']
            else:
                report_id = f"REP-{airport_code}-{clean_date}"
                existing_submit_time = now_str
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT timestamp_submit FROM staging_reports 
            WHERE report_id = ? AND UPPER(airport_code) = ?;
            """, (report_id, airport_code))
            existing_row = cursor.fetchone()
            existing_submit_time = existing_row['timestamp_submit'] if existing_row else now_str

    if user_username:
        clean_u = str(user_username).strip().lower()
        if f"@{clean_u}" not in str(user_name):
            stored_submitted_by = f"{user_name} (@{clean_u})"
        else:
            stored_submitted_by = user_name
    else:
        stored_submitted_by = user_name

    # Siapkan full dict untuk disimpan
    full_data = dict(form_data)
    full_data['REPORT_ID'] = report_id
    full_data['STATUS'] = 'PENDING_DH'
    full_data['TANGGAL'] = tanggal
    full_data['TANGGAL_LAPORAN'] = tanggal
    full_data['SUBMITTED_BY'] = stored_submitted_by
    full_data['SUBMITTED_BY_USERNAME'] = user_username or ''
    full_data['TIMESTAMP_SUBMIT'] = existing_submit_time
    full_data['TIMESTAMP_UPDATE'] = now_str
    full_data['CATATAN_GM'] = ''
    full_data['CATATAN_DH'] = ''

    action = "updated" if existing_submit_time != now_str else "created"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO staging_reports (
            report_id, airport_code, tanggal, status, catatan_gm, catatan_dh,
            submitted_by, submitted_by_username, timestamp_submit, timestamp_update, form_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            report_id,
            airport_code,
            tanggal,
            'PENDING_DH',
            '',
            '',
            stored_submitted_by,
            user_username or '',
            existing_submit_time,
            now_str,
            json.dumps(full_data, ensure_ascii=False)
        ))

    try:
        from app.services.gsheets_service import invalidate_calendar_cache
        invalidate_calendar_cache()
    except Exception:
        pass

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
    Mengambil seluruh laporan draf di tabel SQLite staging_reports (Lokal, 0 HIT API Google).
    """
    airport_code = str(airport_code).upper().strip()
    reports = []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM staging_reports 
        WHERE UPPER(airport_code) = ? AND status != 'APPROVED'
        ORDER BY timestamp_submit DESC;
        """, (airport_code,))
        rows = cursor.fetchall()

    for r in rows:
        try:
            row_dict = json.loads(r['form_data'])
        except Exception:
            row_dict = {}

        raw_status = r['status'] or 'PENDING_DH'
        display_status = 'PENDING_DH' if raw_status == 'PENDING_GM' else raw_status
        catatan_val = r['catatan_dh'] or r['catatan_gm'] or ''

        raw_sub = r['submitted_by'] or row_dict.get('SUBMITTED_BY', '')
        sub_name, sub_uname = parse_submitted_by(raw_sub, airport_code)
        if not sub_uname and r['submitted_by_username']:
            sub_uname = r['submitted_by_username']

        reports.append({
            "report_id": r['report_id'],
            "status": display_status,
            "catatan_gm": catatan_val,
            "catatan_dh": catatan_val,
            "tanggal": r['tanggal'],
            "submitted_by": sub_name or raw_sub,
            "submitted_by_username": sub_uname or "",
            "submitted_by_raw": raw_sub,
            "timestamp_submit": r['timestamp_submit'] or '',
            "timestamp_update": r['timestamp_update'] or '',
            "pci_runway": row_dict.get('RUNWAY_PCI', '-'),
            "kondisi_runway": row_dict.get('RUNWAY_KONDISI', '-'),
            "data": row_dict
        })

    return reports

def get_staging_report_by_id(airport_code, report_id):
    """
    Mengambil 1 laporan spesifik berdasarkan REPORT_ID dari SQLite.
    """
    airport_code = str(airport_code).upper().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM staging_reports 
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (report_id, airport_code))
        r = cursor.fetchone()

    if not r:
        return None

    try:
        row_dict = json.loads(r['form_data'])
    except Exception:
        row_dict = {}

    raw_status = r['status'] or 'PENDING_DH'
    display_status = 'PENDING_DH' if raw_status == 'PENDING_GM' else raw_status
    catatan_val = r['catatan_dh'] or r['catatan_gm'] or ''

    raw_sub = r['submitted_by'] or row_dict.get('SUBMITTED_BY', '')
    sub_name, sub_uname = parse_submitted_by(raw_sub, airport_code)
    if not sub_uname and r['submitted_by_username']:
        sub_uname = r['submitted_by_username']

    return {
        "report_id": r['report_id'],
        "status": display_status,
        "catatan_gm": catatan_val,
        "catatan_dh": catatan_val,
        "tanggal": r['tanggal'],
        "submitted_by": sub_name or raw_sub,
        "submitted_by_username": sub_uname or "",
        "submitted_by_raw": raw_sub,
        "timestamp_submit": r['timestamp_submit'] or '',
        "timestamp_update": r['timestamp_update'] or '',
        "pci_runway": row_dict.get('RUNWAY_PCI', '-'),
        "kondisi_runway": row_dict.get('RUNWAY_KONDISI', '-'),
        "data": row_dict
    }

def gm_request_revision(airport_code, report_id, notes):
    """
    DH memberikan catatan koreksi.
    Status diubah menjadi REVISI di SQLite, dan catatan disimpan (0 HIT API Google).
    """
    airport_code = str(airport_code).upper().strip()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT form_data FROM staging_reports 
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (report_id, airport_code))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Laporan {report_id} tidak ditemukan di staging {airport_code}.")

        try:
            fd = json.loads(row['form_data'])
        except Exception:
            fd = {}

        fd['STATUS'] = 'REVISI'
        fd['CATATAN_GM'] = notes
        fd['CATATAN_DH'] = notes
        fd['TIMESTAMP_UPDATE'] = now_str

        cursor.execute("""
        UPDATE staging_reports 
        SET status = 'REVISI', catatan_gm = ?, catatan_dh = ?, timestamp_update = ?, form_data = ?
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (notes, notes, now_str, json.dumps(fd, ensure_ascii=False), report_id, airport_code))

    try:
        from app.services.gsheets_service import invalidate_calendar_cache
        invalidate_calendar_cache()
    except Exception:
        pass

    return {
        "success": True,
        "report_id": report_id,
        "status": "REVISI",
        "notes": notes
    }

def update_staging_report_by_dh(airport_code, report_id, updated_form_data, dh_name=None, dh_username=None):
    """
    Department Head mengoreksi secara mandiri data laporan di SQLite.
    Memperbarui nilai form fields namun mempertahankan data asli pelapor.
    Status laporan dipastikan tetap/kembali ke PENDING_DH.
    """
    airport_code = str(airport_code).upper().strip()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM staging_reports 
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (report_id, airport_code))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Laporan {report_id} tidak ditemukan di staging {airport_code}.")

        try:
            old_data = json.loads(row['form_data'])
        except Exception:
            old_data = {}

        merged_data = dict(old_data)
        for k, v in updated_form_data.items():
            if k not in ('REPORT_ID', 'TIMESTAMP_SUBMIT', 'SUBMITTED_BY', 'SUBMITTED_BY_USERNAME'):
                merged_data[k] = v

        dh_label = dh_name or 'Department Head'
        catatan_koreksi = f"Dikoreksi mandiri oleh DH ({dh_label})"
        merged_data['STATUS'] = 'PENDING_DH'
        merged_data['TIMESTAMP_UPDATE'] = now_str
        merged_data['CATATAN_DH'] = catatan_koreksi
        merged_data['CATATAN_GM'] = catatan_koreksi

        cursor.execute("""
        UPDATE staging_reports 
        SET status = 'PENDING_DH', catatan_dh = ?, catatan_gm = ?, timestamp_update = ?, form_data = ?
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (catatan_koreksi, catatan_koreksi, now_str, json.dumps(merged_data, ensure_ascii=False), report_id, airport_code))

    try:
        from app.services.gsheets_service import invalidate_calendar_cache
        invalidate_calendar_cache()
    except Exception:
        pass

    return {
        "success": True,
        "report_id": report_id,
        "status": "PENDING_DH",
        "timestamp_update": now_str,
        "updated_data": merged_data
    }

def gm_approve_report(airport_code, report_id):
    """
    DH menyetujui laporan:
    1. Ambil data laporan dari SQLite staging_reports.
    2. Masukkan ke Google Spreadsheet Produksi resmi (DATABASE_REKAP & Tab Harian) -> SATU-SATUNYA HIT API!
    3. Hapus data draf dari tabel SQLite staging_reports.
    """
    airport_code = str(airport_code).upper().strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM staging_reports 
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (report_id, airport_code))
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Laporan {report_id} tidak ditemukan di antrean staging {airport_code}.")

        try:
            form_data = json.loads(row['form_data'])
        except Exception:
            form_data = {}

    # Defensive self-healing untuk TANGGAL & SAPAAN
    date_regex = r'^\d{4}-\d{2}-\d{2}$'
    raw_tanggal = str(form_data.get('TANGGAL', '')).strip()
    if not re.match(date_regex, raw_tanggal):
        if re.match(date_regex, str(form_data.get('SAPAAN', '')).strip()):
            real_date = str(form_data['SAPAAN']).strip()
            form_data['SAPAAN'] = raw_tanggal
            form_data['TANGGAL'] = real_date
        elif re.match(date_regex, str(form_data.get('TANGGAL_LAPORAN', '')).strip()):
            form_data['TANGGAL'] = str(form_data['TANGGAL_LAPORAN']).strip()
        else:
            m = re.search(r'(\d{4})(\d{2})(\d{2})', str(report_id))
            if m:
                form_data['TANGGAL'] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    raw_sub = form_data.get('SUBMITTED_BY', row['submitted_by'])
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

    # 1. EKSEKUSI PENULISAN KE GOOGLE SPREADSHEET PRODUKSI UTAMA (1x HIT API)
    write_daily_report(prod_sheet_url, form_data)

    # 2. Hapus baris data draf dari tabel SQLite staging_reports
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM staging_reports 
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (report_id, airport_code))

    try:
        from app.services.gsheets_service import invalidate_calendar_cache
        invalidate_calendar_cache()
    except Exception:
        pass

    return {
        "success": True,
        "report_id": report_id,
        "message": f"Laporan {report_id} berhasil disetujui, dipindahkan ke Spreadsheet Utama, dan dihapus dari Staging.",
        "form_data": form_data
    }

def delete_staging_report(airport_code, report_id):
    """
    Menghapus laporan pengajuan dari SQLite staging_reports.
    """
    airport_code = str(airport_code).upper().strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM staging_reports 
        WHERE report_id = ? AND UPPER(airport_code) = ?;
        """, (report_id, airport_code))

    try:
        from app.services.notification_service import delete_notifications_by_report_id
        delete_notifications_by_report_id(airport_code, report_id)
    except Exception as e:
        print(f"Warning deleting notifications for report {report_id}: {e}")

    try:
        from app.services.gsheets_service import invalidate_calendar_cache
        invalidate_calendar_cache()
    except Exception:
        pass

    return {
        "success": True,
        "report_id": report_id,
        "message": f"Laporan {report_id} berhasil dihapus dari Staging."
    }
