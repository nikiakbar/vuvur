# api/app/subgroups.py
import os
from flask import Blueprint, jsonify, request, abort
from app.db import get_db
from app.api_key_middleware import api_key_required

bp = Blueprint("subgroups", __name__)
GALLERY_PATH = "/mnt/gallery" # Ensure this matches scanner.py
@api_key_required
@bp.route("/api/gallery/subgroups")
def get_subgroups():
    """
    Get a list of unique second-level directory names (subgroups)
    for files belonging to a specific top-level group_tag.
    """
    group = request.args.get("group", "")
    if not group:
        abort(400, description="Missing 'group' parameter")

    conn = get_db()
    c = conn.cursor()

    # Query paths for the given group_tag
    # We select the full path to extract the subgroup reliably
    c.execute("""
        SELECT DISTINCT path
        FROM media
        WHERE group_tag = ?
    """, (group,))

    rows = c.fetchall()
    conn.close()

    subgroups = set()
    base_group_path = os.path.join(GALLERY_PATH, group)

    for row in rows:
        full_path = row["path"]
        try:
            # Get the path relative to the gallery base
            relative_path = os.path.relpath(os.path.dirname(full_path), GALLERY_PATH)
            # Split the path into components
            path_parts = relative_path.split(os.sep)
            # Ensure it's within the requested group and has a subgroup
            if len(path_parts) > 1 and path_parts[0] == group:
                subgroups.add(path_parts[1]) # Add the second-level directory
        except ValueError:
            # Handle cases where path might be outside GALLERY_PATH (shouldn't happen with current scanner)
            pass

    # Return sorted list of unique subgroup names
    return jsonify(sorted(list(subgroups)))