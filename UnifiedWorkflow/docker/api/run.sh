#!/bin/sh
set -e

# This script runs as root, so it can read secrets.
# Export secrets to environment variables that can be passed to the final process.
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
export REDIS_PASSWORD=$(cat /run/secrets/REDIS_PASSWORD)
export JWT_SECRET_KEY=$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY)

# Construct connection URLs.
# Use Redis URL with username and password for secure operation
export REDIS_URL="redis://lwe-app:${REDIS_PASSWORD}@redis:6379/0"
export DATABASE_URL="postgresql+psycopg2://app_user:${POSTGRES_PASSWORD}@pgbouncer:6432/ai_workflow_db?sslmode=require"
export PYTHONPATH=/project/app

echo "API: Setting certificate permissions."
# The 'app' user needs to be able to read the TLS certificate and key.
chown -R app:app /etc/certs/api
chmod 600 /etc/certs/api/unified-key.pem

echo "API: Starting Uvicorn server."
# Drop privileges to the 'app' user before executing the long-running server process.
# Explicitly pass environment variables to the new user's environment.
# Run on HTTP for internal communication, HTTPS is handled by Caddy
exec su-exec app:app env \
  POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  REDIS_PASSWORD="$REDIS_PASSWORD" \
  JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  API_KEY="$API_KEY" \
  QDRANT_API_KEY="$QDRANT_API_KEY" \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  PYTHONPATH="/project/app" \
  uvicorn api.emergency_main:app --host 0.0.0.0 --port 8000
