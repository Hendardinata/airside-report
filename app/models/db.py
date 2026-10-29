import sqlite3
import os
import json
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'airside.db'))

@contextmanager
def get_db():
    """
    Context manager untuk koneksi SQLite yang thread-safe.
    Kompatibel dengan disk lokal maupun NFS (Network File System seperti di PythonAnywhere).
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        # Coba aktifkan WAL mode untuk performa lokal
        res = conn.execute("PRAGMA journal_mode=WAL;").fetchone()
        # Jika environment NFS (seperti PythonAnywhere) tidak mendukung WAL, fallback ke TRUNCATE
        if res and res[0].lower() not in ('wal',):
            conn.execute("PRAGMA journal_mode=TRUNCATE;")
    except Exception:
        try:
            conn.execute("PRAGMA journal_mode=TRUNCATE;")
        except Exception:
            pass

    try:
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass

    try:
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """
    Inisialisasi tabel SQLite dan migrasi data awal dari users.json & notifications.json jika tabel kosong.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Tabel Users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            airport TEXT,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            is_system INTEGER DEFAULT 0,
            is_legacy_alias INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # 2. Tabel Notifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            airport TEXT,
            recipient_role TEXT,
            recipient_username TEXT,
            sender_username TEXT,
            sender_name TEXT,
            notif_type TEXT,
            title TEXT,
            message TEXT,
            report_id TEXT,
            tanggal TEXT,
            notes TEXT,
            created_at TEXT,
            is_read INTEGER DEFAULT 0
        );
        """)

        # 3. Tabel Staging Reports (Antrean Review & Draf Petugas)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS staging_reports (
            report_id TEXT PRIMARY KEY,
            airport_code TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING_DH',
            catatan_gm TEXT DEFAULT '',
            catatan_dh TEXT DEFAULT '',
            submitted_by TEXT DEFAULT '',
            submitted_by_username TEXT DEFAULT '',
            timestamp_submit TEXT,
            timestamp_update TEXT,
            form_data TEXT NOT NULL
        );
        """)

        # 4. Tabel Report Photos (Dokumentasi Foto Lapangan .webp)
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

        # Indeks untuk query cepat
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_airport_status ON staging_reports(airport_code, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_staging_airport_tanggal ON staging_reports(airport_code, tanggal);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_airport_role ON notifications(airport, recipient_role, is_read);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(recipient_username, is_read);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_airport_tanggal ON report_photos(airport_code, tanggal);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_photos_created_at ON report_photos(created_at);")

        # --- SEEDING USERS ---
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] == 0:
            users_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'users.json'))
            seed_data = {}
            if os.path.exists(users_json_path):
                try:
                    with open(users_json_path, 'r', encoding='utf-8') as f:
                        seed_data = json.load(f)
                except Exception as e:
                    print(f"Warning reading users.json for seed: {e}")

            if not seed_data:
                from app.models.user_store import DEFAULT_USERS
                seed_data = DEFAULT_USERS

            for uname, u in seed_data.items():
                cursor.execute("""
                INSERT OR REPLACE INTO users (
                    username, name, role, airport, password_hash, is_active, is_system, is_legacy_alias, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    uname.lower(),
                    u.get('name', ''),
                    u.get('role', 'staff'),
                    u.get('airport'),
                    u.get('password_hash', ''),
                    1 if u.get('is_active', True) else 0,
                    1 if u.get('is_system', False) else 0,
                    1 if u.get('is_legacy_alias', False) else 0,
                    u.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    u.get('updated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                ))
            print("Database initialized: Users seeded into SQLite.")

        # --- SEEDING NOTIFICATIONS ---
        cursor.execute("SELECT COUNT(*) FROM notifications;")
        if cursor.fetchone()[0] == 0:
            notif_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'notifications.json'))
            if os.path.exists(notif_json_path):
                try:
                    with open(notif_json_path, 'r', encoding='utf-8') as f:
                        notifs = json.load(f)
                        for n in notifs:
                            cursor.execute("""
                            INSERT OR REPLACE INTO notifications (
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
                    print("Database initialized: Notifications seeded into SQLite.")
                except Exception as e:
                    print(f"Warning reading notifications.json for seed: {e}")
