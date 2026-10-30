import os
import py_compile
from jinja2 import Environment, FileSystemLoader

print("=== 1. VERIFYING PYTHON SYNTAX ===")
py_files = [
    r'airside-report-flask/app/routes/auth_routes.py',
    r'airside-report-flask/app/routes/staff_routes.py',
    r'airside-report-flask/app/routes/admin_routes.py',
    r'airside-report-flask/app/routes/gm_routes.py',
    r'airside-report-flask/app/services/photo_service.py',
]
for p in py_files:
    py_compile.compile(p, doraise=True)
    print(f"OK: {p}")

print("\n=== 2. VERIFYING JINJA2 TEMPLATES ===")
env = Environment(loader=FileSystemLoader(r'airside-report-flask/app/templates'))
templates = [
    'base.html',
    'admin_dashboard.html',
    'gm_dashboard.html',
    'staff_dashboard.html',
    'public_dokumentasi.html'
]
for t in templates:
    tpl = env.get_template(t)
    print(f"OK: {t} compiled successfully")

print("\n=== ALL SYNTAX AND TEMPLATE CHECKS PASSED SUCCESSFULLY! ===")

