from flask import Blueprint, jsonify
from app.auth_middleware import login_required

# Create a new blueprint
bp = Blueprint("health", __name__)
@bp.route("/healthz")
@login_required
def health_check():
    """
    A simple health check endpoint that returns a 200 OK response.
    """
    return jsonify({"status": "ok"}), 200