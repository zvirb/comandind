#!/bin/bash
# Simple MCP Orchestration Server Starter

cd /home/marku/ai_workflow_engine/mcp_server
export PYTHONPATH="/home/marku/ai_workflow_engine/mcp_server:$PYTHONPATH"
export AGENT_REGISTRY_PATH="/home/marku/.claude/agents"

# Create directories if they don't exist
mkdir -p /home/marku/.claude/agents
mkdir -p /home/marku/.claude/context-cache

# Start the server
exec python3 mcp_server_main.py