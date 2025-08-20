#!/bin/bash
# scripts/_noisy_log_collector.sh
# Periodically collects and summarizes noisy logs from all running containers.

SCRIPT_DIR="/app/scripts"
LOG_DIR="/app/logs"
NOISY_LOG="$LOG_DIR/noisy_logs.log"
NOISY_SUMMARY="$LOG_DIR/noisy_summary.log"
mkdir -p "$LOG_DIR"

source "$SCRIPT_DIR/_log_formatter.sh"

NOISY_PATTERNS=(
    "error"
    "warn"
    "fail"
    "fatal"
    "exception"
)

while true; do
    echo "--- Noisy Log Capture Run at $(date) ---" > "$NOISY_LOG"
    
    # Get all running project containers
    docker compose ps -q | while read -r container_id; do
        if [ -z "$container_id" ]; then continue; fi
        
        container_name=$(docker inspect -f '{{.Name}}' "$container_id" | sed 's/\///')
        service_name=$(extract_service_name "$container_name")

        # Grab recent logs and filter for noisy patterns
        docker logs --tail 200 "$container_id" 2>&1 | while IFS= read -r line; do
            for pattern in "${NOISY_PATTERNS[@]}"; do
                if echo "$line" | grep -qi "$pattern"; then
                    echo "[$service_name] $line" >> "$NOISY_LOG"
                    break # Avoid duplicate lines for multiple pattern matches
                fi
            done
        done
    done

    # Generate the summary for the noisy log
    echo "=== NOISY LOG SUMMARY (Last 90s) ===" > "$NOISY_SUMMARY"
    echo "Counts per service:" >> "$NOISY_SUMMARY"
    if [ -f "$NOISY_LOG" ]; then
        grep -o '^\[[a-zA-Z_-]*\]' "$NOISY_LOG" | sort | uniq -c | sort -nr >> "$NOISY_SUMMARY"
    fi
    echo "" >> "$NOISY_SUMMARY"

    sleep 90
done
