#!/bin/bash
# scripts/_setup_soft.sh
#
# This script provides a soft setup for the AI Workflow Engine.
# It handles dependency checks and Docker image builds without regenerating
# certificates or secrets (preserves existing ones).
#
# This is used by run.sh --soft-reset to avoid regenerating certificates
# and passwords while still rebuilding the application.

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
    log_warn() { echo "WARN: $*"; }
    log_error() { echo "ERROR: $*"; }
fi

log_info "Starting AI Workflow Engine soft setup (preserving certificates and secrets)..."

# --- Ensure all scripts are executable ---
# This prevents "Permission Denied" errors, especially for scripts mounted into containers.
log_info "Making all shell scripts in the project executable..."
find "$PROJECT_ROOT" -type f -name "*.sh" -exec chmod +x {} +
log_success "✅ All scripts are now executable."

# --- Full Teardown Check ---
if [[ " $@ " =~ " --full-teardown " ]]; then
    log_info "Performing a full teardown of the environment..."
    # This stops containers, removes them, and deletes all associated volumes.
    docker compose --project-directory "$PROJECT_ROOT" down -v --remove-orphans
    log_success "✅ Full teardown complete."
fi

# --- Check if certificates and secrets exist ---
log_info "Checking for existing certificates and secrets..."

# Check for certificates in Docker volume
if docker volume ls -q | grep -q "ai_workflow_engine_certs"; then
    log_success "✅ Certificate volume exists, preserving existing certificates."
else
    log_warn "⚠️  Certificate volume not found. Certificates may need to be regenerated."
    log_info "Run 'scripts/_setup_secrets_and_certs.sh' to generate missing certificates."
fi

# Check for secrets directory
if [ -d "$PROJECT_ROOT/secrets" ] && [ "$(ls -A "$PROJECT_ROOT/secrets" 2>/dev/null)" ]; then
    log_success "✅ Secrets directory exists with files, preserving existing secrets."
else
    log_warn "⚠️  Secrets directory empty or missing. Secrets may need to be regenerated."
    log_info "Run 'scripts/_setup_secrets_and_certs.sh' to generate missing secrets."
fi

# --- Generate only environment files (if missing) ---
log_info "Ensuring environment configuration files exist..."

# Detect hostname for CORS configuration
HOSTNAME=$(hostname)
HOSTNAME_SHORT=$(hostname -s)
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "")

# Build CORS origins list including common variations and production domain
CORS_ORIGINS="https://localhost,https://127.0.0.1"
if [ -n "$HOSTNAME" ] && [ "$HOSTNAME" != "localhost" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,https://$HOSTNAME"
fi
if [ -n "$HOSTNAME_SHORT" ] && [ "$HOSTNAME_SHORT" != "$HOSTNAME" ] && [ "$HOSTNAME_SHORT" != "localhost" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,https://$HOSTNAME_SHORT,https://$HOSTNAME_SHORT.local"
fi
if [ -n "$LOCAL_IP" ] && [ "$LOCAL_IP" != "127.0.0.1" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,https://$LOCAL_IP"
fi

# Add production domain
CORS_ORIGINS="$CORS_ORIGINS,https://aiwfe.com,http://aiwfe.com"

# Generate .env file if it doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.template" ]; then
        cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
        # Update CORS origins in the generated file
        if [ -n "$CORS_ORIGINS" ]; then
            sed -i "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=$CORS_ORIGINS|g" "$PROJECT_ROOT/.env"
        fi
        log_info "Generated .env file from template with detected hostname configuration"
    else
        log_warn ".env.template not found, creating basic .env file"
        cat > "$PROJECT_ROOT/.env" <<EOF
# AI Workflow Engine Environment Configuration
ENVIRONMENT=production
DEBUG=false
POSTGRES_USER=app_user
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ai_workflow_db
REDIS_HOST=redis
REDIS_PORT=6379
QDRANT_HOST=qdrant
QDRANT_PORT=6333
OLLAMA_API_BASE_URL=http://ollama:11434
OLLAMA_GENERATION_MODEL_NAME=llama3.2:3b
OLLAMA_EMBEDDING_MODEL_NAME=nomic-embed-text
CORS_ALLOWED_ORIGINS=$CORS_ORIGINS
EOF
    fi
else
    log_info ".env file already exists, skipping generation"
fi

# Generate local.env file if it doesn't exist  
if [ ! -f "$PROJECT_ROOT/local.env" ]; then
    if [ -f "$PROJECT_ROOT/local.env.template" ]; then
        cp "$PROJECT_ROOT/local.env.template" "$PROJECT_ROOT/local.env"
        # Update CORS origins and hostname in the generated file
        if [ -n "$CORS_ORIGINS" ]; then
            sed -i "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=$CORS_ORIGINS|g" "$PROJECT_ROOT/local.env"
        fi
        if [ -n "$HOSTNAME" ]; then
            echo "# Detected hostname: $HOSTNAME" >> "$PROJECT_ROOT/local.env"
        fi
        log_info "Generated local.env file from template with detected hostname configuration"
    else
        log_warn "local.env.template not found, creating basic local.env file"
        cat > "$PROJECT_ROOT/local.env" <<EOF
# Local development environment overrides
ENVIRONMENT=development
DEBUG=true
WEBUI_PORT=5173
API_PORT=8000
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_workflow_engine
POSTGRES_USER=postgres
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_API_BASE_URL=http://localhost:11434
CORS_ALLOWED_ORIGINS=$CORS_ORIGINS
# Detected hostname: $HOSTNAME
EOF
    fi
else
    log_info "local.env file already exists, skipping generation"
fi

log_success "✅ Environment configuration files ensured."

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

log_success "✅ Soft setup complete. Docker images are built."
log_info "All user data, certificates, and secrets have been preserved from the previous setup."
log_info "You can now start the application by running './run.sh'."