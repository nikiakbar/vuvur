import os
import sqlite3
from app.db import DB_PATH
from PIL import Image, ExifTags

GALLERY_PATH = "/mnt/gallery"
LIKED_PATH = os.path.join(GALLERY_PATH, "liked")
RECYCLEBIN_PATH = os.path.join(GALLERY_PATH, "recyclebin")

def extract_user_comment(image_path):
    """Try to read EXIF UserComment (Stable Diffusion prompt)."""
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if not exif:
            return None
        for tag_id, value in exif.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            if tag == "UserComment":
                if isinstance(value, bytes):
                    try:
                        return value.decode("utf-8", errors="ignore").strip()
                    except Exception:
                        return None
                return str(value).strip()
    except Exception:
        return None
    return None

def scan():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for root, dirs, files in os.walk(GALLERY_PATH):
        # skip recyclebin entirely
        if RECYCLEBIN_PATH in root:
            continue

        for fname in files:
            path = os.path.join(root, fname)

            # file type detection (image/video only)
            ext = fname.lower().split(".")[-1]
            if ext in ("jpg", "jpeg", "png", "webp", "bmp"):
                ftype = "image"
            elif ext in ("mp4", "webm", "mov", "avi", "mkv"):
                ftype = "video"
            else:
                continue

            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue

            size = stat.st_size
            mtime = stat.st_mtime

            # check existing record
            c.execute("SELECT size, mtime, user_comment FROM media WHERE path=?", (path,))
            row = c.fetchone()

            user_comment = None
            need_update = False

            if ftype == "image":
                # always extract if missing or file changed
                if row is None or row[0] != size or row[1] != mtime or row[2] is None:
                    user_comment = extract_user_comment(path)
                    need_update = True

            if row is None:
                # new file → insert
                c.execute("""
                    INSERT INTO media (path, filename, type, size, mtime, user_comment)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (path, fname, ftype, size, mtime, user_comment))
            elif need_update:
                # update existing with new mtime/size/comment
                c.execute("""
                    UPDATE media
                    SET size=?, mtime=?, user_comment=?
                    WHERE path=?
                """, (size, mtime, user_comment, path))

    # delete missing/recycled files from DB
    c.execute("SELECT path FROM media")
    all_paths = [r[0] for r in c.fetchall()]
    for db_path in all_paths:
        if not os.path.exists(db_path) or db_path.startswith(RECYCLEBIN_PATH):
            c.execute("DELETE FROM media WHERE path=?", (db_path,))

    conn.commit()
    conn.close()
