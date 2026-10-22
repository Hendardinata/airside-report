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

    # Kelompokkan berdasarkan (airport, report_id)
    by_report = {}
    for n in notif_list:
        rid = n.get('report_id')
        apt = (n.get('airport') or '').upper()
        if rid:
            key = (apt, rid)
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
            # Notifikasi terbaru adalah revisi dari GM -> buang semua notifikasi pending untuk laporan ini
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

def create_notification(airport_code, recipient_role, notif_type, title, message, report_id=None, tanggal=None, notes=None):
    """
    Menambahkan notifikasi baru.
    recipient_role: 'staff', 'gm', atau 'all'
    notif_type: 'revisi', 'approved', 'pending', 'info'
    """
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    notif = {
        "id": f"notif_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
        "airport": (airport_code or 'LOP').upper(),
        "recipient_role": recipient_role,
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
            if notif_type == 'revisi':
                # Saat GM memberi revisi: buang notifikasi pending ('Menunggu GM') untuk laporan ini
                data = [n for n in data if not (n.get('report_id') == report_id and n.get('notif_type') == 'pending')]
            elif notif_type == 'approved':
                # Saat GM menyetujui: buang notifikasi pending dan revisi untuk laporan ini
                data = [n for n in data if not (n.get('report_id') == report_id and n.get('notif_type') in ('pending', 'revisi'))]
            elif notif_type == 'pending':
                # Saat Petugas mengirim ulang revisi: buang notifikasi revisi lama dan pending lama
                data = [n for n in data if not (n.get('report_id') == report_id and n.get('notif_type') in ('revisi', 'pending'))]

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

def get_notifications(airport_code, role='staff'):
    """
    Mengambil daftar notifikasi untuk airport dan role tertentu.
    Juga menyinkronkan status revisi / pending dari staging sheet jika ada,
    dan memastikan notifikasi yang usang (superseded) atau laporannya sudah dihapus
    dari Staging tidak lagi ditampilkan.
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
    filtered = []
    for n in raw_list:
        if n.get('airport', '').upper() == airport:
            r = n.get('recipient_role', 'all')
            if r in (role, 'all'):
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
                if rid and rid not in existing_revisi_rids and role in ('staff', 'all'):
                    # Auto generate notification for active revision
                    auto_notif = create_notification(
                        airport_code=airport,
                        recipient_role='staff',
                        notif_type='revisi',
                        title='Catatan Koreksi GM',
                        message=f'Pesan GM: "{srep.get("catatan_gm") or "Periksa kembali data inspeksi."}"',
                        report_id=rid,
                        tanggal=srep.get('tanggal'),
                        notes=srep.get('catatan_gm')
                    )
                    filtered.insert(0, auto_notif)
                    existing_revisi_rids.add(rid)

        # Buang notifikasi 'pending' jika report_id tersebut sudah ada tanggapan GM (revisi/approved) atau di staging statusnya REVISI
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

def mark_all_as_read(airport_code, role='staff'):
    airport = (airport_code or 'LOP').upper()
    with _lock:
        data = _load_raw_notifications()
        for n in data:
            if n.get('airport', '').upper() == airport:
                r = n.get('recipient_role', 'all')
                if r in (role, 'all'):
                    n['is_read'] = True
        _save_raw_notifications(data)
