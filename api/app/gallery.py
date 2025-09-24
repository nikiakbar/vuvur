from flask import Blueprint, jsonify, request
from app.db import get_db
import json

bp = Blueprint("gallery", __name__)

@bp.route("/api/gallery")
def gallery():
    """
    Get a paginated list of media items with sorting and searching.
    """
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit
    sort = request.args.get("sort", "random")
    query = request.args.get("q", "")

    conn = get_db()
    c = conn.cursor()

    # ✅ MODIFICATION: Updated to use FTS for searching
    base_sql = "FROM media"
    join_clause = ""
    where_clause = ""
    params = []

    if query:
        join_clause = " JOIN media_fts f ON media.id = f.rowid "
        where_clause = " WHERE media_fts MATCH ? "
        params.append(query)

    # Get total count for pagination
    count_sql = "SELECT COUNT(*) as cnt " + base_sql + join_clause + where_clause
    c.execute(count_sql, tuple(params))
    total_row = c.fetchone()
    total_items = total_row["cnt"] if total_row else 0
    total_pages = (total_items + limit - 1) // limit

    # Build the main query for fetching items
    sql = "SELECT * " + base_sql + join_clause + where_clause

    # Handle sorting
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
    else: # Default to random if sort is unknown
        sql += " ORDER BY RANDOM()"

    # Add pagination
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(sql, tuple(params))
    
    # ✅ FIX: Decode the exif string into a dictionary
    items = []
    for row in c.fetchall():
        item = dict(row)
        if item.get("exif"):
            try:
                item["exif"] = json.loads(item["exif"])
            except (json.JSONDecodeError, TypeError):
                item["exif"] = {} # Default to empty object on parsing error
        items.append(item)
        
    conn.close()

    return jsonify({
        "total_items": total_items,
        "page": page,
        "total_pages": total_pages,
        "items": items
    })