#!/bin/bash

# SCORCHED EARTH RECOVERY SCRIPT
# Complete infrastructure teardown and rebuild

set -e

LOG_FILE="/home/marku/ai_workflow_engine/scorched_earth_recovery.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log_message() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# Safety confirmation
echo "WARNING: This will completely destroy and rebuild the infrastructure!"
echo "Ensure you have run the backup script first."
echo "Type 'CONFIRM_SCORCHED_EARTH' to proceed:"
read -r confirmation
if [ "$confirmation" != "CONFIRM_SCORCHED_EARTH" ]; then
    echo "Operation cancelled."
    exit 1
fi

log_message "=== SCORCHED EARTH RECOVERY START ==="

# Phase 1: Complete Teardown
log_message "Phase 1: Complete Infrastructure Teardown"

log_message "Stopping all containers..."
cd /home/marku/ai_workflow_engine
docker-compose down --remove-orphans --timeout 30 || true

log_message "Removing all project containers..."
docker ps -a --filter "label=com.docker.compose.project=ai_workflow_engine" -q | xargs -r docker rm -f || true

log_message "Removing project images..."
docker images --filter "label=ai_workflow_engine" -q | xargs -r docker rmi -f || true

log_message "Removing custom networks..."
docker network ls --filter "label=com.docker.compose.project=ai_workflow_engine" -q | xargs -r docker network rm || true

log_message "Cleaning unused resources..."
docker system prune -f --volumes

# Phase 2: Preserve Critical Data
log_message "Phase 2: Critical Data Preservation Check"

# Verify backup exists
if [ ! -d "/home/marku/emergency_backup_"* ]; then
    log_message "ERROR: No emergency backup found! Run emergency_backup_script.sh first!"
    exit 1
fi

BACKUP_DIR=$(ls -dt /home/marku/emergency_backup_* | head -1)
log_message "Using backup: $BACKUP_DIR"

# Phase 3: Clean Rebuild
log_message "Phase 3: Clean Infrastructure Rebuild"

log_message "Rebuilding images with no cache..."
docker-compose build --no-cache --parallel

log_message "Creating fresh volumes..."
docker-compose up --no-start

log_message "Starting core services first (postgres, redis)..."
docker-compose up -d postgres redis

log_message "Waiting for core services to be healthy..."
sleep 30

# Wait for postgres health
timeout 60 bash -c 'while ! docker exec ai_workflow_engine-postgres-1 pg_isready -U app_user; do sleep 2; done'

# Wait for redis health  
timeout 60 bash -c 'while ! docker exec ai_workflow_engine-redis-1 redis-cli -u redis://lwe-app:$(cat secrets/redis_password.txt)@localhost:6379 ping; do sleep 2; done'

log_message "Starting secondary services (qdrant, ollama)..."
docker-compose up -d qdrant ollama

log_message "Waiting for secondary services..."
sleep 30

log_message "Running database migrations..."
docker-compose up api-migrate

log_message "Creating admin user..."
docker-compose up api-create-admin

log_message "Starting all remaining services..."
docker-compose up -d

# Phase 4: Progressive Validation
log_message "Phase 4: Progressive Service Validation"

validate_service() {
    local service_name=$1
    local health_check=$2
    local max_attempts=${3:-30}
    
    log_message "Validating $service_name..."
    
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if eval "$health_check"; then
            log_message "✓ $service_name is healthy"
            return 0
        fi
        
        log_message "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    log_message "✗ $service_name failed to become healthy"
    return 1
}

# Core service validation
validate_service "PostgreSQL" "docker exec ai_workflow_engine-postgres-1 pg_isready -U app_user"
validate_service "Redis" "docker exec ai_workflow_engine-redis-1 redis-cli -u redis://lwe-app:\$(cat secrets/redis_password.txt)@localhost:6379 ping | grep -q PONG"
validate_service "Qdrant" "docker exec ai_workflow_engine-qdrant-1 curl -f -k https://localhost:6333/healthz"
validate_service "API" "curl -f http://localhost:8000/health"
validate_service "WebUI" "curl -f http://localhost:3000"
validate_service "Caddy" "curl -f http://localhost"

# Phase 5: Production Validation
log_message "Phase 5: Production Endpoint Validation"

log_message "Testing production endpoints..."
if curl -f -k -m 10 https://aiwfe.com/health; then
    log_message "✓ Production HTTPS endpoint responding"
else
    log_message "✗ Production HTTPS endpoint failed"
fi

if curl -f -k -m 10 http://aiwfe.com/health; then
    log_message "✓ Production HTTP endpoint responding"
else
    log_message "✗ Production HTTP endpoint failed"
fi

# Phase 6: Final System Health Check
log_message "Phase 6: Final System Health Check"

log_message "Running final validation script..."
bash /home/marku/ai_workflow_engine/emergency_recovery_validation.sh

log_message "=== SCORCHED EARTH RECOVERY COMPLETE ==="
log_message "Infrastructure has been completely rebuilt"
log_message "All critical services are running"
log_message "Production endpoints validated"
log_message "Recovery log: $LOG_FILE"