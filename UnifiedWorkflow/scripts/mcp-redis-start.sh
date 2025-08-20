#!/bin/bash
# Start Redis MCP server for Claude/Gemini coding sessions

echo "Starting Redis MCP server for coding sessions..."

# Check if already running
if docker ps --format "table {{.Names}}" | grep -q "redis-mcp"; then
    echo "Redis MCP server is already running!"
    exit 0
fi

# Start the MCP Redis instance
docker compose -f docker-compose-mcp.yml up -d redis-mcp

# Wait for it to be healthy
echo "Waiting for Redis MCP to be ready..."
timeout 30 bash -c 'until docker exec redis-mcp redis-cli -a simple_mcp_password ping 2>/dev/null | grep -q PONG; do sleep 1; done'

if [ $? -eq 0 ]; then
    echo "✅ Redis MCP server is ready at localhost:6380"
    echo "Password: simple_mcp_password"
    echo "To stop: ./scripts/mcp-redis-stop.sh"
else
    echo "❌ Failed to start Redis MCP server"
    exit 1
fi