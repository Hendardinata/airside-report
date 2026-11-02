path = 'app/templates/admin_dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                <!-- Sticky Action Footer -->
                <div class="vfb-sticky-footer">
                    <div id="vfbStatusIndicator" class="vfb-footer-status">
                        ${isSchemaDirty ? `
                            <span class="vfb-dot-amber"></span>
                            <span>Perubahan belum disimpan</span>
                        ` : `
                            <i class="fa-solid fa-circle-check text-success"></i>
                            <span>Semua perubahan tersimpan</span>
                        `}
                    </div>
                    <div class="vfb-footer-right">
                        <div class="d-flex align-items-center gap-2">
                            <button type="button" class="vfb-btn-discard" onclick="discardSchemaChanges()">Batalkan Perubahan</button>
                            <button type="button" class="vfb-btn-save" id="vfbBtnSave" onclick="saveSchema()">Simpan Perubahan</button>
                        </div>
                        <div class="vfb-footer-help">Setelah disimpan, formulir petugas dan susunan kolom spreadsheet akan diperbarui.</div>
                    </div>
                </div>"""

replacement = """                <!-- Sticky Action Footer -->
                <div class="vfb-sticky-footer" style="justify-content: flex-end;">
                    <div class="d-flex align-items-center gap-2">
                        <button type="button" class="vfb-btn-discard" onclick="discardSchemaChanges()">Batalkan Perubahan</button>
                        <button type="button" class="vfb-btn-save" id="vfbBtnSave" onclick="saveSchema()">Simpan Perubahan</button>
                    </div>
                </div>"""

# Handle both CRLF and LF
if target in content:
    content = content.replace(target, replacement)
    print("Found exact target (LF)")
elif target.replace('\n', '\r\n') in content:
    content = content.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'))
    print("Found exact target (CRLF)")
else:
    print("Error: target not found!")
    exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Successfully removed footer status indicator and help text!")
