#!/bin/bash
# scripts/_app_log_collector.sh
# Collects application debug logs and copies relevant errors to centralized logs

# Get the directory of the script itself, and from there, find the project root's log directory.
SCRIPT_DIR="/app/scripts"
PROJECT_ROOT="/app"
LOG_DIR="$PROJECT_ROOT/logs"
APP_LOG="$LOG_DIR/application_errors.log"
mkdir -p "$LOG_DIR"

echo "--- Application Log Collector Started at $(date) ---"

# Application log files to monitor
APP_LOG_FILES=(
    "/app/application/api_debug.log"
    "/app/application/worker_debug.log"
    "/app/application/debug.log"
)

# Keep track of last read positions to avoid duplicates
POSITION_FILE="$LOG_DIR/.app_log_positions"
touch "$POSITION_FILE"

# Function to get last read position for a file
get_last_position() {
    local file="$1"
    grep "^$file:" "$POSITION_FILE" | cut -d: -f2 || echo "0"
}

# Function to update last read position
update_position() {
    local file="$1"
    local position="$2"
    
    # Remove old entry and add new one
    grep -v "^$file:" "$POSITION_FILE" > "$POSITION_FILE.tmp" 2>/dev/null || true
    echo "$file:$position" >> "$POSITION_FILE.tmp"
    mv "$POSITION_FILE.tmp" "$POSITION_FILE"
}

# Function to process new lines from a log file
process_log_file() {
    local log_file="$1"
    
    if [ ! -f "$log_file" ]; then
        return 0
    fi
    
    local last_position=$(get_last_position "$log_file")
    local current_size=$(wc -c < "$log_file")
    
    # Skip if file hasn't grown
    if [ "$current_size" -le "$last_position" ]; then
        return 0
    fi
    
    # Read new content
    local new_content=$(tail -c +$((last_position + 1)) "$log_file")
    
    # Filter for error lines and add to centralized log
    echo "$new_content" | while IFS= read -r line; do
        if [ -n "$line" ] && (echo "$line" | grep -qi -E "(error|critical|fatal|exception|traceback|failed|unauthorized)"); then
            local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            local log_basename=$(basename "$log_file")
            echo "[$timestamp] [$log_basename] $line" >> "$APP_LOG"
            echo "App log error detected in $log_basename: $line"
        fi
    done
    
    # Update position
    update_position "$log_file" "$current_size"
}

# Main collection loop
while true; do
    for log_file in "${APP_LOG_FILES[@]}"; do
        process_log_file "$log_file"
    done
    
    # Check every 10 seconds
    sleep 10
done