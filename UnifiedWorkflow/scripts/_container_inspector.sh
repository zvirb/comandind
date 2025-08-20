#!/bin/bash
# scripts/_container_inspector.sh
# Periodically inspects all running containers and saves the output to a log file.

SCRIPT_DIR="/app/scripts"
LOG_DIR="/app/logs"
INSPECT_LOG="$LOG_DIR/container_inspect.log"
mkdir -p "$LOG_DIR"

while true; do
    echo "--- Container Inspection Run at $(date) ---" > "$INSPECT_LOG"

    # Get all running container IDs for the project and inspect them
    container_ids=$(docker compose ps -q)
    if [ -n "$container_ids" ]; then
        docker inspect $container_ids >> "$INSPECT_LOG" 2>&1
    else
        echo "No running project containers found." >> "$INSPECT_LOG"
    fi

    # Wait for 120 seconds before the next run
    sleep 120
done
