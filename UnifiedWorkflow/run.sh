#!/bin/bash
# run.sh
# This script is the primary entrypoint for starting the ai_workflow_engine services.
# It should be run after the one-time setup using 'scripts/_setup.sh'.
export INVOCATION_COMMAND="$0 $@"
set -e # Exit immediately if a command exits with a non-zero status.

# Source common functions
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/scripts/_common_functions.sh"

# Function to ask for confirmation with detailed warnings
confirm_destructive_action() {
    local action="$1"
    local warning="$2"
    local preserve_info="$3"
    
    echo ""
    log_warn "⚠️  WARNING: You are about to perform a $action"
    echo ""
    log_warn "📋 WHAT WILL BE REMOVED:"
    echo "$warning"
    
    if [[ -n "$preserve_info" ]]; then
        echo ""
        log_info "✅ WHAT WILL BE PRESERVED:"
        echo "$preserve_info"
    fi
    
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Operation cancelled by user."
        exit 0
    fi
}

log_info "Starting ai_workflow_engine services..."

# Check for Docker and Docker Compose
check_command "docker"
check_command "docker compose"

# Check if we can write to the project directory (permission check)
if ! touch "$SCRIPT_DIR/.permission_test" 2>/dev/null; then
    log_warn "⚠️  Permission issue detected in project directory"
    log_info "Some files may be owned by root due to Docker operations"
    log_info "To fix this, run: sudo ./scripts/fix_permissions.sh"
    log_info "Continuing with current permissions..."
else
    rm -f "$SCRIPT_DIR/.permission_test"
fi

# Handle reset flags first. They both imply a build.
if [[ " $@ " =~ " --reset " ]]; then
    confirm_destructive_action \
        "FULL RESET" \
        "   • All user accounts and passwords
   • All theme settings and preferences  
   • All uploaded documents and tasks
   • All chat history and conversations
   • All AI model downloads (several GB)
   • All vector embeddings and memory
   • All session data and login tokens
   • All monitoring/dashboard data
   • All SSL certificates" \
        ""
    
    log_info "Full reset confirmed. Tearing down the stack and removing all volumes..."
    docker compose --project-directory "$SCRIPT_DIR" down --volumes
    log_info "Stack has been fully reset."
    
    log_info "Running the setup script to rebuild images..."
    "$SCRIPT_DIR/scripts/_setup.sh"
    
    log_info "Copying latest README.md to WebUI static folder..."
    cp "$SCRIPT_DIR/README.md" "$SCRIPT_DIR/app/webui/static/" || log_warn "Failed to copy README.md (file may not exist)"

elif [[ " $@ " =~ " --soft-reset " ]]; then
    confirm_destructive_action \
        "SOFT RESET" \
        "   • All monitoring/dashboard data (Prometheus, Grafana)
   • All temporary build artifacts and caches" \
        "   • User accounts, passwords, and theme settings (database preserved)
   • Uploaded documents, tasks, and chat history (database preserved)
   • All AI model downloads (several GB saved)
   • Vector embeddings and semantic memory (Qdrant preserved)
   • Session data and login tokens (Redis preserved)
   • SSL certificates and secrets (preserved)"
    
    log_info "Soft reset confirmed. Tearing down the stack, preserving user data, AI models, certificates, and secrets..."
    docker compose --project-directory "$SCRIPT_DIR" down
    # Preserve critical data volumes: postgres_data (user settings), redis_data (sessions), qdrant_data (embeddings), ollama_data (AI models), certs (SSL certificates)
    docker volume ls -q | grep -v -E "(postgres_data|redis_data|qdrant_data|ollama_data|certs)" | xargs -r docker volume rm --force || true
    log_info "Application volumes removed. User data, cache, embeddings, AI models, certificates, and secrets preserved."

    log_info "Running soft setup to rebuild images without regenerating certificates/secrets..."
    "$SCRIPT_DIR/scripts/_setup_soft.sh"
    
    log_info "Copying latest README.md to WebUI static folder..."
    cp "$SCRIPT_DIR/README.md" "$SCRIPT_DIR/app/webui/static/" || log_warn "Failed to copy README.md (file may not exist)"
    
    log_info "Rebuilding WebUI with no cache to ensure UI changes take effect..."
    docker compose --project-directory "$SCRIPT_DIR" build --no-cache webui

# Handle the standalone build flag if no reset flag was present.
elif [[ " $@ " =~ " --build " ]]; then
    confirm_destructive_action \
        "BUILD/REBUILD" \
        "   • All running containers will be stopped and rebuilt
   • Temporary build caches may be cleared" \
        "   • All user data and settings
   • All AI models and downloads
   • All documents, tasks, and chat history
   • All vector embeddings and memory"
    
    log_info "Build confirmed. Running the setup script to rebuild images..."
    "$SCRIPT_DIR/scripts/_setup.sh"
    
    log_info "Copying latest README.md to WebUI static folder..."
    cp "$SCRIPT_DIR/README.md" "$SCRIPT_DIR/app/webui/static/" || log_warn "Failed to copy README.md (file may not exist)"
fi

# --- Step 1: Start all services ---
log_info "Starting all services..."
# The -d flag runs services in the background. Using --project-directory is more explicit and robust than using a subshell with cd.
docker compose --project-directory "$SCRIPT_DIR" up -d

# --- Step 2: Display status ---
log_success "✅ AI Workflow Engine services are up and running!"
docker compose --project-directory "$SCRIPT_DIR" ps -a

# --- Step 2.5: Background Docker system cleanup ---
log_info "🧹 Scheduling Docker system cleanup (will run in 30 seconds to allow services to stabilize)..."
(
    sleep 30
    log_info "Running Docker system prune to free up disk space..."
    
    # Get disk usage before cleanup
    before_cleanup=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || echo "Could not get disk usage")
    
    # Run system prune (excludes volumes to preserve data)
    docker system prune -f --filter "until=24h" >/dev/null 2>&1 || true
    
    # Get disk usage after cleanup  
    after_cleanup=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || echo "Could not get disk usage")
    
    # Log results to a cleanup log file
    {
        echo "=== Docker System Cleanup - $(date) ==="
        echo "Before cleanup:"
        echo "$before_cleanup"
        echo ""
        echo "After cleanup:"
        echo "$after_cleanup"
        echo ""
    } >> "$SCRIPT_DIR/logs/docker_cleanup.log"
    
    log_success "✅ Docker system cleanup completed. Check logs/docker_cleanup.log for details."
) &

# --- Step 3: Run post-startup fixes after everything is up ---
if [[ " $@ " =~ " --reset " ]] || [[ " $@ " =~ " --soft-reset " ]]; then
    log_info "🔧 Running post-startup fixes to resolve any non-fatal database authentication issues..."
    "$SCRIPT_DIR/scripts/post_startup_fixes.sh"
    log_success "✅ Post-startup fixes completed successfully!"
fi

log_info "Docker Watch has been disabled. You can monitor logs via the log files in the 'logs' directory."
log_info "For real-time structured errors, run: tail -f logs/runtime_errors.log"
log_info "For a periodic summary, run: cat logs/error_summary.log"
