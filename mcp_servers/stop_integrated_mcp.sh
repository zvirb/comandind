#!/bin/bash

# Stop Integrated MCP Server
echo "🛑 Stopping Integrated MCP Server..."

if [ -f "mcp_server.pid" ]; then
    SERVER_PID=$(cat mcp_server.pid)
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "Stopping server (PID: $SERVER_PID)..."
        kill $SERVER_PID
        sleep 1
        if ps -p $SERVER_PID > /dev/null 2>&1; then
            kill -9 $SERVER_PID 2>/dev/null || true
        fi
        echo "✅ Server stopped"
    else
        echo "Server not running (PID: $SERVER_PID)"
    fi
    rm mcp_server.pid
else
    echo "No PID file found. Server may not be running."
fi