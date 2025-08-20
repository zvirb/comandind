#!/bin/bash
# scripts/worker_universal_fix.sh
# Universal worker fix script that works on both local and server environments
# This script addresses common worker restart issues

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🔧 Universal Worker Fix"
log_info "======================"
log_info "This script works on both local and server environments"

# Function to check system resources
check_system_resources() {
    log_info "📊 Checking system resources..."
    
    # Check memory
    if command -v free >/dev/null 2>&1; then
        TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
        AVAILABLE_MEM=$(free -m | awk 'NR==2{print $7}')
        log_info "Memory: ${AVAILABLE_MEM}MB available / ${TOTAL_MEM}MB total"
        
        if [ "$AVAILABLE_MEM" -lt 1024 ]; then
            log_warn "⚠️  Low available memory ($AVAILABLE_MEM MB). This may cause worker restarts."
        fi
    fi
    
    # Check disk space
    DISK_USAGE=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
    log_info "Disk usage: ${DISK_USAGE}%"
    
    if [ "$DISK_USAGE" -gt 90 ]; then
        log_warn "⚠️  High disk usage (${DISK_USAGE}%). This may cause worker issues."
    fi
}

# Function to verify worker configuration
verify_worker_config() {
    log_info "🔍 Verifying worker configuration..."
    
    # Check if healthcheck script exists
    if [ -f "$PROJECT_ROOT/docker/worker/healthcheck.sh" ]; then
        log_success "✅ Healthcheck script exists"
    else
        log_error "❌ Healthcheck script missing"
        return 1
    fi
    
    # Check if healthcheck script is executable
    if [ -x "$PROJECT_ROOT/docker/worker/healthcheck.sh" ]; then
        log_success "✅ Healthcheck script is executable"
    else
        log_warn "⚠️  Making healthcheck script executable..."
        chmod +x "$PROJECT_ROOT/docker/worker/healthcheck.sh"
    fi
    
    # Check docker-compose configuration
    if docker compose --project-directory "$PROJECT_ROOT" config >/dev/null 2>&1; then
        log_success "✅ Docker compose configuration is valid"
    else
        log_error "❌ Docker compose configuration has errors"
        return 1
    fi
}

# Function to fix worker issues
fix_worker_issues() {
    log_info "🔧 Applying worker fixes..."
    
    # Stop worker if running
    if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "Stopping current worker..."
        docker stop ai_workflow_engine-worker-1 || true
    fi
    
    # Remove unhealthy container
    if docker ps -a --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
        log_info "Removing existing worker container..."
        docker rm ai_workflow_engine-worker-1 || true
    fi
    
    # Ensure dependencies are healthy
    log_info "Checking dependencies..."
    DEPS=("postgres" "redis" "qdrant")
    for dep in "${DEPS[@]}"; do
        if ! docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-${dep}-1"; then
            log_warn "⚠️  $dep is not running, starting..."
            docker compose --project-directory "$PROJECT_ROOT" up -d "$dep"
        fi
    done
    
    # Wait for dependencies to be healthy
    log_info "Waiting for dependencies to be healthy..."
    sleep 10
    
    # Start worker with new configuration
    log_info "Starting worker with updated configuration..."
    docker compose --project-directory "$PROJECT_ROOT" up -d worker
    
    # Monitor worker startup
    log_info "Monitoring worker startup..."
    for i in {1..30}; do
        if docker ps --format "{{.Names}}\t{{.Status}}" | grep worker; then
            STATUS=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep worker | awk '{print $2}')
            log_info "Worker status: $STATUS"
            
            if [[ "$STATUS" == *"healthy"* ]]; then
                log_success "✅ Worker is healthy!"
                break
            elif [[ "$STATUS" == *"unhealthy"* ]]; then
                log_warn "⚠️  Worker is unhealthy, checking logs..."
                docker logs ai_workflow_engine-worker-1 --tail 10
            fi
        fi
        
        if [ $i -eq 30 ]; then
            log_error "❌ Worker did not become healthy within 5 minutes"
            return 1
        fi
        
        sleep 10
    done
}

# Function to test worker functionality
test_worker_functionality() {
    log_info "🧪 Testing worker functionality..."
    
    # Test healthcheck directly
    if docker exec ai_workflow_engine-worker-1 /usr/local/bin/healthcheck.sh >/dev/null 2>&1; then
        log_success "✅ Healthcheck passes"
    else
        log_error "❌ Healthcheck fails"
        return 1
    fi
    
    # Test if worker can connect to Redis
    if docker exec ai_workflow_engine-worker-1 python -c "
import redis
r = redis.Redis(host='redis', port=6379, username='lwe-app', password=open('/run/secrets/REDIS_PASSWORD').read().strip())
print('Redis ping:', r.ping())
" >/dev/null 2>&1; then
        log_success "✅ Redis connection works"
    else
        log_error "❌ Redis connection fails"
        return 1
    fi
    
    # Test Celery status
    if docker exec ai_workflow_engine-worker-1 bash -c "
cd /app
export POSTGRES_PASSWORD=\$(cat /run/secrets/POSTGRES_PASSWORD)
export REDIS_PASSWORD=\$(cat /run/secrets/REDIS_PASSWORD)
export JWT_SECRET_KEY=\$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=\$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=\$(cat /run/secrets/QDRANT_API_KEY)
export DATABASE_URL=\"postgresql+psycopg2://app_user:\${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db\"
export REDIS_URL=\"redis://lwe-app:\${REDIS_PASSWORD}@redis:6379/0\"
export PYTHONPATH=/app
timeout 10 celery -A worker.celery_app status
" >/dev/null 2>&1; then
        log_success "✅ Celery status works"
    else
        log_warn "⚠️  Celery status check failed (may be normal during startup)"
    fi
}

# Function to provide environment-specific recommendations
provide_recommendations() {
    log_info "💡 Environment-specific recommendations..."
    
    # Check if this is likely a server environment
    if [ "$TOTAL_MEM" -lt 4096 ] || [ "$AVAILABLE_MEM" -lt 1024 ]; then
        log_info "🖥️  Server environment detected (limited resources)"
        log_info "   - Consider increasing healthcheck timeouts"
        log_info "   - Monitor memory usage during operation"
        log_info "   - Worker concurrency is automatically adjusted based on available memory"
    else
        log_info "💻 Development environment detected (ample resources)"
        log_info "   - Worker should run without resource constraints"
        log_info "   - Higher concurrency may be available"
    fi
    
    log_info "📋 Monitoring commands:"
    log_info "   - Worker logs: docker logs -f ai_workflow_engine-worker-1"
    log_info "   - Worker status: docker ps | grep worker"
    log_info "   - Resource usage: docker stats ai_workflow_engine-worker-1"
    log_info "   - Test healthcheck: docker exec ai_workflow_engine-worker-1 /usr/local/bin/healthcheck.sh"
}

# Main execution
main() {
    log_info "Starting universal worker fix for both local and server environments..."
    
    check_system_resources
    verify_worker_config
    fix_worker_issues
    test_worker_functionality
    provide_recommendations
    
    log_success "🎯 Universal worker fix complete!"
    log_info "The worker should now be stable on both local and server environments."
    log_info "If issues persist, check the logs: docker logs ai_workflow_engine-worker-1"
}

# Handle command line arguments
case "${1:-}" in
    "check")
        check_system_resources
        verify_worker_config
        ;;
    "fix")
        fix_worker_issues
        ;;
    "test")
        test_worker_functionality
        ;;
    *)
        main
        ;;
esac