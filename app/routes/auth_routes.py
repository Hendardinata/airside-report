from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models.airport_profiles import USERS, verify_user_password, update_user_profile
import time
import secrets
import os

bp = Blueprint('auth', __name__)

# In-memory store untuk proteksi brute force per akun pengguna
# Format: { 'username': [timestamp1, timestamp2, ...] }
FAILED_LOGIN_ATTEMPTS = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 menit

def check_user_lockout(username):
    """
    Memeriksa apakah akun pengguna tertentu sedang dalam masa penangguhan (lockout).
    Mengembalikan (is_locked, remaining_minutes)
    """
    if not username:
        return False, 0
    now = time.time()
    attempts = FAILED_LOGIN_ATTEMPTS.get(username, [])
    recent_attempts = [t for t in attempts if now - t < LOCKOUT_DURATION_SECONDS]
    FAILED_LOGIN_ATTEMPTS[username] = recent_attempts

    if len(recent_attempts) >= MAX_FAILED_ATTEMPTS:
        oldest_relevant = min(recent_attempts)
        remaining_sec = LOCKOUT_DURATION_SECONDS - (now - oldest_relevant)
        remaining_min = max(1, int(remaining_sec // 60) + 1)
        return True, remaining_min
    return False, 0

def record_failed_attempt(username):
    if not username:
        return
    now = time.time()
    if username not in FAILED_LOGIN_ATTEMPTS:
        FAILED_LOGIN_ATTEMPTS[username] = []
    FAILED_LOGIN_ATTEMPTS[username].append(now)

def get_remaining_attempts(username):
    now = time.time()
    attempts = FAILED_LOGIN_ATTEMPTS.get(username, [])
    recent = [t for t in attempts if now - t < LOCKOUT_DURATION_SECONDS]
    return max(0, MAX_FAILED_ATTEMPTS - len(recent))

def clear_failed_attempts(username):
    FAILED_LOGIN_ATTEMPTS.pop(username, None)

@bp.route('/', methods=['GET'])
def index():
    if 'user_id' in session:
        user = USERS.get(session['user_id'])
        if user and not user.get('is_active', True):
            session.clear()
            flash("Akun Anda saat ini dinonaktifkan. Silakan hubungi Administrator.", "warning")
            return render_template('login.html')

        if user and user.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user and user.get('role') in ('dh', 'gm'):
            return redirect(url_for('gm.dashboard'))
        elif user:
            return redirect(url_for('staff.dashboard'))
    return render_template('login.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('auth.index'))

    username = (request.form.get('username') or '').strip().lower()
    password = request.form.get('password') or ''
    selected_role = (request.form.get('role') or '').strip().lower()

    if not username or not password:
        flash("Username dan password wajib diisi.", "danger")
        return redirect(url_for('auth.index'))

    # Cek apakah akun ini (hanya akun yang bersangkutan) sedang ditangguhkan
    is_locked, remaining_min = check_user_lockout(username)
    if is_locked:
        flash(f"Akun '{username.upper()}' ditangguhkan sementara karena 5 kali percobaan login gagal. Silakan coba lagi dalam {remaining_min} menit.", "danger")
        return redirect(url_for('auth.index'))

    # Ambil pengguna langsung dari Database Utama (SQLite airside.db)
    user = USERS.get(username)

    if not user:
        record_failed_attempt(username)
        sisa = get_remaining_attempts(username)
        if sisa > 0:
            flash(f"Nama pengguna atau kata sandi tidak valid. Sisa percobaan: {sisa} kali.", "danger")
        else:
            flash(f"Akun '{username.upper()}' kini ditangguhkan sementara selama 15 menit.", "danger")
        return redirect(url_for('auth.index'))

    # Validasi apakah akun sedang dinonaktifkan oleh Administrator
    if not user.get('is_active', True):
        flash(f"Login ditolak: Akun '{username.upper()}' saat ini berstatus NONAKTIF (pindah tugas atau berhenti). Silakan hubungi Administrator Regional II.", "danger")
        return redirect(url_for('auth.index'))

    # Verifikasi Password menggunakan hash aman dari database
    if verify_user_password(user, password):
        # Validasi role jika dipilih
        if selected_role:
            sel_norm = 'dh' if selected_role in ('gm', 'dh') else selected_role
            user_norm = 'dh' if user.get('role') in ('gm', 'dh') else user.get('role')
            if user_norm != sel_norm:
                record_failed_attempt(username)
                sisa = get_remaining_attempts(username)
                if sisa > 0:
                    flash(f"Peran (Role) yang dipilih tidak sesuai dengan akun '{username.upper()}'. Sisa percobaan: {sisa} kali.", "danger")
                else:
                    flash(f"Akun '{username.upper()}' kini ditangguhkan sementara selama 15 menit.", "danger")
                return redirect(url_for('auth.index'))

        # Validasi kecocokan Cabang Bandara untuk akun petugas dan Department Head
        selected_airport = (request.form.get('airportCode') or '').strip().upper()
        if user.get('role') in ('staff', 'dh', 'gm') and selected_airport:
            user_airport = (user.get('airport') or '').upper()
            if user_airport != selected_airport:
                record_failed_attempt(username)
                sisa = get_remaining_attempts(username)
                role_label = "Department Head" if user.get('role') in ('dh', 'gm') else "Petugas"
                flash(f"Login ditolak: Akun {role_label} '{username.upper()}' terdaftar untuk cabang {user_airport}, tidak sesuai dengan cabang yang dipilih ({selected_airport}). Silakan pilih cabang {user_airport}.", "danger")
                return redirect(url_for('auth.index'))

        # Bersihkan record kegagalan setelah login berhasil
        clear_failed_attempts(username)

        # Mencegah Session Fixation: bersihkan session lama sebelum membuat baru
        session.clear()
        session['user_id'] = username
        session.permanent = True
        session['_csrf_token'] = secrets.token_hex(32)

        if user.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.get('role') in ('dh', 'gm'):
            return redirect(url_for('gm.dashboard'))
        else:
            return redirect(url_for('staff.dashboard'))

    # Catat kegagalan login jika password salah
    record_failed_attempt(username)
    sisa = get_remaining_attempts(username)

    if sisa > 0:
        flash(f"Password salah untuk akun '{username.upper()}'. Sisa percobaan: {sisa} kali sebelum akun ditangguhkan.", "danger")
    else:
        flash(f"Akun '{username.upper()}' telah mencapai batas maksimal kesalahan dan ditangguhkan sementara selama 15 menit.", "danger")

    return redirect(url_for('auth.index'))

@bp.route('/logout', methods=['GET', 'POST'])
@bp.route('/api/auth/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    session['_csrf_token'] = secrets.token_hex(32)
    return redirect(url_for('auth.index'))

@bp.route('/api/user/profile', methods=['GET', 'POST'])
def api_user_profile():
    """
    Endpoint pembaruan profil mandiri:
    - Staff: bisa ganti foto profil dan nama Pengguna (name), nama akun (username) terkunci.
    - DH: HANYA bisa ganti foto profil saja.
    - Admin: bisa ganti foto profil dan nama pengguna dia sendiri.
    """
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Sesi Anda telah berakhir. Silakan login kembali."}), 401
    
    current_username = session['user_id']
    user = USERS.get(current_username)
    if not user:
        return jsonify({"success": False, "error": "Pengguna tidak ditemukan."}), 404

    if request.method == 'GET':
        return jsonify({
            "success": True,
            "user": {
                "username": user['username'],
                "name": user['name'],
                "role": user['role'],
                "airport": user.get('airport') or '',
                "avatar": user.get('avatar') or ''
            }
        })

    # POST: Update profile
    role = user.get('role', 'staff')
    
    avatar_url = None
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename:
            from app.services.photo_service import UPLOADS_ROOT
            allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
            if ext not in allowed_extensions:
                return jsonify({"success": False, "error": "Format foto tidak didukung. Harap gunakan format PNG, JPG, JPEG, atau WEBP."}), 400
            
            avatars_dir = os.path.join(UPLOADS_ROOT, 'avatars')
            os.makedirs(avatars_dir, exist_ok=True)
            
            safe_filename = f"avatar_{current_username}_{int(time.time())}.{ext}"
            file_dest = os.path.join(avatars_dir, safe_filename)
            file.save(file_dest)
            avatar_url = f"/static/uploads/avatars/{safe_filename}"
            
    if request.form.get('remove_avatar') == 'true':
        avatar_url = ''

    # Role specific update permissions:
    # 1. Staff: can change foto and nama Pengguna saja, NOT nama akun (username)
    # 2. DH: ONLY change foto profile saja
    # 3. Admin: can change foto profile and nama pengguna dia sendiri
    new_name = None
    if role in ('staff', 'admin'):
        req_name = request.form.get('name')
        if req_name is not None and req_name.strip():
            new_name = req_name.strip()

    # Kata Sandi (Password) Update
    new_password = (request.form.get('new_password') or request.form.get('password') or '').strip()
    if new_password:
        current_password = (request.form.get('current_password') or '').strip()
        confirm_password = (request.form.get('confirm_password') or '').strip()
        if not current_password:
            return jsonify({"success": False, "error": "Kata sandi saat ini wajib diisi untuk verifikasi keamanan."}), 400
        if not verify_user_password(user, current_password):
            return jsonify({"success": False, "error": "Kata sandi saat ini yang Anda masukkan tidak sesuai."}), 400
        if confirm_password and new_password != confirm_password:
            return jsonify({"success": False, "error": "Konfirmasi kata sandi baru tidak cocok."}), 400
        if len(new_password) < 3:
            return jsonify({"success": False, "error": "Kata sandi baru minimal 3 karakter."}), 400

    try:
        updated_user = update_user_profile(
            username=current_username,
            name=new_name,
            avatar=avatar_url,
            password=new_password if new_password else None
        )
        return jsonify({
            "success": True,
            "message": "Profil berhasil diperbarui.",
            "user": {
                "username": updated_user['username'],
                "name": updated_user['name'],
                "role": updated_user['role'],
                "airport": updated_user.get('airport') or '',
                "avatar": updated_user.get('avatar') or ''
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


def _format_tanggal_indo(d_str):
    if not d_str:
        return "-"
    try:
        parts = str(d_str)[:10].split("-")
        if len(parts) == 3:
            months = [
                "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"
            ]
            d = int(parts[2])
            m = months[int(parts[1]) - 1]
            y = parts[0]
            return f"{d} {m} {y}"
    except Exception:
        pass
    return str(d_str)


@bp.route('/dokumentasi', methods=['GET'])
@bp.route('/dokumentasi/', methods=['GET'])
@bp.route('/dokumentasi/<date_str>', methods=['GET'])
@bp.route('/dokumentasi/<date_str>/<airport_code>', methods=['GET'])
@bp.route('/dok/<date_str>', methods=['GET'])
@bp.route('/dok/<date_str>/<airport_code>', methods=['GET'])
@bp.route('/d/<date_str>', methods=['GET'])
@bp.route('/d/<date_str>/<airport_code>', methods=['GET'])
def public_dokumentasi(date_str=None, airport_code=None):
    """
    Halaman korporat untuk melihat, memfilter per cabang, dan mengunduh massal (ZIP)
    dokumentasi foto lapangan hasil inspeksi fasilitas sisi udara.
    """
    import re
    from app.services.photo_service import (
        get_all_airports_photos_by_date,
        get_latest_documentation_date
    )
    from app.models.airport_profiles import AIRPORTS

    raw_date = date_str or request.args.get('date') or request.args.get('tanggal')
    clean_date = str(raw_date or '').strip()[:10]
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', clean_date):
        clean_date = get_latest_documentation_date()

    req_branch = airport_code or request.args.get('branch') or request.args.get('airport') or 'ALL'
    req_branch = str(req_branch).strip().upper()
    if req_branch in ('', 'ALL', 'SEMUA', 'SEMUA_CABANG'):
        initial_branch = 'ALL'
    else:
        initial_branch = req_branch

    photos_by_airport = get_all_airports_photos_by_date(clean_date)
    if initial_branch != 'ALL' and initial_branch not in photos_by_airport:
        initial_branch = 'ALL'

    branch_list = list(photos_by_airport.keys())
    total_photos = sum(len(v) for v in photos_by_airport.values())
    active_branches_count = sum(1 for v in photos_by_airport.values() if len(v) > 0)

    airport_names = {
        "DPS": "Bandara Internasional I Gusti Ngurah Rai",
        "LOP": "Bandara Internasional Zainuddin Abdul Madjid",
        "BWX": "Bandara Internasional Banyuwangi",
        "KOE": "Bandara El Tari Kupang"
    }
    for code in branch_list:
        if code not in airport_names:
            info = AIRPORTS.get(code, {})
            airport_names[code] = info.get('name') or f"Bandara Cabang {code}"

    og_image_url = url_for('auth.public_dokumentasi_preview', date_str=clean_date, _external=True)

    return render_template(
        'public_dokumentasi.html',
        date_str=clean_date,
        formatted_date=_format_tanggal_indo(clean_date),
        photos_by_airport=photos_by_airport,
        branch_list=branch_list,
        initial_branch=initial_branch,
        total_photos=total_photos,
        active_branches_count=active_branches_count,
        airport_names=airport_names,
        og_image_url=og_image_url
    )


@bp.route('/api/documentation/download', methods=['GET'])
@bp.route('/dokumentasi/download', methods=['GET'])
def download_documentation_zip():
    """
    Endpoint Bulk Download ZIP dokumentasi foto lapangan berdasarkan tanggal dan filter cabang:
    - GET /api/documentation/download?date=2026-10-15&branch=all
      -> Dokumentasi_Airside_2026-10-15_Semua_Cabang.zip
    - GET /api/documentation/download?date=2026-10-15&branch=LOP
      -> Dokumentasi_Airside_2026-10-15_LOP.zip
    """
    from flask import send_file
    from app.services.photo_service import build_documentation_zip

    # Jika terdapat sesi login aktif, pastikan akun masih berstatus aktif
    if 'user_id' in session:
        user = USERS.get(session.get('user_id'))
        if user and not user.get('is_active', True):
            return jsonify({
                "success": False,
                "status": "error",
                "message": "Akses ditolak: Akun pengguna saat ini berstatus nonaktif."
            }), 403

    date_param = (request.args.get('date') or request.args.get('tanggal') or '').strip()[:10]
    branch_param = (request.args.get('branch') or request.args.get('airport') or request.args.get('cabang') or 'ALL').strip()

    if not date_param:
        return jsonify({
            "success": False,
            "status": "error",
            "message": "Parameter tanggal dokumentasi (date) wajib disertakan."
        }), 400

    try:
        spool_file, zip_filename, total_files, included_branches = build_documentation_zip(
            tanggal=date_param,
            branch=branch_param
        )
    except ValueError as val_err:
        return jsonify({
            "success": False,
            "status": "error",
            "message": str(val_err)
        }), 400
    except Exception as err:
        return jsonify({
            "success": False,
            "status": "error",
            "message": f"Gagal menyiapkan arsip ZIP dokumentasi: {str(err)}"
        }), 500

    if not spool_file or total_files == 0:
        return jsonify({
            "success": False,
            "status": "empty",
            "message": "Tidak ada dokumentasi foto yang dapat diunduh untuk pilihan tanggal dan cabang ini."
        }), 404

    response = send_file(
        spool_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_filename
    )
    response.headers['X-Photo-Count'] = str(total_files)
    response.headers['X-Included-Branches'] = ",".join(included_branches)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response


@bp.route('/dokumentasi/<date_str>/preview.jpg', methods=['GET'])
def public_dokumentasi_preview(date_str):
    """
    Endpoint gambar untuk OpenGraph Link Preview otomatis di WhatsApp (status 200 langsung).
    """
    from flask import Response, send_from_directory, send_file
    from app.services.photo_service import generate_og_preview_jpeg, get_all_airports_photos_by_date, UPLOADS_ROOT
    import os

    clean_date = str(date_str or '').strip()[:10]
    jpeg_bytes = generate_og_preview_jpeg(clean_date)
    if jpeg_bytes:
        return Response(jpeg_bytes, mimetype='image/jpeg')

    # Fallback langsung kirim file gambar pertama dengan status 200 OK agar crawler WhatsApp merender thumbnail
    grouped = get_all_airports_photos_by_date(clean_date)
    for code in ('DPS', 'LOP', 'KOE', 'BWX'):
        if grouped.get(code):
            first_url = grouped[code][0]['url']
            rel_path = first_url.replace('/static/uploads/', '').replace('/', os.sep)
            abs_path = os.path.join(UPLOADS_ROOT, rel_path)
            if os.path.exists(abs_path):
                return send_file(abs_path, mimetype='image/webp')

    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'img')
    return send_from_directory(static_dir, 'logo-kawung.png')

