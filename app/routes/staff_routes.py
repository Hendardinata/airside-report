from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS

bp = Blueprint('staff', __name__)

@bp.before_request
def require_login():
    user_id = session.get('user_id')
    user = USERS.get(user_id) if user_id else None
    if not user or user.get('role') != 'staff':
        if request.path.startswith('/staff/api/') or request.is_json or request.method == 'POST':
            return jsonify({"status": "error", "message": "Unauthorized. Sesi login petugas diperlukan."}), 401
        return redirect(url_for('auth.index'))

from app.models.config_store import get_airport_config, get_admin_config
from app.services.gsheets_service import write_daily_report

def generate_wa_message(data, airport_code):
    def v(key):
        val = data.get(key, '').strip()
        return val if val and val != '-' else '-'
        
    def f_kerusakan(jml, jenis='-'):
        if jml == '-' and jenis == '-': return '-'
        res = f"{jml}"
        if jml != '-' and not jml.lower().endswith('titik'):
            res += " titik"
        if jenis != '-':
            res += f" ({jenis})"
        return res
    
    tgl = v('TANGGAL')
    try:
        from datetime import datetime
        dt = datetime.strptime(tgl, '%Y-%m-%d')
        months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tgl_str = f"{dt.day} {months[dt.month-1]} {dt.year}"
    except:
        tgl_str = tgl
        
    penerima = f"1. {v('PENERIMA_1')}\n2. {v('PENERIMA_2')}\n3. {v('PENERIMA_3')}"
    if v('PENERIMA_4') != '-':
        penerima += f"\n4. {v('PENERIMA_4')}"
        
    catatan = ""
    idx = 1
    for i in range(1, 7):
        c = v(f'CATATAN_{i}')
        if c != '-':
            catatan += f"{idx}. {c}\n"
            idx += 1
    if not catatan:
        catatan = "-\n"
        
    # Extract only the airport code/name nicely (e.g. "1. Kantor Cabang LOP" -> "LOP")
    cabang_str = v('KANTOR_CABANG')
    
    msg = f"""*Assalamu'alaikum Wr. Wb*
*{v('SAPAAN')}*

Kepada Yth. :
{penerima}

Mohon izin, menyampaikan Laporan Harian Kondisi Fasilitas Sisi Udara di PT Angkasa Pura Indonesia
Tanggal : *{tgl_str}*

Region II
{cabang_str}

*A. RUNWAY*
• Kondisi Keseluruhan : {v('RUNWAY_KONDISI')}
• Performance (PCI)   : {v('RUNWAY_PCI')}
• Titik Kerusakan     : {f_kerusakan(v('RUNWAY_TITIK_RUSAK'))}
  - Sudah Diperbaiki  : {f_kerusakan(v('RUNWAY_TITIK_DIPERBAIKI'), v('RUNWAY_JENIS_DIPERBAIKI'))}
  - Belum Diperbaiki  : {f_kerusakan(v('RUNWAY_TITIK_BELUM'), v('RUNWAY_JENIS_BELUM'))}
  - Rusak Berulang    : {f_kerusakan(v('RUNWAY_TITIK_BERULANG'))}
• Marka :
  - Standar     : {v('RUNWAY_MARKA_STD')}
  - Realisasi   : {v('RUNWAY_MARKA_REALISASI')}
  - Performance : {v('RUNWAY_MARKA_PERF')}
• Standing Water :
  - Pengukuran  : {v('RUNWAY_STANDING_WATER')}
  - Performance : {v('RUNWAY_WATER_PERF')}
• Rubber Removal :
  - Standar     : {v('RUNWAY_RUBBER_STD')}
  - Realisasi   : {v('RUNWAY_RUBBER_REAL')}
  - Nilai Skid  : {v('RUNWAY_RUBBER_SKID')}

*B. TAXIWAY*
• Kondisi Keseluruhan : {v('TAXIWAY_STATUS')} ({v('TAXIWAY_NAMA')})
• Performance (PCI)   : {v('TAXIWAY_PCI')}
• Titik Kerusakan     : {f_kerusakan(v('TWY_TITIK_RUSAK'))}
  - Sudah Diperbaiki  : {f_kerusakan(v('TWY_TITIK_DIPERBAIKI'), v('TWY_JENIS_DIPERBAIKI'))}
  - Belum Diperbaiki  : {f_kerusakan(v('TWY_TITIK_BELUM'), v('TWY_JENIS_BELUM'))}
  - Rusak Berulang    : {f_kerusakan(v('TWY_TITIK_BERULANG'))}
• Marka :
  - Standar     : {v('TWY_MARKA_STD')}
  - Realisasi   : {v('TWY_MARKA_REALISASI')}
  - Performance : {v('TWY_MARKA_PERF')}
• Standing Water : 
  - Pengukuran  : {v('TWY_STANDING_WATER')}

*C. APRON*
• Kondisi Keseluruhan : {v('APRON_KONDISI')}
• Performance (PCI)   : {v('APRON_PCI')}
• Titik Kerusakan     : {f_kerusakan(v('APN_TITIK_RUSAK'))}
  - Sudah Diperbaiki  : {f_kerusakan(v('APN_TITIK_DIPERBAIKI'), v('APN_JENIS_DIPERBAIKI'))}
  - Belum Diperbaiki  : {f_kerusakan(v('APN_TITIK_BELUM'), v('APN_JENIS_BELUM'))}
  - Rusak Berulang    : {f_kerusakan(v('APN_TITIK_BERULANG'))}
• Marka :
  - Standar     : {v('APN_MARKA_STD')}
  - Realisasi   : {v('APN_MARKA_REALISASI')}
  - Performance : {v('APN_MARKA_PERF')}
• Standing Water :
  - Pengukuran  : {v('APN_STANDING_WATER')}

*D. PEMOTONGAN RUMPUT*
  - Standar     : {v('RUMPUT_STD')}
  - Realisasi   : {v('RUMPUT_REALISASI')}
  - Performance : {v('RUMPUT_PERF')}

*Catatan Khusus :*
{catatan.strip()}"""
    return msg

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
    
    # Filter data agar hanya field yang sah di schema aktif yang diproses
    import os, json
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema_data = json.load(f)
            allowed = set()
            for step in schema_data.get('steps', []):
                for sec in step.get('sections', []):
                    for f_item in sec.get('fields', []):
                        allowed.add(f_item.get('name'))
            data = {k: v for k, v in data.items() if k in allowed}
    except Exception as err:
        print("Warning filter submit data:", err)
    
    try:
        write_daily_report(sheet_url, data)
        admin_config = get_admin_config()
        admin_phone = admin_config.get('admin_phone', '')
        admin_message = generate_wa_message(data, airport_code)
        
        return jsonify({
            "status": "success", 
            "message": "Data berhasil disimpan ke Spreadsheet!",
            "admin_phone": admin_phone,
            "admin_message": admin_message,
            "airport_code": airport_code
        })
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
                    header_rows = rekap_sheet.get_values('A1:ZZ3')
                    header_row = []
                    if header_rows:
                        for row in header_rows:
                            if 'TANGGAL' in row or 'KANTOR_CABANG' in row:
                                header_row = row
                                break
                        if not header_row and len(header_rows) > 0:
                            header_row = header_rows[0]
                    
                    tanggal_col_idx = 3 # default fallback
                    if header_row:
                        for i, h in enumerate(header_row):
                            if str(h).strip() == 'TANGGAL':
                                tanggal_col_idx = i + 1
                                break
                            
                    filled_dates_raw = rekap_sheet.col_values(tanggal_col_idx, value_render_option='UNFORMATTED_VALUE')
                    
                    # Abaikan nilai-nilai dari area header (baris 1-3)
                    # Karena kita tidak tahu persis index mulainya data (setelah header_row),
                    # kita buang string header
                    cleaned_raw = []
                    for val in filled_dates_raw:
                        if isinstance(val, str) and (val.strip().upper() == 'TANGGAL' or val.strip() == ''):
                            continue
                        cleaned_raw.append(val)
                        
                    filled_dates_raw = cleaned_raw
                        
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
