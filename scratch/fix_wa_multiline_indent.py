import re

def update_admin_dashboard():
    path = 'app/templates/admin_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_format_indent = """                                const formatIndent = (prefix, val) => {
                                    let c = vClean(val);
                                    if (!c || c === "-" || c.toLowerCase() === "nihil") return `${prefix}-\\n`;
                                    const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    if (lines.length === 0) return `${prefix}-\\n`;
                                    const indent = ' '.repeat(prefix.length);
                                    return `${prefix}${lines.join('\\n' + indent)}\\n`;
                                };"""

    new_format_indent = """                                const formatIndent = (prefix, val) => {
                                    let c = vClean(val);
                                    if (!c || c === "-" || c.toLowerCase() === "nihil") return `${prefix}-\\n`;
                                    const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    if (lines.length === 0) return `${prefix}-\\n`;
                                    if (lines.length === 1) return `${prefix}${lines[0]}\\n`;
                                    const leadingSpaces = (prefix.match(/^ +/) || [''])[0].length;
                                    const textPart = prefix.slice(leadingSpaces);
                                    const visualSpaces = Math.round(textPart.length * 1.42);
                                    const indent = ' '.repeat(leadingSpaces + visualSpaces);
                                    return `${prefix}${lines.join('\\n' + indent)}\\n`;
                                };"""

    old_fmt_jenis = """                                const fmtJenis = (val, label = "Jenis kerusakan") => {
                                    const c = vClean(val);
                                    if (!c || c === "-" || c.toLowerCase() === "nihil") return `    ${label} : -\\n`;
                                    const prefix = `    ${label} : `;
                                    const indent = ' '.repeat(prefix.length);
                                    const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    if (lines.length === 0) return `${prefix}-\\n`;
                                    return `${prefix}${lines.join('\\n' + indent)}\\n`;
                                };"""

    new_fmt_jenis = """                                const fmtJenis = (val, label = "Jenis kerusakan") => {
                                    const c = vClean(val);
                                    if (!c || c === "-" || c.toLowerCase() === "nihil") return `    ${label} : -\\n`;
                                    const prefix = `    ${label} : `;
                                    const lines = String(c).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                    if (lines.length === 0) return `${prefix}-\\n`;
                                    if (lines.length === 1) return `${prefix}${lines[0]}\\n`;
                                    const leadingSpaces = (prefix.match(/^ +/) || [''])[0].length;
                                    const textPart = prefix.slice(leadingSpaces);
                                    const visualSpaces = Math.round(textPart.length * 1.42);
                                    const indent = ' '.repeat(leadingSpaces + visualSpaces);
                                    return `${prefix}${lines.join('\\n' + indent)}\\n`;
                                };"""

    if old_format_indent in content:
        content = content.replace(old_format_indent, new_format_indent)
        print("Updated formatIndent in admin_dashboard.html")
    else:
        print("Warning: old_format_indent not found in admin_dashboard.html")

    if old_fmt_jenis in content:
        content = content.replace(old_fmt_jenis, new_fmt_jenis)
        print("Updated fmtJenis in admin_dashboard.html")
    else:
        print("Warning: old_fmt_jenis not found in admin_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_staff_dashboard():
    path = 'app/templates/staff_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_format_indent = """        const formatIndent = (prefix, val) => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `${prefix}-\\n`;
            const lines = String(val).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) return `${prefix}-\\n`;
            const indent = ' '.repeat(prefix.length);
            return `${prefix}${lines.join('\\n' + indent)}\\n`;
        };"""

    new_format_indent = """        const formatIndent = (prefix, val) => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `${prefix}-\\n`;
            const lines = String(val).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) return `${prefix}-\\n`;
            if (lines.length === 1) return `${prefix}${lines[0]}\\n`;
            const leadingSpaces = (prefix.match(/^ +/) || [''])[0].length;
            const textPart = prefix.slice(leadingSpaces);
            const visualSpaces = Math.round(textPart.length * 1.42);
            const indent = ' '.repeat(leadingSpaces + visualSpaces);
            return `${prefix}${lines.join('\\n' + indent)}\\n`;
        };"""

    old_format_jenis = """        const formatJenis = (val, label = 'Jenis kerusakan') => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `    ${label} : -\\n`;
            const prefix = `    ${label} : `;
            const indent = ' '.repeat(prefix.length);
            const lines = String(val).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) return `${prefix}-\\n`;
            return `${prefix}${lines.join('\\n' + indent)}\\n`;
        };"""

    new_format_jenis = """        const formatJenis = (val, label = 'Jenis kerusakan') => {
            if (!val || val === '-' || val.trim().toLowerCase() === 'nihil') return `    ${label} : -\\n`;
            const prefix = `    ${label} : `;
            const lines = String(val).replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length === 0) return `${prefix}-\\n`;
            if (lines.length === 1) return `${prefix}${lines[0]}\\n`;
            const leadingSpaces = (prefix.match(/^ +/) || [''])[0].length;
            const textPart = prefix.slice(leadingSpaces);
            const visualSpaces = Math.round(textPart.length * 1.42);
            const indent = ' '.repeat(leadingSpaces + visualSpaces);
            return `${prefix}${lines.join('\\n' + indent)}\\n`;
        };"""

    if old_format_indent in content:
        content = content.replace(old_format_indent, new_format_indent)
        print("Updated formatIndent in staff_dashboard.html")
    else:
        print("Warning: old_format_indent not found in staff_dashboard.html")

    if old_format_jenis in content:
        content = content.replace(old_format_jenis, new_format_jenis)
        print("Updated formatJenis in staff_dashboard.html")
    else:
        print("Warning: old_format_jenis not found in staff_dashboard.html")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def update_staff_routes():
    path = 'app/routes/staff_routes.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_format_indent = """    def format_indent(prefix, val):
        if not val or val == '-' or str(val).lower() == 'nihil':
            return f"{prefix}-\\n"
        lines = [l.strip() for l in str(val).replace('\\r\\n', '\\n').replace('\\r', '\\n').split('\\n') if l.strip()]
        if not lines:
            return f"{prefix}-\\n"
        indent = " " * len(prefix)
        return f"{prefix}" + f"\\n{indent}".join(lines) + "\\n\""""

    new_format_indent = """    def format_indent(prefix, val):
        if not val or val == '-' or str(val).lower() == 'nihil':
            return f"{prefix}-\\n"
        lines = [l.strip() for l in str(val).replace('\\r\\n', '\\n').replace('\\r', '\\n').split('\\n') if l.strip()]
        if not lines:
            return f"{prefix}-\\n"
        if len(lines) == 1:
            return f"{prefix}{lines[0]}\\n"
        m = re.match(r'^( *)', prefix)
        leading_spaces = len(m.group(1)) if m else 0
        text_part = prefix[leading_spaces:]
        visual_spaces = round(len(text_part) * 1.42)
        indent = " " * (leading_spaces + visual_spaces)
        return f"{prefix}" + f"\\n{indent}".join(lines) + "\\n\""""

    old_damage_line = """    def format_damage_line(val, label="Jenis kerusakan"):
        if not val or val == '-' or str(val).lower() == 'nihil':
            return f"    {label} : -\\n"
        prefix = f"    {label} : "
        indent = " " * len(prefix)
        lines = [l.strip() for l in str(val).replace('\\r\\n', '\\n').replace('\\r', '\\n').split('\\n') if l.strip()]
        if not lines:
            return f"{prefix}-\\n"
        return f"{prefix}" + f"\\n{indent}".join(lines) + "\\n\""""

    new_damage_line = """    def format_damage_line(val, label="Jenis kerusakan"):
        if not val or val == '-' or str(val).lower() == 'nihil':
            return f"    {label} : -\\n"
        prefix = f"    {label} : "
        lines = [l.strip() for l in str(val).replace('\\r\\n', '\\n').replace('\\r', '\\n').split('\\n') if l.strip()]
        if not lines:
            return f"{prefix}-\\n"
        if len(lines) == 1:
            return f"{prefix}{lines[0]}\\n"
        m = re.match(r'^( *)', prefix)
        leading_spaces = len(m.group(1)) if m else 0
        text_part = prefix[leading_spaces:]
        visual_spaces = round(len(text_part) * 1.42)
        indent = " " * (leading_spaces + visual_spaces)
        return f"{prefix}" + f"\\n{indent}".join(lines) + "\\n\""""

    if old_format_indent in content:
        content = content.replace(old_format_indent, new_format_indent)
        print("Updated format_indent in staff_routes.py")
    else:
        print("Warning: old_format_indent not found in staff_routes.py")

    if old_damage_line in content:
        content = content.replace(old_damage_line, new_damage_line)
        print("Updated format_damage_line in staff_routes.py")
    else:
        print("Warning: old_damage_line not found in staff_routes.py")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_admin_dashboard()
    update_staff_dashboard()
    update_staff_routes()
    print("Completed fixing WhatsApp multiline indentation!")

