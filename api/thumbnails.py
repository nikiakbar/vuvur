import os, subprocess
from flask import Blueprint, send_file, abort
from PIL import Image
from .db import get_db

bp = Blueprint("thumbnails", __name__)
THUMB_DIR = "/app/data/thumbs"
os.makedirs(THUMB_DIR, exist_ok=True)

def image_thumb(src, dst, size=(300,300)):
    im = Image.open(src)
    im.thumbnail(size)
    im.save(dst, "JPEG")

def video_thumb(src, dst):
    subprocess.run([
        "ffmpeg","-y","-i",src,"-ss","00:00:01.000","-vframes","1",dst
    ], check=False)

@bp.route("/api/thumbnails/<int:mid>")
def thumb(mid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM media WHERE id=?", (mid,))
    row = c.fetchone()
    conn.close()
    if not row: abort(404)

    src = row["path"]
    dst = os.path.join(THUMB_DIR, f"{mid}.jpg")
    if not os.path.exists(dst):
        if row["type"] == "image":
            image_thumb(src, dst)
        else:
            video_thumb(src, dst)
    return send_file(dst, mimetype="image/jpeg")
