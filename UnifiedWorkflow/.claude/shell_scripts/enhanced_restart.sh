#!/bin/bash

# Enhanced Restart Script with Improved Startup Sequencing

set -e

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Wait for service to be available
wait_for_service() {
    local host=$1
    local port=$2
    local timeout=${3:-60}
    local start_time=$(date +%s)

    log "Waiting for $host:$port to be available..."
    while ! nc -z "$host" "$port"; do
        local current_time=$(date +%s)
        if [ $((current_time - start_time)) -gt "$timeout" ]; then
            log "ERROR: Service $host:$port did not become available within $timeout seconds"
            return 1
        fi
        sleep 1
    done
    log "Service $host:$port is now available"
}

# Orchestrated Restart Sequence
main() {
    log "Starting Orchestrated Restart"

    # Stop existing containers
    log "Stopping existing containers"
    docker-compose down --remove-orphans

    # Prune unused networks and volumes
    docker network prune -f
    docker volume prune -f

    # Start critical infrastructure services first
    log "Starting infrastructure services"
    docker-compose up -d postgres redis qdrant pgbouncer ollama

    # Wait for database and cache services
    wait_for_service localhost 5432  # Postgres
    wait_for_service localhost 6379  # Redis
    wait_for_service localhost 6333  # Qdrant

    # Start API and background workers
    log "Starting API and workers"
    docker-compose up -d api worker

    # Wait for API to be fully ready
    wait_for_service localhost 8000

    # Start frontend and additional services
    log "Starting frontend and additional services"
    docker-compose up -d webui caddy_reverse_proxy grafana prometheus

    # Final health check
    log "Performing final health checks"
    docker-compose ps
    docker-compose health

    log "Restart sequence completed successfully"
}

# Execute main function with error handling
main || {
    log "Restart sequence failed. Rolling back..."
    docker-compose down
    exit 1
}