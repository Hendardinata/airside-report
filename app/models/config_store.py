import json
import os
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'app_config.json')
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), '..', 'form_schema.json')

DEFAULT_CONFIG = {
    "active_month": "",
    "airports": {
        "LOP": {"sheet_url": "", "active_month": "", "drive_folder": "", "template_id": "", "pic_phone": ""},
        "DPS": {"sheet_url": "", "active_month": "", "drive_folder": "", "template_id": "", "pic_phone": ""},
        "BWX": {"sheet_url": "", "active_month": "", "drive_folder": "1jBdLeBkpy0RLRnPoOd53bduNET-I7ysT", "template_id": "", "pic_phone": ""},
        "KOE": {"sheet_url": "", "active_month": "", "drive_folder": "", "template_id": "", "pic_phone": ""}
    },
    "admin": {
        "master_sheet_url": "",
        "deputy_phone": "",
        "admin_phone": ""
    }
}

def load_config():
    """
    Memuat konfigurasi aplikasi dari SQLite (prioritas utama yang kebal terhadap git pull/reset)
    atau fallback ke app_config.json jika belum tersimpan di SQLite.
    """
    config = None
    try:
        from app.models.db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT config_value FROM system_config WHERE config_key = 'app_config';")
            row = cursor.fetchone()
            if row and row['config_value']:
                config = json.loads(row['config_value'])
    except Exception:
        config = None

    if not config:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                config = DEFAULT_CONFIG.copy()
        else:
            config = DEFAULT_CONFIG.copy()

    # Migrasi config lama jika field baru belum ada
    modified = False
    if 'active_month' not in config:
        config['active_month'] = ""
        modified = True

    if 'active_year' not in config:
        config['active_year'] = config.get('active_month', '').split('-')[0] if config.get('active_month') else "2026"
        modified = True

    if 'active_month_label' not in config:
        config['active_month_label'] = "Bulan NOV 2026"
        modified = True

    for code in config.get('airports', {}):
        if 'sheet_name' not in config['airports'][code]:
            config['airports'][code]['sheet_name'] = ""
            modified = True
        if 'active_month' not in config['airports'][code]:
            config['airports'][code]['active_month'] = ""
            modified = True
        if 'pic_phone' not in config['airports'][code]:
            config['airports'][code]['pic_phone'] = ""
            modified = True
        if 'gm_phone' not in config['airports'][code]:
            config['airports'][code]['gm_phone'] = ""
            modified = True
        if 'dh_phone' not in config['airports'][code]:
            config['airports'][code]['dh_phone'] = config['airports'][code].get('gm_phone', "")
            modified = True
    
    if 'admin' not in config:
        config['admin'] = {"master_sheet_url": "", "deputy_phone": "", "admin_phone": ""}
        modified = True
    else:
        if 'deputy_phone' not in config['admin']:
            config['admin']['deputy_phone'] = ""
            modified = True
        if 'admin_phone' not in config['admin']:
            config['admin']['admin_phone'] = ""
            modified = True
            
    # Pastikan data tersimpan di SQLite
    save_config(config)
    return config

def save_config(config_data):
    """
    Menyimpan konfigurasi secara permanen ke SQLite (tidak akan ter-reset oleh git pull)
    serta menulis cadangan ke app_config.json.
    """
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1. Simpan permanen ke SQLite
    try:
        from app.models.db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
            VALUES (?, ?, ?);
            """, ('app_config', json.dumps(config_data, indent=4), now_str))
    except Exception as e:
        print(f"Warning simpan konfigurasi ke SQLite: {e}")

    # 2. Cadangan ke file JSON
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Warning simpan konfigurasi ke file: {e}")

def load_schema():
    """
    Memuat kustomisasi schema form builder dari SQLite (kebal git pull/reset)
    atau fallback ke app/form_schema.json.
    """
    schema = None
    try:
        from app.models.db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT config_value FROM system_config WHERE config_key = 'form_schema';")
            row = cursor.fetchone()
            if row and row['config_value']:
                schema = json.loads(row['config_value'])
    except Exception:
        schema = None

    if not schema:
        if os.path.exists(SCHEMA_FILE):
            try:
                with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
            except Exception:
                schema = {}
        else:
            schema = {}

        if schema:
            save_schema(schema)

    return schema

def save_schema(schema_data):
    """
    Menyimpan schema form builder ke SQLite (permanen) dan cadangan ke app/form_schema.json.
    """
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        from app.models.db import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO system_config (config_key, config_value, updated_at)
            VALUES (?, ?, ?);
            """, ('form_schema', json.dumps(schema_data, indent=2), now_str))
    except Exception as e:
        print(f"Warning simpan schema ke SQLite: {e}")

    try:
        with open(SCHEMA_FILE, 'w', encoding='utf-8') as f:
            json.dump(schema_data, f, indent=2)
    except Exception as e:
        print(f"Warning simpan schema ke file: {e}")

def get_airport_config(airport_code):
    config = load_config()
    conf = config['airports'].get(airport_code, {})
    if conf and not conf.get('dh_phone'):
        conf['dh_phone'] = conf.get('gm_phone', '')
    return conf

def update_airport_config(airport_code, sheet_url=None, drive_folder=None, template_id=None, pic_phone=None, gm_phone=None, dh_phone=None, active_month=None, sheet_name=None):
    config = load_config()
    if airport_code in config['airports']:
        if sheet_url is not None:
            config['airports'][airport_code]['sheet_url'] = sheet_url
        if sheet_name is not None:
            config['airports'][airport_code]['sheet_name'] = sheet_name
        if drive_folder is not None:
            config['airports'][airport_code]['drive_folder'] = drive_folder
        if template_id is not None:
            config['airports'][airport_code]['template_id'] = template_id
        if pic_phone is not None:
            config['airports'][airport_code]['pic_phone'] = pic_phone
        
        target_dh_phone = dh_phone if dh_phone is not None else gm_phone
        if target_dh_phone is not None:
            config['airports'][airport_code]['dh_phone'] = target_dh_phone
            config['airports'][airport_code]['gm_phone'] = target_dh_phone
        if active_month is not None:
            config['airports'][airport_code]['active_month'] = str(active_month).strip()
            config['active_month'] = str(active_month).strip()
        save_config(config)
        try:
            from app.services.gsheets_service import invalidate_calendar_cache
            invalidate_calendar_cache(airport_code)
        except Exception:
            pass

def update_fleet_matrix_meta(active_year=None, active_month=None, active_month_label=None):
    config = load_config()
    if active_year is not None:
        config['active_year'] = str(active_year).strip()
    if active_month is not None:
        config['active_month'] = str(active_month).strip()
    if active_month_label is not None:
        config['active_month_label'] = str(active_month_label).strip()
    save_config(config)

def get_active_month(airport_code=None):
    config = load_config()
    if airport_code and airport_code in config.get('airports', {}):
        branch_m = config['airports'][airport_code].get('active_month')
        if branch_m:
            return branch_m
    return config.get('active_month', '')

def set_active_month(active_month, airport_code=None):
    config = load_config()
    month_val = str(active_month).strip()
    config['active_month'] = month_val
    if airport_code and airport_code in config.get('airports', {}):
        config['airports'][airport_code]['active_month'] = month_val
    elif not airport_code:
        # Update semua bandara
        for code in config.get('airports', {}):
            config['airports'][code]['active_month'] = month_val
    save_config(config)
    try:
        from app.services.gsheets_service import invalidate_calendar_cache
        invalidate_calendar_cache(airport_code)
    except Exception:
        pass

def get_admin_config():
    config = load_config()
    return config.get('admin', {})

def update_admin_config(deputy_phone=None, admin_phone=None):
    config = load_config()
    if 'admin' not in config:
        config['admin'] = {}
    if deputy_phone is not None:
        config['admin']['deputy_phone'] = deputy_phone
    if admin_phone is not None:
        config['admin']['admin_phone'] = admin_phone
    save_config(config)

