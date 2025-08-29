import os
import shutil
import random
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
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
SCAN_INTERVAL_SECONDS = 300 # 5 minutes
MAX_WORKERS = os.cpu_count() or 4 # Use all available CPU cores for scanning

# --- Global variable to track scan status ---
SCAN_STATUS = {"scanning": False, "progress": 0, "total": 0}

# --- Directory Setup ---
os.makedirs(ALL_DIR, exist_ok=True)
os.makedirs(LIKED_DIR, exist_ok=True)
os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)


def get_latest_mod_time(directory):
    latest_mod = os.path.getmtime(directory)
    for root, dirs, files in os.walk(directory):
        for f in files: latest_mod = max(latest_mod, os.path.getmtime(os.path.join(root, f)))
        for d in dirs: latest_mod = max(latest_mod, os.path.getmtime(os.path.join(root, d)))
    return latest_mod

def process_image(full_path):
    """Worker function to process a single image in a thread."""
    global SCAN_STATUS
    try:
        relative_path = os.path.relpath(full_path, ALL_DIR).replace('\\', '/')
        with Image.open(full_path) as img:
            width, height = img.size
        SCAN_STATUS["progress"] += 1
        return {"path": relative_path, "width": width, "height": height}
    except (UnidentifiedImageError, FileNotFoundError):
        SCAN_STATUS["progress"] += 1
        return None

def scan_and_cache_files():
    """Scans all files in parallel and saves the result to a JSON cache file."""
    global SCAN_STATUS
    if SCAN_STATUS["scanning"]: return
    SCAN_STATUS = {"scanning": True, "progress": 0, "total": 0}
    print(f"Starting parallel directory scan with {MAX_WORKERS} workers...")
    
    # First, get a complete list of all file paths
    all_file_paths = [os.path.join(root, filename) for root, _, files in os.walk(ALL_DIR) for filename in files]
    SCAN_STATUS["total"] = len(all_file_paths)

    all_files_with_dims = []
    # Use ThreadPoolExecutor to process images in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_image, all_file_paths)
        # Filter out None results from non-image files
        all_files_with_dims = [res for res in results if res is not None]

    with open(FILE_LIST_CACHE, 'w') as f:
        json.dump(all_files_with_dims, f)
    
    SCAN_STATUS = {"scanning": False, "progress": SCAN_STATUS["total"], "total": SCAN_STATUS["total"]}
    print(f"Scan complete. Cached {len(all_files_with_dims)} files.")

def background_scanner_task():
    """A persistent background task that periodically checks for updates."""
    while True:
        try:
            if not os.path.exists(FILE_LIST_CACHE):
                print("Cache not found. Starting initial scan.")
                scan_and_cache_files()
            else:
                cache_mod_time = os.path.getmtime(FILE_LIST_CACHE)
                source_mod_time = get_latest_mod_time(ALL_DIR)
                if source_mod_time > cache_mod_time:
                    print("Source directory has been modified. Re-scanning...")
                    scan_and_cache_files()
                else:
                    print("No changes detected. Sleeping.")
        except Exception as e:
            print(f"Error in background scanner: {e}")
        
        time.sleep(SCAN_INTERVAL_SECONDS)

# --- API Endpoints ---
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
        if not SCAN_STATUS["scanning"]:
            threading.Thread(target=scan_and_cache_files, daemon=True).start()
        return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

# ... (The rest of your endpoints remain the same) ...
@app.route('/api/scan-status')
def get_scan_status():
    if not SCAN_STATUS["scanning"] and os.path.exists(FILE_LIST_CACHE):
         return jsonify({"status": "complete"})
    return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

@app.route('/api/files/random')
def random_files():
    try:
        count = int(request.args.get('count', 1))
        if not os.path.exists(FILE_LIST_CACHE): return jsonify([])
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
    if os.path.exists(FILE_LIST_CACHE):
        os.remove(FILE_LIST_CACHE)
        print("File list cache cleared.")
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
    if not SCAN_STATUS["scanning"]:
        threading.Thread(target=scan_and_cache_files, daemon=True).start()
    return jsonify({"message": "Cache cleanup successful. File list will be regenerated.", "deleted_files": deleted_count}), 200

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

scanner_thread = threading.Thread(target=background_scanner_task, daemon=True)
scanner_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)