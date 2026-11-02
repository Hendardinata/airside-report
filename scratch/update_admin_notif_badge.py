path = 'app/templates/admin_dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update CSS
old_css = """    .notif-badge-dot {
        position: absolute;
        top: 8px;
        right: 9px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #ef4444;
        border: 2px solid #ffffff;
    }

    .notif-badge-dot.success {
        background-color: #22c55e;
    }

    .notif-badge-dot.warning {
        background-color: #ea580c;
    }"""

new_css = """    .notif-badge-count {
        position: absolute;
        top: -3px;
        right: -3px;
        min-width: 19px;
        height: 19px;
        padding: 0 4px;
        border-radius: 10px;
        background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
        color: #ffffff;
        font-size: 0.68rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #ffffff;
        box-shadow: 0 2px 6px rgba(234, 88, 12, 0.4);
        font-family: 'Outfit', sans-serif;
        line-height: 1;
        box-sizing: border-box;
        transition: all 0.2s ease;
    }

    .notif-badge-count.success {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        box-shadow: 0 2px 6px rgba(16, 185, 129, 0.4);
    }

    .notif-badge-dot {
        display: none !important;
    }"""

if old_css in content:
    content = content.replace(old_css, new_css)
    print("Replaced CSS successfully")
else:
    print("Warning: old_css not found")

# 2. Update HTML Bell Button
old_html = """                        <button type="button" class="topbar-notif-btn" id="topbarNotifBtn" title="Status Notifikasi Laporan Cabang" onclick="toggleNotifDropdown(event)">
                            <i class="fa-regular fa-bell"></i>
                            <span class="notif-badge-dot warning" id="notifBadgeDot"></span>
                        </button>"""

new_html = """                        <button type="button" class="topbar-notif-btn" id="topbarNotifBtn" title="Status Notifikasi Laporan Cabang" onclick="toggleNotifDropdown(event)">
                            <i class="fa-regular fa-bell"></i>
                            <span class="notif-badge-count" id="notifBadgeCount">4</span>
                        </button>"""

if old_html in content:
    content = content.replace(old_html, new_html)
    print("Replaced HTML successfully")
else:
    print("Warning: old_html not found")

# 3. Update JavaScript updateNotificationCenter
old_js = """        if (notifBadgeDot) {
            notifBadgeDot.className = pendingCount > 0 ? 'notif-badge-dot warning' : 'notif-badge-dot success';
        }"""

new_js = """        const notifBadgeCount = document.getElementById('notifBadgeCount');
        if (notifBadgeCount) {
            if (pendingCount > 0) {
                notifBadgeCount.className = 'notif-badge-count';
                notifBadgeCount.textContent = pendingCount;
                notifBadgeCount.style.display = 'flex';
                notifBadgeCount.title = `${pendingCount} bandara belum mengirim laporan`;
            } else {
                notifBadgeCount.className = 'notif-badge-count success';
                notifBadgeCount.innerHTML = '<i class="fa-solid fa-check" style="font-size: 0.58rem;"></i>';
                notifBadgeCount.style.display = 'flex';
                notifBadgeCount.title = 'Seluruh bandara sudah mengirim laporan';
            }
        }
        if (notifBadgeDot) {
            notifBadgeDot.style.display = 'none';
        }"""

if old_js in content:
    content = content.replace(old_js, new_js)
    print("Replaced JavaScript successfully")
else:
    print("Warning: old_js not found")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done updating admin notification badge!")
