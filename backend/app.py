import os
import shutil
import random
from flask import Flask, jsonify, send_from_directory, abort, send_file, request
from flask_cors import CORS
from PIL import Image
from io import BytesIO

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Configuration ---
MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media')
ALL_DIR = os.path.join(MEDIA_DIR, 'all')
LIKED_DIR = os.path.join(MEDIA_DIR, 'liked')
PREVIEW_MAX_WIDTH = 800

# --- Ensure media directories exist ---
os.makedirs(ALL_DIR, exist_ok=True)
os.makedirs(LIKED_DIR, exist_ok=True)

# --- API Endpoints ---
@app.route('/api/files')
def list_files():
    """Returns a list of filenames, sorted or shuffled."""
    sort_order = request.args.get('sort', 'default')
    try:
        files = [f for f in os.listdir(ALL_DIR) if os.path.isfile(os.path.join(ALL_DIR, f))]
        
        if sort_order == 'random':
            random.shuffle(files)
        else:
            files.sort()
            
        return jsonify(files)
    except FileNotFoundError:
        return jsonify([])

@app.route('/api/view/all/<path:filename>')
def serve_full_file(filename):
    """Serves the full-resolution file."""
    return send_from_directory(ALL_DIR, filename)

@app.route('/api/preview/<path:filename>')
def serve_preview_image(filename):
    """Serves a dynamically generated, compressed preview of an image."""
    img_path = os.path.join(ALL_DIR, filename)
    if not os.path.exists(img_path):
        abort(404)
    try:
        img = Image.open(img_path)
        if img.size[0] > PREVIEW_MAX_WIDTH:
            w_percent = (PREVIEW_MAX_WIDTH / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((PREVIEW_MAX_WIDTH, h_size), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img_io = BytesIO()
        img.save(img_io, 'JPEG', quality=85)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception:
        return send_from_directory(ALL_DIR, filename) # Fallback for non-images

@app.route('/api/like/<path:filename>', methods=['POST'])
def like_file(filename):
    """Moves a file to the 'liked' directory."""
    src_path = os.path.join(ALL_DIR, filename)
    if os.path.exists(src_path):
        shutil.move(src_path, os.path.join(LIKED_DIR, filename))
        return jsonify({"message": f"'{filename}' liked."}), 200
    return jsonify({"error": "File not found"}), 404

@app.route('/api/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    """Deletes a file."""
    file_path = os.path.join(ALL_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"'{filename}' deleted."}), 200
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)