import sqlite3
import os
from argon2 import PasswordHasher, exceptions

DB_PATH = os.environ.get("DB_PATH", "app.db")
ph = PasswordHasher()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
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
        exif TEXT 
    )
    """)

    # ---- Full Text Search (FTS5) for fast search on filename + user_comment ----
    c.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS media_fts
    USING fts5(filename, user_comment, content='media', content_rowid='id')
    """)

    # Keep FTS index in sync
    c.executescript("""
    CREATE TRIGGER IF NOT EXISTS media_ai AFTER INSERT ON media BEGIN
      INSERT INTO media_fts(rowid, filename, user_comment)
      VALUES (new.id, new.filename, new.user_comment);
    END;
    CREATE TRIGGER IF NOT EXISTS media_ad AFTER DELETE ON media BEGIN
      INSERT INTO media_fts(media_fts, rowid, filename, user_comment)
      VALUES('delete', old.id, old.filename, old.user_comment);
    END;
    CREATE TRIGGER IF NOT EXISTS media_au AFTER UPDATE ON media BEGIN
      INSERT INTO media_fts(media_fts, rowid, filename, user_comment)
      VALUES('delete', old.id, old.filename, old.user_comment);
      INSERT INTO media_fts(rowid, filename, user_comment)
      VALUES (new.id, new.filename, new.user_comment);
    END;
    """)

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