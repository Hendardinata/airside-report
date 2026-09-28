import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'app_config.json')

DEFAULT_CONFIG = {
    "airports": {
        "LOP": {"sheet_url": "", "drive_folder": "", "template_id": "", "pic_phone": ""},
        "DPS": {"sheet_url": "", "drive_folder": "", "template_id": "", "pic_phone": ""},
        "BWX": {"sheet_url": "", "drive_folder": "1jBdLeBkpy0RLRnPoOd53bduNET-I7ysT", "template_id": "", "pic_phone": ""},
        "KOE": {"sheet_url": "", "drive_folder": "", "template_id": "", "pic_phone": ""}
    },
    "admin": {
        "master_sheet_url": ""
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        # Migrasi config lama jika pic_phone belum ada
        modified = False
        for code in config.get('airports', {}):
            if 'pic_phone' not in config['airports'][code]:
                config['airports'][code]['pic_phone'] = ""
                modified = True
        if modified:
            save_config(config)
        return config

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

def get_airport_config(airport_code):
    config = load_config()
    return config['airports'].get(airport_code, {})

def update_airport_config(airport_code, sheet_url, drive_folder=None, template_id=None, pic_phone=None):
    config = load_config()
    if airport_code in config['airports']:
        if sheet_url is not None:
            config['airports'][airport_code]['sheet_url'] = sheet_url
        if drive_folder is not None:
            config['airports'][airport_code]['drive_folder'] = drive_folder
        if template_id is not None:
            config['airports'][airport_code]['template_id'] = template_id
        if pic_phone is not None:
            config['airports'][airport_code]['pic_phone'] = pic_phone
        save_config(config)
