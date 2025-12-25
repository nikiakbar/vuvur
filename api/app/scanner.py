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
        # Check if it's a GIF early, as Pillow's EXIF handling for GIF is limited
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.gif':
            return None, None # GIFs generally don't have standard EXIF

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
                        # Look for common patterns indicating start of text
                        if comment_bytes.startswith(b'UNICODE\x00'):
                             text_start = 8
                        elif comment_bytes.startswith(b'ASCII\x00\x00\x00'):
                             text_start = 8
                        elif b'\x00\x00' in comment_bytes[8:]:
                             text_start = comment_bytes.index(b'\x00\x00', 8) + 2
                        else:
                             text_start = 0 # Fallback if no header found
                    except ValueError:
                        text_start = 8 # Fallback for slightly different formats

                    # 2. Get the raw text bytes
                    raw_text_bytes = comment_bytes[text_start:]
                    
                    # 3. Filter out the interspersed null bytes common in some encodings
                    cleaned_bytes = bytes([b for b in raw_text_bytes if b != 0])
                    
                    # 4. Decode the clean byte string
                    user_comment = cleaned_bytes.decode('utf-8', errors='ignore').strip()

                    all_tags["UserComment"] = user_comment
                    # Only save if we actually got a comment
                    if user_comment:
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

def scan(limit=None):
    init_db()
    
    start_time = time.time()
    logger.info(f"Starting library scan... (Limit: {limit})")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    logger.info("Fetching existing media from database...")
    db_media = {row["path"]: dict(row) for row in c.execute("SELECT * FROM media")}
    db_paths = set(db_media.keys())
    logger.info(f"Database contains {len(db_paths)} records.")

    logger.info("Discovering files on disk...")
    
    files_to_process = []
    # all_disk_paths is used for deletion logic. 
    # If limit is set, we will NOT perform deletion, so we don't strictly need to track everything found if we exit early.
    all_disk_paths = [] 
    
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".mp4", ".webm", ".mov", ".avi", ".mkv"}
    
    limit_reached = False
    
    for root, _, files in os.walk(GALLERY_PATH):
        if limit_reached:
            break
            
        if RECYCLEBIN_PATH in root:
            continue
            
        for fname in files:
            if os.path.splitext(fname)[1].lower() in valid_extensions:
                full_path = os.path.join(root, fname)
                all_disk_paths.append(full_path)
                
                # Check if needs processing
                needs_processing = False
                try:
                    stat = os.stat(full_path)
                    if full_path not in db_paths:
                        needs_processing = True
                    elif db_media[full_path]["size"] != stat.st_size or \
                         db_media[full_path]["mtime"] != stat.st_mtime:
                        needs_processing = True
                except FileNotFoundError:
                    continue # File disappeared, skip

                if needs_processing:
                    files_to_process.append(full_path)
                    
                    if limit is not None and len(files_to_process) >= limit:
                        logger.info(f"Scan limit of {limit} reached during discovery. Stopping file walk.")
                        limit_reached = True
                        break

    total_files_found = len(all_disk_paths)
    if limit_reached:
        logger.info(f"Discovery stopped early. Found {total_files_found} files (partial) and identified {len(files_to_process)} for processing.")
    else:
        logger.info(f"Discovery complete. Found {total_files_found} total media files.")

    logger.info(f"Found {len(files_to_process)} new or modified files to process for metadata.")

    if not files_to_process and not (limit_reached is False and len(db_paths) != len(all_disk_paths)):
        # If nothing to process AND (limit reached OR no diff in counts implying no deletions needed?)
        # Actually safer to just check if we have nothing to process and limit was set.
        # If limit was NOT set, we still might need to delete.
        if limit is not None or not (db_paths - set(all_disk_paths)):
             logger.info("No new/modified files and no deletions pending. Scan complete.")
             conn.close()
             return

    # --- Now process the identified files in parallel ---
    files_to_add = []
    files_to_update = []
    
    # ... (process_file_metadata function remains same, but locally defined) ...
    # We need to redefine or pass dependencies if we moved this logic. 
    # Refactoring slightly to keep it clean.
    
    def process_file_metadata_wrapper(path):
        return process_file_metadata(path)

    # Note: process_file_metadata calls get_metadata which is global. 
    # But wait, the original code had process_file_metadata nested or global? 
    # It was nested. I need to keep it nested or make it global. 
    # I will keep the original implementation style if possible or define it here.
    
    def process_wrapper(path):
        # Re-implementing the inner logic or calling a helper. 
        # Since I am replacing the whole block, I will just paste the logic here.
        try:
            ext = os.path.splitext(path)[1].lower()
            ftype = "image" if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"} else "video"
            stat = os.stat(path)
            width, height, user_comment, exif = get_metadata(path, ftype)
            
            rel_path = os.path.relpath(path, GALLERY_PATH)
            group_tag = rel_path.split(os.sep)[0] if os.sep in rel_path else None
            
            return {
                "path": path, "filename": os.path.basename(path), "type": ftype,
                "size": stat.st_size, "mtime": stat.st_mtime, "user_comment": user_comment,
                "width": width, "height": height, "exif": exif, "group_tag": group_tag
            }
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to process metadata for {path}: {e}")
            return None

    if files_to_process:
        logger.info(f"Starting metadata extraction for {len(files_to_process)} files...")
        processed_count = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(process_wrapper, files_to_process)
            for data in results:
                processed_count += 1
                if data is None: continue
                    
                if data['path'] not in db_paths:
                    files_to_add.append(tuple(data.values()))
                else:
                    update_data = (data['size'], data['mtime'], data['user_comment'], data['width'], data['height'], data['exif'], data['group_tag'], data['path'])
                    files_to_update.append(update_data)
                
                if processed_count % 50 == 0:
                    logger.info(f"Metadata extraction progress: {processed_count}/{len(files_to_process)}")
                    update_scan_status(processed_count, len(files_to_process))
                    
        update_scan_status(len(files_to_process), len(files_to_process))

    if files_to_add:
        logger.info(f"Adding {len(files_to_add)} new files...")
        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)

    if files_to_update:
        logger.info(f"Updating {len(files_to_update)} existing files...")
        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=?, group_tag=? WHERE path=?", files_to_update)

    # Deletion Logic
    if limit is not None:
        logger.info("Scan limit active. Skipping deletion phase to prevent data loss on partial scan.")
    else:
        paths_to_delete = db_paths - set(all_disk_paths)
        if paths_to_delete:
            logger.info(f"Removing {len(paths_to_delete)} deleted files...")
            c.executemany("DELETE FROM media WHERE path=?", [(path,) for path in paths_to_delete])

    logger.info("Committing changes...")
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