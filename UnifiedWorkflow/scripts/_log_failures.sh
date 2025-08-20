#!/bin/bash
# Exit immediately if a command fails.
set -e

# The name of the container that failed, passed as the first argument.
FAILED_CONTAINER_NAME=$1

# This path corresponds to the mounted volume in docker-compose.
LOGS_DIR="/app/logs"
mkdir -p $LOGS_DIR

# Get the current timestamp.
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "---"
echo "🚨 Failure Detected in container: $FAILED_CONTAINER_NAME at $TIMESTAMP"
echo "---"
echo "Collecting logs from all project containers..."

# Loop through all containers (running or stopped).
for container_id in $(docker ps -aq); do
    container_name=$(docker inspect --format='{{.Name}}' "$container_id" | sed 's,^/,,')

    # Filter to only get logs for containers belonging to this project.
    # Based on your logs, your containers are prefixed with 'ai_workflow_engine'.
    if [[ $container_name == ai_workflow_engine* ]]; then
        # Sanitize the container name for the file format.
        sanitized_name=$(echo "$container_name" | sed 's/^ai_workflow_engine-//;s/-1$//')
        LOG_FILE="$LOGS_DIR/${TIMESTAMP}_${sanitized_name}.log"

        echo "   -> Saving inspect output and logs for '$container_name' to '$LOG_FILE'"

        # Save the inspect output and logs for the container to the file.
        {
            echo "--- DOCKER INSPECT: $container_name ($container_id) ---"
            docker inspect "$container_id"
            echo -e "\n--- DOCKER LOGS: $container_name ($container_id) ---"
            docker logs "$container_id"
        } > "$LOG_FILE" 2>&1
    fi
done

echo "---"
echo "✅ Log collection complete."
echo "---"