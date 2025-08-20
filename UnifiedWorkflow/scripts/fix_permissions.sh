#!/bin/bash
# scripts/fix_permissions.sh
# Fix file permissions issues caused by Docker operations
# This script should be run with sudo to fix ownership issues

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

# Get the user who should own the files (the user who originally cloned the repo)
if [ -n "$SUDO_USER" ]; then
    # If running with sudo, use the original user
    TARGET_USER="$SUDO_USER"
    TARGET_GROUP=$(id -gn "$SUDO_USER")
else
    # If not running with sudo, use current user
    TARGET_USER=$(whoami)
    TARGET_GROUP=$(id -gn)
fi

echo "🔧 Fixing File Permissions"
echo "=========================="
echo "Target user: $TARGET_USER"
echo "Target group: $TARGET_GROUP"
echo "Project root: $PROJECT_ROOT"
echo ""

# Function to fix ownership and permissions
fix_permissions() {
    local path="$1"
    local description="$2"
    
    if [ -e "$path" ]; then
        echo "Fixing $description..."
        
        # Change ownership to the target user
        chown -R "$TARGET_USER:$TARGET_GROUP" "$path"
        
        # Set appropriate permissions
        find "$path" -type f -name "*.sh" -exec chmod 755 {} \;  # Make scripts executable
        find "$path" -type f ! -name "*.sh" -exec chmod 644 {} \;  # Regular files
        find "$path" -type d -exec chmod 755 {} \;  # Directories
        
        echo "✅ Fixed $description"
    else
        echo "⚠️  $path does not exist, skipping"
    fi
    echo ""
}

# Fix common directories that get affected by Docker operations
fix_permissions "$PROJECT_ROOT/scripts" "scripts directory"
fix_permissions "$PROJECT_ROOT/docker" "docker directory"
fix_permissions "$PROJECT_ROOT/config" "config directory"
fix_permissions "$PROJECT_ROOT/app" "app directory"
fix_permissions "$PROJECT_ROOT/logs" "logs directory"
fix_permissions "$PROJECT_ROOT/secrets" "secrets directory"
fix_permissions "$PROJECT_ROOT/docs" "docs directory"

# Fix specific files that commonly get wrong permissions
fix_permissions "$PROJECT_ROOT/run.sh" "main run script"
fix_permissions "$PROJECT_ROOT/docker-compose.yml" "docker-compose file"
fix_permissions "$PROJECT_ROOT/.env" "environment file"
fix_permissions "$PROJECT_ROOT/local.env" "local environment file"

# Special handling for secrets directory - should be more restrictive
if [ -d "$PROJECT_ROOT/secrets" ]; then
    echo "Setting restrictive permissions for secrets directory..."
    chown -R "$TARGET_USER:$TARGET_GROUP" "$PROJECT_ROOT/secrets"
    chmod 700 "$PROJECT_ROOT/secrets"  # Directory accessible only to owner
    find "$PROJECT_ROOT/secrets" -type f -exec chmod 600 {} \;  # Files readable only by owner
    echo "✅ Secrets directory permissions secured"
    echo ""
fi

# Fix any files that might have been created by Docker volumes
if [ -d "$PROJECT_ROOT" ]; then
    echo "Fixing any remaining permission issues..."
    
    # Find and fix files owned by root (common issue with Docker)
    find "$PROJECT_ROOT" -user root -exec chown "$TARGET_USER:$TARGET_GROUP" {} \; 2>/dev/null || true
    
    # Fix any files with overly restrictive permissions
    find "$PROJECT_ROOT" -type f -perm 000 -exec chmod 644 {} \; 2>/dev/null || true
    find "$PROJECT_ROOT" -type d -perm 000 -exec chmod 755 {} \; 2>/dev/null || true
    
    echo "✅ Fixed remaining permission issues"
    echo ""
fi

echo "🎯 Permission fix complete!"
echo ""
echo "You should now be able to run scripts without sudo:"
echo "  ./run.sh"
echo "  ./scripts/worker_universal_fix.sh"
echo "  ./scripts/_setup_secrets_and_certs.sh"
echo ""
echo "If you still encounter permission issues, you may need to:"
echo "1. Check if any Docker volumes are mounted with incorrect permissions"
echo "2. Ensure your user is in the 'docker' group: sudo usermod -aG docker $TARGET_USER"
echo "3. Log out and log back in for group changes to take effect"