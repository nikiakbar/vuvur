import os
from functools import wraps
from flask import session, jsonify

ENABLE_LOGIN = os.getenv("ENABLE_LOGIN", "false").lower() == "true"

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if ENABLE_LOGIN and "user" not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return wrapper
