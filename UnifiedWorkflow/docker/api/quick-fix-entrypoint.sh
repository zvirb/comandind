#!/bin/bash
set -e

# Quick fix for missing dependencies
echo "Installing missing dependencies..."
pip install pydantic-settings tenacity PyJWT "pwdlib[argon2]" slowapi aiohttp tiktoken ollama asyncpg tavily-python beautifulsoup4 langchain langchain-ollama

# Set the correct Python path
export PYTHONPATH=/app:/app/app:/app/app/shared

# Change to the app directory containing the modules
cd /app/app

# Run the original entrypoint
exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --log-level info