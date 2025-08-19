#!/bin/bash

# Start Sequential Thinking MCP Server

echo "🧠 Starting Sequential Thinking MCP Server..."

# Check if the package is installed
if ! npm list -g @modelcontextprotocol/server-sequential-thinking > /dev/null 2>&1; then
    echo "📦 Installing Sequential Thinking server..."
    npm install -g @modelcontextprotocol/server-sequential-thinking
fi

# Start the server using npx
echo "🚀 Launching Sequential Thinking server..."
npx -y @modelcontextprotocol/server-sequential-thinking &
ST_PID=$!

echo $ST_PID > sequential_thinking.pid

echo "✅ Sequential Thinking server started!"
echo "   Process ID: $ST_PID"
echo ""
echo "📚 Features:"
echo "   - Break down complex problems into steps"
echo "   - Revise and refine thoughts dynamically"
echo "   - Branch into alternative reasoning paths"
echo "   - Generate and verify solution hypotheses"
echo ""
echo "🛑 To stop: ./stop_sequential_thinking.sh"