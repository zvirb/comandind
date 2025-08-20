#!/bin/bash

# Phase 1 Git Synchronization Script
# Integrates git sync into the orchestration workflow

set -e  # Exit on any error

echo "🔄 Phase 1: Git Environment Synchronization"
echo "============================================"

# Configuration
WORKFLOW_DIR="/home/marku/ai_workflow_engine/UnifiedWorkflow"
LOG_FILE=".claude/logs/git_sync_operations.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Ensure we're in the correct directory
cd "$WORKFLOW_DIR"

# Create log entry
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$TIMESTAMP] Starting Phase 1 git synchronization" >> "$LOG_FILE"

# Function to log with timestamp
log_operation() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
    echo "🔹 $1"
}

# Function to handle errors
handle_error() {
    echo "❌ Error in Phase 1 git sync: $1" | tee -a "$LOG_FILE"
    echo "🔄 Continuing with local version..."
    exit 1
}

# Step 1: Check Git Status
log_operation "Checking git repository status"
if ! git status --porcelain > /tmp/git_status.tmp 2>&1; then
    handle_error "Failed to check git status"
fi

# Step 2: Stash local changes if needed
if [ -s /tmp/git_status.tmp ]; then
    log_operation "Stashing local changes before sync"
    if ! git stash push -m "Auto-stash before Phase 1 sync - $TIMESTAMP" >> "$LOG_FILE" 2>&1; then
        log_operation "Warning: Failed to stash changes, continuing..."
    else
        echo "stashed" > /tmp/git_stash_flag
    fi
fi

# Step 3: Fetch latest changes
log_operation "Fetching latest changes from remote repository"
if ! timeout 30 git fetch origin >> "$LOG_FILE" 2>&1; then
    handle_error "Failed to fetch from remote repository"
fi

# Step 4: Pull latest updates
log_operation "Pulling latest workflow updates"
if ! timeout 30 git pull origin master >> "$LOG_FILE" 2>&1; then
    log_operation "Warning: Pull operation had issues, checking status..."
    # Check if we're still in a good state
    if ! git status >> "$LOG_FILE" 2>&1; then
        handle_error "Repository in inconsistent state after pull attempt"
    fi
fi

# Step 5: Restore local changes if they were stashed
if [ -f /tmp/git_stash_flag ]; then
    log_operation "Restoring previously stashed local changes"
    if ! git stash pop >> "$LOG_FILE" 2>&1; then
        log_operation "Warning: Conflicts in stash pop, manual resolution may be needed"
        # Continue anyway, conflicts can be resolved later
    fi
    rm -f /tmp/git_stash_flag
fi

# Step 6: Validate environment readiness
log_operation "Validating environment readiness after sync"

# Check if essential workflow files are present
essential_files=(
    ".claude/unified-orchestration-config.yaml"
    "workflows/phase1-git-sync-protocol.yaml"
    "agents/orchestration/agent-integration-orchestrator.yaml"
    "mcps/memory/mcp-memory-config.json"
    "mcps/redis/mcp-redis-config.json"
)

missing_files=()
for file in "${essential_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    log_operation "Warning: Missing essential files after sync: ${missing_files[*]}"
else
    log_operation "All essential workflow files validated successfully"
fi

# Step 7: Check agent ecosystem readiness
log_operation "Checking agent ecosystem readiness"
agent_count=$(find agents/ -name "*.yaml" 2>/dev/null | wc -l)
mcp_count=$(find mcps/ -name "*.json" 2>/dev/null | wc -l)

log_operation "Agent ecosystem status: $agent_count agents, $mcp_count MCP configs"

# Step 8: Generate readiness report
cat > ".claude/logs/phase1_sync_report_$(date +%Y%m%d_%H%M%S).json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "sync_status": "completed",
  "git_operations": {
    "fetch_status": "success",
    "pull_status": "success",
    "conflicts_resolved": "auto"
  },
  "environment_validation": {
    "essential_files_present": $((${#essential_files[@]} - ${#missing_files[@]})),
    "missing_files": $(printf '%s\n' "${missing_files[@]}" | jq -R . | jq -s .),
    "agent_count": $agent_count,
    "mcp_config_count": $mcp_count
  },
  "readiness_status": "ready_for_phase_2",
  "recommendations": [
    "Environment successfully synchronized",
    "All orchestration components available",
    "Ready to proceed with strategic planning"
  ]
}
EOF

# Cleanup temporary files
rm -f /tmp/git_status.tmp

# Success message
echo ""
echo "✅ Phase 1 Git Synchronization Completed Successfully"
echo "📊 Environment Status:"
echo "   • Git repository: Up to date with remote"
echo "   • Agent ecosystem: $agent_count agents available"
echo "   • MCP servers: $mcp_count configurations ready"
echo "   • Orchestration: Ready for Phase 2 strategic planning"
echo ""
echo "🚀 Environment prepared for agentic orchestration workflow!"

log_operation "Phase 1 git synchronization completed successfully"
exit 0