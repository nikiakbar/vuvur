from flask import Blueprint, request, jsonify, session
from db import user_exists, create_user, authenticate

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/register", methods=["POST"])
def register():
    if user_exists():
        return jsonify({"error": "Registration closed"}), 403
    data = request.json
    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Missing fields"}), 400
    create_user(data["username"], data["password"])
    return jsonify({"message": "User registered"}), 201

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json
    if authenticate(data.get("username"), data.get("password")):
        session["user"] = data["username"]
        return jsonify({"message": "Logged in"})
    return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return jsonify({"message": "Logged out"})

@auth_bp.route("/api/login_required", methods=["GET"])
def login_required_flag():
    # Frontend uses this to know if login/register is needed
    return jsonify({
        "login_required": True,
        "users_exist": user_exists()
    })
