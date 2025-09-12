from flask import Blueprint, jsonify, request
from app.db import get_db

bp = Blueprint("gallery", __name__)

@bp.route("/api/gallery")
def gallery():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    offset = (page - 1) * limit

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM media")
    total = c.fetchone()["cnt"]

    c.execute("SELECT * FROM media ORDER BY mtime DESC LIMIT ? OFFSET ?", (limit, offset))
    items = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify({"total": total, "page": page, "items": items})
