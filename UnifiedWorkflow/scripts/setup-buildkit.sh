#!/bin/bash
# ==============================================================================
# Docker BuildKit Setup and Optimization Script
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to check Docker version
check_docker_version() {
    local min_version="18.09"
    local docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0.0.0")
    
    if [ "$(printf '%s\n' "$min_version" "$docker_version" | sort -V | head -n1)" != "$min_version" ]; then
        log_error "Docker version $docker_version is too old. Minimum required: $min_version"
        return 1
    fi
    
    log_success "Docker version $docker_version supports BuildKit"
    return 0
}

# Function to enable BuildKit
enable_buildkit() {
    log_info "Enabling Docker BuildKit..."
    
    # Create Docker config directory if it doesn't exist
    mkdir -p ~/.docker
    
    # Check if daemon.json exists
    if [ -f ~/.docker/daemon.json ]; then
        # Backup existing configuration
        cp ~/.docker/daemon.json ~/.docker/daemon.json.backup
        log_info "Backed up existing Docker daemon configuration"
    fi
    
    # Enable BuildKit in Docker daemon configuration
    if [ -f /etc/docker/daemon.json ]; then
        log_warning "/etc/docker/daemon.json exists. Please manually add: \"features\": {\"buildkit\": true}"
    else
        log_info "BuildKit will be enabled via environment variable"
    fi
    
    # Set BuildKit environment variable for current session
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    log_success "BuildKit enabled for current session"
}

# Function to setup BuildKit persistent configuration
setup_persistent_buildkit() {
    log_info "Setting up persistent BuildKit configuration..."
    
    # Create shell profile configuration
    local shell_profile=""
    
    if [ -f ~/.bashrc ]; then
        shell_profile=~/.bashrc
    elif [ -f ~/.zshrc ]; then
        shell_profile=~/.zshrc
    elif [ -f ~/.profile ]; then
        shell_profile=~/.profile
    else
        log_warning "No shell profile found. Please manually add BuildKit exports to your shell configuration"
        return
    fi
    
    # Check if BuildKit exports already exist
    if grep -q "DOCKER_BUILDKIT" "$shell_profile"; then
        log_info "BuildKit configuration already exists in $shell_profile"
    else
        # Add BuildKit exports to shell profile
        cat >> "$shell_profile" << 'EOF'

# Docker BuildKit Configuration
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export BUILDKIT_PROGRESS=plain
EOF
        log_success "Added BuildKit configuration to $shell_profile"
    fi
}

# Function to create BuildKit builder
create_buildkit_builder() {
    log_info "Creating optimized BuildKit builder..."
    
    # Check if builder already exists
    if docker buildx ls | grep -q "ai-workflow-builder"; then
        log_info "Builder 'ai-workflow-builder' already exists"
        docker buildx rm ai-workflow-builder 2>/dev/null || true
    fi
    
    # Create new builder with optimized configuration
    docker buildx create \
        --name ai-workflow-builder \
        --driver docker-container \
        --driver-opt network=host \
        --driver-opt image=moby/buildkit:latest \
        --config "$PROJECT_ROOT/docker-buildkit.toml" \
        --use
    
    # Bootstrap the builder
    docker buildx inspect --bootstrap
    
    log_success "Created optimized BuildKit builder 'ai-workflow-builder'"
}

# Function to setup build cache
setup_build_cache() {
    log_info "Setting up build cache volumes..."
    
    # Create cache volumes
    docker volume create ai_workflow_buildkit_cache 2>/dev/null || true
    docker volume create ai_workflow_npm_cache 2>/dev/null || true
    
    log_success "Build cache volumes created"
}

# Function to optimize Docker daemon
optimize_docker_daemon() {
    log_info "Optimizing Docker daemon configuration..."
    
    # Check if running with sufficient privileges
    if [ "$EUID" -ne 0 ]; then
        log_warning "Skipping daemon optimization (requires root). Run with sudo for full optimization."
        return
    fi
    
    # Create optimized daemon configuration
    cat > /tmp/docker-daemon-optimized.json << 'EOF'
{
  "features": {
    "buildkit": true
  },
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "10GB"
    }
  },
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 10,
  "registry-mirrors": [],
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    
    # Backup existing configuration
    if [ -f /etc/docker/daemon.json ]; then
        cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
        log_info "Backed up existing daemon configuration"
    fi
    
    # Apply optimized configuration
    cp /tmp/docker-daemon-optimized.json /etc/docker/daemon.json
    
    # Restart Docker daemon
    systemctl restart docker || service docker restart
    
    log_success "Docker daemon optimized and restarted"
}

# Function to verify BuildKit setup
verify_buildkit() {
    log_info "Verifying BuildKit setup..."
    
    # Check environment variable
    if [ "${DOCKER_BUILDKIT:-0}" = "1" ]; then
        log_success "DOCKER_BUILDKIT environment variable is set"
    else
        log_warning "DOCKER_BUILDKIT environment variable is not set"
    fi
    
    # Test BuildKit with a simple build
    log_info "Testing BuildKit with a simple build..."
    
    # Create temporary Dockerfile
    local temp_dir=$(mktemp -d)
    cat > "$temp_dir/Dockerfile" << 'EOF'
# syntax=docker/dockerfile:1
FROM alpine:latest
RUN echo "BuildKit test successful"
EOF
    
    # Try to build with BuildKit
    if DOCKER_BUILDKIT=1 docker build --progress=plain -t buildkit-test "$temp_dir" >/dev/null 2>&1; then
        log_success "BuildKit is working correctly"
        docker rmi buildkit-test >/dev/null 2>&1
    else
        log_error "BuildKit test failed"
    fi
    
    # Clean up
    rm -rf "$temp_dir"
}

# Function to show BuildKit usage tips
show_usage_tips() {
    echo -e "\n${BLUE}BuildKit Usage Tips:${NC}"
    echo "1. BuildKit is now enabled. Use these commands for optimized builds:"
    echo "   docker build --progress=plain .    # Show detailed build progress"
    echo "   docker build --cache-from ...      # Use external cache"
    echo "   docker build --secret ...           # Use build secrets securely"
    echo ""
    echo "2. For multi-platform builds:"
    echo "   docker buildx build --platform linux/amd64,linux/arm64 ."
    echo ""
    echo "3. For the AI Workflow Engine project:"
    echo "   ./scripts/docker-rebuild.sh --force  # Full rebuild with BuildKit"
    echo "   ./scripts/rebuild-webui.sh          # Quick WebUI rebuild"
    echo ""
    echo "4. Monitor build cache usage:"
    echo "   docker buildx du                    # Show cache disk usage"
    echo "   docker buildx prune                  # Clean build cache"
}

# Main execution
main() {
    log_info "Docker BuildKit Setup Starting..."
    
    # Check Docker version
    if ! check_docker_version; then
        log_error "Please upgrade Docker to use BuildKit"
        exit 1
    fi
    
    # Enable BuildKit
    enable_buildkit
    
    # Setup persistent configuration
    setup_persistent_buildkit
    
    # Create optimized builder
    if command -v docker buildx &> /dev/null; then
        create_buildkit_builder
    else
        log_warning "docker buildx not available. Install docker-buildx-plugin for advanced features"
    fi
    
    # Setup build cache
    setup_build_cache
    
    # Optimize Docker daemon (if root)
    if [ "$EUID" -eq 0 ]; then
        optimize_docker_daemon
    fi
    
    # Verify setup
    verify_buildkit
    
    log_success "BuildKit setup completed!"
    
    # Show usage tips
    show_usage_tips
    
    echo -e "\n${GREEN}BuildKit is ready!${NC} Source your shell profile or run:"
    echo "  export DOCKER_BUILDKIT=1"
    echo "  export COMPOSE_DOCKER_CLI_BUILD=1"
}

# Run main function
main