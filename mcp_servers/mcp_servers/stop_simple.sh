#!/bin/bash

# Simple MCP Servers Shutdown Script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🛑 Stopping MCP Servers..."

# Function to stop a process
stop_process() {
    local pid_file=$1
    local name=$2
    
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping $name (PID: $PID)..."
            kill $PID 2>/dev/null || true
            sleep 1
            # Force kill if still running
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID 2>/dev/null || true
            fi
        fi
        rm "$pid_file"
    fi
}

# Stop all servers
stop_process "pids/redis_alt.pid" "Redis Alternative"
stop_process "pids/redis_mcp.pid" "Redis MCP Server"
stop_process "pids/memory_mcp.pid" "Memory MCP Server"

echo "✅ All MCP servers stopped."