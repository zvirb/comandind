#!/bin/bash
# scripts/_diagnostic_logger.sh
# Listens for Docker container events (e.g., die, oom) and logs detailed diagnostic information.

# Get the directory of the script itself, and from there, find the project root's log directory.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
LOG_FILE="$PROJECT_ROOT/logs/error_log.txt"
mkdir -p "$(dirname "$LOG_FILE")"

echo "--- Diagnostic Logger Started at $(date) ---"

# Listen for container 'die' or 'oom' (Out Of Memory) events
docker events --filter type=container --filter event=die --filter event=oom --format '{{json .}}' | while read -r event; do
    # Use jq to parse the JSON event data
    container_id=$(echo "$event" | jq -r '.id')
    container_name=$(echo "$event" | jq -r '.Actor.Attributes.name')
    
    # Only log for containers that are part of this project
    project_name=$(docker inspect "$container_id" | jq -r '.[0].Config.Labels["com.docker.compose.project"]' 2>/dev/null)
    expected_project_name=$(basename "$PROJECT_ROOT")
    expected_project_name_normalized=$(echo "$expected_project_name" | tr -d '_-' | tr '[:upper:]' '[:lower:]')
    project_name_normalized=$(echo "$project_name" | tr -d '_-' | tr '[:upper:]' '[:lower:]')

    if [[ -z "$project_name" || "$project_name_normalized" != "$expected_project_name_normalized" ]]; then
        continue # Ignore events from other projects
    fi

    # --- Log Header ---
    echo "" >> "$LOG_FILE"
    echo "--- CONTAINER FAILURE LOGGED AT $(date) for service: $container_name ---" >> "$LOG_FILE"
    
    # Capture the command used to invoke the setup script
    invocation_cmd_path="$PROJECT_ROOT/logs/.last_invocation_command"
    if [ -f "$invocation_cmd_path" ]; then
        echo "Invocation Command: $(cat "$invocation_cmd_path")" >> "$LOG_FILE"
    else
        echo "Invocation Command: Not captured" >> "$LOG_FILE"
    fi
    echo "" >> "$LOG_FILE"

    # --- Detailed Container Inspection ---
    container_inspect_json=$(docker inspect "$container_id")
    
    echo "--- STATE & HEALTH ---" >> "$LOG_FILE"
    echo "$container_inspect_json" | jq '.[0].State' >> "$LOG_FILE"
    last_health_check=$(echo "$container_inspect_json" | jq -r '.[0].State.Health.Log[-1].Output // "N/A"')
    echo "Last Health Check Output: $last_health_check" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    echo "--- CONFIGURATION ---" >> "$LOG_FILE"
    echo "Command: $(echo "$container_inspect_json" | jq '.[0].Config.Cmd')" >> "$LOG_FILE"
    echo "Environment Variables:" >> "$LOG_FILE"
    echo "$container_inspect_json" | jq -r '.[0].Config.Env[]' | sed 's/^/  - /' >> "$LOG_FILE"
    echo "Volume Mounts:" >> "$LOG_FILE"
    echo "$container_inspect_json" | jq -r '.[0].Mounts | .[] | "  - Source: \(.Source)\n    Destination: \(.Destination)\n    Mode: \(.Mode)"' >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # --- Entrypoint Script Logging ---
    entrypoint_path=$(echo "$container_inspect_json" | jq -r '.[0].Config.Entrypoint | if type == "array" then .[0] else . end')
    if [[ -n "$entrypoint_path" && "$entrypoint_path" != "null" ]]; then
        echo "--- ENTRYPOINT SCRIPT ---" >> "$LOG_FILE"
        echo "Path inside container: $entrypoint_path" >> "$LOG_FILE"
        echo "--- SCRIPT CONTENT START ---" >> "$LOG_FILE"
        docker exec "$container_id" cat "$entrypoint_path" >> "$LOG_FILE" 2>/dev/null || echo "Could not read entrypoint script." >> "$LOG_FILE"
        echo "--- SCRIPT CONTENT END ---" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
    fi

    # --- Docker Events & Logs ---
    echo "--- RECENT DOCKER EVENTS (last 60s) ---" >> "$LOG_FILE"
docker events --since 60s --until 0s --filter "container=$container_name" --format '{{.Time}} {{.Action}}' | sort -r | head -n 20 >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    echo "--- CONTAINER LOGS (last 200 lines) ---" >> "$LOG_FILE"
    # Using --tail to avoid dumping excessively large logs.
    docker logs --tail 200 "$container_id" >> "$LOG_FILE" 2>&1
    echo "" >> "$LOG_FILE"
    
    echo "--- END ERROR LOG ---" >> "$LOG_FILE"
done