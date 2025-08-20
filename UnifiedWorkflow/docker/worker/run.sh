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
export REDIS_URL="redis://lwe-app:${REDIS_PASSWORD}@redis:6379/0"
export DATABASE_URL="postgresql+psycopg2://app_user:${POSTGRES_PASSWORD}@pgbouncer:6432/app_tx?sslmode=require"
export PYTHONPATH=/

echo "Worker: Starting Celery worker..."

# Wait for dependencies to be ready (helps with slower servers)
echo "Worker: Waiting for dependencies..."
python -c "
import redis
import time
import sys

max_retries = 30
retry_delay = 1

# Test Redis connection
for i in range(max_retries):
    try:
        r = redis.Redis(host='redis', port=6379, username='lwe-app', password='${REDIS_PASSWORD}')
        r.ping()
        print('Redis connection successful')
        break
    except Exception as e:
        if i == max_retries - 1:
            print(f'Redis connection failed after {max_retries} attempts: {e}')
            sys.exit(1)
        print(f'Redis connection attempt {i+1} failed, retrying in {retry_delay}s...')
        time.sleep(retry_delay)
"

# Determine concurrency based on available resources
# This helps servers with limited resources
CONCURRENCY=1
if [ -f /proc/meminfo ]; then
    # Get available memory in MB
    AVAILABLE_MEM=$(awk '/MemAvailable/ { print int($2/1024) }' /proc/meminfo)
    if [ "$AVAILABLE_MEM" -gt 2048 ]; then
        CONCURRENCY=2
    fi
fi

echo "Worker: Using concurrency: $CONCURRENCY"

# Drop privileges to the 'app' user before executing the long-running server process.
# Explicitly pass environment variables to the new user's environment.
exec gosu app:app env \
  POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  REDIS_PASSWORD="$REDIS_PASSWORD" \
  JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  API_KEY="$API_KEY" \
  QDRANT_API_KEY="$QDRANT_API_KEY" \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  PYTHONPATH="$PYTHONPATH" \
  celery -A worker.celery_app worker --loglevel=info --pool=prefork --concurrency=$CONCURRENCY
