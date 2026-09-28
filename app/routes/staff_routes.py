from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS

bp = Blueprint('staff', __name__)

@bp.before_request
def require_login():
    if 'user_id' not in session or USERS.get(session['user_id'])['role'] != 'staff':
        return redirect(url_for('auth.index'))

from app.models.config_store import get_airport_config
from app.services.gsheets_service import write_daily_report

@bp.route('/dashboard')
def dashboard():
    import os, json
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    config = get_airport_config(airport_code)
    has_sheet_url = bool(config.get('sheet_url'))
    
    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema: {e}")
        
    return render_template('staff_dashboard.html', current_user=user, has_sheet_url=has_sheet_url, schema=schema)

@bp.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    user = USERS.get(session['user_id'])
    airport_code = user['airport']
    
    config = get_airport_config(airport_code)
    sheet_url = config.get('sheet_url')
    
    if not sheet_url:
        return jsonify({"status": "error", "message": "Admin belum mengatur URL Spreadsheet untuk bandara ini!"})
    
    try:
        write_daily_report(sheet_url, data)
        return jsonify({"status": "success", "message": "Data berhasil disimpan ke Spreadsheet!"})
    except Exception as e:
        print(f"Error writing to sheets: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@bp.route('/api/active-month')
def api_active_month():
    user = USERS.get(session['user_id'])
    airport_code = user['airport']
    config = get_airport_config(airport_code)
    sheet_url = config.get('sheet_url')
    
    if not sheet_url:
        return jsonify({"success": False, "error": "No sheet configured"})
        
    try:
        from app.services.gsheets_service import get_client
        import calendar
        client = get_client()
        sheet = client.open_by_url(sheet_url)
        title = sheet.title # e.g. "DPS_SEP_2026"
        
        # Parse month and year from title
        parts = title.split('_')
        if len(parts) >= 3:
            month_abbr = parts[-2]
            year_str = parts[-1]
            
            indonesian_months = ["JAN", "FEB", "MAR", "APR", "MEI", "JUN", "JUL", "AGS", "SEP", "OKT", "NOV", "DES"]
            if month_abbr in indonesian_months:
                month_idx = indonesian_months.index(month_abbr) + 1
                year_int = int(year_str)
                last_day = calendar.monthrange(year_int, month_idx)[1]
                
                min_date = f"{year_str}-{month_idx:02d}-01"
                max_date = f"{year_str}-{month_idx:02d}-{last_day:02d}"
                
                # Cek tanggal yang sudah terisi
                filled_dates = []
                try:
                    rekap_sheet = sheet.worksheet('DATABASE_REKAP')
                    header_row = rekap_sheet.row_values(1)
                    
                    tanggal_col_idx = 3 # default fallback
                    for i, h in enumerate(header_row):
                        if str(h).strip() == 'TANGGAL':
                            tanggal_col_idx = i + 1
                            break
                            
                    filled_dates_raw = rekap_sheet.col_values(tanggal_col_idx, value_render_option='UNFORMATTED_VALUE')
                    # Hapus header
                    if len(filled_dates_raw) > 0:
                        filled_dates_raw = filled_dates_raw[1:]
                        
                    from datetime import timedelta, datetime
                    for d in filled_dates_raw:
                        if isinstance(d, (int, float)):
                            dt_val = datetime(1899, 12, 30) + timedelta(days=d)
                            filled_dates.append(dt_val.strftime("%Y-%m-%d"))
                        elif isinstance(d, str):
                            filled_dates.append(d.strip())
                except Exception as e:
                    print("Gagal fetch filled dates:", e)
                    
                return jsonify({
                    "success": True, 
                    "min": min_date, 
                    "max": max_date, 
                    "month_name": f"{month_abbr} {year_str}",
                    "filled_dates": filled_dates
                })
                
        return jsonify({"success": False, "error": "Cannot parse title"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
