def update_gm_routes():
    path = 'app/routes/gm_routes.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old = """    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema in gm_routes: {e}")"""

    new = """    schema = {}
    try:
        from app.models.config_store import load_schema
        schema = load_schema()
    except Exception as e:
        print(f"Error loading schema in gm_routes: {e}")"""

    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated gm_routes.py successfully")
    else:
        print("Warning: old pattern not found in gm_routes.py")

def update_staff_routes():
    path = 'app/routes/staff_routes.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old1 = """    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema in staff_routes: {e}")"""

    new1 = """    schema = {}
    try:
        from app.models.config_store import load_schema
        schema = load_schema()
    except Exception as e:
        print(f"Error loading schema in staff_routes: {e}")"""

    old2 = """        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema_data = json.load(f)"""

    new2 = """        from app.models.config_store import load_schema
        schema_data = load_schema()"""

    if old1 in content:
        content = content.replace(old1, new1)
        print("Updated old1 in staff_routes.py")
    if old2 in content:
        content = content.replace(old2, new2)
        print("Updated old2 in staff_routes.py")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_gsheets_service():
    path = 'app/services/gsheets_service.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. In get_schema_field_names
    old_names = """    if schema is None:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)"""

    new_names = """    if schema is None:
        from app.models.config_store import load_schema
        schema = load_schema()"""

    if old_names in content:
        content = content.replace(old_names, new_names)
        print("Updated get_schema_field_names in gsheets_service.py")

    # 2. In sync_schema_from_sheet
    old_sync_load = """    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
    with open(schema_path, 'r') as f:
        schema = json.load(f)"""

    new_sync_load = """    from app.models.config_store import load_schema, save_schema
    schema = load_schema()"""

    if old_sync_load in content:
        content = content.replace(old_sync_load, new_sync_load)
        print("Updated sync_schema_from_sheet load in gsheets_service.py")

    old_sync_save = """    if added_fields or removed_fields:
        with open(schema_path, 'w') as f:
            json.dump(schema, f, indent=2)"""

    new_sync_save = """    if added_fields or removed_fields:
        save_schema(schema)"""

    if old_sync_save in content:
        content = content.replace(old_sync_save, new_sync_save)
        print("Updated sync_schema_from_sheet save in gsheets_service.py")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_gm_routes()
    update_staff_routes()
    update_gsheets_service()
    print("Done integrating persistent schema!")
with open('app/routes/staff_routes.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """    schema = {}
    try:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'form_schema.json')
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema: {e}")"""

replacement = """    schema = {}
    try:
        from app.models.config_store import load_schema
        schema = load_schema()
    except Exception as e:
        print(f"Error loading schema: {e}")"""

if target in text:
    text = text.replace(target, replacement, 1)
    with open('app/routes/staff_routes.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Replaced staff_routes dashboard schema successfully!")
else:
    print("Target not found in staff_routes.py")
