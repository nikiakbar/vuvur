# In api/app/scanner.py
import os
import sqlite3
import logging
import subprocess
import json
import concurrent.futures
import time  # Import the time module
from app.db import DB_PATH, init_db
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import piexif

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
    Extracts metadata from an image, with specific, robust handling for the
    UserComment encoding from AUTOMATIC1111 Stable Diffusion generations.
    """
    try:
        img = Image.open(image_path)
        user_comment = None
        exif_json = None
        all_tags = {}

        # For PNG files, the prompt is stored directly in the info dictionary
        if "parameters" in img.info:
            user_comment = img.info["parameters"]
            all_tags["parameters"] = user_comment
            exif_json = json.dumps(all_tags, default=str)
            return exif_json, user_comment

        # For JPEG/WebP, parse the raw EXIF data using piexif
        if "exif" in img.info:
            try:
                exif_dict = piexif.load(img.info["exif"])
                if "Exif" in exif_dict and piexif.ExifIFD.UserComment in exif_dict["Exif"]:
                    comment_bytes = exif_dict["Exif"][piexif.ExifIFD.UserComment]
                    
                    # ✅ THIS IS THE DEFINITIVE FIX:
                    # Manually clean the byte string to remove encoding headers and null bytes.
                    
                    # 1. Find the start of the actual text (skip headers like UNICODE, ASCII, etc.)
                    try:
                        text_start = comment_bytes.index(b'\x00\x00', 8) + 2
                    except ValueError:
                        text_start = 8 # Fallback for slightly different formats

                    # 2. Get the raw text bytes
                    raw_text_bytes = comment_bytes[text_start:]
                    
                    # 3. Filter out the interspersed null bytes
                    cleaned_bytes = bytes([b for b in raw_text_bytes if b != 0])
                    
                    # 4. Decode the clean byte string
                    user_comment = cleaned_bytes.decode('utf-8', errors='ignore')

                    all_tags["UserComment"] = user_comment
                    exif_json = json.dumps(all_tags, default=str)

                return exif_json, user_comment

            except Exception as e:
                logger.warning(f"Piexif failed for {image_path}: {e}")

    except Exception as e:
        logger.error(f"Failed to extract metadata from {image_path}: {e}")

    return None, None


def update_scan_status(progress, total):
    """Writes the current scan progress to a file."""
    with open(SCAN_STATUS_PATH, 'w') as f:
        json.dump({"progress": progress, "total": total}, f)

def scan():
    init_db()
    
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
    
    logger.info("Identifying files that need processing (in parallel)...")
    
    files_to_process = []
    
    # --- OPTIMIZATION: Parallelize the file status check ---
    def check_file_status(path):
        """Checks if a file is new or modified and returns it if so."""
        try:
            stat = os.stat(path)
            # Check if it's a new file OR an existing file with a different size or modification time
            if path not in db_paths or \
               db_media[path]["size"] != stat.st_size or \
               db_media[path]["mtime"] != stat.st_mtime:
                return path
        except FileNotFoundError:
            return None
        return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # This will run os.stat and the comparison for all files concurrently
        results = executor.map(check_file_status, all_disk_paths)
        # Filter out the None results for files that haven't changed
        files_to_process = [path for path in results if path is not None]

    logger.info(f"Found {len(files_to_process)} new or modified files to process for metadata.")

    if not files_to_process:
        logger.info("No new or modified files found. Scan complete.")
        conn.close()
        return

    # --- Now process the identified files in parallel ---
    files_to_add = []
    files_to_update = []

    def process_file_metadata(path):
        """Wrapper function to get all data for a single file."""
        try:
            ext = os.path.splitext(path)[1].lower()
            ftype = "image" if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} else "video"
            stat = os.stat(path)
            width, height, user_comment, exif = get_metadata(path, ftype)
            
            # Automatically determine the group tag
            rel_path = os.path.relpath(path, GALLERY_PATH)
            group_tag = rel_path.split(os.sep)[0] if os.sep in rel_path else None
            
            return {
                "path": path, "filename": os.path.basename(path), "type": ftype,
                "size": stat.st_size, "mtime": stat.st_mtime, "user_comment": user_comment,
                "width": width, "height": height, "exif": exif, "group_tag": group_tag
            }
        except FileNotFoundError:
            logger.warning(f"File not found during metadata scan, skipping: {path}")
            return None # Return None if file was deleted mid-scan
        except Exception as e:
            logger.error(f"Failed to process metadata for {path}: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(process_file_metadata, files_to_process)
        for i, data in enumerate(results):
            if data is None: # Skip files that failed or were not found
                continue
                
            if data['path'] not in db_paths:
                files_to_add.append(tuple(data.values()))
            else:
                update_data = (data['size'], data['mtime'], data['user_comment'], data['width'], data['height'], data['exif'], data['group_tag'], data['path'])
                files_to_update.append(update_data)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Metadata extraction progress: {i + 1}/{len(files_to_process)}")
                update_scan_status(i + 1, len(files_to_process))

    logger.info("Metadata extraction complete. Preparing database updates.")

    if files_to_add:
        logger.info(f"Adding {len(files_to_add)} new files to the database...")
        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)

    if files_to_update:
        logger.info(f"Updating {len(files_to_update)} existing files in the database...")
        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=?, group_tag=? WHERE path=?", files_to_update)

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