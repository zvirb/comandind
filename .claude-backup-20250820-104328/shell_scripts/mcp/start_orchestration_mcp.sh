#!/bin/bash

# Start Claude Agent Orchestration MCP Server
# This script starts the orchestration MCP server with Redis integration

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Claude Agent Orchestration MCP Server...${NC}"

# Check if Redis MCP is running
if ! docker ps | grep -q redis-mcp; then
    echo -e "${RED}❌ Redis MCP container not running${NC}"
    exit 1
fi

# Test Redis connectivity
echo -e "${YELLOW}🔍 Testing Redis MCP connectivity...${NC}"
if docker exec redis-mcp redis-cli -a simple_mcp_password ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis MCP accessible${NC}"
else
    echo -e "${RED}❌ Redis MCP not accessible${NC}"
    exit 1
fi

# Navigate to MCP server directory
cd /home/marku/ai_workflow_engine/mcp_server

# Set Python path
export PYTHONPATH="/home/marku/ai_workflow_engine/mcp_server:$PYTHONPATH"

# Set environment variables for orchestration
export AGENT_REGISTRY_PATH="$HOME/.claude/agents"
export ORCHESTRATION_DB_PATH="$HOME/.claude/orchestration.db"
export CONTEXT_CACHE_DIR="$HOME/.claude/context-cache"
export KNOWLEDGE_GRAPH_URL="sqlite:///$HOME/.claude/knowledge.db"
export LOG_LEVEL="INFO"

# Create necessary directories
mkdir -p "$HOME/.claude/context-cache"
mkdir -p "$HOME/.claude/checkpoints"
mkdir -p "$HOME/.claude/agents"

echo -e "${GREEN}✅ Environment configured${NC}"
echo -e "${GREEN}✅ Starting Orchestration MCP Server with Redis integration...${NC}"

# Start the MCP server
exec python3 mcp_server_main.py --verbose