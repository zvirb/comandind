#!/bin/bash

# Start Integrated MCP Server
echo "🚀 Starting Integrated MCP Server..."

# Create storage directories
mkdir -p mcp_servers/storage/{entities,knowledge_graph}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "mcp_venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv mcp_venv
fi

# Activate virtual environment
source mcp_venv/bin/activate

# Install required packages
echo "📦 Installing dependencies..."
pip install -q fastapi uvicorn pydantic

# Start the integrated server
echo "🔧 Starting server on port 8000..."
python mcp_servers/integrated_mcp_server.py &
SERVER_PID=$!

# Save PID
echo $SERVER_PID > mcp_server.pid

# Wait for server to start
sleep 3

# Check health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Integrated MCP Server is running!"
    echo ""
    echo "📍 Service Endpoint: http://localhost:8000"
    echo "📊 API Documentation: http://localhost:8000/docs"
    echo "📈 Server Status: http://localhost:8000/status"
    echo ""
    echo "Server PID: $SERVER_PID (saved to mcp_server.pid)"
    echo "To stop: ./stop_integrated_mcp.sh"
else
    echo "⚠️ Server health check failed"
fi