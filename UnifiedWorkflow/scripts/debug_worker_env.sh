#!/bin/bash
# scripts/debug_worker_env.sh
# Debug worker environment variables and secrets

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "🔍 Worker Environment Debug"
log_info "==========================="

# Check if worker container is running
if ! docker ps --format "{{.Names}}" | grep -q "ai_workflow_engine-worker-1"; then
    log_error "❌ Worker container is not running"
    exit 1
fi

log_info "1. Checking secrets availability in worker container..."
docker exec ai_workflow_engine-worker-1 bash -c "
echo 'Secrets directory:'
ls -la /run/secrets/
echo ''

echo 'Testing secret file contents:'
for secret in POSTGRES_PASSWORD REDIS_PASSWORD JWT_SECRET_KEY API_KEY QDRANT_API_KEY; do
    if [ -f /run/secrets/\$secret ]; then
        echo \"\$secret: [$(cat /run/secrets/\$secret | wc -c) bytes]\"
    else
        echo \"\$secret: MISSING\"
    fi
done
"

log_info "2. Checking environment variables in worker container..."
docker exec ai_workflow_engine-worker-1 bash -c "
echo 'Environment variables related to worker:'
env | grep -E '(POSTGRES|REDIS|JWT|API|QDRANT|DATABASE|PYTHONPATH)' | sort || echo 'No matching environment variables found'
"

log_info "3. Testing if worker run.sh script can read secrets..."
docker exec ai_workflow_engine-worker-1 bash -c "
echo 'Testing secret reading:'
if [ -f /usr/local/bin/run.sh ]; then
    echo 'run.sh exists'
    # Test reading secrets like the run.sh script does
    if [ -f /run/secrets/POSTGRES_PASSWORD ]; then
        POSTGRES_PASSWORD=\$(cat /run/secrets/POSTGRES_PASSWORD)
        echo 'POSTGRES_PASSWORD: [read successfully]'
    else
        echo 'POSTGRES_PASSWORD: FAILED to read'
    fi
else
    echo 'run.sh not found'
fi
"

log_info "4. Testing Python configuration loading..."
docker exec ai_workflow_engine-worker-1 bash -c "
echo 'Testing Python config loading with secrets:'
cd /app

# First, set up environment variables like run.sh does
export POSTGRES_PASSWORD=\$(cat /run/secrets/POSTGRES_PASSWORD)
export REDIS_PASSWORD=\$(cat /run/secrets/REDIS_PASSWORD)
export JWT_SECRET_KEY=\$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=\$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=\$(cat /run/secrets/QDRANT_API_KEY)
export DATABASE_URL=\"postgresql+psycopg2://app_user:\${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db\"
export REDIS_URL=\"redis://lwe-app:\${REDIS_PASSWORD}@redis:6379/0\"
export PYTHONPATH=/app

echo 'Environment variables set. Testing Python config:'
python -c '
import sys
sys.path.insert(0, \"/app\")
try:
    from shared.utils.config import get_settings
    settings = get_settings()
    print(\"✅ Settings loaded successfully\")
    print(f\"Database URL: {settings.DATABASE_URL[:50]}...\")
    print(f\"Redis URL: {settings.REDIS_URL[:50]}...\")
except Exception as e:
    print(f\"❌ Settings failed to load: {e}\")
    sys.exit(1)
'
"

log_info "5. Testing Celery with proper environment..."
docker exec ai_workflow_engine-worker-1 bash -c "
echo 'Testing Celery with proper environment setup:'
cd /app

# Set up environment like run.sh does
export POSTGRES_PASSWORD=\$(cat /run/secrets/POSTGRES_PASSWORD)
export REDIS_PASSWORD=\$(cat /run/secrets/REDIS_PASSWORD)
export JWT_SECRET_KEY=\$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=\$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=\$(cat /run/secrets/QDRANT_API_KEY)
export DATABASE_URL=\"postgresql+psycopg2://app_user:\${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db\"
export REDIS_URL=\"redis://lwe-app:\${REDIS_PASSWORD}@redis:6379/0\"
export PYTHONPATH=/app

echo 'Testing Celery app loading:'
python -c '
import sys
sys.path.insert(0, \"/app\")
try:
    from worker.celery_app import celery_app
    print(\"✅ Celery app loaded successfully\")
    print(f\"Broker: {celery_app.conf.broker_url[:50]}...\")
    print(f\"Result backend: {celery_app.conf.result_backend[:50]}...\")
except Exception as e:
    print(f\"❌ Celery app failed to load: {e}\")
    sys.exit(1)
'

echo 'Testing Celery status:'
timeout 10 celery -A worker.celery_app status || echo 'Celery status command timed out or failed'
"

log_info "🎯 Environment debug complete"