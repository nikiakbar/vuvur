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
RECYCLE_BIN_DIR = '/mnt/gallery/recyclebin' # New Recycle Bin Path
DATA_DIR = '/app/data'

DB_PATH = os.path.join(DATA_DIR, 'vuvur.db')
PREVIEW_CACHE_DIR = os.path.join(DATA_DIR, 'cache_preview')
THUMB_CACHE_DIR = os.path.join(DATA_DIR, 'cache_thumb')
SETTINGS_PATH = os.path.join(DATA_DIR, 'settings.json')

PREVIEW_MAX_WIDTH, PREVIEW_QUALITY = 800, 90
THUMB_MAX_WIDTH, THUMB_QUALITY = 250, 80
SCAN_INTERVAL_SECONDS = 300
MAX_WORKERS = os.cpu_count() or 4
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.mkv', '.avi'}
SCAN_STATUS = {"scanning": False, "progress": 0, "total": 0}

for path in [IMAGE_DIR, VIDEO_DIR, LIKED_DIR, RECYCLE_BIN_DIR, DATA_DIR, PREVIEW_CACHE_DIR, THUMB_CACHE_DIR]:
    os.makedirs(path, exist_ok=True)

# --- DATABASE / HELPERS / SCANNER ---
def get_db():
    db = sqlite3.connect(DB_PATH); db.row_factory = sqlite3.Row; return db
def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS media (...)''') # Unchanged
def get_media_type(filename):
    return 'video' if os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS else 'image'
def get_source_dir(media_type):
    return VIDEO_DIR if media_type == 'video' else IMAGE_DIR
def get_exif_for_file(img_path):
    pass # Unchanged
def process_file(full_path):
    pass # Unchanged
def scan_and_cache_files():
    pass # Unchanged
def get_latest_mod_time(directory):
    pass # Unchanged
def background_scanner_task():
    pass # Unchanged
def load_settings():
    pass # Unchanged
def save_settings(new_settings):
    pass # Unchanged

# --- API ENDPOINTS ---
@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    pass # Unchanged
@app.route('/api/files')
def list_files():
    pass # Unchanged
@app.route('/api/scan-status')
def get_scan_status():
    pass # Unchanged
@app.route('/api/files/random')
def random_files():
    pass # Unchanged
@app.route('/api/random-single')
def random_single_file():
    pass # Unchanged
@app.route('/api/thumbnail/<path:filename>')
def serve_thumbnail(filename):
    pass # Unchanged
@app.route('/api/preview/<path:filename>')
def serve_preview_image(filename):
    pass # Unchanged
def generate_and_serve_cached_media(filename, cache_dir, max_width, quality):
    pass # Unchanged
@app.route('/api/view/all/<path:filename>')
def serve_full_file(filename):
    pass # Unchanged
@app.route('/api/like/<path:filename>', methods=['POST'])
def like_file(filename):
    pass # Unchanged


# --- UPDATED DELETE ENDPOINT ---
@app.route('/api/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    media_type = get_media_type(filename)
    source_dir = get_source_dir(media_type)
    file_path = os.path.join(source_dir, filename)
    
    if os.path.exists(file_path):
        try:
            # 1. Move the original file to the recycle bin
            recycle_path = os.path.join(RECYCLE_BIN_DIR, os.path.basename(filename))
            shutil.move(file_path, recycle_path)

            # 2. Delete the file from the database
            with get_db() as db:
                db.execute("DELETE FROM media WHERE path = ?", (filename,))
                db.commit()
            
            # 3. Delete its caches
            thumb_cache = os.path.join(THUMB_CACHE_DIR, filename)
            prev_cache = os.path.join(PREVIEW_CACHE_DIR, filename)
            if os.path.exists(thumb_cache): os.remove(thumb_cache)
            if os.path.exists(prev_cache): os.remove(prev_cache)
                
            return jsonify({"message": f"'{filename}' moved to recycle bin."})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "File not found"}), 404

# --- STARTUP ---
scanner_thread = threading.Thread(target=background_scanner_task, daemon=True)
scanner_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)