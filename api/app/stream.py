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
    c.execute("SELECT path FROM media WHERE id=?", (media_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        abort(404)

    file_path = row["path"]
    if not os.path.exists(file_path):
        abort(404)

    mime_type, _ = mimetypes.guess_type(file_path)
    file_size = os.path.getsize(file_path)

    range_header = request.headers.get("Range", None)
    if not range_header:
        return send_file(file_path, mimetype=mime_type)

    # ✅ Sentinel: Safely parse Range header and validate byte bounds
    try:
        if not range_header.startswith("bytes="):
            raise ValueError("Invalid range specifier")
        range_val = range_header[6:].strip()
        start_str, end_str = range_val.split("-", 1)
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
        if start < 0 or end < start or start >= file_size:
            raise ValueError("Unsatisfiable range bounds")
        end = min(end, file_size - 1)
    except (ValueError, IndexError):
        response = Response(status=416)
        response.headers["Content-Range"] = f"bytes */{file_size}"
        return response

    response = Response(
        generate_range_response(file_path, start, end),
        status=206,
        mimetype=mime_type,
        direct_passthrough=True,
    )
    response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
    response.headers.add("Accept-Ranges", "bytes")
    return response
