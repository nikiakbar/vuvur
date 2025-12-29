import os, shutil
from flask import Blueprint, jsonify, abort
from app.db import get_db
from app.api_key_middleware import api_key_required

bp = Blueprint("like", __name__)
LIKED_DIR = "/mnt/gallery/liked"
@api_key_required
@bp.route("/api/toggle_like/<int:mid>", methods=["POST"])
def toggle_like(mid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM media WHERE id=?", (mid,))
    row = c.fetchone()
    if not row:
        conn.close()
        abort(404)

    path = row["path"]
    liked = row["liked"]
    orig = row["original_path"] if row["original_path"] else None  # May be None for old records

    if liked:
        # Unlike -> move back to original location
        if orig and os.path.exists(os.path.dirname(orig)):
            target = orig
        else:
            # Fallback: if original_path is missing, keep in liked folder
            # This shouldn't happen but prevents errors
            conn.close()
            return jsonify({"status": "error", "message": "Cannot unlike: original path unknown"}), 400
        
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.move(path, target)
        c.execute("UPDATE media SET path=?, liked=0, original_path=NULL WHERE id=?", (target, mid))
    else:
        # Like -> move to liked folder and store original path
        target = os.path.join(LIKED_DIR, os.path.basename(path))
        os.makedirs(LIKED_DIR, exist_ok=True)
        shutil.move(path, target)
        c.execute("UPDATE media SET path=?, liked=1, original_path=? WHERE id=?", (target, path, mid))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "liked": not liked})

