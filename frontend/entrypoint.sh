#!/bin/sh

# Set the path to the config file within the Nginx static root
CONFIG_FILE=/usr/share/nginx/html/config.js

# Use environment variables, providing a default value if they are not set
PRELOAD=${VITE_RANDOM_PRELOAD_COUNT:-3}
HISTORY=${VITE_RANDOM_HISTORY_SIZE:-5}

echo "Generating config.js with PRELOAD_COUNT=${PRELOAD} and HISTORY_SIZE=${HISTORY}"

# Overwrite the config.js file with values from the environment
cat <<EOF > ${CONFIG_FILE}
window.env = {
  VITE_RANDOM_PRELOAD_COUNT: "${PRELOAD}",
  VITE_RANDOM_HISTORY_SIZE: "${HISTORY}"
};
EOF

# Call the original Nginx entrypoint to start the server
exec /docker-entrypoint.sh "$@"