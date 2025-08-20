#!/bin/bash
# MCP Session Manager - tracks active sessions and manages Redis lifecycle

SESSION_DIR="/tmp/mcp-sessions"
REDIS_COMPOSE_FILE="/home/marku/ai_workflow_engine/docker-compose-mcp.yml"
SESSION_TIMEOUT=1800  # 30 minutes

# Ensure session directory exists
mkdir -p "$SESSION_DIR"

# Function to create a session marker
create_session() {
    local session_id=$(date +%s)_$$
    echo $session_id > "$SESSION_DIR/session_${session_id}"
    echo $session_id
}

# Function to cleanup expired sessions
cleanup_expired_sessions() {
    local current_time=$(date +%s)
    for session_file in "$SESSION_DIR"/session_*; do
        if [ -f "$session_file" ]; then
            local session_time=$(basename "$session_file" | cut -d'_' -f2)
            if [ $((current_time - session_time)) -gt $SESSION_TIMEOUT ]; then
                rm -f "$session_file"
            fi
        fi
    done
}

# Function to check if any active sessions exist
has_active_sessions() {
    cleanup_expired_sessions
    [ $(ls -1 "$SESSION_DIR"/session_* 2>/dev/null | wc -l) -gt 0 ]
}

# Function to ensure Redis is running
ensure_redis_running() {
    if ! docker ps --format "table {{.Names}}" | grep -q "redis-mcp"; then
        echo "🚀 Starting Redis MCP server for coding session..." >&2
        cd /home/marku/ai_workflow_engine
        docker compose -f docker-compose-mcp.yml up -d redis-mcp >&2
        
        # Wait for it to be ready
        timeout 30 bash -c 'until docker exec redis-mcp redis-cli -a simple_mcp_password ping 2>/dev/null | grep -q PONG; do sleep 1; done' >&2
        
        if [ $? -eq 0 ]; then
            echo "✅ Redis MCP server is ready" >&2
        else
            echo "❌ Failed to start Redis MCP server" >&2
            exit 1
        fi
    fi
}

# Function to stop Redis if no active sessions
stop_redis_if_idle() {
    if ! has_active_sessions && docker ps --format "table {{.Names}}" | grep -q "redis-mcp"; then
        echo "🧹 No active sessions, stopping Redis MCP server..." >&2
        cd /home/marku/ai_workflow_engine
        docker compose -f docker-compose-mcp.yml down >&2
        echo "✅ Redis MCP server stopped" >&2
    fi
}

# Main logic based on command
case "${1:-start}" in
    "start")
        ensure_redis_running
        session_id=$(create_session)
        echo "Session started: $session_id" >&2
        
        # Schedule cleanup check
        (
            sleep $SESSION_TIMEOUT
            stop_redis_if_idle
        ) &
        ;;
    "cleanup")
        stop_redis_if_idle
        ;;
    "status")
        if has_active_sessions; then
            echo "Active sessions: $(ls -1 "$SESSION_DIR"/session_* 2>/dev/null | wc -l)" >&2
        else
            echo "No active sessions" >&2
        fi
        ;;
esac