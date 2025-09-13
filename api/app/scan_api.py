from flask import Blueprint, jsonify
from app.scanner import scan

scan_bp = Blueprint("scan", __name__)

@scan_bp.route("/api/scan", methods=["POST"])
def trigger_scan():
    """Triggers a library scan."""
    try:
        scan()
        return jsonify({"status": "ok", "message": "Scan completed"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@scan_bp.route("/api/cache/cleanup", methods=["POST"])
def cleanup_cache():
    """Triggers a library re-scan."""
    try:
        scan()
        return jsonify({"message": "Library re-scan triggered successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500