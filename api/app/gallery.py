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
    group = request.args.get("group", "") # New group filter

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
    total_pages = (total_items + limit - 1) // limit

    # ✅ FIX: Apply sorting logic correctly
    if sort == "random":
        # When searching, FTS has a default 'rank' order. We override it.
        sql += " ORDER BY RANDOM()"
    elif sort == "date_desc":
        sql += " ORDER BY mtime DESC"
    elif sort == "date_asc":
        sql += " ORDER BY mtime ASC"
    elif sort == "file_asc":
        sql += " ORDER BY filename ASC"
    elif sort == "file_desc":
        sql += " ORDER BY filename DESC"
    
    # Add pagination
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(sql, tuple(params))
    
    # --- END CORRECTION ---

    # Decode the exif string into a dictionary
    items = []
    for row in c.fetchall():
        item = dict(row)
        if item.get("exif"):
            try:
                item["exif"] = json.loads(item["exif"])
            except (json.JSONDecodeError, TypeError):
                item["exif"] = {}
        items.append(item)
        
    conn.close()

    return jsonify({
        "total_items": total_items,
        "page": page,
        "total_pages": total_pages,
        "items": items
    })