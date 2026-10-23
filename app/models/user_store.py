import json
import os
import threading
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import hmac

USERS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'users.json'))
_lock = threading.Lock()

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

def load_users():
    """
    Memuat seluruh data pengguna dari users.json.
    Jika file belum ada, otomatis membuat dari DEFAULT_USERS.
    """
    with _lock:
        if not os.path.exists(USERS_FILE):
            _save_users_internal(DEFAULT_USERS)
            return dict(DEFAULT_USERS)

        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Migrasi data jika ada akun baru di default yang belum ada di file
            modified = False
            for k, default_record in DEFAULT_USERS.items():
                if k not in data:
                    data[k] = default_record
                    modified = True
                else:
                    # Pastikan field is_active ada
                    if 'is_active' not in data[k]:
                        data[k]['is_active'] = True
                        modified = True
                    # Migrasi role gm -> dh jika masih gm
                    if data[k].get('role') == 'gm':
                        data[k]['role'] = 'dh'
                        modified = True

            if modified:
                _save_users_internal(data)

            return data
        except Exception as e:
            print(f"Error reading users.json: {e}")
            return dict(DEFAULT_USERS)

def _save_users_internal(users_dict):
    """Fungsi pembantu penyimpanan internal."""
    tmp_file = f"{USERS_FILE}.tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(users_dict, f, indent=4, ensure_ascii=False)
    if os.path.exists(USERS_FILE):
        os.replace(tmp_file, USERS_FILE)
    else:
        os.rename(tmp_file, USERS_FILE)

def save_users(users_dict):
    """Menyimpan dictionary pengguna ke users.json dengan thread-safety."""
    with _lock:
        _save_users_internal(users_dict)

def get_user(username):
    """Mengambil data pengguna berdasarkan username (case-insensitive)."""
    if not username:
        return None
    users = load_users()
    return users.get(username.strip().lower())

def get_all_users(include_legacy_alias=False):
    """
    Mengambil daftar seluruh pengguna untuk ditampilkan di Admin Dashboard.
    Secara default menyembunyikan alias backward-compatibility gm_*.
    """
    users = load_users()
    user_list = []
    for uname, u in users.items():
        if not include_legacy_alias and u.get('is_legacy_alias'):
            continue
        user_list.append(u)
    # Urutkan: admin pertama, lalu berdasar role (dh -> staff), lalu nama
    def sort_key(item):
        role_prio = {'admin': 0, 'dh': 1, 'staff': 2}.get(item.get('role'), 9)
        return (role_prio, item.get('airport') or '', item.get('name') or '')
    user_list.sort(key=sort_key)
    return user_list

def add_user(username, name, role, airport, password, is_active=True):
    """
    Menambahkan pengguna baru.
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

    users = load_users()
    if clean_username in users:
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
        'created_at': now_str,
        'updated_at': now_str
    }

    users[clean_username] = new_user
    save_users(users)
    return new_user

def update_user_status(username, is_active):
    """
    Mengaktifkan atau menonaktifkan akun pengguna.
    Superadmin ('admin') tidak bisa dinonaktifkan.
    """
    clean_username = (username or '').strip().lower()
    if clean_username == 'admin':
        raise ValueError("Akun Administrator Utama tidak dapat dinonaktifkan.")

    users = load_users()
    if clean_username not in users:
        raise ValueError(f"Pengguna '{clean_username}' tidak ditemukan.")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    users[clean_username]['is_active'] = bool(is_active)
    users[clean_username]['updated_at'] = now_str
    save_users(users)
    return users[clean_username]

def update_user(username, name=None, role=None, airport=None, password=None, is_active=None):
    """
    Memperbarui profil pengguna (nama, role, cabang penempatan, kata sandi, status aktif).
    """
    clean_username = (username or '').strip().lower()
    users = load_users()
    if clean_username not in users:
        raise ValueError(f"Pengguna '{clean_username}' tidak ditemukan.")

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    target = users[clean_username]

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Nama lengkap tidak boleh kosong.")
        target['name'] = clean_name

    if role is not None and clean_username != 'admin':
        clean_role = role.strip().lower()
        if clean_role not in ('staff', 'dh', 'admin'):
            raise ValueError("Peran hanya boleh 'staff', 'dh', atau 'admin'.")
        target['role'] = clean_role

    if airport is not None and clean_username != 'admin':
        clean_airport = airport.strip().upper()
        if not clean_airport:
            raise ValueError("Cabang bandara wajib dipilih.")
        target['airport'] = clean_airport

    if is_active is not None and clean_username != 'admin':
        target['is_active'] = bool(is_active)

    if password is not None and str(password).strip():
        target['password_hash'] = generate_password_hash(str(password).strip())

    target['updated_at'] = now_str
    users[clean_username] = target
    save_users(users)
    return target

def delete_user(username):
    """
    Menghapus akun pengguna (hanya untuk akun non-system atau non-admin).
    """
    clean_username = (username or '').strip().lower()
    if clean_username == 'admin':
        raise ValueError("Akun Administrator Utama tidak dapat dihapus.")

    users = load_users()
    if clean_username not in users:
        raise ValueError(f"Pengguna '{clean_username}' tidak ditemukan.")

    del users[clean_username]
    save_users(users)
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
