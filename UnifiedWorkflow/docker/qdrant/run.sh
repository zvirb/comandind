#!/bin/sh
set -e

# This script runs as root, so it can read secrets.
# Export Qdrant API key from Docker secret
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY)

echo "Qdrant: Starting with Docker secret API key"

# Execute qdrant with the API key environment variable
exec /qdrant/qdrant