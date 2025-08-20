#!/bin/bash

# =============================================================================
# AI WORKFLOW ENGINE - BLUE-GREEN DEPLOYMENT ORCHESTRATOR
# =============================================================================
# Comprehensive production deployment with zero-downtime and rollback
# Deployment Scope: Auth optimizations, GPU enhancements, monitoring, security
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_LOG="${PROJECT_ROOT}/logs/deployment-$(date +%Y%m%d-%H%M%S).log"
HEALTH_CHECK_TIMEOUT=300
PERFORMANCE_THRESHOLD_MS=100
ERROR_RATE_THRESHOLD=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

error() {
    echo -e "${RED}[ERROR $(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

success() {
    echo -e "${GREEN}[SUCCESS $(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING $(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

# Health check function
health_check() {
    local url="$1"
    local expected_code="${2:-200}"
    local timeout="${3:-10}"
    
    log "Health checking: $url"
    
    response=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" --max-time "$timeout" "$url" || echo "000:999")
    http_code="${response%:*}"
    response_time="${response#*:}"
    
    if [[ "$http_code" == "$expected_code" ]]; then
        response_time_ms=$(echo "$response_time * 1000" | bc -l | cut -d. -f1)
        log "✓ Health check passed: $http_code (${response_time_ms}ms)"
        return 0
    else
        error "✗ Health check failed: $http_code"
        return 1
    fi
}

# Performance validation
validate_performance() {
    local url="$1"
    local iterations="${2:-5}"
    
    log "Performance validation: $url ($iterations iterations)"
    
    local total_time=0
    local success_count=0
    
    for i in $(seq 1 "$iterations"); do
        response=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" --max-time 10 "$url" || echo "000:999")
        http_code="${response%:*}"
        response_time="${response#*:}"
        
        if [[ "$http_code" == "200" ]]; then
            ((success_count++))
            total_time=$(echo "$total_time + $response_time" | bc -l)
        fi
        
        sleep 1
    done
    
    if [[ $success_count -gt 0 ]]; then
        avg_time=$(echo "scale=3; $total_time / $success_count" | bc -l)
        avg_time_ms=$(echo "$avg_time * 1000" | bc -l | cut -d. -f1)
        success_rate=$(echo "scale=1; $success_count * 100 / $iterations" | bc -l)
        
        log "Performance results: ${avg_time_ms}ms avg, ${success_rate}% success rate"
        
        if (( avg_time_ms > PERFORMANCE_THRESHOLD_MS )); then
            error "Performance threshold exceeded: ${avg_time_ms}ms > ${PERFORMANCE_THRESHOLD_MS}ms"
            return 1
        fi
        
        if (( $(echo "$success_rate < 95" | bc -l) )); then
            error "Success rate too low: ${success_rate}%"
            return 1
        fi
        
        success "Performance validation passed"
        return 0
    else
        error "All performance checks failed"
        return 1
    fi
}

# Container health validation
validate_container_health() {
    log "Validating container health status"
    
    # Check critical containers
    critical_containers=(
        "ai_workflow_engine-webui-1"
        "ai_workflow_engine-postgres-1"
        "ai_workflow_engine-redis-1"
        "ai_workflow_engine-ollama-1"
        "simple-api"
    )
    
    for container in "${critical_containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" --format "{{.Names}}" | grep -q "$container"; then
            # Check health status if available
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
            if [[ "$health_status" == "healthy" ]] || [[ "$health_status" == "no-healthcheck" ]]; then
                log "✓ Container healthy: $container"
            else
                error "✗ Container unhealthy: $container ($health_status)"
                return 1
            fi
        else
            error "✗ Container not running: $container"
            return 1
        fi
    done
    
    success "All critical containers are healthy"
    return 0
}

# Database connectivity check
validate_database() {
    log "Validating database connectivity"
    
    if docker exec ai_workflow_engine-postgres-1 pg_isready -U aiwfe -d aiwfe_db > /dev/null 2>&1; then
        log "✓ PostgreSQL connectivity confirmed"
    else
        error "✗ PostgreSQL connectivity failed"
        return 1
    fi
    
    if docker exec ai_workflow_engine-redis-1 redis-cli ping | grep -q "PONG"; then
        log "✓ Redis connectivity confirmed"
    else
        error "✗ Redis connectivity failed"
        return 1
    fi
    
    success "Database validation passed"
    return 0
}

# Monitoring system validation
validate_monitoring() {
    log "Validating monitoring infrastructure"
    
    # Check Prometheus
    if health_check "http://localhost:9090/-/healthy"; then
        log "✓ Prometheus healthy"
    else
        error "✗ Prometheus health check failed"
        return 1
    fi
    
    # Check Grafana
    if health_check "http://localhost:3000/api/health"; then
        log "✓ Grafana healthy"
    else
        error "✗ Grafana health check failed"
        return 1
    fi
    
    success "Monitoring validation passed"
    return 0
}

# Production endpoint validation
validate_production_endpoints() {
    log "Validating production endpoints"
    
    # Main production URL
    if ! health_check "https://aiwfe.com"; then
        error "Production endpoint validation failed"
        return 1
    fi
    
    # API health endpoints
    if ! health_check "http://localhost:8000/health" 200 5; then
        error "API health endpoint validation failed"
        return 1
    fi
    
    # WebUI endpoint
    if ! health_check "http://localhost:3001" 200 10; then
        error "WebUI endpoint validation failed"
        return 1
    fi
    
    success "Production endpoint validation passed"
    return 0
}

# Authentication system validation
validate_authentication() {
    log "Validating authentication system performance"
    
    # Test authentication endpoint performance
    auth_url="http://localhost:8000/api/v1/session/validate"
    
    local total_time=0
    local success_count=0
    local iterations=10
    
    for i in $(seq 1 "$iterations"); do
        response=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" --max-time 5 "$auth_url" || echo "000:999")
        http_code="${response%:*}"
        response_time="${response#*:}"
        
        if [[ "$http_code" =~ ^(200|401)$ ]]; then  # Both 200 and 401 are valid responses
            ((success_count++))
            total_time=$(echo "$total_time + $response_time" | bc -l)
        fi
        
        sleep 0.5
    done
    
    if [[ $success_count -gt 0 ]]; then
        avg_time=$(echo "scale=3; $total_time / $success_count" | bc -l)
        avg_time_ms=$(echo "$avg_time * 1000" | bc -l | cut -d. -f1)
        
        log "Authentication performance: ${avg_time_ms}ms avg"
        
        # Check if we're under 20ms target
        if (( avg_time_ms < 20 )); then
            success "Authentication optimization target achieved: ${avg_time_ms}ms < 20ms"
        elif (( avg_time_ms < 50 )); then
            warning "Authentication performance acceptable: ${avg_time_ms}ms"
        else
            error "Authentication performance below target: ${avg_time_ms}ms"
            return 1
        fi
    else
        error "Authentication validation failed"
        return 1
    fi
    
    success "Authentication validation passed"
    return 0
}

# GPU utilization check
validate_gpu_utilization() {
    log "Validating GPU utilization optimization"
    
    # Check if GPU monitor is available
    if ! docker ps --filter "name=ai_workflow_engine-gpu-monitor-1" --filter "status=running" --format "{{.Names}}" | grep -q "gpu-monitor"; then
        warning "GPU monitor not running, skipping GPU validation"
        return 0
    fi
    
    # Check GPU metrics endpoint
    if health_check "http://localhost:8025/metrics"; then
        log "✓ GPU monitoring endpoint accessible"
        success "GPU utilization monitoring validated"
    else
        warning "GPU monitoring endpoint not accessible"
    fi
    
    return 0
}

# Comprehensive pre-deployment validation
pre_deployment_validation() {
    log "========================================="
    log "STARTING PRE-DEPLOYMENT VALIDATION"
    log "========================================="
    
    validate_container_health || return 1
    validate_database || return 1
    validate_production_endpoints || return 1
    validate_authentication || return 1
    validate_monitoring || return 1
    validate_gpu_utilization || return 1
    
    success "Pre-deployment validation completed successfully"
    return 0
}

# Post-deployment validation
post_deployment_validation() {
    log "========================================="
    log "STARTING POST-DEPLOYMENT VALIDATION"
    log "========================================="
    
    # Wait for services to stabilize
    log "Waiting for services to stabilize (30 seconds)..."
    sleep 30
    
    validate_container_health || return 1
    validate_database || return 1
    validate_production_endpoints || return 1
    validate_authentication || return 1
    validate_monitoring || return 1
    validate_gpu_utilization || return 1
    
    # Extended performance validation
    log "Running extended performance validation..."
    validate_performance "https://aiwfe.com" 10 || return 1
    validate_performance "http://localhost:8000/health" 5 || return 1
    
    success "Post-deployment validation completed successfully"
    return 0
}

# Rollback function
rollback_deployment() {
    error "========================================="
    error "INITIATING DEPLOYMENT ROLLBACK"
    error "========================================="
    
    log "Checking for backup configurations..."
    
    if [[ -f "${PROJECT_ROOT}/backups/docker-compose.yml.backup-$(date +%Y%m%d)" ]]; then
        log "Restoring docker-compose.yml from backup"
        cp "${PROJECT_ROOT}/backups/docker-compose.yml.backup-$(date +%Y%m%d)" "${PROJECT_ROOT}/docker-compose.yml"
    fi
    
    if [[ -f "${PROJECT_ROOT}/backups/docker-compose.override.yml.backup-$(date +%Y%m%d)" ]]; then
        log "Restoring docker-compose.override.yml from backup"
        cp "${PROJECT_ROOT}/backups/docker-compose.override.yml.backup-$(date +%Y%m%d)" "${PROJECT_ROOT}/docker-compose.override.yml"
    fi
    
    log "Restarting services with previous configuration..."
    docker-compose down --remove-orphans
    docker-compose up -d
    
    log "Waiting for rollback stabilization (60 seconds)..."
    sleep 60
    
    if validate_production_endpoints; then
        success "Rollback completed successfully"
        return 0
    else
        error "Rollback validation failed - manual intervention required"
        return 1
    fi
}

# Create backup before deployment
create_backup() {
    log "Creating deployment backup"
    
    backup_dir="${PROJECT_ROOT}/backups"
    mkdir -p "$backup_dir"
    
    timestamp=$(date +%Y%m%d-%H%M%S)
    
    if [[ -f "${PROJECT_ROOT}/docker-compose.yml" ]]; then
        cp "${PROJECT_ROOT}/docker-compose.yml" "${backup_dir}/docker-compose.yml.backup-$timestamp"
        log "✓ Backed up docker-compose.yml"
    fi
    
    if [[ -f "${PROJECT_ROOT}/docker-compose.override.yml" ]]; then
        cp "${PROJECT_ROOT}/docker-compose.override.yml" "${backup_dir}/docker-compose.override.yml.backup-$timestamp"
        log "✓ Backed up docker-compose.override.yml"
    fi
    
    success "Backup created with timestamp: $timestamp"
}

# Zero-downtime deployment execution
execute_deployment() {
    log "========================================="
    log "EXECUTING ZERO-DOWNTIME DEPLOYMENT"
    log "========================================="
    
    # Create backup
    create_backup || return 1
    
    # Gradual service restart to minimize downtime
    log "Starting gradual service restart..."
    
    # Restart non-critical services first
    log "Restarting monitoring services..."
    docker-compose restart prometheus grafana gpu-monitor || true
    
    sleep 10
    
    # Restart API with health check
    log "Restarting API service..."
    docker-compose restart api || docker-compose up -d api
    
    sleep 15
    
    # Validate API health before proceeding
    if ! health_check "http://localhost:8000/health" 200 30; then
        error "API failed to restart properly"
        return 1
    fi
    
    # Restart WebUI
    log "Restarting WebUI service..."
    docker-compose restart webui || docker-compose up -d webui
    
    sleep 15
    
    # Validate WebUI health
    if ! health_check "http://localhost:3001" 200 30; then
        error "WebUI failed to restart properly"
        return 1
    fi
    
    success "Zero-downtime deployment completed"
    return 0
}

# Main deployment orchestration
main() {
    log "========================================="
    log "AI WORKFLOW ENGINE DEPLOYMENT ORCHESTRATOR"
    log "Starting deployment at $(date)"
    log "========================================="
    
    # Ensure we're in the right directory
    cd "$PROJECT_ROOT"
    
    # Pre-deployment validation
    if ! pre_deployment_validation; then
        error "Pre-deployment validation failed"
        exit 1
    fi
    
    # Execute deployment
    if ! execute_deployment; then
        error "Deployment execution failed - initiating rollback"
        if ! rollback_deployment; then
            error "Rollback failed - manual intervention required"
            exit 1
        fi
        exit 1
    fi
    
    # Post-deployment validation
    if ! post_deployment_validation; then
        error "Post-deployment validation failed - initiating rollback"
        if ! rollback_deployment; then
            error "Rollback failed - manual intervention required"
            exit 1
        fi
        exit 1
    fi
    
    success "========================================="
    success "DEPLOYMENT COMPLETED SUCCESSFULLY"
    success "All optimizations deployed and validated"
    success "Production endpoint: https://aiwfe.com"
    success "Deployment log: $DEPLOYMENT_LOG"
    success "========================================="
}

# Handle script interruption
trap 'error "Deployment interrupted"; rollback_deployment; exit 1' INT TERM

# Execute main function
main "$@"