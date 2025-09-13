import os
import sqlite3
import logging
import subprocess
import json
from app.db import DB_PATH
from PIL import Image, ExifTags

# Configure logging
logger = logging.getLogger(__name__)

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
    except Exception as e:
        logger.error(f"Could not extract EXIF from {image_path}: {e}")
        return None
    return None

def scan():
    logger.info("Starting library scan...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Make sure you can access columns by name
    c = conn.cursor()

    # --- Scanning files on disk ---
    file_count = 0
    for root, dirs, files in os.walk(GALLERY_PATH):
        if RECYCLEBIN_PATH in root:
            continue

        for fname in files:
            file_count += 1
            path = os.path.join(root, fname)

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
            
            c.execute("SELECT * FROM media WHERE path=?", (path,))
            row = c.fetchone()
            
            user_comment = None
            width, height = None, None

            # Get dimensions and metadata
            if ftype == "image":
                user_comment = extract_user_comment(path)
                try:
                    with Image.open(path) as img:
                        width, height = img.size
                except Exception as e:
                    logger.error(f"Could not get image dimensions for {path}: {e}")
            elif ftype == 'video':
                width, height = get_video_dimensions(path)

            if row is None:
                logger.info(f"New file found: {path}")
                c.execute(
                    "INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (path, fname, ftype, size, mtime, user_comment, width, height)
                )
            else:
                # Check if an update is needed
                needs_update = False
                if row['size'] != size or row['mtime'] != mtime:
                    needs_update = True
                if ftype == 'image' and row['user_comment'] != user_comment:
                    needs_update = True
                if row['width'] != width or row['height'] != height:
                    needs_update = True

                if needs_update:
                    logger.info(f"Updating file metadata: {path}")
                    c.execute(
                        "UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=? WHERE path=?",
                        (size, mtime, user_comment, width, height, path)
                    )
                    
    logger.info(f"Finished checking {file_count} files on disk.")

    # --- Deleting missing files from DB ---
    logger.info("Checking for files to remove from the database...")
    c.execute("SELECT path FROM media")
    all_paths = [r["path"] for r in c.fetchall()]
    deleted_count = 0
    for db_path in all_paths:
        if not os.path.exists(db_path) or db_path.startswith(RECYCLEBIN_PATH):
            logger.info(f"Removing missing file from DB: {db_path}")
            c.execute("DELETE FROM media WHERE path=?", (db_path,))
            deleted_count += 1
    if deleted_count > 0:
        logger.info(f"Removed {deleted_count} missing files from the database.")

    conn.commit()
    conn.close()
    logger.info("Library scan finished.")
    
def get_video_dimensions(video_path):
    """Get video dimensions using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            return data["streams"][0].get("width"), data["streams"][0].get("height")
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Could not get dimensions for {video_path}: {e}")
    return None, None