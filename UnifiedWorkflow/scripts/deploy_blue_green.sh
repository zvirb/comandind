#!/bin/bash
# scripts/deploy_blue_green.sh
# Advanced Blue-Green Deployment Script for AI Workflow Engine
# Implements zero-downtime deployment with automated health validation and rollback

set -e
source "$(dirname "$0")/_common_functions.sh"

# Configuration
BLUE_ENV="blue"
GREEN_ENV="green"
HEALTH_CHECK_TIMEOUT=300
TRAFFIC_SHIFT_DELAY=30
ROLLBACK_THRESHOLD=95  # Health check success rate threshold

# Global variables
CURRENT_ENV=""
TARGET_ENV=""
SOURCE_ENV=""
DEPLOYMENT_ID=""
ROLLBACK_TRIGGERED=false

# Initialize deployment
initialize_deployment() {
    DEPLOYMENT_ID=$(date +"%Y%m%d_%H%M%S")
    log_info "🚀 Starting Blue-Green deployment (ID: $DEPLOYMENT_ID)"
    
    # Determine current active environment
    CURRENT_ENV=$(get_active_environment)
    TARGET_ENV=$([ "$CURRENT_ENV" = "$BLUE_ENV" ] && echo "$GREEN_ENV" || echo "$BLUE_ENV")
    SOURCE_ENV=$CURRENT_ENV
    
    log_info "📊 Current active environment: $CURRENT_ENV"
    log_info "🎯 Target deployment environment: $TARGET_ENV"
    
    # Create deployment log directory
    mkdir -p "logs/deployments/$DEPLOYMENT_ID"
    
    # Log deployment metadata
    cat > "logs/deployments/$DEPLOYMENT_ID/metadata.json" << EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "timestamp": "$(date -Iseconds)",
    "source_environment": "$SOURCE_ENV",
    "target_environment": "$TARGET_ENV",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF
}

# Get the currently active environment
get_active_environment() {
    # Check which environment is receiving traffic via Caddy configuration
    local active_env="blue"  # Default to blue
    
    if [ -f "config/caddy/active_environment" ]; then
        active_env=$(cat config/caddy/active_environment)
    fi
    
    echo "$active_env"
}

# Validate environment readiness
validate_environment_readiness() {
    local env=$1
    log_info "🔍 Validating $env environment readiness..."
    
    # Check if target environment exists
    if ! docker compose -f "docker-compose.$env.yml" config &>/dev/null; then
        log_error "❌ $env environment configuration not found"
        return 1
    fi
    
    # Check resource availability
    validate_system_resources
    
    # Validate secrets and certificates
    validate_secrets_and_certificates
    
    log_success "✅ $env environment is ready for deployment"
}

# Validate system resources
validate_system_resources() {
    local min_memory_gb=8
    local min_disk_gb=20
    
    # Check available memory
    local available_memory_gb=$(free -g | awk 'NR==2{printf "%.1f", $7}')
    if (( $(echo "$available_memory_gb < $min_memory_gb" | bc -l) )); then
        log_error "❌ Insufficient memory: ${available_memory_gb}GB available, ${min_memory_gb}GB required"
        return 1
    fi
    
    # Check available disk space
    local available_disk_gb=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if (( available_disk_gb < min_disk_gb )); then
        log_error "❌ Insufficient disk space: ${available_disk_gb}GB available, ${min_disk_gb}GB required"
        return 1
    fi
    
    log_info "✅ System resources validated (Memory: ${available_memory_gb}GB, Disk: ${available_disk_gb}GB)"
}

# Validate secrets and certificates
validate_secrets_and_certificates() {
    log_info "🔐 Validating secrets and certificates..."
    
    # Check critical secrets exist
    local critical_secrets=("postgres_password.txt" "jwt_secret_key.txt" "api_key.txt")
    for secret in "${critical_secrets[@]}"; do
        if [ ! -f "secrets/$secret" ]; then
            log_error "❌ Critical secret missing: $secret"
            return 1
        fi
    done
    
    # Check certificate expiration
    if [ -f "secrets/ca_cert.pem" ]; then
        local cert_expiry=$(openssl x509 -in secrets/ca_cert.pem -noout -enddate | cut -d= -f2)
        local cert_expiry_epoch=$(date -d "$cert_expiry" +%s)
        local current_epoch=$(date +%s)
        local days_until_expiry=$(( (cert_expiry_epoch - current_epoch) / 86400 ))
        
        if [ $days_until_expiry -lt 30 ]; then
            log_warn "⚠️  CA certificate expires in $days_until_expiry days"
        fi
    fi
    
    log_success "✅ Secrets and certificates validated"
}

# Deploy to target environment
deploy_environment() {
    local env=$1
    log_info "🚢 Deploying to $env environment..."
    
    # Export environment-specific variables
    export ENVIRONMENT=$env
    export COMPOSE_PROJECT_NAME="ai_workflow_engine_$env"
    
    # Stop existing environment services (if running)
    log_info "🛑 Stopping existing $env environment services..."
    docker compose -f "docker-compose.$env.yml" down --remove-orphans || true
    
    # Build images with environment-specific tags
    log_info "🔨 Building images for $env environment..."
    docker compose -f "docker-compose.$env.yml" build --pull --no-cache \
        --build-arg DEPLOYMENT_ID=$DEPLOYMENT_ID \
        --build-arg ENVIRONMENT=$env
    
    # Start services in dependency order
    log_info "🚀 Starting $env environment services..."
    
    # Phase 1: Infrastructure services
    docker compose -f "docker-compose.$env.yml" up -d \
        postgres redis qdrant
    
    # Wait for infrastructure readiness
    wait_for_service_health "$env" "postgres" 60
    wait_for_service_health "$env" "redis" 30
    wait_for_service_health "$env" "qdrant" 60
    
    # Phase 2: Application services
    docker compose -f "docker-compose.$env.yml" up -d \
        api worker
    
    wait_for_service_health "$env" "api" 120
    wait_for_service_health "$env" "worker" 90
    
    # Phase 3: Frontend and proxy services
    docker compose -f "docker-compose.$env.yml" up -d \
        webui caddy_reverse_proxy
    
    wait_for_service_health "$env" "webui" 60
    
    # Phase 4: Monitoring services
    docker compose -f "docker-compose.$env.yml" up -d \
        prometheus grafana alertmanager cadvisor \
        redis_exporter postgres_exporter pgbouncer_exporter
    
    log_success "✅ $env environment deployed successfully"
}

# Wait for service health
wait_for_service_health() {
    local env=$1
    local service=$2
    local timeout=$3
    local start_time=$(date +%s)
    
    log_info "⏳ Waiting for $service health in $env environment (timeout: ${timeout}s)..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "❌ Health check timeout for $service in $env environment"
            return 1
        fi
        
        # Check container health
        local health_status=$(docker compose -f "docker-compose.$env.yml" ps -q $service | xargs -r docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        
        if [ "$health_status" = "healthy" ] || [ "$health_status" = "unknown" ]; then
            # If no health check defined or healthy, check if container is running
            local container_status=$(docker compose -f "docker-compose.$env.yml" ps -a $service --format "{{.State}}" 2>/dev/null || echo "unknown")
            if [ "$container_status" = "running" ]; then
                log_success "✅ $service is healthy in $env environment"
                return 0
            fi
        fi
        
        sleep 5
    done
}

# Validate deployment health
validate_deployment_health() {
    local env=$1
    log_info "🏥 Validating $env environment health..."
    
    local health_checks=0
    local passed_checks=0
    
    # API health check
    if validate_api_health "$env"; then
        ((passed_checks++))
    fi
    ((health_checks++))
    
    # Database connectivity check
    if validate_database_health "$env"; then
        ((passed_checks++))
    fi
    ((health_checks++))
    
    # Redis connectivity check
    if validate_redis_health "$env"; then
        ((passed_checks++))
    fi
    ((health_checks++))
    
    # WebUI accessibility check
    if validate_webui_health "$env"; then
        ((passed_checks++))
    fi
    ((health_checks++))
    
    # Calculate success rate
    local success_rate=$((passed_checks * 100 / health_checks))
    
    log_info "📊 Health validation: $passed_checks/$health_checks checks passed ($success_rate%)"
    
    if [ $success_rate -lt $ROLLBACK_THRESHOLD ]; then
        log_error "❌ Health validation failed: $success_rate% < $ROLLBACK_THRESHOLD%"
        return 1
    fi
    
    log_success "✅ $env environment health validation passed"
    
    # Log health status
    cat > "logs/deployments/$DEPLOYMENT_ID/health_validation.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "environment": "$env",
    "total_checks": $health_checks,
    "passed_checks": $passed_checks,
    "success_rate": $success_rate,
    "threshold": $ROLLBACK_THRESHOLD,
    "status": "passed"
}
EOF
}

# Validate API health
validate_api_health() {
    local env=$1
    local api_port=$(get_service_port "$env" "api")
    
    log_info "🔍 Validating API health on port $api_port..."
    
    # Check API health endpoint
    if curl -f -s --max-time 10 "http://localhost:$api_port/health" > /dev/null; then
        log_success "✅ API health check passed"
        return 0
    else
        log_error "❌ API health check failed"
        return 1
    fi
}

# Validate database health
validate_database_health() {
    local env=$1
    
    log_info "🔍 Validating database connectivity..."
    
    # Test database connection
    if docker compose -f "docker-compose.$env.yml" exec -T postgres pg_isready -U app_user -d ai_workflow_db > /dev/null 2>&1; then
        log_success "✅ Database health check passed"
        return 0
    else
        log_error "❌ Database health check failed"
        return 1
    fi
}

# Validate Redis health
validate_redis_health() {
    local env=$1
    
    log_info "🔍 Validating Redis connectivity..."
    
    # Test Redis connection
    if docker compose -f "docker-compose.$env.yml" exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "✅ Redis health check passed"
        return 0
    else
        log_error "❌ Redis health check failed"
        return 1
    fi
}

# Validate WebUI health
validate_webui_health() {
    local env=$1
    local webui_port=$(get_service_port "$env" "webui")
    
    log_info "🔍 Validating WebUI accessibility on port $webui_port..."
    
    # Check WebUI accessibility
    if curl -f -s --max-time 10 "http://localhost:$webui_port" > /dev/null; then
        log_success "✅ WebUI health check passed"
        return 0
    else
        log_error "❌ WebUI health check failed"
        return 1
    fi
}

# Get service port for environment
get_service_port() {
    local env=$1
    local service=$2
    
    # Return environment-specific port or default
    case "$env:$service" in
        "blue:api") echo "8000" ;;
        "green:api") echo "8001" ;;
        "blue:webui") echo "3000" ;;
        "green:webui") echo "3001" ;;
        *) echo "8000" ;;
    esac
}

# Progressive traffic switching
shift_traffic_progressive() {
    local source_env=$1
    local target_env=$2
    
    log_info "🔄 Starting progressive traffic shift: $source_env → $target_env"
    
    # Traffic shift phases: 10% → 50% → 100%
    local phases=(10 50 100)
    
    for phase in "${phases[@]}"; do
        log_info "📊 Shifting ${phase}% traffic to $target_env..."
        
        # Update load balancer configuration
        update_traffic_split "$source_env" "$target_env" "$phase"
        
        # Wait for traffic shift to stabilize
        sleep $TRAFFIC_SHIFT_DELAY
        
        # Monitor metrics during traffic shift
        if ! monitor_traffic_shift_health "$target_env" "$phase"; then
            log_error "❌ Health degradation detected during ${phase}% traffic shift"
            trigger_rollback "$source_env" "$target_env"
            return 1
        fi
        
        log_success "✅ ${phase}% traffic shift completed successfully"
    done
    
    # Update active environment marker
    echo "$target_env" > "config/caddy/active_environment"
    
    log_success "✅ Traffic shift completed: $target_env is now active"
}

# Update traffic split configuration
update_traffic_split() {
    local source_env=$1
    local target_env=$2
    local target_percentage=$3
    local source_percentage=$((100 - target_percentage))
    
    # Generate Caddy configuration for traffic splitting
    cat > "config/caddy/traffic_split.conf" << EOF
# Traffic split configuration - Generated by blue-green deployment
# Source: $source_env ($source_percentage%) | Target: $target_env ($target_percentage%)

(traffic_split) {
    @split_to_target expr("randInt(1, 101) <= $target_percentage")
    
    handle @split_to_target {
        reverse_proxy {
            to webui_$target_env:3000
            health_uri /health
            health_interval 10s
            health_timeout 5s
        }
    }
    
    handle {
        reverse_proxy {
            to webui_$source_env:3000
            health_uri /health
            health_interval 10s
            health_timeout 5s
        }
    }
}
EOF
    
    # Reload Caddy configuration
    docker compose exec caddy_reverse_proxy caddy reload --config /etc/caddy/Caddyfile
}

# Monitor traffic shift health
monitor_traffic_shift_health() {
    local target_env=$1
    local traffic_percentage=$2
    local monitoring_duration=60  # Monitor for 60 seconds
    
    log_info "📈 Monitoring health during ${traffic_percentage}% traffic to $target_env..."
    
    local start_time=$(date +%s)
    local error_count=0
    local max_errors=5
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $monitoring_duration ]; then
            break
        fi
        
        # Check API response times
        local response_time=$(curl -w "%{time_total}" -s -o /dev/null --max-time 5 "http://localhost:$(get_service_port $target_env api)/health" || echo "999")
        
        # Consider response time > 2 seconds as degradation
        if (( $(echo "$response_time > 2.0" | bc -l) )); then
            ((error_count++))
            log_warn "⚠️  Elevated response time: ${response_time}s (errors: $error_count/$max_errors)"
            
            if [ $error_count -ge $max_errors ]; then
                log_error "❌ Health degradation threshold exceeded"
                return 1
            fi
        fi
        
        sleep 10
    done
    
    log_success "✅ Health monitoring passed for ${traffic_percentage}% traffic shift"
    return 0
}

# Trigger automatic rollback
trigger_rollback() {
    local source_env=$1
    local target_env=$2
    
    if [ "$ROLLBACK_TRIGGERED" = true ]; then
        log_error "❌ Rollback already in progress, preventing cascade"
        return 1
    fi
    
    ROLLBACK_TRIGGERED=true
    log_error "🚨 TRIGGERING AUTOMATIC ROLLBACK: $target_env → $source_env"
    
    # Immediately shift traffic back to source environment
    log_info "🔄 Emergency traffic rollback to $source_env..."
    update_traffic_split "$target_env" "$source_env" 0
    
    # Log rollback event
    cat > "logs/deployments/$DEPLOYMENT_ID/rollback.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "deployment_id": "$DEPLOYMENT_ID",
    "reason": "health_degradation",
    "source_environment": "$source_env",
    "target_environment": "$target_env",
    "rollback_triggered": true
}
EOF
    
    # Send alert notification
    send_rollback_alert "$source_env" "$target_env"
    
    log_error "❌ Deployment failed and rolled back to $source_env"
    exit 1
}

# Send rollback alert
send_rollback_alert() {
    local source_env=$1
    local target_env=$2
    
    # Send alert through multiple channels
    local alert_message="🚨 DEPLOYMENT ROLLBACK: $target_env deployment failed, rolled back to $source_env (ID: $DEPLOYMENT_ID)"
    
    # Log alert
    log_error "$alert_message"
    
    # Send to alertmanager if available
    if command -v curl >/dev/null 2>&1; then
        curl -s -X POST http://localhost:9093/api/v1/alerts -H "Content-Type: application/json" -d "[{
            \"labels\": {
                \"alertname\": \"DeploymentRollback\",
                \"severity\": \"critical\",
                \"deployment_id\": \"$DEPLOYMENT_ID\",
                \"environment\": \"$target_env\"
            },
            \"annotations\": {
                \"summary\": \"$alert_message\"
            }
        }]" || true
    fi
}

# Cleanup old environments
cleanup_old_environment() {
    local env=$1
    
    log_info "🧹 Cleaning up old $env environment..."
    
    # Stop and remove containers
    docker compose -f "docker-compose.$env.yml" down --remove-orphans
    
    # Remove unused images (keep recent ones)
    docker images --filter "label=environment=$env" --filter "dangling=true" -q | xargs -r docker rmi || true
    
    log_success "✅ Old $env environment cleaned up"
}

# Main deployment function
main() {
    local skip_validation=false
    local skip_cleanup=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-validation)
                skip_validation=true
                shift
                ;;
            --skip-cleanup)
                skip_cleanup=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Initialize deployment
    initialize_deployment
    
    # Validate environment readiness
    if [ "$skip_validation" != true ]; then
        validate_environment_readiness "$TARGET_ENV"
    fi
    
    # Deploy to target environment
    deploy_environment "$TARGET_ENV"
    
    # Validate deployment health
    validate_deployment_health "$TARGET_ENV"
    
    # Progressive traffic switching
    shift_traffic_progressive "$SOURCE_ENV" "$TARGET_ENV"
    
    # Cleanup old environment
    if [ "$skip_cleanup" != true ]; then
        cleanup_old_environment "$SOURCE_ENV"
    fi
    
    # Log successful deployment
    cat > "logs/deployments/$DEPLOYMENT_ID/success.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "deployment_id": "$DEPLOYMENT_ID",
    "source_environment": "$SOURCE_ENV",
    "target_environment": "$TARGET_ENV",
    "status": "success",
    "duration": $(( $(date +%s) - $(date -d "$(jq -r .timestamp logs/deployments/$DEPLOYMENT_ID/metadata.json)" +%s) ))
}
EOF
    
    log_success "🎉 Blue-Green deployment completed successfully!"
    log_info "📊 Deployment ID: $DEPLOYMENT_ID"
    log_info "🌍 Active environment: $TARGET_ENV"
    log_info "📁 Deployment logs: logs/deployments/$DEPLOYMENT_ID/"
}

# Show usage information
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Blue-Green Deployment Script for AI Workflow Engine

OPTIONS:
    --skip-validation    Skip environment readiness validation
    --skip-cleanup      Skip cleanup of old environment
    --help              Show this help message

EXAMPLES:
    $0                          # Standard blue-green deployment
    $0 --skip-validation        # Deploy without validation (faster, riskier)
    $0 --skip-cleanup          # Deploy but keep old environment running

ENVIRONMENT VARIABLES:
    HEALTH_CHECK_TIMEOUT       # Health check timeout in seconds (default: 300)
    TRAFFIC_SHIFT_DELAY        # Delay between traffic shifts in seconds (default: 30)
    ROLLBACK_THRESHOLD         # Health check success rate threshold (default: 95)

EOF
}

# Trap errors and cleanup
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_number=$2
    
    log_error "❌ Deployment failed on line $line_number (exit code: $exit_code)"
    
    if [ -n "$TARGET_ENV" ] && [ -n "$SOURCE_ENV" ] && [ "$ROLLBACK_TRIGGERED" != true ]; then
        log_error "🔄 Attempting automatic rollback..."
        trigger_rollback "$SOURCE_ENV" "$TARGET_ENV"
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi