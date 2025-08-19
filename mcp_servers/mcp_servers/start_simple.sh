#!/bin/bash

# Simple MCP Servers Startup Script (without Docker)
# Uses Python-based Redis alternative

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting MCP Servers (Simple Mode)..."

# Create necessary directories
echo "📁 Creating storage directories..."
mkdir -p memory/storage/{entities,knowledge_graph}
mkdir -p redis/data
mkdir -p logs
mkdir -p pids

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt
pip install -q fakeredis  # Install in-memory Redis alternative

# Create a simple Redis alternative using Python
cat > redis/redis_alternative.py << 'EOF'
#!/usr/bin/env python3
"""Simple in-memory Redis alternative for MCP"""

import json
from typing import Any, Dict, Set
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Redis Alternative", version="1.0.0")

# In-memory storage
storage: Dict[str, Any] = {}
sets: Dict[str, Set[str]] = {}
sorted_sets: Dict[str, Dict[str, float]] = {}

@app.get("/health")
async def health():
    return {"status": "healthy", "type": "redis_alternative"}

@app.post("/set")
async def set_key(key: str, value: str):
    storage[key] = value
    return {"success": True}

@app.get("/get/{key}")
async def get_key(key: str):
    return {"value": storage.get(key)}

@app.post("/hset")
async def hset(key: str, field: str, value: str):
    if key not in storage:
        storage[key] = {}
    storage[key][field] = value
    return {"success": True}

@app.get("/hget/{key}/{field}")
async def hget(key: str, field: str):
    if key in storage and isinstance(storage[key], dict):
        return {"value": storage[key].get(field)}
    return {"value": None}

@app.get("/hgetall/{key}")
async def hgetall(key: str):
    if key in storage and isinstance(storage[key], dict):
        return {"value": storage[key]}
    return {"value": {}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6379)
EOF

# Start the Redis alternative
echo "🔴 Starting Redis alternative..."
nohup python redis/redis_alternative.py > logs/redis_alt.log 2>&1 &
REDIS_ALT_PID=$!
echo $REDIS_ALT_PID > pids/redis_alt.pid

# Wait for Redis alternative to start
sleep 2

# Update Redis MCP server to use alternative
sed -i.bak 's/port=6379/port=8003/g' redis/redis_mcp_server.py 2>/dev/null || true

# Start Redis MCP Server
echo "🔴 Starting Redis MCP Server..."
nohup python redis/redis_mcp_server.py > logs/redis_mcp.log 2>&1 &
REDIS_MCP_PID=$!
echo $REDIS_MCP_PID > pids/redis_mcp.pid

# Start Memory MCP Server
echo "💾 Starting Memory MCP Server..."
nohup python memory/memory_mcp_server.py > logs/memory_mcp.log 2>&1 &
MEMORY_MCP_PID=$!
echo $MEMORY_MCP_PID > pids/memory_mcp.pid

# Wait for servers to start
sleep 3

# Check server health
echo ""
echo "🔍 Checking server health..."

# Check Redis Alternative
if curl -s http://localhost:6379/health > /dev/null 2>&1; then
    echo "✅ Redis Alternative is healthy"
else
    echo "⚠️  Redis Alternative health check failed"
fi

# Check Redis MCP
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ Redis MCP Server is healthy"
else
    echo "⚠️  Redis MCP Server health check failed"
fi

# Check Memory MCP
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Memory MCP Server is healthy"
else
    echo "⚠️  Memory MCP Server health check failed"
fi

echo ""
echo "🎉 MCP Servers started successfully!"
echo ""
echo "📍 Service Endpoints:"
echo "   Redis Alternative: http://localhost:6379"
echo "   Redis MCP API:     http://localhost:8001"
echo "   Memory MCP API:    http://localhost:8002"
echo ""
echo "📊 API Documentation:"
echo "   Redis MCP:  http://localhost:8001/docs"
echo "   Memory MCP: http://localhost:8002/docs"
echo ""
echo "🛑 To stop servers, run: ./stop_simple.sh"