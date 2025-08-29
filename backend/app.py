import os
import shutil
import random
import json
import time
import threading
from flask import Flask, jsonify, send_from_directory, abort, send_file, request
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from io import BytesIO

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# --- Configuration ---
MEDIA_DIR = '/mnt' 
ALL_DIR = os.path.join(MEDIA_DIR, 'all')
LIKED_DIR = os.path.join(MEDIA_DIR, 'liked')
PREVIEW_CACHE_DIR = os.path.join(MEDIA_DIR, 'cache_preview')
THUMB_CACHE_DIR = os.path.join(MEDIA_DIR, 'cache_thumb')
FILE_LIST_CACHE = os.path.join(MEDIA_DIR, 'file_list_cache.json')
PREVIEW_MAX_WIDTH, PREVIEW_QUALITY = 800, 90
THUMB_MAX_WIDTH, THUMB_QUALITY = 250, 80

# --- Global variable to track scan status ---
SCAN_STATUS = {"scanning": False, "progress": 0, "total": 0}

# --- Directory Setup ---
os.makedirs(ALL_DIR, exist_ok=True)
os.makedirs(LIKED_DIR, exist_ok=True)
os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)


def scan_and_cache_files():
    """Scans all files and saves the result to a JSON cache file."""
    global SCAN_STATUS
    if SCAN_STATUS["scanning"]:
        return

    SCAN_STATUS = {"scanning": True, "progress": 0, "total": 0}
    print("Starting background directory scan...")

    # First, count total files for progress tracking
    total_files = sum(len(files) for _, _, files in os.walk(ALL_DIR))
    SCAN_STATUS["total"] = total_files
    
    all_files_with_dims = []
    scanned_count = 0
    for root, _, files in os.walk(ALL_DIR):
        for filename in files:
            try:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, ALL_DIR).replace('\\', '/')
                with Image.open(full_path) as img:
                    width, height = img.size
                all_files_with_dims.append({
                    "path": relative_path, "width": width, "height": height
                })
            except (UnidentifiedImageError, FileNotFoundError):
                pass
            finally:
                scanned_count += 1
                SCAN_STATUS["progress"] = scanned_count

    with open(FILE_LIST_CACHE, 'w') as f:
        json.dump(all_files_with_dims, f)
    
    SCAN_STATUS = {"scanning": False, "progress": total_files, "total": total_files}
    print(f"Scan complete. Cached {len(all_files_with_dims)} files.")
    return all_files_with_dims

def background_scanner_task():
    """The task for the background thread."""
    if not os.path.exists(FILE_LIST_CACHE):
        scan_and_cache_files()

@app.route('/api/files')
def list_files():
    """Returns file list if cache exists, otherwise returns scan status."""
    if os.path.exists(FILE_LIST_CACHE):
        with open(FILE_LIST_CACHE, 'r') as f:
            all_files_with_dims = json.load(f)
        
        sort_order = request.args.get('sort', 'default')
        if sort_order == 'random':
            random.shuffle(all_files_with_dims)
        else:
            all_files_with_dims.sort(key=lambda x: x['path'])
        return jsonify(all_files_with_dims)
    else:
        # If scan isn't running, start it
        if not SCAN_STATUS["scanning"]:
            threading.Thread(target=scan_and_cache_files, daemon=True).start()
        return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

@app.route('/api/scan-status')
def get_scan_status():
    """Endpoint for the frontend to poll for scan progress."""
    if not SCAN_STATUS["scanning"] and os.path.exists(FILE_LIST_CACHE):
         return jsonify({"status": "complete"})
    return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

# ... (The rest of your endpoints: /random, /exif, /thumbnail, etc. remain the same) ...
@app.route('/api/files/random')
def random_files():
    try:
        count = int(request.args.get('count', 1))
        if not os.path.exists(FILE_LIST_CACHE): return jsonify([]) # Return empty if cache not built
        with open(FILE_LIST_CACHE, 'r') as f: all_files = json.load(f)
        if not all_files: return jsonify([])
        count = min(count, len(all_files))
        random_sample = random.sample(all_files, k=count)
        return jsonify(random_sample)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exif/<path:filename>')
def get_exif_data(filename):
    source_path = os.path.join(ALL_DIR, filename)
    if not os.path.exists(source_path): abort(404)
    try:
        img = Image.open(source_path)
        exif_data = {}
        if hasattr(img, '_getexif'):
            exif_info = img._getexif()
            if exif_info:
                for tag, value in exif_info.items():
                    decoded_tag = TAGS.get(tag, tag)
                    if isinstance(value, bytes):
                        try: value = value.decode('utf-8', errors='ignore')
                        except: value = repr(value)
                    exif_data[decoded_tag] = value
        if 'parameters' in img.info: exif_data['parameters'] = img.info['parameters']
        elif 'Comment' in exif_data: exif_data['parameters'] = exif_data['Comment']
        return jsonify(exif_data)
    except Exception as e:
        return jsonify({"error": f"Could not read EXIF data: {str(e)}"})

@app.route('/api/thumbnail/<path:filename>')
def serve_thumbnail(filename):
    return generate_and_serve_image(filename, THUMB_CACHE_DIR, THUMB_MAX_WIDTH, THUMB_QUALITY)

@app.route('/api/preview/<path:filename>')
def serve_preview_image(filename):
    return generate_and_serve_image(filename, PREVIEW_CACHE_DIR, PREVIEW_MAX_WIDTH, PREVIEW_QUALITY)

def generate_and_serve_image(filename, cache_dir, max_width, quality):
    cache_path = os.path.join(cache_dir, filename)
    if os.path.exists(cache_path): return send_from_directory(cache_dir, filename)
    source_path = os.path.join(ALL_DIR, filename)
    if not os.path.exists(source_path): abort(404)
    try:
        img = Image.open(source_path)
        if img.size[0] > max_width:
            w_percent = (max_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        img.save(cache_path, 'JPEG', quality=quality)
        return send_from_directory(cache_dir, filename)
    except Exception:
        return send_from_directory(ALL_DIR, filename)

@app.route('/api/cache/cleanup', methods=['POST'])
def cleanup_cache():
    # When cleaning up, also delete the file list cache to force a new scan
    if os.path.exists(FILE_LIST_CACHE):
        os.remove(FILE_LIST_CACHE)
        print("File list cache cleared.")
    # ... (rest of cleanup logic is the same)
    deleted_count = 0
    source_files = set()
    for root, _, files in os.walk(ALL_DIR):
        for filename in files:
            relative_path = os.path.relpath(os.path.join(root, filename), ALL_DIR).replace('\\', '/')
            source_files.add(relative_path)
    for cache_dir in [PREVIEW_CACHE_DIR, THUMB_CACHE_DIR]:
        for root, _, files in os.walk(cache_dir):
            for filename in files:
                cached_file_rel_path = os.path.relpath(os.path.join(root, filename), cache_dir).replace('\\', '/')
                if cached_file_rel_path not in source_files:
                    os.remove(os.path.join(root, filename))
                    deleted_count += 1
    return jsonify({"message": "Cache cleanup successful. File list will be regenerated on next visit.", "deleted_files": deleted_count}), 200

@app.route('/api/view/all/<path:filename>')
def serve_full_file(filename):
    return send_from_directory(ALL_DIR, filename)

@app.route('/api/like/<path:filename>', methods=['POST'])
def like_file(filename):
    src_path = os.path.join(ALL_DIR, filename)
    if os.path.exists(src_path):
        dest_filename = os.path.basename(filename)
        shutil.move(src_path, os.path.join(LIKED_DIR, dest_filename))
        return jsonify({"message": f"'{filename}' liked."}), 200
    return jsonify({"error": "File not found"}), 404

@app.route('/api/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    file_path = os.path.join(ALL_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        try:
            dir_path = os.path.dirname(file_path)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
        except OSError:
            pass
        return jsonify({"message": f"'{filename}' deleted."}), 200
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    # Start the background scanner thread if the cache doesn't exist.
    if not os.path.exists(FILE_LIST_CACHE):
       scanner_thread = threading.Thread(target=background_scanner_task, daemon=True)
       scanner_thread.start()
    app.run(host='0.0.0.0', port=5000)