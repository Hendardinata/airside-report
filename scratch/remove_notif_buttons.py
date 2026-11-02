import os

path = 'app/templates/admin_dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update .notif-item-desc CSS margin
old_css = """.notif-item-desc {
        font-size: 0.74rem;
        color: #64748b;
        line-height: 1.35;
        margin-bottom: 0.45rem;
    }"""

new_css = """.notif-item-desc {
        font-size: 0.74rem;
        color: #64748b;
        line-height: 1.35;
        margin-bottom: 0;
    }"""

if old_css in content:
    content = content.replace(old_css, new_css, 1)
    print("Updated .notif-item-desc CSS")
else:
    print("Warning: old_css not found")

# 2. Remove buttons in notification template
old_js = """                if (info.is_submitted) {
                    html += `
                        <div class="notif-item">
                            <i class="fa-solid fa-circle-check notif-item-icon" style="color: #00B7CD;"></i>
                            <div class="notif-item-content">
                                <div class="notif-item-title">
                                    <span><strong>${code}</strong> - ${meta.city}</span>
                                    <span class="notif-pill success">Sudah Mengirim</span>
                                </div>
                                <div class="notif-item-desc">Laporan harian terverifikasi (PCI Runway: <strong>${info.pci || '-'}</strong>).</div>
                                <div class="notif-item-actions">
                                    <button type="button" class="notif-mini-btn" onclick="openBranchSuccessSheet('${code}')">
                                        <i class="fa-solid fa-eye"></i> Detail
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="notif-item unread">
                            <i class="fa-solid fa-circle-exclamation notif-item-icon text-warning"></i>
                            <div class="notif-item-content">
                                <div class="notif-item-title">
                                    <span><strong>${code}</strong> - ${meta.city}</span>
                                    <span class="notif-pill warning">Belum Mengirim</span>
                                </div>
                                <div class="notif-item-desc">Laporan tanggal ${dateStr} belum diinput ke sistem.</div>
                                <div class="notif-item-actions">
                                    <button type="button" class="notif-mini-btn btn-gm" onclick="contactGMWhatsApp('${code}')" title="Hubungi General Manager ${code}">
                                        <i class="fa-solid fa-user-tie"></i> WhatsApp GM
                                    </button>
                                    <button type="button" class="notif-mini-btn" onclick="remindPicWhatsApp('${code}', '${info.pic_phone || ''}', '${meta.city}', '${dateStr}')" title="WhatsApp PIC">
                                        <i class="fa-brands fa-whatsapp text-success"></i> PIC
                                    </button>
                                    <button type="button" class="notif-mini-btn" onclick="syncRekap('${code}')" title="Tarik data sheet">
                                        <i class="fa-solid fa-cloud-arrow-down text-primary"></i> Tarik
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }"""

new_js = """                if (info.is_submitted) {
                    html += `
                        <div class="notif-item">
                            <i class="fa-solid fa-circle-check notif-item-icon" style="color: #00B7CD;"></i>
                            <div class="notif-item-content">
                                <div class="notif-item-title">
                                    <span><strong>${code}</strong> - ${meta.city}</span>
                                    <span class="notif-pill success">Sudah Mengirim</span>
                                </div>
                                <div class="notif-item-desc">Laporan harian terverifikasi (PCI Runway: <strong>${info.pci || '-'}</strong>).</div>
                            </div>
                        </div>
                    `;
                } else {
                    html += `
                        <div class="notif-item unread">
                            <i class="fa-solid fa-circle-exclamation notif-item-icon text-warning"></i>
                            <div class="notif-item-content">
                                <div class="notif-item-title">
                                    <span><strong>${code}</strong> - ${meta.city}</span>
                                    <span class="notif-pill warning">Belum Mengirim</span>
                                </div>
                                <div class="notif-item-desc">Laporan tanggal ${dateStr} belum diinput ke sistem.</div>
                            </div>
                        </div>
                    `;
                }"""

if old_js in content:
    content = content.replace(old_js, new_js, 1)
    print("Removed notification action buttons successfully!")
else:
    print("Warning: old_js not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

