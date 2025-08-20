#!/bin/bash
# scripts/fix_worker_healthcheck.sh
# Fix worker healthcheck issues that cause "unhealthy" status

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🏥 Worker Healthcheck Fix"
log_info "========================"

# Check current worker status
WORKER_STATUS=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep worker | awk '{print $2}')
log_info "Current worker status: $WORKER_STATUS"

if [[ "$WORKER_STATUS" == *"unhealthy"* ]]; then
    log_warn "⚠️  Worker is unhealthy. Investigating..."
    
    # Show the healthcheck command
    HEALTHCHECK_CMD=$(docker inspect ai_workflow_engine-worker-1 --format='{{range .Config.Healthcheck.Test}}{{.}} {{end}}' 2>/dev/null)
    log_info "Healthcheck command: $HEALTHCHECK_CMD"
    
    # Test healthcheck manually with detailed output
    log_info "Testing healthcheck manually..."
    
    if docker exec ai_workflow_engine-worker-1 bash -c "
        echo 'Testing Redis connection...'
        if ! python -c 'import redis; r=redis.Redis(host=\"redis\", port=6379, username=\"lwe-app\", password=open(\"/run/secrets/REDIS_PASSWORD\").read().strip()); print(r.ping())' 2>/dev/null; then
            echo 'Redis connection failed'
            exit 1
        fi
        echo 'Redis connection OK'
        
        echo 'Testing Celery ping...'
        PYTHONPATH=/app celery -A worker.celery_app --broker redis://lwe-app:\$(cat /run/secrets/REDIS_PASSWORD)@redis:6379/0 inspect ping -d celery@\${HOSTNAME} --timeout=5
    " 2>&1; then
        log_success "✅ Manual healthcheck passed"
    else
        log_error "❌ Manual healthcheck failed"
        
        # Check if it's a timeout issue
        log_info "Checking if this is a timeout issue..."
        
        # Test with longer timeout
        if docker exec ai_workflow_engine-worker-1 bash -c "
            echo 'Testing with longer timeout...'
            timeout 30 bash -c 'PYTHONPATH=/app celery -A worker.celery_app --broker redis://lwe-app:\$(cat /run/secrets/REDIS_PASSWORD)@redis:6379/0 inspect ping -d celery@\${HOSTNAME}'
        " 2>&1; then
            log_warn "⚠️  Healthcheck passes with longer timeout - this is a timing issue"
            
            # Fix by increasing healthcheck timeout in docker-compose.yml
            log_info "The issue is likely healthcheck timeout. Consider increasing timeout in docker-compose.yml:"
            log_info "  healthcheck:"
            log_info "    timeout: 30s  # Increase from 10s"
            log_info "    interval: 60s  # Increase from 30s"
            
        else
            log_error "❌ Healthcheck still failing even with longer timeout"
            
            # Check worker logs for errors
            log_info "Checking worker logs for errors..."
            docker logs ai_workflow_engine-worker-1 --tail 20
        fi
    fi
    
    # Check if worker is actually processing tasks
    log_info "Checking if worker can process tasks..."
    
    if docker exec ai_workflow_engine-worker-1 python -c "
import sys
sys.path.insert(0, '/app')

try:
    from worker.celery_app import celery_app
    
    # Test task registration
    print('Registered tasks:')
    for task in celery_app.tasks:
        if not task.startswith('celery.'):
            print(f'  - {task}')
    
    # Check if worker is ready
    inspect = celery_app.control.inspect()
    stats = inspect.stats()
    if stats:
        print('✅ Worker is responding to control commands')
        for worker, stat in stats.items():
            print(f'  Worker {worker}: {stat.get(\"pool\", {}).get(\"max-concurrency\", \"unknown\")} max concurrency')
    else:
        print('❌ Worker is not responding to control commands')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Error checking worker: {e}')
    sys.exit(1)
    " 2>/dev/null; then
        log_success "✅ Worker is functional for task processing"
    else
        log_error "❌ Worker cannot process tasks properly"
    fi
    
    # Try a simple fix by restarting worker
    log_info "Attempting to fix by restarting worker..."
    docker compose restart worker
    
    # Wait for restart and check again
    log_info "Waiting for worker to restart..."
    sleep 20
    
    # Check new status
    NEW_STATUS=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep worker | awk '{print $2}')
    log_info "New worker status: $NEW_STATUS"
    
    if [[ "$NEW_STATUS" == *"unhealthy"* ]]; then
        log_warn "⚠️  Worker is still unhealthy after restart"
        
        # More aggressive fix - restart dependencies
        log_info "Trying more aggressive fix - restarting dependencies..."
        docker compose restart redis pgbouncer
        
        sleep 10
        docker compose restart worker
        
        sleep 20
        
        FINAL_STATUS=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep worker | awk '{print $2}')
        log_info "Final worker status: $FINAL_STATUS"
        
        if [[ "$FINAL_STATUS" == *"healthy"* ]]; then
            log_success "✅ Worker is now healthy!"
        else
            log_error "❌ Worker is still unhealthy. Manual intervention required."
            log_info "Next steps:"
            log_info "1. Check worker logs: docker logs ai_workflow_engine-worker-1"
            log_info "2. Check Redis connection: docker exec ai_workflow_engine-worker-1 python -c 'import redis; r=redis.Redis(host=\"redis\", port=6379); print(r.ping())'"
            log_info "3. Consider increasing healthcheck timeout in docker-compose.yml"
        fi
    else
        log_success "✅ Worker is now healthy!"
    fi
    
elif [[ "$WORKER_STATUS" == *"healthy"* ]]; then
    log_success "✅ Worker is already healthy"
else
    log_info "Worker status: $WORKER_STATUS"
    log_info "Worker may still be starting up. Wait a moment and check again."
fi

log_info "🎯 Healthcheck fix attempt complete"