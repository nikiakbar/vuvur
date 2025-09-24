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

    # --- CORRECTED QUERY LOGIC ---
    
    base_sql = "FROM media"
    params = []
    
    # If there's a search query, we must use the FTS table
    if query:
        # We select from the main media table but join with the FTS table to filter
        count_sql = "SELECT COUNT(*) as cnt FROM media JOIN media_fts f ON media.id = f.rowid WHERE media_fts MATCH ?"
        sql = "SELECT * FROM media JOIN media_fts f ON media.id = f.rowid WHERE media_fts MATCH ?"
        # Add the wildcard to the search term for prefix matching
        params.append(f'{query}*')
    else:
        # If no query, use the simpler queries
        count_sql = "SELECT COUNT(*) as cnt FROM media"
        sql = "SELECT * FROM media"

    # Get total count for pagination
    c.execute(count_sql, tuple(params))
    total_row = c.fetchone()
    total_items = total_row["cnt"] if total_row else 0
    total_pages = (total_items + limit - 1) // limit

    # Handle sorting
    # Note: Random search is less efficient with FTS, but will still work
    if sort == "random" and not query:
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
                item["exif"] = {} # Default to empty object on parsing error
        items.append(item)
        
    conn.close()

    return jsonify({
        "total_items": total_items,
        "page": page,
        "total_pages": total_pages,
        "items": items
    })