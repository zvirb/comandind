#!/bin/bash

# MCP Servers Startup Script
# This script starts all required MCP servers for AI Workflow Orchestration

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting MCP Servers for AI Workflow Orchestration..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating storage directories..."
mkdir -p redis/data
mkdir -p memory/storage/{entities,knowledge_graph}

# Start Redis with Docker Compose
echo "🔴 Starting Redis server..."
if docker compose version &> /dev/null; then
    docker compose up -d redis
else
    docker-compose up -d redis
fi

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
for i in {1..30}; do
    if docker exec mcp_redis redis-cli ping &> /dev/null; then
        echo "✅ Redis is ready!"
        break
    fi
    sleep 1
done

# Check if Python environment exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Start Redis MCP Server
echo "🔴 Starting Redis MCP Server..."
nohup python redis/redis_mcp_server.py > logs/redis_mcp.log 2>&1 &
REDIS_MCP_PID=$!
echo "Redis MCP Server PID: $REDIS_MCP_PID"

# Start Memory MCP Server
echo "💾 Starting Memory MCP Server..."
nohup python memory/memory_mcp_server.py > logs/memory_mcp.log 2>&1 &
MEMORY_MCP_PID=$!
echo "Memory MCP Server PID: $MEMORY_MCP_PID"

# Save PIDs to file for shutdown script
echo "$REDIS_MCP_PID" > pids/redis_mcp.pid
echo "$MEMORY_MCP_PID" > pids/memory_mcp.pid

# Wait a moment for servers to start
sleep 3

# Check server health
echo ""
echo "🔍 Checking server health..."

# Check Redis MCP
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Redis MCP Server is healthy"
else
    echo "⚠️  Redis MCP Server health check failed"
fi

# Check Memory MCP
if curl -s http://localhost:8002/health > /dev/null; then
    echo "✅ Memory MCP Server is healthy"
else
    echo "⚠️  Memory MCP Server health check failed"
fi

echo ""
echo "🎉 MCP Servers started successfully!"
echo ""
echo "📍 Service Endpoints:"
echo "   Redis Database: localhost:6379"
echo "   Redis MCP API:  http://localhost:8001"
echo "   Memory MCP API: http://localhost:8002"
echo ""
echo "📊 API Documentation:"
echo "   Redis MCP:  http://localhost:8001/docs"
echo "   Memory MCP: http://localhost:8002/docs"
echo ""
echo "🛑 To stop servers, run: ./stop_mcp_servers.sh"