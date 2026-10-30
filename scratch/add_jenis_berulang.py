# -*- coding: utf-8 -*-
"""Tambah field baru: *_JENIS_BERULANG (Jenis kerusakan titik rusak berulang)."""
import re

BASE = r'airside-report-flask/app'
LABEL = 'Jenis kerusakan titik rusak berulang'
AREAS = [  # (prefix field, placeholder, gm_view_indent_marker)
    ('RUNWAY', 'Contoh: Deflection di TH 09 / -'),
    ('TWY', 'Contoh: Rutting di Twy E / -'),
    ('APN', 'Contoh: Joint Sealant Damage / -'),
]


def rw(path, fn):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        c = f.read()
    crlf = '\r\n' in c
    c = c.replace('\r\n', '\n')
    c = fn(c)
    if crlf:
        c = c.replace('\n', '\r\n')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(c)
    print('OK', path)


def must_replace(c, old, new, count=1):
    n = c.count(old)
    if n != count:
        raise SystemExit(f'expected {count} of {old[:90]!r}, found {n}')
    return c.replace(old, new)


# 1. form_schema.json -> sisipkan field setelah *_TITIK_BERULANG
def f_schema(c):
    if '_JENIS_BERULANG' in c:
        return c
    for pfx, ph in AREAS:
        key = f'"name": "{pfx}_TITIK_BERULANG"'
        i = c.index(key)
        close = c.index('}', i)
        line_start = c.rfind('\n', 0, close) + 1
        ind = c[line_start:close]  # indent dari kurung tutup objek
        fi = ind + '  '
        block = (f',\n{ind}{{\n'
                 f'{fi}"label": "{LABEL}",\n'
                 f'{fi}"name": "{pfx}_JENIS_BERULANG",\n'
                 f'{fi}"placeholder": "{ph}",\n'
                 f'{fi}"required": false,\n'
                 f'{fi}"type": "text"\n'
                 f'{ind}}}')
        c = c[:close + 1] + block + c[close + 1:]
    return c


rw(f'{BASE}/form_schema.json', f_schema)


# 2. gsheets_service.py -> daftar field opsional inline
def f_gs(c):
    if 'RUNWAY_JENIS_BERULANG' in c:
        return c
    c = must_replace(c, """OPTIONAL_INLINE_FIELDS = {
    'RUNWAY_MARKA_PERSENTASE', 'RUNWAY_RUBBER_PROGRES', 'RUNWAY_RUBBER_PERF',
    'TWY_MARKA_PERSENTASE', 'TWY_WATER_DRY',
    'APN_MARKA_PERSENTASE', 'APN_WATER_DRY'
}""", """OPTIONAL_INLINE_FIELDS = {
    'RUNWAY_MARKA_PERSENTASE', 'RUNWAY_RUBBER_PROGRES', 'RUNWAY_RUBBER_PERF',
    'TWY_MARKA_PERSENTASE', 'TWY_WATER_DRY',
    'APN_MARKA_PERSENTASE', 'APN_WATER_DRY',
    'RUNWAY_JENIS_BERULANG', 'TWY_JENIS_BERULANG', 'APN_JENIS_BERULANG'
}""")
    c = must_replace(c, """                    'TWY_MARKA_PERSENTASE', 'TWY_WATER_DRY',
                    'APN_MARKA_PERSENTASE', 'APN_WATER_DRY'
                }""", """                    'TWY_MARKA_PERSENTASE', 'TWY_WATER_DRY',
                    'APN_MARKA_PERSENTASE', 'APN_WATER_DRY',
                    'RUNWAY_JENIS_BERULANG', 'TWY_JENIS_BERULANG', 'APN_JENIS_BERULANG'
                }""")
    return c


rw(f'{BASE}/services/gsheets_service.py', f_gs)


# 3. staff_routes.py (pesan WA server)
def f_staff_routes(c):
    for pfx, _ in AREAS:
        old = f"{{f_titik(v('{pfx}_TITIK_BERULANG'))}}\n"
        new = old + f"{{format_damage_line(v('{pfx}_JENIS_BERULANG'), '{LABEL}')}}"
        c = must_replace(c, old, new)
    return c


rw(f'{BASE}/routes/staff_routes.py', f_staff_routes)


# 4. staff_dashboard.html (pratinjau WA petugas)
def f_staff_dash(c):
    for pfx, _ in AREAS:
        old = f"${{f_titik(v('{pfx}_TITIK_BERULANG'))}}\n"
        new = old + f"${{formatJenis(v('{pfx}_JENIS_BERULANG'), '{LABEL}')}}"
        c = must_replace(c, old, new)
    return c


rw(f'{BASE}/templates/staff_dashboard.html', f_staff_dash)


# 5. admin_dashboard.html (kompilasi Deputy)
def f_admin(c):
    for pfx, _ in AREAS:
        m = re.search(r'( *)branchText \+= `\u2022  Jml titik rusak berulang > 1x : \$\{fTitik\(gf\("' + pfx + r'_TITIK_BERULANG", \d+\)\)\}\\n`;\n', c)
        if not m:
            raise SystemExit(f'admin berulang line not found for {pfx}')
        ind = m.group(1)
        ins = f'{ind}branchText += fmtJenis(gf("{pfx}_JENIS_BERULANG"), "{LABEL}");\n'
        c = c[:m.end()] + ins + c[m.end():]
    return c


rw(f'{BASE}/templates/admin_dashboard.html', f_admin)


# 6. gm_dashboard.html (tampilan dokumen + form koreksi DH)
def f_gm(c):
    for pfx, ph in AREAS:
        # a. tampilan dokumen (read-only)
        m = re.search(r'( *)<div class="doc-pair-val">\$\{fmtTitik\(d\.' + pfx + r'_RUSAK_BERULANG \|\| d\.' + pfx + r'_TITIK_BERULANG, \'0\'\)\}</div>\n( *)</div>\n', c)
        if not m:
            raise SystemExit(f'gm view not found for {pfx}')
        vi = m.group(1)
        ri = m.group(2)
        view = (f'{ri}<div class="doc-pair-row">\n'
                f'{vi}<div class="doc-pair-key">{LABEL}</div>\n'
                f'{vi}<div class="doc-pair-sep">:</div>\n'
                f'{vi}<div class="doc-pair-val">${{fmt(d.{pfx}_JENIS_BERULANG, \'-\')}}</div>\n'
                f'{ri}</div>\n')
        c = c[:m.end()] + view + c[m.end():]

        # b. form koreksi (input)
        m = re.search(r'( *)<input type="text" name="' + pfx + r'_TITIK_BERULANG"[^\n]*\n( *)</div>\n( *)</div>\n', c)
        if not m:
            raise SystemExit(f'gm edit not found for {pfx}')
        ii, vi, ri = m.group(1), m.group(2), m.group(3)
        edit = (f'{ri}<div class="doc-pair-row">\n'
                f'{vi}<div class="doc-pair-key">{LABEL}</div>\n'
                f'{vi}<div class="doc-pair-sep">:</div>\n'
                f'{vi}<div class="doc-pair-val">\n'
                f'{ii}<input type="text" name="{pfx}_JENIS_BERULANG" class="doc-inline-input" value="${{safe(d.{pfx}_JENIS_BERULANG)}}" placeholder="{ph}">\n'
                f'{vi}</div>\n'
                f'{ri}</div>\n')
        c = c[:m.end()] + edit + c[m.end():]
    return c


rw(f'{BASE}/templates/gm_dashboard.html', f_gm)

