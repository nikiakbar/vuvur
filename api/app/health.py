from flask import Blueprint, jsonify
from app.api_key_middleware import api_key_required

# Create a new blueprint
bp = Blueprint("health", __name__)
@api_key_required
@bp.route("/healthz")
def health_check():
    """
    A simple health check endpoint that returns a 200 OK response.
    """
    return jsonify({"status": "ok"}), 200