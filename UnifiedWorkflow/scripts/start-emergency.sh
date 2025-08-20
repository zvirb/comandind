#!/bin/bash

echo "Starting Emergency AIWFE Services..."

# Kill any existing containers
docker rm -f api-emergency webui-emergency 2>/dev/null

# Start API
echo "Starting API container..."
docker run -d --name api-emergency \
  --network ai_workflow_engine_ai_workflow_engine_net \
  -p 8000:8000 \
  -v $(pwd):/project \
  -e DATABASE_URL=postgresql://ai_workflow_admin:YBFYsQ2mKL@postgres:5432/ai_workflow_db \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  -e QDRANT_HOST=qdrant \
  -e QDRANT_PORT=6333 \
  -e JWT_SECRET_KEY=DptuJoCCd1Yqd6qnBOCOqIFQI-0R6VySbB30lE1JT44 \
  -e CSRF_SECRET_KEY=Ow2OZe60Jkz6c6mF6V2vD1SFdN2xWXjJvQ9sMu8k8vU \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  -e PYTHONPATH=/project/app \
  -w /project \
  python:3.11 \
  bash -c "pip install fastapi uvicorn sqlalchemy psycopg2-binary redis httpx python-jose python-multipart passlib tenacity qdrant-client bcrypt && cd /project/app/api && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

# Start WebUI
echo "Starting WebUI container..."
docker run -d --name webui-emergency \
  --network ai_workflow_engine_ai_workflow_engine_net \
  -p 3000:3000 \
  -v $(pwd)/app/webui-next:/app \
  -e NEXT_PUBLIC_API_URL=http://api-emergency:8000 \
  -e NODE_ENV=production \
  -w /app \
  node:18-alpine \
  sh -c "npm install && npm run dev"

echo "Containers starting..."
echo "API will be available at: http://localhost:8000"
echo "WebUI will be available at: http://localhost:3000"
echo ""
echo "Check logs with:"
echo "  docker logs api-emergency"
echo "  docker logs webui-emergency"