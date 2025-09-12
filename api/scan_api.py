from flask import Blueprint, jsonify
from .scanner import scan_media

scan_bp = Blueprint("scan", __name__)

@scan_bp.route("", methods=["POST"])
def trigger_scan():
    try:
        scan_media()
        return jsonify({"status": "ok", "message": "Scan completed"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
