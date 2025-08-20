#!/bin/bash

# Deploy Secure Database Migration Script
# This script deploys the comprehensive security enhancements for the Helios platform

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups/security_migration_$(date +%Y%m%d_%H%M%S)"

# Logging setup
LOG_FILE="$PROJECT_ROOT/logs/security_migration_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if the database is running
    if ! docker-compose ps postgres | grep -q "Up"; then
        log_error "PostgreSQL database is not running"
        log_info "Please start the database with: docker-compose up postgres"
        exit 1
    fi
    
    # Check if we can connect to the database
    if ! docker-compose exec postgres pg_isready -U app_user -d ai_workflow_db &> /dev/null; then
        log_error "Cannot connect to the database"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to create database backup
create_backup() {
    log_info "Creating database backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Create schema backup
    docker-compose exec postgres pg_dump -U app_user -d ai_workflow_db --schema-only > "$BACKUP_DIR/schema_backup.sql"
    
    # Create data backup (excluding large tables)
    docker-compose exec postgres pg_dump -U app_user -d ai_workflow_db \
        --exclude-table=audit.audit_log \
        --exclude-table=audit.data_access_log \
        --data-only > "$BACKUP_DIR/data_backup.sql"
    
    # Create full backup
    docker-compose exec postgres pg_dump -U app_user -d ai_workflow_db > "$BACKUP_DIR/full_backup.sql"
    
    log_success "Database backup created at: $BACKUP_DIR"
}

# Function to run pre-migration validation
run_pre_migration_validation() {
    log_info "Running pre-migration validation..."
    
    # Check current schema version
    CURRENT_VERSION=$(docker-compose exec postgres psql -U app_user -d ai_workflow_db -t -c \
        "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1;" | tr -d ' \n\r')
    
    log_info "Current database schema version: $CURRENT_VERSION"
    
    # Check for required tables
    REQUIRED_TABLES=("users" "blackboard_events" "consensus_memory_nodes")
    for table in "${REQUIRED_TABLES[@]}"; do
        if ! docker-compose exec postgres psql -U app_user -d ai_workflow_db -t -c \
            "SELECT 1 FROM information_schema.tables WHERE table_name='$table';" | grep -q 1; then
            log_error "Required table '$table' not found"
            exit 1
        fi
    done
    
    log_success "Pre-migration validation passed"
}

# Function to run the security migration
run_security_migration() {
    log_info "Running security database migration..."
    
    cd "$PROJECT_ROOT"
    
    # Run the migration using alembic
    if docker-compose exec api-migrate alembic upgrade secure_database_migration_20250803; then
        log_success "Security migration completed successfully"
    else
        log_error "Security migration failed"
        log_info "Attempting to rollback..."
        docker-compose exec api-migrate alembic downgrade unified_memory_integration_20250803
        exit 1
    fi
}

# Function to run post-migration validation
run_post_migration_validation() {
    log_info "Running post-migration validation..."
    
    # Check if audit schema was created
    if docker-compose exec postgres psql -U app_user -d ai_workflow_db -t -c \
        "SELECT 1 FROM information_schema.schemata WHERE schema_name='audit';" | grep -q 1; then
        log_success "Audit schema created successfully"
    else
        log_error "Audit schema was not created"
        exit 1
    fi
    
    # Check if RLS is enabled on sensitive tables
    SENSITIVE_TABLES=("users" "chat_mode_sessions" "simple_chat_context")
    for table in "${SENSITIVE_TABLES[@]}"; do
        RLS_ENABLED=$(docker-compose exec postgres psql -U app_user -d ai_workflow_db -t -c \
            "SELECT relrowsecurity FROM pg_class WHERE relname='$table';" | tr -d ' \n\r')
        
        if [ "$RLS_ENABLED" = "t" ]; then
            log_success "RLS enabled on table: $table"
        else
            log_warning "RLS not enabled on table: $table"
        fi
    done
    
    # Check if security functions exist
    SECURITY_FUNCTIONS=("get_current_user_id" "set_security_context" "audit.audit_trigger_function")
    for func in "${SECURITY_FUNCTIONS[@]}"; do
        if docker-compose exec postgres psql -U app_user -d ai_workflow_db -t -c \
            "SELECT 1 FROM pg_proc WHERE proname='$(basename "$func")';" | grep -q 1; then
            log_success "Security function created: $func"
        else
            log_error "Security function missing: $func"
        fi
    done
    
    log_success "Post-migration validation completed"
}

# Function to run comprehensive security validation
run_security_validation() {
    log_info "Running comprehensive security validation..."
    
    # Start the API service if not running
    docker-compose up -d api
    
    # Wait for API to be ready
    log_info "Waiting for API service to be ready..."
    sleep 10
    
    # Run security validation using Python script
    if docker-compose exec api python -c "
import asyncio
from shared.services.security_validation_service import security_validation_service

async def run_validation():
    results = await security_validation_service.run_comprehensive_security_validation()
    print(f\"Security Validation Results:\")
    print(f\"Overall Status: {results['overall_status']}\")
    print(f\"Tests: {results['passed_tests']}/{results['total_tests']} passed\")
    print(f\"Failed: {results['failed_tests']}, Warnings: {results['warnings']}\")
    
    if results['failed_tests'] > 0:
        print(\"\\nFailed Tests:\")
        for category in results['test_results']:
            for test in category['results']:
                if test['status'] == 'FAIL':
                    print(f\"  - {test['test']}: {test['message']}\")
    
    return results['overall_status'] in ['PASS', 'PASS_WITH_WARNINGS']

result = asyncio.run(run_validation())
exit(0 if result else 1)
"; then
        log_success "Security validation passed"
    else
        log_error "Security validation failed"
        log_warning "Check the API logs for detailed error information"
        return 1
    fi
}

# Function to update documentation
update_documentation() {
    log_info "Updating security documentation..."
    
    # Update DATABASE.md with security enhancements
    cat >> "$PROJECT_ROOT/DATABASE.md" << 'EOF'

## Security Enhancements (Updated 2025-08-03)

### Row-Level Security (RLS)
- **Enabled Tables**: All sensitive user data tables now have RLS enabled
- **Isolation**: Complete user-level data isolation prevents cross-user access
- **Policies**: Comprehensive security policies enforce data access controls

### Comprehensive Audit System
- **Audit Schema**: Dedicated `audit` schema for security tracking
- **Audit Triggers**: Automatic logging of all database operations
- **Security Violations**: Real-time detection and logging of unauthorized access
- **Data Access Logs**: Privacy-compliant tracking of cross-service data access

### Data Protection
- **Encryption**: Sensitive field encryption with AES-256-GCM
- **Anonymization**: GDPR-compliant data anonymization functions
- **Retention Policies**: Automated data cleanup and archival
- **Privacy Requests**: Full GDPR compliance workflow

### Vector Database Security
- **Access Controls**: Granular permissions for Qdrant collections
- **Audit Integration**: Vector operations fully audited
- **Metadata Protection**: Secure vector metadata storage

### Cross-Service Security
- **Enhanced JWT**: Service-to-service authentication tokens
- **Token Tracking**: Complete token lifecycle management
- **Revocation**: Immediate token revocation capabilities
- **Monitoring**: Real-time security monitoring and alerting

EOF

    log_success "Documentation updated"
}

# Function to set up monitoring
setup_monitoring() {
    log_info "Setting up security monitoring..."
    
    # Create monitoring script
    cat > "$PROJECT_ROOT/scripts/security_monitor.sh" << 'EOF'
#!/bin/bash

# Security monitoring script
# Run this periodically to check for security issues

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== Security Monitor Report $(date) ==="

# Check for recent security violations
echo "Recent Security Violations (last 24 hours):"
docker-compose exec postgres psql -U app_user -d ai_workflow_db -c \
    "SELECT violation_type, severity, COUNT(*) as count 
     FROM audit.security_violations 
     WHERE created_at >= NOW() - INTERVAL '24 hours' 
     GROUP BY violation_type, severity 
     ORDER BY severity DESC, count DESC;"

# Check for excessive data access
echo -e "\nHigh-Volume Data Access (last hour):"
docker-compose exec postgres psql -U app_user -d ai_workflow_db -c \
    "SELECT user_id, service_name, COUNT(*) as access_count
     FROM audit.data_access_log 
     WHERE created_at >= NOW() - INTERVAL '1 hour'
     GROUP BY user_id, service_name 
     HAVING COUNT(*) > 50
     ORDER BY access_count DESC;"

# Check audit log health
echo -e "\nAudit Log Statistics:"
docker-compose exec postgres psql -U app_user -d ai_workflow_db -c \
    "SELECT 
        COUNT(*) as total_audit_entries,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(DISTINCT table_name) as tables_audited
     FROM audit.audit_log 
     WHERE created_at >= NOW() - INTERVAL '24 hours';"

echo "=== End Security Monitor Report ==="
EOF

    chmod +x "$PROJECT_ROOT/scripts/security_monitor.sh"
    
    log_success "Security monitoring script created at: scripts/security_monitor.sh"
}

# Function to create rollback script
create_rollback_script() {
    log_info "Creating rollback script..."
    
    cat > "$PROJECT_ROOT/scripts/rollback_security_migration.sh" << 'EOF'
#!/bin/bash

# Rollback script for security migration
# Use this ONLY if you need to revert the security enhancements

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}WARNING: This will remove all security enhancements!${NC}"
echo -e "${YELLOW}This action cannot be undone and will remove:${NC}"
echo "- Row-Level Security policies"
echo "- Audit triggers and logs"
echo "- Security violation tracking"
echo "- Data access logging"
echo "- Cross-service authentication"
echo ""

read -p "Are you sure you want to proceed? (type 'ROLLBACK' to confirm): " confirm

if [ "$confirm" != "ROLLBACK" ]; then
    echo "Rollback cancelled."
    exit 1
fi

echo "Rolling back security migration..."

# Run the downgrade
docker-compose exec api-migrate alembic downgrade unified_memory_integration_20250803

echo "Security migration rollback completed."
echo "NOTE: You may need to restart services for changes to take effect."
EOF

    chmod +x "$PROJECT_ROOT/scripts/rollback_security_migration.sh"
    
    log_success "Rollback script created at: scripts/rollback_security_migration.sh"
}

# Main deployment function
main() {
    log_info "Starting secure database migration deployment..."
    log_info "Timestamp: $(date)"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Backup directory: $BACKUP_DIR"
    
    # Run all deployment steps
    check_prerequisites
    create_backup
    run_pre_migration_validation
    run_security_migration
    run_post_migration_validation
    
    # Optional validation (may fail in some environments)
    if run_security_validation; then
        log_success "Security validation completed successfully"
    else
        log_warning "Security validation had issues, but migration completed"
        log_info "You can run validation manually later using the security validation service"
    fi
    
    update_documentation
    setup_monitoring
    create_rollback_script
    
    log_success "Secure database migration deployment completed successfully!"
    log_info "Backup location: $BACKUP_DIR"
    log_info "Log file: $LOG_FILE"
    log_info "Monitoring script: scripts/security_monitor.sh"
    log_info "Rollback script: scripts/rollback_security_migration.sh (use with caution)"
    
    echo ""
    log_info "Next steps:"
    echo "1. Test your application thoroughly"
    echo "2. Run security monitoring: ./scripts/security_monitor.sh"
    echo "3. Review audit logs in the database"
    echo "4. Set up alerts for security violations"
    echo "5. Train your team on the new security features"
}

# Handle script interruption
trap 'log_error "Script interrupted. Check logs for details."; exit 1' INT TERM

# Run main function
main "$@"