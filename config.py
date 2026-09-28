import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-airside'
    # Base directory for local excel files
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXCEL_PATHS = {
        'LOP': os.path.join(BASE_DIR, 'LOP_OKT_2026 (1).xlsx'),
        'DPS': os.path.join(BASE_DIR, 'DPS_OKT_2026.xlsx'),
        'BWX': os.path.join(BASE_DIR, 'BWX_OKT_2026.xlsx'),
        'KOE': os.path.join(BASE_DIR, 'KOE_OKT_2026.xlsx'),
        'ADMIN': os.path.join(BASE_DIR, 'ADMIN_OKT_2026.xlsx')
    }
