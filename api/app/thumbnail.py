import os
import subprocess
import logging
from flask import Blueprint, send_file, abort
from PIL import Image

# Get the logger
logger = logging.getLogger(__name__)

bp = Blueprint("thumbnails", __name__)
THUMB_DIR = "/app/data/thumbs"
os.makedirs(THUMB_DIR, exist_ok=True)

def image_thumb(src, dst, size=(300, 300)):
    """Creates a thumbnail for an image file."""
    try:
        logger.info(f"Creating thumbnail for: {src}")
        im = Image.open(src)
        im.thumbnail(size)
        im.save(dst, "JPEG")
        logger.info(f"Successfully saved thumbnail to: {dst}")
    except Exception as e:
        logger.error(f"Failed to create thumbnail for {src}: {e}", exc_info=True)
        raise

def video_thumb(src, dst):
    """Creates a thumbnail for a video file."""
    try:
        logger.info(f"Creating video thumbnail for: {src}")
        result = subprocess.run([
            "ffmpeg", "-y", "-i", src, "-ss", "00:00:01.000", "-vframes", "1", dst
        ], check=True, capture_output=True, text=True)
        logger.info(f"Successfully saved video thumbnail to: {dst}")
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed for {src}. Return code: {e.returncode}")
        logger.error(f"ffmpeg stdout: {e.stdout}")
        logger.error(f"ffmpeg stderr: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating video thumbnail for {src}: {e}", exc_info=True)
        raise

@bp.route("/api/thumbnails/<int:mid>")
def thumb(mid):
    conn = None
    try:
        from app.db import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM media WHERE id=?", (mid,))
        row = c.fetchone()
    except Exception as e:
        logger.error(f"Database error while fetching media ID {mid}: {e}", exc_info=True)
        abort(500)
    finally:
        if conn:
            conn.close()

    if not row:
        logger.warning(f"Thumbnail requested for non-existent media ID: {mid}")
        abort(404)

    src = row["path"]
    dst = os.path.join(THUMB_DIR, f"{mid}.jpg")

    if not os.path.exists(dst):
        try:
            if not os.path.exists(src):
                logger.error(f"Source file does not exist: {src} for media ID: {mid}")
                abort(404)
            
            if row["type"] == "image":
                image_thumb(src, dst)
            else:
                video_thumb(src, dst)
        except Exception:
            # The specific error is already logged in the thumb functions
            abort(500) # Internal Server Error

    if not os.path.exists(dst):
        logger.error(f"Thumbnail file not found at {dst} after generation attempt.")
        abort(500)

    return send_file(dst, mimetype="image/jpeg")