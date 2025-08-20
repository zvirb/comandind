#!/bin/bash

# Restart Profiling Script for AI Workflow Engine

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S.%N')] $*"
}

# Capture system resources before restart
log "PRE-RESTART SYSTEM RESOURCES"
top -bn1 | head -n 5
free -h
df -h

# Start timing the restart
log "RESTART SEQUENCE INITIATED"
start_time=$(date +%s.%N)

# Restart docker-compose
cd /home/marku/ai_workflow_engine
docker-compose down
docker-compose up -d

# Monitor container startup times
log "CONTAINER STARTUP MONITORING"
declare -A container_start_times
for container in $(docker ps -a --format '{{.Names}}'); do
    start_time=$(docker inspect -f '{{.State.StartedAt}}' "$container")
    health_status=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null)
    log "Container: $container, Start Time: $start_time, Health: ${health_status:-N/A}"
    
    # Additional health checks
    if [[ "$health_status" != "healthy" ]]; then
        log "POTENTIAL ISSUE: $container not reporting as healthy"
        docker logs "$container" | tail -n 20
    fi
done

# Port availability check
log "PORT AVAILABILITY CHECK"
netstat -tuln | grep -E '80|443|3000|3001|8000|11434'

# Capture system resources after restart
log "POST-RESTART SYSTEM RESOURCES"
top -bn1 | head -n 5
free -h
df -h

# Network connectivity test
log "NETWORK CONNECTIVITY TEST"
curl -I http://localhost
curl -I https://localhost
curl -I http://localhost:3001  # Webui
curl -I http://localhost:8000  # API

# Log end of profile
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)
log "RESTART SEQUENCE COMPLETED. Total Duration: $duration seconds"