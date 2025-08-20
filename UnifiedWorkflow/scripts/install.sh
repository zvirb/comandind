#!/bin/bash
# install.sh - AI Workflow Engine Installation Script
# 
# This script provides a complete installation for fresh server setups
# and handles development rebuilds when needed.

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Check if common functions exist
if [ -f "$SCRIPT_DIR/scripts/_common_functions.sh" ]; then
    source "$SCRIPT_DIR/scripts/_common_functions.sh"
else
    # Simple logger fallback
    log_info() { echo "INFO: $*"; }
    log_warn() { echo "WARN: $*"; }
    log_error() { echo "ERROR: $*"; }
    log_success() { echo "SUCCESS: $*"; }
fi

# --- Parse Command Line Arguments ---
FRESH_INSTALL=false
REBUILD_ONLY=false
NO_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fresh-install)
            FRESH_INSTALL=true
            shift
            ;;
        --rebuild-only)
            REBUILD_ONLY=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --help|-h)
            echo "AI Workflow Engine Installation Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --fresh-install    Complete fresh installation (default for new setups)"
            echo "  --rebuild-only     Only rebuild and restart specific services"
            echo "  --no-cache         Rebuild without using Docker cache"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Fresh install or smart detection"
            echo "  $0 --fresh-install    # Complete fresh installation"
            echo "  $0 --rebuild-only     # Quick rebuild for development"
            echo "  $0 --no-cache         # Full rebuild without cache"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# --- Detect Installation Type ---
if [ "$FRESH_INSTALL" = false ] && [ "$REBUILD_ONLY" = false ]; then
    # Auto-detect based on existing installation
    if [ ! -f ".env" ] || [ ! -f "local.env" ] || [ ! -d "secrets" ]; then
        log_info "Environment files or secrets missing - performing fresh installation"
        FRESH_INSTALL=true
    elif docker compose ps | grep -q "Up"; then
        log_info "Services already running - performing rebuild only"
        REBUILD_ONLY=true
    else
        log_info "No running services detected - performing fresh installation"
        FRESH_INSTALL=true
    fi
fi

# --- Fresh Installation Path ---
if [ "$FRESH_INSTALL" = true ]; then
    log_info "🚀 Starting fresh installation of AI Workflow Engine..."
    
    # Check if this is a server environment
    if [ -f "$SCRIPT_DIR/scripts/_setup_server.sh" ]; then
        log_info "Running server-specific setup..."
        "$SCRIPT_DIR/scripts/_setup_server.sh"
    fi
    
    # Run main setup
    log_info "Running main setup script..."
    "$SCRIPT_DIR/scripts/_setup.sh"
    
    # Start services with retry logic
    if [ -f "$SCRIPT_DIR/scripts/_start_services_with_retry.sh" ]; then
        log_info "Starting services with retry logic..."
        "$SCRIPT_DIR/scripts/_start_services_with_retry.sh"
    else
        log_info "Starting all services..."
        docker compose up -d
    fi
    
    log_success "🎉 Fresh installation complete!"

# --- Rebuild Only Path ---
elif [ "$REBUILD_ONLY" = true ]; then
    log_info "🔄 Rebuilding services for development..."
    
    # Prune build cache if requested
    if [ "$NO_CACHE" = true ]; then
        log_info "Pruning Docker build cache..."
        docker builder prune -f
    fi
    
    # Services to be rebuilt (can be customized)
    SERVICES="webui api worker"
    
    log_info "Stopping services: $SERVICES"
    docker compose stop $SERVICES
    
    log_info "Removing containers: $SERVICES"
    docker compose rm -f $SERVICES
    
    # Build arguments
    BUILD_ARGS=""
    if [ "$NO_CACHE" = true ]; then
        BUILD_ARGS="--no-cache"
    fi
    
    log_info "Rebuilding services: $SERVICES"
    docker compose build $BUILD_ARGS $SERVICES
    
    log_info "Starting all services..."
    docker compose up -d
    
    log_success "🎉 Rebuild complete!"
fi

# --- Post-Installation Information ---
log_info ""
log_info "📋 Installation Summary:"
log_info "  Type: $([ "$FRESH_INSTALL" = true ] && echo "Fresh Installation" || echo "Rebuild Only")"
log_info "  Cache: $([ "$NO_CACHE" = true ] && echo "Disabled" || echo "Enabled")"
log_info ""
log_info "🌐 Access the application:"
log_info "  - WebUI: https://localhost:5173"
log_info "  - API: https://localhost:8000"
log_info ""
log_info "🔧 Useful commands:"
log_info "  - View logs: docker compose logs -f"
log_info "  - Check status: docker compose ps"
log_info "  - Restart service: docker compose restart <service>"
log_info "  - Stop all: docker compose down"
log_info ""
log_info "📚 For troubleshooting, see the logs/ directory or run:"
log_info "  docker compose logs <service-name>"
