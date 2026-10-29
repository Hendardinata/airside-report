from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.airport_profiles import USERS, verify_user_password
import time
import secrets

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

    user = USERS.get(username)

    # Validasi apakah akun sedang dinonaktifkan oleh Administrator
    if user and not user.get('is_active', True):
        flash(f"Login ditolak: Akun '{username.upper()}' saat ini berstatus NONAKTIF (pindah tugas atau berhenti). Silakan hubungi Administrator Regional II.", "danger")
        return redirect(url_for('auth.index'))

    # Verifikasi Password menggunakan hash aman
    if user and verify_user_password(user, password):
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

    # Catat kegagalan login khusus untuk username ini
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


@bp.route('/dokumentasi/<date_str>', methods=['GET'])
@bp.route('/dokumentasi/<date_str>/<airport_code>', methods=['GET'])
def public_dokumentasi(date_str, airport_code=None):
    """
    Halaman publik (tanpa login) untuk melihat & mencetak PDF dokumentasi foto lapangan
    yang dikirimkan melalui tautan di laporan WhatsApp ke Deputy / Pimpinan.
    """
    from app.services.photo_service import get_all_airports_photos_by_date, get_photos_by_date

    clean_date = str(date_str or '').strip()[:10]
    if airport_code and airport_code.upper() in ('DPS', 'LOP', 'BWX', 'KOE'):
        code = airport_code.upper()
        photos_by_airport = {c: ([] if c != code else get_photos_by_date(code, clean_date)) for c in ('DPS', 'LOP', 'BWX', 'KOE')}
    else:
        photos_by_airport = get_all_airports_photos_by_date(clean_date)

    total_photos = sum(len(v) for v in photos_by_airport.values())
    airport_names = {
        "DPS": "Bandara Internasional I Gusti Ngurah Rai — Bali",
        "LOP": "Bandara Internasional Zainuddin Abdul Madjid — Lombok",
        "BWX": "Bandara Internasional Banyuwangi",
        "KOE": "Bandara El Tari — Kupang"
    }

    og_image_url = url_for('auth.public_dokumentasi_preview', date_str=clean_date, _external=True)

    return render_template(
        'public_dokumentasi.html',
        date_str=clean_date,
        formatted_date=_format_tanggal_indo(clean_date),
        photos_by_airport=photos_by_airport,
        total_photos=total_photos,
        airport_names=airport_names,
        og_image_url=og_image_url
    )


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
    for code in ('DPS', 'LOP', 'BWX', 'KOE'):
        if grouped.get(code):
            first_url = grouped[code][0]['url']
            rel_path = first_url.replace('/static/uploads/', '').replace('/', os.sep)
            abs_path = os.path.join(UPLOADS_ROOT, rel_path)
            if os.path.exists(abs_path):
                return send_file(abs_path, mimetype='image/webp')

    static_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'img')
    return send_from_directory(static_dir, 'logo-kawung.png')

