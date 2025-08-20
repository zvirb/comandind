#!/bin/bash
# scripts/_enhanced_restart.sh
# Enhanced restart with health checks and service ordering

set -e
source "$(dirname "$0")/_common_functions.sh"

SERVICE_NAME="$1"
TIMEOUT=60
HEALTH_CHECK_INTERVAL=2

# Health check functions
check_service_health() {
    local service_name="$1"
    local timeout="$2"
    local elapsed=0
    
    log_info "Checking health for service: $service_name"
    
    while [ $elapsed -lt $timeout ]; do
        if docker compose exec "$service_name" pgrep -f "$(docker compose config | yq ".services.$service_name.command // \"node\"" | tr -d '"')" > /dev/null 2>&1; then
            log_info "Service $service_name is healthy"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        log_info "Waiting for $service_name... (${elapsed}s/${timeout}s)"
    done
    
    log_error "Service $service_name failed health check"
    return 1
}

# Port availability check
check_port_availability() {
    local service_name="$1"
    local port="$2"
    local timeout=30
    local elapsed=0
    
    log_info "Checking port availability for $service_name on port $port"
    
    while [ $elapsed -lt $timeout ]; do
        if curl -sf "http://localhost:$port" > /dev/null 2>&1; then
            log_info "Port $port is available for $service_name"
            return 0
        fi
        
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    log_warning "Port $port not responding within timeout, but continuing..."
    return 0
}

# Enhanced restart logic
enhanced_restart() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        log_error "Usage: $0 <service_name>"
        exit 1
    fi
    
    log_info "Starting enhanced restart for service: $service_name"
    
    # Step 1: Build with error handling
    log_info "Building $service_name..."
    if ! docker compose build "$service_name"; then
        log_error "Build failed for $service_name"
        return 1
    fi
    
    # Step 2: Stop service gracefully
    log_info "Stopping $service_name gracefully..."
    docker compose stop "$service_name" || log_warning "Service may already be stopped"
    
    # Step 3: Remove container to ensure clean start
    log_info "Removing old container..."
    docker compose rm -f "$service_name" || log_warning "Container may not exist"
    
    # Step 4: Start service
    log_info "Starting $service_name..."
    if ! docker compose up -d "$service_name"; then
        log_error "Failed to start $service_name"
        return 1
    fi
    
    # Step 5: Health check
    if ! check_service_health "$service_name" $TIMEOUT; then
        log_error "Health check failed for $service_name"
        return 1
    fi
    
    # Step 6: Port-specific checks
    case "$service_name" in
        "webui")
            check_port_availability "webui" "3001"
            ;;
        "grafana")
            check_port_availability "grafana" "3000"
            ;;
        "api")
            check_port_availability "api" "8000"
            ;;
    esac
    
    log_info "Enhanced restart completed successfully for $service_name"
    return 0
}

# Main execution
if enhanced_restart "$SERVICE_NAME"; then
    log_info "Service restart successful"
    
    if [[ ! " $@ " =~ " --no-watch " ]]; then
        log_info "Launching Docker Watch dashboard (Ctrl+C to exit)..."
        ./scripts/_docker_watch.sh
    fi
else
    log_error "Service restart failed"
    exit 1
fi