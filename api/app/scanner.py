import os
import sqlite3
import logging
import subprocess
import json
from app.db import DB_PATH
from PIL import Image

# Import this to handle PNG metadata
from PIL.PngImagePlugin import PngInfo

logger = logging.getLogger(__name__)

GALLERY_PATH = "/mnt/gallery"
LIKED_PATH = os.path.join(GALLERY_PATH, "liked")
RECYCLEBIN_PATH = os.path.join(GALLERY_PATH, "recyclebin")
SCAN_STATUS_PATH = "/app/data/scan_status.json"

def get_video_dimensions(video_path):
    """Get video dimensions using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", video_path
        ]
        # Set the timeout for the subprocess run command to 5 seconds
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            return data["streams"][0].get("width"), data["streams"][0].get("height")
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timed out for {video_path}. Skipping file.")
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Could not get dimensions for {video_path}: {e}")
    return None, None

def extract_exif_data(image_path):
    """
    Extracts metadata from an image, using the AUTOMATIC1111/stable-diffusion-webui logic.
    For PNGs, it reads the 'parameters' text chunk.
    For JPEGs, it falls back to reading standard EXIF.
    """
    try:
        with Image.open(image_path) as img:
            # A1111's primary method for PNGs
            if "parameters" in img.info:
                user_comment = img.info["parameters"]
                # The full data is the user_comment itself
                exif_json = json.dumps({"parameters": user_comment})
                return exif_json, user_comment

            # Fallback for JPEGs and other formats with standard EXIF
            exif_data = img.getexif()
            if exif_data:
                # Use the robust piexif-style logic for standard EXIF as a fallback
                from PIL import ExifTags
                all_tags = {}
                for key, val in exif_data.items():
                    if key in ExifTags.TAGS:
                        tag_name = ExifTags.TAGS[key]
                        if isinstance(val, bytes):
                           val = val.decode(errors='ignore')
                        all_tags[tag_name] = val

                exif_ifd = exif_data.get_ifd(ExifTags.IFD.Exif)
                for key, val in exif_ifd.items():
                    if key in ExifTags.TAGS:
                        tag_name = ExifTags.TAGS[key]
                        if isinstance(val, bytes):
                           val = val.decode(errors='ignore')
                        all_tags[tag_name] = val
                
                user_comment = all_tags.get("UserComment")
                exif_json = json.dumps(all_tags, default=str)
                return exif_json, user_comment

    except Exception as e:
        logger.error(f"Could not extract metadata from {image_path}: {e}")

    return None, None


def update_scan_status(progress, total):
    """Writes the current scan progress to a file."""
    with open(SCAN_STATUS_PATH, 'w') as f:
        json.dump({"progress": progress, "total": total}, f)

def scan():
    logger.info("Starting library scan...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

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

    db_media = {row["path"]: dict(row) for row in c.execute("SELECT * FROM media")}
    db_paths = set(db_media.keys())
    
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
                width, height, user_comment, exif = get_metadata(path, ftype)
                files_to_add.append((path, fname, ftype, size, mtime, user_comment, width, height, exif))
            else:
                db_file = db_media[path]
                if db_file["size"] != size or db_file["mtime"] != mtime:
                    width, height, user_comment, exif = get_metadata(path, ftype)
                    files_to_update.append((size, mtime, user_comment, width, height, exif, path))
            
            if processed_count % 10 == 0:
                update_scan_status(processed_count, total_files)

    update_scan_status(total_files, total_files)

    if files_to_add:
        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)
    if files_to_update:
        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=? WHERE path=?", files_to_update)

    paths_to_delete = db_paths - disk_paths
    if paths_to_delete:
        c.executemany("DELETE FROM media WHERE path=?", [(path,) for path in paths_to_delete])

    conn.commit()
    conn.close()
    logger.info("Library scan finished.")

def get_metadata(path, ftype):
    """Helper function to get all metadata for a file."""
    user_comment, width, height, exif = None, None, None, None
    if ftype == "image":
        exif, user_comment = extract_exif_data(path)
        try:
            with Image.open(path) as img:
                width, height = img.size
        except Exception as e:
            logger.error(f"Could not get image dimensions for {path}: {e}")
    elif ftype == 'video':
        width, height = get_video_dimensions(path)
    return width, height, user_comment, exif