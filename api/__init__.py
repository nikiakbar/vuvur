from flask import Flask, request, jsonify, session, send_file, Response, Blueprint
import os
import mimetypes
from werkzeug.security import generate_password_hash, check_password_hash
from db import init_db, get_user_count, create_user, get_user_by_username

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "changeme")

# ---------- DB Setup ----------
init_db()

# ---------- Auth Routes ----------
@app.route("/api/register", methods=["POST"])
def register():
    if get_user_count() > 0:
        return jsonify({"error": "Registration closed"}), 403
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400
    create_user(username, generate_password_hash(password))
    return jsonify({"message": "User created"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    user = get_user_by_username(username)
    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        return jsonify({"message": "Logged in"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/status")
def auth_status():
    return jsonify({
        "logged_in": "user_id" in session,
        "needs_registration": get_user_count() == 0
    })

# ---------- Media Streaming ----------
media_bp = Blueprint("media", __name__)

def stream_file(path):
    range_header = request.headers.get("Range", None)
    if not os.path.exists(path):
        return jsonify({"error": "Not found"}), 404

    file_size = os.path.getsize(path)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "application/octet-stream"

    if range_header:
        byte1, byte2 = 0, None
        m = range_header.replace("bytes=", "").split("-")
        if m[0]:
            byte1 = int(m[0])
        if len(m) > 1 and m[1]:
            byte2 = int(m[1])
        length = (byte2 or file_size - 1) - byte1 + 1

        with open(path, "rb") as f:
            f.seek(byte1)
            data = f.read(length)

        resp = Response(data, 206, mimetype=mime_type, direct_passthrough=True)
        resp.headers.add("Content-Range", f"bytes {byte1}-{byte1+length-1}/{file_size}")
        resp.headers.add("Accept-Ranges", "bytes")
        resp.headers.add("Content-Length", str(length))
        return resp

    return send_file(path, mimetype=mime_type)

@media_bp.route("/api/stream/<media_id>")
def stream(media_id):
    # In real app: look up path from DB by id
    media_path = os.path.join("media", media_id)
    return stream_file(media_path)

app.register_blueprint(media_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
