#!/bin/bash

# Emergency API startup script
echo "Starting emergency API service..."

# Set environment variables
export DATABASE_URL="postgresql://app_user:$(cat secrets/postgres_password.txt)@localhost:5432/ai_workflow_db"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export PYTHONPATH="/home/marku/ai_workflow_engine:/home/marku/ai_workflow_engine/app"

# Install required packages if needed
pip install -q fastapi uvicorn sqlalchemy asyncpg redis python-multipart python-jose[cryptography] passlib[bcrypt] httpx

# Start the API
cd /home/marku/ai_workflow_engine
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload