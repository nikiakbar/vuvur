from flask import Flask
import os
from flasgger import Swagger
import logging
import threading
import time
from app.scanner import scan
from app import auth, db, gallery, like, scan_api, search, settings, stream, thumbnail, random_scroller

def run_scan_scheduler():
    """Periodically runs the scanner based on the SCAN_INTERVAL."""
    interval = int(os.environ.get("SCAN_INTERVAL", 3600))
    if interval == 0:
        logging.info("Periodic scanning is disabled as SCAN_INTERVAL is set to 0.")
        return
        
    logging.info(f"Scanner will run every {interval} seconds.")
    while True:
        scan()
        time.sleep(interval)
        
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
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize the database
    with app.app_context():
        db.init_db()

    # Register blueprints
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(gallery.bp)
    app.register_blueprint(like.bp)
    app.register_blueprint(scan_api.scan_bp)
    app.register_blueprint(search.search_bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(stream.stream_bp)
    app.register_blueprint(thumbnail.bp)
    app.register_blueprint(random_scroller.bp) # Add this line
    # Run the initial scan in a separate thread to avoid blocking the server startup
    initial_scan_thread = threading.Thread(target=run_scan_scheduler, daemon=True)
    initial_scan_thread.start()

    return app