#!/bin/bash
# scripts/_start_services.sh
# Rebuilds and restarts a single specific service.

set -e
source "$(dirname "$0")/_common_functions.sh"

SERVICE_NAME="$1"
if [ -z "$SERVICE_NAME" ]; then
    log_error "Usage: $0 <service_name>"
    exit 1
fi

log_info "Starting individual service restart for: $SERVICE_NAME"

log_info "Rebuilding image for service '$SERVICE_NAME'..."
docker compose build "$SERVICE_NAME"
if [ $? -ne 0 ]; then
    log_error "Build failed for service '$SERVICE_NAME'. Exiting."
    exit 1
fi
log_info "Image for '$SERVICE_NAME' rebuilt."

log_info "Restarting service '$SERVICE_NAME'..."
docker compose up -d "$SERVICE_NAME"
if [ $? -ne 0 ]; then
    log_error "Failed to restart service '$SERVICE_NAME'. Exiting."
    exit 1
fi
log_info "Service '$SERVICE_NAME' restarted successfully."

if [[ " $@ " =~ " --no-watch " ]]; then
    log_info "Skipping dashboard launch due to --no-watch flag."
else
    log_info "Launching Docker Watch dashboard (Ctrl+C to exit)..."
    ./scripts/_docker_watch.sh
fi