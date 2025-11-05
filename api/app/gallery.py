# api/app/gallery.py
import os # Import os
from flask import Blueprint, jsonify, request
from app.db import get_db
import json
from app.api_key_middleware import api_key_required

bp = Blueprint("gallery", __name__)
GALLERY_PATH = "/mnt/gallery" # Ensure this matches scanner.py
@api_key_required
@bp.route("/api/gallery")
def gallery():
    """
    Get a paginated list of media items with sorting, searching, and group/subgroup filtering.
    """
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit
    sort = request.args.get("sort", "random")
    query = request.args.get("q", "")
    group = request.args.get("group", "")
    subgroup = request.args.get("subgroup", "") # New subgroup filter

    conn = get_db()
    c = conn.cursor()

    # --- Dynamic Query Building ---
    params = []
    where_conditions = []
    base_sql = "FROM media"
    join_sql = ""

    if query:
        join_sql = "JOIN media_fts f ON media.id = f.rowid"
        where_conditions.append("media_fts MATCH ?")
        params.append(f'{query}*')

    if group:
        where_conditions.append("group_tag = ?")
        params.append(group)
        # ✅ If subgroup is specified, add a path-based filter
        if subgroup:
            # Construct the expected path prefix for the subgroup
            # IMPORTANT: This assumes paths are stored like /mnt/gallery/group/subgroup/...
            # Using LIKE ensures flexibility, but might be slow on huge datasets without path indexing
            subgroup_path_prefix = os.path.join(GALLERY_PATH, group, subgroup) + os.sep
            where_conditions.append("path LIKE ?")
            params.append(f'{subgroup_path_prefix}%')

    where_sql = ""
    if where_conditions:
        where_sql = "WHERE " + " AND ".join(where_conditions)

    # Build final SQL
    sql = f"SELECT * {base_sql} {join_sql} {where_sql}"
    count_sql = f"SELECT COUNT(*) as cnt {base_sql} {join_sql} {where_sql}"

    # Get total count for pagination
    c.execute(count_sql, tuple(params))
    total_row = c.fetchone()
    total_items = total_row["cnt"] if total_row else 0
    total_pages = (total_items + limit - 1) // limit if limit > 0 else 1

    # Apply sorting logic correctly
    if sort == "random":
        sql += " ORDER BY RANDOM()"
    elif sort == "date_desc":
        sql += " ORDER BY mtime DESC"
    elif sort == "date_asc":
        sql += " ORDER BY mtime ASC"
    elif sort == "file_asc":
        sql += " ORDER BY filename ASC"
    elif sort == "file_desc":
        sql += " ORDER BY filename DESC"
    # If no sort specified and no query, default to something reasonable (e.g., date descending)
    elif not sort and not query:
         sql += " ORDER BY mtime DESC"


    # Add pagination
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(sql, tuple(params))

    # Decode the exif string into a dictionary
    items = []
    for row in c.fetchall():
        item = dict(row)
        if item.get("exif"):
            try:
                # Handle both dict (already parsed?) and string cases
                if isinstance(item["exif"], str):
                     item["exif"] = json.loads(item["exif"])
                elif not isinstance(item["exif"], dict):
                     item["exif"] = {} # Default to empty if it's neither string nor dict
            except (json.JSONDecodeError, TypeError):
                item["exif"] = {} # Default to empty on error
        else:
             item["exif"] = {} # Ensure exif key exists even if null in DB
        items.append(item)

    conn.close()

    return jsonify({
        "total_items": total_items,
        "page": page,
        "total_pages": total_pages,
        "items": items
    })