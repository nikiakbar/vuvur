import os, json
from flask import Blueprint, jsonify, request

bp = Blueprint("settings", __name__)
SETTINGS_PATH = "/app/data/settings.json"

DEFAULTS = {
    "scan_interval": int(os.getenv("SCAN_INTERVAL", 15)),
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    return DEFAULTS.copy()

def save_settings(data):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f)

@bp.route("/api/settings", methods=["GET","POST"])
def settings():
    if request.method == "GET":
        return jsonify({
            "settings": load_settings(),
            "locked_keys": []
        })
    data = request.json or {}
    save_settings(data)
    return jsonify(load_settings())
