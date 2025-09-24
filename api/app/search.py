from flask import Blueprint, request, jsonify
import sqlite3
from app.db import DB_PATH

search_bp = Blueprint("search", __name__)

@search_bp.route("/api/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Missing search query"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # MODIFICATION HERE
    c.execute("""
        SELECT id, filename, type, user_comment
        FROM media
        WHERE filename LIKE ? OR user_comment LIKE ? OR exif LIKE ?
        LIMIT 100
    """, (f'{q}*',))
    results = [dict(r) for r in c.fetchall()]
    conn.close()

    return jsonify(results)