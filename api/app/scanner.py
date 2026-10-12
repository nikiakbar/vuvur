# In api/app/scanner.py
import os
import sqlite3
import logging
import subprocess
import json
import concurrent.futures
import time
import sys
import hashlib
import threading
from collections import deque
from typing import TYPE_CHECKING

# Python 3.15+ lazy imports optimization (PEP 690)
# Defers heavy module loading until first use
if TYPE_CHECKING:
    from PIL import Image
    import piexif
    from app.thumbnails import create_image_version, create_video_thumb, create_audio_thumb

# Lightweight imports only
from app.db import DB_PATH, init_db

logger = logging.getLogger(__name__)

GALLERY_PATH = "/mnt/gallery"
LIKED_PATH = os.path.join(GALLERY_PATH, "liked")
RECYCLEBIN_PATH = os.path.join(GALLERY_PATH, "recyclebin")
SCAN_STATUS_PATH = "/app/data/scan_status.json"

# Auto-detect optimal worker counts
CPU_WORKERS = min(8, (os.cpu_count() or 2))  # Increased for better parallelism
BATCH_SIZE = 100  # Smaller batches for better memory management
THUMB_WORKERS = min(4, (os.cpu_count() or 2))  # Separate pool for I/O-bound thumbnail generation


def hash_path(path: str) -> int:
    """Fast hash for memory-efficient path comparison. Uses 8 bytes instead of full string."""
    return int.from_bytes(
        hashlib.blake2s(path.encode(), digest_size=8).digest(),
        'little'
    )


class StreamingBatchCommitter:
    """
    Thread-safe streaming batch committer.
    Collects records from worker threads and commits in main thread only.
    Uses deques for O(1) append/clear.
    """
    def __init__(self, batch_size=50):
        self.batch_size = batch_size
        self.add_buffer = deque()
        self.update_buffer = deque()
        self.total_added = 0
        self.total_updated = 0
        self._lock = threading.Lock()
    
    def add(self, record):
        """Thread-safe: Add a record to insert buffer."""
        with self._lock:
            self.add_buffer.append(record)
            return len(self.add_buffer) >= self.batch_size
    
    def update(self, record):
        """Thread-safe: Add a record to update buffer."""
        with self._lock:
            self.update_buffer.append(record)
            return len(self.update_buffer) >= self.batch_size
    
    def _flush_adds(self, cursor, connection):
        """Commit all pending inserts. MUST be called from main thread only."""
        with self._lock:
            if not self.add_buffer:
                return
            count = len(self.add_buffer)
            records = list(self.add_buffer)
            self.add_buffer.clear()
        
        logger.info(f"Streaming insert: committing {count} files...")
        cursor.executemany(
            "INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            records
        )
        connection.commit()
        self.total_added += count
    
    def _flush_updates(self, cursor, connection):
        """Commit all pending updates. MUST be called from main thread only."""
        with self._lock:
            if not self.update_buffer:
                return
            count = len(self.update_buffer)
            records = list(self.update_buffer)
            self.update_buffer.clear()
        
        logger.info(f"Streaming update: committing {count} files...")
        cursor.executemany(
            "UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=?, group_tag=? WHERE path=?",
            records
        )
        connection.commit()
        self.total_updated += count
    
    def flush(self, cursor, connection):
        """Flush any remaining items in buffers. MUST be called from main thread only."""
        self._flush_adds(cursor, connection)
        self._flush_updates(cursor, connection)
        return self.total_added, self.total_updated

def get_video_dimensions_cached(video_path, file_size, file_mtime, cursor):
    """
    Get video dimensions with caching to avoid redundant ffprobe calls.
    Cache is validated by file size and mtime.
    """
    # Check cache first
    cursor.execute("""
        SELECT width, height 
        FROM video_dimensions_cache 
        WHERE path = ? AND file_size = ? AND file_mtime = ?
    """, (video_path, file_size, file_mtime))
    
    result = cursor.fetchone()
    if result:
        # Cache hit - return immediately
        return result[0], result[1]
    
    # Cache miss - call ffprobe
    width, height = get_video_dimensions(video_path)
    
    # Update cache if we got valid dimensions
    if width is not None and height is not None:
        cursor.execute("""
            INSERT OR REPLACE INTO video_dimensions_cache 
            (path, file_size, file_mtime, width, height)
            VALUES (?, ?, ?, ?, ?)
        """, (video_path, file_size, file_mtime, width, height))
    
    return width, height


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
    
    Uses lazy imports to defer PIL/piexif loading until actually needed.
    """
    # Lazy import - only load when processing images
    from PIL import Image
    import piexif
    
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
                        # Using .replace is orders of magnitude faster and uses 0 extra memory compared to list comprehension
                        cleaned_bytes = raw_text_bytes.replace(b'\x00', b'')
                        
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


def process_file_chunk(files_chunk, committer, cursor, conn, db_paths_set, db_media, offset=0):
    """Process a chunk of files and return count processed."""
    if not files_chunk:
        return 0
    
    def process_wrapper(path_and_stat):
        # Unpack (path, stat) tuple to reuse stat from discovery phase
        path, stat = path_and_stat
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
                ftype = "image"
            elif ext in {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".wma", ".aac"}:
                ftype = "audio"
            else:
                ftype = "video"
            
            width, height, user_comment, exif = get_metadata(path, ftype, stat.st_size, stat.st_mtime)
            
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
    
    processed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=CPU_WORKERS) as executor:
        MAX_WINDOW = 1000
        file_iter = iter(files_chunk)
        futures = set()

        # Initial submission seed
        for _ in range(min(len(files_chunk), MAX_WINDOW)):
            try:
                path = next(file_iter)
                futures.add(executor.submit(process_wrapper, path))
            except StopIteration:
                break

        while futures:
            done, futures = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)
            
            for future in done:
                try:
                    data = future.result()
                except Exception as e:
                    logger.error(f"Worker generated exception: {e}")
                    data = None

                processed_count += 1
                
                # Refill the window
                try:
                    next_path = next(file_iter)
                    futures.add(executor.submit(process_wrapper, next_path))
                except StopIteration:
                    pass

                if data is None:
                    continue
                    
                # Add to committer buffer
                should_flush_adds = False
                should_flush_updates = False
                
                if data['path'] not in db_paths_set:
                    should_flush_adds = committer.add(tuple(data.values()))
                else:
                    update_data = (data['size'], data['mtime'], data['user_comment'], data['width'], data['height'], data['exif'], data['group_tag'], data['path'])
                    should_flush_updates = committer.update(update_data)
                
                # Commit from main thread when batch is full
                if should_flush_adds:
                    committer._flush_adds(cursor, conn)
                if should_flush_updates:
                    committer._flush_updates(cursor, conn)
                
                if processed_count % 50 == 0:
                    logger.info(f"Metadata extraction progress: {offset + processed_count}/{offset + len(files_chunk)}")
                    update_scan_status(offset + processed_count, offset + len(files_chunk))
    
    return processed_count

def scan(limit=None):
    init_db()
    
    start_time = time.time()
    logger.info(f"Starting library scan... (Limit: {limit})")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    logger.info("Fetching existing media from database...")
    # Load path -> (size, mtime) mapping for change detection
    # Memory: ~200-300MB for 100k files, but avoids 100k+ SQL queries during discovery
    db_media = {row["path"]: (row["size"], row["mtime"]) for row in c.execute("SELECT path, size, mtime FROM media")}
    db_paths_set = db_media.keys()
    logger.info(f"Database contains {len(db_media)} records.")

    logger.info("Discovering files on disk...")
    
    # Memory optimization: Stream processing in chunks
    # Process and clear files in batches to avoid holding all paths in memory
    DISCOVERY_CHUNK_SIZE = 500  # Process 500 files at a time
    files_to_process = []
    discovered_paths_for_deletion = set() if limit is None else None
    total_discovered = 0
    total_processed_count = 0 
    
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
                            
                            # Track discovered paths for deletion check (memory-efficient set)
                            if discovered_paths_for_deletion is not None:
                                discovered_paths_for_deletion.add(full_path)
                            
                            needs_processing = False
                            try:
                                # entry.stat() is cached on Windows during scandir, making it very fast
                                stat = entry.stat()
                                if full_path not in db_paths_set:
                                    needs_processing = True
                                else:
                                    # Fast in-memory comparison (no SQL query per file)
                                    db_size, db_mtime = db_media[full_path]
                                    if db_size != stat.st_size or db_mtime != stat.st_mtime:
                                        needs_processing = True
                            except (FileNotFoundError, OSError):
                                continue # File disappeared or other error, skip

                            if needs_processing:
                                # Store (path, stat) tuple to avoid redundant stat() calls later
                                files_to_process.append((full_path, stat))
                                
                                # Memory optimization: Process in chunks to avoid holding all paths
                                if len(files_to_process) >= DISCOVERY_CHUNK_SIZE:
                                    # Process this chunk before discovering more
                                    total_processed_count += process_file_chunk(
                                        files_to_process, committer, c, conn, db_paths_set, db_media, total_processed_count
                                    )
                                    files_to_process.clear()  # Free memory
                                
                                if limit is not None and total_processed_count + len(files_to_process) >= limit:
                                    logger.info(f"Scan limit of {limit} reached during discovery. Stopping scan.")
                                    limit_reached = True
                                    break
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not scan directory {current_dir}: {e}")
            continue

    total_files_found = len(discovered_paths_for_deletion) if discovered_paths_for_deletion is not None else "unknown (limited scan)"
    if limit_reached:
        logger.info(f"Discovery stopped early. Processed {total_processed_count} files so far.")
    else:
        logger.info(f"Discovery complete. Found {total_files_found} total media files.")

    logger.info(f"Remaining files in buffer: {len(files_to_process)}")

    # Early exit if nothing to do
    if total_processed_count == 0 and not files_to_process:
        if limit is not None:
            logger.info("No new/modified files found. Scan complete.")
            conn.close()
            return
        # Check for deletions when full scan
        elif discovered_paths_for_deletion is not None:
            paths_to_delete = db_paths_set - discovered_paths_for_deletion
            if not paths_to_delete:
                logger.info("No new/modified files and no deletions pending. Scan complete.")
                conn.close()
                return

    # Process any remaining files from last chunk
    committer = StreamingBatchCommitter(batch_size=BATCH_SIZE)
    if files_to_process:
        logger.info(f"Processing final chunk of {len(files_to_process)} files...")
        total_processed_count += process_file_chunk(
            files_to_process, committer, c, conn, db_paths_set, db_media, total_processed_count
        )
        files_to_process.clear()

    # Flush any remaining items in committer buffers
    added, updated = committer.flush(c, conn)
    logger.info(f"Streaming commit complete: {added} added, {updated} updated")
    # Deletion Logic
    if limit is not None:
        logger.info("Scan limit active. Skipping deletion phase to prevent data loss on partial scan.")
    elif discovered_paths_for_deletion is not None:
        # Memory-efficient deletion: process in chunks
        paths_to_delete = db_paths_set - discovered_paths_for_deletion
        
        if paths_to_delete:
            logger.info(f"Removing {len(paths_to_delete)} deleted files...")
            # Delete in chunks to avoid large SQL statements
            chunk_size = 1000
            paths_list = list(paths_to_delete)
            for i in range(0, len(paths_list), chunk_size):
                chunk = paths_list[i:i+chunk_size]
                c.executemany("DELETE FROM media WHERE path=?", [(path,) for path in chunk])
                if i % 5000 == 0 and i > 0:
                    logger.info(f"Deletion progress: {i}/{len(paths_to_delete)}")

    logger.info("Committing changes...")
    conn.commit()
    conn.close()
    end_time = time.time()
    logger.info(f"Library scan finished in {end_time - start_time:.2f} seconds.")

def get_metadata(path, ftype, file_size=None, file_mtime=None):
    """Helper function to get all metadata for a file."""
    user_comment, width, height, exif = None, None, None, None
    if ftype == "image":
        exif, user_comment, width, height = extract_exif_data(path)
    elif ftype == 'video':
        # Always use direct ffprobe call (no cursor available in worker threads)
        width, height = get_video_dimensions(path)
    # Audio files just return None for everything
    return width, height, user_comment, exif


def process_single_file(path):
    """
    Upserts a single media file into the database.
    Used by both the bulk scanner and the real-time watchdog watcher.
    Returns True on success, False on failure.
    """
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

        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.execute("SELECT id FROM media WHERE path=?", (path,))
            existing = c.fetchone()
            if existing:
                c.execute(
                    "UPDATE media SET size=?, mtime=?, user_comment=?, width=?, height=?, exif=?, group_tag=? WHERE path=?",
                    (stat.st_size, stat.st_mtime, user_comment, width, height, exif, group_tag, path)
                )
                logger.info(f"Updated media record for: {path}")
            else:
                filename = os.path.basename(path)
                c.execute(
                    "INSERT INTO media (path, filename, type, size, mtime, user_comment, width, height, exif, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (path, filename, ftype, stat.st_size, stat.st_mtime, user_comment, width, height, exif, group_tag)
                )
                logger.info(f"Inserted new media record for: {path}")
            conn.commit()
        finally:
            conn.close()
        return True
    except FileNotFoundError:
        logger.warning(f"File disappeared before processing: {path}")
        return False
    except Exception as e:
        logger.error(f"Failed to process file {path}: {e}", exc_info=True)
        return False


def delete_single_file(path):
    """
    Removes a media record (and its thumbnail) from the database.
    Used by the real-time watchdog watcher when a file deletion is detected.
    """
    from app.thumbnails import THUMB_DIR
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.execute("SELECT id FROM media WHERE path=?", (path,))
            row = c.fetchone()
            if row:
                media_id = row[0]
                c.execute("DELETE FROM media WHERE path=?", (path,))
                conn.commit()
                logger.info(f"Deleted media record for: {path} (id={media_id})")
                # Clean up associated thumbnail(s) - check both old .jpg and new .webp/.gif
                for ext in (".jpg", ".gif", ".webp"):
                    thumb_path = os.path.join(THUMB_DIR, f"{media_id}{ext}")
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                        logger.info(f"Deleted thumbnail: {thumb_path}")
            else:
                logger.debug(f"Delete event for unknown path (not in DB): {path}")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to delete record for {path}: {e}", exc_info=True)

def precompute_missing_thumbnails(batch_size=200, last_processed_id=0):
    """
    Finds missing thumbnails in the background and generates them.
    Returns (processed_any: bool, last_id: int) tuple.
    Uses pagination to avoid loading all media into memory.
    Adaptive batch size: starts large for catch-up, then smaller for responsiveness.
    """
    # Lazy import - only load when generating thumbnails
    from app.thumbnails import create_image_version, create_video_thumb, create_audio_thumb, THUMB_DIR
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Memory-efficient pagination: only load batch_size records at a time
        # Start from last_processed_id to avoid re-checking already processed files
        c.execute(
            "SELECT id, path, type FROM media WHERE id > ? ORDER BY id LIMIT ?",
            (last_processed_id, batch_size * 2)  # Query 2x batch to find enough missing ones
        )
        
        missing_items = []
        max_id_seen = last_processed_id
        for row in c:
            mid = row['id']
            max_id_seen = max(max_id_seen, mid)
            src = row['path']
            ftype = row['type']
            
            is_gif = src.lower().endswith(".gif")
            # Use WebP for most thumbnails, GIF only for original GIFs
            thumb_ext = ".gif" if is_gif else ".webp"
            dst = os.path.join(THUMB_DIR, f"{mid}{thumb_ext}")
            
            # Audio and Video thumbs are always .webp
            if ftype in ("audio", "video"):
                dst = os.path.join(THUMB_DIR, f"{mid}.webp")

            if not os.path.exists(dst):
                missing_items.append((dict(row), dst))
                if len(missing_items) >= batch_size:
                    break
                    
        conn.close()
    except Exception as e:
        logger.error(f"Database error while fetching media for thumbnails: {e}")
        return False, last_processed_id
                
    if not missing_items:
        # No more missing thumbnails in this batch - check if we've reached the end
        # If max_id_seen hasn't changed, we're done; reset to 0 for next full cycle
        if max_id_seen == last_processed_id:
            return False, 0
        # Otherwise, more records exist beyond this batch
        return False, max_id_seen
        
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
                 create_image_version(src_path, dst_path, size=(600, 600), quality=85)
            elif f_type == "audio":
                 create_audio_thumb(dst_path)
            else:
                 # Videos use smaller thumbnails (400x400) for faster generation
                 create_video_thumb(src_path, dst_path, size=(400, 400))
        except Exception as e:
            logger.error(f"Failed to precompute thumb for media ID {media_id}: {e}")
            
    # Use ThreadPoolExecutor with THUMB_WORKERS (4) for parallel generation
    with concurrent.futures.ThreadPoolExecutor(max_workers=THUMB_WORKERS) as executor:
        list(executor.map(process_thumb, missing_items))
        
    return True, max_id_seen
