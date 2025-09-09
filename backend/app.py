import os
import shutil
import random
import json
import time
import threading
import subprocess
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify, send_from_directory, abort, send_file, request
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
IMAGE_DIR = '/mnt/gallery/images'
VIDEO_DIR = '/mnt/gallery/videos'
LIKED_DIR = '/mnt/gallery/liked'
DATA_DIR = '/app/data'
DB_PATH = os.path.join(DATA_DIR, 'vuvur.db')
PREVIEW_CACHE_DIR = os.path.join(DATA_DIR, 'cache_preview')
THUMB_CACHE_DIR = os.path.join(DATA_DIR, 'cache_thumb')
SETTINGS_PATH = os.path.join(DATA_DIR, 'settings.json')
PREVIEW_MAX_WIDTH, PREVIEW_QUALITY = 800, 90
THUMB_MAX_WIDTH, THUMB_QUALITY = 250, 80
MAX_WORKERS = os.cpu_count() or 4
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.mkv', '.avi'}
SCAN_STATUS = {"scanning": False, "progress": 0, "total": 0}

for path in [IMAGE_DIR, VIDEO_DIR, LIKED_DIR, DATA_DIR, PREVIEW_CACHE_DIR, THUMB_CACHE_DIR]:
    os.makedirs(path, exist_ok=True)

# --- DATABASE SETUP ---
def get_db():
    db = sqlite3.connect(DB_PATH); db.row_factory = sqlite3.Row; return db
def init_db():
    with get_db() as db:
        db.execute('''
        CREATE TABLE IF NOT EXISTS media (
            path TEXT PRIMARY KEY, type TEXT NOT NULL, width INTEGER,
            height INTEGER, mod_time REAL NOT NULL, exif_json TEXT
        )''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_mod_time ON media (mod_time)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_type ON media (type)')
        db.commit()

# --- HELPER FUNCTIONS ---
def get_media_type(filename):
    return 'video' if os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS else 'image'
def get_source_dir(media_type):
    return VIDEO_DIR if media_type == 'video' else IMAGE_DIR
def get_exif_for_file(img_path):
    try:
        img = Image.open(img_path)
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
        return json.dumps(exif_data, default=str)
    except Exception:
        return "{}"

# --- BACKGROUND SCANNER ---
def process_file(full_path):
    global SCAN_STATUS
    try:
        media_type = get_media_type(full_path)
        source_dir = get_source_dir(media_type)
        relative_path = os.path.relpath(full_path, source_dir).replace('\\', '/')
        mod_time = os.path.getmtime(full_path)
        width, height, exif_json = 0, 0, "{}"
        if media_type == 'image':
            with Image.open(full_path) as img:
                width, height = img.size
            exif_json = get_exif_for_file(full_path)
        SCAN_STATUS["progress"] += 1
        return (relative_path, media_type, width, height, mod_time, exif_json)
    except Exception:
        SCAN_STATUS["progress"] += 1
        return None

def scan_and_cache_files():
    global SCAN_STATUS
    if SCAN_STATUS["scanning"]: return
    SCAN_STATUS = {"scanning": True, "progress": 0, "total": 0}
    print(f"Starting parallel media index scan with {MAX_WORKERS} workers...")
    init_db() 
    paths = [os.path.join(root, f) for d in [IMAGE_DIR, VIDEO_DIR] for root, _, files in os.walk(d) for f in files]
    SCAN_STATUS["total"] = len(paths)
    media_data = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_file, paths)
        media_data = [res for res in results if res is not None]
    print(f"Indexing {len(media_data)} items into database...")
    with get_db() as db:
        db.execute("DELETE FROM media") 
        db.executemany("INSERT OR REPLACE INTO media (path, type, width, height, mod_time, exif_json) VALUES (?, ?, ?, ?, ?, ?)", media_data)
        db.commit()
    SCAN_STATUS = {"scanning": False, "progress": SCAN_STATUS["total"], "total": SCAN_STATUS["total"]}
    print(f"Scan complete. Indexed {len(media_data)} media files.")

def get_latest_mod_time(directory):
    latest_mod = os.path.getmtime(directory)
    for root, dirs, files in os.walk(directory):
        for f in files: latest_mod = max(latest_mod, os.path.getmtime(os.path.join(root, f)))
        for d in dirs: latest_mod = max(latest_mod, os.path.getmtime(os.path.join(root, d)))
    return latest_mod

def background_scanner_task():
    print("Background scanner thread started. Waiting 10s for app startup...")
    time.sleep(10)
    print("Scanner awake. Starting main loop.")
    
    while True:
        scan_needed = False
        try:
            init_db() 
            db_populated = False
            if os.path.exists(DB_PATH):
                 with get_db() as db:
                    try:
                        count = db.execute("SELECT COUNT(1) FROM media").fetchone()[0]
                        if count > 0:
                            db_populated = True
                    except sqlite3.OperationalError:
                        db_populated = False 

            if not db_populated:
                print("Database is empty or missing. Starting initial scan.")
                scan_needed = True
            else:
                db_mod_time = os.path.getmtime(DB_PATH) 
                img_mod_time = get_latest_mod_time(IMAGE_DIR)
                vid_mod_time = get_latest_mod_time(VIDEO_DIR)
                source_mod_time = max(img_mod_time, vid_mod_time)
                
                if source_mod_time > db_mod_time:
                    print("Source directory has been modified. Re-scanning...")
                    scan_needed = True
                else:
                    print("No changes detected.")
            
            if scan_needed:
                scan_and_cache_files()

        except Exception as e:
            print(f"Error in background scanner check: {e}")

        # --- CONSOLIDATED SLEEP LOGIC ---
        try:
            settings = load_settings()
            scan_interval = settings.get('scan_interval', 3600)
            if scan_interval <= 0:
                print("Periodic scanning disabled. Checking again in 5 minutes.")
                time.sleep(300)
            else:
                print(f"Sleeping for {scan_interval} seconds.")
                time.sleep(scan_interval)
        except Exception as e:
            print(f"Error in scanner sleep cycle: {e}")
            time.sleep(300)

# --- SETTINGS MANAGEMENT ---
DEFAULT_SETTINGS = {'scan_interval': 3600, 'batch_size': 20, 'preload_count': 3, 'zoom_level': 2.5}
LOCKED_SETTINGS = set()

def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, 'r') as f: settings.update(json.load(f))
        except json.JSONDecodeError: pass 
    
    env_scan = os.environ.get('SCAN_INTERVAL')
    if env_scan is not None: settings['scan_interval'] = int(env_scan); LOCKED_SETTINGS.add('scan_interval')
    env_batch = os.environ.get('GALLERY_BATCH_SIZE')
    if env_batch is not None: settings['batch_size'] = int(env_batch); LOCKED_SETTINGS.add('batch_size')
    env_preload = os.environ.get('RANDOM_PRELOAD_COUNT')
    if env_preload is not None: settings['preload_count'] = int(env_preload); LOCKED_SETTINGS.add('preload_count')
    env_zoom = os.environ.get('ZOOM_LEVEL')
    if env_zoom is not None: settings['zoom_level'] = float(env_zoom); LOCKED_SETTINGS.add('zoom_level')
    return settings

def save_settings(new_settings):
    current_settings = load_settings()
    for key, value in new_settings.items():
        if key not in LOCKED_SETTINGS:
            current_settings[key] = value
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(current_settings, f, indent=2)
    return current_settings

# --- API ENDPOINTS ---
@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        user_settings = request.json
        new_settings = save_settings(user_settings)
        return jsonify(new_settings)
    settings = load_settings()
    return jsonify({"settings": settings, "locked_keys": list(LOCKED_SETTINGS)})

@app.route('/api/files')
def list_files():
    if not os.path.exists(DB_PATH) or (SCAN_STATUS["scanning"] and SCAN_STATUS["progress"] == 0):
        if not SCAN_STATUS["scanning"]:
             threading.Thread(target=scan_and_cache_files, daemon=True).start()
        return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})
    try:
        init_db() 
        settings = load_settings()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', settings.get('batch_size', 20)))
        offset = (page - 1) * limit
        sort_by = request.args.get('sort', 'random')
        query_q = request.args.get('q', '').lower()
        query_exif = request.args.get('exif_q', '').lower()
        params = []
        sql_query = "SELECT path, type, width, height, mod_time, exif_json FROM media"
        where_clauses = []
        if query_q:
            where_clauses.append("path LIKE ?"); params.append(f"%{query_q}%")
        if query_exif:
            where_clauses.append("exif_json LIKE ?"); params.append(f"%{query_exif}%")
        if where_clauses:
            sql_query += " WHERE " + " AND ".join(where_clauses)
        with get_db() as db:
            total_count_result = db.execute(f"SELECT COUNT(1) FROM ({sql_query}) AS base_query", params).fetchone()
            total_count = total_count_result[0] if total_count_result else 0
        sort_map = {'date_desc': 'mod_time DESC', 'date_asc': 'mod_time ASC', 'file_asc': 'path ASC', 'file_desc': 'path DESC', 'random': 'RANDOM()'}
        order_by = sort_map.get(sort_by, 'RANDOM()')
        sql_query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with get_db() as db:
            results = db.execute(sql_query, params).fetchall()
            items = []
            for row in results:
                exif_string = row['exif_json'] or '{}'
                items.append({
                    "path": row['path'],
                    "type": row['type'],
                    "width": row['width'],
                    "height": row['height'],
                    "mod_time": row['mod_time'],
                    "exif": json.loads(exif_string)
                })
        return jsonify({"total_items": total_count, "page": page, "total_pages": (total_count // limit) + 1, "items": items})
    except Exception as e:
        print(f"Error in list_files: {e}")
        return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

@app.route('/api/scan-status')
def get_scan_status():
    if not SCAN_STATUS["scanning"] and os.path.exists(DB_PATH): 
        return jsonify({"status": "complete"})
    return jsonify({"status": "scanning", "progress": SCAN_STATUS["progress"], "total": SCAN_STATUS["total"]})

@app.route('/api/files/random')
def random_files():
    count = int(request.args.get('count', 1))
    if not os.path.exists(DB_PATH): return jsonify([])
    try:
        init_db() 
        with get_db() as db:
            results = db.execute("SELECT path, type, width, height, mod_time, exif_json FROM media ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
            items = []
            for row in results:
                exif_string = row['exif_json'] or '{}'
                items.append({
                    "path": row['path'],
                    "type": row['type'],
                    "width": row['width'],
                    "height": row['height'],
                    "mod_time": row['mod_time'],
                    "exif": json.loads(exif_string)
                })
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
                    w_percent = (max_width / float(img.size[0])); h_size = int((float(img.size[1]) * float(w_percent)))
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
        print(f"Error generating thumbnail for {filename}: {e}"); abort(500)

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
            dir_path = os.path.dirname(file_path);
            if not os.listdir(dir_path): os.rmdir(dir_path)
        except OSError: pass
        return jsonify({"message": f"'{filename}' deleted."})
    return jsonify({"error": "File not found"}), 404

@app.route('/api/cache/cleanup', methods=['POST'])
def cleanup_cache():
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    for cache_dir in [PREVIEW_CACHE_DIR, THUMB_CACHE_DIR]:
        if os.path.exists(cache_dir): shutil.rmtree(cache_dir); os.makedirs(cache_dir)
    if not SCAN_STATUS["scanning"]:
        threading.Thread(target=scan_and_cache_files, daemon=True).start()
    return jsonify({"message": "Database and all caches cleared. A new library scan has started."})

scanner_thread = threading.Thread(target=background_scanner_task, daemon=True)
scanner_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)