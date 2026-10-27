from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models.airport_profiles import USERS, AIRPORTS
from app.models.config_store import get_airport_config, get_admin_config
from app.services.staging_service import (
    get_staging_reports,
    get_staging_report_by_id,
    gm_request_revision,
    gm_approve_report,
    update_staging_report_by_dh
)
from app.routes.staff_routes import generate_wa_message

bp = Blueprint('gm', __name__)

@bp.before_request
def require_login():
    user_id = session.get('user_id')
    user = USERS.get(user_id) if user_id else None
    if not user or user.get('role') not in ('dh', 'gm') or not user.get('is_active', True):
        if request.path.startswith('/gm/api/') or request.is_json or request.method == 'POST':
            return jsonify({"status": "error", "message": "Unauthorized. Sesi login Department Head diperlukan."}), 401
        return redirect(url_for('auth.index'))

MONTH_NAMES_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

def format_indo_date(date_str):
    if not date_str:
        return '-'
    try:
        parts = str(date_str).split('T')[0].split('-')
        if len(parts) == 3:
            day = int(parts[2])
            month = int(parts[1])
            year = parts[0]
            if 1 <= month <= 12:
                return f"{day} {MONTH_NAMES_ID[month]} {year}"
    except Exception:
        pass
    return str(date_str)

@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    airport_info = AIRPORTS.get(airport_code, {'name': airport_code})
    
    config = get_airport_config(airport_code)
    reports = get_staging_reports(airport_code)
    for r in reports:
        r['tanggal_indo'] = format_indo_date(r.get('tanggal'))
    
    # Hitung statistik staging
    pending_count = sum(1 for r in reports if r.get('status') in ('PENDING_DH', 'PENDING_GM'))
    revisi_count = sum(1 for r in reports if r.get('status') == 'REVISI')

    # Ambil laporan yang telah disetujui & masuk ke Spreadsheet Produksi Utama
    from app.services.gsheets_service import get_production_approved_reports
    approved_reports = get_production_approved_reports(airport_code)
    approved_count = len(approved_reports)
    
    import os, json
    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema in gm_routes: {e}")

    from app.services.notification_service import get_notifications
    gm_notifs = get_notifications(airport_code, role='dh')
    unread_notifs = sum(1 for n in gm_notifs if not n.get('is_read'))
    total_notifs = len(gm_notifs)
    notif_badge_num = unread_notifs

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
        approved_reports=approved_reports,
        approved_count=approved_count,
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

@bp.route('/api/approved-reports', methods=['GET'])
def api_approved_reports():
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    from app.services.gsheets_service import get_production_approved_reports
    reports = get_production_approved_reports(airport_code)
    return jsonify({"success": True, "reports": reports, "count": len(reports)})

@bp.route('/api/report/<report_id>', methods=['GET'])
def api_report_detail(report_id):
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    report = get_staging_report_by_id(airport_code, report_id)
    if not report:
        from app.services.gsheets_service import get_production_report_by_id
        report = get_production_report_by_id(airport_code, report_id)

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
        target_username = report.get('submitted_by_username') if report else None
        target_name = report.get('submitted_by') if report else f"Petugas {airport_code}"
        tgl = report.get('tanggal', '') if report else ''
        
        # Format pesan WhatsApp ke Petugas / PIC
        airport_conf = get_airport_config(airport_code)
        pic_phone = airport_conf.get('pic_phone', '')
        if target_username:
            target_user_record = USERS.get(target_username)
            if target_user_record and target_user_record.get('phone'):
                pic_phone = target_user_record.get('phone')

        staff_message = (
            f"*Catatan Koreksi Laporan Airside dari Department Head*\n"
            f"Cabang: *{airport_code}*\n"
            f"Tanggal Laporan: *{tgl}*\n"
            f"Ditujukan Kepada Petugas: *{target_name}*\n\n"
            f"Mohon izin menyampaikan bahwa terdapat beberapa poin koreksi/revisi yang perlu disesuaikan pada laporan tersebut:\n\n"
            f"📌 *Poin Koreksi :*\n{notes}\n\n"
            f"Mohon bantuan Sdr. {target_name} untuk membuka portal, memperbarui data sesuai catatan, dan mengirimkan kembali ke Department Head. Terima kasih."
        )

        from app.services.notification_service import create_notification
        create_notification(
            airport_code=airport_code,
            recipient_role='staff',
            recipient_username=target_username,
            sender_username=user.get('username'),
            sender_name=user.get('name', f"Department Head {airport_code}"),
            notif_type='revisi',
            title='Catatan Koreksi DH',
            message=f'Pesan DH: "{notes}"',
            report_id=report_id,
            tanggal=tgl,
            notes=notes
        )

        return jsonify({
            "success": True,
            "message": f"Catatan koreksi berhasil disimpan untuk {target_name}. Status laporan diubah menjadi 'Perlu Revisi'.",
            "pic_phone": pic_phone,
            "staff_message": staff_message
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.route('/api/edit-report', methods=['POST'])
def api_edit_report():
    data = request.json or {}
    report_id = data.get('report_id')
    form_data = data.get('form_data') or {}
    auto_approve = bool(data.get('auto_approve', False))

    if not report_id:
        return jsonify({"success": False, "error": "ID Laporan diperlukan"}), 400
    if not form_data:
        return jsonify({"success": False, "error": "Data formulir koreksi tidak boleh kosong"}), 400

    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    dh_name = user.get('name', f"Department Head {airport_code}")
    dh_username = user.get('username')

    try:
        old_rep = get_staging_report_by_id(airport_code, report_id)
        if not old_rep:
            return jsonify({"success": False, "error": f"Laporan {report_id} tidak ditemukan di staging."}), 404

        target_username = old_rep.get('submitted_by_username')
        tgl = form_data.get('TANGGAL') or old_rep.get('tanggal', '')

        # 1. Update data di staging
        res = update_staging_report_by_dh(
            airport_code=airport_code,
            report_id=report_id,
            updated_form_data=form_data,
            dh_name=dh_name,
            dh_username=dh_username
        )

        from app.services.notification_service import create_notification
        # Notifikasi ke staf bahwa laporannya dikoreksi mandiri oleh DH
        create_notification(
            airport_code=airport_code,
            recipient_role='staff',
            recipient_username=target_username,
            sender_username=dh_username,
            sender_name=dh_name,
            notif_type='pending',
            title='Laporan Dikoreksi oleh DH',
            message=f'Department Head ({dh_name}) telah melakukan koreksi mandiri pada data laporan tanggal {tgl}.',
            report_id=report_id,
            tanggal=tgl
        )

        # Invalidate calendar cache
        try:
            from app.services.gsheets_service import invalidate_calendar_cache
            invalidate_calendar_cache(airport_code)
        except Exception:
            pass

        # 2. Jika opsi 'Simpan & Langsung Setujui' dipilih
        if auto_approve:
            approve_res = gm_approve_report(airport_code, report_id)
            final_form_data = approve_res.get('form_data', {})
            
            # Notifikasi ke staf: Disetujui
            create_notification(
                airport_code=airport_code,
                recipient_role='staff',
                recipient_username=target_username,
                sender_username=dh_username,
                sender_name=dh_name,
                notif_type='approved',
                title='Laporan Dikoreksi & Disetujui DH',
                message=f'Laporan tanggal {tgl} telah disesuaikan langsung dan disetujui oleh Department Head serta dipindahkan ke Spreadsheet Produksi.',
                report_id=report_id,
                tanggal=tgl
            )
            # Notifikasi riwayat DH
            create_notification(
                airport_code=airport_code,
                recipient_role='dh',
                sender_username=dh_username,
                sender_name=dh_name,
                notif_type='approved',
                title='Laporan Dikoreksi & Disetujui',
                message=f'Laporan tanggal {tgl} (ID: {report_id}) berhasil dikoreksi mandiri dan disetujui ke Spreadsheet Produksi.',
                report_id=report_id,
                tanggal=tgl
            )

            # Generate format pesan WhatsApp ke Admin Regional II
            admin_conf = get_admin_config()
            admin_phone = admin_conf.get('admin_phone', '')
            wa_report = generate_wa_message(final_form_data, airport_code)

            full_admin_message = wa_report

            return jsonify({
                "success": True,
                "action": "approved",
                "message": "Koreksi mandiri berhasil disimpan dan laporan langsung disetujui ke Spreadsheet Produksi!",
                "admin_phone": admin_phone,
                "admin_message": full_admin_message
            })

        # Jika hanya Simpan Koreksi (tetap di staging)
        updated_rep = get_staging_report_by_id(airport_code, report_id)
        return jsonify({
            "success": True,
            "action": "saved",
            "message": "Koreksi mandiri berhasil disimpan. Data laporan di staging telah diperbarui.",
            "report": updated_rep
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
        # Ambil info pengirim dari staging sebelum data dihapus
        pre_report = get_staging_report_by_id(airport_code, report_id)
        target_username = pre_report.get('submitted_by_username') if pre_report else None
        target_name = pre_report.get('submitted_by') if pre_report else f"Petugas {airport_code}"

        res = gm_approve_report(airport_code, report_id)
        form_data = res.get('form_data', {})
        tgl = form_data.get('TANGGAL', '') or form_data.get('TANGGAL_LAPORAN', '')
        
        # Simpan notifikasi ke Petugas bahwa laporan disetujui DH (khusus akun pengirim)
        from app.services.notification_service import create_notification
        create_notification(
            airport_code=airport_code,
            recipient_role='staff',
            recipient_username=target_username,
            sender_username=user.get('username'),
            sender_name=user.get('name', f"Department Head {airport_code}"),
            notif_type='approved',
            title='Laporan Disetujui DH',
            message=f'Laporan Harian Airside tanggal {tgl} telah diverifikasi dan disetujui oleh Department Head serta dipindahkan ke Spreadsheet Produksi.',
            report_id=report_id,
            tanggal=tgl
        )
        # Notifikasi untuk riwayat DH juga
        create_notification(
            airport_code=airport_code,
            recipient_role='dh',
            sender_username=user.get('username'),
            sender_name=user.get('name', f"Department Head {airport_code}"),
            notif_type='approved',
            title='Laporan Berhasil Disetujui',
            message=f'Laporan tanggal {tgl} (ID: {report_id}) dari {target_name} telah berhasil disetujui & disinkronkan ke Spreadsheet Produksi.',
            report_id=report_id,
            tanggal=tgl
        )
        
        # Generate format pesan laporan resmi untuk WhatsApp ke Admin Regional II
        admin_conf = get_admin_config()
        admin_phone = admin_conf.get('admin_phone', '')
        wa_report = generate_wa_message(form_data, airport_code)

        full_admin_message = wa_report

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
    from app.models.config_store import get_active_month
    active_m = get_active_month(airport_code)
    notifs = get_notifications(airport_code, role='dh', active_month=active_m)
    unread_count = sum(1 for n in notifs if not n.get('is_read'))
    return jsonify({
        "success": True,
        "notifications": notifs,
        "unread_count": unread_count,
        "active_month": active_m
    })

@bp.route('/api/notifications/mark-read', methods=['POST'])
def api_notifications_mark_read():
    data = request.json or {}
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    from app.services.notification_service import mark_notification_as_read, mark_all_as_read, set_notification_read_status
    
    if data.get('mark_all'):
        mark_all_as_read(airport_code, role='dh')
    elif data.get('notif_id'):
        is_read = data.get('is_read', True)
        set_notification_read_status(data.get('notif_id'), is_read=is_read)
    return jsonify({"success": True})

@bp.route('/api/notifications/clear', methods=['POST'])
def api_notifications_clear():
    data = request.json or {}
    user = USERS.get(session['user_id'])
    airport_code = user.get('airport', 'LOP')
    from app.services.notification_service import clear_notifications, delete_single_notification
    from app.models.config_store import get_active_month
    active_m = get_active_month(airport_code)

    notif_id = data.get('notif_id')
    if notif_id:
        delete_single_notification(notif_id)
    else:
        clear_notifications(airport_code, role='dh', active_month=active_m)

    return jsonify({"success": True, "message": "Notifikasi berhasil dibersihkan."})
