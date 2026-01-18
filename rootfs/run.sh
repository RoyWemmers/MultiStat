#!/usr/bin/with-contenv bashio
set -e

# Read configuration
CONFIG_PATH=/data/options.json

# Start the application
python3 /app/main.py