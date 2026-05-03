import os
import io
import subprocess
import logging
import threading
from flask import Blueprint, send_file, abort
from werkzeug.exceptions import HTTPException
from PIL import Image, ImageDraw
from app.db import get_db
from app.api_key_middleware import api_key_required

logger = logging.getLogger(__name__)
bp = Blueprint("thumbnails", __name__)

# Define directories for thumbnails
THUMB_DIR = "/app/data/thumbs"
os.makedirs(THUMB_DIR, exist_ok=True)
GENERATION_SEMAPHORE = threading.Semaphore(4)

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
                    # Create a copy of the first frame and ensure it's closed
                    with im.copy() as first_frame:
                        first_frame.thumbnail(size)
                        # Ensure RGB mode for saving as JPEG if needed (though we save as GIF)
                        if first_frame.mode not in ("RGB", "L", "P"): # L=Grayscale, P=Palette
                            with first_frame.convert("RGB") as rgb_frame:
                                rgb_frame.save(dst, format="GIF")
                        else:
                            first_frame.save(dst, format="GIF")
            else:
                # Handle non-animated images (including static GIFs)
                im.thumbnail(size)
                # Ensure image is in a saveable format (convert images with transparency to RGB for JPEG)
                save_kwargs = {}
                if output_format == "JPEG":
                    save_kwargs['quality'] = quality
                    if im.mode in ("P", "PA", "RGBA"):
                        with im.convert("RGB") as rgb_im:
                            rgb_im.save(dst, output_format, **save_kwargs)
                            logger.info(f"Successfully saved converted image version to: {dst}")
                            return # Early exit to avoid double save

                # Save with appropriate format and options
                im.save(dst, output_format, **save_kwargs)

        logger.info(f"Successfully saved image version to: {dst}")
    except Exception as e:
        logger.error(f"Failed to create image version for {src}: {e}", exc_info=True)
        logger.info(f"Creating fallback error thumbnail for {src}")
        create_error_thumb(dst)

def create_video_thumb(src, dst):
    """Creates a thumbnail for a video file."""
    try:
        logger.info(f"Creating video thumbnail for: {src}")
        # Moving -ss before -i for Input Seeking (much faster)
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "00:00:01.000", "-i", src, "-vframes", "1", "-strict", "unofficial", dst],
            check=False, capture_output=True, text=True
        )
        
        # Fallback for short videos if 1s target failed to create file
        if not os.path.exists(dst):
                logger.info(f"Thumbnail at 1s failed (likely short video), trying at 0s for: {src}")
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", "00:00:00.000", "-i", src, "-vframes", "1", "-strict", "unofficial", dst],
                    check=True, capture_output=True, text=True
                )

        if os.path.exists(dst):
            logger.info(f"Successfully saved video thumbnail to: {dst}")
        else:
            logger.warning(f"ffmpeg completed but no file created for {src}. Creating error placeholder.")
            create_error_thumb(dst)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed for {src}: {e.stderr}")
        logger.info(f"Creating fallback error thumbnail for {src}")
        create_error_thumb(dst)

def create_error_thumb(dst):
    """Creates a placeholder thumbnail for corrupted or unreadable files."""
    try:
        # Create a 600x600 dark red square using a context manager
        with Image.new('RGB', (600, 600), color=(50, 0, 0)) as img:
            d = ImageDraw.Draw(img)
            # Draw a cross
            d.line([(150, 150), (450, 450)], fill=(200, 50, 50), width=20)
            d.line([(450, 150), (150, 450)], fill=(200, 50, 50), width=20)
            output_format = "JPEG" if dst.lower().endswith(".jpg") else "GIF"
            img.save(dst, output_format, quality=90) if output_format == "JPEG" else img.save(dst, output_format)
            logger.info(f"Successfully saved error thumbnail to: {dst}")
    except Exception as eval_e:
        logger.error(f"Failed to create error thumbnail: {eval_e}", exc_info=True)
def create_audio_thumb(dst):
    """Creates a placeholder thumbnail for audio files."""
    try:
        # Create a 600x600 dark grey square using a context manager
        with Image.new('RGB', (600, 600), color=(50, 50, 50)) as img:
            d = ImageDraw.Draw(img)
            # We can't easily rely on fonts being present, so just draw a simple shape
            # Draw a lighter grey circle in the middle
            d.ellipse([150, 150, 450, 450], fill=(100, 100, 100))
            img.save(dst, "JPEG", quality=90)
            logger.info(f"Successfully saved audio thumbnail to: {dst}")
    except Exception as e:
        logger.error(f"Failed to create audio thumbnail: {e}", exc_info=True)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error fetching media ID {media_id}: {e}", exc_info=True)
        abort(500)
    finally:
        if conn:
            conn.close()

@bp.route("/api/thumbnails/<int:mid>")
@api_key_required
def thumb(mid):
    """Serves a thumbnail. JPG for most, GIF for original GIFs."""
    row = get_media_row(mid)
    src = row["path"]
    
    is_gif = src.lower().endswith(".gif")
    thumb_ext = ".gif" if is_gif else ".jpg"
    dst = os.path.join(THUMB_DIR, f"{mid}{thumb_ext}")
    mime_type = "image/gif" if is_gif else "image/jpeg"

    # 1. If the thumbnail exists, serve it instantly (Happy Path)
    if os.path.exists(dst):
        return send_file(dst, mimetype=mime_type, max_age=31536000)

    # 2. Source file is missing from disk
    if not os.path.exists(src):
        abort(404)

    # 3. Handle Generation with a TIMEOUT (The Fast Fail)
    # Wait a maximum of 1.0 seconds for a free CPU slot. 
    acquired = GENERATION_SEMAPHORE.acquire(timeout=1.0)
    
    if not acquired:
        # The server is slammed. 4 threads are already generating thumbnails.
        # Don't block Flask! Return a temporary placeholder immediately.
        logger.warning(f"Server busy. Fast-failing thumbnail generation for ID: {mid}")
        return serve_busy_placeholder()

    try:
        # We secured a slot! Safe to generate.
        if row["type"] == "image":
             create_image_version(src, dst, size=(600, 600), quality=90)
        elif row["type"] == "audio":
             dst_jpg = os.path.join(THUMB_DIR, f"{mid}.jpg")
             create_audio_thumb(dst_jpg)
             dst = dst_jpg
             mime_type = "image/jpeg"
        else: 
             dst_jpg = os.path.join(THUMB_DIR, f"{mid}.jpg")
             create_video_thumb(src, dst_jpg)
             dst = dst_jpg
             mime_type = "image/jpeg"
    finally:
        # ALWAYS release the lock so the next request can use it, even if generation crashes.
        GENERATION_SEMAPHORE.release()

    # Serve the newly generated file, or 500 if something went terribly wrong.
    if os.path.exists(dst):
        return send_file(dst, mimetype=mime_type, max_age=31536000)
    else:
        abort(500)


# Pre-generate the busy placeholder once at module load time to avoid disk I/O and race conditions
BUSY_IMG_BYTES = io.BytesIO()
with Image.new('RGB', (600, 600), color=(100, 100, 100)) as img:
    img.save(BUSY_IMG_BYTES, "JPEG", quality=70)


def serve_busy_placeholder():
    """Serves a lightweight 'Busy' placeholder from memory."""
    # Max age is short (60s). We WANT the browser to ask for this image again soon,
    # because the background scanner will eventually finish the real thumbnail!
    return send_file(io.BytesIO(BUSY_IMG_BYTES.getvalue()), mimetype="image/jpeg", max_age=60)