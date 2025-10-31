#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

INITIAL_SCAN_FLAG_PATH="/app/data/.initial_scan_complete"

# Only run the scanner script if the flag file does NOT exist
if [ ! -f "$INITIAL_SCAN_FLAG_PATH" ]; then
    echo "--- Initial scan flag not found. Running one-time scan. ---"
    python run_scanner.py
else
    echo "--- Initial scan already completed. Skipping scan. ---"
fi

# Start the Gunicorn web server
echo "--- Starting Gunicorn web server ---"
# ✅ Use the WORKERS environment variable, with a default of 2
exec gunicorn -w ${WORKERS:-3} -k gevent --max-requests 1000 -b 0.0.0.0:5000 "main:create_app()"