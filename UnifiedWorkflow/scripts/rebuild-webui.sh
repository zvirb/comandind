#!/bin/bash
# ==============================================================================
# Quick WebUI Rebuild Script - Ensures immediate code reflection
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
USE_DEV=false
FORCE_REBUILD=false
CLEAR_CACHE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dev)
            USE_DEV=true
            shift
            ;;
        -f|--force)
            FORCE_REBUILD=true
            shift
            ;;
        -c|--clear-cache)
            CLEAR_CACHE=true
            shift
            ;;
        -h|--help)
            cat << EOF
Usage: $0 [OPTIONS]

Quick WebUI rebuild script for immediate code reflection.

OPTIONS:
    -d, --dev          Use development mode with hot-reload
    -f, --force        Force rebuild without cache
    -c, --clear-cache  Clear node_modules and build cache
    -h, --help         Show this help message

EXAMPLES:
    $0              # Quick production rebuild
    $0 --dev        # Start development mode with hot-reload
    $0 --force      # Force complete rebuild
EOF
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"

# Generate fresh build metadata
export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
export GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

log_info "WebUI Rebuild Starting..."
log_info "Build metadata: DATE=$BUILD_DATE, GIT_HASH=$GIT_HASH"

if [ "$USE_DEV" = true ]; then
    # Development mode with hot-reload
    log_info "Starting development mode with hot-reload..."
    
    # Stop existing webui container
    docker compose -f docker-compose.dev.yml stop webui 2>/dev/null || true
    docker compose -f docker-compose.dev.yml rm -f webui 2>/dev/null || true
    
    # Clear cache if requested
    if [ "$CLEAR_CACHE" = true ]; then
        log_warning "Clearing node_modules cache..."
        docker volume rm ai_workflow_engine_webui_dev_node_modules 2>/dev/null || true
    fi
    
    # Start in development mode
    docker compose -f docker-compose.dev.yml up -d webui
    
    log_success "Development server started with hot-reload!"
    log_info "Access WebUI at: http://localhost:3001"
    log_info "Changes to source files will reflect immediately"
    
    # Show logs
    echo -e "\n${BLUE}Showing WebUI logs (Ctrl+C to exit):${NC}"
    docker compose -f docker-compose.dev.yml logs -f webui
    
else
    # Production mode rebuild
    log_info "Rebuilding WebUI for production..."
    
    # Stop the webui service
    log_info "Stopping WebUI service..."
    docker compose stop webui 2>/dev/null || true
    
    # Remove the old container
    docker compose rm -f webui 2>/dev/null || true
    
    # Remove old image to ensure fresh build
    if [ "$FORCE_REBUILD" = true ]; then
        log_warning "Removing old WebUI image..."
        docker rmi ai_workflow_engine/webui-next 2>/dev/null || true
        
        # Clear builder cache
        log_warning "Clearing Docker builder cache..."
        docker builder prune -f --filter "label=build.service=webui" 2>/dev/null || true
    fi
    
    # Build with cache busting
    log_info "Building WebUI with fresh code..."
    if [ "$FORCE_REBUILD" = true ]; then
        docker compose build --no-cache \
            --build-arg BUILD_DATE="$BUILD_DATE" \
            --build-arg GIT_HASH="$GIT_HASH" \
            webui
    else
        docker compose build \
            --build-arg BUILD_DATE="$BUILD_DATE" \
            --build-arg GIT_HASH="$GIT_HASH" \
            webui
    fi
    
    # Start the new container
    log_info "Starting WebUI service..."
    docker compose up -d webui
    
    # Wait for service to be healthy
    log_info "Waiting for WebUI to be healthy..."
    for i in {1..30}; do
        if docker compose exec webui wget --quiet --tries=1 --spider http://localhost:3001/ 2>/dev/null; then
            log_success "WebUI is healthy!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo
    
    # Verify the new build
    log_info "Verifying new build..."
    
    # Check container status
    docker compose ps webui
    
    # Show image info
    echo -e "\n${BLUE}WebUI Image Info:${NC}"
    docker images ai_workflow_engine/webui-next --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # Check build labels
    echo -e "\n${BLUE}Build Metadata:${NC}"
    docker inspect ai_workflow_engine/webui-next:latest | grep -E "build\.(date|git_hash)" | head -2
    
    log_success "WebUI rebuild completed!"
    
    # Test the endpoint
    log_info "Testing WebUI endpoint..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 | grep -q "200\|302"; then
        log_success "WebUI is accessible at: http://localhost:3001"
    else
        log_warning "WebUI may not be fully ready yet. Check logs with: docker compose logs -f webui"
    fi
fi

# Show helpful commands
echo -e "\n${BLUE}Useful commands:${NC}"
echo "  View logs:           docker compose logs -f webui"
echo "  Restart service:     docker compose restart webui"
echo "  Enter container:     docker compose exec webui sh"
echo "  Check code changes:  docker compose exec webui ls -la /app/dist/"

if [ "$USE_DEV" = false ]; then
    echo "  Switch to dev mode:  $0 --dev"
fi