#!/bin/sh
set -e

# Export secrets to environment variables
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD 2>/dev/null || echo "YBFYsQ2mKL")
export REDIS_PASSWORD=$(cat /run/secrets/REDIS_PASSWORD 2>/dev/null || echo "")
export JWT_SECRET_KEY=$(cat /run/secrets/JWT_SECRET_KEY 2>/dev/null || echo "DptuJoCCd1Yqd6qnBOCOqIFQI-0R6VySbB30lE1JT44")
export API_KEY=$(cat /run/secrets/API_KEY 2>/dev/null || echo "nh2Jof8cBvRvudq41oTKklKpJB5u2gn0aqCGBNUbUiY")
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY 2>/dev/null || echo "")

# Construct connection URLs
export REDIS_URL="redis://redis:6379/0"
export DATABASE_URL="postgresql+psycopg2://ai_workflow_admin:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db"
export PYTHONPATH=/project/app

echo "API: Starting Uvicorn server (emergency mode)."
# Run directly as root since we don't have app user
exec uvicorn api.emergency_main:app --host 0.0.0.0 --port 8000