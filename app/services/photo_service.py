import os
import re
import time
import uuid
import shutil
from datetime import datetime, timedelta
from app.models.db import get_db

UPLOADS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads'))
ALLOWED_EXTENSIONS = {'.webp', '.jpg', '.jpeg', '.png'}
DEFAULT_RETENTION_DAYS = 90


def _ensure_photos_table():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_photos (
            id TEXT PRIMARY KEY,
            airport_code TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            report_id TEXT,
            area_tag TEXT DEFAULT 'Umum',
            caption TEXT DEFAULT '',
            file_path TEXT NOT NULL,
            url TEXT NOT NULL,
            size_kb REAL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_airport_tanggal ON report_photos(airport_code, tanggal);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_created_at ON report_photos(created_at);")


def _sanitize_slug(val, fallback='umum'):
    if not val:
        return fallback
    s = re.sub(r'[^a-zA-Z0-9_-]', '', str(val).strip().lower())
    return s[:24] if s else fallback


def save_uploaded_photos(airport_code, tanggal, report_id, uploaded_files, areas=None, captions=None, keep_photo_ids=None, is_edit=False):
    """
    Menyimpan foto-foto dokumentasi (.webp) untuk bandara & tanggal tertentu.
    Jika is_edit=True (atau sudah ada foto di tanggal tersebut dan keep_photo_ids dikirim),
    foto lama yang tidak ada di keep_photo_ids akan dihapus dari disk dan database.
    Otomatis menjalankan cleanup_old_photos(90) di akhir proses.
    """
    _ensure_photos_table()
    airport_code = str(airport_code or '').upper().strip()
    tanggal = str(tanggal or datetime.now().strftime('%Y-%m-%d')).strip()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', tanggal):
        tanggal = datetime.now().strftime('%Y-%m-%d')

    month_folder = tanggal[:7]  # YYYY-MM
    target_dir = os.path.join(UPLOADS_ROOT, month_folder, airport_code)
    os.makedirs(target_dir, exist_ok=True)

    areas = areas or []
    captions = captions or []

    # 1. Kelola foto lama jika keep_photo_ids diberikan atau sedang mode edit
    if keep_photo_ids is not None or is_edit:
        keep_set = set(str(pid).strip() for pid in (keep_photo_ids or []) if str(pid).strip())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, file_path FROM report_photos
            WHERE UPPER(airport_code) = ? AND tanggal = ?;
            """, (airport_code, tanggal))
            existing_rows = cursor.fetchall()
            for row in existing_rows:
                if row['id'] not in keep_set:
                    abs_path = os.path.join(UPLOADS_ROOT, row['file_path'].replace('/', os.sep))
                    if os.path.exists(abs_path):
                        try:
                            os.remove(abs_path)
                        except Exception:
                            pass
                    cursor.execute("DELETE FROM report_photos WHERE id = ?;", (row['id'],))

    # 2. Simpan file baru yang diunggah
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ts_short = int(time.time() * 1000) % 100000000

    for idx, file_storage in enumerate(uploaded_files or []):
        if not file_storage or not getattr(file_storage, 'filename', ''):
            continue

        orig_name = str(file_storage.filename)
        _, ext = os.path.splitext(orig_name.lower())
        if ext not in ALLOWED_EXTENSIONS:
            ext = '.webp'

        area_tag = str(areas[idx]).strip() if idx < len(areas) and areas[idx] else 'Umum'
        caption = str(captions[idx]).strip() if idx < len(captions) and captions[idx] else ''
        area_slug = _sanitize_slug(area_tag, 'umum')

        photo_id = f"PHO-{airport_code}-{tanggal.replace('-', '')}-{uuid.uuid4().hex[:6].upper()}"
        filename = f"{airport_code}_{tanggal}_{area_slug}_{ts_short}_{idx + 1}{ext}"
        abs_file_path = os.path.join(target_dir, filename)

        file_bytes = file_storage.read()
        if not file_bytes:
            continue

        # Jika bukan .webp dan PIL tersedia di server, konversi ke .webp
        if ext != '.webp':
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(file_bytes))
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
                img.thumbnail((1280, 1280))
                out_buf = io.BytesIO()
                img.save(out_buf, format='WEBP', quality=78)
                file_bytes = out_buf.getvalue()
                filename = os.path.splitext(filename)[0] + '.webp'
                abs_file_path = os.path.join(target_dir, filename)
            except Exception:
                pass

        with open(abs_file_path, 'wb') as f:
            f.write(file_bytes)

        size_kb = round(len(file_bytes) / 1024.0, 1)
        rel_path = f"{month_folder}/{airport_code}/{filename}"
        public_url = f"/static/uploads/{rel_path}"

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO report_photos (
                id, airport_code, tanggal, report_id, area_tag, caption, file_path, url, size_kb, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                photo_id,
                airport_code,
                tanggal,
                report_id or f"REP-{airport_code}-{tanggal.replace('-', '')}",
                area_tag,
                caption,
                rel_path,
                public_url,
                size_kb,
                now_str
            ))

    # 3. Jalankan Auto-Cleanup (> 90 Hari) secara senyap
    try:
        cleanup_old_photos(DEFAULT_RETENTION_DAYS)
    except Exception as e:
        print(f"Warning auto-cleanup photos: {e}")

    return get_photos_by_date(airport_code, tanggal)


def get_photos_by_date(airport_code, tanggal):
    """
    Mengambil daftar foto untuk 1 cabang pada tanggal tertentu.
    Juga memverifikasi apakah file fisiknya masih ada di disk.
    """
    _ensure_photos_table()
    if not airport_code or not tanggal:
        return []
    airport_code = str(airport_code).upper().strip()
    tanggal = str(tanggal).strip()[:10]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, airport_code, tanggal, report_id, area_tag, caption, file_path, url, size_kb, created_at
        FROM report_photos
        WHERE UPPER(airport_code) = ? AND tanggal = ?
        ORDER BY created_at ASC, id ASC;
        """, (airport_code, tanggal))
        rows = cursor.fetchall()

    photos = []
    for r in rows:
        abs_path = os.path.join(UPLOADS_ROOT, r['file_path'].replace('/', os.sep))
        if os.path.exists(abs_path):
            photos.append({
                "id": r['id'],
                "airport_code": r['airport_code'],
                "tanggal": r['tanggal'],
                "report_id": r['report_id'],
                "area_tag": r['area_tag'] or 'Umum',
                "caption": r['caption'] or '',
                "url": r['url'],
                "size_kb": r['size_kb'] or 0,
                "created_at": r['created_at']
            })
    return photos


def get_all_airports_photos_by_date(tanggal):
    """
    Mengambil seluruh foto dari 4 bandara (LOP, DPS, BWX, KOE) pada tanggal tertentu,
    dikelompokkan per kode bandara.
    """
    result = {"LOP": [], "DPS": [], "BWX": [], "KOE": []}
    if not tanggal:
        return result
    for code in ["LOP", "DPS", "BWX", "KOE"]:
        result[code] = get_photos_by_date(code, tanggal)
    return result


def delete_photos_for_report(airport_code, tanggal=None, report_id=None):
    """
    Menghapus seluruh foto milik suatu laporan ketika draf laporan dihapus.
    """
    _ensure_photos_table()
    airport_code = str(airport_code or '').upper().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        if tanggal:
            cursor.execute("""
            SELECT id, file_path FROM report_photos
            WHERE UPPER(airport_code) = ? AND tanggal = ?;
            """, (airport_code, tanggal))
        elif report_id:
            cursor.execute("""
            SELECT id, file_path FROM report_photos
            WHERE UPPER(airport_code) = ? AND report_id = ?;
            """, (airport_code, report_id))
        else:
            return 0

        rows = cursor.fetchall()
        deleted = 0
        for r in rows:
            abs_path = os.path.join(UPLOADS_ROOT, r['file_path'].replace('/', os.sep))
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass
            cursor.execute("DELETE FROM report_photos WHERE id = ?;", (r['id'],))
            deleted += 1
        return deleted


def cleanup_old_photos(retention_days=DEFAULT_RETENTION_DAYS):
    """
    Menghapus foto-foto yang umurnya lebih dari `retention_days` (default 90 hari / 3 bulan),
    baik berdasarkan tanggal laporan maupun waktu pembuatan file.
    """
    _ensure_photos_table()
    cutoff_dt = datetime.now() - timedelta(days=int(retention_days))
    cutoff_date_str = cutoff_dt.strftime('%Y-%m-%d')
    cutoff_ts_str = cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')

    deleted_count = 0
    freed_kb = 0.0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, file_path, size_kb FROM report_photos
        WHERE tanggal < ? OR created_at < ?;
        """, (cutoff_date_str, cutoff_ts_str))
        old_rows = cursor.fetchall()

        for r in old_rows:
            abs_path = os.path.join(UPLOADS_ROOT, r['file_path'].replace('/', os.sep))
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass
            freed_kb += float(r['size_kb'] or 0)
            cursor.execute("DELETE FROM report_photos WHERE id = ?;", (r['id'],))
            deleted_count += 1

    # Bersihkan juga file yatim (orphan) di folder uploads yang berumur > retention_days
    cutoff_epoch = cutoff_dt.timestamp()
    if os.path.exists(UPLOADS_ROOT):
        for root, dirs, files in os.walk(UPLOADS_ROOT, topdown=False):
            for fname in files:
                if fname == '.gitkeep':
                    continue
                fpath = os.path.join(root, fname)
                try:
                    if os.path.getmtime(fpath) < cutoff_epoch:
                        fsize = os.path.getsize(fpath) / 1024.0
                        os.remove(fpath)
                        deleted_count += 1
                        freed_kb += fsize
                except Exception:
                    pass
            # Hapus sub-folder kosong
            if root != UPLOADS_ROOT:
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                except Exception:
                    pass

    return {
        "deleted_count": deleted_count,
        "freed_kb": round(freed_kb, 1),
        "freed_mb": round(freed_kb / 1024.0, 2),
        "retention_days": retention_days,
        "cutoff_date": cutoff_date_str
    }


def get_storage_stats():
    """
    Mengembalikan ringkasan penggunaan penyimpanan foto dokumentasi di server.
    """
    _ensure_photos_table()
    total_files = 0
    total_bytes = 0

    if os.path.exists(UPLOADS_ROOT):
        for root, _, files in os.walk(UPLOADS_ROOT):
            for fname in files:
                if fname == '.gitkeep':
                    continue
                fpath = os.path.join(root, fname)
                try:
                    total_bytes += os.path.getsize(fpath)
                    total_files += 1
                except Exception:
                    pass

    total_kb = round(total_bytes / 1024.0, 1)
    total_mb = round(total_bytes / (1024.0 * 1024.0), 2)
    quota_mb = 300.0  # Batas aman alokasi foto pada PythonAnywhere (512MB total)
    usage_pct = min(100.0, round((total_mb / quota_mb) * 100.0, 1)) if quota_mb > 0 else 0.0

    return {
        "total_files": total_files,
        "total_kb": total_kb,
        "total_mb": total_mb,
        "quota_mb": quota_mb,
        "usage_pct": usage_pct,
        "retention_days": DEFAULT_RETENTION_DAYS
    }

