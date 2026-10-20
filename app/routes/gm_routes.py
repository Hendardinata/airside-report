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

    return render_template(
        'gm_dashboard.html',
        current_user=user,
        airport_code=airport_code,
        airport_info=airport_info,
        config=config,
        reports=reports,
        pending_count=pending_count,
        revisi_count=revisi_count,
        schema=schema
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
        
        # Generate format pesan laporan resmi untuk WhatsApp ke Admin Regional II
        admin_conf = get_admin_config()
        admin_phone = admin_conf.get('admin_phone', '')
        wa_report = generate_wa_message(form_data, airport_code)

        approval_header = (
            f"*[VERIFIKASI GM SELESAI - LAPORAN DISETUJUI]*\n"
            f"Laporan Harian Fasilitas Sisi Udara Cabang *{airport_code}* telah diverifikasi dan disetujui oleh General Manager.\n\n"
        )
        full_admin_message = approval_header + wa_report

        return jsonify({
            "success": True,
            "message": "Laporan berhasil disetujui, dimasukkan ke Spreadsheet Produksi, dan dihapus dari Staging.",
            "admin_phone": admin_phone,
            "admin_message": full_admin_message
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
