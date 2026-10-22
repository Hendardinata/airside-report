from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS, AIRPORTS
from app.models.config_store import get_airport_config, get_admin_config
from app.services.staging_service import (
    get_staging_reports,
    get_staging_report_by_id,
    gm_request_revision,
    gm_approve_report
)
from app.routes.staff_routes import generate_wa_message

bp = Blueprint('gm', __name__)

@bp.before_request
def require_login():
    user_id = session.get('user_id')
    user = USERS.get(user_id) if user_id else None
    if not user or user.get('role') != 'gm':
        if request.path.startswith('/gm/api/') or request.is_json or request.method == 'POST':
            return jsonify({"status": "error", "message": "Unauthorized. Sesi login General Manager diperlukan."}), 401
        return redirect(url_for('auth.index'))

@bp.route('/dashboard')
def dashboard():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    airport_info = AIRPORTS.get(airport_code, {'name': airport_code})
    
    config = get_airport_config(airport_code)
    reports = get_staging_reports(airport_code)
    
    # Hitung statistik
    pending_count = sum(1 for r in reports if r.get('status') == 'PENDING_GM')
    revisi_count = sum(1 for r in reports if r.get('status') == 'REVISI')
    
    import os, json
    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema in gm_routes: {e}")

    from app.services.notification_service import get_notifications
    gm_notifs = get_notifications(airport_code, role='gm')
    unread_notifs = sum(1 for n in gm_notifs if not n.get('is_read'))
    total_notifs = len(gm_notifs)
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
    active_sheet_title = cal_data.get('sheet_title', '') if cal_data else ''

    return render_template(
        'gm_dashboard.html',
        current_user=user,
        airport_code=airport_code,
        airport_info=airport_info,
        config=config,
        reports=reports,
        pending_count=pending_count,
        revisi_count=revisi_count,
        schema=schema,
        notif_badge_num=notif_badge_num,
        unread_notifs_count=unread_notifs,
        total_notifs_count=total_notifs,
        active_month_label=active_month_label,
        active_sheet_title=active_sheet_title,
        cal_data=cal_data
    )

@bp.route('/api/reports', methods=['GET'])
def api_reports():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    reports = get_staging_reports(airport_code)
    return jsonify({"success": True, "reports": reports})

@bp.route('/api/report/<report_id>', methods=['GET'])
def api_report_detail(report_id):
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    report = get_staging_report_by_id(airport_code, report_id)
    if not report:
        return jsonify({"success": False, "error": "Laporan tidak ditemukan"}), 404
    return jsonify({"success": True, "report": report})

@bp.route('/api/revision', methods=['POST'])
def api_revision():
    data = request.json or {}
    report_id = data.get('report_id')
    notes = (data.get('notes') or '').strip()
    
    if not report_id:
        return jsonify({"success": False, "error": "ID Laporan diperlukan"}), 400
    if not notes:
        return jsonify({"success": False, "error": "Catatan koreksi/revisi wajib diisi"}), 400

    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    
    try:
        res = gm_request_revision(airport_code, report_id, notes)
        report = get_staging_report_by_id(airport_code, report_id)
        tgl = report.get('tanggal', '') if report else ''
        
        # Format pesan WhatsApp ke Petugas / PIC
        airport_conf = get_airport_config(airport_code)
        pic_phone = airport_conf.get('pic_phone', '')
        staff_message = (
            f"*Catatan Koreksi Laporan Airside dari General Manager*\n"
            f"Cabang: *{airport_code}*\n"
            f"Tanggal Laporan: *{tgl}*\n\n"
            f"Mohon izin menyampaikan bahwa terdapat beberapa poin koreksi/revisi yang perlu disesuaikan pada laporan tersebut:\n\n"
            f"📌 *Poin Koreksi :*\n{notes}\n\n"
            f"Mohon bantuan rekan-rekan petugas untuk membuka portal, memperbarui data sesuai catatan, dan mengirimkan kembali ke GM. Terima kasih."
        )

        from app.services.notification_service import create_notification
        create_notification(
            airport_code=airport_code,
            recipient_role='staff',
            notif_type='revisi',
            title='Catatan Koreksi GM',
            message=f'Pesan GM: "{notes}"',
            report_id=report_id,
            tanggal=tgl,
            notes=notes
        )

        return jsonify({
            "success": True,
            "message": "Catatan koreksi berhasil disimpan. Status laporan diubah menjadi 'Perlu Revisi'.",
            "pic_phone": pic_phone,
            "staff_message": staff_message
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/api/approve', methods=['POST'])
def api_approve():
    data = request.json or {}
    report_id = data.get('report_id')
    
    if not report_id:
        return jsonify({"success": False, "error": "ID Laporan diperlukan"}), 400

    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    
    try:
        res = gm_approve_report(airport_code, report_id)
        form_data = res.get('form_data', {})
        tgl = form_data.get('TANGGAL', '') or form_data.get('TANGGAL_LAPORAN', '')
        
        # Simpan notifikasi ke Petugas bahwa laporan disetujui GM
        from app.services.notification_service import create_notification
        create_notification(
            airport_code=airport_code,
            recipient_role='staff',
            notif_type='approved',
            title='Laporan Disetujui GM',
            message=f'Laporan Harian Airside tanggal {tgl} telah diverifikasi dan disetujui oleh General Manager serta dipindahkan ke Spreadsheet Produksi.',
            report_id=report_id,
            tanggal=tgl
        )
        # Notifikasi untuk riwayat GM juga
        create_notification(
            airport_code=airport_code,
            recipient_role='gm',
            notif_type='approved',
            title='Laporan Berhasil Disetujui',
            message=f'Laporan tanggal {tgl} (ID: {report_id}) telah berhasil disetujui & disinkronkan ke Spreadsheet Produksi.',
            report_id=report_id,
            tanggal=tgl
        )
        
        # Generate format pesan laporan resmi untuk WhatsApp ke Admin Regional II
        admin_conf = get_admin_config()
        admin_phone = admin_conf.get('admin_phone', '')
        wa_report = generate_wa_message(form_data, airport_code)

        approval_header = (
            f"*[VERIFIKASI GM SELESAI - LAPORAN DISETUJUI]*\n"
            f"Laporan Harian Fasilitas Sisi Udara Cabang *{airport_code}* telah diverifikasi dan disetujui oleh General Manager.\n\n"
        )
        full_admin_message = approval_header + wa_report

        # Invalidate cache kalender
        try:
            from app.services.gsheets_service import invalidate_calendar_cache
            invalidate_calendar_cache(airport_code)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Laporan berhasil disetujui, dimasukkan ke Spreadsheet Produksi, dan dihapus dari Staging.",
            "admin_phone": admin_phone,
            "admin_message": full_admin_message
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/api/delete-report', methods=['POST'])
def api_delete_report():
    data = request.json or {}
    report_id = data.get('report_id')
    if not report_id:
        return jsonify({"success": False, "error": "ID Laporan diperlukan"}), 400

    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')

    try:
        from app.services.staging_service import delete_staging_report
        from app.services.gsheets_service import invalidate_calendar_cache
        from app.services.notification_service import delete_notifications_by_report_id

        res = delete_staging_report(airport_code, report_id)
        delete_notifications_by_report_id(airport_code, report_id)
        invalidate_calendar_cache(airport_code)
        return jsonify({"success": True, "message": "Laporan pengajuan dan notifikasi terkait berhasil dihapus dari sistem."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/api/notifications', methods=['GET'])
def api_notifications():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    from app.services.notification_service import get_notifications
    notifs = get_notifications(airport_code, role='gm')
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
        mark_all_as_read(airport_code, role='gm')
    elif data.get('notif_id'):
        mark_notification_as_read(data.get('notif_id'))
    return jsonify({"success": True})

