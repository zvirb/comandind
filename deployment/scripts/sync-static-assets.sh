#!/bin/bash

# Static Asset Synchronization Script for Blue-Green Deployment
# This script ensures static assets are properly synchronized when switching between environments

set -euo pipefail

# Configuration
BLUE_CONTAINER="game-blue"
GREEN_CONTAINER="game-green"
ACTIVE_ENV=${1:-blue}
SHARED_VOLUME="game-static-assets"
LOG_FILE="/var/log/static-asset-sync.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [STATIC-SYNC] $1" | tee -a "$LOG_FILE"
}

# Function to check container health
check_container_health() {
    local container=$1
    if ! docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        log "ERROR: Container $container is not running"
        return 1
    fi
    
    # Check health status
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
    if [[ "$health_status" == "healthy" ]] || [[ "$health_status" == "no-health-check" ]]; then
        log "Container $container is healthy"
        return 0
    else
        log "WARNING: Container $container health status: $health_status"
        return 1
    fi
}

# Function to sync static assets from active container
sync_static_assets() {
    local source_container=$1
    log "Starting static asset synchronization from $source_container"
    
    # Check if source container is healthy
    if ! check_container_health "$source_container"; then
        log "ERROR: Source container $source_container is not healthy, aborting sync"
        exit 1
    fi
    
    # Create temporary directory for asset extraction
    local temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT
    
    # Extract static assets from container
    log "Extracting static assets from $source_container to temporary directory"
    if ! docker cp "$source_container:/usr/share/nginx/html/." "$temp_dir/"; then
        log "ERROR: Failed to extract static assets from $source_container"
        exit 1
    fi
    
    # Verify assets were extracted
    if [[ ! -d "$temp_dir" ]] || [[ -z "$(ls -A $temp_dir)" ]]; then
        log "ERROR: No static assets found in $source_container"
        exit 1
    fi
    
    # Get list of files for logging
    local file_count=$(find "$temp_dir" -type f | wc -l)
    local total_size=$(du -sh "$temp_dir" | cut -f1)
    log "Extracted $file_count files, total size: $total_size"
    
    # Copy assets to shared volume via temporary container
    log "Copying assets to shared volume $SHARED_VOLUME"
    docker run --rm \
        --volume "$SHARED_VOLUME:/target" \
        --volume "$temp_dir:/source:ro" \
        alpine:latest \
        sh -c "
            # Clear target directory
            rm -rf /target/*
            # Copy new assets
            cp -r /source/* /target/
            # Set proper permissions
            chown -R 101:101 /target
            chmod -R 755 /target
            # List final contents for verification
            echo 'Final asset count:' \$(find /target -type f | wc -l)
        "
    
    if [[ $? -eq 0 ]]; then
        log "Successfully synchronized static assets from $source_container"
        
        # Verify sync by listing some key files
        docker run --rm --volume "$SHARED_VOLUME:/check:ro" alpine:latest \
            sh -c "ls -la /check/ | head -10" | while read line; do
                log "VERIFY: $line"
            done
    else
        log "ERROR: Failed to synchronize static assets to shared volume"
        exit 1
    fi
}

# Function to switch active environment
switch_environment() {
    local new_active=$1
    local source_container
    
    if [[ "$new_active" == "blue" ]]; then
        source_container="$BLUE_CONTAINER"
    elif [[ "$new_active" == "green" ]]; then
        source_container="$GREEN_CONTAINER"
    else
        log "ERROR: Invalid environment '$new_active'. Must be 'blue' or 'green'"
        exit 1
    fi
    
    log "Switching static assets to $new_active environment ($source_container)"
    sync_static_assets "$source_container"
    
    # Update upstream configuration if needed
    # This would integrate with the existing blue-green switching mechanism
    log "Static asset switch to $new_active completed successfully"
}

# Function to handle emergency fallback
emergency_fallback() {
    log "EMERGENCY: Attempting fallback static asset sync"
    
    # Try both containers in order of preference
    for container in "$BLUE_CONTAINER" "$GREEN_CONTAINER"; do
        if check_container_health "$container"; then
            log "EMERGENCY: Using $container for fallback assets"
            sync_static_assets "$container"
            return 0
        fi
    done
    
    log "EMERGENCY: No healthy containers available for static assets"
    exit 1
}

# Function to verify static assets are available
verify_static_assets() {
    log "Verifying static assets availability"
    
    # Check if shared volume has content
    local asset_count=$(docker run --rm --volume "$SHARED_VOLUME:/check:ro" alpine:latest \
        sh -c "find /check -type f -name '*.js' -o -name '*.css' -o -name '*.html' | wc -l")
    
    if [[ "$asset_count" -gt 0 ]]; then
        log "Verification successful: $asset_count static assets found"
        return 0
    else
        log "Verification failed: No static assets found in shared volume"
        return 1
    fi
}

# Main execution
main() {
    log "Static asset synchronization started for environment: $ACTIVE_ENV"
    
    case "${2:-sync}" in
        "sync")
            switch_environment "$ACTIVE_ENV"
            verify_static_assets
            ;;
        "verify")
            verify_static_assets
            ;;
        "emergency")
            emergency_fallback
            ;;
        *)
            echo "Usage: $0 <blue|green> [sync|verify|emergency]"
            echo "  sync:      Synchronize static assets from specified environment (default)"
            echo "  verify:    Verify static assets are available"
            echo "  emergency: Emergency fallback to any healthy container"
            exit 1
            ;;
    esac
    
    log "Static asset synchronization completed successfully"
}

# Run main function
main "$@"