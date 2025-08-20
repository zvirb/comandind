#!/bin/bash
# Start the Claude Agent Orchestrator MCP Server with Ollama Integration
# This script starts the complete MCP server with all 30 agents and Ollama integration

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Claude Agent Orchestrator MCP Server with Ollama Integration...${NC}"

# Check if Ollama server is accessible
echo -e "${YELLOW}🔍 Checking Ollama server connectivity...${NC}"
if curl -s http://alienware.local:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama server accessible at alienware.local:11434${NC}"
    OLLAMA_MODELS=$(curl -s http://alienware.local:11434/api/tags | jq -r '.models[].name' 2>/dev/null | tr '\n' ', ' || echo "Unable to parse")
    echo -e "${GREEN}✅ Available models: ${OLLAMA_MODELS}${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama server not accessible, continuing with partial functionality${NC}"
fi

# Navigate to project directory
cd /home/marku/ai_workflow_engine

# Set Python path for MCP server
export PYTHONPATH="mcp_server:$PYTHONPATH"

# Set environment variables for orchestration
export AGENT_REGISTRY_PATH="$HOME/.claude-code/agents"
export ORCHESTRATION_DB_PATH="$HOME/.claude-code/orchestration.db"
export CONTEXT_CACHE_DIR="$HOME/.claude-code/context-cache"
export KNOWLEDGE_GRAPH_URL="sqlite:///$HOME/.claude-code/knowledge.db"
export LOG_LEVEL="INFO"

# Ollama integration settings
export OLLAMA_HOST="http://alienware.local:11434"
export OLLAMA_DEFAULT_MODEL="llama3.2:3b"
export OLLAMA_EMBED_MODEL="nomic-embed-text:latest"

echo -e "${GREEN}✅ Environment configured${NC}"
echo -e "${GREEN}✅ Agent registry path: $AGENT_REGISTRY_PATH${NC}"
echo -e "${GREEN}✅ Ollama host: $OLLAMA_HOST${NC}"

# Create necessary directories
mkdir -p "$HOME/.claude-code/context-cache"
mkdir -p "$HOME/.claude-code/checkpoints"

echo -e "${GREEN}✅ Starting MCP server with 30 agents and Ollama integration...${NC}"

# Start the MCP server
python3 -m claude_agent_orchestrator.server --verbose

echo -e "${BLUE}🏁 MCP Server stopped${NC}"