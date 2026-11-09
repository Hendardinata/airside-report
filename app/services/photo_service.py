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


def save_uploaded_photos(airport_code, tanggal, report_id, uploaded_files, areas=None, captions=None, keep_photo_ids=None, is_edit=False, keep_photo_areas=None, keep_photo_captions=None):
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

    # 1. Kelola foto lama HANYA jika keep_photo_ids diberikan secara eksplisit
    if keep_photo_ids is not None:
        keep_list = [str(pid).strip() for pid in keep_photo_ids if str(pid).strip()]
        keep_set = set(keep_list)
        keep_meta_map = {}
        for k_idx, pid in enumerate(keep_list):
            k_area = str(keep_photo_areas[k_idx]).strip() if keep_photo_areas and k_idx < len(keep_photo_areas) else None
            k_cap = str(keep_photo_captions[k_idx]).strip() if keep_photo_captions and k_idx < len(keep_photo_captions) else None
            keep_meta_map[pid] = (k_area, k_cap)

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
                elif row['id'] in keep_meta_map:
                    k_area, k_cap = keep_meta_map[row['id']]
                    if k_area is not None and k_cap is not None:
                        cursor.execute(
                            "UPDATE report_photos SET area_tag = ?, caption = ? WHERE id = ?;",
                            (k_area or 'Umum', k_cap, row['id'])
                        )

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

        photo_id = f"PHO-{airport_code}-{tanggal.replace('-', '')}-{idx + 1:02d}-{uuid.uuid4().hex[:6].upper()}"
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
    Mengambil seluruh foto dari cabang bandara yang terdaftar di profil maupun
    yang tercatat di database pada tanggal tertentu, dikelompokkan per kode bandara.
    """
    _ensure_photos_table()
    try:
        from app.models.airport_profiles import AIRPORTS
        branch_codes = [str(c).upper().strip() for c in AIRPORTS.keys() if str(c).strip()]
    except Exception:
        branch_codes = ["DPS", "LOP", "KOE", "BWX"]

    if not branch_codes:
        branch_codes = ["DPS", "LOP", "KOE", "BWX"]

    clean_date = str(tanggal or '').strip()[:10]
    if clean_date:
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT UPPER(airport_code) AS code FROM report_photos WHERE tanggal = ? ORDER BY code ASC;",
                    (clean_date,)
                )
                for row in cursor.fetchall():
                    db_code = (row['code'] or '').strip().upper()
                    if db_code and db_code not in branch_codes:
                        branch_codes.append(db_code)
        except Exception:
            pass

    result = {code: [] for code in branch_codes}
    if not clean_date:
        return result
    for code in branch_codes:
        result[code] = get_photos_by_date(code, clean_date)
    return result


def get_latest_documentation_date():
    """
    Mengambil tanggal dokumentasi terbaru yang memiliki foto di database,
    atau tanggal hari ini jika belum ada foto.
    """
    _ensure_photos_table()
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(tanggal) AS latest_date FROM report_photos;")
            row = cursor.fetchone()
            if row and row['latest_date']:
                return str(row['latest_date']).strip()[:10]
    except Exception:
        pass
    return datetime.now().strftime('%Y-%m-%d')


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


def generate_og_preview_jpeg(tanggal, airport_code=None):
    """
    Membuat gambar pratinjau OpenGraph (1200x630 JPEG) untuk preview link WhatsApp.
    Menggabungkan hingga 4 foto dokumentasi pada tanggal tersebut menjadi kolase rapi.
    """
    all_photos = []
    if airport_code:
        all_photos = get_photos_by_date(airport_code, tanggal)
    else:
        grouped = get_all_airports_photos_by_date(tanggal)
        for code in ["DPS", "LOP", "BWX", "KOE"]:
            all_photos.extend(grouped.get(code, []))

    if not all_photos:
        return None

    try:
        from PIL import Image, ImageOps
        import io

        canvas_w, canvas_h = 1200, 630
        canvas = Image.new("RGB", (canvas_w, canvas_h), (15, 23, 42))

        sample = all_photos[:4]
        n = len(sample)
        pad = 12

        if n == 1:
            boxes = [(pad, pad, canvas_w - pad, canvas_h - pad)]
        elif n == 2:
            mid_x = canvas_w // 2
            boxes = [
                (pad, pad, mid_x - pad // 2, canvas_h - pad),
                (mid_x + pad // 2, pad, canvas_w - pad, canvas_h - pad)
            ]
        elif n == 3:
            mid_x = canvas_w // 2
            mid_y = canvas_h // 2
            boxes = [
                (pad, pad, mid_x - pad // 2, canvas_h - pad),
                (mid_x + pad // 2, pad, canvas_w - pad, mid_y - pad // 2),
                (mid_x + pad // 2, mid_y + pad // 2, canvas_w - pad, canvas_h - pad)
            ]
        else:
            mid_x = canvas_w // 2
            mid_y = canvas_h // 2
            boxes = [
                (pad, pad, mid_x - pad // 2, mid_y - pad // 2),
                (mid_x + pad // 2, pad, canvas_w - pad, mid_y - pad // 2),
                (pad, mid_y + pad // 2, mid_x - pad // 2, canvas_h - pad),
                (mid_x + pad // 2, mid_y + pad // 2, canvas_w - pad, canvas_h - pad)
            ]

        for idx, p in enumerate(sample):
            rel = p["url"].replace("/static/uploads/", "").replace("/", os.sep)
            abs_p = os.path.join(UPLOADS_ROOT, rel)
            if not os.path.exists(abs_p):
                continue
            x1, y1, x2, y2 = boxes[idx]
            w, h = x2 - x1, y2 - y1
            with Image.open(abs_p) as img:
                img_rgb = img.convert("RGB")
                fitted = ImageOps.fit(img_rgb, (w, h), method=Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                canvas.paste(fitted, (x1, y1))

        buf = io.BytesIO()
        canvas.save(buf, format="JPEG", quality=82, optimize=True)
        return buf.getvalue()
    except ImportError:
        return None
    except Exception as e:
        print(f"Warning generate_og_preview_jpeg: {e}")
        return None


def _format_safe_area_filename_prefix(area_tag):
    """
    Mengubah nama area/lokasi menjadi prefix nama file yang bersih dan mudah dibaca,
    misalnya 'Runway 09' -> 'Runway_09', 'Runway' -> 'Runway', 'Apron Utara' -> 'Apron_Utara'.
    """
    raw = str(area_tag or 'Umum').strip()
    if not raw:
        raw = 'Umum'
    cleaned = re.sub(r'[\s\-/\\]+', '_', raw)
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '', cleaned).strip('_')
    return cleaned[:40] if cleaned else 'Dokumentasi'


def build_documentation_zip(tanggal, branch='ALL'):
    """
    Membangun arsip ZIP dokumentasi foto untuk tanggal dan filter cabang tertentu.
    - Jika branch adalah 'ALL' / 'all' / 'SEMUA':
        Nama ZIP: Dokumentasi_Airside_<YYYY-MM-DD>_Semua_Cabang.zip
        Struktur: Dokumentasi_Airside_<YYYY-MM-DD>/<BRANCH>/<Area>_<No>.webp
    - Jika branch adalah kode cabang spesifik (misal 'LOP', 'DPS', 'KOE', 'BWX'):
        Nama ZIP: Dokumentasi_Airside_<YYYY-MM-DD>_<BRANCH>.zip
        Struktur: Dokumentasi_Airside_<YYYY-MM-DD>/<BRANCH>/<Area>_<No>.webp
    Menggunakan SpooledTemporaryFile (5 MB threshold) agar hemat RAM dan tidak meninggalkan file permanen.
    Mengembalikan tuple: (spool_file, zip_filename, total_added, included_branches)
    """
    import zipfile
    import tempfile

    clean_date = str(tanggal or '').strip()[:10]
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', clean_date):
        raise ValueError("Format tanggal dokumentasi tidak valid (harus YYYY-MM-DD).")

    raw_branch = str(branch or 'ALL').strip()
    upper_branch = raw_branch.upper()

    if upper_branch in ('', 'ALL', 'SEMUA', 'SEMUA_CABANG'):
        is_all = True
        grouped = get_all_airports_photos_by_date(clean_date)
        photos_by_branch = {code: plist for code, plist in grouped.items() if plist}
        zip_filename = f"Dokumentasi_Airside_{clean_date}_Semua_Cabang.zip"
    else:
        if not re.match(r'^[A-Z0-9_-]{2,10}$', upper_branch):
            raise ValueError("Kode cabang bandara tidak valid.")
        is_all = False
        branch_photos = get_photos_by_date(upper_branch, clean_date)
        photos_by_branch = {upper_branch: branch_photos} if branch_photos else {}
        zip_filename = f"Dokumentasi_Airside_{clean_date}_{upper_branch}.zip"

    if not photos_by_branch:
        return None, zip_filename, 0, []

    real_uploads_root = os.path.realpath(UPLOADS_ROOT)
    root_folder = f"Dokumentasi_Airside_{clean_date}"

    spool = tempfile.SpooledTemporaryFile(max_size=5 * 1024 * 1024, mode='w+b')
    total_added = 0
    included_branches = []

    try:
        with zipfile.ZipFile(spool, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for code, plist in photos_by_branch.items():
                safe_code = re.sub(r'[^A-Z0-9_-]', '', str(code).upper()) or 'CABANG'
                area_counters = {}
                used_filenames = set()
                branch_added = 0

                for p in plist:
                    url_val = str(p.get('url') or '')
                    rel_part = url_val.replace('/static/uploads/', '').lstrip('/\\').replace('/', os.sep)
                    if not rel_part:
                        continue

                    candidate_abs = os.path.realpath(os.path.join(real_uploads_root, rel_part))
                    # Proteksi ketat terhadap Path Traversal di luar UPLOADS_ROOT
                    if not (candidate_abs == real_uploads_root or candidate_abs.startswith(real_uploads_root + os.sep)):
                        continue
                    if not os.path.isfile(candidate_abs):
                        continue

                    _, ext = os.path.splitext(candidate_abs)
                    ext = ext.lower() if ext else '.webp'
                    if ext not in ALLOWED_EXTENSIONS:
                        ext = '.webp'

                    area_prefix = _format_safe_area_filename_prefix(p.get('area_tag'))
                    area_key = area_prefix.lower()
                    seq = area_counters.get(area_key, 0) + 1
                    area_counters[area_key] = seq

                    entry_name = f"{area_prefix}_{seq:02d}{ext}"
                    while entry_name.lower() in used_filenames:
                        seq += 1
                        area_counters[area_key] = seq
                        entry_name = f"{area_prefix}_{seq:02d}{ext}"

                    used_filenames.add(entry_name.lower())
                    arcname = f"{root_folder}/{safe_code}/{entry_name}"
                    zf.write(candidate_abs, arcname=arcname)
                    total_added += 1
                    branch_added += 1

                if branch_added > 0:
                    included_branches.append(safe_code)

        if total_added == 0:
            spool.close()
            return None, zip_filename, 0, []

        spool.seek(0)
        return spool, zip_filename, total_added, included_branches
    except Exception:
        try:
            spool.close()
        except Exception:
            pass
        raise



