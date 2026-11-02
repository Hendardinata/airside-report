path = 'app/templates/admin_dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update config-view-header
old_header = """                    <div class="d-flex gap-2">
                        <button type="button" class="btn-outline-action" onclick="syncFromSheet()" title="Tarik perubahan kolom/baris dari Google Sheets">
                            <i class="fa-solid fa-arrows-rotate me-1 text-primary"></i> Tarik dari Spreadsheet
                        </button>
                    </div>"""

new_header = """                    <div class="d-flex gap-2 align-items-center flex-wrap">
                        <button type="button" class="btn-outline-action" onclick="syncFromSheet()" title="Tarik perubahan kolom/baris dari Google Sheets">
                            <i class="fa-solid fa-arrows-rotate me-1 text-primary"></i> Tarik dari Spreadsheet
                        </button>
                        <button type="button" class="vfb-btn-discard" onclick="discardSchemaChanges()">Batalkan Perubahan</button>
                        <button type="button" class="vfb-btn-save" id="vfbBtnSave" onclick="saveSchema()">Simpan Perubahan</button>
                    </div>"""

if old_header in content:
    content = content.replace(old_header, new_header)
    print("Updated header with buttons (LF)")
elif old_header.replace('\n', '\r\n') in content:
    content = content.replace(old_header.replace('\n', '\r\n'), new_header.replace('\n', '\r\n'))
    print("Updated header with buttons (CRLF)")
else:
    print("Error: old_header not found!")
    exit(1)

# 2. Remove bottom footer from renderVisualBuilder
old_footer = """                <!-- Sticky Action Footer -->
                <div class="vfb-sticky-footer" style="justify-content: flex-end;">
                    <div class="d-flex align-items-center gap-2">
                        <button type="button" class="vfb-btn-discard" onclick="discardSchemaChanges()">Batalkan Perubahan</button>
                        <button type="button" class="vfb-btn-save" id="vfbBtnSave" onclick="saveSchema()">Simpan Perubahan</button>
                    </div>
                </div>"""

if old_footer in content:
    content = content.replace(old_footer, "")
    print("Removed bottom footer from renderVisualBuilder (LF)")
elif old_footer.replace('\n', '\r\n') in content:
    content = content.replace(old_footer.replace('\n', '\r\n'), "")
    print("Removed bottom footer from renderVisualBuilder (CRLF)")
else:
    print("Error: old_footer not found!")
    exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Buttons moved to top header successfully!")
