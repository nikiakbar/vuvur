from flask import Blueprint, request, jsonify
import sqlite3
from app.db import DB_PATH
from app.api_key_middleware import api_key_required
from app.auth_middleware import login_required

search_bp = Blueprint("search", __name__)
@search_bp.route("/api/search")
@api_key_required
@login_required
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Missing search query"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ⚡ Bolt: Optimized search using FTS5 and fixed parameter binding mismatch.
    # Expected impact: Reduces search latency from O(N) to O(log N) using the FTS5 index.
    # Fixes a bug where 3 placeholders were used with only 1 parameter.
    c.execute("""
        SELECT m.id, m.filename, m.type, m.user_comment
        FROM media_fts f
        JOIN media m ON m.id = f.rowid
        WHERE media_fts MATCH ?
        LIMIT 100
    """, (f'{q}*',))
    results = [dict(r) for r in c.fetchall()]
    conn.close()

    return jsonify(results)