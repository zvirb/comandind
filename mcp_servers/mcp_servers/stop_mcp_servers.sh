#!/bin/bash

# MCP Servers Shutdown Script

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🛑 Stopping MCP Servers..."

# Stop Python MCP servers
if [ -f "pids/redis_mcp.pid" ]; then
    REDIS_MCP_PID=$(cat pids/redis_mcp.pid)
    if ps -p $REDIS_MCP_PID > /dev/null; then
        echo "Stopping Redis MCP Server (PID: $REDIS_MCP_PID)..."
        kill $REDIS_MCP_PID
    fi
    rm pids/redis_mcp.pid
fi

if [ -f "pids/memory_mcp.pid" ]; then
    MEMORY_MCP_PID=$(cat pids/memory_mcp.pid)
    if ps -p $MEMORY_MCP_PID > /dev/null; then
        echo "Stopping Memory MCP Server (PID: $MEMORY_MCP_PID)..."
        kill $MEMORY_MCP_PID
    fi
    rm pids/memory_mcp.pid
fi

# Stop Redis container
echo "Stopping Redis container..."
if docker compose version &> /dev/null; then
    docker compose down
else
    docker-compose down
fi

echo "✅ All MCP servers stopped."