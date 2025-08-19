#!/bin/bash

# Setup and Start Python Sequential Thinking MCP Server

echo "🧠 Setting up Sequential Thinking MCP Server (Python)..."

# Navigate to the Sequential Thinking directory
cd python-sequential-thinking-mcp/sequential-thinking-mcp

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q mcp

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in sequential-thinking-mcp directory"
    exit 1
fi

# Start the server
echo "🚀 Starting Sequential Thinking server..."
python main.py &
ST_PID=$!

# Save PID
echo $ST_PID > ../../sequential_thinking_python.pid

echo "✅ Sequential Thinking server (Python) started!"
echo "   Process ID: $ST_PID"
echo ""
echo "📚 Features:"
echo "   - Step-by-step thinking process"
echo "   - Thought revision and refinement"
echo "   - Alternative reasoning branches"
echo "   - Dynamic thought adjustment"
echo "   - Solution hypothesis generation"
echo ""
echo "🔧 Resources:"
echo "   - thoughts://history - Complete thought history"
echo "   - thoughts://branches/{id} - Specific branch thoughts"
echo "   - thoughts://summary - All thoughts summary"
echo ""
echo "🛑 To stop: kill $ST_PID"