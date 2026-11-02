import re

def update_gsheets_service():
    path = 'app/services/gsheets_service.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update unsanitize_sheet_value
    old_unsanitize = """def unsanitize_sheet_value(val):
    \"\"\"
    Menghapus petik satu escape formula injection saat membaca dari Spreadsheet
    agar tampilan di web/dokumen kembali persis seperti yang diinputkan pengguna.
    \"\"\"
    if val is None:
        return ''
    s = str(val)
    if s.startswith("'") and len(s) > 1 and s[1] in ('=', '+', '-', '@', '\\t', '\\r'):
        return s[1:]
    return s"""

    new_unsanitize = """def unsanitize_sheet_value(val):
    \"\"\"
    Menghapus petik satu escape formula injection saat membaca dari Spreadsheet
    agar tampilan di web/dokumen kembali persis seperti yang diinputkan pengguna.
    \"\"\"
    if val is None:
        return ''
    s = str(val)
    if s.startswith("'"):
        rem = s[1:].lstrip()
        if rem and rem[0] in ('=', '+', '-', '@', '\\t', '\\r'):
            return s[1:]
    return s"""

    if old_unsanitize in content:
        content = content.replace(old_unsanitize, new_unsanitize)
        print("Updated unsanitize_sheet_value in gsheets_service.py")
    else:
        print("old_unsanitize not found in gsheets_service.py")

    # 2. Update get_daily_summary
    old_pci = 'summary[code]["pci"] = str(row_data[pci_col_idx]) if len(row_data) > pci_col_idx else "-"'
    new_pci = 'summary[code]["pci"] = unsanitize_sheet_value(str(row_data[pci_col_idx]).strip() if len(row_data) > pci_col_idx else "-")'
    if old_pci in content:
        content = content.replace(old_pci, new_pci)
        print("Updated pci unsanitize in gsheets_service.py")

    old_f1 = 'field_dict[c_key] = str(row_data[idx_col]).strip()'
    new_f1 = 'field_dict[c_key] = unsanitize_sheet_value(str(row_data[idx_col]).strip())'
    if old_f1 in content:
        content = content.replace(old_f1, new_f1)
        print("Updated f1 unsanitize in gsheets_service.py")

    old_f2 = 'field_dict[std_key] = str(row_data[pos]).strip()'
    new_f2 = 'field_dict[std_key] = unsanitize_sheet_value(str(row_data[pos]).strip())'
    if old_f2 in content:
        content = content.replace(old_f2, new_f2)
        print("Updated f2 unsanitize in gsheets_service.py")

    old_extra = 'col_val = str(row_data[i]).strip()'
    new_extra = 'col_val = unsanitize_sheet_value(str(row_data[i]).strip())'
    if old_extra in content:
        content = content.replace(old_extra, new_extra)
        print("Updated extra unsanitize in gsheets_service.py")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_admin_dashboard():
    path = 'app/templates/admin_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update vClean
    old_vclean = """                    function vClean(val) {
                        if (val === null || val === undefined || val === "") return "-";
                        let s = String(val).trim();
                        if (s.startsWith("'") and s.length > 1 and ['=', '+', '-', '@', '\\t', '\\r'].includes(s[1])) {
                            s = s.slice(1).trim();
                        }
                        return s || "-";
                    }"""
    # Note: in javascript, `and` was `&&`!
    old_vclean_js = """                    function vClean(val) {
                        if (val === null || val === undefined || val === "") return "-";
                        let s = String(val).trim();
                        if (s.startsWith("'") && s.length > 1 && ['=', '+', '-', '@', '\\t', '\\r'].includes(s[1])) {
                            s = s.slice(1).trim();
                        }
                        return s || "-";
                    }"""

    new_vclean_js = """                    function vClean(val) {
                        if (val === null || val === undefined || val === "") return "-";
                        let s = String(val).trim();
                        if (s.startsWith("'")) {
                            let rem = s.slice(1).trimStart();
                            if (rem && ['=', '+', '-', '@', '\\t', '\\r'].includes(rem[0])) {
                                s = s.slice(1).trim();
                            }
                        }
                        return s || "-";
                    }"""

    if old_vclean_js in content:
        content = content.replace(old_vclean_js, new_vclean_js)
        print("Updated vClean in admin_dashboard.html")
    else:
        print("old_vclean_js not found in admin_dashboard.html")

    # 2. Add formatIndent and update fmtJenis in renderFleetRekap
    old_fmtjenis = """                                const fmtJenis = (val, label = "Jenis kerusakan") => {
                                    const c = vClean(val);
                                    if (c === "-" || c.toLowerCase() === "nihil") return `    ${label} : -\\n`;
                                    if (c.includes("\\n")) return `    ${label} :\\n${c}\\n`;
                                    return `    ${label} : ${c}\\n`;
                                };"""

    new_fmtjenis = """                                const formatIndent = (prefix, val) => {
                                    let c = vClean(val);
                                    if (!c || c === "-" || c.toLowerCase() === "nihil") return `${prefix}-\\n`;
                                    const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    if (lines.length === 0) return `${prefix}-\\n`;
                                    const indent = ' '.repeat(prefix.length);
                                    return `${prefix}${lines.join('\\n' + indent)}\\n`;
                                };
                                const fmtJenis = (val, label = "Jenis kerusakan") => {
                                    const c = vClean(val);
                                    if (!c || c === "-" || c.toLowerCase() === "nihil") return `    ${label} : -\\n`;
                                    const prefix = `    ${label} : `;
                                    const indent = ' '.repeat(prefix.length);
                                    const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    if (lines.length === 0) return `${prefix}-\\n`;
                                    return `${prefix}${lines.join('\\n' + indent)}\\n`;
                                };"""

    if old_fmtjenis in content:
        content = content.replace(old_fmtjenis, new_fmtjenis)
        print("Updated formatIndent and fmtJenis in admin_dashboard.html")
    else:
        print("old_fmtjenis not found in admin_dashboard.html")

    # 3. Update Realisasi fields in branchText
    old_rwy_marka = 'branchText += `       Realisasi : ${vClean(gf("RUNWAY_MARKA_REALISASI", 17))}\\n`;'
    new_rwy_marka = 'branchText += formatIndent("       Realisasi : ", gf("RUNWAY_MARKA_REALISASI", 17));'
    if old_rwy_marka in content:
        content = content.replace(old_rwy_marka, new_rwy_marka)
        print("Updated RUNWAY_MARKA_REALISASI in admin_dashboard.html")

    old_rwy_rubber = 'branchText += `       Realisasi : ${vClean(gf("RUNWAY_RUBBER_REAL", 22))}\\n`;'
    new_rwy_rubber = 'branchText += formatIndent("       Realisasi : ", gf("RUNWAY_RUBBER_REAL", 22));'
    if old_rwy_rubber in content:
        content = content.replace(old_rwy_rubber, new_rwy_rubber)
        print("Updated RUNWAY_RUBBER_REAL in admin_dashboard.html")

    old_twy_marka = 'branchText += `      Realisasi : ${vClean(gf("TWY_MARKA_REALISASI", 34))}\\n`;'
    new_twy_marka = 'branchText += formatIndent("      Realisasi : ", gf("TWY_MARKA_REALISASI", 34));'
    if old_twy_marka in content:
        content = content.replace(old_twy_marka, new_twy_marka)
        print("Updated TWY_MARKA_REALISASI in admin_dashboard.html")

    old_apn_marka = 'branchText += `      Realisasi : ${vClean(gf("APN_MARKA_REALISASI", 47))}\\n`;'
    new_apn_marka = 'branchText += formatIndent("      Realisasi : ", gf("APN_MARKA_REALISASI", 47));'
    if old_apn_marka in content:
        content = content.replace(old_apn_marka, new_apn_marka)
        print("Updated APN_MARKA_REALISASI in admin_dashboard.html")

    old_rumput = 'branchText += `      Realisasi : ${vClean(gf("RUMPUT_REALISASI", 52))}\\n`;'
    new_rumput = 'branchText += formatIndent("      Realisasi : ", gf("RUMPUT_REALISASI", 52));'
    if old_rumput in content:
        content = content.replace(old_rumput, new_rumput)
        print("Updated RUMPUT_REALISASI in admin_dashboard.html")

    # 4. Update Catatan Khusus in branchText
    old_cat_loop = """                                branchText += `Catatan Khusus : \\n`;
                                if (catList.length > 0) {
                                    catList.forEach((c, cIdx) => {
                                        branchText += `${cIdx + 1}. ${c}\\n`;
                                    });
                                } else {
                                    branchText += `- (Nihil)\\n`;
                                }"""

    new_cat_loop = """                                branchText += `Catatan Khusus : \\n`;
                                if (catList.length > 0) {
                                    catList.forEach((c, cIdx) => {
                                        const catPrefix = `${cIdx + 1}. `;
                                        const catIndent = ' '.repeat(catPrefix.length);
                                        const cLines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                        if (cLines.length > 0) {
                                            branchText += `${catPrefix}${cLines.join('\\n' + catIndent)}\\n`;
                                        }
                                    });
                                } else {
                                    branchText += `- (Nihil)\\n`;
                                }"""

    if old_cat_loop in content:
        content = content.replace(old_cat_loop, new_cat_loop)
        print("Updated Catatan Khusus in admin_dashboard.html")
    else:
        print("old_cat_loop not found in admin_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_staff_dashboard():
    path = 'app/templates/staff_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update v in updateLiveWaPreview
    old_v = """        const v = (id) => {
            const el = document.getElementById('input-' + id) || document.querySelector(`[name="${id}"]`);
            if (!el) return '-';
            let val = (el.value || '').trim();
            if (val.startsWith("'") && val.length > 1 && ['=', '+', '-', '@', '\\t', '\\r'].includes(val[1])) {
                val = val.slice(1).trim();
            }
            return val || '-';
        };"""

    new_v = """        const v = (id) => {
            const el = document.getElementById('input-' + id) || document.querySelector(`[name="${id}"]`);
            if (!el) return '-';
            let val = (el.value || '').trim();
            if (val.startsWith("'")) {
                let rem = val.slice(1).trimStart();
                if (rem && ['=', '+', '-', '@', '\\t', '\\r'].includes(rem[0])) {
                    val = val.slice(1).trim();
                }
            }
            return val || '-';
        };

        const formatIndent = (prefix, val) => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `${prefix}-\\n`;
            const lines = String(val).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) return `${prefix}-\\n`;
            const indent = ' '.repeat(prefix.length);
            return `${prefix}${lines.join('\\n' + indent)}\\n`;
        };"""

    if old_v in content:
        content = content.replace(old_v, new_v)
        print("Updated v and formatIndent in staff_dashboard.html")
    else:
        print("old_v not found in staff_dashboard.html")

    # 2. Update formatJenis
    old_fj = """        const formatJenis = (val, label = 'Jenis kerusakan') => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `    ${label} : -\\n`;
            const cleaned = val.trim();
            if (cleaned.includes('\\n')) return `    ${label} :\\n${cleaned}\\n`;
            return `    ${label} : ${cleaned}\\n`;
        };"""

    new_fj = """        const formatJenis = (val, label = 'Jenis kerusakan') => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `    ${label} : -\\n`;
            const prefix = `    ${label} : `;
            const indent = ' '.repeat(prefix.length);
            const lines = String(val).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) return `${prefix}-\\n`;
            return `${prefix}${lines.join('\\n' + indent)}\\n`;
        };"""

    if old_fj in content:
        content = content.replace(old_fj, new_fj)
        print("Updated formatJenis in staff_dashboard.html")
    else:
        print("old_fj not found in staff_dashboard.html")

    # 3. Update catatanStr
    old_cat = """        let catatanStr = '';
        let cIdx = 1;
        for (let i = 1; i <= 7; i++) {
            const c = v('CATATAN_' + i);
            if (c && c !== '-' && c.toLowerCase() !== 'nihil') {
                catatanStr += `${cIdx}. ${c}\\n`;
                cIdx++;
            }
        }
        if (!catatanStr) catatanStr = '- (Nihil)\\n';"""

    new_cat = """        let catatanStr = '';
        let cIdx = 1;
        for (let i = 1; i <= 7; i++) {
            const c = v('CATATAN_' + i);
            if (c && c !== '-' && c.toLowerCase() !== 'nihil') {
                const prefix = `${cIdx}. `;
                const indent = ' '.repeat(prefix.length);
                const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                if (lines.length > 0) {
                    catatanStr += `${prefix}${lines.join('\\n' + indent)}\\n`;
                    cIdx++;
                }
            }
        }
        if (!catatanStr) catatanStr = '- (Nihil)\\n';"""

    if old_cat in content:
        content = content.replace(old_cat, new_cat)
        print("Updated catatanStr in staff_dashboard.html")
    else:
        print("old_cat not found in staff_dashboard.html")

    # 4. Update Realisasi fields in template literal
    old_tpl_rwy_marka = """•  Marka :
       Standar : ${v('RUNWAY_MARKA_STD')}
       Realisasi : ${v('RUNWAY_MARKA_REALISASI')}"""

    new_tpl_rwy_marka = """•  Marka :
       Standar : ${v('RUNWAY_MARKA_STD')}
${formatIndent('       Realisasi : ', v('RUNWAY_MARKA_REALISASI'))}"""

    if old_tpl_rwy_marka in content:
        content = content.replace(old_tpl_rwy_marka, new_tpl_rwy_marka)
        print("Updated RUNWAY_MARKA_REALISASI in staff_dashboard.html")
    else:
        print("old_tpl_rwy_marka not found in staff_dashboard.html")

    old_tpl_rwy_rub = """•  Rubber Removal :  
       Standar ketentuan : ${v('RUNWAY_RUBBER_STD')}
       Realisasi : ${v('RUNWAY_RUBBER_REAL')}"""

    new_tpl_rwy_rub = """•  Rubber Removal :  
       Standar ketentuan : ${v('RUNWAY_RUBBER_STD')}
${formatIndent('       Realisasi : ', v('RUNWAY_RUBBER_REAL'))}"""

    if old_tpl_rwy_rub in content:
        content = content.replace(old_tpl_rwy_rub, new_tpl_rwy_rub)
        print("Updated RUNWAY_RUBBER_REAL in staff_dashboard.html")
    else:
        print("old_tpl_rwy_rub not found in staff_dashboard.html")

    old_tpl_twy_marka = """•  Marka :
      Standar : ${v('TWY_MARKA_STD')}
      Realisasi : ${v('TWY_MARKA_REALISASI')}"""

    new_tpl_twy_marka = """•  Marka :
      Standar : ${v('TWY_MARKA_STD')}
${formatIndent('      Realisasi : ', v('TWY_MARKA_REALISASI'))}"""

    if old_tpl_twy_marka in content:
        content = content.replace(old_tpl_twy_marka, new_tpl_twy_marka)
        print("Updated TWY_MARKA_REALISASI in staff_dashboard.html")
    else:
        print("old_tpl_twy_marka not found in staff_dashboard.html")

    old_tpl_apn_marka = """•  Marka :
      Standar : ${v('APN_MARKA_STD')}
      Realisasi : ${v('APN_MARKA_REALISASI')}"""

    new_tpl_apn_marka = """•  Marka :
      Standar : ${v('APN_MARKA_STD')}
${formatIndent('      Realisasi : ', v('APN_MARKA_REALISASI'))}"""

    if old_tpl_apn_marka in content:
        content = content.replace(old_tpl_apn_marka, new_tpl_apn_marka)
        print("Updated APN_MARKA_REALISASI in staff_dashboard.html")
    else:
        print("old_tpl_apn_marka not found in staff_dashboard.html")

    old_tpl_rumput = """D. Pemeliharaan Potong Rumput
      Standar : ${v('RUMPUT_STD')}
      Realisasi : ${v('RUMPUT_REALISASI')}"""

    new_tpl_rumput = """D. Pemeliharaan Potong Rumput
      Standar : ${v('RUMPUT_STD')}
${formatIndent('      Realisasi : ', v('RUMPUT_REALISASI'))}"""

    if old_tpl_rumput in content:
        content = content.replace(old_tpl_rumput, new_tpl_rumput)
        print("Updated RUMPUT_REALISASI in staff_dashboard.html")
    else:
        print("old_tpl_rumput not found in staff_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_gm_dashboard():
    path = 'app/templates/gm_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update fmt at line 5536
    old_gm_fmt = """                        if (s.startsWith("'") && s.length > 1 && ['=', '+', '-', '@', '\\t', '\\r'].includes(s[1])) {
                            s = s.slice(1).trim();
                        }"""
    new_gm_fmt = """                        if (s.startsWith("'")) {
                            let rem = s.slice(1).trimStart();
                            if (rem && ['=', '+', '-', '@', '\\t', '\\r'].includes(rem[0])) {
                                s = s.slice(1).trim();
                            }
                        }"""
    if old_gm_fmt in content:
        content = content.replace(old_gm_fmt, new_gm_fmt)
        print("Updated fmt in gm_dashboard.html")
    else:
        print("old_gm_fmt not found in gm_dashboard.html")

    # 2. Update safe, fmt, and renderDocField in edit mode
    old_gm_safe = """                    const safe = (v) => {
                        if (v === undefined || v === null || String(v).trim() === '-') return '';
                        let s = String(v);
                        if (s.startsWith("'") && s.length > 1 && ['=', '+', '-', '@', '\\t', '\\r'].includes(s[1])) {
                            s = s.slice(1);
                        }
                        return s.replace(/"/g, '&quot;');
                    };"""

    new_gm_safe = """                    const safe = (v) => {
                        if (v === undefined || v === null || String(v).trim() === '-') return '';
                        let s = String(v);
                        if (s.startsWith("'")) {
                            let rem = s.slice(1).trimStart();
                            if (rem && ['=', '+', '-', '@', '\\t', '\\r'].includes(rem[0])) {
                                s = s.slice(1);
                            }
                        }
                        return s.replace(/"/g, '&quot;');
                    };"""
    if old_gm_safe in content:
        content = content.replace(old_gm_safe, new_gm_safe)
        print("Updated safe in gm_dashboard.html")

    old_gm_fmt2 = """                    const fmt = (val, fallback = '-') => {
                        if (val === undefined || val === null || String(val).trim() === '') return fallback;
                        let s = String(val).trim();
                        if (s.startsWith("'") && s.length > 1 && ['=', '+', '-', '@', '\\t', '\\r'].includes(s[1])) {
                            s = s.slice(1).trim();
                        }
                        return s;
                    };"""

    new_gm_fmt2 = """                    const fmt = (val, fallback = '-') => {
                        if (val === undefined || val === null || String(val).trim() === '') return fallback;
                        let s = String(val).trim();
                        if (s.startsWith("'")) {
                            let rem = s.slice(1).trimStart();
                            if (rem && ['=', '+', '-', '@', '\\t', '\\r'].includes(rem[0])) {
                                s = s.slice(1).trim();
                            }
                        }
                        return s;
                    };"""
    if old_gm_fmt2 in content:
        content = content.replace(old_gm_fmt2, new_gm_fmt2)
        print("Updated fmt2 in gm_dashboard.html")

    old_gm_render = """                        if (val.startsWith("'") && val.length > 1 && ['=', '+', '-', '@', '\\t', '\\r'].includes(val[1])) {
                            val = val.slice(1);
                        }"""

    new_gm_render = """                        if (val.startsWith("'")) {
                            let rem = val.slice(1).trimStart();
                            if (rem && ['=', '+', '-', '@', '\\t', '\\r'].includes(rem[0])) {
                                val = val.slice(1);
                            }
                        }"""
    if old_gm_render in content:
        content = content.replace(old_gm_render, new_gm_render)
        print("Updated renderDocField quote check in gm_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_gsheets_service()
    update_admin_dashboard()
    update_staff_dashboard()
    update_gm_dashboard()
    print("All updates completed successfully!")
