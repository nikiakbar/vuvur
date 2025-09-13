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
SCAN_STATUS_PATH = "/app/data/scan_status.json" # New file to store progress

# --- (get_video_dimensions and extract_user_comment functions remain the same) ---
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
                        return value.decode("utf-16", errors="ignore").strip()
                    except UnicodeDecodeError:
                        return value.decode("utf-8", errors="ignore").strip()
                return str(value).strip()
    except Exception as e:
        logger.error(f"Could not extract EXIF from {image_path}: {e}")
    return None

def update_scan_status(progress, total):
    """Writes the current scan progress to a file."""
    with open(SCAN_STATUS_PATH, 'w') as f:
        json.dump({"progress": progress, "total": total}, f)

def scan():
    logger.info("Starting library scan...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # --- Pre-scan: Count total files for the progress bar ---
    logger.info("Counting total files for scanning...")
    total_files = 0
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
    for root, _, files in os.walk(GALLERY_PATH):
        if RECYCLEBIN_PATH in root:
            continue
        for fname in files:
            if os.path.splitext(fname)[1].lower() in valid_extensions:
                total_files += 1
    update_scan_status(0, total_files)

    # --- Fetch existing data from DB ---
    db_media = {row["path"]: dict(row) for row in c.execute("SELECT * FROM media")}
    db_paths = set(db_media.keys())
    
    # --- Main Scan: Walk filesystem and process files ---
    logger.info("Scanning files on disk...")
    disk_paths = set()
    files_to_add = []
    files_to_update = []
    processed_count = 0

    for root, _, files in os.walk(GALLERY_PATH):
        if RECYCLEBIN_PATH in root:
            continue

        for fname in files:
            path = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            
            if ext not in valid_extensions:
                continue

            processed_count += 1
            disk_paths.add(path)
            
            ftype = "image" if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} else "video"

            try:
                stat = os.stat(path)
            except FileNotFoundError:
                continue

            size = stat.st_size
            mtime = stat.st_mtime
            
            if path not in db_paths:
                width, height, user_comment = get_metadata(path, ftype)
                files_to_add.append((path, fname, ftype, size, mtime, user_comment, width, height))
            else:
                db_file = db_media[path]
                if db_file["size"] != size or db_file["mtime"] != mtime:
                    width, height, user_comment = get_metadata(path, ftype)
                    files_to_update.append((size, mtime, user_comment, width, height, path))
            
            # Update progress every 10 files to avoid excessive writes
            if processed_count % 10 == 0:
                update_scan_status(processed_count, total_files)

    update_scan_status(total_files, total_files) # Final update

    # --- Batch database operations ---
    if files_to_add:
        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)
    if files_to_update:
        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=? WHERE path=?", files_to_update)

    # --- Remove deleted files ---
    paths_to_delete = db_paths - disk_paths
    if paths_to_delete:
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