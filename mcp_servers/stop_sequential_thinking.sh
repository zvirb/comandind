#!/bin/bash

# Stop Sequential Thinking MCP Server

echo "🛑 Stopping Sequential Thinking server..."

if [ -f "sequential_thinking.pid" ]; then
    ST_PID=$(cat sequential_thinking.pid)
    if ps -p $ST_PID > /dev/null 2>&1; then
        echo "Stopping server (PID: $ST_PID)..."
        kill $ST_PID
        sleep 1
        if ps -p $ST_PID > /dev/null 2>&1; then
            kill -9 $ST_PID 2>/dev/null || true
        fi
        echo "✅ Server stopped"
    else
        echo "Server not running (PID: $ST_PID)"
    fi
    rm sequential_thinking.pid
else
    echo "No PID file found. Server may not be running."
fi