#!/bin/bash
# Auto-start Redis MCP server wrapper for Claude/Gemini sessions

SCRIPT_DIR="/home/marku/ai_workflow_engine/scripts"

# Register this session and ensure Redis is running
"$SCRIPT_DIR/mcp-session-manager.sh" start

# Set up cleanup on exit
cleanup() {
    echo "🔄 MCP session ending, checking for cleanup..." >&2
    "$SCRIPT_DIR/mcp-session-manager.sh" cleanup
}
trap cleanup EXIT

# Now run the actual MCP Redis server
exec npx @modelcontextprotocol/server-redis "redis://:simple_mcp_password@localhost:6380"