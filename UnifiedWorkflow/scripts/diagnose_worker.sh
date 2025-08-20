#!/bin/bash
# scripts/diagnose_worker.sh
# Comprehensive diagnostic script for worker container restart issues

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🔍 Worker Container Diagnostic Tool"
log_info "=================================="

# Function to check container status
check_container_status() {
    log_info "📊 Container Status Check"
    echo "=========================="
    
    # Check if worker container exists and its status
    if docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "Worker container found:"
        docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "ai_workflow_engine-worker-1"
        
        # Get restart count
        RESTART_COUNT=$(docker inspect ai_workflow_engine-worker-1 --format='{{.RestartCount}}' 2>/dev/null || echo "N/A")
        log_info "Restart count: $RESTART_COUNT"
        
        # Check exit code of last run
        EXIT_CODE=$(docker inspect ai_workflow_engine-worker-1 --format='{{.State.ExitCode}}' 2>/dev/null || echo "N/A")
        log_info "Last exit code: $EXIT_CODE"
        
        # Check if it's currently running
        if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
            log_success "✅ Worker container is currently running"
        else
            log_warn "⚠️  Worker container is not running"
        fi
    else
        log_error "❌ Worker container not found"
        return 1
    fi
    echo ""
}

# Function to check recent logs
check_logs() {
    log_info "📋 Recent Worker Logs (last 50 lines)"
    echo "====================================="
    
    if docker logs ai_workflow_engine-worker-1 --tail 50 2>/dev/null; then
        echo ""
    else
        log_error "❌ Could not retrieve worker logs"
    fi
    echo ""
}

# Function to check resource usage
check_resources() {
    log_info "💻 Resource Usage Check"
    echo "======================"
    
    # Check system resources
    log_info "System Memory:"
    free -h
    echo ""
    
    log_info "System Disk Usage:"
    df -h / /tmp 2>/dev/null || df -h /
    echo ""
    
    # Check Docker stats for worker if running
    if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "Worker Container Resources:"
        docker stats ai_workflow_engine-worker-1 --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
        echo ""
    fi
}

# Function to check dependencies
check_dependencies() {
    log_info "🔗 Dependency Health Check"
    echo "=========================="
    
    # Check dependent services
    DEPENDENCIES=("postgres" "redis" "qdrant" "ollama")
    
    for dep in "${DEPENDENCIES[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-${dep}-1"; then
            # Check if service is healthy
            HEALTH=$(docker inspect ai_workflow_engine-${dep}-1 --format='{{.State.Health.Status}}' 2>/dev/null || echo "no healthcheck")
            if [ "$HEALTH" = "healthy" ]; then
                log_success "✅ $dep: running and healthy"
            elif [ "$HEALTH" = "no healthcheck" ]; then
                log_info "ℹ️  $dep: running (no healthcheck)"
            else
                log_warn "⚠️  $dep: running but $HEALTH"
            fi
        else
            log_error "❌ $dep: not running"
        fi
    done
    echo ""
}

# Function to check environment and configuration
check_environment() {
    log_info "🌍 Environment Configuration Check"
    echo "=================================="
    
    # Check if environment files exist
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_success "✅ .env file exists"
    else
        log_error "❌ .env file missing"
    fi
    
    if [ -f "$PROJECT_ROOT/local.env" ]; then
        log_success "✅ local.env file exists"
    else
        log_warn "⚠️  local.env file missing (optional)"
    fi
    
    # Check secrets
    if [ -d "$PROJECT_ROOT/secrets" ] && [ "$(ls -A "$PROJECT_ROOT/secrets" 2>/dev/null)" ]; then
        log_success "✅ Secrets directory exists with files"
        SECRET_COUNT=$(ls -1 "$PROJECT_ROOT/secrets"/*.txt 2>/dev/null | wc -l)
        log_info "Secret files count: $SECRET_COUNT"
    else
        log_error "❌ Secrets directory empty or missing"
    fi
    
    # Check GPU availability if configured
    if docker compose --project-directory "$PROJECT_ROOT" config | grep -q "nvidia"; then
        log_info "GPU configuration detected, checking nvidia-smi:"
        if command -v nvidia-smi >/dev/null 2>&1; then
            nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits 2>/dev/null || log_warn "⚠️  GPU not accessible"
        else
            log_warn "⚠️  nvidia-smi not available"
        fi
    fi
    echo ""
}

# Function to check worker-specific issues
check_worker_specifics() {
    log_info "🔧 Worker-Specific Diagnostics"
    echo "=============================="
    
    # Check worker healthcheck
    if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "Testing worker healthcheck manually:"
        
        # Get the actual healthcheck command from docker-compose
        HEALTHCHECK_CMD=$(docker inspect ai_workflow_engine-worker-1 --format='{{range .Config.Healthcheck.Test}}{{.}} {{end}}' 2>/dev/null || echo "No healthcheck defined")
        log_info "Healthcheck command: $HEALTHCHECK_CMD"
        
        # Try to run healthcheck manually
        if docker exec ai_workflow_engine-worker-1 bash -c "PYTHONPATH=/app celery -A ai_workflow_engine.worker.celery_app --broker redis://lwe-app:\$(cat /run/secrets/REDIS_PASSWORD)@redis:6379/0 inspect ping -d celery@\${HOSTNAME}" 2>/dev/null; then
            log_success "✅ Worker healthcheck passed"
        else
            log_error "❌ Worker healthcheck failed"
        fi
    else
        log_warn "⚠️  Worker not running, cannot test healthcheck"
    fi
    
    # Check if Celery can connect to Redis
    if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "Testing Redis connectivity:"
        if docker exec ai_workflow_engine-worker-1 bash -c "python -c 'import redis; r=redis.Redis(host=\"redis\", port=6379, username=\"lwe-app\", password=open(\"/run/secrets/REDIS_PASSWORD\").read().strip()); print(r.ping())'" 2>/dev/null; then
            log_success "✅ Redis connection successful"
        else
            log_error "❌ Redis connection failed"
        fi
    fi
    echo ""
}

# Function to check Docker daemon and system
check_docker_system() {
    log_info "🐳 Docker System Check"
    echo "====================="
    
    # Check Docker daemon status
    if docker info >/dev/null 2>&1; then
        log_success "✅ Docker daemon is running"
    else
        log_error "❌ Docker daemon is not accessible"
        return 1
    fi
    
    # Check Docker version
    DOCKER_VERSION=$(docker --version)
    log_info "Docker version: $DOCKER_VERSION"
    
    # Check docker-compose version
    COMPOSE_VERSION=$(docker compose version 2>/dev/null || docker-compose --version 2>/dev/null)
    log_info "Docker Compose version: $COMPOSE_VERSION"
    
    # Check Docker disk usage
    log_info "Docker disk usage:"
    docker system df
    echo ""
}

# Function to provide recommendations
provide_recommendations() {
    log_info "💡 Troubleshooting Recommendations"
    echo "=================================="
    
    # Check if worker is currently failing
    if ! docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "🔧 Worker is not running. Common solutions:"
        echo "   1. Check logs: docker logs ai_workflow_engine-worker-1"
        echo "   2. Restart worker: docker compose restart worker"
        echo "   3. Check dependencies: Ensure postgres, redis, qdrant, ollama are healthy"
        echo "   4. Check resources: Ensure sufficient memory and disk space"
        echo "   5. Check secrets: Verify all secret files exist in secrets/ directory"
        echo ""
    fi
    
    # Check restart count
    RESTART_COUNT=$(docker inspect ai_workflow_engine-worker-1 --format='{{.RestartCount}}' 2>/dev/null || echo "0")
    if [ "$RESTART_COUNT" -gt 5 ]; then
        log_warn "⚠️  High restart count ($RESTART_COUNT). This indicates a persistent issue."
        echo "   Consider:"
        echo "   - Checking for memory leaks or resource exhaustion"
        echo "   - Reviewing recent changes to worker code"
        echo "   - Examining system logs for hardware issues"
        echo "   - Checking for network connectivity issues"
        echo ""
    fi
    
    # Memory recommendations
    TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
    if [ "$TOTAL_MEM" -lt 4096 ]; then
        log_warn "⚠️  Low system memory ($TOTAL_MEM MB). Consider:"
        echo "   - Increasing server memory"
        echo "   - Monitoring memory usage during worker operation"
        echo "   - Reducing concurrent worker processes"
        echo ""
    fi
    
    log_info "📚 Additional debugging commands:"
    echo "   - View live logs: docker logs -f ai_workflow_engine-worker-1"
    echo "   - Check all service status: docker compose ps"
    echo "   - Restart all services: docker compose restart"
    echo "   - Check service dependencies: docker compose config"
    echo ""
}

# Main execution
main() {
    log_info "Starting worker container diagnostics..."
    echo ""
    
    check_docker_system
    check_container_status
    check_dependencies
    check_environment
    check_resources
    check_worker_specifics
    check_logs
    provide_recommendations
    
    log_success "🎯 Diagnostic complete!"
    log_info "If the issue persists, please share the output of this script for further analysis."
}

# Run diagnostics
main "$@"