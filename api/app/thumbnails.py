import os
import subprocess
import logging
from flask import Blueprint, send_file, abort
from PIL import Image, ImageSequence # Import ImageSequence for GIF handling
from app.db import get_db

logger = logging.getLogger(__name__)
bp = Blueprint("thumbnails", __name__)

# Define directories for thumbnails
THUMB_DIR = "/app/data/thumbs"
os.makedirs(THUMB_DIR, exist_ok=True)

def create_image_version(src, dst, size, quality):
    """Creates a resized and compressed version of an image or GIF."""
    try:
        logger.info(f"Creating image version for: {src} at size {size}")
        
        # Determine output format based on destination extension
        output_format = "JPEG" if dst.lower().endswith(".jpg") else "GIF"
        
        with Image.open(src) as im:
            # Handle animated GIFs - create a static thumbnail from the first frame
            if im.format == "GIF" and getattr(im, 'is_animated', False):
                 logger.info(f"Detected animated GIF: {src}. Creating static thumbnail.")
                 # Create a copy of the first frame
                 first_frame = im.copy()
                 first_frame.thumbnail(size)
                 # Ensure RGB mode for saving as JPEG if needed (though we save as GIF)
                 if first_frame.mode not in ("RGB", "L", "P"): # L=Grayscale, P=Palette
                      first_frame = first_frame.convert("RGB")
                 # Save the first frame as a static GIF
                 first_frame.save(dst, format="GIF")
            else:
                # Handle non-animated images (including static GIFs)
                im.thumbnail(size)
                # Ensure image is in a saveable format (convert images with transparency to RGB for JPEG)
                save_kwargs = {}
                if output_format == "JPEG":
                    if im.mode in ("P", "PA", "RGBA"):
                        im = im.convert("RGB")
                    save_kwargs['quality'] = quality
                # Save with appropriate format and options
                im.save(dst, output_format, **save_kwargs)

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
    """Serves a thumbnail. JPG for most, GIF for original GIFs."""
    row = get_media_row(mid)
    src = row["path"]
    
    # Determine thumbnail extension based on original file type
    is_gif = src.lower().endswith(".gif")
    thumb_ext = ".gif" if is_gif else ".jpg"
    dst = os.path.join(THUMB_DIR, f"{mid}{thumb_ext}")
    mime_type = "image/gif" if is_gif else "image/jpeg"

    if not os.path.exists(dst):
        if not os.path.exists(src):
            abort(404)
        if row["type"] == "image":
             # Use 600x600 size, quality 90 for JPEGs
             create_image_version(src, dst, size=(600, 600), quality=90)
        else: # Videos always get a JPG thumb
             # Ensure dst is .jpg for video thumbs
             dst_jpg = os.path.join(THUMB_DIR, f"{mid}.jpg")
             create_video_thumb(src, dst_jpg)
             # Update dst and mime_type for sending the file
             dst = dst_jpg
             mime_type = "image/jpeg"
             
    return send_file(dst, mimetype=mime_type)

# The /api/preview endpoint has been removed.