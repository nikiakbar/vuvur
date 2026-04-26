import sqlite3
import os
from argon2 import PasswordHasher, exceptions

DB_PATH = os.environ.get("DB_PATH", "/app/data/app.db")
ph = PasswordHasher()
# DUMMY_HASH used to mitigate timing attacks during authentication
DUMMY_HASH = ph.hash("dummy_password")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # ⚡ Bolt: WAL mode for better concurrency, NORMAL synchronous for balance of speed and safety,
    # and a larger cache to reduce disk I/O.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-10000;") # 10MB cache
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ---- Users table ----
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # ---- Media table ----
    c.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        path TEXT NOT NULL,
        size INTEGER,
        mtime INTEGER,
        liked INTEGER DEFAULT 0,
        user_comment TEXT,
        type TEXT,
        width INTEGER,
        height INTEGER,
        exif TEXT,
        group_tag TEXT,
        original_path TEXT
    )
    """)

    # ---- Full Text Search (FTS5) for fast search on filename + user_comment ----
    c.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS media_fts
    USING fts5(filename, user_comment, exif, content='media', content_rowid='id')
    """)

    # Keep FTS index in sync
    c.executescript("""
    CREATE TRIGGER IF NOT EXISTS media_ai AFTER INSERT ON media BEGIN
      INSERT INTO media_fts(rowid, filename, user_comment, exif)
      VALUES (new.id, new.filename, new.user_comment, new.exif);
    END;
    CREATE TRIGGER IF NOT EXISTS media_ad AFTER DELETE ON media BEGIN
      INSERT INTO media_fts(media_fts, rowid, filename, user_comment, exif)
      VALUES('delete', old.id, old.filename, old.user_comment, old.exif);
    END;
    CREATE TRIGGER IF NOT EXISTS media_au AFTER UPDATE ON media BEGIN
      INSERT INTO media_fts(media_fts, rowid, filename, user_comment, exif)
      VALUES('delete', old.id, old.filename, old.user_comment, old.exif);
      INSERT INTO media_fts(rowid, filename, user_comment, exif)
      VALUES (new.id, new.filename, new.user_comment, new.exif);
    END;
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_media_group_tag ON media (group_tag);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_media_path ON media (path);")
    # ⚡ Bolt: Added indexes on mtime and filename to optimize gallery sorting.
    # Expected impact: Eliminates full table scans and temporary B-tree sorts for gallery views.
    # Reduces query time from O(N log N) to O(K) where K is the page size, assuming index usage.
    c.execute("CREATE INDEX IF NOT EXISTS idx_media_mtime ON media (mtime);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_media_filename ON media (filename);")
    # ⚡ Bolt: Added composite indexes to optimize grouped gallery views and subgroup discovery.
    # idx_media_group_mtime eliminates temporary B-tree sorts when filtering by group.
    # idx_media_group_path enables covering index scans for subgroup path discovery.
    c.execute("CREATE INDEX IF NOT EXISTS idx_media_group_mtime ON media (group_tag, mtime DESC);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_media_group_path ON media (group_tag, path);")

    conn.commit()
    conn.close()


# ---------- User helpers ----------
def user_exists():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM users")
    row = c.fetchone()
    conn.close()
    return row["count"] > 0


def create_user(username, password_hash):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()


def authenticate(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if not row:
        # ✅ Sentinel: Mitigate timing attacks/username enumeration by performing a dummy verification
        try:
            ph.verify(DUMMY_HASH, password)
        except Exception:
            pass
        return False

    try:
        ph.verify(row["password"], password)
        return True
    except exceptions.VerifyMismatchError:
        return False

# ---------- Media helpers ----------
def insert_media(filename, path, size, mtime, user_comment=None):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO media (filename, path, size, mtime, user_comment) VALUES (?, ?, ?, ?, ?)",
        (filename, path, size, mtime, user_comment),
    )
    conn.commit()
    conn.close()


def update_media(media_id, size, mtime, user_comment=None):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE media SET size=?, mtime=?, user_comment=? WHERE id=?",
        (size, mtime, user_comment, media_id),
    )
    conn.commit()
    conn.close()


def delete_media(media_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM media WHERE id=?", (media_id,))
    conn.commit()
    conn.close()