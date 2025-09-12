from flask import Flask
import os

from app import auth, db, gallery, like, scan_api, search, settings, stream, thumbnails

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "vuvur.sqlite"),
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
    app.register_blueprint(thumbnails.bp)

    # a simple page that says hello
    @app.route("/hello")
    def hello():
        return "Hello, World!"

    return app