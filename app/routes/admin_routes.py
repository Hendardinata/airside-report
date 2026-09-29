from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS
from app.models.config_store import update_airport_config, get_airport_config, get_admin_config, update_admin_config
from app.services.drive_service import create_monthly_sheet
from app.services.gsheets_service import get_daily_summary
from datetime import datetime

bp = Blueprint('admin', __name__)

@bp.before_request
def require_login():
    user_id = session.get('user_id')
    user = USERS.get(user_id) if user_id else None
    if not user or user.get('role') != 'admin':
        if request.path.startswith('/admin/api/') or request.is_json:
            return jsonify({"success": False, "error": "Unauthorized. Sesi login admin diperlukan."}), 401
        return redirect(url_for('auth.index'))

@bp.route('/empty-trash', methods=['POST'])
def empty_trash():
    from app.services.drive_service import get_drive_service
    try:
        service = get_drive_service()
        service.files().emptyTrash().execute()
        return jsonify({"success": True, "message": "Trash Google Drive berhasil dikosongkan."})
    except Exception as e:
        return jsonify({"success": False, "error": f"Gagal mengosongkan trash: {str(e)}"}), 500

DEFAULT_TEMPLATE_ID = "1-NfvG7t8uhp7NPKygxv_oSDsmzP1GlajIRvkGXKjwuk"

@bp.route('/dashboard')
def dashboard():
    from app.models.airport_profiles import AIRPORTS
    from app.models.config_store import load_config
    user = USERS.get(session['user_id'])
    config = load_config()
    open_batch = request.args.get('modal') == 'batch-hub' or request.args.get('open') == 'batch-hub'
    return render_template(
        'admin_dashboard.html', 
        current_user=user, 
        airports=AIRPORTS, 
        config=config, 
        default_template_id=DEFAULT_TEMPLATE_ID,
        open_batch=open_batch
    )

@bp.route('/batch-hub')
def batch_hub():
    return redirect(url_for('admin.dashboard', modal='batch-hub'))

import re
from datetime import datetime

def extract_drive_id(text):
    if not text: return ""
    match = re.search(r'[-\w]{25,}', text)
    return match.group(0) if match else text.strip()

@bp.route('/config/update', methods=['POST'])
def update_config():
    airport_code = request.form.get('airportCode')
    sheet_url = request.form.get('sheetUrl')
    drive_folder = request.form.get('driveFolder')
    template_id = request.form.get('templateId')
    target_month_str = request.form.get('targetMonth')
    pic_phone = request.form.get('picPhone', '')
    deputy_phone = request.form.get('deputyPhone')
    admin_phone = request.form.get('adminPhone')
    
    # Bersihkan nomor HP jika ada awalan 0 atau +62
    pic_phone = ''.join(filter(str.isdigit, pic_phone))
    if pic_phone.startswith('0'):
        pic_phone = '62' + pic_phone[1:]
        
    if deputy_phone is not None:
        deputy_phone = ''.join(filter(str.isdigit, deputy_phone))
        if deputy_phone.startswith('0'):
            deputy_phone = '62' + deputy_phone[1:]
            
    if admin_phone is not None:
        admin_phone = ''.join(filter(str.isdigit, admin_phone))
        if admin_phone.startswith('0'):
            admin_phone = '62' + admin_phone[1:]
        
    drive_folder = extract_drive_id(drive_folder)
    template_id = extract_drive_id(template_id)
    
    if airport_code:
        update_airport_config(airport_code, sheet_url, drive_folder, template_id, pic_phone)
        
    if deputy_phone is not None or admin_phone is not None:
        update_admin_config(deputy_phone=deputy_phone, admin_phone=admin_phone)
    
    if sheet_url:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            import os
            cred_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
            credentials = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
            client = gspread.authorize(credentials)
            sheet = client.open_by_url(sheet_url)
            return jsonify({"status": "success", "message": "Konfigurasi tersimpan. Link Valid dan Terkoneksi."})
        except Exception as e:
            error_details = getattr(e, 'response', repr(e))
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_details = e.response.text
            return jsonify({"status": "warning", "message": f"Konfigurasi tersimpan, TAPI link ditolak. Pastikan file sudah di-Share ke email robot! Detail: {error_details}"})
            
    return jsonify({"status": "success", "message": "Konfigurasi tersimpan tanpa link."})

@bp.route('/api/config', methods=['GET'])
def get_config():
    airport_code = request.args.get('airportCode')
    if not airport_code:
        # Return only global admin config if no airport selected
        return jsonify({"success": True, "data": {}, "admin_config": get_admin_config()})
    
    config = get_airport_config(airport_code)
    admin_config = get_admin_config()
    response_data = dict(config)
    if response_data.get('template_id') == DEFAULT_TEMPLATE_ID:
        response_data['template_id'] = ""
        
    return jsonify({"success": True, "data": response_data, "admin_config": admin_config})

@bp.route('/api/rekap', methods=['GET'])
def api_rekap():
    date_str = request.args.get('date')
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    summary = get_daily_summary(date_str)
    return jsonify({"success": True, "data": summary, "date": date_str})

@bp.route('/api/create-sheet', methods=['POST'])
def api_create_sheet():
    data = request.json
    airport_code = data.get('airportCode')
    target_month_str = data.get('targetMonth')
    drive_folder = data.get('driveFolder')
    template_id = data.get('templateId')
    
    drive_folder = extract_drive_id(drive_folder)
    template_id = extract_drive_id(template_id)
    
    config = get_airport_config(airport_code)
    
    # Fallback to stored config if not provided in form
    if not drive_folder:
        drive_folder = config.get('drive_folder')
    if not template_id:
        template_id = config.get('template_id')
        
    # Final fallback to default template
    if not template_id:
        template_id = DEFAULT_TEMPLATE_ID
    
    if not drive_folder:
        return jsonify({"success": False, "error": "Folder ID Tujuan tidak ditemukan. Silakan isi terlebih dahulu."}), 400
        
    if not target_month_str:
        return jsonify({"success": False, "error": "Target Bulan Laporan belum dipilih. Silakan pilih bulan terlebih dahulu."}), 400

    try:
        dt = datetime.strptime(target_month_str, "%Y-%m")
        indonesian_months = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]
        month = indonesian_months[dt.month - 1]
        year = dt.strftime("%Y")
            
        new_name = f"{airport_code}_{month}_{year}"
        
        # --- CEK DUPLIKASI ---
        from app.services.drive_service import get_drive_service
        try:
            drive_svc = get_drive_service()
            query = f"name='{new_name}' and '{drive_folder}' in parents and trashed=false"
            res = drive_svc.files().list(q=query, spaces='drive', fields='files(id, name, webViewLink)').execute()
            if res.get('files'):
                return jsonify({"success": False, "error": f"GAGAL: Spreadsheet dengan nama '{new_name}' SUDAH ADA di dalam folder tersebut! Sistem menolak membuat duplikat."}), 400
        except Exception as check_err:
            print("Gagal cek duplikat:", check_err)
            
        new_url = create_monthly_sheet(new_name, drive_folder, template_id)
        # Update config to point to new sheet
        update_airport_config(airport_code, new_url)
        
        # --- Update Judul di dalam Spreadsheet (Cell A1) ---
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            import os
            cred_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
            credentials = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
            client = gspread.authorize(credentials)
            sheet = client.open_by_url(new_url)
            
            title_text = f"LAPORAN HARIAN {airport_code} — {month.upper()} {year}"
            
            # Ganti teks di tab PETUNJUK
            try:
                ws_petunjuk = sheet.worksheet("PETUNJUK")
                ws_petunjuk.update_acell('A1', title_text)
            except:
                pass
                
            # Ganti teks di tab 1
            try:
                ws_1 = sheet.worksheet("1")
                ws_1.update_acell('A1', title_text)
            except:
                pass
        except Exception as sheet_err:
            print("Warning: Gagal mengganti teks judul di dalam sheet:", sheet_err)
            
        return jsonify({"success": True, "url": new_url})
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'content'):
            error_msg = e.content.decode('utf-8') if isinstance(e.content, bytes) else str(e.content)
        error_msg = error_msg.replace('<', '&lt;').replace('>', '&gt;')
        return jsonify({"success": False, "error": f"Error: {error_msg}. Pastikan Folder tujuan sudah di-Share (Editor) ke email Robot Service Account!"}), 500

@bp.route('/api/list-sheets', methods=['GET'])
def api_list_sheets():
    airport_code = request.args.get('airportCode')
    drive_folder = request.args.get('driveFolder')
    drive_folder = extract_drive_id(drive_folder)
    
    if not drive_folder:
        return jsonify({"success": False, "error": "Folder ID Google Drive kosong."})
        
    try:
        from app.services.drive_service import get_drive_service
        drive_service = get_drive_service()
        # Query all active spreadsheets in this folder
        query = f"'{drive_folder}' in parents and trashed=false and mimeType='application/vnd.google-apps.spreadsheet'"
        results = drive_service.files().list(
            q=query, 
            spaces='drive', 
            fields='files(id, name, webViewLink, modifiedTime)',
            orderBy='modifiedTime desc'
        ).execute()
        
        all_files = results.get('files', [])
        
        if airport_code:
            code_upper = airport_code.upper()
            matching = [f for f in all_files if code_upper in f.get('name', '').upper()]
            others = [f for f in all_files if code_upper not in f.get('name', '').upper()]
            all_files = matching + others
            
        return jsonify({"success": True, "files": all_files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/api/schema', methods=['GET'])
def get_schema():
    import os, json
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
            return jsonify({"success": True, "data": schema})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/api/schema/update', methods=['POST'])
def update_schema():
    import os, json
    try:
        schema_data = request.json
        if not schema_data or 'steps' not in schema_data:
            return jsonify({"success": False, "error": "Invalid schema data"})
            
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'w') as f:
            json.dump(schema_data, f, indent=2)
            
        # SINKRONISASI OTOMATIS KE SELURUH GOOGLE SPREADSHEET
        from app.services.gsheets_service import sync_schema_to_all_sheets
        sync_result = sync_schema_to_all_sheets(schema_data)
            
        return jsonify({
            "success": True, 
            "message": "Schema berhasil diperbarui dan disinkronkan ke Spreadsheet",
            "sync_result": sync_result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@bp.route('/api/schema/sync-from-sheet', methods=['POST'])
def api_sync_schema_from_sheet():
    data = request.json or {}
    airport_code = data.get('airportCode', 'LOP')
    
    config = get_airport_config(airport_code)
    sheet_url = config.get('sheet_url')
    
    if not sheet_url:
        # Fallback cari bandara pertama yang memiliki URL spreadsheet
        import os, json
        from app.models.config_store import CONFIG_FILE
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                c = json.load(f)
                for code, conf in c.get('airports', {}).items():
                    if conf.get('sheet_url'):
                        sheet_url = conf.get('sheet_url')
                        airport_code = code
                        break
                        
    if not sheet_url:
        return jsonify({"success": False, "error": f"Tautan spreadsheet untuk bandara {airport_code} belum dikonfigurasi"})
        
    try:
        from app.services.gsheets_service import sync_sheets_to_schema
        result = sync_sheets_to_schema(sheet_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@bp.route('/api/sync-rekap', methods=['POST'])
def api_sync_rekap():
    data = request.json
    airport_code = data.get('airportCode')
    if not airport_code:
        return jsonify({"success": False, "error": "Kode bandara diperlukan"})
        
    config = get_airport_config(airport_code)
    sheet_url = config.get('sheet_url')
    if not sheet_url:
        return jsonify({"success": False, "error": "Tautan spreadsheet belum dikonfigurasi"})
        
    try:
        from app.services.gsheets_service import sync_sheets_to_rekap
        synced = sync_sheets_to_rekap(sheet_url)
        return jsonify({"success": True, "synced_count": synced})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==============================================================================
# BATCH OPERATIONS HUB (V2) - MULTI-AIRPORT ENTERPRISE API
# ==============================================================================

@bp.route('/api/batch/create-sheets', methods=['POST'])
def api_batch_create_sheets():
    """
    Membuat & mengaktifkan Google Spreadsheet baru secara massal untuk seluruh cabang terpilih.
    Otomatis memeriksa duplikasi, menggandakan template master, menyelaraskan judul,
    menyinkronkan kolom form schema, dan langsung mengaktifkannya sebagai spreadsheet aktif.
    """
    data = request.json or {}
    target_month_str = data.get('targetMonth')
    raw_template_id = data.get('templateId') or DEFAULT_TEMPLATE_ID
    template_id = extract_drive_id(raw_template_id)
    airport_codes = data.get('airports', ['LOP', 'DPS', 'BWX', 'KOE'])
    
    if not target_month_str:
        return jsonify({"success": False, "error": "Target Bulan Laporan belum dipilih."}), 400
        
    try:
        dt = datetime.strptime(target_month_str, "%Y-%m")
        indonesian_months = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]
        month = indonesian_months[dt.month - 1]
        year = dt.strftime("%Y")
    except Exception as e:
        return jsonify({"success": False, "error": f"Format bulan tidak valid: {str(e)}"}), 400
        
    results = []
    from app.services.drive_service import get_drive_service, create_monthly_sheet
    from app.services.gsheets_service import sync_schema_to_sheets, get_client
    
    for code in airport_codes:
        conf = get_airport_config(code)
        drive_folder = conf.get('drive_folder')
        
        if not drive_folder:
            results.append({
                "airport": code,
                "status": "error",
                "message": "Folder Google Drive tujuan belum dikonfigurasi di sistem."
            })
            continue
            
        new_name = f"{code}_{month}_{year}"
        
        # 1. Cek duplikasi di Google Drive
        already_exists = False
        try:
            drive_svc = get_drive_service()
            query = f"name='{new_name}' and '{drive_folder}' in parents and trashed=false"
            res = drive_svc.files().list(q=query, spaces='drive', fields='files(id, name, webViewLink)').execute()
            if res.get('files'):
                existing_file = res['files'][0]
                existing_url = existing_file.get('webViewLink') or f"https://docs.google.com/spreadsheets/d/{existing_file['id']}/edit"
                # Otomatis langsung aktifkan
                update_airport_config(code, existing_url)
                try:
                    sync_schema_to_sheets(existing_url)
                except Exception:
                    pass
                results.append({
                    "airport": code,
                    "status": "warning",
                    "url": existing_url,
                    "sheet_name": new_name,
                    "message": f"Sheet '{new_name}' sudah ada di Drive. Berhasil disinkronkan & diaktifkan."
                })
                already_exists = True
        except Exception as check_err:
            print(f"Warning cek duplikat {code}:", check_err)
            
        if already_exists:
            continue
            
        # 2. Buat sheet baru dari template master
        try:
            new_url = create_monthly_sheet(new_name, drive_folder, template_id)
            
            # 3. Update Judul Cell A1 di tab PETUNJUK dan 1
            try:
                client = get_client()
                sheet = client.open_by_url(new_url)
                title_text = f"LAPORAN HARIAN {code} — {month.upper()} {year}"
                try:
                    ws_petunjuk = sheet.worksheet("PETUNJUK")
                    ws_petunjuk.update_acell('A1', title_text)
                except Exception:
                    pass
                try:
                    ws_1 = sheet.worksheet("1")
                    ws_1.update_acell('A1', title_text)
                except Exception:
                    pass
            except Exception as title_err:
                print(f"Warning update title {code}:", title_err)
                
            # 4. Sinkronkan schema form aktif ke sheet baru
            try:
                sync_schema_to_sheets(new_url)
            except Exception as sync_err:
                print(f"Warning sync schema {code}:", sync_err)
                
            # 5. Otomatis LANGSUNG AKTIFKAN di konfigurasi cabang
            update_airport_config(code, new_url)
            
            results.append({
                "airport": code,
                "status": "success",
                "url": new_url,
                "sheet_name": new_name,
                "message": f"Berhasil dibuat & langsung diaktifkan ({new_name})"
            })
        except Exception as create_err:
            results.append({
                "airport": code,
                "status": "error",
                "message": f"Gagal membuat sheet: {str(create_err)}"
            })
            
    return jsonify({
        "success": True,
        "month_label": f"{month} {year}",
        "results": results
    })

@bp.route('/api/batch/update-matrix', methods=['POST'])
def api_batch_update_matrix():
    """Menyimpan seluruh konfigurasi tabel matriks cabang sekaligus."""
    data = request.json or {}
    airports_data = data.get('airports', {})
    admin_data = data.get('admin', {})
    
    for code, item in airports_data.items():
        drive_folder = extract_drive_id(item.get('drive_folder'))
        sheet_url = item.get('sheet_url')
        pic_phone = item.get('pic_phone', '')
        if pic_phone:
            pic_phone = ''.join(filter(str.isdigit, pic_phone))
            if pic_phone.startswith('0'):
                pic_phone = '62' + pic_phone[1:]
        update_airport_config(code, sheet_url=sheet_url, drive_folder=drive_folder, pic_phone=pic_phone)
        
    deputy = admin_data.get('deputy_phone')
    admin_p = admin_data.get('admin_phone')
    if deputy is not None:
        deputy = ''.join(filter(str.isdigit, deputy))
        if deputy.startswith('0'):
            deputy = '62' + deputy[1:]
    if admin_p is not None:
        admin_p = ''.join(filter(str.isdigit, admin_p))
        if admin_p.startswith('0'):
            admin_p = '62' + admin_p[1:]
    update_admin_config(deputy_phone=deputy, admin_phone=admin_p)
    
    return jsonify({"success": True, "message": "Konfigurasi seluruh cabang berhasil disimpan!"})

@bp.route('/api/batch/sync-all-rekap', methods=['POST'])
def api_batch_sync_all_rekap():
    """Menyinkronkan seluruh tab harian manual di 4 bandara ke DATABASE_REKAP masing-masing."""
    from app.services.gsheets_service import sync_sheets_to_rekap
    from app.models.config_store import load_config
    config = load_config()
    results = {}
    
    for code, conf in config.get('airports', {}).items():
        url = conf.get('sheet_url')
        if url:
            try:
                cnt = sync_sheets_to_rekap(url)
                results[code] = {"status": "success", "count": cnt}
            except Exception as e:
                results[code] = {"status": "error", "error": str(e)}
        else:
            results[code] = {"status": "skipped", "message": "Belum ada link sheet aktif"}
            
    return jsonify({"success": True, "results": results})