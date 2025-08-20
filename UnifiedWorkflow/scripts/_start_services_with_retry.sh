#!/bin/bash
# scripts/_start_services_with_retry.sh
#
# Robust service startup script that handles startup dependencies and retries
# This addresses common issues with postgres/pgbouncer startup race conditions

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "Starting AI Workflow Engine services with retry logic..."

cd "$PROJECT_ROOT"

# --- Step 1: Start Core Infrastructure Services First ---
log_info "Starting core infrastructure services..."

CORE_SERVICES="postgres redis qdrant"
log_info "Starting: $CORE_SERVICES"
docker compose up -d $CORE_SERVICES

# Wait for postgres to be ready
log_info "Waiting for PostgreSQL to be ready..."
for i in {1..60}; do
    if docker compose exec -T postgres pg_isready -U app_user -d ai_workflow_db >/dev/null 2>&1; then
        log_success "✅ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        log_error "❌ PostgreSQL failed to start after 60 seconds"
        docker compose logs postgres
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Wait for Redis to be ready
log_info "Waiting for Redis to be ready..."
for i in {1..30}; do
    if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        log_success "✅ Redis is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "❌ Redis failed to start after 30 seconds"
        docker compose logs redis
        exit 1
    fi
    echo -n "."
    sleep 1
done

# --- Step 2: Start Database Proxy Services ---
log_info "Starting database proxy services..."

PROXY_SERVICES="pgbouncer"
log_info "Starting: $PROXY_SERVICES"
docker compose up -d $PROXY_SERVICES

# Wait for pgbouncer to be ready with retry
log_info "Waiting for PgBouncer to be ready..."
for i in {1..30}; do
    if docker compose exec -T pgbouncer psql -h localhost -p 6432 -U app_user -d ai_workflow_db -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "✅ PgBouncer is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        log_warn "⚠️ PgBouncer not responding, attempting restart..."
        docker compose restart pgbouncer
        sleep 5
        
        # Second attempt after restart
        for j in {1..15}; do
            if docker compose exec -T pgbouncer psql -h localhost -p 6432 -U app_user -d ai_workflow_db -c "SELECT 1;" >/dev/null 2>&1; then
                log_success "✅ PgBouncer is ready after restart"
                break
            fi
            if [ $j -eq 15 ]; then
                log_error "❌ PgBouncer failed to start after restart"
                docker compose logs pgbouncer
                exit 1
            fi
            echo -n "."
            sleep 1
        done
        break
    fi
    echo -n "."
    sleep 1
done

# --- Step 3: Start Application Services ---
log_info "Starting application services..."

APP_SERVICES="api worker webui"
log_info "Starting: $APP_SERVICES"
docker compose up -d $APP_SERVICES

# --- Step 4: Start Supporting Services ---
log_info "Starting supporting services..."

SUPPORT_SERVICES="ollama prometheus grafana cadvisor postgres_exporter pgbouncer_exporter redis_exporter"
log_info "Starting: $SUPPORT_SERVICES"
docker compose up -d $SUPPORT_SERVICES

# --- Step 5: Health Check All Services ---
log_info "Performing health checks..."

# Wait a bit for services to start
sleep 10

# Check critical services
CRITICAL_SERVICES="postgres redis pgbouncer api worker webui"
FAILED_SERVICES=""

for service in $CRITICAL_SERVICES; do
    if docker compose ps $service | grep -q "Up"; then
        log_success "✅ $service is running"
    else
        log_error "❌ $service failed to start"
        FAILED_SERVICES="$FAILED_SERVICES $service"
    fi
done

# If any critical services failed, attempt one more restart
if [ -n "$FAILED_SERVICES" ]; then
    log_warn "⚠️ Some services failed. Attempting restart for: $FAILED_SERVICES"
    docker compose restart $FAILED_SERVICES
    sleep 15
    
    # Check again
    STILL_FAILED=""
    for service in $FAILED_SERVICES; do
        if docker compose ps $service | grep -q "Up"; then
            log_success "✅ $service is now running"
        else
            log_error "❌ $service still failed after restart"
            STILL_FAILED="$STILL_FAILED $service"
        fi
    done
    
    if [ -n "$STILL_FAILED" ]; then
        log_error "❌ The following services failed to start: $STILL_FAILED"
        log_info "Check logs with: docker compose logs <service-name>"
        exit 1
    fi
fi

# --- Step 6: Final Status Check ---
log_info "Final service status check..."
docker compose ps

log_success "🎉 All services started successfully!"
log_info ""
log_info "🌐 Access the application at:"
log_info "  - https://localhost:8000 (API)"
log_info "  - https://localhost:5173 (WebUI)"
log_info ""
log_info "📊 Monitoring:"
log_info "  - Grafana: http://localhost:3000"
log_info "  - Prometheus: http://localhost:9090"
log_info ""
log_info "🔍 Check service logs with:"
log_info "  docker compose logs -f [service-name]"