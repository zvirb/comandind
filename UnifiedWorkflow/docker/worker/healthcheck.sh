#!/bin/bash
# docker/worker/healthcheck.sh
# Universal healthcheck script for worker that properly sets up environment
# This script works on both local development and server environments

set -e

# Set up environment variables from secrets (same as run.sh)
# This ensures the healthcheck has access to the same configuration as the worker
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
export REDIS_PASSWORD=$(cat /run/secrets/REDIS_PASSWORD)
export JWT_SECRET_KEY=$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY)

# Construct URLs (same as run.sh)
export DATABASE_URL="postgresql+psycopg2://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db"
export REDIS_URL="redis://lwe-app:${REDIS_PASSWORD}@redis:6379/0"
export PYTHONPATH=/app

# Change to app directory
cd /app

# Simple Redis connectivity test first (faster than Celery ping)
python -c "
import redis
import sys
try:
    r = redis.Redis(host='redis', port=6379, username='lwe-app', password='${REDIS_PASSWORD}')
    r.ping()
except Exception as e:
    print(f'Redis connection failed: {e}')
    sys.exit(1)
" || exit 1

# Test Celery worker ping with reasonable timeout
# The timeout prevents the healthcheck from hanging on slower servers
timeout 15 celery -A worker.celery_app --broker "redis://lwe-app:${REDIS_PASSWORD}@redis:6379/0" inspect ping -d "celery@${HOSTNAME}" > /dev/null 2>&1