#!/bin/bash
# scripts/_dev_restart.sh
# Quickly rebuilds and restarts the services for development.

set -e
source "$(dirname "$0")/_common_functions.sh"

log_info "Performing a quick development restart..."

log_info "Rebuilding Docker images (only changed ones)..."
docker compose build
if [ $? -ne 0 ]; then
    log_error "Build failed. Please check the output above."
    exit 1
fi
log_info "Images rebuilt."

log_info "Stopping existing services..."
docker compose stop

log_info "Starting all services..."
docker compose up -d

log_info "Verifying stack health..."
if ! ./scripts/_check_stack_health.sh; then
    log_error "Stack health verification failed. One or more services did not start correctly."
    exit 1
fi

log_info "✅ Development environment restarted successfully."

if [[ " $@ " =~ " --no-watch " ]]; then
    log_info "Skipping dashboard launch due to --no-watch flag."
else
    log_info "Launching Docker Watch dashboard (Ctrl+C to exit)..."
    ./scripts/_docker_watch.sh
fi