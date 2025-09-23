from flask import Flask
import os
from flasgger import Swagger
import logging
import threading
import time
from filelock import FileLock, Timeout

from app.scanner import scan
from app import auth, db, gallery, like, scan_api, search, stream, random_scroller, thumbnails, health

# Define paths globally for clarity
LOCK_PATH = "/app/data/scanner.lock"

def run_scanner_manager():
    """
    Manages the scanning process for periodic scans.
    The initial scan is now handled by the run.sh startup script.
    """
    interval = int(os.environ.get("SCAN_INTERVAL", 3600))
    lock = FileLock(LOCK_PATH, timeout=10)

    # --- PERIODIC SCANNING ---
    if interval == 0:
        logging.info("SCAN_INTERVAL is 0. Periodic scanning is disabled.")
        return
        
    logging.info(f"Periodic scanner will run every {interval} seconds.")
    while True:
        time.sleep(interval)
        try:
            with lock:
                logging.info("Starting periodic background scan...")
                scan()
                logging.info("Periodic background scan finished.")
        except Timeout:
            logging.warning("Could not acquire lock for periodic scan; it may be running in another process.")
        
def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    swagger = Swagger(app)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "vuvur.sqlite"),
    )

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure the instance and data folders exist
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs("/app/data", exist_ok=True)
    except OSError as e:
        logging.error(f"Error creating directories: {e}")

    # Initialize the database
    with app.app_context():
        db.init_db()

    # Register blueprints
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(gallery.bp)
    app.register_blueprint(like.bp)
    app.register_blueprint(scan_api.scan_bp)
    app.register_blueprint(search.search_bp)
    # app.register_blueprint(settings.bp)
    app.register_blueprint(stream.stream_bp)
    app.register_blueprint(thumbnails.bp)
    app.register_blueprint(random_scroller.bp)
    app.register_blueprint(health.bp)
    
    # Start the scanner manager in a background thread
    scan_thread = threading.Thread(target=run_scanner_manager, daemon=True)
    scan_thread.start()

    return app