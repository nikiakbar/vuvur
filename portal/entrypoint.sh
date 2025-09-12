#!/bin/sh

set -e

CONFIG_FILE=/usr/share/nginx/html/config.js

# Read environment variables, default to an empty string if not set
BATCH_SIZE=${VITE_GALLERY_BATCH_SIZE:-""}
PRELOAD_COUNT=${VITE_RANDOM_PRELOAD_COUNT:-""}
ZOOM_LEVEL=${VITE_ZOOM_LEVEL:-""} # Add the new zoom variable

echo "Generating config.js..."
echo "GALLERY_BATCH_SIZE: [${BATCH_SIZE}]"
echo "RANDOM_PRELOAD_COUNT: [${PRELOAD_COUNT}]"
echo "ZOOM_LEVEL: [${ZOOM_LEVEL}]"

# Create the config file for the React app to read
cat <<EOF > ${CONFIG_FILE}
window.env = {
  GALLERY_BATCH_SIZE: "${BATCH_SIZE}",
  RANDOM_PRELOAD_COUNT: "${PRELOAD_COUNT}",
  ZOOM_LEVEL: "${ZOOM_LEVEL}"
};
EOF

# Run the original Nginx command
exec /docker-entrypoint.sh "$@"