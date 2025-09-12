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

    # FTS MATCH query (fast full-text search)
    c.execute("""
        SELECT m.id, m.filename, m.type, m.user_comment
        FROM media_fts f
        JOIN media m ON m.id = f.rowid
        WHERE media_fts MATCH ?
        ORDER BY rank
        LIMIT 100
    """, (q,))
    results = [dict(r) for r in c.fetchall()]
    conn.close()

    return jsonify(results)
