import mimetypes
import os
from flask import Blueprint, request, Response, abort, send_file
from app.db import get_db
from app.auth_middleware import login_required
from app.api_key_middleware import api_key_required

stream_bp = Blueprint("stream", __name__)

CHUNK_SIZE = 8192

def generate_range_response(path, start, end):
    with open(path, "rb") as f:
        f.seek(start)
        while start <= end:
            data = f.read(min(CHUNK_SIZE, end - start + 1))
            if not data:
                break
            yield data
            start += len(data)

@stream_bp.route("/api/stream/<int:media_id>")
@api_key_required
@login_required
def stream(media_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT path, mtime FROM media WHERE id=?", (media_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        abort(404)

    file_path = row["path"]
    file_mtime = row["mtime"]
    if not os.path.exists(file_path):
        abort(404)

    mime_type, _ = mimetypes.guess_type(file_path)
    file_size = os.path.getsize(file_path)
    
    # Generate ETag based on media_id and mtime (file modification time)
    etag = f'"{media_id}-{int(file_mtime)}"'
    
    # Support conditional requests (If-None-Match)
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match == etag:
        # File hasn't changed, return 304 Not Modified
        return Response(status=304)

    range_header = request.headers.get("Range", None)
    if not range_header:
        response = send_file(file_path, mimetype=mime_type)
        response.headers['Cache-Control'] = 'private, max-age=3600'
        response.headers['ETag'] = etag
        return response

    # Parse Range header
    range_match = range_header.strip().split("=")[-1]
    start, end = range_match.split("-")
    start = int(start)
    end = int(end) if end else file_size - 1

    response = Response(
        generate_range_response(file_path, start, end),
        status=206,
        mimetype=mime_type,
        direct_passthrough=True,
    )
    response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    response.headers['Cache-Control'] = 'private, max-age=3600'
    response.headers['ETag'] = etag
    return response
