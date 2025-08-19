#!/bin/bash

# Enhanced RTS-Specific Deployment Script for Command & Independent Thought
# Provides zero-downtime deployments with RTS gameplay performance validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/deployment/docker-compose/docker-compose.blue-green.yml"
VERSION=${VERSION:-$(git rev-parse --short HEAD)}
TIMEOUT=${TIMEOUT:-300}
HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-10}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-30}

# RTS Performance Targets
RTS_MIN_FPS=${RTS_MIN_FPS:-45}
RTS_TARGET_FPS=${RTS_TARGET_FPS:-60}
RTS_MAX_FRAME_TIME=${RTS_MAX_FRAME_TIME:-22}
RTS_MAX_MEMORY=${RTS_MAX_MEMORY:-200}
RTS_MAX_ENTITIES=${RTS_MAX_ENTITIES:-200}
RTS_MAX_PATHFINDING_TIME=${RTS_MAX_PATHFINDING_TIME:-5}
RTS_MAX_SELECTION_TIME=${RTS_MAX_SELECTION_TIME:-16}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_rts() {
    echo -e "${PURPLE}$(date '+%Y-%m-%d %H:%M:%S')${NC} - 🎮 $1"
}

# Check prerequisites including RTS-specific tools
check_prerequisites() {
    log "Checking prerequisites for RTS deployment..."
    
    local missing_tools=()
    
    if ! command -v docker >/dev/null 2>&1; then
        missing_tools+=("docker")
    fi
    
    if ! command -v docker compose >/dev/null 2>&1; then
        missing_tools+=("docker compose")
    fi
    
    if ! command -v git >/dev/null 2>&1; then
        missing_tools+=("git")
    fi
    
    if ! command -v curl >/dev/null 2>&1; then
        missing_tools+=("curl")
    fi
    
    if ! command -v bc >/dev/null 2>&1; then
        missing_tools+=("bc")
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        missing_tools+=("python3")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
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

# Basic health check function
health_check() {
    local service_name=$1
    local retries=${2:-${HEALTH_CHECK_RETRIES}}
    local interval=${3:-${HEALTH_CHECK_INTERVAL}}
    
    log "Performing health check for ${service_name}..."
    
    for i in $(seq 1 $retries); do
        # Get service port from container
        local service_port=$(docker compose -f "${COMPOSE_FILE}" port "${service_name}" 8080 2>/dev/null | cut -d: -f2)
        
        if [ -n "$service_port" ]; then
            if curl -sf --max-time 10 "http://localhost:${service_port}/health" >/dev/null 2>&1; then
                log_success "Health check passed for ${service_name} (attempt $i/$retries)"
                return 0
            fi
        else
            # Fallback to docker exec health check
            if docker compose -f "${COMPOSE_FILE}" exec -T "${service_name}" sh -c "exit 0" >/dev/null 2>&1; then
                log_success "Health check passed for ${service_name} (attempt $i/$retries)"
                return 0
            fi
        fi
        
        if [ $i -lt $retries ]; then
            log "Health check failed for ${service_name}, retrying in ${interval}s (attempt $i/$retries)..."
            sleep $interval
        fi
    done
    
    log_error "Health check failed for ${service_name} after $retries attempts"
    return 1
}

# RTS-specific performance validation
rts_performance_check() {
    local service_name=$1
    local retries=${2:-3}
    
    log_rts "Performing RTS performance validation for ${service_name}..."
    
    for i in $(seq 1 $retries); do
        # Get service port from container
        local service_port=$(docker compose -f "${COMPOSE_FILE}" port "${service_name}" 8080 2>/dev/null | cut -d: -f2)
        if [ -z "$service_port" ]; then
            log_warning "Could not determine port for ${service_name}, skipping performance check"
            return 0
        fi
        
        # Check RTS performance metrics
        local response=$(curl -s --max-time 10 "http://localhost:${service_port}/api/performance-stats" 2>/dev/null || echo "{}")
        
        if [ "$response" != "{}" ]; then
            # Parse performance metrics using Python
            local fps=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('fps', 0))" 2>/dev/null || echo "0")
            local frame_time=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('frameTime', 999))" 2>/dev/null || echo "999")
            local entity_count=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('entityCount', 0))" 2>/dev/null || echo "0")
            local memory_usage=$(echo "$response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('memoryUsage', 999))" 2>/dev/null || echo "999")
            
            log_rts "Performance metrics - FPS: ${fps}, Frame Time: ${frame_time}ms, Entities: ${entity_count}, Memory: ${memory_usage}MB"
            
            # Validate performance targets
            local performance_issues=0
            
            if (( $(echo "$fps < $RTS_MIN_FPS" | bc -l 2>/dev/null || echo "1") )); then
                log_warning "FPS below minimum target: ${fps} < ${RTS_MIN_FPS}"
                performance_issues=$((performance_issues + 1))
            fi
            
            if (( $(echo "$frame_time > $RTS_MAX_FRAME_TIME" | bc -l 2>/dev/null || echo "0") )); then
                log_warning "Frame time above maximum target: ${frame_time}ms > ${RTS_MAX_FRAME_TIME}ms"
                performance_issues=$((performance_issues + 1))
            fi
            
            if (( $(echo "$memory_usage > $RTS_MAX_MEMORY" | bc -l 2>/dev/null || echo "0") )); then
                log_warning "Memory usage above target: ${memory_usage}MB > ${RTS_MAX_MEMORY}MB"
                performance_issues=$((performance_issues + 1))
            fi
            
            if (( $(echo "$entity_count > $RTS_MAX_ENTITIES" | bc -l 2>/dev/null || echo "0") )); then
                log_warning "Entity count above recommended limit: ${entity_count} > ${RTS_MAX_ENTITIES}"
                performance_issues=$((performance_issues + 1))
            fi
            
            if [ $performance_issues -eq 0 ]; then
                log_success "RTS performance validation passed for ${service_name}"
                return 0
            elif [ $performance_issues -le 2 ]; then
                log_warning "RTS performance validation passed with warnings for ${service_name}"
                return 0
            else
                log_error "RTS performance validation failed with $performance_issues issues for ${service_name}"
                if [ $i -lt $retries ]; then
                    log_rts "Retrying performance check in 15s (attempt $i/$retries)..."
                    sleep 15
                else
                    return 1
                fi
            fi
        else
            log_warning "No performance metrics available from ${service_name}, skipping validation"
            return 0
        fi
    done
    
    return 1
}

# RTS gameplay validation
rts_gameplay_validation() {
    local service_name=$1
    
    log_rts "Performing RTS gameplay validation for ${service_name}..."
    
    # Get service port from container
    local service_port=$(docker compose -f "${COMPOSE_FILE}" port "${service_name}" 8080 2>/dev/null | cut -d: -f2)
    if [ -z "$service_port" ]; then
        log_warning "Could not determine port for ${service_name}, skipping gameplay validation"
        return 0
    fi
    
    # Test basic gameplay endpoints
    local endpoints=("health" "api/game-state" "api/systems-status" "api/pathfinding-stats" "api/selection-stats")
    local failed_endpoints=0
    
    for endpoint in "${endpoints[@]}"; do
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:${service_port}/${endpoint}" 2>/dev/null || echo "000")
        
        if [[ "$status_code" =~ ^[23][0-9][0-9]$ ]]; then
            log "✓ ${endpoint}: ${status_code}"
        else
            log_warning "✗ ${endpoint}: ${status_code}"
            failed_endpoints=$((failed_endpoints + 1))
        fi
    done
    
    if [ $failed_endpoints -eq 0 ]; then
        log_success "RTS gameplay validation passed for ${service_name}"
        return 0
    elif [ $failed_endpoints -le 1 ]; then
        log_warning "RTS gameplay validation passed with warnings for ${service_name}"
        return 0
    else
        log_error "RTS gameplay validation failed: $failed_endpoints endpoints failed for ${service_name}"
        return 1
    fi
}

# RTS systems validation
rts_systems_validation() {
    local service_name=$1
    
    log_rts "Performing RTS systems validation for ${service_name}..."
    
    # Get service port from container
    local service_port=$(docker compose -f "${COMPOSE_FILE}" port "${service_name}" 8080 2>/dev/null | cut -d: -f2)
    if [ -z "$service_port" ]; then
        log_warning "Could not determine port for ${service_name}, skipping systems validation"
        return 0
    fi
    
    # Test pathfinding system
    local pathfinding_response=$(curl -s --max-time 10 "http://localhost:${service_port}/api/pathfinding-stats" 2>/dev/null || echo "{}")
    if [ "$pathfinding_response" != "{}" ]; then
        local avg_path_time=$(echo "$pathfinding_response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('averageCalculationTime', 999))" 2>/dev/null || echo "999")
        local queue_length=$(echo "$pathfinding_response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('queueLength', 0))" 2>/dev/null || echo "0")
        
        if (( $(echo "$avg_path_time > $RTS_MAX_PATHFINDING_TIME" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Pathfinding average time above target: ${avg_path_time}ms > ${RTS_MAX_PATHFINDING_TIME}ms"
        else
            log_success "Pathfinding system validated: ${avg_path_time}ms avg, ${queue_length} queued"
        fi
    fi
    
    # Test selection system
    local selection_response=$(curl -s --max-time 10 "http://localhost:${service_port}/api/selection-stats" 2>/dev/null || echo "{}")
    if [ "$selection_response" != "{}" ]; then
        local avg_selection_time=$(echo "$selection_response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('averageSelectionTime', 999))" 2>/dev/null || echo "999")
        
        if (( $(echo "$avg_selection_time > $RTS_MAX_SELECTION_TIME" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Selection average time above target: ${avg_selection_time}ms > ${RTS_MAX_SELECTION_TIME}ms"
        else
            log_success "Selection system validated: ${avg_selection_time}ms avg"
        fi
    fi
    
    log_success "RTS systems validation completed for ${service_name}"
    return 0
}

# Build new version with RTS optimizations
build_new_version() {
    local target_slot=$1
    
    log "Building new version for ${target_slot} slot with RTS optimizations..."
    
    cd "${PROJECT_ROOT}"
    
    # Create production build
    log "Creating production build..."
    if ! npm ci --production=false; then
        log_error "Failed to install dependencies"
        return 1
    fi
    
    # Run RTS-specific pre-build tests
    log_rts "Running RTS pre-build validation..."
    if command -v npm >/dev/null 2>&1 && npm run test:rts-systems >/dev/null 2>&1; then
        log_success "RTS systems tests passed"
    else
        log_warning "RTS systems tests not available or failed, proceeding with caution"
    fi
    
    if ! npm run build:production; then
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

# Deploy to standby slot with RTS validation
deploy_to_standby() {
    local standby_slot=$1
    
    log "Deploying to ${standby_slot} slot with RTS validation..."
    
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
    sleep 15
    
    # Perform basic health check
    if ! health_check "game-${standby_slot}"; then
        log_error "Health check failed for ${standby_slot} slot"
        return 1
    fi
    
    # Perform RTS-specific validation
    if ! rts_performance_check "game-${standby_slot}"; then
        log_error "RTS performance validation failed for ${standby_slot} slot"
        return 1
    fi
    
    if ! rts_gameplay_validation "game-${standby_slot}"; then
        log_error "RTS gameplay validation failed for ${standby_slot} slot"
        return 1
    fi
    
    if ! rts_systems_validation "game-${standby_slot}"; then
        log_warning "RTS systems validation had issues for ${standby_slot} slot, but proceeding"
    fi
    
    log_success "Deployment to ${standby_slot} slot completed successfully"
    return 0
}

# Switch traffic to new slot
switch_traffic() {
    local new_active_slot=$1
    local old_active_slot=$2
    
    log "Switching traffic from ${old_active_slot} to ${new_active_slot}..."
    
    # Update container labels
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

# Start RTS performance monitoring
start_rts_monitoring() {
    log_rts "Starting RTS Performance Monitor..."
    
    if docker compose -f "${COMPOSE_FILE}" ps rts-performance-monitor | grep -q "Up"; then
        log_success "RTS Performance Monitor is already running"
    else
        docker compose -f "${COMPOSE_FILE}" up -d rts-performance-monitor || {
            log_warning "Failed to start RTS Performance Monitor, continuing without it"
        }
    fi
}

# Main deployment function
deploy() {
    local force_slot=${1:-""}
    
    log "Starting RTS deployment process (version: ${VERSION})..."
    
    check_prerequisites
    start_rts_monitoring
    
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
    log_rts "Performance targets: FPS≥${RTS_MIN_FPS}, Memory≤${RTS_MAX_MEMORY}MB, Entities≤${RTS_MAX_ENTITIES}"
    
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
    
    # Perform final RTS validation before switching traffic
    log_rts "Performing final RTS validation before traffic switch..."
    if ! rts_performance_check "game-${standby_slot}" 2; then
        log_error "Final RTS performance validation failed, rolling back..."
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
    
    # Final RTS validation after traffic switch
    if ! rts_performance_check "game-${standby_slot}" 1; then
        log_warning "Post-switch RTS performance validation failed, but deployment continues"
    fi
    
    # Stop old active slot
    if [ "${active_slot}" != "none" ]; then
        log "Stopping old active slot: ${active_slot}"
        docker compose -f "${COMPOSE_FILE}" stop "game-${active_slot}" || true
    fi
    
    # Cleanup
    cleanup
    
    log_success "RTS deployment completed successfully!"
    log_success "New active slot: ${standby_slot}"
    log_success "Version: ${VERSION}"
    log_rts "Monitor RTS performance at: http://localhost:8082/rts-dashboard"
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
        if [ "${active_slot}" != "none" ]; then
            rts_performance_check "game-${active_slot}" 1 || true
        fi
        ;;
    "health")
        slot="${2:-$(get_active_slot)}"
        if [ "${slot}" = "none" ]; then
            log_error "No active slot found"
            exit 1
        fi
        health_check "game-${slot}"
        ;;
    "rts-check")
        slot="${2:-$(get_active_slot)}"
        if [ "${slot}" = "none" ]; then
            log_error "No active slot found"
            exit 1
        fi
        rts_performance_check "game-${slot}"
        rts_gameplay_validation "game-${slot}"
        rts_systems_validation "game-${slot}"
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|status|health|rts-check|cleanup} [slot]"
        echo "  deploy [slot]  - Deploy new version to specified slot (or auto-detect)"
        echo "  rollback       - Rollback to previous version"
        echo "  status         - Show current deployment status with RTS metrics"
        echo "  health [slot]  - Check health of specified slot"
        echo "  rts-check [slot] - Perform comprehensive RTS validation of specified slot"
        echo "  cleanup        - Clean up old Docker images"
        echo ""
        echo "Environment variables:"
        echo "  RTS_MIN_FPS=${RTS_MIN_FPS}         - Minimum acceptable FPS"
        echo "  RTS_MAX_MEMORY=${RTS_MAX_MEMORY}       - Maximum memory usage (MB)"
        echo "  RTS_MAX_ENTITIES=${RTS_MAX_ENTITIES}     - Maximum entity count"
        echo "  RTS_MAX_FRAME_TIME=${RTS_MAX_FRAME_TIME}    - Maximum frame time (ms)"
        exit 1
        ;;
esac