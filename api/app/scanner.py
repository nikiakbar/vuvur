import os
import sqlite3
import logging
import subprocess
import json
from app.db import DB_PATH
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

GALLERY_PATH = "/mnt/gallery"
LIKED_PATH = os.path.join(GALLERY_PATH, "liked")
RECYCLEBIN_PATH = os.path.join(GALLERY_PATH, "recyclebin")

def get_video_dimensions(video_path):
    """Get video dimensions using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            return data["streams"][0].get("width"), data["streams"][0].get("height")
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Could not get dimensions for {video_path}: {e}")
    return None, None

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
                        # Attempt to decode UTF-16, then fall back to UTF-8 with error handling
                        return value.decode("utf-16", errors="ignore").strip()
                    except UnicodeDecodeError:
                        return value.decode("utf-8", errors="ignore").strip()
                return str(value).strip()
    except Exception as e:
        logger.error(f"Could not extract EXIF from {image_path}: {e}")
    return None

def scan():
    logger.info("Starting library scan...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # --- Step 1: Fetch all existing media data from the DB into a dictionary ---
    logger.info("Fetching existing media from the database...")
    db_media = {row["path"]: dict(row) for row in c.execute("SELECT * FROM media")}
    db_paths = set(db_media.keys())
    
    # --- Step 2: Walk the filesystem and compare against the DB data ---
    logger.info("Scanning files on disk...")
    disk_paths = set()
    files_to_add = []
    files_to_update = []

    for root, _, files in os.walk(GALLERY_PATH):
        if RECYCLEBIN_PATH in root:
            continue

        for fname in files:
            path = os.path.join(root, fname)
            disk_paths.add(path)

            ext = fname.lower().split(".")[-1]
            ftype = None
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
            
            # --- Compare with DB data ---
            if path not in db_paths:
                # New file found
                width, height, user_comment = get_metadata(path, ftype)
                files_to_add.append((path, fname, ftype, size, mtime, user_comment, width, height))
            else:
                # Existing file, check if it needs an update
                db_file = db_media[path]
                if db_file["size"] != size or db_file["mtime"] != mtime:
                    width, height, user_comment = get_metadata(path, ftype)
                    files_to_update.append((size, mtime, user_comment, width, height, path))

    # --- Step 3: Batch database operations ---
    if files_to_add:
        logger.info(f"Adding {len(files_to_add)} new files to the database...")
        c.executemany(
            "INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            files_to_add
        )

    if files_to_update:
        logger.info(f"Updating {len(files_to_update)} files in the database...")
        c.executemany(
            "UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=? WHERE path=?",
            files_to_update
        )

    # --- Step 4: Find and remove deleted files ---
    paths_to_delete = db_paths - disk_paths
    if paths_to_delete:
        logger.info(f"Removing {len(paths_to_delete)} deleted files from the database...")
        c.executemany("DELETE FROM media WHERE path=?", [(path,) for path in paths_to_delete])

    conn.commit()
    conn.close()
    logger.info("Library scan finished.")

def get_metadata(path, ftype):
    """Helper function to get all metadata for a file."""
    user_comment, width, height = None, None, None
    if ftype == "image":
        user_comment = extract_user_comment(path)
        try:
            with Image.open(path) as img:
                width, height = img.size
        except Exception as e:
            logger.error(f"Could not get image dimensions for {path}: {e}")
    elif ftype == 'video':
        width, height = get_video_dimensions(path)
    return width, height, user_comment