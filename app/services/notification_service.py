import os
import json
import uuid
from datetime import datetime
import threading

NOTIF_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'notifications.json')
_lock = threading.Lock()

def _load_raw_notifications():
    if not os.path.exists(NOTIF_FILE):
        return []
    try:
        with open(NOTIF_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading notifications.json: {e}")
        return []

def _save_raw_notifications(data):
    try:
        with open(NOTIF_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving notifications.json: {e}")

def _clean_superseded_notifications(notif_list):
    """
    Menghilangkan notifikasi yang telah usang/useless (superseded) per report_id:
    - Jika report_id sudah ada tanggapan GM 'revisi' (catatan GM):
      buang notifikasi 'pending' ('Menunggu GM') agar petugas tidak bingung.
    - Jika report_id sudah 'approved' (disetujui):
      buang notifikasi 'pending' dan 'revisi' untuk report_id tersebut.
    - Jika ada 'pending' baru (hasil perbaikan petugas yang dikirim ulang):
      buang notifikasi 'revisi' lama untuk report_id tersebut.
    """
    if not notif_list:
        return []

    # Kelompokkan berdasarkan (airport, report_id, role_norm, recipient_username)
    by_report = {}
    for n in notif_list:
        rid = n.get('report_id')
        apt = (n.get('airport') or '').upper()
        r_role = (n.get('recipient_role') or '').strip().lower()
        r_norm = 'dh' if r_role in ('dh', 'gm') else r_role
        recip_u = (n.get('recipient_username') or '').strip().lower()
        if rid:
            key = (apt, rid, r_norm, recip_u)
            if key not in by_report:
                by_report[key] = []
            by_report[key].append(n)

    ids_to_remove = set()

    for key, items in by_report.items():
        # Urutkan dari yang terbaru ke terlama berdasarkan created_at
        items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        has_approved = any(i.get('notif_type') == 'approved' for i in items)
        if has_approved:
            for i in items:
                if i.get('notif_type') in ('pending', 'revisi'):
                    ids_to_remove.add(i.get('id'))
            continue

        latest_item = items[0]
        latest_type = latest_item.get('notif_type')

        if latest_type == 'revisi':
            # Notifikasi terbaru adalah revisi dari GM/DH -> buang notifikasi pending untuk laporan ini bagi role tersebut
            for i in items:
                if i.get('notif_type') == 'pending':
                    ids_to_remove.add(i.get('id'))
        elif latest_type == 'pending':
            # Notifikasi terbaru adalah pengajuan/perbaikan petugas -> buang revisi lama yang sudah diselesaikan
            for i in items[1:]:
                if i.get('notif_type') == 'revisi':
                    ids_to_remove.add(i.get('id'))

    cleaned = [n for n in notif_list if n.get('id') not in ids_to_remove]
    return cleaned

def create_notification(airport_code, recipient_role, notif_type, title, message, report_id=None, tanggal=None, notes=None, recipient_username=None, sender_username=None, sender_name=None):
    """
    Menambahkan notifikasi baru.
    recipient_role: 'staff', 'dh', 'gm', atau 'all'
    recipient_username: opsional username akun staf spesifik (misal 'lop_hendar')
    sender_username: opsional username akun pengirim
    sender_name: opsional nama akun pengirim
    notif_type: 'revisi', 'approved', 'pending', 'info'
    """
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    clean_recip_u = (recipient_username or '').strip().lower()
    notif = {
        "id": f"notif_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
        "airport": (airport_code or 'LOP').upper(),
        "recipient_role": recipient_role,
        "recipient_username": clean_recip_u,
        "sender_username": (sender_username or '').strip().lower(),
        "sender_name": sender_name or '',
        "notif_type": notif_type,
        "title": title,
        "message": message,
        "report_id": report_id or "",
        "tanggal": tanggal or "",
        "notes": notes or "",
        "created_at": now_str,
        "is_read": False
    }

    with _lock:
        data = _load_raw_notifications()

        # Otomatis buang notifikasi lama yang statusnya digantikan oleh aksi baru ini
        if report_id:
            def matches_recipient(existing_n):
                # Cocokkan apakah notifikasi ditujukan ke role dan penerima yang sama
                ex_role = (existing_n.get('recipient_role') or '').strip().lower()
                cur_role = (recipient_role or '').strip().lower()
                ex_norm = 'dh' if ex_role in ('dh', 'gm') else ex_role
                cur_norm = 'dh' if cur_role in ('dh', 'gm') else cur_role
                if ex_norm != cur_norm:
                    return False
                ex_u = (existing_n.get('recipient_username') or '').strip().lower()
                return not clean_recip_u or not ex_u or ex_u == clean_recip_u

            if notif_type == 'revisi':
                # Saat GM/DH memberi revisi: buang notifikasi pending untuk laporan ini bagi staf bersangkutan
                data = [n for n in data if not (n.get('report_id') == report_id and n.get('notif_type') == 'pending' and matches_recipient(n))]
            elif notif_type == 'approved':
                # Saat GM/DH menyetujui: buang notifikasi pending dan revisi untuk laporan ini bagi role tersebut
                data = [n for n in data if not (n.get('report_id') == report_id and n.get('notif_type') in ('pending', 'revisi') and matches_recipient(n))]
            elif notif_type == 'pending':
                # Saat Petugas mengirim ulang: buang revisi lama dan pending lama bagi role tersebut
                data = [n for n in data if not (n.get('report_id') == report_id and n.get('notif_type') in ('revisi', 'pending') and matches_recipient(n))]

        data.insert(0, notif)
        data = _clean_superseded_notifications(data)
        if len(data) > 100:
            data = data[:100]
        _save_raw_notifications(data)

    return notif

def delete_notifications_by_report_id(airport_code, report_id):
    """
    Menghapus seluruh notifikasi terkait report_id tertentu
    (misal saat laporan dihapus dari Staging oleh GM atau dibatalkan).
    """
    if not report_id:
        return
    airport = (airport_code or '').upper()
    with _lock:
        data = _load_raw_notifications()
        initial_len = len(data)
        data = [
            n for n in data
            if not (
                n.get('report_id') == report_id and
                (not airport or n.get('airport', '').upper() == airport)
            )
        ]
        if len(data) != initial_len:
            _save_raw_notifications(data)

def get_notifications(airport_code, role='staff', username=None):
    """
    Mengambil daftar notifikasi untuk airport dan role tertentu.
    Jika role == 'staff' dan username diberikan, hanya mengambil notifikasi yang:
    - Ditujukan spesifik ke username tersebut, ATAU
    - Merupakan notifikasi broadcast untuk seluruh staf bandara (recipient_username kosong).
    """
    airport = (airport_code or 'LOP').upper()
    with _lock:
        raw_list = _load_raw_notifications()

    # Bersihkan notifikasi usang/superseded di level database
    cleaned_list = _clean_superseded_notifications(raw_list)
    if len(cleaned_list) != len(raw_list):
        with _lock:
            _save_raw_notifications(cleaned_list)
        raw_list = cleaned_list

    # Filter untuk bandara dan role terkait
    target_roles = {'all', role}
    if role in ('dh', 'gm'):
        target_roles.update({'dh', 'gm'})

    u_filter = (username or '').strip().lower()

    filtered = []
    for n in raw_list:
        if n.get('airport', '').upper() == airport:
            r = n.get('recipient_role', 'all')
            if r in target_roles:
                recip_user = (n.get('recipient_username') or '').strip().lower()
                # Jika filtering role staff:
                if role == 'staff':
                    # Jika notifikasi ditargetkan ke username tertentu:
                    if recip_user and u_filter and recip_user != u_filter:
                        continue # Notifikasi untuk staf lain, lewati!
                filtered.append(n)

    # Sinkronisasi dengan staging reports aktif
    try:
        from app.services.staging_service import get_staging_reports
        active_staging = get_staging_reports(airport)
        active_staging_ids = {srep.get('report_id') for srep in active_staging if srep.get('report_id')}
        staging_status_map = {srep.get('report_id'): srep.get('status') for srep in active_staging if srep.get('report_id')}
        
        # Cek jika ada laporan REVISI aktif yang belum tercatat di notifikasi
        existing_revisi_rids = {n.get('report_id') for n in filtered if n.get('notif_type') == 'revisi'}
        for srep in active_staging:
            if srep.get('status') == 'REVISI':
                rid = srep.get('report_id')
                rep_user = (srep.get('submitted_by_username') or '').strip().lower()
                if rid and rid not in existing_revisi_rids and role in ('staff', 'all'):
                    # Jika filter username aktif, hanya generate jika cocok
                    if u_filter and rep_user and rep_user != u_filter:
                        continue
                    # Auto generate notification for active revision
                    auto_notif = create_notification(
                        airport_code=airport,
                        recipient_role='staff',
                        recipient_username=rep_user or u_filter,
                        notif_type='revisi',
                        title='Catatan Koreksi DH',
                        message=f'Pesan DH: "{srep.get("catatan_gm") or "Periksa kembali data inspeksi."}"',
                        report_id=rid,
                        tanggal=srep.get('tanggal'),
                        notes=srep.get('catatan_gm')
                    )
                    filtered.insert(0, auto_notif)
                    existing_revisi_rids.add(rid)

        # Buang notifikasi 'pending' jika report_id tersebut sudah ada tanggapan DH (revisi/approved) atau di staging statusnya REVISI
        # DAN buang notifikasi pending/revisi yang laporannya SUDAH DIHAPUS dari Staging!
        final_filtered = []
        orphan_notif_ids = set()

        for n in filtered:
            rid = n.get('report_id')
            ntype = n.get('notif_type')

            # Jika notifikasi pending atau revisi, periksa apakah laporannya masih aktif di staging
            if rid and ntype in ('pending', 'revisi'):
                if rid not in active_staging_ids:
                    # Laporan sudah dihapus dari staging, buang notifikasinya!
                    orphan_notif_ids.add(n.get('id'))
                    continue
                if ntype == 'pending':
                    # Jika status di staging sudah REVISI
                    if staging_status_map.get(rid) == 'REVISI':
                        continue
                    # Jika ada notifikasi revisi atau approved untuk report ini
                    if rid in existing_revisi_rids:
                        continue

            final_filtered.append(n)
        filtered = final_filtered

        # Bersihkan notifikasi orphan yang terdeteksi dari penyimpanan database
        if orphan_notif_ids:
            with _lock:
                current_raw = _load_raw_notifications()
                new_raw = [n for n in current_raw if n.get('id') not in orphan_notif_ids]
                if len(new_raw) != len(current_raw):
                    _save_raw_notifications(new_raw)

    except Exception as e:
        print(f"Warning sync staging to notifications: {e}")

    # Urutkan berdasarkan created_at descending
    filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return filtered

def mark_notification_as_read(notif_id):
    with _lock:
        data = _load_raw_notifications()
        for n in data:
            if n.get('id') == notif_id:
                n['is_read'] = True
                break
        _save_raw_notifications(data)

def mark_all_as_read(airport_code, role='staff', username=None):
    airport = (airport_code or 'LOP').upper()
    target_roles = {'all', role}
    if role in ('dh', 'gm'):
        target_roles.update({'dh', 'gm'})
    u_filter = (username or '').strip().lower()
    with _lock:
        data = _load_raw_notifications()
        for n in data:
            if n.get('airport', '').upper() == airport:
                r = n.get('recipient_role', 'all')
                if r in target_roles:
                    recip_user = (n.get('recipient_username') or '').strip().lower()
                    if role == 'staff' and u_filter:
                        if recip_user and recip_user != u_filter:
                            continue
                    n['is_read'] = True
        _save_raw_notifications(data)
