#!/bin/bash
# scripts/test_worker_healthcheck.sh
# Test the worker healthcheck command manually

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🩺 Testing Worker Healthcheck"
log_info "============================"

# Test the corrected healthcheck command
log_info "Testing corrected healthcheck command..."

if docker exec ai_workflow_engine-worker-1 bash -c "PYTHONPATH=/app celery -A worker.celery_app --broker redis://lwe-app:\$(cat /run/secrets/REDIS_PASSWORD)@redis:6379/0 inspect ping -d celery@\${HOSTNAME}" 2>&1; then
    log_success "✅ Healthcheck command works!"
else
    log_error "❌ Healthcheck command failed"
    
    # Try alternative approaches
    log_info "Trying alternative healthcheck approaches..."
    
    # Test 1: Simple Redis connection
    log_info "1. Testing Redis connection..."
    if docker exec ai_workflow_engine-worker-1 python -c "
import redis
r = redis.Redis(host='redis', port=6379, username='lwe-app', password=open('/run/secrets/REDIS_PASSWORD').read().strip())
print('Redis ping:', r.ping())
" 2>&1; then
        log_success "✅ Redis connection works"
    else
        log_error "❌ Redis connection failed"
    fi
    
    # Test 2: Celery status command
    log_info "2. Testing Celery status..."
    if docker exec ai_workflow_engine-worker-1 bash -c "cd /app && PYTHONPATH=/app celery -A worker.celery_app status" 2>&1; then
        log_success "✅ Celery status works"
    else
        log_error "❌ Celery status failed"
    fi
    
    # Test 3: Inspect active tasks
    log_info "3. Testing Celery inspect active..."
    if docker exec ai_workflow_engine-worker-1 bash -c "cd /app && PYTHONPATH=/app celery -A worker.celery_app inspect active" 2>&1; then
        log_success "✅ Celery inspect active works"
    else
        log_error "❌ Celery inspect active failed"
    fi
fi

# Restart worker to apply the updated healthcheck
log_info "Restarting worker to apply updated healthcheck..."
docker compose restart worker

log_info "Waiting for worker to restart..."
sleep 30

# Check new status
NEW_STATUS=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep worker)
log_info "New worker status: $NEW_STATUS"

if [[ "$NEW_STATUS" == *"healthy"* ]]; then
    log_success "✅ Worker is now healthy with corrected healthcheck!"
elif [[ "$NEW_STATUS" == *"unhealthy"* ]]; then
    log_warn "⚠️  Worker is still unhealthy. Checking logs..."
    docker logs ai_workflow_engine-worker-1 --tail 20
else
    log_info "Worker is still starting up. Status: $NEW_STATUS"
fi

log_info "🎯 Healthcheck test complete"