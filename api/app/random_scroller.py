from flask import Blueprint, jsonify, request
from app.db import get_db
from app.api_key_middleware import api_key_required

bp = Blueprint("random_scroller", __name__)
@bp.route("/api/files/random")
@api_key_required
def random_files():
    """Get a list of random media files."""
    try:
        count = int(request.args.get("count", 1))
    except ValueError:
        count = 1
        
    conn = get_db()
    c = conn.cursor()
    # ⚡ Bolt: Late Row Lookup optimization.
    # Sorting only the IDs by RANDOM() is significantly faster than sorting full rows (with EXIF).
    c.execute("""
        SELECT m.* FROM media m
        JOIN (SELECT id FROM media ORDER BY RANDOM() LIMIT ?) as t ON m.id = t.id
    """, (count,))
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(items)

@bp.route("/api/random-single")
@api_key_required
def random_single():
    """Get a single random media file, optionally matching a query."""
    q = request.args.get("q", "").strip()
    
    conn = get_db()
    c = conn.cursor()
    
    item = None
    if q:
        # ⚡ Bolt: Late Row Lookup for random selection with FTS.
        c.execute("""
            SELECT m.*
            FROM media m
            JOIN (
                SELECT rowid
                FROM media_fts
                WHERE media_fts MATCH ?
                ORDER BY RANDOM()
                LIMIT 1
            ) as t ON m.id = t.rowid
        """, (f'{q}*',))
        item = c.fetchone()
    else:
        # ⚡ Bolt: Late Row Lookup for random selection from entire library.
        c.execute("""
            SELECT m.* FROM media m
            JOIN (SELECT id FROM media ORDER BY RANDOM() LIMIT 1) as t ON m.id = t.id
        """)
        item = c.fetchone()
        
    conn.close()
    
    if not item:
        return jsonify({"error": "No media found matching that query."}), 404
        
    return jsonify([dict(item)])