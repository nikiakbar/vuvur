# In api/app/scanner.py
import os
import sqlite3
import logging
import subprocess
import json
import concurrent.futures
import time  # Import the time module
from app.db import DB_PATH, init_db
from app.thumbnails import create_image_version, create_video_thumb, create_audio_thumb, THUMB_DIR
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
    Returns (exif_json, user_comment, width, height).
    """
    try:
        # Check if it's a GIF early, as Pillow's EXIF handling for GIF is limited
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.gif':
            return None, None, None, None # GIFs generally don't have standard EXIF

        with Image.open(image_path) as img:
            width, height = img.size
            user_comment = None
            exif_json = None
            all_tags = {}

            # For PNG files, the prompt is stored directly in the info dictionary
            if "parameters" in img.info:
                user_comment = img.info["parameters"]
                all_tags["parameters"] = user_comment
                exif_json = json.dumps(all_tags, default=str)
                return exif_json, user_comment, width, height

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

                    return exif_json, user_comment, width, height

                except Exception as e:
                    logger.warning(f"Piexif failed for {image_path}: {e}")
                    return None, None, width, height

            return None, None, width, height

    except Exception as e:
        logger.error(f"Failed to extract metadata from {image_path}: {e}")

    return None, None, None, None


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
    # Fetch only needed columns to drastically reduce memory usage
    db_media = {row["path"]: {"size": row["size"], "mtime": row["mtime"]} for row in c.execute("SELECT path, size, mtime FROM media")}
    db_paths = set(db_media.keys())
    logger.info(f"Database contains {len(db_paths)} records.")

    logger.info("Discovering files on disk...")
    
    files_to_process = []
    # all_disk_paths is used for deletion logic. 
    # If limit is set, we will NOT perform deletion, so we don't strictly need to track everything found if we exit early.
    all_disk_paths = set() 
    
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".mp4", ".webm", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".wma", ".aac"}
    
    limit_reached = False
    stack = [GALLERY_PATH]
    
    while stack and not limit_reached:
        current_dir = stack.pop()
        
        # Skip recycle bin
        if RECYCLEBIN_PATH in current_dir:
            continue
            
        try:
            with os.scandir(current_dir) as it:
                for entry in it:
                    if limit_reached:
                        break
                        
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in valid_extensions:
                            full_path = entry.path
                            all_disk_paths.add(full_path)
                            
                            needs_processing = False
                            try:
                                # entry.stat() is cached on Windows during scandir, making it very fast
                                stat = entry.stat()
                                if full_path not in db_paths:
                                    needs_processing = True
                                elif db_media[full_path]["size"] != stat.st_size or \
                                     db_media[full_path]["mtime"] != stat.st_mtime:
                                    needs_processing = True
                            except (FileNotFoundError, OSError):
                                continue # File disappeared or other error, skip

                            if needs_processing:
                                files_to_process.append(full_path)
                                if limit is not None and len(files_to_process) >= limit:
                                    logger.info(f"Scan limit of {limit} reached during discovery. Stopping scan.")
                                    limit_reached = True
                                    break
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not scan directory {current_dir}: {e}")
            continue

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
        if limit is not None or not (db_paths - all_disk_paths):
             logger.info("No new/modified files and no deletions pending. Scan complete.")
             conn.close()
             return

    # --- Now process the identified files in parallel ---
    files_to_add = []
    files_to_update = []
    
    # Refactoring slightly to keep it clean.
    
    def process_wrapper(path):
        # Re-implementing the inner logic or calling a helper. 
        # Since I am replacing the whole block, I will just paste the logic here.
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
                ftype = "image"
            elif ext in {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".wma", ".aac"}:
                ftype = "audio"
            else:
                ftype = "video"
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
        BATCH_SIZE = 500  # <--- Batch size limit to flush RAM
        
        # <--- Cap max_workers to 4 to prevent 32 concurrent processes eating memory
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # We use a set of futures with a "sliding window" to keep RAM usage low.
            # This prevents creating thousands of Future objects at once.
            MAX_WINDOW = 1000
            file_iter = iter(files_to_process)
            futures = set()

            # Initial submission seed
            for _ in range(min(len(files_to_process), MAX_WINDOW)):
                path = next(file_iter)
                futures.add(executor.submit(process_wrapper, path))

            while futures:
                # Wait for the first task to finish
                done, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
                
                for future in done:
                    try:
                        data = future.result()
                    except Exception as e:
                        logger.error(f"Worker generated exception: {e}")
                        data = None

                    processed_count += 1
                    
                    # Refill the window as tasks finish
                    try:
                        next_path = next(file_iter)
                        futures.add(executor.submit(process_wrapper, next_path))
                    except StopIteration:
                        pass

                    if data is None: continue
                        
                    if data['path'] not in db_paths:
                        files_to_add.append(tuple(data.values()))
                    else:
                        update_data = (data['size'], data['mtime'], data['user_comment'], data['width'], data['height'], data['exif'], data['group_tag'], data['path'])
                        files_to_update.append(update_data)
                    
                    # --- NEW BATCH COMMIT LOGIC ---
                    if len(files_to_add) >= BATCH_SIZE:
                        logger.info(f"Batch inserting {len(files_to_add)} files...")
                        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)
                        conn.commit()
                        files_to_add.clear() # <--- FREE RAM
                        
                    if len(files_to_update) >= BATCH_SIZE:
                        logger.info(f"Batch updating {len(files_to_update)} files...")
                        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=?, group_tag=? WHERE path=?", files_to_update)
                        conn.commit()
                        files_to_update.clear() # <--- FREE RAM
                    
                    if processed_count % 50 == 0:
                        logger.info(f"Metadata extraction progress: {processed_count}/{len(files_to_process)}")
                        update_scan_status(processed_count, len(files_to_process))
                    
        update_scan_status(len(files_to_process), len(files_to_process))

    # Catch any remaining items after the loop finishes
    if files_to_add:
        logger.info(f"Adding final {len(files_to_add)} new files...")
        c.executemany("INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", files_to_add)

    if files_to_update:
        logger.info(f"Updating final {len(files_to_update)} existing files...")
        c.executemany("UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=?, group_tag=? WHERE path=?", files_to_update)
    # Deletion Logic
    if limit is not None:
        logger.info("Scan limit active. Skipping deletion phase to prevent data loss on partial scan.")
    else:
        paths_to_delete = db_paths - all_disk_paths
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
        exif, user_comment, width, height = extract_exif_data(path)
    elif ftype == 'video':
        width, height = get_video_dimensions(path)
    # Audio files just return None for everything
    return width, height, user_comment, exif

def precompute_missing_thumbnails(batch_size=50):
    """
    Finds missing thumbnails in the background and generates them.
    Returns True if some thumbnails were missing, False if all caught up.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Query media, ordered by ID DESC to prioritize new files
        c.execute("SELECT id, path, type FROM media ORDER BY id DESC")
        
        missing_items = []
        for row in c:
            mid = row['id']
            src = row['path']
            ftype = row['type']
            
            is_gif = src.lower().endswith(".gif")
            thumb_ext = ".gif" if is_gif else ".jpg"
            dst = os.path.join(THUMB_DIR, f"{mid}{thumb_ext}")
            
            # Audio and Video thumbs are always .jpg
            if ftype in ("audio", "video"):
                dst = os.path.join(THUMB_DIR, f"{mid}.jpg")

            if not os.path.exists(dst):
                missing_items.append((dict(row), dst))
                if len(missing_items) >= batch_size:
                    break
                    
        conn.close()
    except Exception as e:
        logger.error(f"Database error while fetching media for thumbnails: {e}")
        return False
                
    if not missing_items:
        return False
        
    logger.info(f"Precomputing thumbnails for {len(missing_items)} missing items...")
    
    def process_thumb(item):
        row, dst_path = item
        src_path = row['path']
        f_type = row['type']
        media_id = row['id']
        
        if not os.path.exists(src_path):
            return # Original file deleted, skip
            
        try:
            if f_type == "image":
                 create_image_version(src_path, dst_path, size=(600, 600), quality=90)
            elif f_type == "audio":
                 create_audio_thumb(dst_path)
            else:
                 create_video_thumb(src_path, dst_path)
        except Exception as e:
            logger.error(f"Failed to precompute thumb for media ID {media_id}: {e}")
            
    # Use ThreadPoolExecutor to speed up generation, especially for many images
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(process_thumb, missing_items))
        
    return True
