from flask import Blueprint, jsonify, request
from app.db import get_db

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

    # Base query parts
    base_sql = "FROM media"
    where_clause = ""
    params = []

    # Handle search query
    if query:
        where_clause = " WHERE filename LIKE ? OR user_comment LIKE ?"
        params.extend([f"%{query}%", f"%{query}%"])

    # Get total count for pagination
    count_sql = "SELECT COUNT(*) as cnt " + base_sql + where_clause
    c.execute(count_sql, tuple(params))
    total_row = c.fetchone()
    total_items = total_row["cnt"] if total_row else 0
    total_pages = (total_items + limit - 1) // limit

    # Build the main query for fetching items
    sql = "SELECT * " + base_sql + where_clause

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
    items = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify({
        "total_items": total_items,
        "page": page,
        "total_pages": total_pages,
        "items": items
    })