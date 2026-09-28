from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS
from app.models.config_store import update_airport_config, get_airport_config
from app.services.drive_service import create_monthly_sheet
from app.services.gsheets_service import get_daily_summary
from datetime import datetime

bp = Blueprint('admin', __name__)

@bp.before_request
def require_login():
    if request.endpoint == 'admin.empty_trash':
        return # Allow empty trash without login for debugging
    if 'user_id' not in session or USERS.get(session['user_id'])['role'] != 'admin':
        return redirect(url_for('auth.index'))

@bp.route('/empty-trash')
def empty_trash():
    from app.services.drive_service import get_drive_service
    try:
        service = get_drive_service()
        service.files().emptyTrash().execute()
        return "Trash dikosongkan! Silakan kembali dan coba Buat Sheet lagi."
    except Exception as e:
        return f"Gagal: {str(e)}"

@bp.route('/dashboard')
def dashboard():
    user = USERS.get(session['user_id'])
    return render_template('admin_dashboard.html', current_user=user)

import re
from datetime import datetime

def extract_drive_id(text):
    if not text: return ""
    match = re.search(r'[-\w]{25,}', text)
    return match.group(0) if match else text.strip()

DEFAULT_TEMPLATE_ID = "1-NfvG7t8uhp7NPKygxv_oSDsmzP1GlajIRvkGXKjwuk"

@bp.route('/config/update', methods=['POST'])
def update_config():
    airport_code = request.form.get('airportCode')
    sheet_url = request.form.get('sheetUrl')
    drive_folder = request.form.get('driveFolder')
    template_id = request.form.get('templateId')
    target_month_str = request.form.get('targetMonth')
    pic_phone = request.form.get('picPhone', '')
    
    # Bersihkan nomor HP jika ada awalan 0 atau +62
    pic_phone = ''.join(filter(str.isdigit, pic_phone))
    if pic_phone.startswith('0'):
        pic_phone = '62' + pic_phone[1:]
        
    drive_folder = extract_drive_id(drive_folder)
    template_id = extract_drive_id(template_id)
    
    update_airport_config(airport_code, sheet_url, drive_folder, template_id, pic_phone)
    
    if sheet_url:
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            credentials = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
            client = gspread.authorize(credentials)
            sheet = client.open_by_url(sheet_url)
            return jsonify({"status": "success", "message": "Konfigurasi tersimpan. Link Valid dan Terkoneksi (✅)."})
        except Exception as e:
            error_details = getattr(e, 'response', repr(e))
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_details = e.response.text
            return jsonify({"status": "warning", "message": f"Konfigurasi tersimpan, TAPI link ditolak (❌). Pastikan file sudah di-Share ke email robot! Detail: {error_details}"})
            
    return jsonify({"status": "success", "message": "Konfigurasi tersimpan tanpa link."})

@bp.route('/api/config', methods=['GET'])
def get_config():
    airport_code = request.args.get('airportCode')
    if not airport_code:
        return jsonify({"success": False, "error": "Missing airportCode"}), 400
    
    config = get_airport_config(airport_code)
    response_data = dict(config)
    if response_data.get('template_id') == DEFAULT_TEMPLATE_ID:
        response_data['template_id'] = ""
        
    return jsonify({"success": True, "data": response_data})

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
            credentials = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
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
            
        return jsonify({"success": True, "message": "Schema berhasil diperbarui"})
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