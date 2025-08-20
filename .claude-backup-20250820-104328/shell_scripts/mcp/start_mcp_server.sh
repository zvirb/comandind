#!/bin/bash
# Start the Claude Agent Orchestrator MCP Server
# This script starts the MCP server for testing

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Claude Agent Orchestrator MCP Server...${NC}"

# Navigate to MCP server directory
cd ~/.claude-code/mcp-servers

# Activate environment
source orchestrator-env/bin/activate

# Set Python path
export PYTHONPATH="../../ai_workflow_engine/mcp_server:$PYTHONPATH"

# Set environment variables
export AGENT_REGISTRY_PATH="$HOME/.claude-code/agents"
export ORCHESTRATION_DB_PATH="$HOME/.claude-code/orchestration.db"
export CONTEXT_CACHE_DIR="$HOME/.claude-code/context-cache"
export KNOWLEDGE_GRAPH_URL="sqlite:///$HOME/.claude-code/knowledge.db"
export LOG_LEVEL="INFO"

echo -e "${GREEN}✅ Environment configured${NC}"
echo -e "${GREEN}✅ Agent registry path: $AGENT_REGISTRY_PATH${NC}"
echo -e "${GREEN}✅ Starting MCP server on stdio...${NC}"

# Start the MCP server
python3 -m claude_agent_orchestrator.server --verbose