import os
import shutil
from flask import Flask, jsonify, send_from_directory, abort, send_file
from flask_cors import CORS # Import CORS
from PIL import Image
from io import BytesIO

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Configuration & Other Code ---
# (The rest of your app.py code remains the same)
# ...
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media')
ALL_DIR = os.path.join(MEDIA_DIR, 'all')
LIKED_DIR = os.path.join(MEDIA_DIR, 'liked')

# (Ensure your API routes and logic are here)
# ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)