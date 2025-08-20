#!/bin/bash
# ==============================================================================
# Docker Container Rebuild Script with Cache Management
# ==============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_ROOT}/docker compose.yml"
COMPOSE_DEV_FILE="${PROJECT_ROOT}/docker compose.dev.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [SERVICE...]

Docker container rebuild script with cache management.

OPTIONS:
    -h, --help              Show this help message
    -d, --dev               Use development configuration
    -f, --force             Force rebuild without cache
    -c, --clean             Clean all Docker resources before rebuild
    -p, --prune             Prune unused Docker resources after rebuild
    -b, --build-only        Only build images without starting services
    -r, --restart           Restart services after rebuild
    --no-cache              Build without using cache
    --pull                  Always pull base images
    --parallel              Build services in parallel
    --push                  Push images to registry after build

SERVICE:
    Specific service(s) to rebuild (e.g., webui api worker)
    If not specified, all services will be rebuilt

EXAMPLES:
    $0                      # Rebuild all services with cache
    $0 --force webui        # Force rebuild webui without cache
    $0 --dev                # Use development configuration
    $0 --clean --force      # Clean everything and rebuild from scratch
    $0 --build-only api     # Only build API image without starting

EOF
}

# Parse command line arguments
SERVICES=()
USE_DEV=false
FORCE_REBUILD=false
CLEAN_BUILD=false
PRUNE_AFTER=false
BUILD_ONLY=false
RESTART_SERVICES=false
NO_CACHE=""
PULL_IMAGES=""
PARALLEL_BUILD=""
PUSH_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -d|--dev)
            USE_DEV=true
            shift
            ;;
        -f|--force)
            FORCE_REBUILD=true
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -p|--prune)
            PRUNE_AFTER=true
            shift
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -r|--restart)
            RESTART_SERVICES=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --pull)
            PULL_IMAGES="--pull"
            shift
            ;;
        --parallel)
            PARALLEL_BUILD="--parallel"
            shift
            ;;
        --push)
            PUSH_IMAGES=true
            shift
            ;;
        *)
            SERVICES+=("$1")
            shift
            ;;
    esac
done

# Set compose file based on environment
if [ "$USE_DEV" = true ]; then
    COMPOSE_CMD="docker compose -f $COMPOSE_DEV_FILE"
    log_info "Using development configuration"
else
    COMPOSE_CMD="docker compose -f $COMPOSE_FILE"
    log_info "Using production configuration"
fi

# Generate build arguments for cache busting
export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
export GIT_HASH=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")

log_info "Build metadata: DATE=$BUILD_DATE, GIT_HASH=$GIT_HASH"

# Function to clean Docker resources
clean_docker_resources() {
    log_warning "Cleaning Docker resources..."
    
    # Stop all project containers
    log_info "Stopping all project containers..."
    $COMPOSE_CMD down -v || true
    
    # Remove project images
    log_info "Removing project images..."
    docker images | grep "ai_workflow_engine" | awk '{print $3}' | xargs -r docker rmi -f || true
    
    # Clean build cache
    log_info "Cleaning build cache..."
    docker builder prune -af || true
    
    log_success "Docker resources cleaned"
}

# Function to build services
build_services() {
    local services="${SERVICES[@]:-}"
    local build_args="$NO_CACHE $PULL_IMAGES $PARALLEL_BUILD"
    
    if [ -z "$services" ]; then
        log_info "Building all services..."
        $COMPOSE_CMD build $build_args
    else
        log_info "Building services: $services"
        $COMPOSE_CMD build $build_args $services
    fi
}

# Function to restart services
restart_services() {
    local services="${SERVICES[@]:-}"
    
    if [ -z "$services" ]; then
        log_info "Restarting all services..."
        $COMPOSE_CMD restart
    else
        log_info "Restarting services: $services"
        $COMPOSE_CMD restart $services
    fi
}

# Function to start services
start_services() {
    local services="${SERVICES[@]:-}"
    
    if [ -z "$services" ]; then
        log_info "Starting all services..."
        $COMPOSE_CMD up -d
    else
        log_info "Starting services: $services"
        $COMPOSE_CMD up -d $services
    fi
}

# Function to push images
push_images() {
    local services="${SERVICES[@]:-}"
    
    if [ -z "$services" ]; then
        log_info "Pushing all images..."
        $COMPOSE_CMD push
    else
        log_info "Pushing images for services: $services"
        $COMPOSE_CMD push $services
    fi
}

# Function to prune Docker resources
prune_docker_resources() {
    log_info "Pruning unused Docker resources..."
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (careful with this)
    read -p "Remove unused volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    # Remove unused networks
    docker network prune -f
    
    log_success "Docker resources pruned"
}

# Function to verify rebuild
verify_rebuild() {
    log_info "Verifying rebuild..."
    
    # Check if services are running
    local running_services=$($COMPOSE_CMD ps --services --filter "status=running" | wc -l)
    
    if [ "$running_services" -gt 0 ]; then
        log_success "Services are running"
        
        # Show service status
        $COMPOSE_CMD ps
        
        # Show recent image builds
        echo -e "\n${BLUE}Recently built images:${NC}"
        docker images --filter "label=build.date=$BUILD_DATE" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    else
        log_warning "No services are running"
    fi
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    log_info "Starting Docker rebuild process..."
    
    # Clean if requested
    if [ "$CLEAN_BUILD" = true ]; then
        clean_docker_resources
    fi
    
    # Force rebuild without cache if requested
    if [ "$FORCE_REBUILD" = true ]; then
        NO_CACHE="--no-cache"
        log_warning "Forcing rebuild without cache"
    fi
    
    # Build services
    build_services
    
    # Push images if requested
    if [ "$PUSH_IMAGES" = true ]; then
        push_images
    fi
    
    # Start services unless build-only
    if [ "$BUILD_ONLY" = false ]; then
        if [ "$RESTART_SERVICES" = true ]; then
            restart_services
        else
            start_services
        fi
        
        # Wait for services to stabilize
        log_info "Waiting for services to stabilize..."
        sleep 5
        
        # Verify rebuild
        verify_rebuild
    else
        log_success "Build completed (build-only mode)"
    fi
    
    # Prune if requested
    if [ "$PRUNE_AFTER" = true ]; then
        prune_docker_resources
    fi
    
    log_success "Docker rebuild process completed!"
    
    # Show helpful commands
    echo -e "\n${BLUE}Helpful commands:${NC}"
    echo "  View logs:        $COMPOSE_CMD logs -f [service]"
    echo "  Check status:     $COMPOSE_CMD ps"
    echo "  Enter container:  $COMPOSE_CMD exec [service] sh"
    echo "  Stop services:    $COMPOSE_CMD down"
    
    if [ "$USE_DEV" = true ]; then
        echo -e "\n${GREEN}Development mode active!${NC}"
        echo "  WebUI:     http://localhost:3001"
        echo "  API:       http://localhost:8000"
        echo "  Hot-reload is enabled for source code changes"
    fi
}

# Run main function
main