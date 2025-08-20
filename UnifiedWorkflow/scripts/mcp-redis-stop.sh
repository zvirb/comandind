#!/bin/bash
# Stop Redis MCP server

echo "Stopping Redis MCP server..."

if docker ps --format "table {{.Names}}" | grep -q "redis-mcp"; then
    docker compose -f docker-compose-mcp.yml down
    echo "✅ Redis MCP server stopped"
else
    echo "Redis MCP server is not running"
fi