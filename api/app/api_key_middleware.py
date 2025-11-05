import os
from functools import wraps
from flask import request, jsonify

# Get the secret key from the environment variable
API_SECRET = os.getenv("API_SECRET_KEY")

def api_key_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # If no API_SECRET_KEY is set on the server, bypass the check.
        # This allows the app to run unsecured if the key is not defined.
        if not API_SECRET:
            return f(*args, **kwargs)

        # Check if the 'X-Api-Key' header was provided and if it matches
        provided_key = request.headers.get("X-Api-Key")
        if provided_key and provided_key == API_SECRET:
            # Key is valid, proceed with the original function
            return f(*args, **kwargs)
        
        # Key is missing or invalid
        return jsonify({"error": "Unauthorized"}), 401
    return wrapper