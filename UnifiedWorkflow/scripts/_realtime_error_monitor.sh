#!/bin/bash
# scripts/_realtime_error_monitor.sh
# Continuously monitors running containers for runtime errors and logs them

# Get the directory of the script itself, and from there, find the project root's log directory.
SCRIPT_DIR="/app/scripts"
PROJECT_ROOT="/app"
LOG_DIR="$PROJECT_ROOT/logs"
ERROR_LOG="$LOG_DIR/runtime_errors.log"
SUMMARY_LOG="$LOG_DIR/error_summary.log"
mkdir -p "$LOG_DIR"

# Source logging utilities
source "$SCRIPT_DIR/_log_formatter.sh"

echo "--- Real-time Error Monitor Started at $(date) ---"
echo "Monitoring containers for runtime errors..."

# Error patterns to detect
ERROR_PATTERNS=(
    "ERROR"
    "CRITICAL" 
    "FATAL"
    "Exception"
    "Traceback"
    "sqlalchemy.exc"
    "psycopg2.OperationalError"
    "SSL error"
    "connection.*failed"
    "handshake.*failed"
    "certificate.*verify.*failed"
    "Authentication.*failed"
    "unauthorized"
    "500.*Internal.*Server.*Error"
)

# Function to log detected errors
log_error() {
    local container_name="$1"
    local error_line="$2"
    
    local service=$(extract_service_name "$container_name")
    local severity=$(determine_severity "$error_line")
    
    write_structured_log "$ERROR_LOG" "$severity" "$service" "$error_line"
    echo "Runtime error detected in $service: $error_line"
}

# Function to monitor a single container
monitor_container() {
    local container_id="$1"
    local container_name="$2"
    
    echo "Starting monitor for container: $container_name"
    
    # Follow container logs and filter for error patterns
    docker logs -f --tail 0 "$container_id" 2>&1 | while IFS= read -r line; do
        # Skip our own log messages to prevent infinite loops
        if echo "$line" | grep -q "Runtime error detected"; then
            continue
        fi
        
        # Check each error pattern
        for pattern in "${ERROR_PATTERNS[@]}"; do
            if echo "$line" | grep -qi "$pattern"; then
                log_error "$container_name" "$line"
                break
            fi
        done
    done &
}

# Start summary generator in background
generate_summaries() {
    while true; do
        sleep 300  # Generate summary every 5 minutes
        if [ -f "$ERROR_LOG" ]; then
            create_log_summary "$ERROR_LOG" "$SUMMARY_LOG"
        fi
    done
}
generate_summaries &

# Main monitoring loop
while true; do
    # Get all running containers for this project
    project_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep "ai_workflow_engine")
    
    if [ -z "$project_containers" ]; then
        echo "No project containers found, waiting..."
        sleep 10
        continue
    fi
    
    # Monitor each container
    while IFS= read -r container_info; do
        if [ -n "$container_info" ]; then
            container_id=$(echo "$container_info" | awk '{print $1}')
            container_name=$(echo "$container_info" | awk '{print $2}')
            
            # Check if we're already monitoring this container
            if ! pgrep -f "docker logs -f.*$container_id" > /dev/null; then
                monitor_container "$container_id" "$container_name"
            fi
        fi
    done <<< "$project_containers"
    
    # Check for new containers every 30 seconds
    sleep 30
done