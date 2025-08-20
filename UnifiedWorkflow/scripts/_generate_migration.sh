#!/bin/bash
# scripts/_generate_migration.sh
# Creates a new Alembic database migration file.

set -e
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/_common_functions.sh"

MIGRATION_MESSAGE="$1"
if [ -z "$MIGRATION_MESSAGE" ]; then
    log_error "Usage: $0 \"<Your migration message>\""
    exit 1
fi

API_SERVICE="api"

log_info "Ensuring $API_SERVICE and database services are running..."
docker compose up -d --no-deps "$API_SERVICE" pgbouncer postgres redis qdrant

log_info "Waiting for the '$API_SERVICE' service to be healthy..."

# Timeout in seconds
TIMEOUT=120
INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Use docker inspect to get the health status directly. It's more reliable than parsing `ps` output.
    # The `|| true` prevents the script from exiting if the container isn't running yet.
    CONTAINER_ID=$(docker compose ps -q "$API_SERVICE" 2>/dev/null || true)
    if [ -n "$CONTAINER_ID" ]; then
        HEALTH_STATUS=$(docker inspect --format '{{.State.Health.Status}}' "$CONTAINER_ID" 2>/dev/null)
        case "$HEALTH_STATUS" in
            "healthy")
                log_success "✅ Service '$API_SERVICE' is healthy."
                break
                ;;
            "unhealthy")
                log_error "❌ Service '$API_SERVICE' is unhealthy. Aborting."
                docker compose logs "$API_SERVICE"
                exit 1
                ;;
        esac
    fi
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    log_info "Waiting for '$API_SERVICE' to be healthy... ($ELAPSED/$TIMEOUT s)"
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    log_error "❌ Timed out waiting for '$API_SERVICE' to become healthy."
    docker compose logs "$API_SERVICE"
    exit 1
fi

log_info "Generating Alembic migration: \"$MIGRATION_MESSAGE\""
DB_URL="postgresql://$(cat $SCRIPT_DIR/../secrets/postgres_user.txt):$(cat $SCRIPT_DIR/../secrets/postgres_password.txt)@postgres:5432/$(cat $SCRIPT_DIR/../secrets/postgres_db.txt)"
docker compose exec -e DATABASE_URL=$DB_URL "$API_SERVICE" alembic revision --autogenerate -m "$MIGRATION_MESSAGE"
if [ $? -ne 0 ]; then
    log_error "Failed to generate migration."
    exit 1
fi
log_info "✅ Successfully created new migration file."