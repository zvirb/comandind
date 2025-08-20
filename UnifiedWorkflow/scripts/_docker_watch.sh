#!/bin/bash
# scripts/_docker_watch.sh
# Provides a simple, refreshing dashboard to monitor container status and logs.

clear
echo "--- ai_workflow_engine Docker Watch (GPU Profile) ---"
echo "Press Ctrl+C to exit."

# Use watch to refresh every 2 seconds
watch -n 2 "
  echo '-------------------------------------'
  echo '    Container Status     '
  echo '-------------------------------------'
  docker compose ps
  echo
  echo '-------------------------------------'
  echo '     Recent Errors & Warnings        '
  echo '-------------------------------------'
  docker compose logs --tail 20 --no-log-prefix 2>&1 | grep -iE 'error|warn|fail|fatal|exception' || echo 'No recent errors/warnings'
"
