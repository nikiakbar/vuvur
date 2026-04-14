from flask import Flask
import os
from flasgger import Swagger
import logging
from filelock import FileLock, Timeout

from app import auth, db, gallery, groups, subgroups, like, scan_api, search, stream, random_scroller, thumbnails, health
from app import delete

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    swagger = Swagger(app)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "vuvur.sqlite"),
    )

    from logging.handlers import RotatingFileHandler
    
    # Configure logging
    log_dir = "/app/data/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    root_logger = logging.getLogger()
    
    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "api.log"),
        maxBytes=10*1024*1024, # 10MB
        backupCount=5
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    
    # Ensure the instance and data folders exist
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs("/app/data", exist_ok=True)
    except OSError as e:
        logging.error(f"Error creating directories: {e}")

    # Initialize the database with a lock to prevent contention
    # Multiple workers may try to set WAL mode simultaneously
    DB_INIT_LOCK_PATH = "/app/data/db_init.lock"
    db_init_lock = FileLock(DB_INIT_LOCK_PATH, timeout=10)
    
    try:
        with db_init_lock:
            with app.app_context():
                db.init_db()
                logging.info("Database initialized successfully")
    except Timeout:
        logging.info("Another worker is initializing database, skipping...")
    except Exception as e:
        logging.error(f"Error initializing database: {e}", exc_info=True)

    # Register blueprints
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(gallery.bp)
    app.register_blueprint(groups.bp)
    app.register_blueprint(subgroups.bp)
    app.register_blueprint(like.bp)
    app.register_blueprint(scan_api.scan_bp)
    app.register_blueprint(search.search_bp)
    # app.register_blueprint(settings.bp)
    app.register_blueprint(stream.stream_bp)
    app.register_blueprint(thumbnails.bp)
    app.register_blueprint(random_scroller.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(delete.bp)
    
    logging.info("API workers ready (scanner runs in separate service)")

    return app