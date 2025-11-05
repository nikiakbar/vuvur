from flask import Blueprint, jsonify
from app.db import get_db
from app.api_key_middleware import api_key_required

bp = Blueprint("groups", __name__)
@api_key_required
@bp.route("/api/gallery/groups")
def get_groups():
    """
    Get a list of all unique group_tags and the count of items in each.
    """
    conn = get_db()
    c = conn.cursor()
    # Get distinct, non-null group tags, count them
    c.execute("""
        SELECT group_tag, COUNT(*) as count 
        FROM media 
        WHERE group_tag IS NOT NULL AND group_tag != ''
        GROUP BY group_tag
        ORDER BY group_tag ASC
    """)
    groups = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(groups)