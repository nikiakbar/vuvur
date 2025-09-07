#!/bin/sh

set -e

CONFIG_FILE=/usr/share/nginx/html/config.js

# Read environment variables, default to an empty string if not set
BATCH_SIZE=${VITE_GALLERY_BATCH_SIZE:-""}
PRELOAD_COUNT=${VITE_RANDOM_PRELOAD_COUNT:-""}

echo "Generating config.js..."
echo "GALLERY_BATCH_SIZE: [${BATCH_SIZE}]"
echo "RANDOM_PRELOAD_COUNT: [${PRELOAD_COUNT}]"

# Create the config file for the React app to read
cat <<EOF > ${CONFIG_FILE}
window.env = {
  GALLERY_BATCH_SIZE: "${BATCH_SIZE}",
  RANDOM_PRELOAD_COUNT: "${PRELOAD_COUNT}"
};
EOF

# Run the original Nginx command
exec /docker-entrypoint.sh "$@"