import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'app_config.json')

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
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        # Migrasi config lama jika field baru belum ada
        modified = False
        if 'active_month' not in config:
            config['active_month'] = ""
            modified = True

        if 'staging_folder_id' not in config:
            config['staging_folder_id'] = "1qdPtWNaXQK8ZZYt0eq2nxHrRL3IJ8b3L"
            modified = True
            
        if 'staging_sheets' not in config:
            config['staging_sheets'] = {"LOP": "", "DPS": "", "BWX": "", "KOE": ""}
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
                
        if modified:
            save_config(config)
        return config

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

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

def get_staging_folder_id():
    config = load_config()
    return config.get('staging_folder_id', '1qdPtWNaXQK8ZZYt0eq2nxHrRL3IJ8b3L')

def get_staging_sheet_url(airport_code):
    config = load_config()
    return config.get('staging_sheets', {}).get(airport_code, '')

def update_staging_sheet_url(airport_code, sheet_url):
    config = load_config()
    if 'staging_sheets' not in config:
        config['staging_sheets'] = {}
    config['staging_sheets'][airport_code] = sheet_url
    save_config(config)

def update_staging_folder_id(folder_id):
    config = load_config()
    config['staging_folder_id'] = folder_id
    save_config(config)
