from werkzeug.security import generate_password_hash, check_password_hash
import hmac

AIRPORTS = {
    'LOP': {'name': 'Lombok', 'id': 'LOP', 'code': '1. Kantor Cabang LOP'},
    'DPS': {'name': 'Bali', 'id': 'DPS', 'code': '2. Kantor Cabang DPS'},
    'BWX': {'name': 'Banyuwangi', 'id': 'BWX', 'code': '3. Kantor Cabang BWX'},
    'KOE': {'name': 'Kupang', 'id': 'KOE', 'code': '4. Kantor Cabang KOE'}
}

# Default password '123' disimpan dalam format cryptographic hash (pbkdf2/scrypt)
# Bukan plaintext lagi!
USERS = {
    'admin': {
        'password_hash': generate_password_hash('123'),
        'role': 'admin',
        'name': 'Admin Regional'
    },
    'lop': {
        'password_hash': generate_password_hash('123'),
        'role': 'staff',
        'airport': 'LOP',
        'name': 'Petugas LOP'
    },
    'dps': {
        'password_hash': generate_password_hash('123'),
        'role': 'staff',
        'airport': 'DPS',
        'name': 'Petugas DPS'
    },
    'bwx': {
        'password_hash': generate_password_hash('123'),
        'role': 'staff',
        'airport': 'BWX',
        'name': 'Petugas BWX'
    },
    'koe': {
        'password_hash': generate_password_hash('123'),
        'role': 'staff',
        'airport': 'KOE',
        'name': 'Petugas KOE'
    },
}

def verify_user_password(user_record, password):
    """
    Verifikasi password menggunakan perbandingan konstan & hash aman.
    """
    if not user_record or not password:
        return False
        
    stored_hash = user_record.get('password_hash')
    if stored_hash:
        return check_password_hash(stored_hash, password)
        
    # Fallback jika ada password plaintext lama (dengan constant-time compare)
    legacy_pass = user_record.get('password')
    if legacy_pass:
        return hmac.compare_digest(str(legacy_pass), str(password))
        
    return False
