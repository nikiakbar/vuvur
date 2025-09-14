from flask import Blueprint, jsonify
from app.scanner import scan
import os
import json

scan_bp = Blueprint("scan", __name__)
INITIAL_SCAN_FLAG_PATH = "/app/data/.initial_scan_complete"
SCAN_STATUS_PATH = "/app/data/scan_status.json"

@scan_bp.route("/api/scan/status", methods=["GET"])
def scan_status():
    """Checks the status of the library scan."""
    is_complete = os.path.exists(INITIAL_SCAN_FLAG_PATH)
    progress_data = {"progress": 0, "total": 0}
    if os.path.exists(SCAN_STATUS_PATH):
        try:
            with open(SCAN_STATUS_PATH, 'r') as f:
                progress_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass # Keep defaults if file is corrupt or missing
            
    return jsonify({
        "scan_complete": is_complete,
        "progress": progress_data["progress"],
        "total": progress_data["total"]
    })

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
        # To ensure a fresh scan, we must remove the flag file
        if os.path.exists(INITIAL_SCAN_FLAG_PATH):
            os.remove(INITIAL_SCAN_FLAG_PATH)
        scan()
        # ADD THIS BLOCK TO FIX THE ISSUE
        # Re-create the flag file to signal that the scan is done
        with open(INITIAL_SCAN_FLAG_PATH, 'w') as f:
            f.write('done')
        return jsonify({"message": "Library re-scan triggered successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500