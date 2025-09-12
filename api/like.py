import os, shutil
from flask import Blueprint, jsonify, abort
from .db import get_db

bp = Blueprint("like", __name__)
LIKED_DIR = "/mnt/gallery/liked"

@bp.route("/api/toggle_like/<int:mid>", methods=["POST"])
def toggle_like(mid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM media WHERE id=?", (mid,))
    row = c.fetchone()
    if not row:
        conn.close()
        abort(404)

    path, liked, orig = row["path"], row["liked"], row["original_path"]

    if liked:
        # unlike -> move back
        target = orig
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.move(path, target)
        c.execute("UPDATE media SET path=?, liked=0 WHERE id=?", (target, mid))
    else:
        # like -> move into liked
        target = os.path.join(LIKED_DIR, os.path.basename(path))
        os.makedirs(LIKED_DIR, exist_ok=True)
        shutil.move(path, target)
        c.execute("UPDATE media SET path=?, liked=1 WHERE id=?", (target, mid))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "liked": not liked})
