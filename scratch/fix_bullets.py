# -*- coding: utf-8 -*-
"""Reposisi bullet (•) pada blok titik kerusakan agar sesuai format referensi."""
import re

BASE = r'airside-report-flask/app'
B = '\u2022'  # •


def patch(path, pairs):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        c = f.read()
    crlf = '\r\n' in c
    c = c.replace('\r\n', '\n')
    for old, new, count in pairs:
        n = c.count(old)
        if n != count:
            raise SystemExit(f'{path}: expected {count} of {old!r}, found {n}')
        c = c.replace(old, new)
    if crlf:
        c = c.replace('\n', '\r\n')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(c)
    print('OK', path)


# ---------- staff_routes.py ----------
if False: patch(f'{BASE}/routes/staff_routes.py', [
    ("""    def format_damage_line(val):
        if not val or val == '-':
            return "\u2022  Jenis kerusakan : -\\n"
        lines = [l.strip() for l in str(val).strip().split('\\n') if l.strip()]
        if not lines:
            return "\u2022  Jenis kerusakan : -\\n"
        if len(lines) == 1:
            return f"\u2022  Jenis kerusakan : {lines[0]}\\n"
        formatted_items = "\\n".join(f"  {l}" for l in lines)
        return f"\u2022  Jenis kerusakan :\\n{formatted_items}\\n\"""",
     """    def format_damage_line(val, label="Jenis kerusakan"):
        if not val or val == '-':
            return f"    {label} : -\\n"
        lines = [l.strip() for l in str(val).strip().split('\\n') if l.strip()]
        if not lines:
            return f"    {label} : -\\n"
        if len(lines) == 1:
            return f"    {label} : {lines[0]}\\n"
        formatted_items = "\\n".join(f"      {l}" for l in lines)
        return f"    {label} :\\n{formatted_items}\\n\"""", 1),
    ("    Jml Titik Rusak : ", f"{B}  Jml Titik Rusak : ", 3),
    ("    Jml titik yang sudah diperbaiki : ", f"{B}  Jml titik yang sudah diperbaiki : ", 3),
    ("_JENIS_DIPERBAIKI'))}    Jml titik yang belum diperbaiki : ",
     f"_JENIS_DIPERBAIKI'))}}{B}  Jml titik yang belum diperbaiki : ", 3),
    ("_JENIS_BELUM'))}    Jml titik rusak berulang > 1x : ",
     f"_JENIS_BELUM'), 'Jenis kerusakan yang belum diperbaiki')}}{B}  Jml titik rusak berulang > 1x : ", 3),
])

# ---------- staff_dashboard.html (preview WA petugas) ----------
patch(f'{BASE}/templates/staff_dashboard.html', [
    ("""        const formatJenis = (val) => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return '\u2022  Jenis kerusakan : -\\n';
            const cleaned = val.trim();
            if (cleaned.includes('\\n')) return `\u2022  Jenis kerusakan :\\n${cleaned}\\n`;
            return `\u2022  Jenis kerusakan : ${cleaned}\\n`;
        };""",
     """        const formatJenis = (val, label = 'Jenis kerusakan') => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `    ${label} : -\\n`;
            const cleaned = val.trim();
            if (cleaned.includes('\\n')) return `    ${label} :\\n${cleaned}\\n`;
            return `    ${label} : ${cleaned}\\n`;
        };""", 1),
    ("    Jml Titik Rusak : ", f"{B}  Jml Titik Rusak : ", 3),
    ("    Jml titik yang sudah diperbaiki : ", f"{B}  Jml titik yang sudah diperbaiki : ", 3),
    ("_JENIS_DIPERBAIKI'))}    Jml titik yang belum diperbaiki : ",
     f"_JENIS_DIPERBAIKI'))}}{B}  Jml titik yang belum diperbaiki : ", 3),
    ("_JENIS_BELUM'))}    Jml titik rusak berulang > 1x : ",
     f"_JENIS_BELUM'), 'Jenis kerusakan yang belum diperbaiki')}}{B}  Jml titik rusak berulang > 1x : ", 3),
])

# ---------- admin_dashboard.html (kompilasi Deputy) ----------
patch(f'{BASE}/templates/admin_dashboard.html', [
    ("""                                const fmtJenis = (val) => {
                                    const c = vClean(val);
                                    if (c === "-" || c.toLowerCase() === "nihil") return "\u2022  Jenis kerusakan : -\\n";
                                    if (c.includes("\\n")) return `\u2022  Jenis kerusakan :\\n${c}\\n`;
                                    return `\u2022  Jenis kerusakan : ${c}\\n`;
                                };""",
     """                                const fmtJenis = (val, label = "Jenis kerusakan") => {
                                    const c = vClean(val);
                                    if (c === "-" || c.toLowerCase() === "nihil") return `    ${label} : -\\n`;
                                    if (c.includes("\\n")) return `    ${label} :\\n${c}\\n`;
                                    return `    ${label} : ${c}\\n`;
                                };""", 1),
    ("branchText += `    Jml Titik Rusak : ", f"branchText += `{B}  Jml Titik Rusak : ", 3),
    ("branchText += `    Jml titik yang sudah diperbaiki : ", f"branchText += `{B}  Jml titik yang sudah diperbaiki : ", 3),
    ("branchText += `    Jml titik yang belum diperbaiki : ", f"branchText += `{B}  Jml titik yang belum diperbaiki : ", 3),
    ("branchText += `    Jml titik rusak berulang > 1x : ", f"branchText += `{B}  Jml titik rusak berulang > 1x : ", 3),
])

# label "yang belum diperbaiki" untuk fmtJenis(*_JENIS_BELUM) di admin
path = f'{BASE}/templates/admin_dashboard.html'
with open(path, 'r', encoding='utf-8', newline='') as f:
    c = f.read()
c, n = re.subn(r'fmtJenis\(gf\("(\w+_JENIS_BELUM)", (\d+)\)\)',
               r'fmtJenis(gf("\1", \2), "Jenis kerusakan yang belum diperbaiki")', c)
print('admin JENIS_BELUM label replaced:', n)
with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(c)
