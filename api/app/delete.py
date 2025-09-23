import os
import shutil
from flask import Blueprint, jsonify, abort
from app.db import get_db

bp = Blueprint("delete", __name__)

# Define the path to the recycle bin
RECYCLEBIN_PATH = "/mnt/gallery/recyclebin"

@bp.route("/api/delete/<int:mid>", methods=["POST"])
def delete_media_item(mid):
    """
    Moves a media file to the recycle bin and deletes its DB record.
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
    
    # Define the destination path in the recycle bin
    destination_path = os.path.join(RECYCLEBIN_PATH, os.path.basename(file_path))

    try:
        # Move the file
        shutil.move(file_path, destination_path)
        
        # If move is successful, delete the record from the database
        c.execute("DELETE FROM media WHERE id=?", (mid,))
        conn.commit()
        
    except FileNotFoundError:
        # If the file is already missing, just delete the DB record
        c.execute("DELETE FROM media WHERE id=?", (mid,))
        conn.commit()
        return jsonify({"status": "warning", "message": "File not found, but DB record was cleaned up."}), 200
    except Exception as e:
        conn.close()
        # Return a server error if something goes wrong
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()
        
    return jsonify({"status": "ok", "message": "File moved to recycle bin"}), 200