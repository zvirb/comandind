#!/bin/bash
# Automated Service Recovery and Restart System
# Provides intelligent service restart with health monitoring and automatic recovery procedures

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RECOVERY_LOG_DIR="$PROJECT_ROOT/logs/service_recovery"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RECOVERY_ID="recovery_${TIMESTAMP}"

# Recovery parameters
MAX_RESTART_ATTEMPTS=3
RESTART_DELAY=10
HEALTH_CHECK_INTERVAL=5
HEALTH_CHECK_TIMEOUT=30
CASCADE_RECOVERY=true

# Service dependencies map
declare -A SERVICE_DEPS
SERVICE_DEPS["api"]="postgres pgbouncer redis qdrant ollama"
SERVICE_DEPS["worker"]="postgres pgbouncer redis qdrant ollama"
SERVICE_DEPS["webui"]="api"
SERVICE_DEPS["caddy_reverse_proxy"]="api webui"
SERVICE_DEPS["coordination-service"]="postgres redis qdrant"
SERVICE_DEPS["hybrid-memory-service"]="postgres qdrant ollama"
SERVICE_DEPS["learning-service"]="postgres redis qdrant ollama"
SERVICE_DEPS["perception-service"]="ollama"
SERVICE_DEPS["reasoning-service"]="postgres redis ollama"
SERVICE_DEPS["infrastructure-recovery-service"]="postgres redis prometheus"
SERVICE_DEPS["pgbouncer"]="postgres"
SERVICE_DEPS["prometheus"]="qdrant"
SERVICE_DEPS["grafana"]="prometheus"
SERVICE_DEPS["alertmanager"]="prometheus"

# Service start order (reverse of dependencies)
STARTUP_ORDER=(
    "postgres"
    "redis"
    "qdrant"
    "ollama"
    "pgbouncer"
    "prometheus"
    "alertmanager"
    "grafana"
    "coordination-service"
    "hybrid-memory-service"
    "learning-service"
    "perception-service"
    "reasoning-service"
    "infrastructure-recovery-service"
    "api"
    "worker"
    "webui"
    "caddy_reverse_proxy"
)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Initialize recovery system
initialize_recovery() {
    echo -e "${BLUE}[INIT]${NC} Initializing service recovery system (ID: $RECOVERY_ID)"
    
    mkdir -p "$RECOVERY_LOG_DIR"
    mkdir -p "$RECOVERY_LOG_DIR/$RECOVERY_ID"
    
    # Create recovery metadata
    cat > "$RECOVERY_LOG_DIR/$RECOVERY_ID/metadata.json" << EOF
{
    "recovery_id": "$RECOVERY_ID",
    "timestamp": "$(date -Iseconds)",
    "docker_version": "$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'unknown')",
    "compose_version": "$(docker compose version --short 2>/dev/null || echo 'unknown')"
}
EOF
}

# Logging function
log_recovery() {
    local level=$1
    local message=$2
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    case $level in
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
        ERROR)   echo -e "${RED}[ERROR]${NC} $message" ;;
        WARNING) echo -e "${YELLOW}[WARNING]${NC} $message" ;;
        INFO)    echo -e "${BLUE}[INFO]${NC} $message" ;;
        RECOVER) echo -e "${CYAN}[RECOVER]${NC} $message" ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$RECOVERY_LOG_DIR/$RECOVERY_ID/recovery.log"
}

# Get service health status
get_service_health() {
    local service=$1
    local container_id=$(docker compose ps -q "$service" 2>/dev/null || echo "")
    
    if [ -z "$container_id" ]; then
        echo "not_found"
        return
    fi
    
    local running=$(docker inspect "$container_id" --format='{{.State.Running}}' 2>/dev/null || echo "false")
    local health=$(docker inspect "$container_id" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
    
    if [ "$running" != "true" ]; then
        echo "stopped"
    elif [ "$health" = "healthy" ] || [ "$health" = "none" ]; then
        echo "healthy"
    else
        echo "$health"
    fi
}

# Check service dependencies
check_dependencies() {
    local service=$1
    local deps="${SERVICE_DEPS[$service]}"
    
    if [ -z "$deps" ]; then
        return 0
    fi
    
    log_recovery "INFO" "Checking dependencies for $service: $deps"
    
    for dep in $deps; do
        local dep_health=$(get_service_health "$dep")
        if [ "$dep_health" != "healthy" ]; then
            log_recovery "WARNING" "Dependency $dep is not healthy (status: $dep_health)"
            
            if [ "$CASCADE_RECOVERY" = true ]; then
                log_recovery "RECOVER" "Attempting to recover dependency $dep first"
                if ! recover_service "$dep"; then
                    log_recovery "ERROR" "Failed to recover dependency $dep"
                    return 1
                fi
            else
                return 1
            fi
        fi
    done
    
    log_recovery "SUCCESS" "All dependencies for $service are healthy"
    return 0
}

# Graceful service stop
stop_service() {
    local service=$1
    local timeout=30
    
    log_recovery "INFO" "Stopping service $service gracefully"
    
    # Send stop signal
    docker compose stop -t $timeout "$service" 2>&1 | \
        tee "$RECOVERY_LOG_DIR/$RECOVERY_ID/${service}_stop.log" >/dev/null
    
    # Wait for complete stop
    local wait_time=0
    while [ $wait_time -lt $timeout ]; do
        local status=$(get_service_health "$service")
        if [ "$status" = "not_found" ] || [ "$status" = "stopped" ]; then
            log_recovery "SUCCESS" "Service $service stopped successfully"
            return 0
        fi
        sleep 1
        ((wait_time++))
    done
    
    # Force stop if graceful stop failed
    log_recovery "WARNING" "Graceful stop timeout, forcing stop for $service"
    docker compose kill "$service" 2>&1 | \
        tee -a "$RECOVERY_LOG_DIR/$RECOVERY_ID/${service}_stop.log" >/dev/null
    
    return 0
}

# Start service with health monitoring
start_service() {
    local service=$1
    local max_wait=$HEALTH_CHECK_TIMEOUT
    
    log_recovery "INFO" "Starting service $service"
    
    # Start the service
    docker compose up -d "$service" 2>&1 | \
        tee "$RECOVERY_LOG_DIR/$RECOVERY_ID/${service}_start.log" >/dev/null
    
    # Wait for healthy state
    local wait_time=0
    while [ $wait_time -lt $max_wait ]; do
        local health=$(get_service_health "$service")
        
        if [ "$health" = "healthy" ]; then
            log_recovery "SUCCESS" "Service $service started and healthy"
            return 0
        elif [ "$health" = "not_found" ] || [ "$health" = "stopped" ]; then
            log_recovery "ERROR" "Service $service failed to start"
            return 1
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        ((wait_time += HEALTH_CHECK_INTERVAL))
        
        if [ $((wait_time % 10)) -eq 0 ]; then
            log_recovery "INFO" "Waiting for $service to become healthy (${wait_time}s/${max_wait}s)"
        fi
    done
    
    log_recovery "ERROR" "Service $service failed to become healthy within ${max_wait}s"
    return 1
}

# Recover individual service
recover_service() {
    local service=$1
    local attempt=1
    
    log_recovery "RECOVER" "Starting recovery for service: $service"
    
    # Check current health
    local initial_health=$(get_service_health "$service")
    log_recovery "INFO" "Initial health status: $initial_health"
    
    if [ "$initial_health" = "healthy" ]; then
        log_recovery "SUCCESS" "Service $service is already healthy"
        return 0
    fi
    
    # Check dependencies first
    if ! check_dependencies "$service"; then
        log_recovery "ERROR" "Dependencies check failed for $service"
        return 1
    fi
    
    # Attempt recovery
    while [ $attempt -le $MAX_RESTART_ATTEMPTS ]; do
        log_recovery "INFO" "Recovery attempt $attempt/$MAX_RESTART_ATTEMPTS for $service"
        
        # Stop the service
        stop_service "$service"
        
        # Wait before restart
        sleep $RESTART_DELAY
        
        # Clear any lingering resources
        docker compose rm -f "$service" 2>/dev/null || true
        
        # Start the service
        if start_service "$service"; then
            log_recovery "SUCCESS" "Service $service recovered successfully"
            
            # Log recovery success
            cat > "$RECOVERY_LOG_DIR/$RECOVERY_ID/${service}_recovery.json" << EOF
{
    "service": "$service",
    "recovery_id": "$RECOVERY_ID",
    "initial_status": "$initial_health",
    "attempts": $attempt,
    "status": "recovered",
    "timestamp": "$(date -Iseconds)"
}
EOF
            return 0
        fi
        
        ((attempt++))
    done
    
    log_recovery "ERROR" "Failed to recover $service after $MAX_RESTART_ATTEMPTS attempts"
    
    # Log recovery failure
    cat > "$RECOVERY_LOG_DIR/$RECOVERY_ID/${service}_recovery.json" << EOF
{
    "service": "$service",
    "recovery_id": "$RECOVERY_ID",
    "initial_status": "$initial_health",
    "attempts": $attempt,
    "status": "failed",
    "timestamp": "$(date -Iseconds)"
}
EOF
    
    return 1
}

# Recover all unhealthy services
recover_all_services() {
    local services_to_check=("$@")
    local unhealthy_services=()
    local recovered_services=()
    local failed_services=()
    
    # If no services specified, check all
    if [ ${#services_to_check[@]} -eq 0 ]; then
        services_to_check=("${STARTUP_ORDER[@]}")
    fi
    
    log_recovery "INFO" "Checking health of ${#services_to_check[@]} services"
    
    # Identify unhealthy services
    for service in "${services_to_check[@]}"; do
        local health=$(get_service_health "$service")
        if [ "$health" != "healthy" ]; then
            unhealthy_services+=("$service")
            log_recovery "WARNING" "Service $service is unhealthy: $health"
        fi
    done
    
    if [ ${#unhealthy_services[@]} -eq 0 ]; then
        log_recovery "SUCCESS" "All services are healthy"
        return 0
    fi
    
    log_recovery "INFO" "Found ${#unhealthy_services[@]} unhealthy services"
    
    # Attempt recovery in dependency order
    for service in "${STARTUP_ORDER[@]}"; do
        if [[ " ${unhealthy_services[@]} " =~ " ${service} " ]]; then
            if recover_service "$service"; then
                recovered_services+=("$service")
            else
                failed_services+=("$service")
            fi
        fi
    done
    
    # Generate recovery report
    cat > "$RECOVERY_LOG_DIR/$RECOVERY_ID/recovery_summary.json" << EOF
{
    "recovery_id": "$RECOVERY_ID",
    "timestamp": "$(date -Iseconds)",
    "total_unhealthy": ${#unhealthy_services[@]},
    "recovered": ${#recovered_services[@]},
    "failed": ${#failed_services[@]},
    "unhealthy_services": $(printf '%s\n' "${unhealthy_services[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "recovered_services": $(printf '%s\n' "${recovered_services[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "failed_services": $(printf '%s\n' "${failed_services[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
}
EOF
    
    # Print summary
    echo -e "\n${BLUE}=== Recovery Summary ===${NC}"
    echo -e "Unhealthy services found: ${#unhealthy_services[@]}"
    echo -e "Services recovered: ${GREEN}${#recovered_services[@]}${NC}"
    echo -e "Services failed: ${RED}${#failed_services[@]}${NC}"
    
    if [ ${#recovered_services[@]} -gt 0 ]; then
        echo -e "\n${GREEN}Recovered services:${NC}"
        printf '%s\n' "${recovered_services[@]}"
    fi
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        echo -e "\n${RED}Failed services:${NC}"
        printf '%s\n' "${failed_services[@]}"
        return 1
    fi
    
    return 0
}

# Full system restart
full_system_restart() {
    log_recovery "INFO" "Initiating full system restart"
    
    # Stop all services in reverse order
    echo -e "\n${BLUE}=== Stopping All Services ===${NC}"
    for ((i=${#STARTUP_ORDER[@]}-1; i>=0; i--)); do
        local service="${STARTUP_ORDER[$i]}"
        stop_service "$service"
    done
    
    # Wait for complete shutdown
    sleep 10
    
    # Start all services in order
    echo -e "\n${BLUE}=== Starting All Services ===${NC}"
    local failed_starts=()
    
    for service in "${STARTUP_ORDER[@]}"; do
        if ! start_service "$service"; then
            failed_starts+=("$service")
            log_recovery "ERROR" "Failed to start $service during full restart"
        fi
    done
    
    if [ ${#failed_starts[@]} -eq 0 ]; then
        log_recovery "SUCCESS" "Full system restart completed successfully"
        return 0
    else
        log_recovery "ERROR" "Full system restart completed with failures: ${failed_starts[*]}"
        return 1
    fi
}

# Monitor mode - continuous health checking
monitor_mode() {
    local check_interval=${1:-60}
    
    log_recovery "INFO" "Starting monitor mode (check interval: ${check_interval}s)"
    echo -e "${CYAN}Press Ctrl+C to stop monitoring${NC}\n"
    
    while true; do
        local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
        echo -e "\n${BLUE}[${timestamp}] Running health check...${NC}"
        
        local unhealthy_count=0
        for service in "${STARTUP_ORDER[@]}"; do
            local health=$(get_service_health "$service")
            if [ "$health" != "healthy" ]; then
                echo -e "${YELLOW}⚠ $service: $health${NC}"
                ((unhealthy_count++))
                
                # Auto-recover if enabled
                if [ "$AUTO_RECOVER" = true ]; then
                    log_recovery "RECOVER" "Auto-recovering $service"
                    recover_service "$service"
                fi
            fi
        done
        
        if [ $unhealthy_count -eq 0 ]; then
            echo -e "${GREEN}✓ All services healthy${NC}"
        else
            echo -e "${YELLOW}Found $unhealthy_count unhealthy services${NC}"
        fi
        
        sleep $check_interval
    done
}

# Main function
main() {
    local mode="check"
    local services=()
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --recover)
                mode="recover"
                shift
                ;;
            --restart)
                mode="restart"
                shift
                ;;
            --monitor)
                mode="monitor"
                shift
                ;;
            --auto-recover)
                AUTO_RECOVER=true
                shift
                ;;
            --service)
                services+=("$2")
                shift 2
                ;;
            --interval)
                MONITOR_INTERVAL=$2
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --recover         Recover unhealthy services"
                echo "  --restart         Full system restart"
                echo "  --monitor         Continuous monitoring mode"
                echo "  --auto-recover    Auto-recover in monitor mode"
                echo "  --service NAME    Specific service to recover"
                echo "  --interval SECS   Monitor check interval (default: 60)"
                echo "  --help           Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0 --recover                    # Recover all unhealthy services"
                echo "  $0 --recover --service api      # Recover specific service"
                echo "  $0 --restart                    # Full system restart"
                echo "  $0 --monitor --auto-recover     # Monitor with auto-recovery"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Initialize
    initialize_recovery
    
    # Execute based on mode
    case $mode in
        check)
            echo -e "${BLUE}=== Service Health Check ===${NC}"
            for service in "${STARTUP_ORDER[@]}"; do
                local health=$(get_service_health "$service")
                case $health in
                    healthy)
                        echo -e "${GREEN}✓${NC} $service: $health"
                        ;;
                    not_found|stopped)
                        echo -e "${RED}✗${NC} $service: $health"
                        ;;
                    *)
                        echo -e "${YELLOW}⚠${NC} $service: $health"
                        ;;
                esac
            done
            ;;
        recover)
            echo -e "${BLUE}=== Service Recovery Mode ===${NC}"
            recover_all_services "${services[@]}"
            ;;
        restart)
            echo -e "${BLUE}=== Full System Restart ===${NC}"
            full_system_restart
            ;;
        monitor)
            monitor_mode "${MONITOR_INTERVAL:-60}"
            ;;
    esac
    
    echo -e "\n${BLUE}Recovery logs: $RECOVERY_LOG_DIR/$RECOVERY_ID/${NC}"
}

# Trap Ctrl+C for clean exit
trap 'echo -e "\n${CYAN}Monitoring stopped${NC}"; exit 0' INT

# Run main
main "$@"