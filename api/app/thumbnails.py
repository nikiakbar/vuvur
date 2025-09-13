import os
import subprocess
import logging
from flask import Blueprint, send_file, abort
from PIL import Image
from app.db import get_db

logger = logging.getLogger(__name__)
bp = Blueprint("thumbnails", __name__)

# Define directories for both thumbnails and previews
THUMB_DIR = "/app/data/thumbs"
PREVIEW_DIR = "/app/data/previews"
os.makedirs(THUMB_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

def create_image_version(src, dst, size, quality):
    """Creates a resized and compressed version of an image."""
    try:
        logger.info(f"Creating image version for: {src} at size {size} with quality {quality}")
        with Image.open(src) as im:
            im.thumbnail(size)
            # Ensure image is in a saveable format (e.g., convert palette images to RGB)
            if im.mode in ("P", "PA"):
                im = im.convert("RGB")
            im.save(dst, "JPEG", quality=quality)
        logger.info(f"Successfully saved image version to: {dst}")
    except Exception as e:
        logger.error(f"Failed to create image version for {src}: {e}", exc_info=True)
        raise

def create_video_thumb(src, dst):
    """Creates a thumbnail for a video file."""
    try:
        logger.info(f"Creating video thumbnail for: {src}")
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-ss", "00:00:01.000", "-vframes", "1", dst],
            check=True, capture_output=True, text=True
        )
        logger.info(f"Successfully saved video thumbnail to: {dst}")
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed for {src}: {e.stderr}")
        raise

def get_media_row(media_id):
    """Fetches a media record from the database by its ID."""
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM media WHERE id=?", (media_id,))
        row = c.fetchone()
        if not row:
            logger.warning(f"Media ID not found: {media_id}")
            abort(404)
        return row
    except Exception as e:
        logger.error(f"Database error fetching media ID {media_id}: {e}", exc_info=True)
        abort(500)
    finally:
        if conn:
            conn.close()

@bp.route("/api/thumbnails/<int:mid>")
def thumb(mid):
    """Serves a small, highly compressed thumbnail."""
    row = get_media_row(mid)
    src = row["path"]
    dst = os.path.join(THUMB_DIR, f"{mid}.jpg")

    if not os.path.exists(dst):
        if not os.path.exists(src):
            abort(404)
        if row["type"] == "image":
            # size=(400, 400), quality=75 for thumbnails
            create_image_version(src, dst, size=(400, 400), quality=75)
        else:
            create_video_thumb(src, dst)
    
    return send_file(dst, mimetype="image/jpeg")

@bp.route("/api/preview/<int:mid>")
def preview(mid):
    """Serves a larger, lightly compressed preview image."""
    row = get_media_row(mid)
    src = row["path"]
    dst = os.path.join(PREVIEW_DIR, f"{mid}.jpg")

    if not os.path.exists(dst):
        if not os.path.exists(src):
            abort(404)
        if row["type"] == "image":
            # size=(1920, 1080), quality=90 for previews
            create_image_version(src, dst, size=(1920, 1080), quality=90)
        else: # For videos, serve the same thumbnail as the preview
            thumb_path = os.path.join(THUMB_DIR, f"{mid}.jpg")
            if not os.path.exists(thumb_path):
                 create_video_thumb(src, thumb_path)
            return send_file(thumb_path, mimetype="image/jpeg")

    return send_file(dst, mimetype="image/jpeg")