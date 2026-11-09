import re
from typing import Dict, Any, Tuple, Optional
from app.models.config_store import load_schema

def get_schema_field_definitions(schema: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Ekstrak metadata setiap field dari Form Schema aktif ke dalam dictionary terindeks berdasarkan nama field.
    """
    if schema is None:
        try:
            schema = load_schema()
        except Exception as e:
            print(f"Warning load_schema in validator_service: {e}")
            schema = {}

    field_map: Dict[str, Dict[str, Any]] = {}
    if not schema or not isinstance(schema, dict):
        return field_map

    for step in schema.get('steps', []):
        for section in step.get('sections', []):
            for field in section.get('fields', []):
                name = field.get('name')
                if not name:
                    continue
                field_map[name] = {
                    'name': name,
                    'label': field.get('label', name),
                    'type': field.get('type', 'text'),
                    'required': bool(field.get('required', False)),
                    'allow_decimal': bool(field.get('allow_decimal', False) or field.get('type') == 'decimal'),
                    'allow_negative': bool(field.get('allow_negative', False)),
                    'min': field.get('min'),
                    'max': field.get('max'),
                    'unit': field.get('unit', ''),
                    'options': field.get('options', [])
                }
    return field_map

def validate_numeric_value(raw_val: Any, field_def: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validasi nilai input khusus untuk field bertipe 'number' atau desimal/integer.
    Mencegah teks, huruf, simbol, dan memastikan hanya angka bulat (0-9) yang masuk,
    kecuali jika konfigurasi mengizinkan desimal (allow_decimal) atau negatif (allow_negative).
    Mengembalikan (is_valid, cleaned_str_or_error_msg).
    """
    label = field_def.get('label') or field_def.get('name') or 'Pertanyaan Angka'
    is_required = bool(field_def.get('required', False))
    allow_decimal = bool(field_def.get('allow_decimal', False) or field_def.get('type') == 'decimal')
    allow_negative = bool(field_def.get('allow_negative', False))

    if raw_val is None:
        val_str = ""
    else:
        val_str = str(raw_val).strip()

    # Bersihkan kutip tunggal escape formula jika ada
    if val_str.startswith("'"):
        val_str = val_str[1:].strip()

    # Jika kosong
    if val_str == "" or val_str == "-":
        if is_required:
            return False, f"Kolom '{label}' wajib diisi dengan angka."
        return True, ""

    # Rule 1: Angka Bulat Murni (0–9) - Default
    if not allow_decimal and not allow_negative:
        if not re.match(r'^\d+$', val_str):
            return False, f"Kolom '{label}' hanya boleh berisi angka bulat numerik (0–9) tanpa huruf, spasi, atau simbol."
        try:
            num_val = int(val_str)
        except ValueError:
            return False, f"Kolom '{label}' bernilai angka tidak valid."
    else:
        # Rule 2: Mendukung Desimal atau Negatif jika diizinkan konfigurasi
        normalized = val_str.replace(',', '.')
        if allow_decimal and allow_negative:
            pattern = r'^-?\d+(\.\d+)?$'
        elif allow_decimal:
            pattern = r'^\d+(\.\d+)?$'
        elif allow_negative:
            pattern = r'^-?\d+$'
        else:
            pattern = r'^\d+$'

        if not re.match(pattern, normalized):
            rules_desc = []
            if allow_decimal:
                rules_desc.append("desimal")
            if allow_negative:
                rules_desc.append("negatif")
            suffix = f" (mendukung {' & '.join(rules_desc)})" if rules_desc else ""
            return False, f"Kolom '{label}' harus berupa angka valid{suffix}."

        try:
            num_val = float(normalized) if allow_decimal else int(normalized)
        except ValueError:
            return False, f"Kolom '{label}' bernilai angka tidak valid."

    # Validasi Range Minimum & Maksimum jika diatur
    min_bound = field_def.get('min')
    max_bound = field_def.get('max')

    if min_bound is not None and min_bound != '':
        try:
            if num_val < float(min_bound):
                return False, f"Nilai kolom '{label}' tidak boleh lebih kecil dari {min_bound}."
        except (ValueError, TypeError):
            pass

    if max_bound is not None and max_bound != '':
        try:
            if num_val > float(max_bound):
                return False, f"Nilai kolom '{label}' tidak boleh lebih besar dari {max_bound}."
        except (ValueError, TypeError):
            pass

    return True, val_str

def validate_form_data(form_data: Dict[str, Any], schema: Optional[Dict[str, Any]] = None, require_all: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validasi data formulir sebelum disimpan ke Database Staging atau dikirim ke Google Sheets.
    Secara dinamis memeriksa seluruh pertanyaan berdasarkan konfigurasi Form Schema aktif.
    Mengembalikan tuple: (is_valid, error_message, cleaned_form_data).
    """
    if not form_data:
        return True, "", {}

    cleaned = dict(form_data)
    field_defs = get_schema_field_definitions(schema)

    for field_name, field_def in field_defs.items():
        is_present = field_name in cleaned
        val = cleaned.get(field_name)
        f_type = field_def.get('type', 'text')
        label = field_def.get('label') or field_name

        # 1. Validasi khusus field tipe Number / Decimal / Integer
        if f_type in ('number', 'decimal', 'integer') or field_def.get('allow_decimal'):
            if is_present or require_all:
                ok, res = validate_numeric_value(val, field_def)
                if not ok:
                    return False, res, {}
                if is_present:
                    cleaned[field_name] = res

        # 2. Validasi field required untuk tipe lainnya
        elif field_def.get('required'):
            if is_present or require_all:
                if val is None or str(val).strip() == '':
                    # Pengecualian field yang diatur otomatis sistem
                    if field_name not in ('REPORT_ID', 'KANTOR_CABANG', 'csrf_token'):
                        return False, f"Kolom '{label}' wajib diisi.", {}

    return True, "", cleaned
