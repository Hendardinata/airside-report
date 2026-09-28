import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(BASE_DIR, '.secret_key')

def get_or_create_secret_key():
    env_secret = os.environ.get('SECRET_KEY')
    if env_secret and env_secret.strip():
        return env_secret.strip()
    
    if os.path.exists(SECRET_FILE):
        try:
            with open(SECRET_FILE, 'r', encoding='utf-8') as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass
            
    # Generate a cryptographically strong 256-bit random key
    new_key = secrets.token_hex(32)
    try:
        with open(SECRET_FILE, 'w', encoding='utf-8') as f:
            f.write(new_key)
    except Exception:
        pass
    return new_key

class Config:
    SECRET_KEY = get_or_create_secret_key()
    
    # Session Cookie Security Hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # DoS protection: limit request payload to 16MB
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Base directory for local excel files
    PARENT_DIR = os.path.dirname(BASE_DIR)
    EXCEL_PATHS = {
        'LOP': os.path.join(PARENT_DIR, 'LOP_OKT_2026 (1).xlsx'),
        'DPS': os.path.join(PARENT_DIR, 'DPS_OKT_2026.xlsx'),
        'BWX': os.path.join(PARENT_DIR, 'BWX_OKT_2026.xlsx'),
        'KOE': os.path.join(PARENT_DIR, 'KOE_OKT_2026.xlsx'),
        'ADMIN': os.path.join(PARENT_DIR, 'ADMIN_OKT_2026.xlsx')
    }
