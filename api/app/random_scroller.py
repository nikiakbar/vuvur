from flask import Blueprint, jsonify, request
from app.db import get_db

bp = Blueprint("random_scroller", __name__)

@bp.route("/api/files/random")
def random_files():
    """Get a list of random media files."""
    try:
        count = int(request.args.get("count", 1))
    except ValueError:
        count = 1
        
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM media ORDER BY RANDOM() LIMIT ?", (count,))
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(items)

@bp.route("/api/random-single")
def random_single():
    """Get a single random media file, optionally matching a query."""
    q = request.args.get("q", "").strip()
    
    conn = get_db()
    c = conn.cursor()
    
    sql = "SELECT * FROM media"
    params = []

    if q:
        sql += " WHERE filename LIKE ? OR user_comment LIKE ?"
        params.extend([f"%{q}%", f"%{q}%"])

    sql += " ORDER BY RANDOM() LIMIT 1"
    
    c.execute(sql, tuple(params))
    item = c.fetchone()
    conn.close()
    
    if not item:
        return jsonify({"error": "No media found"}), 404
        
    return jsonify([dict(item)])