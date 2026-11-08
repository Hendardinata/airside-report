import re
import uuid
from datetime import datetime
import threading
from app.models.db import get_db

_lock = threading.Lock()

def _row_to_notif(row):
    if not row:
        return None
    return {
        "id": row['id'],
        "airport": (row['airport'] or '').upper(),
        "recipient_role": (row['recipient_role'] or '').lower(),
        "recipient_username": (row['recipient_username'] or '').lower(),
        "sender_username": row['sender_username'] or '',
        "sender_name": row['sender_name'] or '',
        "notif_type": row['notif_type'] or 'info',
        "title": row['title'] or '',
        "message": row['message'] or '',
        "report_id": row['report_id'] or '',
        "tanggal": row['tanggal'] or '',
        "notes": row['notes'] or '',
        "created_at": row['created_at'] or '',
        "is_read": bool(row['is_read'])
    }

def _load_raw_notifications():
    """Memuat seluruh baris notifikasi dari database SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC;")
        return [_row_to_notif(r) for r in cursor.fetchall()]

def _save_raw_notifications(data):
    """Menyimpan list notifikasi ke database SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notifications;")
        for n in data:
            cursor.execute("""
            INSERT INTO notifications (
                id, airport, recipient_role, recipient_username, sender_username, sender_name,
                notif_type, title, message, report_id, tanggal, notes, created_at, is_read
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                n.get('id'),
                (n.get('airport') or '').upper(),
                (n.get('recipient_role') or '').lower(),
                (n.get('recipient_username') or '').lower(),
                n.get('sender_username', ''),
                n.get('sender_name', ''),
                n.get('notif_type', 'info'),
                n.get('title', ''),
                n.get('message', ''),
                n.get('report_id', ''),
                n.get('tanggal', ''),
                n.get('notes', ''),
                n.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                1 if n.get('is_read') else 0
            ))

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
        items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        has_approved = any(i.get('notif_type') == 'approved' for i in items)
        if has_approved:
            for i in items:
                if i.get('notif_type') in ('pending', 'revisi'):
                    ids_to_remove.add(i.get('id'))
            continue

        latest_type = items[0].get('notif_type')
        if latest_type == 'revisi':
            for i in items:
                if i.get('notif_type') == 'pending':
                    ids_to_remove.add(i.get('id'))
        elif latest_type == 'pending':
            for i in items[1:]:
                if i.get('notif_type') == 'revisi':
                    ids_to_remove.add(i.get('id'))

    cleaned = [n for n in notif_list if n.get('id') not in ids_to_remove]
    return cleaned

def create_notification(airport_code, recipient_role, notif_type, title, message, report_id=None, tanggal=None, notes=None, recipient_username=None, sender_username=None, sender_name=None):
    """
    Menambahkan notifikasi baru ke database SQLite secara atomic.
    """
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    clean_recip_u = (recipient_username or '').strip().lower()
    notif_id = f"notif_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    airport = (airport_code or 'LOP').upper()
    
    notif = {
        "id": notif_id,
        "airport": airport,
        "recipient_role": (recipient_role or 'staff').lower(),
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
        with get_db() as conn:
            cursor = conn.cursor()
            # 1. Hapus superseded notifications untuk report_id ini jika ada
            if report_id:
                if notif_type == 'revisi':
                    cursor.execute("""
                    DELETE FROM notifications 
                    WHERE report_id = ? AND UPPER(airport) = ? AND notif_type = 'pending';
                    """, (report_id, airport))
                elif notif_type == 'approved':
                    cursor.execute("""
                    DELETE FROM notifications 
                    WHERE report_id = ? AND UPPER(airport) = ? AND notif_type IN ('pending', 'revisi');
                    """, (report_id, airport))
                elif notif_type == 'pending':
                    cursor.execute("""
                    DELETE FROM notifications 
                    WHERE report_id = ? AND UPPER(airport) = ? AND notif_type IN ('pending', 'revisi');
                    """, (report_id, airport))

            # 2. Insert notifikasi baru
            cursor.execute("""
            INSERT OR REPLACE INTO notifications (
                id, airport, recipient_role, recipient_username, sender_username, sender_name,
                notif_type, title, message, report_id, tanggal, notes, created_at, is_read
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                notif["id"],
                notif["airport"],
                notif["recipient_role"],
                notif["recipient_username"],
                notif["sender_username"],
                notif["sender_name"],
                notif["notif_type"],
                notif["title"],
                notif["message"],
                notif["report_id"],
                notif["tanggal"],
                notif["notes"],
                notif["created_at"],
                0
            ))

            # 3. Pangkas notifikasi lama jika lebih dari 150
            cursor.execute("""
            DELETE FROM notifications 
            WHERE id NOT IN (
                SELECT id FROM notifications ORDER BY created_at DESC LIMIT 150
            );
            """)

    return notif

def delete_notifications_by_report_id(airport_code, report_id):
    """
    Menghapus seluruh notifikasi terkait report_id tertentu dari SQLite.
    """
    if not report_id:
        return
    airport = (airport_code or '').upper()
    with get_db() as conn:
        cursor = conn.cursor()
        if airport:
            cursor.execute("DELETE FROM notifications WHERE report_id = ? AND UPPER(airport) = ?;", (report_id, airport))
        else:
            cursor.execute("DELETE FROM notifications WHERE report_id = ?;", (report_id,))

def _matches_active_month(n, active_month):
    """
    Memeriksa apakah notifikasi terkait dengan periode bulan aktif ('YYYY-MM').
    """
    if not active_month:
        return True
    
    clean_month = str(active_month).strip()
    month_compact = clean_month.replace('-', '')
    
    tgl = str(n.get('tanggal') or '').strip()
    if tgl and len(tgl) >= 7:
        return tgl.startswith(clean_month)
        
    rid = str(n.get('report_id') or '').strip()
    if rid:
        if month_compact in rid or clean_month in rid:
            return True
        if re.search(r'20\d{4,6}', rid):
            return False

    msg = f"{n.get('title', '')} {n.get('message', '')}"
    if clean_month in msg:
        return True
    m_date = re.search(r'20\d{2}-\d{2}', msg)
    if m_date:
        return m_date.group(0) == clean_month

    created = str(n.get('created_at') or '').strip()
    if created and len(created) >= 7:
        return created.startswith(clean_month)

    return True

def get_notifications(airport_code, role='staff', username=None, active_month=None):
    """
    Mengambil daftar notifikasi untuk airport dan role tertentu yang sesuai dengan bulan aktif dari SQLite.
    """
    airport = (airport_code or 'LOP').upper()
    if not active_month:
        try:
            from app.models.config_store import get_active_month
            active_month = get_active_month(airport)
        except Exception:
            active_month = None

    with _lock:
        raw_list = _load_raw_notifications()

    cleaned_list = _clean_superseded_notifications(raw_list)
    if len(cleaned_list) != len(raw_list):
        cleaned_ids = {n['id'] for n in cleaned_list}
        stale_ids = [n['id'] for n in raw_list if n['id'] not in cleaned_ids]
        if stale_ids:
            with _lock:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.executemany("DELETE FROM notifications WHERE id = ?;", [(sid,) for sid in stale_ids])
        raw_list = cleaned_list

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
                if role == 'staff':
                    if recip_user and u_filter and recip_user != u_filter:
                        continue

                if active_month and not _matches_active_month(n, active_month):
                    continue

                filtered.append(n)

    # Sinkronisasi dengan staging reports aktif di SQLite
    try:
        from app.services.staging_service import get_staging_reports
        active_staging = get_staging_reports(airport)
        active_staging_ids = {srep.get('report_id') for srep in active_staging if srep.get('report_id')}
        staging_status_map = {srep.get('report_id'): srep.get('status') for srep in active_staging if srep.get('report_id')}
        
        existing_revisi_rids = {n.get('report_id') for n in filtered if n.get('notif_type') == 'revisi'}
        for srep in active_staging:
            if srep.get('status') == 'REVISI':
                rid = srep.get('report_id')
                rep_user = (srep.get('submitted_by_username') or '').strip().lower()
                rep_tgl = str(srep.get('tanggal') or '').strip()
                if active_month and rep_tgl and not rep_tgl.startswith(active_month):
                    continue
                if rid and rid not in existing_revisi_rids and role in ('staff', 'all'):
                    if u_filter and rep_user and rep_user != u_filter:
                        continue
                    auto_notif = create_notification(
                        airport_code=airport,
                        recipient_role='staff',
                        recipient_username=rep_user or u_filter,
                        notif_type='revisi',
                        title='Catatan Koreksi DH',
                        message=f'Pesan DH: "{srep.get("catatan_gm") or srep.get("catatan_dh") or "Periksa kembali data inspeksi."}"',
                        report_id=rid,
                        tanggal=srep.get('tanggal'),
                        notes=srep.get('catatan_gm') or srep.get('catatan_dh')
                    )
                    filtered.insert(0, auto_notif)
                    existing_revisi_rids.add(rid)

        final_filtered = []
        orphan_notif_ids = set()

        for n in filtered:
            rid = n.get('report_id')
            ntype = n.get('notif_type')

            if rid and ntype in ('pending', 'revisi'):
                if rid not in active_staging_ids:
                    orphan_notif_ids.add(n.get('id'))
                    continue
                if ntype == 'revisi' and staging_status_map.get(rid) != 'REVISI':
                    # Laporan telah diperbaiki / diajukan ulang / disetujui, notifikasi revisi usang dibersihkan
                    orphan_notif_ids.add(n.get('id'))
                    continue
                if ntype == 'pending':
                    if staging_status_map.get(rid) == 'REVISI':
                        continue
                    if rid in existing_revisi_rids:
                        continue

            final_filtered.append(n)
        filtered = final_filtered

        if orphan_notif_ids:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.executemany("DELETE FROM notifications WHERE id = ?;", [(oid,) for oid in orphan_notif_ids])

    except Exception as e:
        print(f"Warning sync staging to notifications: {e}")

    filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return filtered

def clear_notifications(airport_code, role='staff', username=None, active_month=None):
    """
    Menghapus seluruh notifikasi untuk bandara, role, username, dan bulan aktif tertentu.
    Pengecualian Mutlak: Notifikasi bertipe 'revisi' yang laporannya masih aktif berstatus REVISI
    TIDAK BOLEH dihapus secara permanen sampai laporan direvisi dan diselesaikan.
    """
    airport = (airport_code or 'LOP').upper()
    target_roles = {'all', role}
    if role in ('dh', 'gm'):
        target_roles.update({'dh', 'gm'})
    u_filter = (username or '').strip().lower()

    if not active_month:
        try:
            from app.models.config_store import get_active_month
            active_month = get_active_month(airport)
        except Exception:
            active_month = None

    # Cari report_id aktif yang berstatus REVISI
    active_revisi_rids = set()
    try:
        from app.services.staging_service import get_staging_reports
        active_stg = get_staging_reports(airport)
        active_revisi_rids = {s.get('report_id') for s in active_stg if s.get('status') == 'REVISI' and s.get('report_id')}
    except Exception as err:
        print("Warning check active revisi rids:", err)

    with _lock:
        raw_list = _load_raw_notifications()
        ids_to_delete = []
        for n in raw_list:
            # Pengecualian proteksi: jangan hapus notifikasi revisi yang masih aktif
            if n.get('notif_type') == 'revisi' and n.get('report_id') in active_revisi_rids:
                continue

            apt_match = (n.get('airport', '').upper() == airport)
            role_match = (n.get('recipient_role', 'all') in target_roles)
            user_match = True
            if role == 'staff' and u_filter:
                recip_u = (n.get('recipient_username') or '').strip().lower()
                if recip_u and recip_u != u_filter:
                    user_match = False

            month_match = _matches_active_month(n, active_month) if active_month else True

            if apt_match and role_match and user_match and month_match:
                ids_to_delete.append(n.get('id'))

        if ids_to_delete:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.executemany("DELETE FROM notifications WHERE id = ?;", [(nid,) for nid in ids_to_delete])

def delete_single_notification(notif_id):
    """
    Menghapus satu notifikasi spesifik berdasarkan ID notifikasi di SQLite.
    Pengecualian: Notifikasi bertipe 'revisi' yang laporannya masih aktif berstatus REVISI
    TIDAK BOLEH dihapus.
    """
    if not notif_id:
        return False
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_id, notif_type, airport FROM notifications WHERE id = ?;", (notif_id,))
            row = cursor.fetchone()
            if not row:
                return False

            if (row['notif_type'] or '').lower() == 'revisi' and row['report_id']:
                try:
                    from app.services.staging_service import get_staging_reports
                    stg = get_staging_reports(row['airport'])
                    active_revisi_rids = {s.get('report_id') for s in stg if s.get('status') == 'REVISI'}
                    if row['report_id'] in active_revisi_rids:
                        # Ditolak karena revisi masih aktif
                        return False
                except Exception:
                    pass

            cursor.execute("DELETE FROM notifications WHERE id = ?;", (notif_id,))
            return True

def set_notification_read_status(notif_id, is_read=True):
    """
    Mengubah status baca (is_read: True/False) untuk satu notifikasi spesifik di SQLite secara atomic.
    """
    if not notif_id:
        return
    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notifications SET is_read = ? WHERE id = ?;", (1 if is_read else 0, notif_id))

def mark_notification_as_read(notif_id):
    set_notification_read_status(notif_id, is_read=True)

def mark_all_as_read(airport_code, role='staff', username=None):
    """
    Menandai semua notifikasi untuk bandara dan role tertentu telah dibaca di SQLite secara atomic.
    """
    airport = (airport_code or 'LOP').upper()
    u_filter = (username or '').strip().lower()

    with _lock:
        with get_db() as conn:
            cursor = conn.cursor()
            if role == 'staff' and u_filter:
                cursor.execute("""
                UPDATE notifications 
                SET is_read = 1 
                WHERE UPPER(airport) = ? 
                  AND recipient_role IN ('staff', 'all')
                  AND (recipient_username = '' OR LOWER(recipient_username) = ?)
                  AND notif_type != 'revisi';
                """, (airport, u_filter))
            elif role in ('dh', 'gm'):
                cursor.execute("""
                UPDATE notifications 
                SET is_read = 1 
                WHERE UPPER(airport) = ? 
                  AND recipient_role IN ('dh', 'gm', 'all')
                  AND notif_type != 'revisi';
                """, (airport,))
            else:
                cursor.execute("""
                UPDATE notifications 
                SET is_read = 1 
                WHERE UPPER(airport) = ? 
                  AND recipient_role IN (?, 'all')
                  AND notif_type != 'revisi';
                """, (airport, role))
