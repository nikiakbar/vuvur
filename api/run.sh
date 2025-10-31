#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# --- REMOVED THE BLOCKING SCAN ---
# The initial scan is now handled by a background thread
# inside the main:create_app() function.

# Start the Gunicorn web server
echo "--- Starting Gunicorn web server ---"
# Use the WORKERS environment variable, with a default of 2
exec gunicorn -w ${WORKERS:-2} -k gevent --max-requests 1000 -b 0.0.0.0:5000 "main:create_app()"