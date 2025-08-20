#!/bin/sh
echo "▶️ Starting Docker event listener..."

# Listen for 'die' events, which occur when a container stops.
docker events --filter 'event=die' | while read event; do
    # Extract the exit code and container name from the event details.
    EXIT_CODE=$(echo "$event" | sed -n 's/.*exitCode=\([0-9]*\).*/\1/p')
    CONTAINER_NAME=$(echo "$event" | sed -n 's/.*name=\([^,)]*\).*/\1/p')

    # Check if the exit code is non-zero, which indicates a failure.
    if [ -n "$EXIT_CODE" ] && [ "$EXIT_CODE" -ne 0 ]; then
        # If a container fails, run the log collection script.
        /app/scripts/_log_failures.sh "$CONTAINER_NAME"
    fi
done