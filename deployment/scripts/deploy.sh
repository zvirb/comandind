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
    
    # Perform enhanced health check
    if ! enhanced_health_check "game-${standby_slot}"; then
        log_error "Enhanced health check failed for ${standby_slot} slot"
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
    
    # Update nginx upstream configuration
    local nginx_dir="${PROJECT_ROOT}/deployment/nginx"
    local upstream_source="${nginx_dir}/upstream-${new_active_slot}.conf"
    local upstream_target="${nginx_dir}/upstream.conf"
    
    if [ ! -f "${upstream_source}" ]; then
        log_error "Upstream configuration template not found: ${upstream_source}"
        return 1
    fi
    
    # Backup current upstream config
    if [ -f "${upstream_target}" ]; then
        cp "${upstream_target}" "${upstream_target}.backup"
    fi
    
    # Copy new upstream configuration
    log "Updating upstream configuration to route traffic to ${new_active_slot}..."
    if ! cp "${upstream_source}" "${upstream_target}"; then
        log_error "Failed to update upstream configuration"
        return 1
    fi
    
    # Verify nginx configuration is valid
    log "Validating nginx configuration..."
    if ! docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -t; then
        log_error "Invalid nginx configuration, rolling back..."
        if [ -f "${upstream_target}.backup" ]; then
            cp "${upstream_target}.backup" "${upstream_target}"
        fi
        return 1
    fi
    
    # Update container labels for tracking
    docker container update --label-add "deployment.status=active" "game-${new_active_slot}" || true
    if [ "${old_active_slot}" != "none" ]; then
        docker container update --label-add "deployment.status=standby" "game-${old_active_slot}" || true
    fi
    
    # PERFORMANCE OPTIMIZATION: Synchronize static assets before nginx reload
    log "Synchronizing static assets for ${new_active_slot} environment..."
    local sync_script="${SCRIPT_DIR}/sync-static-assets.sh"
    if [ -f "${sync_script}" ]; then
        if ! "${sync_script}" "${new_active_slot}" sync; then
            log_warning "Static asset synchronization failed, continuing with deployment..."
            # Don't fail deployment for static asset sync issues, but log the problem
        else
            log_success "Static assets synchronized successfully"
        fi
    else
        log_warning "Static asset sync script not found, skipping optimization"
    fi
    
    # Gracefully reload nginx configuration
    log "Reloading nginx to apply new upstream configuration..."
    if ! docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -s reload; then
        log_warning "Graceful reload failed, attempting restart..."
        if ! docker compose -f "${COMPOSE_FILE}" restart nginx-lb; then
            log_error "Failed to restart nginx load balancer"
            # Restore backup configuration
            if [ -f "${upstream_target}.backup" ]; then
                cp "${upstream_target}.backup" "${upstream_target}"
                docker compose -f "${COMPOSE_FILE}" restart nginx-lb
            fi
            return 1
        fi
        # Wait for nginx to stabilize after restart
        sleep 10
    fi
    
    # Verify traffic is actually routing to new slot
    log "Verifying traffic routing to ${new_active_slot}..."
    if ! verify_traffic_routing "${new_active_slot}"; then
        log_error "Traffic verification failed, rolling back..."
        # Restore backup configuration
        if [ -f "${upstream_target}.backup" ]; then
            cp "${upstream_target}.backup" "${upstream_target}"
            docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -s reload || docker compose -f "${COMPOSE_FILE}" restart nginx-lb
        fi
        return 1
    fi
    
    # Clean up backup
    rm -f "${upstream_target}.backup"
    
    log_success "Traffic successfully switched to ${new_active_slot} slot"
    log_success "Upstream configuration updated and nginx reloaded"
}

# Verify traffic is routing to the expected slot
verify_traffic_routing() {
    local expected_slot=$1
    local retries=5
    local interval=5
    
    for i in $(seq 1 $retries); do
        # Get the container IP for the expected slot
        local container_ip=$(docker inspect "game-${expected_slot}" --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
        
        if [ -z "${container_ip}" ]; then
            log_warning "Could not determine container IP for ${expected_slot}, attempt $i/$retries"
            sleep $interval
            continue
        fi
        
        # Test through load balancer to see if we reach the expected container
        local response_headers=$(docker compose -f "${COMPOSE_FILE}" exec nginx-lb curl -s -I http://localhost/health 2>/dev/null || echo "")
        
        if echo "${response_headers}" | grep -q "HTTP/1.1 200"; then
            log "Traffic routing verification successful (attempt $i/$retries)"
            return 0
        fi
        
        if [ $i -lt $retries ]; then
            log "Traffic routing verification failed, retrying in ${interval}s (attempt $i/$retries)..."
            sleep $interval
        fi
    done
    
    log_error "Traffic routing verification failed after $retries attempts"
    return 1
}

# Enhanced health check with slot verification
enhanced_health_check() {
    local service_name=$1
    local retries=${2:-${HEALTH_CHECK_RETRIES}}
    local interval=${3:-${HEALTH_CHECK_INTERVAL}}
    
    log "Performing enhanced health check for ${service_name}..."
    
    for i in $(seq 1 $retries); do
        # Container health check
        if ! docker compose -f "${COMPOSE_FILE}" exec -T "${service_name}" /usr/local/bin/health-check.sh quick >/dev/null 2>&1; then
            if [ $i -lt $retries ]; then
                log "Health check failed for ${service_name}, retrying in ${interval}s (attempt $i/$retries)..."
                sleep $interval
                continue
            else
                log_error "Health check failed for ${service_name} after $retries attempts"
                return 1
            fi
        fi
        
        # Additional endpoint verification
        local container_ip=$(docker inspect "${service_name}" --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
        if [ -n "${container_ip}" ]; then
            if docker compose -f "${COMPOSE_FILE}" exec nginx-lb curl -f -s "http://${container_ip}:8080/health" >/dev/null 2>&1; then
                log_success "Enhanced health check passed for ${service_name} (attempt $i/$retries)"
                return 0
            fi
        fi
        
        if [ $i -lt $retries ]; then
            log "Enhanced health check failed for ${service_name}, retrying in ${interval}s (attempt $i/$retries)..."
            sleep $interval
        fi
    done
    
    log_error "Enhanced health check failed for ${service_name} after $retries attempts"
    return 1
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
    if ! enhanced_health_check "game-${rollback_target}" 3 10; then
        log_error "Rollback target ${rollback_target} is not healthy"
        return 1
    fi
    
    # Switch traffic back
    if ! switch_traffic "${rollback_target}" "${current_active}"; then
        log_error "Failed to switch traffic during rollback"
        return 1
    fi
    
    # Verify rollback was successful
    if ! verify_traffic_routing "${rollback_target}"; then
        log_error "Rollback traffic verification failed"
        return 1
    fi
    
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
    
    # Perform final enhanced health check before switching traffic
    log "Performing final enhanced health check before traffic switch..."
    if ! enhanced_health_check "game-${standby_slot}" 5 15; then
        log_error "Final enhanced health check failed, rolling back..."
        docker compose -f "${COMPOSE_FILE}" stop "game-${standby_slot}" || true
        exit 1
    fi
    
    # Switch traffic
    switch_traffic "${standby_slot}" "${active_slot}"
    
    # Verify new active slot after traffic switch
    log "Verifying new active slot after traffic switch..."
    sleep 30
    
    if ! enhanced_health_check "game-${standby_slot}" 3 10; then
        log_error "Post-switch enhanced health check failed, initiating rollback..."
        rollback "${standby_slot}" "${active_slot}"
        exit 1
    fi
    
    # Additional verification that traffic is actually routing correctly
    if ! verify_traffic_routing "${standby_slot}"; then
        log_error "Traffic routing verification failed, initiating rollback..."
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
        enhanced_health_check "game-${slot}"
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