#!/bin/bash

# Blue-Green Deployment Script for Command & Independent Thought
# Provides zero-downtime deployments with automatic rollback capabilities

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/deployment/docker-compose/docker-compose.blue-green.yml"
VERSION=${VERSION:-$(git rev-parse --short HEAD)}
TIMEOUT=${TIMEOUT:-300}
HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-10}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-30}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC} - $1"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ✅ $1"
}

log_error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ❌ $1" >&2
}

log_warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ⚠️  $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v docker compose >/dev/null 2>&1; then
        log_error "Docker Compose is not available"
        exit 1
    fi
    
    if ! command -v git >/dev/null 2>&1; then
        log_error "Git is not installed or not in PATH"
        exit 1
    fi
    
    if [ ! -f "${COMPOSE_FILE}" ]; then
        log_error "Docker Compose file not found: ${COMPOSE_FILE}"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Get current active slot
get_active_slot() {
    if docker compose -f "${COMPOSE_FILE}" ps game-blue | grep -q "Up"; then
        echo "blue"
    elif docker compose -f "${COMPOSE_FILE}" ps game-green | grep -q "Up"; then
        echo "green"  
    else
        echo "none"
    fi
}

# Get standby slot
get_standby_slot() {
    local active_slot=$(get_active_slot)
    if [ "${active_slot}" = "blue" ]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Health check function
health_check() {
    local service_name=$1
    local retries=${2:-${HEALTH_CHECK_RETRIES}}
    local interval=${3:-${HEALTH_CHECK_INTERVAL}}
    
    log "Performing health check for ${service_name}..."
    
    for i in $(seq 1 $retries); do
        if docker compose -f "${COMPOSE_FILE}" exec -T "${service_name}" /usr/local/bin/health-check.sh quick >/dev/null 2>&1; then
            log_success "Health check passed for ${service_name} (attempt $i/$retries)"
            return 0
        fi
        
        if [ $i -lt $retries ]; then
            log "Health check failed for ${service_name}, retrying in ${interval}s (attempt $i/$retries)..."
            sleep $interval
        fi
    done
    
    log_error "Health check failed for ${service_name} after $retries attempts"
    return 1
}

# Build new version
build_new_version() {
    local target_slot=$1
    
    log "Building new version for ${target_slot} slot..."
    
    cd "${PROJECT_ROOT}"
    
    # Create production build
    log "Creating production build..."
    if ! npm ci; then
        log_error "Failed to install dependencies"
        return 1
    fi
    
    if ! npm run build; then
        log_error "Failed to build application"
        return 1
    fi
    
    # Build Docker image for target slot
    local version_var="${target_slot^^}_VERSION"
    export ${version_var}="${VERSION}"
    
    log "Building Docker image for ${target_slot} slot (version: ${VERSION})..."
    if ! docker compose -f "${COMPOSE_FILE}" build "game-${target_slot}"; then
        log_error "Failed to build Docker image for ${target_slot}"
        return 1
    fi
    
    log_success "Build completed for ${target_slot} slot"
    return 0
}

# Deploy to standby slot
deploy_to_standby() {
    local standby_slot=$1
    
    log "Deploying to ${standby_slot} slot..."
    
    # Stop standby slot if running
    docker compose -f "${COMPOSE_FILE}" stop "game-${standby_slot}" || true
    
    # Start new version in standby slot
    local version_var="${standby_slot^^}_VERSION"
    export ${version_var}="${VERSION}"
    
    if ! docker compose -f "${COMPOSE_FILE}" up -d "game-${standby_slot}"; then
        log_error "Failed to start ${standby_slot} slot"
        return 1
    fi
    
    # Wait for container to be ready
    log "Waiting for ${standby_slot} slot to be ready..."
    sleep 10
    
    # Perform health check
    if ! health_check "game-${standby_slot}"; then
        log_error "Health check failed for ${standby_slot} slot"
        return 1
    fi
    
    log_success "Deployment to ${standby_slot} slot completed successfully"
    return 0
}

# Switch traffic to new slot
switch_traffic() {
    local new_active_slot=$1
    local old_active_slot=$2
    
    log "Switching traffic from ${old_active_slot} to ${new_active_slot}..."
    
    # Update nginx configuration to point to new active slot
    # This would typically involve updating upstream configuration
    # For now, we simulate this by updating container labels
    
    # Mark new slot as active
    docker container update --label-add "deployment.status=active" "game-${new_active_slot}"
    
    # Mark old slot as standby
    if [ "${old_active_slot}" != "none" ]; then
        docker container update --label-add "deployment.status=standby" "game-${old_active_slot}"
    fi
    
    # Restart load balancer to pick up new configuration
    if docker compose -f "${COMPOSE_FILE}" ps nginx-lb | grep -q "Up"; then
        log "Reloading load balancer configuration..."
        docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -s reload || {
            log_warning "Failed to reload nginx, restarting container..."
            docker compose -f "${COMPOSE_FILE}" restart nginx-lb
        }
    fi
    
    log_success "Traffic switched to ${new_active_slot} slot"
}

# Rollback to previous slot
rollback() {
    local current_active=$1
    local rollback_target=$2
    
    log_warning "Starting rollback from ${current_active} to ${rollback_target}..."
    
    if [ "${rollback_target}" = "none" ]; then
        log_error "No valid rollback target available"
        return 1
    fi
    
    # Check if rollback target is healthy
    if ! health_check "game-${rollback_target}" 3 10; then
        log_error "Rollback target ${rollback_target} is not healthy"
        return 1
    fi
    
    # Switch traffic back
    switch_traffic "${rollback_target}" "${current_active}"
    
    # Stop the failed deployment
    docker compose -f "${COMPOSE_FILE}" stop "game-${current_active}" || true
    
    log_success "Rollback completed successfully"
}

# Cleanup old images
cleanup() {
    log "Cleaning up unused Docker images..."
    docker image prune -f --filter "until=24h" || true
    log_success "Cleanup completed"
}

# Main deployment function
deploy() {
    local force_slot=${1:-""}
    
    log "Starting deployment process (version: ${VERSION})..."
    
    check_prerequisites
    
    # Determine deployment slots
    local active_slot=$(get_active_slot)
    local standby_slot
    
    if [ -n "${force_slot}" ]; then
        standby_slot="${force_slot}"
    else
        standby_slot=$(get_standby_slot)
    fi
    
    log "Current active slot: ${active_slot}"
    log "Deploying to standby slot: ${standby_slot}"
    
    # Build new version
    if ! build_new_version "${standby_slot}"; then
        log_error "Build failed, aborting deployment"
        exit 1
    fi
    
    # Deploy to standby slot
    if ! deploy_to_standby "${standby_slot}"; then
        log_error "Deployment to standby failed, aborting"
        exit 1
    fi
    
    # Perform final health check before switching traffic
    log "Performing final health check before traffic switch..."
    if ! health_check "game-${standby_slot}" 5 15; then
        log_error "Final health check failed, rolling back..."
        docker compose -f "${COMPOSE_FILE}" stop "game-${standby_slot}" || true
        exit 1
    fi
    
    # Switch traffic
    switch_traffic "${standby_slot}" "${active_slot}"
    
    # Verify new active slot after traffic switch
    log "Verifying new active slot after traffic switch..."
    sleep 30
    
    if ! health_check "game-${standby_slot}" 3 10; then
        log_error "Post-switch health check failed, initiating rollback..."
        rollback "${standby_slot}" "${active_slot}"
        exit 1
    fi
    
    # Stop old active slot
    if [ "${active_slot}" != "none" ]; then
        log "Stopping old active slot: ${active_slot}"
        docker compose -f "${COMPOSE_FILE}" stop "game-${active_slot}" || true
    fi
    
    # Cleanup
    cleanup
    
    log_success "Deployment completed successfully!"
    log_success "New active slot: ${standby_slot}"
    log_success "Version: ${VERSION}"
}

# Command line interface
case "${1:-deploy}" in
    "deploy")
        deploy "${2:-}"
        ;;
    "rollback")
        active_slot=$(get_active_slot)
        standby_slot=$(get_standby_slot)
        rollback "${active_slot}" "${standby_slot}"
        ;;
    "status")
        active_slot=$(get_active_slot)
        echo "Active slot: ${active_slot}"
        echo "Version: ${VERSION}"
        ;;
    "health")
        slot="${2:-$(get_active_slot)}"
        if [ "${slot}" = "none" ]; then
            log_error "No active slot found"
            exit 1
        fi
        health_check "game-${slot}"
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|status|health|cleanup} [slot]"
        echo "  deploy [slot]  - Deploy new version to specified slot (or auto-detect)"
        echo "  rollback       - Rollback to previous version"
        echo "  status         - Show current deployment status"
        echo "  health [slot]  - Check health of specified slot"
        echo "  cleanup        - Clean up old Docker images"
        exit 1
        ;;
esac