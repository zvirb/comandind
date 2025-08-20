#!/bin/bash
# scripts/_setup.sh
#
# This script provides a comprehensive setup for the AI Workflow Engine.
# It handles dependency checks, secret generation, Docker image builds,
# and service startup in the correct order.

set -e

# Get the directory of this script to source common functions
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

# Check for _common_functions.sh and source it if it exists
if [ -f "$SCRIPT_DIR/_common_functions.sh" ]; then
    source "$SCRIPT_DIR/_common_functions.sh"
else
    # Simple logger fallback if common functions are not available
    log_info() { echo "INFO: $*"; }
    log_success() { echo "SUCCESS: $*"; }
fi

log_info "Starting AI Workflow Engine setup..."

# --- Ensure all scripts are executable ---
# This prevents "Permission Denied" errors, especially for scripts mounted into containers.
log_info "Making all shell scripts in the project executable..."

# First, try to fix any permission issues that might prevent chmod from working
if [ "$(whoami)" = "root" ] || [ -n "$SUDO_USER" ]; then
    # If running as root or with sudo, we can fix ownership issues
    TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}"
    if [ "$TARGET_USER" != "root" ]; then
        log_info "Fixing ownership of script files..."
        find "$PROJECT_ROOT" -type f -name "*.sh" -exec chown "$TARGET_USER:$(id -gn $TARGET_USER)" {} \; 2>/dev/null || true
    fi
fi

# Now make scripts executable
if find "$PROJECT_ROOT" -type f -name "*.sh" -exec chmod +x {} + 2>/dev/null; then
    log_success "✅ All scripts are now executable."
else
    log_warn "⚠️  Some scripts could not be made executable due to permission issues."
    log_info "You may need to run: sudo ./scripts/fix_permissions.sh"
fi

# --- Full Teardown Check ---
if [[ " $@ " =~ " --full-teardown " ]]; then
    log_info "Performing a full teardown of the environment..."
    # This stops containers, removes them, and deletes all associated volumes.
    docker compose --project-directory "$PROJECT_ROOT" down -v --remove-orphans
    log_success "✅ Full teardown complete."
fi

# --- Generate Secrets and Certificates ---
log_info "Setting up secrets and certificates..."
"$SCRIPT_DIR/_setup_secrets_and_certs.sh"
log_success "✅ Secrets and certificates setup complete."

# --- Dependency Integrity Check ---
log_info "Checking if poetry.lock is consistent with pyproject.toml..."
# We run this check inside a container to ensure a consistent environment and
# avoid issues with the host's Python or Poetry versions.
# The `poetry lock --check` command will exit with a non-zero status if
# the files are out of sync.

# The command to run inside the container. We use 'set -e' to ensure that
# the script exits immediately if any command fails. We redirect stdout to
# /dev/null so we only see error output from the check if it fails.
CHECK_COMMAND="set -e; python -m pip install --upgrade pip --quiet; python -m pip install 'poetry>=1.5' --quiet; python -m poetry check"

if ! docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim sh -c "$CHECK_COMMAND" >/dev/null; then
    log_info "poetry.lock is out of sync. Regenerating to prevent build failures..."
    # The lock_dependencies.sh script handles the regeneration process cleanly.
    "$SCRIPT_DIR/lock_dependencies.sh"
else
    log_success "✅ poetry.lock is consistent with pyproject.toml."
fi

BUILD_ARGS="--pull"
if [[ " $@ " =~ " --full-teardown " ]]; then
    log_info "Full teardown requested, disabling build cache for a complete refresh."
    BUILD_ARGS="$BUILD_ARGS --no-cache"
elif [[ " $@ " =~ " --no-cache " ]]; then
    log_info "Cache disabled by flag. Performing a full rebuild of all images."
    BUILD_ARGS="$BUILD_ARGS --no-cache"
else
    log_info "Using Docker cache for builds. Use --no-cache for a full rebuild."
fi

log_info "Building all Docker images. This may take some time on the first run..."
# The --pull flag ensures we have the latest base images.
# The --progress=plain flag provides more detailed build output.
docker compose --project-directory "$PROJECT_ROOT" build $BUILD_ARGS --progress=auto

log_success "✅ Setup complete. Docker images are built."
log_info "You can now start the application by running './run.sh'."