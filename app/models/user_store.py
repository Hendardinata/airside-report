from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import hmac
from app.models.db import get_db

# Akun bawaan (Default Seed Users)
DEFAULT_USERS = {
    'admin': {
        'username': 'admin',
        'name': 'Admin Regional',
        'role': 'admin',
        'airport': None,
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'lop': {
        'username': 'lop',
        'name': 'Petugas LOP',
        'role': 'staff',
        'airport': 'LOP',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'dps': {
        'username': 'dps',
        'name': 'Petugas DPS',
        'role': 'staff',
        'airport': 'DPS',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'bwx': {
        'username': 'bwx',
        'name': 'Petugas BWX',
        'role': 'staff',
        'airport': 'BWX',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'koe': {
        'username': 'koe',
        'name': 'Petugas KOE',
        'role': 'staff',
        'airport': 'KOE',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    # Akun Department Head (DH)
    'dh_lop': {
        'username': 'dh_lop',
        'name': 'Department Head LOP',
        'role': 'dh',
        'airport': 'LOP',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'dh_dps': {
        'username': 'dh_dps',
        'name': 'Department Head DPS',
        'role': 'dh',
        'airport': 'DPS',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'dh_bwx': {
        'username': 'dh_bwx',
        'name': 'Department Head BWX',
        'role': 'dh',
        'airport': 'BWX',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'dh_koe': {
        'username': 'dh_koe',
        'name': 'Department Head KOE',
        'role': 'dh',
        'airport': 'KOE',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_system': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    # Kompatibilitas mundur untuk username login lama (gm_*)
    'gm_lop': {
        'username': 'gm_lop',
        'name': 'Department Head LOP',
        'role': 'dh',
        'airport': 'LOP',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_legacy_alias': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'gm_dps': {
        'username': 'gm_dps',
        'name': 'Department Head DPS',
        'role': 'dh',
        'airport': 'DPS',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_legacy_alias': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'gm_bwx': {
        'username': 'gm_bwx',
        'name': 'Department Head BWX',
        'role': 'dh',
        'airport': 'BWX',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_legacy_alias': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    },
    'gm_koe': {
        'username': 'gm_koe',
        'name': 'Department Head KOE',
        'role': 'dh',
        'airport': 'KOE',
        'password_hash': generate_password_hash('123'),
        'is_active': True,
        'is_legacy_alias': True,
        'created_at': '2026-10-01 00:00:00',
        'updated_at': '2026-10-01 00:00:00'
    }
}

def _row_to_user_dict(row):
    if not row:
        return None
    return {
        'username': row['username'],
        'name': row['name'],
        'role': row['role'],
        'airport': row['airport'],
        'password_hash': row['password_hash'],
        'is_active': bool(row['is_active']),
        'is_system': bool(row['is_system']),
        'is_legacy_alias': bool(row['is_legacy_alias']),
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }

def load_users():
    """
    Memuat seluruh data pengguna dari database SQLite.
    Mengembalikan dict dengan key berupa username huruf kecil.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users;")
        rows = cursor.fetchall()
        result = {}
        for r in rows:
            u = _row_to_user_dict(r)
            result[u['username']] = u
        return result

def save_users(users_dict):
    """
    Menyimpan atau memperbarui data dictionary pengguna ke database SQLite.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        for uname, u in users_dict.items():
            cursor.execute("""
            INSERT OR REPLACE INTO users (
                username, name, role, airport, password_hash, is_active, is_system, is_legacy_alias, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                uname.lower(),
                u.get('name', ''),
                u.get('role', 'staff'),
                u.get('airport'),
                u.get('password_hash', ''),
                1 if u.get('is_active', True) else 0,
                1 if u.get('is_system', False) else 0,
                1 if u.get('is_legacy_alias', False) else 0,
                u.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                u.get('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            ))

def get_user(username):
    """Mengambil data pengguna berdasarkan username (case-insensitive)."""
    if not username:
        return None
    clean_username = str(username).strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ?;", (clean_username,))
        row = cursor.fetchone()
        return _row_to_user_dict(row)

def get_all_users(include_legacy_alias=False):
    """
    Mengambil daftar seluruh pengguna untuk ditampilkan di Admin Dashboard.
    Secara default menyembunyikan alias backward-compatibility gm_*.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if include_legacy_alias:
            cursor.execute("SELECT * FROM users;")
        else:
            cursor.execute("SELECT * FROM users WHERE is_legacy_alias = 0;")
        rows = cursor.fetchall()
        user_list = [_row_to_user_dict(r) for r in rows]

    def sort_key(item):
        role_prio = {'admin': 0, 'dh': 1, 'staff': 2}.get(item.get('role'), 9)
        return (role_prio, item.get('airport') or '', item.get('name') or '')
    user_list.sort(key=sort_key)
    return user_list

def add_user(username, name, role, airport, password, is_active=True):
    """
    Menambahkan pengguna baru ke SQLite.
    Cakupan: role 'staff' atau 'dh', penempatan airport tertentu.
    """
    clean_username = (username or '').strip().lower()
    clean_name = (name or '').strip()
    clean_role = (role or '').strip().lower()
    clean_airport = (airport or '').strip().upper() if airport else None
    clean_password = (password or '').strip()

    if not clean_username:
        raise ValueError("Username tidak boleh kosong.")
    if len(clean_username) < 3:
        raise ValueError("Username minimal 3 karakter.")
    if not clean_username.replace('_', '').isalnum():
        raise ValueError("Username hanya boleh berisi huruf, angka, dan underscore (_).")
    if not clean_name:
        raise ValueError("Nama lengkap pengguna wajib diisi.")
    if clean_role not in ('staff', 'dh'):
        raise ValueError("Peran (Role) pengguna hanya boleh 'staff' atau 'dh' (Department Head).")
    if clean_role in ('staff', 'dh') and not clean_airport:
        raise ValueError("Cabang bandara wajib dipilih untuk petugas dan Department Head.")
    if not clean_password:
        clean_password = '123' # Default fallback password

    existing = get_user(clean_username)
    if existing:
        raise ValueError(f"Username '{clean_username}' sudah digunakan oleh pengguna lain. Silakan pilih username lain.")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_user = {
        'username': clean_username,
        'name': clean_name,
        'role': clean_role,
        'airport': clean_airport,
        'password_hash': generate_password_hash(clean_password),
        'is_active': bool(is_active),
        'is_system': False,
        'is_legacy_alias': False,
        'created_at': now_str,
        'updated_at': now_str
    }

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO users (
            username, name, role, airport, password_hash, is_active, is_system, is_legacy_alias, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            clean_username,
            clean_name,
            clean_role,
            clean_airport,
            new_user['password_hash'],
            1 if is_active else 0,
            0,
            0,
            now_str,
            now_str
        ))
    return new_user

def update_user_status(username, is_active):
    """
    Mengaktifkan atau menonaktifkan akun pengguna di SQLite.
    Superadmin ('admin') tidak bisa dinonaktifkan.
    """
    clean_username = (username or '').strip().lower()
    if clean_username == 'admin':
        raise ValueError("Akun Administrator Utama tidak dapat dinonaktifkan.")

    existing = get_user(clean_username)
    if not existing:
        raise ValueError(f"Pengguna '{clean_username}' tidak ditemukan.")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users SET is_active = ?, updated_at = ? WHERE username = ?;
        """, (1 if is_active else 0, now_str, clean_username))

    existing['is_active'] = bool(is_active)
    existing['updated_at'] = now_str
    return existing

def update_user(username, name=None, role=None, airport=None, password=None, is_active=None):
    """
    Memperbarui profil pengguna (nama, role, cabang penempatan, kata sandi, status aktif).
    """
    clean_username = (username or '').strip().lower()
    existing = get_user(clean_username)
    if not existing:
        raise ValueError(f"Pengguna '{clean_username}' tidak ditemukan.")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    new_name = existing['name']
    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Nama lengkap tidak boleh kosong.")
        new_name = clean_name

    new_role = existing['role']
    if role is not None and clean_username != 'admin':
        clean_role = role.strip().lower()
        if clean_role not in ('staff', 'dh', 'admin'):
            raise ValueError("Peran hanya boleh 'staff', 'dh', atau 'admin'.")
        new_role = clean_role

    new_airport = existing['airport']
    if airport is not None and clean_username != 'admin':
        clean_airport = airport.strip().upper()
        if not clean_airport:
            raise ValueError("Cabang bandara wajib dipilih.")
        new_airport = clean_airport

    new_active = existing['is_active']
    if is_active is not None and clean_username != 'admin':
        new_active = bool(is_active)

    new_hash = existing['password_hash']
    if password is not None and str(password).strip():
        new_hash = generate_password_hash(str(password).strip())

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users 
        SET name = ?, role = ?, airport = ?, password_hash = ?, is_active = ?, updated_at = ?
        WHERE username = ?;
        """, (
            new_name,
            new_role,
            new_airport,
            new_hash,
            1 if new_active else 0,
            now_str,
            clean_username
        ))

    existing['name'] = new_name
    existing['role'] = new_role
    existing['airport'] = new_airport
    existing['password_hash'] = new_hash
    existing['is_active'] = new_active
    existing['updated_at'] = now_str
    return existing

def delete_user(username):
    """
    Menghapus akun pengguna dari SQLite (hanya untuk akun non-system atau non-admin).
    """
    clean_username = (username or '').strip().lower()
    if clean_username == 'admin':
        raise ValueError("Akun Administrator Utama tidak dapat dihapus.")

    existing = get_user(clean_username)
    if not existing:
        raise ValueError(f"Pengguna '{clean_username}' tidak ditemukan.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?;", (clean_username,))
    return True

def verify_user_password(user_record, password):
    """
    Verifikasi password menggunakan perbandingan konstan & hash aman.
    """
    if not user_record or not password:
        return False
        
    stored_hash = user_record.get('password_hash')
    if stored_hash:
        return check_password_hash(stored_hash, password)
        
    legacy_pass = user_record.get('password')
    if legacy_pass:
        return hmac.compare_digest(str(legacy_pass), str(password))
        
    return False
