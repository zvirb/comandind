#!/bin/bash
# scripts/fix_worker_database.sh
# Fix database connection issues in worker container

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🔧 Worker Database Connection Fix"
log_info "================================"

# Check if worker is currently running
if docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
    log_info "Worker is currently running. Checking database connection..."
    
    # Test database connection from worker container
    if docker exec ai_workflow_engine-worker-1 python -c "
import os
import sys
sys.path.insert(0, '/app')

try:
    from sqlalchemy import create_engine, text
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        postgres_password = open('/run/secrets/POSTGRES_PASSWORD').read().strip()
        db_url = f'postgresql+psycopg2://app_user:{postgres_password}@postgres:5432/ai_workflow_db'
    
    print(f'Testing connection to: {db_url.replace(postgres_password, \"***\") if \"postgres_password\" in locals() else \"[URL]\"}')
    
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful')
        
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_success "✅ Database connection is working"
    else
        log_error "❌ Database connection failed"
        
        # Try to fix by restarting dependencies
        log_info "Attempting to fix by restarting database dependencies..."
        docker compose restart postgres pgbouncer
        
        # Wait for services to be healthy
        log_info "Waiting for database services to be healthy..."
        sleep 10
        
        # Test again
        if docker exec ai_workflow_engine-worker-1 python -c "
import os
import sys
sys.path.insert(0, '/app')

try:
    from sqlalchemy import create_engine, text
    
    postgres_password = open('/run/secrets/POSTGRES_PASSWORD').read().strip()
    db_url = f'postgresql+psycopg2://app_user:{postgres_password}@postgres:5432/ai_workflow_db'
    
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful after restart')
        
except Exception as e:
    print(f'❌ Database connection still failed: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log_success "✅ Database connection fixed"
        else
            log_error "❌ Database connection still failing"
        fi
    fi
else
    log_warn "⚠️  Worker is not running"
fi

# Check for database initialization issues
log_info "Checking database initialization..."

# Check if database tables exist
if docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | grep -q "0"; then
    log_warn "⚠️  Database appears to be empty, may need migration"
    
    # Run migration
    log_info "Running database migration..."
    docker compose run --rm api-migrate
    
    if [ $? -eq 0 ]; then
        log_success "✅ Database migration completed"
    else
        log_error "❌ Database migration failed"
    fi
else
    log_success "✅ Database tables exist"
fi

# Check worker healthcheck
log_info "Testing worker healthcheck..."
if docker exec ai_workflow_engine-worker-1 bash -c "
PYTHONPATH=/app celery -A worker.celery_app --broker redis://lwe-app:\$(cat /run/secrets/REDIS_PASSWORD)@redis:6379/0 inspect ping -d celery@\${HOSTNAME}
" 2>/dev/null; then
    log_success "✅ Worker healthcheck passed"
else
    log_error "❌ Worker healthcheck failed"
    
    # Try restarting worker
    log_info "Restarting worker container..."
    docker compose restart worker
    
    # Wait and test again
    sleep 15
    if docker exec ai_workflow_engine-worker-1 bash -c "
PYTHONPATH=/app celery -A worker.celery_app --broker redis://lwe-app:\$(cat /run/secrets/REDIS_PASSWORD)@redis:6379/0 inspect ping -d celery@\${HOSTNAME}
" 2>/dev/null; then
        log_success "✅ Worker healthcheck passed after restart"
    else
        log_error "❌ Worker healthcheck still failing"
    fi
fi

log_info "🎯 Database connection fix attempt complete"
log_info "If issues persist, check the worker logs: docker logs ai_workflow_engine-worker-1"