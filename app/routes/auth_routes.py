from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.airport_profiles import USERS, verify_user_password
import time

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
        if user and user.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user:
            return redirect(url_for('staff.dashboard'))
    return render_template('login.html')

@bp.route('/login', methods=['POST'])
def login():
    username = (request.form.get('username') or '').strip().lower()
    password = request.form.get('password') or ''
    selected_role = (request.form.get('role') or '').strip()

    if not username or not password:
        flash("Username dan password wajib diisi.", "danger")
        return redirect(url_for('auth.index'))

    # Cek apakah akun ini (hanya akun yang bersangkutan) sedang ditangguhkan
    is_locked, remaining_min = check_user_lockout(username)
    if is_locked:
        flash(f"Akun '{username.upper()}' ditangguhkan sementara karena 5 kali percobaan login gagal. Silakan coba lagi dalam {remaining_min} menit.", "danger")
        return redirect(url_for('auth.index'))

    user = USERS.get(username)

    # Verifikasi Password menggunakan hash aman
    if user and verify_user_password(user, password):
        # Validasi role jika dipilih
        if selected_role and user.get('role') != selected_role:
            record_failed_attempt(username)
            sisa = get_remaining_attempts(username)
            if sisa > 0:
                flash(f"Peran (Role) yang dipilih tidak sesuai dengan akun '{username.upper()}'. Sisa percobaan: {sisa} kali.", "danger")
            else:
                flash(f"Akun '{username.upper()}' kini ditangguhkan sementara selama 15 menit.", "danger")
            return redirect(url_for('auth.index'))

        # Validasi kecocokan Cabang Bandara untuk akun petugas
        selected_airport = (request.form.get('airportCode') or '').strip().upper()
        if user.get('role') == 'staff' and selected_airport:
            user_airport = (user.get('airport') or '').upper()
            if user_airport != selected_airport:
                record_failed_attempt(username)
                sisa = get_remaining_attempts(username)
                flash(f"Login ditolak: Akun '{username.upper()}' terdaftar untuk cabang {user_airport}, tidak sesuai dengan cabang yang dipilih ({selected_airport}). Silakan pilih cabang {user_airport}.", "danger")
                return redirect(url_for('auth.index'))

        # Bersihkan record kegagalan setelah login berhasil
        clear_failed_attempts(username)

        # Mencegah Session Fixation: bersihkan session lama sebelum membuat baru
        session.clear()
        session['user_id'] = username
        session.permanent = True

        if user.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
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

@bp.route('/api/auth/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
