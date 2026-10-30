with open(r'airside-report-flask/app/routes/auth_routes.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_auth = """@bp.route('/dokumentasi/<date_str>', methods=['GET'])
@bp.route('/dokumentasi/<date_str>/<airport_code>', methods=['GET'])
def public_dokumentasi(date_str, airport_code=None):"""

new_auth = """@bp.route('/dokumentasi/<date_str>', methods=['GET'])
@bp.route('/dokumentasi/<date_str>/<airport_code>', methods=['GET'])
@bp.route('/dok/<date_str>', methods=['GET'])
@bp.route('/dok/<date_str>/<airport_code>', methods=['GET'])
@bp.route('/d/<date_str>', methods=['GET'])
@bp.route('/d/<date_str>/<airport_code>', methods=['GET'])
def public_dokumentasi(date_str, airport_code=None):"""

c_norm = c.replace('\r\n', '\n')
if old_auth in c_norm:
    c_norm = c_norm.replace(old_auth, new_auth, 1)
    with open(r'airside-report-flask/app/routes/auth_routes.py', 'w', encoding='utf-8', newline='') as f:
        f.write(c_norm)
    print('Updated auth_routes.py')
else:
    print('auth_routes target not found')

with open(r'airside-report-flask/app/routes/staff_routes.py', 'r', encoding='utf-8') as f:
    sc = f.read()

sc_norm = sc.replace('\r\n', '\n')
old_staff1 = 'doc_section = f"\\nLampiran Dokumentasi Foto Lapangan ({len(branch_photos)} Foto):\\n{host_base}/dokumentasi/{clean_tgl}/{airport_code}\\n\\n"'
new_staff1 = 'doc_section = f"\\n\\nLampiran Dokumentasi Foto Lapangan ({len(branch_photos)} Foto):\\n\\n{host_base}/dokumentasi/{clean_tgl}/{airport_code}\\n\\n"'

old_staff2 = """        photo_info_line = (
            f"Lampiran Dokumentasi Foto ({len(current_photos)} Foto):\\n"
            f"{host_base}/dokumentasi/{tgl_str}/{airport_code}\\n\\n"
        ) if current_photos else \"\""""

new_staff2 = """        photo_info_line = (
            f"\\nLampiran Dokumentasi Foto ({len(current_photos)} Foto):\\n\\n"
            f"{host_base}/dokumentasi/{tgl_str}/{airport_code}\\n\\n"
        ) if current_photos else \"\""""

if old_staff1 in sc_norm:
    sc_norm = sc_norm.replace(old_staff1, new_staff1, 1)
    print('Updated staff_routes doc_section 1')
else:
    print('Staff 1 not found')

if old_staff2 in sc_norm:
    sc_norm = sc_norm.replace(old_staff2, new_staff2, 1)
    print('Updated staff_routes doc_section 2')
else:
    print('Staff 2 not found')

with open(r'airside-report-flask/app/routes/staff_routes.py', 'w', encoding='utf-8', newline='') as f:
    f.write(sc_norm)

