import os

def update_admin_dashboard():
    path = r'airside-report-flask/app/templates/admin_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update docSection with double newlines
    old_doc = """                    const docUrl = `${window.location.origin}/dokumentasi/${res.date}`;
                    const docSection = totalDocPhotos > 0
                        ? `\\nLampiran Dokumentasi Foto Lapangan (${totalDocPhotos} Foto):\\n${docUrl}\\n\\n`
                        : '\\n';"""

    new_doc = """                    const docUrl = `${window.location.origin}/dokumentasi/${res.date}`;
                    const docSection = totalDocPhotos > 0
                        ? `\\n\\nLampiran Dokumentasi Foto Lapangan (${totalDocPhotos} Foto):\\n\\n${docUrl}\\n\\n`
                        : '\\n\\n';"""

    if old_doc in content:
        content = content.replace(old_doc, new_doc, 1)
        print("Updated docSection in admin_dashboard.html")
    else:
        print("Warning: old_doc not found")

    # 2. Update contactGMWhatsApp
    old_gm = """        const waUrl = `https://wa.me/${cleanNum}?text=${encodeURIComponent(waMsg)}`;
        window.open(waUrl, '_blank');"""

    new_gm = """        if (typeof window.openWhatsAppDirect === 'function') {
            window.openWhatsAppDirect(cleanNum, waMsg);
        } else {
            window.open(`https://wa.me/${cleanNum}?text=${encodeURIComponent(waMsg)}`, '_blank');
        }"""

    if old_gm in content:
        content = content.replace(old_gm, new_gm, 1)
        print("Updated contactGMWhatsApp in admin_dashboard.html")
    else:
        print("Warning: old_gm not found")

    # 3. Update staff direct WA
    old_staff = """        const waMsg = `Halo tim Fasilitas Sisi Udara ${code} - ${branchCity}, mohon segera mengisi laporan harian Airside untuk tanggal *${dateStr}* melalui Dashboard Petugas. Terima kasih.`;
        const waUrl = `https://wa.me/${cleanNum}?text=${encodeURIComponent(waMsg)}`;
        window.open(waUrl, '_blank');"""

    new_staff = """        const waMsg = `Halo tim Fasilitas Sisi Udara ${code} - ${branchCity}, mohon segera mengisi laporan harian Airside untuk tanggal *${dateStr}* melalui Dashboard Petugas. Terima kasih.`;
        if (typeof window.openWhatsAppDirect === 'function') {
            window.openWhatsAppDirect(cleanNum, waMsg);
        } else {
            window.open(`https://wa.me/${cleanNum}?text=${encodeURIComponent(waMsg)}`, '_blank');
        }"""

    if old_staff in content:
        content = content.replace(old_staff, new_staff, 1)
        print("Updated staff direct WA in admin_dashboard.html")
    else:
        print("Warning: old_staff not found")

    # 4. Update kirimWhatsAppDeputy
    old_deputy = """        let cleanNum = numbers[0];
        if (cleanNum.startsWith('0')) cleanNum = '62' + cleanNum.substring(1);
        const url = `https://wa.me/${cleanNum}?text=${encodeURIComponent(text)}`;

        const promptAdminFollowup = () => {
            if (adminPhone && adminPhone.trim()) {
                setTimeout(() => {
                    Swal.fire({
                        title: 'Kirim ke Admin?',
                        text: 'Apakah Anda juga ingin mengirim laporan ini ke nomor Admin Regional?',
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: 'Ya, Kirim ke Admin',
                        cancelButtonText: 'Tidak',
                        confirmButtonColor: '#00B7CD'
                    }).then((result) => {
                        if (result.isConfirmed) {
                            let cleanAdmin = adminPhone.trim().replace(/\\D/g, '');
                            if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                            const adminUrl = `https://wa.me/${cleanAdmin}?text=${encodeURIComponent(text)}`;
                            window.open(adminUrl, '_blank');
                        }
                    });
                }, 1000);
            }
        };

        window.open(url, '_blank');
        promptAdminFollowup();"""

    new_deputy = """        let cleanNum = numbers[0];
        if (cleanNum.startsWith('0')) cleanNum = '62' + cleanNum.substring(1);

        const promptAdminFollowup = () => {
            if (adminPhone && adminPhone.trim()) {
                setTimeout(() => {
                    Swal.fire({
                        title: 'Kirim ke Admin?',
                        text: 'Apakah Anda juga ingin mengirim laporan ini ke nomor Admin Regional?',
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonText: 'Ya, Kirim ke Admin',
                        cancelButtonText: 'Tidak',
                        confirmButtonColor: '#00B7CD'
                    }).then((result) => {
                        if (result.isConfirmed) {
                            let cleanAdmin = adminPhone.trim().replace(/\\D/g, '');
                            if (typeof window.openWhatsAppDirect === 'function') {
                                window.openWhatsAppDirect(cleanAdmin, text);
                            } else {
                                if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                                window.open(`https://wa.me/${cleanAdmin}?text=${encodeURIComponent(text)}`, '_blank');
                            }
                        }
                    });
                }, 1000);
            }
        };

        if (typeof window.openWhatsAppDirect === 'function') {
            window.openWhatsAppDirect(cleanNum, text);
        } else {
            window.open(`https://wa.me/${cleanNum}?text=${encodeURIComponent(text)}`, '_blank');
        }
        promptAdminFollowup();"""

    if old_deputy in content:
        content = content.replace(old_deputy, new_deputy, 1)
        print("Updated kirimWhatsAppDeputy in admin_dashboard.html")
    else:
        print("Warning: old_deputy not found")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_gm_dashboard():
    path = r'airside-report-flask/app/templates/gm_dashboard.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Line ~6772
    old1 = """                                            let cleanAdmin = res.admin_phone.replace(/\\D/g, '');
                                            if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                                            window.open(`https://wa.me/${cleanAdmin}?text=${encodeURIComponent(res.admin_message)}`, '_blank');"""
    new1 = """                                            let cleanAdmin = res.admin_phone.replace(/\\D/g, '');
                                            if (typeof window.openWhatsAppDirect === 'function') {
                                                window.openWhatsAppDirect(cleanAdmin, res.admin_message);
                                            } else {
                                                if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                                                window.open(`https://wa.me/${cleanAdmin}?text=${encodeURIComponent(res.admin_message)}`, '_blank');
                                            }"""

    # 2. Line ~6939
    old2 = """                                let cleanPhone = res.pic_phone.replace(/\\D/g, '');
                                if (cleanPhone.startsWith('0')) cleanPhone = '62' + cleanPhone.substring(1);
                                window.open(`https://wa.me/${cleanPhone}?text=${encodeURIComponent(res.staff_message)}`, '_blank');"""
    new2 = """                                let cleanPhone = res.pic_phone.replace(/\\D/g, '');
                                if (typeof window.openWhatsAppDirect === 'function') {
                                    window.openWhatsAppDirect(cleanPhone, res.staff_message);
                                } else {
                                    if (cleanPhone.startsWith('0')) cleanPhone = '62' + cleanPhone.substring(1);
                                    window.open(`https://wa.me/${cleanPhone}?text=${encodeURIComponent(res.staff_message)}`, '_blank');
                                }"""

    # 3. Line ~7049
    old3 = """                                        let cleanAdmin = res.admin_phone.replace(/\\D/g, '');
                                        if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                                        window.open(`https://wa.me/${cleanAdmin}?text=${encodeURIComponent(res.admin_message)}`, '_blank');"""
    new3 = """                                        let cleanAdmin = res.admin_phone.replace(/\\D/g, '');
                                        if (typeof window.openWhatsAppDirect === 'function') {
                                            window.openWhatsAppDirect(cleanAdmin, res.admin_message);
                                        } else {
                                            if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                                            window.open(`https://wa.me/${cleanAdmin}?text=${encodeURIComponent(res.admin_message)}`, '_blank');
                                        }"""

    if old1 in content:
        content = content.replace(old1, new1, 1)
        print("Updated GM dashboard item 1")
    else:
        print("Warning: GM item 1 not found")

    if old2 in content:
        content = content.replace(old2, new2, 1)
        print("Updated GM dashboard item 2")
    else:
        print("Warning: GM item 2 not found")

    if old3 in content:
        content = content.replace(old3, new3, 1)
        print("Updated GM dashboard item 3")
    else:
        print("Warning: GM item 3 not found")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_wizard_js():
    path = r'airside-report-flask/app/static/js/wizard.js'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_wiz = """                            let text = data.dh_message || data.gm_message || `Halo Department Head, Laporan Harian Airside baru saja diajukan dari cabang ${data.airport_code}. Mohon direview di portal.`;
                            let cleanDH = phone.replace(/\\D/g, '');
                            if (cleanDH.startsWith('0')) cleanDH = '62' + cleanDH.substring(1);
                            window.open(`https://wa.me/${cleanDH}?text=${encodeURIComponent(text)}`, '_blank');"""

    new_wiz = """                            let text = data.dh_message || data.gm_message || `Halo Department Head, Laporan Harian Airside baru saja diajukan dari cabang ${data.airport_code}. Mohon direview di portal.`;
                            let cleanDH = phone.replace(/\\D/g, '');
                            if (typeof window.openWhatsAppDirect === 'function') {
                                window.openWhatsAppDirect(cleanDH, text);
                            } else {
                                if (cleanDH.startsWith('0')) cleanDH = '62' + cleanDH.substring(1);
                                window.open(`https://wa.me/${cleanDH}?text=${encodeURIComponent(text)}`, '_blank');
                            }"""

    if old_wiz in content:
        content = content.replace(old_wiz, new_wiz, 1)
        print("Updated wizard.js")
    else:
        print("Warning: old_wiz not found in wizard.js")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_admin_dashboard()
    update_gm_dashboard()
    update_wizard_js()

