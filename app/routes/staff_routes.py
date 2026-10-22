from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS, AIRPORTS

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
        val = str(data.get(key, '') or '').strip()
        return val if val and val != '-' else '-'
        
    def f_titik(jml):
        if jml == '-' or not jml:
            return '0 titik'
        s = str(jml).strip()
        if 'titik' in s.lower():
            return s
        return f"{s} titik"

    def f_percent(val):
        if val == '-' or not val:
            return '-'
        s = str(val).strip()
        if not s.endswith('%'):
            try:
                float(s.replace(',', '.'))
                return f"{s}%"
            except:
                pass
        return s
    
    tgl = v('TANGGAL')
    try:
        from datetime import datetime
        dt = datetime.strptime(tgl.split('T')[0], '%Y-%m-%d')
        months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tgl_str = f"{dt.day} {months[dt.month-1]} {dt.year}"
    except:
        tgl_str = tgl if tgl != '-' else '27 Agustus 2026'
        
    penerima_items = []
    for pk in ['PENERIMA_1', 'PENERIMA_2', 'PENERIMA_3', 'PENERIMA_4']:
        val = v(pk)
        if val != '-':
            penerima_items.append(val)
    if not penerima_items:
        penerima_items = ['Pak DT API', 'Pak GH API']
    penerima = "\n".join(f"{i+1}. {item}" for i, item in enumerate(penerima_items))
        
    catatan = ""
    idx = 1
    for i in range(1, 8):
        c = v(f'CATATAN_{i}')
        if c != '-':
            catatan += f"{idx}. {c}\n"
            idx += 1
    if not catatan:
        catatan = "-\n"
        
    # Extract only the airport code/name nicely (e.g. "1. Kantor Cabang DPS" -> "1. DPS")
    cabang_raw = v('KANTOR_CABANG')
    if cabang_raw == '-':
        cabang_str = f"1. {airport_code}"
    elif 'Kantor Cabang ' in cabang_raw:
        clean = cabang_raw.replace('Kantor Cabang ', '').strip()
        cabang_str = clean if clean.startswith('1.') else f"1. {clean}"
    elif cabang_raw.startswith('1.'):
        cabang_str = cabang_raw
    else:
        cabang_str = f"1. {cabang_raw}"

    # Helper for damage types
    def format_damage_line(jenis_bel, jenis_dip):
        parts = []
        if jenis_bel != '-' and jenis_bel:
            parts.append(jenis_bel)
        if jenis_dip != '-' and jenis_dip:
            parts.append(jenis_dip)
        if parts:
            return f"Jenis kerusakan : \n- {', '.join(parts)}\n"
        return ""

    rw_damage_str = format_damage_line(v('RUNWAY_JENIS_BELUM'), v('RUNWAY_JENIS_DIPERBAIKI'))
    twy_damage_str = format_damage_line(v('TWY_JENIS_BELUM'), v('TWY_JENIS_DIPERBAIKI'))
    apn_damage_str = format_damage_line(v('APN_JENIS_BELUM'), v('APN_JENIS_DIPERBAIKI'))

    sapaan_val = v('SAPAAN')
    if sapaan_val == '-':
        sapaan_val = 'Selamat Pagi'

    msg = f"""*Assalamu’alaikum Wr. Wb*
*{sapaan_val}*

Kepada Yth. :
{penerima}

Mohon izin,  menyampaikan Laporan Harian Kondisi Fasilitas Sisi Udara di PT Angkasa Pura Indonesia 
Tanggal : *{tgl_str}*

Region II
{cabang_str}
*A. RUNWAY*
•  Kondisi keseluruhan runway : {v('RUNWAY_KONDISI')}
•  Performance pavement : {f_percent(v('RUNWAY_PCI'))}
Jml Titik Rusak : {f_titik(v('RUNWAY_TITIK_RUSAK'))}
{rw_damage_str}Jml titik yang sudah diperbaiki : {f_titik(v('RUNWAY_TITIK_DIPERBAIKI'))}
Jml titik yang belum diperbaiki : {f_titik(v('RUNWAY_TITIK_BELUM'))}
Jml titik rusak berulang > 1x : {f_titik(v('RUNWAY_TITIK_BERULANG'))}
•  Marka :
       Standar : {v('RUNWAY_MARKA_STD')}
       Realisasi : {v('RUNWAY_MARKA_REALISASI')}
       Performance : {f_percent(v('RUNWAY_MARKA_PERF'))}
•  Standing Water :
       Pengukuran : {v('RUNWAY_STANDING_WATER')}
       Performance : {f_percent(v('RUNWAY_WATER_PERF')) if v('RUNWAY_WATER_PERF') != '-' else '100%'}
•  Rubber Removal :  
       Standar ketentuan : {v('RUNWAY_RUBBER_STD')}
       Realisasi : {v('RUNWAY_RUBBER_REAL')}
       Nilai Skid : {v('RUNWAY_RUBBER_SKID')}

*B. TAXIWAY*
•  Kondisi keseluruhan Taxiway : {v('TAXIWAY_STATUS')}
•  Performance pavement : {f_percent(v('TAXIWAY_PCI'))}
Jml Titik Rusak : {f_titik(v('TWY_TITIK_RUSAK'))}
{twy_damage_str}Jml titik yang sudah diperbaiki : {f_titik(v('TWY_TITIK_DIPERBAIKI'))}
Jml titik yang belum diperbaiki : {f_titik(v('TWY_TITIK_BELUM'))}
Jml titik rusak berulang > 1x : {f_titik(v('TWY_TITIK_BERULANG'))}
•  Marka :
      Standar : {v('TWY_MARKA_STD')}
      Realisasi : {v('TWY_MARKA_REALISASI')}
      Performance : {f_percent(v('TWY_MARKA_PERF'))}
•  Standing Water : 
      Pengukuran : {v('TWY_STANDING_WATER')}
      Performance : 100%

*C. APRON*
•  Kondisi keseluruhan. Apron : {v('APRON_KONDISI')}
•  Performance pavement : {f_percent(v('APRON_PCI'))}
Jumlah Lokasi Perbaikan : {f_titik(v('APN_TITIK_RUSAK'))}
{apn_damage_str}Realisasi Perbaikan : {f_titik(v('APN_TITIK_DIPERBAIKI'))}
Rencana Perbaikan : {f_titik(v('APN_TITIK_BELUM'))}
Jml titik rusak berulang > 1x : {f_titik(v('APN_TITIK_BERULANG'))}
•  Marka :
      Standar : {v('APN_MARKA_STD')}
      Realisasi : {v('APN_MARKA_REALISASI')}
      Performance : {f_percent(v('APN_MARKA_PERF'))}
•  Standing Water :
      Pengukuran : {v('APN_STANDING_WATER')}
      Performance : 100%

d. Pemotongan Rumput
      Standar : {v('RUMPUT_STD')}
      Realisasi : {v('RUMPUT_REALISASI')}
      Performance : {f_percent(v('RUMPUT_PERF'))}

Catatan Khusus : 
{catatan.strip()}"""
    return msg

from app.services.staging_service import (
    save_report_to_staging,
    get_staging_reports,
    get_staging_report_by_id
)

@bp.route('/dashboard')
def dashboard():
    import os, json
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    airport_info = AIRPORTS.get(airport_code, {'name': 'Lombok', 'id': 'LOP', 'code': '1. Kantor Cabang LOP'})
    config = get_airport_config(airport_code)
    has_sheet_url = bool(config.get('sheet_url'))
    
    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema: {e}")
        
    staging_reports = get_staging_reports(airport_code)
    
    from app.services.notification_service import get_notifications
    user_notifs = get_notifications(airport_code, role='staff')
    unread_notifs = sum(1 for n in user_notifs if not n.get('is_read'))
    total_notifs = len(user_notifs)
    notif_badge_num = unread_notifs if unread_notifs > 0 else total_notifs

    from app.services.gsheets_service import get_airport_sheet_calendar_data
    cal_data = get_airport_sheet_calendar_data(airport_code)
    active_month_label = cal_data.get('display_month_year', '') if cal_data else ''
    if not active_month_label:
        from app.models.config_store import get_active_month
        m_str = get_active_month(airport_code)
        if m_str:
            from app.services.gsheets_service import parse_month_year_from_title
            MONTH_NAMES_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            m_idx, y_val = parse_month_year_from_title(m_str)
            if m_idx:
                active_month_label = f"{MONTH_NAMES_ID[m_idx]} {y_val}"
    
    return render_template(
        'staff_dashboard.html', 
        current_user=user, 
        airport_code=airport_code,
        airport_info=airport_info,
        has_sheet_url=has_sheet_url, 
        schema=schema,
        staging_reports=staging_reports,
        config=config,
        notif_badge_num=notif_badge_num,
        unread_notifs_count=unread_notifs,
        total_notifs_count=total_notifs,
        active_month_label=active_month_label,
        cal_data=cal_data
    )

@bp.route('/api/staging-report/<report_id>')
def api_get_staging_report(report_id):
    user = USERS.get(session['user_id'])
    airport_code = user['airport']
    report = get_staging_report_by_id(airport_code, report_id)
    if not report:
        # Fallback toleransi jika draf di sheets belum tersinkron tetapi notifikasi revisi ada
        try:
            from app.services.notification_service import _load_raw_notifications
            notifs = _load_raw_notifications()
            matching = next((n for n in notifs if n.get('report_id') == report_id and n.get('airport', '').upper() == airport_code.upper()), None)
            if matching:
                tgl = matching.get('tanggal') or '2026-11-13'
                notes = matching.get('notes', '')
                report = {
                    "report_id": report_id,
                    "status": "REVISI",
                    "catatan_gm": notes,
                    "tanggal": tgl,
                    "submitted_by": user.get('name', f"Petugas {airport_code}"),
                    "data": {
                        "TANGGAL": tgl,
                        "CATATAN_GM": notes
                    }
                }
                return jsonify({"success": True, "report": report})
        except Exception as err:
            print("Fallback notification error:", err)
        return jsonify({"success": False, "error": "Laporan draf tidak ditemukan"}), 404
    return jsonify({"success": True, "report": report})

@bp.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    user = USERS.get(session['user_id'])
    airport_code = user['airport']
    
    config = get_airport_config(airport_code)
    sheet_url = config.get('sheet_url')
    
    if not sheet_url:
        return jsonify({"status": "error", "message": "Admin belum mengatur URL Spreadsheet Produksi untuk bandara ini!"})
    
    report_id = data.get('report_id') or None
    
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
            filtered_data = {k: v for k, v in data.items() if k in allowed}
            # Simpan juga tanggal jika terfilter
            if 'TANGGAL' in data:
                filtered_data['TANGGAL'] = data['TANGGAL']
            data = filtered_data
    except Exception as err:
        print("Warning filter submit data:", err)
    
    tgl_str = data.get('TANGGAL', '').strip()
    if not tgl_str:
        return jsonify({"status": "error", "message": "Tanggal laporan wajib diisi!"})

    # --- Validasi Duplikasi Tanggal terhadap Spreadsheet FIX (Produksi Utama) & Staging ---
    try:
        from app.services.gsheets_service import get_airport_sheet_calendar_data, invalidate_calendar_cache
        cal_data = get_airport_sheet_calendar_data(airport_code)
        if cal_data.get('success'):
            filled_dates = cal_data.get('filled_dates', [])
            staging_pending = cal_data.get('staging_pending_dates', [])
            
            # Jika pengajuan baru (bukan edit)
            if not report_id:
                if tgl_str in filled_dates:
                    return jsonify({
                        "status": "error",
                        "message": f"DITOLAK: Laporan untuk tanggal {tgl_str} SUDAH PERNAH DIISI di Spreadsheet Produksi Utama (FIX)! Sistem menolak duplikasi data. Silakan pilih tanggal lain yang belum terisi di kalender."
                    })
                if tgl_str in staging_pending:
                    return jsonify({
                        "status": "error",
                        "message": f"DITOLAK: Laporan untuk tanggal {tgl_str} saat ini SUDAH ADA di Staging dan sedang MENUNGGU TELAAH GM! Harap menunggu GM menyelesaikan verifikasi atau memberikan catatan koreksi."
                    })
            else:
                # Jika sedang mengedit draf, pastikan tanggal tidak bertabrakan dengan tanggal lain yang sudah FIX
                orig_rep = get_staging_report_by_id(airport_code, report_id)
                orig_tgl = orig_rep.get('tanggal') if orig_rep else ''
                if tgl_str != orig_tgl and tgl_str in filled_dates:
                    return jsonify({
                        "status": "error",
                        "message": f"DITOLAK: Tanggal {tgl_str} sudah pernah tercatat di Spreadsheet Produksi Utama (FIX). Tidak dapat menggunakan tanggal ini."
                    })
    except Exception as check_err:
        print(f"Warning saat validasi duplikasi tanggal staff submit: {check_err}")

    try:
        # Simpan ke spreadsheet staging khusus bandara ini
        staging_res = save_report_to_staging(
            airport_code=airport_code,
            form_data=data,
            user_name=user.get('name', f"Petugas {airport_code}"),
            report_id=report_id
        )
        
        # Segarkan cache kalender agar status staging langsung terupdate
        try:
            from app.services.gsheets_service import invalidate_calendar_cache
            invalidate_calendar_cache(airport_code)
        except Exception:
            pass

        gm_phone = config.get('gm_phone', '')
        if not gm_phone:
            gm_phone = config.get('pic_phone', '')
            
        action_text = "diperbarui (hasil revisi)" if staging_res.get('action') == 'updated' else "berhasil disimpan"
        
        gm_message = (
            f"*Laporan Harian Fasilitas Sisi Udara*\n"
            f"Cabang: *{airport_code}*\n"
            f"Tanggal: *{tgl_str}*\n"
            f"Petugas Pelapor: *{user.get('name', 'Petugas')}*\n\n"
            f"Mohon izin menyampaikan kepada Yth. General Manager {airport_code}, bahwa laporan harian airside telah {action_text} di sistem dan siap untuk ditelaah/dikoreksi.\n\n"
            f"Mohon kesediaan Bapak/Ibu untuk memeriksa di Portal Airside. Terima kasih."
        )
        
        from app.services.notification_service import create_notification
        is_updated = (staging_res.get('action') == 'updated')
        if is_updated:
            create_notification(
                airport_code=airport_code,
                recipient_role='gm',
                notif_type='pending',
                title='Laporan Revisi Dikirim',
                message=f'Petugas {user.get("name", "Petugas")} telah memperbarui laporan tanggal {tgl_str} sesuai catatan koreksi.',
                report_id=staging_res.get('report_id'),
                tanggal=tgl_str
            )
            create_notification(
                airport_code=airport_code,
                recipient_role='staff',
                notif_type='pending',
                title='Perbaikan Laporan Terkirim',
                message=f'Laporan tanggal {tgl_str} berhasil dikirim ulang ke General Manager.',
                report_id=staging_res.get('report_id'),
                tanggal=tgl_str
            )
        else:
            create_notification(
                airport_code=airport_code,
                recipient_role='gm',
                notif_type='pending',
                title='Pengajuan Laporan Baru',
                message=f'Petugas {user.get("name", "Petugas")} mengajukan laporan harian tanggal {tgl_str} untuk ditelaah.',
                report_id=staging_res.get('report_id'),
                tanggal=tgl_str
            )
            create_notification(
                airport_code=airport_code,
                recipient_role='staff',
                notif_type='pending',
                title='Laporan Diajukan ke GM',
                message=f'Laporan tanggal {tgl_str} tersimpan di Staging dan menunggu telaah General Manager.',
                report_id=staging_res.get('report_id'),
                tanggal=tgl_str
            )

        return jsonify({
            "status": "success", 
            "message": f"Data berhasil disimpan ke Spreadsheet Staging {airport_code} dan dikirim ke General Manager untuk ditelaah!",
            "report_id": staging_res.get('report_id'),
            "gm_phone": gm_phone,
            "gm_message": gm_message,
            "airport_code": airport_code
        })
    except Exception as e:
        print(f"Error saving to staging: {str(e)}")
        return jsonify({"status": "error", "message": f"Gagal menyimpan ke Staging: {str(e)}"})

@bp.route('/api/notifications', methods=['GET'])
def api_notifications():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    from app.services.notification_service import get_notifications
    notifs = get_notifications(airport_code, role='staff')
    unread_count = sum(1 for n in notifs if not n.get('is_read'))
    return jsonify({
        "success": True,
        "notifications": notifs,
        "unread_count": unread_count
    })

@bp.route('/api/notifications/mark-read', methods=['POST'])
def api_notifications_mark_read():
    data = request.json or {}
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    from app.services.notification_service import mark_notification_as_read, mark_all_as_read
    
    if data.get('mark_all'):
        mark_all_as_read(airport_code, role='staff')
    elif data.get('notif_id'):
        mark_notification_as_read(data.get('notif_id'))
    return jsonify({"success": True})


@bp.route('/api/active-month')
def api_active_month():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    force_refresh = (request.args.get('refresh') == '1')
    
    from app.services.gsheets_service import get_airport_sheet_calendar_data
    cal_data = get_airport_sheet_calendar_data(airport_code, force_refresh=force_refresh)
    return jsonify(cal_data)

