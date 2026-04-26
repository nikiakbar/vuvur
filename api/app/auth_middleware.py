import os
import secrets
from functools import wraps
from flask import session, jsonify, request
from app.api_key_middleware import API_SECRET

ENABLE_LOGIN = os.getenv("ENABLE_LOGIN", "false").lower() == "true"

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 1. Check for valid user session
        if "user" in session:
            return f(*args, **kwargs)

        # 2. Check for valid API Key (allows programmatic access)
        provided_key = request.headers.get("X-Api-Key")
        if API_SECRET and provided_key and secrets.compare_digest(provided_key, API_SECRET):
            return f(*args, **kwargs)

        # 3. If login is enabled and neither check passed, deny access
        if ENABLE_LOGIN:
            return jsonify({"error": "Login or valid API Key required"}), 401

        # 4. If login is NOT enabled, we allow access (fallback to standard behavior)
        return f(*args, **kwargs)
    return wrapper
