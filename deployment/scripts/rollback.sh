#!/bin/bash

# Automatic Rollback System for Command & Independent Thought
# Provides intelligent rollback capabilities with validation and safety checks

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/deployment/docker-compose/docker-compose.blue-green.yml"
ROLLBACK_TIMEOUT=${ROLLBACK_TIMEOUT:-120}
VALIDATION_RETRIES=${VALIDATION_RETRIES:-5}
VALIDATION_INTERVAL=${VALIDATION_INTERVAL:-15}

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

# Get deployment status
get_deployment_status() {
    local status_output=""
    
    if docker compose -f "${COMPOSE_FILE}" ps --format json 2>/dev/null | jq -r '.[] | select(.Name | contains("game-")) | "\(.Name):\(.State):\(.Status)"' > /tmp/deployment_status.tmp 2>/dev/null; then
        status_output=$(cat /tmp/deployment_status.tmp)
        rm -f /tmp/deployment_status.tmp
    fi
    
    echo "$status_output"
}

# Determine current active and standby slots
analyze_deployment_state() {
    local status_output=$(get_deployment_status)
    local blue_state="down"
    local green_state="down"
    local active_slot="none"
    local standby_slot="none"
    
    if echo "$status_output" | grep -q "game-blue.*running"; then
        blue_state="up"
    fi
    
    if echo "$status_output" | grep -q "game-green.*running"; then
        green_state="up"
    fi
    
    # Determine active slot by checking container labels or health
    if [ "$blue_state" = "up" ] && [ "$green_state" = "up" ]; then
        # Both running - check which is marked as active
        if docker container inspect game-blue --format '{{index .Config.Labels "deployment.status"}}' 2>/dev/null | grep -q "active"; then
            active_slot="blue"
            standby_slot="green"
        elif docker container inspect game-green --format '{{index .Config.Labels "deployment.status"}}' 2>/dev/null | grep -q "active"; then
            active_slot="green"
            standby_slot="blue"
        else
            # Default to blue as active if no labels
            active_slot="blue"
            standby_slot="green"
        fi
    elif [ "$blue_state" = "up" ] && [ "$green_state" = "down" ]; then
        active_slot="blue"
        standby_slot="green"
    elif [ "$blue_state" = "down" ] && [ "$green_state" = "up" ]; then
        active_slot="green"
        standby_slot="blue"
    fi
    
    echo "${active_slot}:${standby_slot}:${blue_state}:${green_state}"
}

# Validate slot health before rollback
validate_rollback_target() {
    local target_slot=$1
    
    log "Validating rollback target: ${target_slot}"
    
    # Check if target container exists and can be started
    if ! docker compose -f "${COMPOSE_FILE}" ps "game-${target_slot}" >/dev/null 2>&1; then
        log_error "Target slot ${target_slot} container does not exist"
        return 1
    fi
    
    # Start target slot if not running
    if ! docker compose -f "${COMPOSE_FILE}" ps "game-${target_slot}" | grep -q "Up"; then
        log "Starting rollback target slot: ${target_slot}"
        if ! docker compose -f "${COMPOSE_FILE}" start "game-${target_slot}"; then
            log_error "Failed to start rollback target slot: ${target_slot}"
            return 1
        fi
        
        # Wait for startup
        sleep 30
    fi
    
    # Perform health checks
    local health_check_count=0
    while [ $health_check_count -lt $VALIDATION_RETRIES ]; do
        if docker compose -f "${COMPOSE_FILE}" exec -T "game-${target_slot}" /usr/local/bin/health-check.sh quick >/dev/null 2>&1; then
            log_success "Rollback target ${target_slot} is healthy"
            return 0
        fi
        
        health_check_count=$((health_check_count + 1))
        if [ $health_check_count -lt $VALIDATION_RETRIES ]; then
            log "Health check ${health_check_count}/${VALIDATION_RETRIES} failed for ${target_slot}, retrying in ${VALIDATION_INTERVAL}s..."
            sleep $VALIDATION_INTERVAL
        fi
    done
    
    log_error "Rollback target ${target_slot} failed health validation after ${VALIDATION_RETRIES} attempts"
    return 1
}

# Execute rollback
execute_rollback() {
    local current_active=$1
    local rollback_target=$2
    local reason=${3:-"manual"}
    
    log "Executing rollback from ${current_active} to ${rollback_target} (reason: ${reason})"
    
    # Validate rollback target
    if ! validate_rollback_target "$rollback_target"; then
        log_error "Cannot rollback to ${rollback_target} - validation failed"
        return 1
    fi
    
    # Create rollback checkpoint
    local rollback_timestamp=$(date '+%Y%m%d-%H%M%S')
    local checkpoint_file="/tmp/rollback_checkpoint_${rollback_timestamp}.json"
    
    cat > "$checkpoint_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "reason": "${reason}",
  "from_slot": "${current_active}",
  "to_slot": "${rollback_target}",
  "containers_before": $(docker compose -f "${COMPOSE_FILE}" ps --format json | jq -c '.'),
  "rollback_id": "${rollback_timestamp}"
}
EOF
    
    log "Created rollback checkpoint: ${checkpoint_file}"
    
    # Step 1: Update container labels to switch active/standby designation
    log "Updating container labels..."
    if docker container inspect "game-${rollback_target}" >/dev/null 2>&1; then
        docker container update --label-add "deployment.status=active" "game-${rollback_target}" || true
    fi
    
    if [ "$current_active" != "none" ] && docker container inspect "game-${current_active}" >/dev/null 2>&1; then
        docker container update --label-add "deployment.status=standby" "game-${current_active}" || true
    fi
    
    # Step 2: Update load balancer configuration
    log "Updating load balancer configuration..."
    if docker compose -f "${COMPOSE_FILE}" ps nginx-lb | grep -q "Up"; then
        # Reload nginx configuration
        docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -s reload 2>/dev/null || {
            log_warning "Nginx reload failed, restarting load balancer..."
            docker compose -f "${COMPOSE_FILE}" restart nginx-lb
            sleep 10
        }
    else
        log_warning "Load balancer not running, starting it..."
        docker compose -f "${COMPOSE_FILE}" start nginx-lb
        sleep 15
    fi
    
    # Step 3: Validate rollback success
    log "Validating rollback success..."
    local validation_count=0
    while [ $validation_count -lt $VALIDATION_RETRIES ]; do
        if docker compose -f "${COMPOSE_FILE}" exec -T "game-${rollback_target}" /usr/local/bin/health-check.sh full >/dev/null 2>&1; then
            log_success "Post-rollback validation successful for ${rollback_target}"
            break
        fi
        
        validation_count=$((validation_count + 1))
        if [ $validation_count -lt $VALIDATION_RETRIES ]; then
            log "Post-rollback validation ${validation_count}/${VALIDATION_RETRIES} failed, retrying in ${VALIDATION_INTERVAL}s..."
            sleep $VALIDATION_INTERVAL
        else
            log_error "Post-rollback validation failed after ${VALIDATION_RETRIES} attempts"
            
            # Attempt emergency recovery
            log_warning "Attempting emergency recovery..."
            if [ "$current_active" != "none" ]; then
                docker container update --label-add "deployment.status=active" "game-${current_active}" || true
                docker container update --label-add "deployment.status=standby" "game-${rollback_target}" || true
                docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -s reload 2>/dev/null || true
            fi
            
            return 1
        fi
    done
    
    # Step 4: Stop old active slot (optional - keep for debugging)
    if [ "$current_active" != "none" ] && [ "${KEEP_OLD_SLOT:-false}" != "true" ]; then
        log "Stopping old active slot: ${current_active}"
        docker compose -f "${COMPOSE_FILE}" stop "game-${current_active}" || {
            log_warning "Failed to stop old active slot, but rollback was successful"
        }
    fi
    
    # Step 5: Record successful rollback
    cat >> "$checkpoint_file.success" << EOF
{
  "rollback_completed": "$(date -Iseconds)",
  "validation_attempts": ${validation_count},
  "new_active_slot": "${rollback_target}",
  "containers_after": $(docker compose -f "${COMPOSE_FILE}" ps --format json | jq -c '.')
}
EOF
    
    log_success "Rollback completed successfully!"
    log_success "Active slot is now: ${rollback_target}"
    log_success "Rollback checkpoint: ${checkpoint_file}"
    
    return 0
}

# Automatic rollback based on health monitoring
auto_rollback() {
    log "Starting automatic rollback assessment..."
    
    local deployment_state=$(analyze_deployment_state)
    local active_slot=$(echo "$deployment_state" | cut -d: -f1)
    local standby_slot=$(echo "$deployment_state" | cut -d: -f2)
    local blue_state=$(echo "$deployment_state" | cut -d: -f3)
    local green_state=$(echo "$deployment_state" | cut -d: -f4)
    
    log "Current deployment state - Active: ${active_slot}, Standby: ${standby_slot}"
    
    if [ "$active_slot" = "none" ]; then
        log_error "No active slot detected - cannot perform automatic rollback"
        return 1
    fi
    
    # Check if current active slot is unhealthy
    local active_healthy=false
    if docker compose -f "${COMPOSE_FILE}" exec -T "game-${active_slot}" /usr/local/bin/health-check.sh quick >/dev/null 2>&1; then
        active_healthy=true
    fi
    
    if [ "$active_healthy" = "true" ]; then
        log_success "Active slot ${active_slot} is healthy - no rollback needed"
        return 0
    fi
    
    log_warning "Active slot ${active_slot} is unhealthy - assessing rollback options"
    
    # Check if standby slot can be used for rollback
    if [ "$standby_slot" = "none" ]; then
        log_error "No standby slot available for rollback"
        return 1
    fi
    
    # Execute automatic rollback
    if execute_rollback "$active_slot" "$standby_slot" "automatic_health_failure"; then
        log_success "Automatic rollback completed successfully"
        return 0
    else
        log_error "Automatic rollback failed"
        return 1
    fi
}

# Manual rollback
manual_rollback() {
    local target_slot=${1:-""}
    local reason=${2:-"manual"}
    
    if [ -z "$target_slot" ]; then
        log_error "Target slot must be specified for manual rollback"
        return 1
    fi
    
    local deployment_state=$(analyze_deployment_state)
    local active_slot=$(echo "$deployment_state" | cut -d: -f1)
    
    if [ "$active_slot" = "$target_slot" ]; then
        log_warning "Target slot ${target_slot} is already active"
        return 0
    fi
    
    log "Manual rollback requested to slot: ${target_slot}"
    
    if execute_rollback "$active_slot" "$target_slot" "$reason"; then
        log_success "Manual rollback completed successfully"
        return 0
    else
        log_error "Manual rollback failed"
        return 1
    fi
}

# Show rollback status and history
show_status() {
    local deployment_state=$(analyze_deployment_state)
    local active_slot=$(echo "$deployment_state" | cut -d: -f1)
    local standby_slot=$(echo "$deployment_state" | cut -d: -f2)
    local blue_state=$(echo "$deployment_state" | cut -d: -f3)
    local green_state=$(echo "$deployment_state" | cut -d: -f4)
    
    echo "=== Deployment Status ==="
    echo "Active Slot: ${active_slot}"
    echo "Standby Slot: ${standby_slot}"
    echo "Blue State: ${blue_state}"
    echo "Green State: ${green_state}"
    echo
    
    # Show health status
    echo "=== Health Status ==="
    for slot in blue green; do
        if [ "${slot}" = "blue" ] && [ "$blue_state" = "up" ] || [ "${slot}" = "green" ] && [ "$green_state" = "up" ]; then
            if docker compose -f "${COMPOSE_FILE}" exec -T "game-${slot}" /usr/local/bin/health-check.sh quick >/dev/null 2>&1; then
                echo "${slot}: ✅ Healthy"
            else
                echo "${slot}: ❌ Unhealthy"
            fi
        else
            echo "${slot}: ⏹️  Stopped"
        fi
    done
    echo
    
    # Show recent rollback history
    echo "=== Recent Rollback History ==="
    if ls /tmp/rollback_checkpoint_*.json.success 2>/dev/null | tail -5 | while read -r checkpoint; do
        if [ -f "$checkpoint" ]; then
            local timestamp=$(jq -r '.rollback_completed' "$checkpoint" 2>/dev/null || echo "Unknown")
            local from_slot=$(jq -r '.from_slot' "${checkpoint%.success}" 2>/dev/null || echo "Unknown")
            local to_slot=$(jq -r '.to_slot' "${checkpoint%.success}" 2>/dev/null || echo "Unknown")
            local reason=$(jq -r '.reason' "${checkpoint%.success}" 2>/dev/null || echo "Unknown")
            echo "${timestamp}: ${from_slot} → ${to_slot} (${reason})"
        fi
    done; then
        :
    else
        echo "No rollback history found"
    fi
}

# Command line interface
case "${1:-status}" in
    "auto")
        auto_rollback
        ;;
    "manual")
        if [ $# -lt 2 ]; then
            log_error "Usage: $0 manual <target_slot> [reason]"
            exit 1
        fi
        manual_rollback "$2" "${3:-manual}"
        ;;
    "blue"|"green")
        manual_rollback "$1" "${2:-manual}"
        ;;
    "status")
        show_status
        ;;
    "validate")
        if [ $# -lt 2 ]; then
            log_error "Usage: $0 validate <slot>"
            exit 1
        fi
        validate_rollback_target "$2"
        ;;
    *)
        echo "Usage: $0 {auto|manual|blue|green|status|validate}"
        echo ""
        echo "Commands:"
        echo "  auto                    - Perform automatic rollback if current active is unhealthy"
        echo "  manual <slot> [reason]  - Manually rollback to specified slot"
        echo "  blue [reason]          - Rollback to blue slot"
        echo "  green [reason]         - Rollback to green slot"
        echo "  status                 - Show current deployment and rollback status"
        echo "  validate <slot>        - Validate if a slot is ready for rollback"
        echo ""
        echo "Environment Variables:"
        echo "  ROLLBACK_TIMEOUT       - Rollback operation timeout (default: 120s)"
        echo "  VALIDATION_RETRIES     - Health check validation retries (default: 5)"
        echo "  VALIDATION_INTERVAL    - Interval between validations (default: 15s)"
        echo "  KEEP_OLD_SLOT         - Keep old slot running after rollback (default: false)"
        exit 1
        ;;
esac