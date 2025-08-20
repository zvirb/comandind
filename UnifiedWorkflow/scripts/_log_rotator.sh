#!/bin/bash
# scripts/_log_rotator.sh
# Handles log rotation for application logs to prevent disk space issues

# Get the directory of the script itself, and from there, find the project root's log directory.
SCRIPT_DIR="/app/scripts"
PROJECT_ROOT="/app"
LOG_DIR="$PROJECT_ROOT/logs"

# Configuration
MAX_SIZE_MB=10          # Rotate when log exceeds 10MB
MAX_FILES=5             # Keep 5 rotated files
CHECK_INTERVAL=3600     # Check every hour

echo "--- Log Rotator Started at $(date) ---"
echo "Configuration: Max size: ${MAX_SIZE_MB}MB, Max files: $MAX_FILES, Check interval: ${CHECK_INTERVAL}s"

# Function to rotate a log file
rotate_log() {
    local log_file="$1"
    local base_name=$(basename "$log_file" .log)
    local dir_name=$(dirname "$log_file")
    
    echo "Rotating log file: $log_file"
    
    # Shift existing rotated files
    for i in $(seq $((MAX_FILES - 1)) -1 1); do
        local old_file="$dir_name/${base_name}.log.$i"
        local new_file="$dir_name/${base_name}.log.$((i + 1))"
        
        if [ -f "$old_file" ]; then
            if [ $i -eq $((MAX_FILES - 1)) ]; then
                # Delete the oldest file
                rm -f "$old_file"
                echo "Deleted oldest log file: $old_file"
            else
                mv "$old_file" "$new_file"
                echo "Moved $old_file to $new_file"
            fi
        fi
    done
    
    # Move current log to .1
    if [ -f "$log_file" ]; then
        mv "$log_file" "$dir_name/${base_name}.log.1"
        touch "$log_file"
        echo "Rotated $log_file to ${base_name}.log.1"
    fi
}

# Function to check if a file needs rotation
needs_rotation() {
    local log_file="$1"
    
    if [ ! -f "$log_file" ]; then
        return 1
    fi
    
    local size_bytes=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null)
    local size_mb=$((size_bytes / 1024 / 1024))
    
    [ $size_mb -gt $MAX_SIZE_MB ]
}

# Main rotation loop
while true; do
    # List of log files to monitor for rotation
    LOG_FILES=(
        "$LOG_DIR/runtime_errors.log"
        "$LOG_DIR/application_errors.log"
        "$LOG_DIR/error_log.txt"
        "$LOG_DIR/error_summary.log"
        "$PROJECT_ROOT/app/api_debug.log"
        "$PROJECT_ROOT/app/worker_debug.log"
        "$PROJECT_ROOT/app/debug.log"
    )
    
    for log_file in "${LOG_FILES[@]}"; do
        if needs_rotation "$log_file"; then
            rotate_log "$log_file"
        fi
    done
    
    # Create cleanup summary
    cleanup_summary="$LOG_DIR/cleanup_summary.log"
    timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    echo "[$timestamp] Log rotation check completed" >> "$cleanup_summary"
    echo "[$timestamp] Total log files monitored: ${#LOG_FILES[@]}" >> "$cleanup_summary"
    
    # Calculate total log directory size
    if [ -d "$LOG_DIR" ]; then
        total_size=$(du -sh "$LOG_DIR" | cut -f1)
        echo "[$timestamp] Total log directory size: $total_size" >> "$cleanup_summary"
    fi
    
    sleep $CHECK_INTERVAL
done