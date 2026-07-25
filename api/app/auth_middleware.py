import os
import secrets
from functools import wraps
from flask import session, jsonify, request

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        enable_login = os.getenv("ENABLE_LOGIN", "false").lower() == "true"
        api_secret = os.getenv("API_SECRET_KEY")

        # 1. Session check (only if login is enabled)
        if enable_login and "user" in session:
            return f(*args, **kwargs)

        # 2. API Key check (fallback or system-wide if API_SECRET is set)
        if api_secret:
            provided_key = request.headers.get("X-Api-Key")
            if provided_key and secrets.compare_digest(provided_key, api_secret):
                return f(*args, **kwargs)
            # If API_SECRET is set but not matched, deny access.
            return jsonify({"error": "Unauthorized"}), 401

        # 3. Deny if login is required but no session (and no API key config to bypass)
        if enable_login:
            return jsonify({"error": "Login required"}), 401

        # 4. Fallback to allow if no security measures are active
        return f(*args, **kwargs)
    return wrapper
