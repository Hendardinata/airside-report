import gspread
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')

def sanitize_sheet_value(val):
    """
    Mitigasi Formula / CSV Injection pada Spreadsheet:
    Jika string diawali dengan karakter '=', '+', '-', '@', '\t', '\r',
    tambahkan tanda petik tunggal (') di awal agar Google Sheets
    memperlakukannya sebagai teks literal murni dan tidak mengeksekusinya sebagai rumus.
    """
    if val is None:
        return ''
    if isinstance(val, (int, float, bool)):
        return val
    s_val = str(val)
    stripped = s_val.strip()
    if stripped.startswith(('=', '+', '-', '@', '\t', '\r')):
        if not s_val.startswith("'"):
            return "'" + s_val
    return s_val

def get_client():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError("File credentials.json tidak ditemukan. Harap masukkan kredensial Service Account GCP di root folder.")
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def write_daily_report(sheet_url, form_data):
    if not sheet_url:
        raise ValueError("URL Spreadsheet belum dikonfigurasi untuk bandara ini.")
        
    client = get_client()
    spreadsheet = client.open_by_url(sheet_url)
    
    try:
        rekap_sheet = spreadsheet.worksheet('DATABASE_REKAP')
    except gspread.WorksheetNotFound:
        raise Exception("Tab 'DATABASE_REKAP' tidak ditemukan pada Spreadsheet tersebut.")
    
    timestamp = datetime.now().isoformat()
    
    # --- FASE 1: DYNAMIC DATA MAPPING & AUTO-INIT HEADER ---
    # Membaca header dari Spreadsheet untuk membuat pemetaan secara dinamis.
    header_rows = rekap_sheet.get_values('A1:ZZ3')
    header_row = []
    is_header_empty = True
    
    if header_rows and len(header_rows) > 0:
        row_1 = header_rows[0]
        if any(str(cell).strip() for cell in row_1):
            is_header_empty = False
            header_row = row_1
    
    # Jika Baris 1 kosong, KITA AUTO-GENERATE HEADERS dari schema!
    if is_header_empty:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        new_headers = ['TIMESTAMP']
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
                for step in schema.get('steps', []):
                    for section in step.get('sections', []):
                        for field in section.get('fields', []):
                            new_headers.append(field['name'])
            
            # Tulis ke Sheet Baris 1
            rekap_sheet.update(values=[new_headers], range_name='A1')
            header_row = new_headers
        except Exception as e:
            print(f"Gagal auto-init header: {e}")
            
    # Jika masih tidak ketemu, cari TANGGAL di baris lain
    if not header_row and header_rows:
        for row in header_rows:
            if 'TANGGAL' in row or 'KANTOR_CABANG' in row:
                header_row = row
                break
                
    row_data = []
    if header_row:
        for idx, header in enumerate(header_row):
            header_clean = str(header).strip()
            # Kolom pertama biasanya Timestamp
            if idx == 0 and (not header_clean or header_clean.lower() == 'timestamp'):
                row_data.append(timestamp)
            elif header_clean:
                row_data.append(form_data.get(header_clean, ''))
            else:
                row_data.append('')
    else:
        # Fallback darurat
        row_data = [timestamp, form_data.get('KANTOR_CABANG', ''), form_data.get('TANGGAL', '')]
    
    # --- Validasi Bulan ---
    tanggal_str = form_data.get('TANGGAL', '')
    if tanggal_str:
        dt = datetime.strptime(tanggal_str, "%Y-%m-%d")
        indonesian_months = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]
        month_abbr = indonesian_months[dt.month - 1]
        year_str = dt.strftime("%Y")
        expected_suffix = f"{month_abbr}_{year_str}"
        
        # Validasi jika nama sheet (misal DPS_SEP_2026) tidak cocok dengan bulan yang diinput (OKT 2026)
        if expected_suffix not in spreadsheet.title:
            raise ValueError(f"DITOLAK: Anda memilih tanggal di bulan {month_abbr} {year_str}, tetapi Spreadsheet yang sedang aktif saat ini adalah untuk bulan lain ({spreadsheet.title}). Harap minta Admin untuk mengganti Link Spreadsheet Aktif di pengaturan terlebih dahulu!")
            
        # --- Validasi Duplikasi Tanggal ---
        # Cari index kolom TANGGAL secara dinamis berdasarkan header_row (1-based index)
        tanggal_col_idx = 3 # default
        if header_row:
            for i, h in enumerate(header_row):
                if str(h).strip() == 'TANGGAL':
                    tanggal_col_idx = i + 1
                    break
                    
        # Ambil semua data di Kolom Tanggal
        try:
            existing_dates_raw = rekap_sheet.col_values(tanggal_col_idx, value_render_option='UNFORMATTED_VALUE')
            existing_dates = []
            from datetime import timedelta
            for d in existing_dates_raw:
                if isinstance(d, (int, float)):
                    # Konversi serial date Google Sheets ke YYYY-MM-DD
                    dt_val = datetime(1899, 12, 30) + timedelta(days=d)
                    existing_dates.append(dt_val.strftime("%Y-%m-%d"))
                elif isinstance(d, str):
                    existing_dates.append(d.strip())
            
            if tanggal_str in existing_dates:
                raise ValueError(f"DITOLAK: Laporan untuk tanggal {tanggal_str} SUDAH PERNAH DIISI sebelumnya! Sistem menolak duplikasi data. Jika ingin mengedit, silakan buka Spreadsheet secara manual.")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            # Jika gagal mengambil col_values karena sheet kosong atau error API, abaikan saja
            print(f"Warning: Gagal mengecek duplikasi tanggal: {str(e)}")
            
    # Append ke DATABASE_REKAP
    # Gunakan table_range="A1" agar Google Sheets tidak "bingung" dan menggeser kolom (bug insert ke BB2)
    # Sanitasi semua nilai untuk mencegah Formula Injection
    sanitized_row_data = [sanitize_sheet_value(x) for x in row_data]
    try:
        rekap_sheet.append_row(sanitized_row_data, table_range="A1")
    except TypeError:
        # Fallback jika gspread versi sangat lama
        rekap_sheet.append_row(sanitized_row_data)
    
    # ====== LOGIKA DOUBLE ACTION (Menduplikasi Tab Harian) ======
    tanggal_str = form_data.get('TANGGAL', '')
    if tanggal_str:
        try:
            # Mengambil angka tanggal (misal '2026-10-01' -> '1')
            day = str(int(tanggal_str.split('-')[2]))
            
            try:
                target_sheet = spreadsheet.worksheet(day)
            except gspread.WorksheetNotFound:
                # Jika belum ada, duplikasi dari tab '1'
                try:
                    template_sheet = spreadsheet.worksheet('1')
                except gspread.WorksheetNotFound:
                    # Fallback jika tidak ada tab '1'
                    template_sheet = spreadsheet.worksheets()[0]
                
                target_sheet = spreadsheet.duplicate_sheet(
                    template_sheet.id, 
                    new_sheet_name=day,
                    insert_sheet_index=len(spreadsheet.worksheets())
                )
            
            # PEMBERSIHAN MUTLAK:
            # Kosongkan sisa input di B4:B66 dan seluruh baris 67 ke bawah (A67:Z150)
            # agar duplikasi tab '1' tidak pernah membawa nilai lama atau pertanyaan yang sudah dihapus
            try:
                target_sheet.batch_clear(["B4:B66", "A67:Z150"])
            except Exception as clear_err:
                print(f"Warning saat clear target sheet: {clear_err}")
            
            # Array kolom B dari B4 sampai B66
            col_B_data = [
                [form_data.get('SAPAAN', '')], # B4
                [form_data.get('TANGGAL', '')], # B5
                [form_data.get('PENERIMA_1', '')],
                [form_data.get('PENERIMA_2', '')],
                [form_data.get('PENERIMA_3', '')],
                [form_data.get('PENERIMA_4', '')],
                [form_data.get('KANTOR_CABANG', '')], # B10
                [''], # B11 Header
                [form_data.get('RUNWAY_KONDISI', '')], # B12
                [form_data.get('RUNWAY_PCI', '')],
                [form_data.get('RUNWAY_TITIK_RUSAK', '')],
                [form_data.get('RUNWAY_TITIK_DIPERBAIKI', '')],
                [form_data.get('RUNWAY_JENIS_DIPERBAIKI', '')],
                [form_data.get('RUNWAY_TITIK_BELUM', '')],
                [form_data.get('RUNWAY_JENIS_BELUM', '')],
                [form_data.get('RUNWAY_TITIK_BERULANG', '')], # B19
                [form_data.get('RUNWAY_MARKA_STD', '')],
                [form_data.get('RUNWAY_MARKA_REALISASI', '')],
                [form_data.get('RUNWAY_MARKA_PERF', '')],
                [form_data.get('RUNWAY_STANDING_WATER', '')],
                [form_data.get('RUNWAY_WATER_PERF', '')], # B24
                [form_data.get('RUNWAY_RUBBER_STD', '')],
                [form_data.get('RUNWAY_RUBBER_REAL', '')],
                [form_data.get('RUNWAY_RUBBER_SKID', '')], # B27
                [''], # B28 Header
                [form_data.get('TAXIWAY_NAMA', '')], # B29
                [form_data.get('TAXIWAY_STATUS', '')],
                [form_data.get('TAXIWAY_PCI', '')],
                [form_data.get('TWY_TITIK_RUSAK', '')],
                [form_data.get('TWY_TITIK_DIPERBAIKI', '')],
                [form_data.get('TWY_JENIS_DIPERBAIKI', '')],
                [form_data.get('TWY_TITIK_BELUM', '')],
                [form_data.get('TWY_JENIS_BELUM', '')],
                [form_data.get('TWY_TITIK_BERULANG', '')], # B37
                [''], # B38 TWY Jenis kerusakan berulang
                [form_data.get('TWY_MARKA_STD', '')], # B39
                [form_data.get('TWY_MARKA_REALISASI', '')],
                [form_data.get('TWY_MARKA_PERF', '')],
                [form_data.get('TWY_STANDING_WATER', '')], # B42
                [''], # B43 TWY_WATER_PERF
                [''], # B44 Header
                [form_data.get('APRON_KONDISI', '')], # B45
                [form_data.get('APRON_PCI', '')],
                [form_data.get('APN_TITIK_RUSAK', '')],
                [form_data.get('APN_TITIK_DIPERBAIKI', '')],
                [form_data.get('APN_JENIS_DIPERBAIKI', '')],
                [form_data.get('APN_TITIK_BELUM', '')],
                [form_data.get('APN_JENIS_BELUM', '')],
                [form_data.get('APN_TITIK_BERULANG', '')], # B52
                [form_data.get('APN_MARKA_STD', '')], # B53
                [form_data.get('APN_MARKA_REALISASI', '')],
                [form_data.get('APN_MARKA_PERF', '')],
                [form_data.get('APN_STANDING_WATER', '')], # B56
                [''], # B57 APN_WATER_PERF
                [form_data.get('RUMPUT_STD', '')], # B58
                [form_data.get('RUMPUT_REALISASI', '')],
                [form_data.get('RUMPUT_PERF', '')], # B60
                [''], # B61 Header
                [form_data.get('CATATAN_1', '')], # B62
                [form_data.get('CATATAN_2', '')],
                [form_data.get('CATATAN_3', '')],
                [form_data.get('CATATAN_4', '')],
                [form_data.get('CATATAN_5', '')] # B66
            ]
            
            # Sanitasi col_B_data
            sanitized_col_B = [[sanitize_sheet_value(cell[0])] for cell in col_B_data]
            target_sheet.update(values=sanitized_col_B, range_name='B4:B66')
            
            # --- FASE 4: DYNAMIC DAILY SHEET MAPPING ---
            # Cari field baru yang dibuat melalui Form Builder yang tidak ada di template standar
            schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
            with open(schema_path, 'r') as f:
                schema = json.load(f)
                
            standard_fields = [
                'SAPAAN', 'TANGGAL', 'PENERIMA_1', 'PENERIMA_2', 'PENERIMA_3', 'PENERIMA_4',
                'KANTOR_CABANG', 'RUNWAY_KONDISI', 'RUNWAY_PCI', 'RUNWAY_TITIK_RUSAK',
                'RUNWAY_TITIK_DIPERBAIKI', 'RUNWAY_JENIS_DIPERBAIKI', 'RUNWAY_TITIK_BELUM',
                'RUNWAY_JENIS_BELUM', 'RUNWAY_TITIK_BERULANG', 'RUNWAY_MARKA_STD',
                'RUNWAY_MARKA_REALISASI', 'RUNWAY_MARKA_PERF', 'RUNWAY_STANDING_WATER',
                'RUNWAY_WATER_PERF', 'RUNWAY_RUBBER_STD', 'RUNWAY_RUBBER_REAL',
                'RUNWAY_RUBBER_SKID', 'TAXIWAY_NAMA', 'TAXIWAY_STATUS', 'TAXIWAY_PCI',
                'TWY_TITIK_RUSAK', 'TWY_TITIK_DIPERBAIKI', 'TWY_JENIS_DIPERBAIKI',
                'TWY_TITIK_BELUM', 'TWY_JENIS_BELUM', 'TWY_TITIK_BERULANG', 'TWY_MARKA_STD',
                'TWY_MARKA_REALISASI', 'TWY_MARKA_PERF', 'TWY_STANDING_WATER',
                'APRON_KONDISI', 'APRON_PCI', 'APN_TITIK_RUSAK', 'APN_TITIK_DIPERBAIKI',
                'APN_JENIS_DIPERBAIKI', 'APN_TITIK_BELUM', 'APN_JENIS_BELUM', 'APN_TITIK_BERULANG',
                'APN_MARKA_STD', 'APN_MARKA_REALISASI', 'APN_MARKA_PERF', 'APN_STANDING_WATER',
                'RUMPUT_STD', 'RUMPUT_REALISASI', 'RUMPUT_PERF', 'CATATAN_1', 'CATATAN_2',
                'CATATAN_3', 'CATATAN_4', 'CATATAN_5'
            ]
            
            extra_data = []
            format_requests = []
            current_row = 67 # Start at row 67 (0-indexed 66)
            
            for step in schema.get('steps', []):
                for sec in step.get('sections', []):
                    sec_added = False
                    is_standard_sec = any(f.get('name') in standard_fields for f in sec.get('fields', []))
                    
                    for field in sec.get('fields', []):
                        if field['name'] not in standard_fields:
                            val = form_data.get(field['name'], '')
                            if not sec_added and not is_standard_sec:
                                # Tambahkan Judul Sub-bab HANYA jika ini bab benar-benar baru
                                sec_title = sec.get('title', 'TAMBAHAN')
                                extra_data.append([sec_title.upper(), ''])
                                format_requests.append({
                                    "copyPaste": {
                                        "source": { "sheetId": target_sheet.id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 2 },
                                        "destination": { "sheetId": target_sheet.id, "startRowIndex": current_row-1, "endRowIndex": current_row, "startColumnIndex": 0, "endColumnIndex": 2 },
                                        "pasteType": "PASTE_FORMAT"
                                    }
                                })
                                current_row += 1
                                sec_added = True
                            
                            # Tambahkan Field Pertanyaan (Format seperti Baris 53 "Marka")
                            label = field.get('label', field['name'])
                            extra_data.append([label, sanitize_sheet_value(val)])
                            format_requests.append({
                                "copyPaste": {
                                    "source": { "sheetId": target_sheet.id, "startRowIndex": 52, "endRowIndex": 53, "startColumnIndex": 0, "endColumnIndex": 2 },
                                    "destination": { "sheetId": target_sheet.id, "startRowIndex": current_row-1, "endRowIndex": current_row, "startColumnIndex": 0, "endColumnIndex": 2 },
                                    "pasteType": "PASTE_FORMAT"
                                }
                            })
                            current_row += 1
                                
            if extra_data:
                # Update data explicitly at row 67 downwards
                end_row = 67 + len(extra_data) - 1
                target_sheet.update(values=extra_data, range_name=f"A67:B{end_row}")
                
                # Apply Formatting
                if format_requests:
                    try:
                        spreadsheet.batch_update({"requests": format_requests})
                    except Exception as fe:
                        print("Warning batch update formatting:", fe)
            
        except Exception as e:
            print(f"Gagal membuat tab harian: {str(e)}")
            pass
            
    return True

def get_daily_summary(date_str):
    from app.models.config_store import CONFIG_FILE
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        
    airports = config.get('airports', {})
    summary = {}
    
    try:
        client = get_client()
    except Exception:
        client = None

    from datetime import datetime, timedelta
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    indonesian_months = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]
    month_abbr = indonesian_months[dt.month - 1]
    year_str = dt.strftime("%Y")

    for code, conf in airports.items():
        summary[code] = {
            "status": "Belum Mengirim",
            "pci": "-",
            "is_submitted": False,
            "pic_phone": conf.get("pic_phone", "")
        }
        
        default_url = conf.get('sheet_url')
        drive_folder = conf.get('drive_folder')
        url = default_url
        
        # Coba periksa apakah default URL sudah sesuai dengan bulan yang dicari
        is_url_match = False
        if url and client:
            try:
                sheet_title = client.open_by_url(url).title
                if f"{month_abbr}_{year_str}" in sheet_title or f"{month_abbr} {year_str}" in sheet_title.upper():
                    is_url_match = True
            except Exception:
                pass
                
        # Jika tidak cocok, lakukan Auto-Discovery menggunakan Drive API
        if not is_url_match and drive_folder:
            try:
                from googleapiclient.discovery import build
                from google.oauth2.service_account import Credentials
                import os
                
                cred_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
                creds = Credentials.from_service_account_file(cred_path, scopes=['https://www.googleapis.com/auth/drive'])
                drive_svc = build('drive', 'v3', credentials=creds)
                
                query = f"'{drive_folder}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and name contains '{month_abbr}' and name contains '{year_str}' and trashed=false"
                res = drive_svc.files().list(q=query, spaces='drive', fields='files(id, name, webViewLink)').execute()
                files = res.get('files', [])
                if files:
                    url = files[0]['webViewLink']
                    print(f"Auto-discovered sheet for {code} {month_abbr} {year_str}: {url}")
            except Exception as e:
                print(f"Gagal auto-discovery Drive API untuk {code}: {e}")
                
        if not url or not client:
            continue
            
        try:
            sheet = client.open_by_url(url).worksheet('DATABASE_REKAP')
            
            # --- DYNAMIC DATA MAPPING ---
            header_rows = sheet.get_values('A1:ZZ3')
            header_row = []
            if header_rows:
                for row in header_rows:
                    if 'TANGGAL' in row or 'KANTOR_CABANG' in row:
                        header_row = row
                        break
                if not header_row and len(header_rows) > 0:
                    header_row = header_rows[0]
            
            tanggal_col_idx = 3 # Default C
            pci_col_idx = 9 # Default J (0-indexed 9)
            
            if header_row:
                for i, h in enumerate(header_row):
                    h_clean = str(h).strip()
                    if h_clean == 'TANGGAL':
                        tanggal_col_idx = i + 1
                    elif h_clean == 'RUNWAY_PCI':
                        pci_col_idx = i
            
            # Ambil semua tanggal dari Kolom yang telah ditemukan
            dates_raw = sheet.col_values(tanggal_col_idx, value_render_option='UNFORMATTED_VALUE')
            from datetime import datetime, timedelta
            
            match_index = -1
            # Cari dari bawah ke atas (data terbaru)
            for i in range(len(dates_raw) - 1, -1, -1):
                d = dates_raw[i]
                date_val_str = ""
                if isinstance(d, (int, float)):
                    dt_val = datetime(1899, 12, 30) + timedelta(days=d)
                    date_val_str = dt_val.strftime("%Y-%m-%d")
                elif isinstance(d, str):
                    date_val_str = d.strip()
                    
                if date_val_str == date_str:
                    match_index = i + 1  # Gspread 1-indexed
                    break
                    
            if match_index != -1:
                # Ambil baris lengkap untuk mendapatkan PCI
                row_data = sheet.row_values(match_index)
                summary[code]["status"] = "Sudah Mengirim"
                summary[code]["is_submitted"] = True
                summary[code]["pci"] = str(row_data[pci_col_idx]) if len(row_data) > pci_col_idx else "-"
                summary[code]["raw_data"] = row_data
                
                # --- EXTRACT DATA TAMBAHAN UNTUK WA ---
                extra_data = []
                if header_row and len(row_data) > 57:
                    # Load schema on demand to get nice labels & sections
                    try:
                        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
                        with open(schema_path, 'r') as f:
                            schema = json.load(f)
                        name_to_label = {}
                        name_to_section = {}
                        for step in schema.get('steps', []):
                            for sec in step.get('sections', []):
                                sec_title = sec.get('title', 'Data Tambahan')
                                for field in sec.get('fields', []):
                                    name_to_label[field['name']] = field.get('label', field['name'])
                                    name_to_section[field['name']] = sec_title
                    except:
                        name_to_label = {}
                        name_to_section = {}
                        
                    for i in range(57, len(row_data)):
                        if i < len(header_row):
                            col_key = str(header_row[i]).strip()
                            col_val = str(row_data[i]).strip()
                            if col_val and col_val != "-":
                                nice_label = name_to_label.get(col_key, col_key)
                                sec_title = name_to_section.get(col_key, "Data Tambahan")
                                extra_data.append({"section": sec_title, "label": nice_label, "value": col_val})
                                
                summary[code]["extra_data"] = extra_data
                
        except Exception as e:
            print(f"Error fetching summary for {code}: {e}")
            
    return summary


def sync_sheets_to_rekap(sheet_url):
    """
    Memindai semua tab harian (1-31) di Spreadsheet,
    dan jika ada tanggal yang belum masuk ke DATABASE_REKAP,
    sistem akan menyedot datanya dan memasukkannya secara otomatis.
    """
    client = get_client()
    sheet = client.open_by_url(sheet_url)
    
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
    schema = {}
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except:
        pass
        
    # Mapping dari Label (Kolom A di tab harian) ke Name (Header di DATABASE_REKAP)
    label_to_name = {}
    for step in schema.get('steps', []):
        for sec in step.get('sections', []):
            for field in sec.get('fields', []):
                lbl = field.get('label', field['name'])
                label_to_name[lbl] = field['name']
                label_to_name[field['name']] = field['name'] # Fallback
                
    rekap_sheet = sheet.worksheet('DATABASE_REKAP')
    rekap_data = rekap_sheet.get_all_values()
    if not rekap_data:
        return 0
        
    header_row = rekap_data[0]
    tanggal_col_idx = 2 # default 0-indexed
    for i, h in enumerate(header_row):
        if str(h).strip() == 'TANGGAL':
            tanggal_col_idx = i
            break
            
    existing_dates = []
    from datetime import datetime, timedelta
    for row in rekap_data[1:]:
        if len(row) > tanggal_col_idx:
            d = str(row[tanggal_col_idx]).strip()
            if d:
                # Convert serial date to YYYY-MM-DD if needed
                if d.isdigit():
                    dt_val = datetime(1899, 12, 30) + timedelta(days=int(d))
                    existing_dates.append(dt_val.strftime("%Y-%m-%d"))
                else:
                    existing_dates.append(d)
                    
    synced_count = 0
    for ws in sheet.worksheets():
        if ws.title in ['DATABASE_REKAP', 'PETUNJUK']:
            continue
            
        # Biasanya nama sheet harian berupa angka '1', '2', dst
        if not ws.title.isdigit():
            continue
            
        # Ambil seluruh data dari tab harian
        try:
            ws_data = ws.get_all_values()
        except:
            continue
            
        form_data = {}
        # Daftar field standar persis seperti struktur B4:B66 (termasuk None untuk baris kosong/header)
        B4_TO_B66_KEYS = [
            'SAPAAN', 'TANGGAL', 'PENERIMA_1', 'PENERIMA_2', 'PENERIMA_3', 'PENERIMA_4', 'KANTOR_CABANG', # B4 - B10
            None, # B11 Header
            'RUNWAY_KONDISI', 'RUNWAY_PCI', 'RUNWAY_TITIK_RUSAK', 'RUNWAY_TITIK_DIPERBAIKI', 'RUNWAY_JENIS_DIPERBAIKI', # B12 - B16
            'RUNWAY_TITIK_BELUM', 'RUNWAY_JENIS_BELUM', 'RUNWAY_TITIK_BERULANG', # B17 - B19
            'RUNWAY_MARKA_STD', 'RUNWAY_MARKA_REALISASI', 'RUNWAY_MARKA_PERF', 'RUNWAY_STANDING_WATER', 'RUNWAY_WATER_PERF', # B20 - B24
            'RUNWAY_RUBBER_STD', 'RUNWAY_RUBBER_REAL', 'RUNWAY_RUBBER_SKID', # B25 - B27
            None, # B28 Header
            'TAXIWAY_NAMA', 'TAXIWAY_STATUS', 'TAXIWAY_PCI', 'TWY_TITIK_RUSAK', 'TWY_TITIK_DIPERBAIKI', 'TWY_JENIS_DIPERBAIKI', # B29 - B34
            'TWY_TITIK_BELUM', 'TWY_JENIS_BELUM', 'TWY_TITIK_BERULANG', # B35 - B37
            None, # B38 TWY Jenis kerusakan berulang
            'TWY_MARKA_STD', 'TWY_MARKA_REALISASI', 'TWY_MARKA_PERF', 'TWY_STANDING_WATER', # B39 - B42
            None, # B43 TWY_WATER_PERF
            None, # B44 Header
            'APRON_KONDISI', 'APRON_PCI', 'APN_TITIK_RUSAK', 'APN_TITIK_DIPERBAIKI', 'APN_JENIS_DIPERBAIKI', # B45 - B49
            'APN_TITIK_BELUM', 'APN_JENIS_BELUM', 'APN_TITIK_BERULANG', # B50 - B52
            'APN_MARKA_STD', 'APN_MARKA_REALISASI', 'APN_MARKA_PERF', 'APN_STANDING_WATER', # B53 - B56
            None, # B57 APN_WATER_PERF
            'RUMPUT_STD', 'RUMPUT_REALISASI', 'RUMPUT_PERF', # B58 - B60
            None, # B61 Header
            'CATATAN_1', 'CATATAN_2', 'CATATAN_3', 'CATATAN_4', 'CATATAN_5' # B62 - B66
        ]
        
        # 1. Map standard fields berdasar index baris yang kaku (Baris 4 sampai 66)
        for i, field_name in enumerate(B4_TO_B66_KEYS):
            if not field_name:
                continue
                
            row_idx = 3 + i # index 3 = Baris 4 di Excel
            if row_idx < len(ws_data):
                row = ws_data[row_idx]
                val = str(row[1]).strip() if len(row) > 1 else ""
                form_data[field_name] = val
                
        # 2. Map data tambahan HANYA untuk baris ke-67 ke bawah (berdasarkan label)
        for row_idx in range(66, len(ws_data)):
            row = ws_data[row_idx]
            if len(row) >= 2:
                lbl = str(row[0]).strip()
                val = str(row[1]).strip()
                if lbl in label_to_name and val:
                    form_data[label_to_name[lbl]] = val
                
        tanggal_str = form_data.get('TANGGAL')
        if not tanggal_str:
            continue
            
        # Jika laporan untuk tanggal ini belum ada di DATABASE_REKAP, sinkronkan!
        if tanggal_str not in existing_dates:
            row_data = []
            for col_name in header_row:
                if col_name == 'TIMESTAMP':
                    row_data.append(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
                else:
                    row_data.append(form_data.get(col_name, ''))
                    
            try:
                sanitized_sync_row = [sanitize_sheet_value(x) for x in row_data]
                rekap_sheet.append_row(sanitized_sync_row, table_range="A1")
                existing_dates.append(tanggal_str)
                synced_count += 1
            except Exception as e:
                print(f"Gagal append sync untuk {tanggal_str}: {e}")
                
    return synced_count


# ==============================================================================
# SINKRONISASI DUA ARAH (TWO-WAY SYNC): FORM SCHEMA <---> GOOGLE SPREADSHEET
# ==============================================================================

STANDARD_CORE_FIELDS = [
    'SAPAAN', 'TANGGAL', 'PENERIMA_1', 'PENERIMA_2', 'PENERIMA_3', 'PENERIMA_4',
    'KANTOR_CABANG', 'RUNWAY_KONDISI', 'RUNWAY_PCI', 'RUNWAY_TITIK_RUSAK',
    'RUNWAY_TITIK_DIPERBAIKI', 'RUNWAY_JENIS_DIPERBAIKI', 'RUNWAY_TITIK_BELUM',
    'RUNWAY_JENIS_BELUM', 'RUNWAY_TITIK_BERULANG', 'RUNWAY_MARKA_STD',
    'RUNWAY_MARKA_REALISASI', 'RUNWAY_MARKA_PERF', 'RUNWAY_STANDING_WATER',
    'RUNWAY_WATER_PERF', 'RUNWAY_RUBBER_STD', 'RUNWAY_RUBBER_REAL',
    'RUNWAY_RUBBER_SKID', 'TAXIWAY_NAMA', 'TAXIWAY_STATUS', 'TAXIWAY_PCI',
    'TWY_TITIK_RUSAK', 'TWY_TITIK_DIPERBAIKI', 'TWY_JENIS_DIPERBAIKI',
    'TWY_TITIK_BELUM', 'TWY_JENIS_BELUM', 'TWY_TITIK_BERULANG', 'TWY_MARKA_STD',
    'TWY_MARKA_REALISASI', 'TWY_MARKA_PERF', 'TWY_STANDING_WATER',
    'APRON_KONDISI', 'APRON_PCI', 'APN_TITIK_RUSAK', 'APN_TITIK_DIPERBAIKI',
    'APN_JENIS_DIPERBAIKI', 'APN_TITIK_BELUM', 'APN_JENIS_BELUM', 'APN_TITIK_BERULANG',
    'APN_MARKA_STD', 'APN_MARKA_REALISASI', 'APN_MARKA_PERF', 'APN_STANDING_WATER',
    'RUMPUT_STD', 'RUMPUT_REALISASI', 'RUMPUT_PERF', 'CATATAN_1', 'CATATAN_2',
    'CATATAN_3', 'CATATAN_4', 'CATATAN_5'
]

def get_schema_field_names(schema=None):
    """Mengambil seluruh nama field (KODE_KOLOM) dari form_schema.json secara berurutan."""
    if schema is None:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    names = []
    for step in schema.get('steps', []):
        for sec in step.get('sections', []):
            for f in sec.get('fields', []):
                fname = f.get('name', '').strip()
                if fname and fname not in names:
                    names.append(fname)
    return names

def sync_schema_to_sheets(sheet_url, schema=None):
    """
    Sinkronisasi Maju: Form Builder/Schema -> Google Sheets
    Menyesuaikan header kolom di DATABASE_REKAP dan baris di Tab '1' (Template)
    agar jika field/bab/sub-bab ditambah atau dihapus, spreadsheet langsung menyesuaikan.
    """
    if not sheet_url:
        return {"success": False, "error": "URL Spreadsheet kosong"}
        
    if schema is None:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
            
    client = get_client()
    spreadsheet = client.open_by_url(sheet_url)
    
    # 1. Sinkronisasi DATABASE_REKAP (Header & Penyelarasan Kolom Data)
    try:
        rekap_sheet = spreadsheet.worksheet('DATABASE_REKAP')
    except gspread.WorksheetNotFound:
        return {"success": False, "error": "Tab 'DATABASE_REKAP' tidak ditemukan"}
        
    schema_fields = get_schema_field_names(schema)
    new_headers = ['TIMESTAMP'] + schema_fields
    
    all_values = rekap_sheet.get_all_values()
    if not all_values or len(all_values) == 0:
        rekap_sheet.update(values=[new_headers], range_name='A1')
    else:
        old_headers = [str(h).strip() for h in all_values[0]]
        old_data = all_values[1:]
        
        col_map = {h: idx for idx, h in enumerate(old_headers) if h}
        
        new_data_rows = []
        for row in old_data:
            new_row = []
            for h in new_headers:
                if h == 'TIMESTAMP':
                    ts_idx = col_map.get('TIMESTAMP', 0 if len(row) > 0 else -1)
                    new_row.append(row[ts_idx] if 0 <= ts_idx < len(row) else '')
                elif h in col_map:
                    idx = col_map[h]
                    new_row.append(row[idx] if idx < len(row) else '')
                else:
                    new_row.append('')
            new_data_rows.append([sanitize_sheet_value(x) for x in new_row])
            
        # Kosongkan seluruh nilai agar kolom yang dihapus tidak tertinggal di sebelah kanan
        rekap_sheet.clear()
        rekap_sheet.update(values=[new_headers] + new_data_rows, range_name='A1')
        
    # 2. Sinkronisasi Tab '1' (Master Harian untuk Template Duplikasi)
    try:
        ws_1 = spreadsheet.worksheet('1')
        # Selalu bersihkan baris 67 ke bawah pada master tab '1'
        ws_1.batch_clear(["A67:Z150"])
        
        extra_template = []
        format_requests = []
        cur_row = 67
        
        for step in schema.get('steps', []):
            for sec in step.get('sections', []):
                sec_added = False
                is_standard_sec = any(f.get('name') in STANDARD_CORE_FIELDS for f in sec.get('fields', []))
                
                for field in sec.get('fields', []):
                    if field.get('name') not in STANDARD_CORE_FIELDS:
                        if not sec_added and not is_standard_sec:
                            sec_title = sec.get('title', 'TAMBAHAN')
                            extra_template.append([sec_title.upper(), ''])
                            format_requests.append({
                                "copyPaste": {
                                    "source": { "sheetId": ws_1.id, "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 0, "endColumnIndex": 2 },
                                    "destination": { "sheetId": ws_1.id, "startRowIndex": cur_row-1, "endRowIndex": cur_row, "startColumnIndex": 0, "endColumnIndex": 2 },
                                    "pasteType": "PASTE_FORMAT"
                                }
                            })
                            cur_row += 1
                            sec_added = True
                            
                        label = field.get('label', field.get('name'))
                        extra_template.append([label, ''])
                        format_requests.append({
                            "copyPaste": {
                                "source": { "sheetId": ws_1.id, "startRowIndex": 52, "endRowIndex": 53, "startColumnIndex": 0, "endColumnIndex": 2 },
                                "destination": { "sheetId": ws_1.id, "startRowIndex": cur_row-1, "endRowIndex": cur_row, "startColumnIndex": 0, "endColumnIndex": 2 },
                                "pasteType": "PASTE_FORMAT"
                            }
                        })
                        cur_row += 1
                        
        if extra_template:
            end_row = 67 + len(extra_template) - 1
            ws_1.update(values=extra_template, range_name=f"A67:B{end_row}")
            if format_requests:
                try:
                    spreadsheet.batch_update({"requests": format_requests})
                except Exception as fe:
                    print("Warning apply formatting tab 1:", fe)
    except Exception as e:
        print("Tab 1 tidak ditemukan atau gagal disinkronkan:", e)
        
    return {
        "success": True, 
        "spreadsheet": spreadsheet.title, 
        "total_columns": len(new_headers),
        "total_rows": len(all_values) if all_values else 1
    }

def sync_schema_to_all_sheets(schema=None):
    """Menyinkronkan schema ke seluruh Google Spreadsheet bandara yang terdaftar di konfigurasi."""
    from app.models.config_store import CONFIG_FILE
    if not os.path.exists(CONFIG_FILE):
        return {"synced": [], "failed": ["Config file not found"]}
        
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        
    airports = config.get('airports', {})
    results = {"synced": [], "failed": []}
    
    for code, conf in airports.items():
        sheet_url = conf.get('sheet_url')
        if not sheet_url:
            continue
        try:
            res = sync_schema_to_sheets(sheet_url, schema)
            if res.get("success"):
                results["synced"].append(f"{code} ({res.get('spreadsheet')})")
            else:
                results["failed"].append(f"{code}: {res.get('error')}")
        except Exception as e:
            results["failed"].append(f"{code}: {str(e)}")
            
    return results

def sync_sheets_to_schema(sheet_url):
    """
    Sinkronisasi Balik: Google Sheets -> Form Builder / Web
    Membaca kolom di DATABASE_REKAP dan baris di Tab '1'.
    Jika ada penambahan atau penghapusan kolom di Spreadsheet, form_schema.json otomatis diperbarui.
    """
    if not sheet_url:
        raise ValueError("URL Spreadsheet belum dikonfigurasi.")
        
    client = get_client()
    spreadsheet = client.open_by_url(sheet_url)
    
    try:
        rekap_sheet = spreadsheet.worksheet('DATABASE_REKAP')
    except gspread.WorksheetNotFound:
        raise Exception("Tab 'DATABASE_REKAP' tidak ditemukan pada Spreadsheet.")
        
    row_1 = rekap_sheet.row_values(1)
    sheet_headers = [str(h).strip() for h in row_1 if str(h).strip()]
    
    if not sheet_headers:
        raise Exception("Header baris 1 di DATABASE_REKAP kosong.")
        
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
    with open(schema_path, 'r') as f:
        schema = json.load(f)
        
    # Kumpulkan seluruh field yang ada di schema saat ini
    existing_schema_fields = {} # name -> (step_idx, sec_idx, field_idx, field_dict)
    for s_idx, step in enumerate(schema.get('steps', [])):
        for sec_idx, sec in enumerate(step.get('sections', [])):
            for f_idx, f in enumerate(sec.get('fields', [])):
                fname = f.get('name', '').strip()
                if fname:
                    existing_schema_fields[fname] = (s_idx, sec_idx, f_idx, f)
                    
    # Baca info label dan section dari Tab '1' baris 67 ke bawah jika ada
    custom_labels_map = {}
    try:
        ws_1 = spreadsheet.worksheet('1')
        ws1_vals = ws_1.get_all_values()
        curr_sec_title = "Catatan Khusus & Tambahan"
        for r_idx in range(66, len(ws1_vals)):
            r = ws1_vals[r_idx]
            if not r: continue
            col_a = str(r[0]).strip() if len(r) > 0 else ""
            col_b = str(r[1]).strip() if len(r) > 1 else ""
            if not col_a: continue
            
            if not col_b and (col_a.isupper() or len(col_a.split()) <= 4):
                curr_sec_title = col_a.title()
            else:
                norm_key = col_a.upper().replace(' ', '_').replace('-', '_')
                custom_labels_map[norm_key] = {
                    "label": col_a,
                    "section_title": curr_sec_title
                }
    except Exception as e:
        print("Tab 1 tidak terbaca saat sync sheet to schema:", e)
        
    added_fields = []
    removed_fields = []
    
    # 1. Deteksi field non-standar yang DIHAPUS dari spreadsheet
    for fname in list(existing_schema_fields.keys()):
        if fname not in STANDARD_CORE_FIELDS and fname != 'TIMESTAMP':
            if fname not in sheet_headers:
                s_idx, sec_idx, f_idx, _ = existing_schema_fields[fname]
                schema['steps'][s_idx]['sections'][sec_idx]['fields'] = [
                    f for f in schema['steps'][s_idx]['sections'][sec_idx]['fields']
                    if f.get('name') != fname
                ]
                removed_fields.append(fname)
                
    # Bersihkan section/step yang kosong jika ada
    for step in schema.get('steps', []):
        step['sections'] = [sec for sec in step.get('sections', []) if len(sec.get('fields', [])) > 0]
    schema['steps'] = [step for step in schema.get('steps', []) if len(step.get('sections', [])) > 0]
    
    # 2. Deteksi field baru yang DITAMBAHKAN di spreadsheet
    current_names_now = set()
    for step in schema.get('steps', []):
        for sec in step.get('sections', []):
            for f in sec.get('fields', []):
                current_names_now.add(f.get('name'))
                
    for h in sheet_headers:
        if h == 'TIMESTAMP' or h in current_names_now:
            continue
            
        info = custom_labels_map.get(h)
        if not info:
            for k, val in custom_labels_map.items():
                if k in h or h in k:
                    info = val
                    break
                    
        label = info['label'] if info else h.replace('_', ' ').title()
        sec_title = info['section_title'] if info else "Field Tambahan Spreadsheet"
        
        if not schema.get('steps'):
            schema['steps'] = [{
                "title": "Langkah 1: Laporan",
                "subtitle": "Form Laporan",
                "icon": "fa-clipboard-list",
                "sections": []
            }]
            
        last_step = schema['steps'][-1]
        target_sec = None
        for sec in last_step.get('sections', []):
            if sec.get('title', '').strip().lower() == sec_title.strip().lower():
                target_sec = sec
                break
                
        if not target_sec:
            target_sec = {
                "title": sec_title,
                "icon": "fa-folder-plus",
                "fields": []
            }
            last_step['sections'].append(target_sec)
            
        target_sec['fields'].append({
            "label": label,
            "name": h,
            "type": "text",
            "required": False
        })
        added_fields.append(h)
        current_names_now.add(h)
        
    # Simpan ke form_schema.json jika ada penambahan / penghapusan
    if added_fields or removed_fields:
        with open(schema_path, 'w') as f:
            json.dump(schema, f, indent=2)
            
    return {
        "success": True,
        "spreadsheet": spreadsheet.title,
        "added": added_fields,
        "removed": removed_fields,
        "schema": schema
    }