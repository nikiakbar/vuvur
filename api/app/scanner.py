# In api/app/scanner.py
import os
import sqlite3
import logging
import subprocess
import json
import concurrent.futures
import time  # Import the time module
from app.db import DB_PATH
from PIL import Image
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
            if "parameters" in img.info:
                user_comment = img.info["parameters"]
                exif_json = json.dumps({"parameters": user_comment})
                return exif_json, user_comment

            exif_data = img.getexif()
            if exif_data:
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
    start_time = time.time()
    logger.info("Starting library scan...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    logger.info("Discovering all files on disk...")
    all_disk_paths = []
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
    for root, _, files in os.walk(GALLERY_PATH):
        if RECYCLEBIN_PATH in root:
            continue
        for fname in files:
            if os.path.splitext(fname)[1].lower() in valid_extensions:
                all_disk_paths.append(os.path.join(root, fname))
    
    total_files = len(all_disk_paths)
    update_scan_status(0, total_files)
    logger.info(f"Found {total_files} total media files.")

    logger.info("Fetching existing media from database...")
    db_media = {row["path"]: dict(row) for row in c.execute("SELECT * FROM media")}
    db_paths = set(db_media.keys())
    logger.info(f"Database contains {len(db_paths)} records.")
    
    logger.info("Identifying files that need metadata extraction...")
    files_to_process = []
    for path in all_disk_paths:
        try:
            stat = os.stat(path)
            if path not in db_paths or db_media[path]["size"] != stat.st_size or db_media[path]["mtime"] != stat.st_mtime:
                files_to_process.append(path)
        except FileNotFoundError:
            continue

    logger.info(f"Found {len(files_to_process)} new or modified files to process in parallel.")

    files_to_add = []
    files_to_update = []

    def process_file_metadata(path):
        """Wrapper function to get all data for a single file."""
        ext = os.path.splitext(path)[1].lower()
        ftype = "image" if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} else "video"
        stat = os.stat(path)
        width, height, user_comment, exif = get_metadata(path, ftype)
        return {
            "path": path, "filename": os.path.basename(path), "type": ftype,
            "size": stat.st_size, "mtime": stat.st_mtime, "user_comment": user_comment,
            "width": width, "height": height, "exif": exif
        }

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(process_file_metadata, files_to_process)
        for i, data in enumerate(results):
            if data['path'] not in db_paths:
                # Prepare data for insertion
                files_to_add.append(tuple(data.values()))
            else:
                # Prepare data for update
                update_data = (data['size'], data['mtime'], data['user_comment'], data['width'], data['height'], data['exif'], data['path'])
                files_to_update.append(update_data)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Metadata extraction progress: {i + 1}/{len(files_to_process)}")
                update_scan_status(i + 1, len(files_to_process))

    logger.info("Metadata extraction complete. Preparing database updates.")

    if files_to_add:
        logger.info(f"Adding {len(files_to_add)} new files to the database...")
        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)

    if files_to_update:
        logger.info(f"Updating {len(files_to_update)} existing files in the database...")
        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=? WHERE path=?", files_to_update)

    paths_to_delete = db_paths - set(all_disk_paths)
    if paths_to_delete:
        logger.info(f"Removing {len(paths_to_delete)} deleted files from the database...")
        c.executemany("DELETE FROM media WHERE path=?", [(path,) for path in paths_to_delete])

    logger.info("Committing changes to the database...")
    conn.commit()
    conn.close()
    end_time = time.time()
    logger.info(f"Library scan finished in {end_time - start_time:.2f} seconds.")

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