import os
import shutil
import random
import json
import time
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, send_from_directory, abort, send_file, request
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS

app = Flask(__name__)
CORS(app)

# --- NEW PATH CONFIGURATION ---
IMAGE_DIR = '/mnt/gallery/images'
VIDEO_DIR = '/mnt/gallery/videos'
LIKED_DIR = '/mnt/gallery/liked'
DATA_DIR = '/app/data'

PREVIEW_CACHE_DIR = os.path.join(DATA_DIR, 'cache_preview')
THUMB_CACHE_DIR = os.path.join(DATA_DIR, 'cache_thumb')
FILE_LIST_CACHE = os.path.join(DATA_DIR, 'file_list_cache.json')

PREVIEW_MAX_WIDTH, PREVIEW_QUALITY = 800, 90
THUMB_MAX_WIDTH, THUMB_QUALITY = 250, 80
SCAN_INTERVAL_SECONDS = 300
MAX_WORKERS = os.cpu_count() or 4
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.mkv', '.avi'}
SCAN_STATUS = {"scanning": False, "progress": 0, "total": 0}

for path in [IMAGE_DIR, VIDEO_DIR, LIKED_DIR, DATA_DIR, PREVIEW_CACHE_DIR, THUMB_CACHE_DIR]:
    os.makedirs(path, exist_ok=True)

# --- HELPER FUNCTIONS ---
def get_media_type(filename):
    return 'video' if os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS else 'image'

def get_source_dir(media_type):
    return VIDEO_DIR if media_type == 'video' else IMAGE_DIR

# --- BACKGROUND SCANNER ---
def process_file(full_path):
    global SCAN_STATUS
    try:
        media_type = get_media_type(full_path)
        source_dir = get_source_dir(media_type)
        relative_path = os.path.relpath(full_path, source_dir).replace('\\', '/')
        width, height = 0, 0
        if media_type == 'image':
            with Image.open(full_path) as img:
                width, height = img.size
        SCAN_STATUS["progress"] += 1
        return {"path": relative_path, "width": width, "height": height, "type": media_type}
    except Exception:
        SCAN_STATUS["progress"] += 1
        return None

def scan_and_cache_files():
    global SCAN_STATUS
    if SCAN_STATUS["scanning"]: return
    SCAN_STATUS = {"scanning": True, "progress": 0, "total": 0}
    print(f"Starting parallel media scan with {MAX_WORKERS} workers...")
    paths = [os.path.join(root, f) for d in [IMAGE_DIR, VIDEO_DIR] for root, _, files in os.walk(d) for f in files]
    SCAN_STATUS["total"] = len(paths)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_file, paths)
        all_media = [res for res in results if res is not None]

    with open(FILE_LIST_CACHE, 'w') as f: json.dump(all_media, f)
    SCAN_STATUS = {"scanning": False, "progress": SCAN_STATUS["total"], "total": SCAN_STATUS["total"]}
    print(f"Scan complete. Cached {len(all_media)} media files.")

def get_latest_mod_time(directory):
    latest_mod = os.path.getmtime(directory)
    for root, dirs, files in os.walk(directory):
        for f in files: latest_mod = max(latest_mod, os.path.getmtime(os.path.join(root, f)))
        for d in dirs: latest_mod = max(latest_mod, os.path.getmtime(os.path.join(root, d)))
    return latest_mod

def background_scanner_task():
    while True:
        try:
            if not os.path.exists(FILE_LIST_CACHE):
                scan_and_cache_files()
            else:
                cache_mod_time = os.path.getmtime(FILE_LIST_CACHE)
                img_mod_time = get_latest_mod_time(IMAGE_DIR)
                vid_mod_time = get_latest_mod_time(VIDEO_DIR)
                source_mod_time = max(img_mod_time, vid_mod_time)
                if source_mod_time > cache_mod_time:
                    scan_and_cache_files()
        except Exception as e:
            print(f"Error in background scanner: {e}")
        time.sleep(SCAN_INTERVAL_SECONDS)

def get_files_from_cache():
    if not os.path.exists(FILE_LIST_CACHE): return None
    with open(FILE_LIST_CACHE, 'r') as f: return json.load(f)

# --- API ENDPOINTS ---
@app.route('/api/files')
def list_files():
    files_data = get_files_from_cache()
    if files_data is None:
        return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})
    sort_order = request.args.get('sort', 'default')
    if sort_order == 'random': random.shuffle(files_data)
    else: files_data.sort(key=lambda x: x['path'])
    return jsonify(files_data)

@app.route('/api/scan-status')
def get_scan_status():
    if not SCAN_STATUS["scanning"] and os.path.exists(FILE_LIST_CACHE): return jsonify({"status": "complete"})
    return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

@app.route('/api/files/random')
def random_files():
    count = int(request.args.get('count', 1))
    all_files = get_files_from_cache()
    if not all_files: return jsonify([])
    count = min(count, len(all_files))
    return jsonify(random.sample(all_files, k=count))

@app.route('/api/thumbnail/<path:filename>')
def serve_thumbnail(filename):
    return generate_and_serve_cached_media(filename, THUMB_CACHE_DIR, THUMB_MAX_WIDTH, THUMB_QUALITY)

@app.route('/api/preview/<path:filename>')
def serve_preview_image(filename):
    return generate_and_serve_cached_media(filename, PREVIEW_CACHE_DIR, PREVIEW_MAX_WIDTH, PREVIEW_QUALITY)

def generate_and_serve_cached_media(filename, cache_dir, max_width, quality):
    cache_path = os.path.join(cache_dir, filename)
    if os.path.exists(cache_path): return send_from_directory(cache_dir, filename)

    media_type = get_media_type(filename)
    source_dir = get_source_dir(media_type)
    source_path = os.path.join(source_dir, filename)
    if not os.path.exists(source_path): abort(404)
    
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    try:
        if media_type == 'image':
            with Image.open(source_path) as img:
                if img.size[0] > max_width:
                    w_percent = (max_width / float(img.size[0]))
                    h_size = int((float(img.size[1]) * float(w_percent)))
                    img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(cache_path, 'JPEG', quality=quality)
        elif media_type == 'video':
            subprocess.run([
                'ffmpeg', '-i', source_path, '-ss', '00:00:01.000', '-vframes', '1',
                '-vf', f'scale={max_width}:-1', cache_path
            ], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        return send_from_directory(cache_dir, filename)
    except Exception as e:
        print(f"Error generating thumbnail for {filename}: {e}")
        abort(500)

@app.route('/api/exif/<path:filename>')
def get_exif_data(filename):
    source_path = os.path.join(IMAGE_DIR, filename)
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

@app.route('/api/view/all/<path:filename>')
def serve_full_file(filename):
    source_dir = get_source_dir(get_media_type(filename))
    return send_from_directory(source_dir, filename)

@app.route('/api/like/<path:filename>', methods=['POST'])
def like_file(filename):
    source_dir = get_source_dir(get_media_type(filename))
    src_path = os.path.join(source_dir, filename)
    if os.path.exists(src_path):
        dest_filename = os.path.basename(filename)
        shutil.move(src_path, os.path.join(LIKED_DIR, dest_filename))
        return jsonify({"message": f"'{filename}' liked."})
    return jsonify({"error": "File not found"}), 404

@app.route('/api/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    source_dir = get_source_dir(get_media_type(filename))
    file_path = os.path.join(source_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        try:
            dir_path = os.path.dirname(file_path)
            if not os.listdir(dir_path): os.rmdir(dir_path)
        except OSError: pass
        return jsonify({"message": f"'{filename}' deleted."})
    return jsonify({"error": "File not found"}), 404

@app.route('/api/cache/cleanup', methods=['POST'])
def cleanup_cache():
    if os.path.exists(FILE_LIST_CACHE): os.remove(FILE_LIST_CACHE)
    # Delete thumbnail/preview caches
    for cache_dir in [PREVIEW_CACHE_DIR, THUMB_CACHE_DIR]:
        if os.path.exists(cache_dir): shutil.rmtree(cache_dir)
        os.makedirs(cache_dir)
    # Trigger a new scan immediately
    if not SCAN_STATUS["scanning"]:
        threading.Thread(target=scan_and_cache_files, daemon=True).start()
    return jsonify({"message": "All caches cleared. A new library scan has started."})

scanner_thread = threading.Thread(target=background_scanner_task, daemon=True)
scanner_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)