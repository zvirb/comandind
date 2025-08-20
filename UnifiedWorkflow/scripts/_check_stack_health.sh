#!/bin/bash
# scripts/_check_stack_health.sh
# Verifies that all long-running services in the Docker Compose setup are healthy.

source "$(dirname "$0")/_common_functions.sh"

log_info "Verifying stack health..."

# Get a list of all services defined in the compose files
SERVICES=$(docker compose config --services)
FAILED_SERVICES=()

for SERVICE in $SERVICES; do
    # Skip one-off jobs that are expected to exit
    is_job=$(docker compose config | yq e ".services.$SERVICE.restart == \"no\"" -)
    if [[ "$is_job" == "true" ]]; then
        STATUS=$(docker compose ps -a "$SERVICE" --format "{{.State}}" 2>/dev/null)
        EXIT_CODE=$(docker compose ps -a "$SERVICE" --format "{{.ExitCode}}" 2>/dev/null)
        if [[ "$STATUS" == "exited" && "$EXIT_CODE" != "0" ]]; then
            log_error "Service '$SERVICE' (one-off job) failed with exit code $EXIT_CODE."
            FAILED_SERVICES+=("$SERVICE")
        fi
        continue
    fi

    # Check long-running services
    STATUS=$(docker compose ps -a "$SERVICE" --format "{{.State}}" 2>/dev/null || echo "unknown")

    if [[ "$STATUS" != "running" && "$STATUS" != "healthy" ]]; then
        log_error "Service '$SERVICE' is not running. Current state: $STATUS"
        FAILED_SERVICES+=("$SERVICE")
    fi
done

if [ ${#FAILED_SERVICES[@]} -ne 0 ]; then
    log_error "Stack is unhealthy. The following services failed: ${FAILED_SERVICES[*]}"
    for FAILED_SERVICE in "${FAILED_SERVICES[@]}"; do
        DEPS=$(docker compose config | yq e ".services.$FAILED_SERVICE.depends_on | keys | .[]" - | tr '\n' ' ')
        log_container_failure "$FAILED_SERVICE" $DEPS
    done
    exit 1
else
    log_info "✅ All services are healthy."
    exit 0
fi