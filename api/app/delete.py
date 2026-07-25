import os
import shutil
import time
import logging
from flask import Blueprint, jsonify, abort
from app.db import get_db
from app.auth_middleware import login_required

logger = logging.getLogger(__name__)
bp = Blueprint("delete", __name__)

# Define the path to the recycle bin
RECYCLEBIN_PATH = "/mnt/gallery/recyclebin"
SECONDARY_MOUNT_PATH = os.environ.get("SECONDARY_MOUNT_PATH", None)


@bp.route("/api/delete/<int:mid>", methods=["POST"])
@login_required
def delete_media_item(mid):
    """
    Moves a media file to the recycle bin, deletes its DB record,
    and moves any matching secondary file to a 'secondary' subfolder in the recycle bin.
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT path FROM media WHERE id=?", (mid,))
    row = c.fetchone()
    if not row:
        conn.close()
        abort(404, description="Media not found")

    file_path = row["path"]

    # Ensure the recycle bin directory exists
    os.makedirs(RECYCLEBIN_PATH, exist_ok=True)
    
    # Generate unique filename with timestamp to prevent collisions
    timestamp = int(time.time() * 1000)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{timestamp}{ext}"
    destination_path = os.path.join(RECYCLEBIN_PATH, unique_filename)


    try:
        # Move the file
        shutil.move(file_path, destination_path)
        if SECONDARY_MOUNT_PATH:
            secondary_file_path = os.path.join(SECONDARY_MOUNT_PATH, filename)
            
            if os.path.exists(secondary_file_path):
                try:
                    # Define and create the secondary recycle bin folder dynamically
                    secondary_recycle_path = os.path.join(RECYCLEBIN_PATH, "secondary")
                    os.makedirs(secondary_recycle_path, exist_ok=True)
                    
                    # Destination for the secondary file
                    secondary_destination_path = os.path.join(secondary_recycle_path, unique_filename)
                    
                    # Move the secondary file
                    shutil.move(secondary_file_path, secondary_destination_path)
                    logger.info(f"Successfully moved secondary file to: {secondary_destination_path}")
                except Exception as e:
                    logger.error(f"Failed to move secondary file {secondary_file_path}: {e}")
            else:
                logger.info(f"Secondary file not found, skipping: {secondary_file_path}")
                
        # If move is successful, delete the record from the database
        c.execute("DELETE FROM media WHERE id=?", (mid,))
        conn.commit()
        
    except FileNotFoundError:
        # If the file is already missing, just delete the DB record
        c.execute("DELETE FROM media WHERE id=?", (mid,))
        conn.commit()
        return jsonify({"status": "warning", "message": "File not found, but DB record was cleaned up."}), 200
    except Exception as e:
        logger.error(f"Error deleting media {mid}: {e}", exc_info=True)
        conn.close()
        # Return a generic server error to avoid leaking details
        return jsonify({"status": "error", "message": "An internal error occurred while deleting the media."}), 500
    finally:
        conn.close()
        
    return jsonify({"status": "ok", "message": "File moved to recycle bin"}), 200