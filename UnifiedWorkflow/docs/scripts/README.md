# Scripts & Automation

Documentation for all scripts, automation tools, and utilities in the AI Workflow Engine project.

## 🛠️ Scripts Overview

The AI Workflow Engine includes comprehensive automation scripts for:
- **Security Setup**: mTLS infrastructure and certificate management
- **Database Operations**: Migrations, backups, and maintenance
- **Deployment**: Automated deployment and validation scripts
- **Testing**: Test automation and validation scripts
- **Maintenance**: System maintenance and cleanup utilities

## 📋 Script Categories

### [📊 Script Overview](overview.md)
Complete inventory of all available scripts:
- Script directory structure
- Usage conventions and patterns
- Common parameters and options
- Script dependencies and requirements

### [🔒 Security Scripts](security.md)
Security-related automation scripts:
- mTLS infrastructure setup
- Certificate generation and rotation
- Security validation and testing
- Vulnerability scanning automation

### [🗄️ Database Scripts](database.md)
Database management and automation:
- Migration generation and execution
- Database backup and restore
- Performance optimization scripts
- Data validation and cleanup

### [🚀 Deployment Scripts](deployment.md)
Deployment automation and validation:
- Environment deployment scripts
- Configuration validation
- Health check automation
- Rollback procedures

## 📂 Script Directory Structure

```
scripts/
├── security/                    # Security automation
│   ├── setup_mtls_infrastructure.sh
│   ├── generate_certificates.sh
│   ├── rotate_certificates.sh
│   └── validate_security.sh
├── database/                    # Database operations
│   ├── _generate_migration.sh
│   ├── backup_database.sh
│   ├── restore_database.sh
│   └── maintenance.sh
├── deployment/                  # Deployment automation
│   ├── deploy_security_enhancements.sh
│   ├── deploy_ssl_fixes.sh
│   ├── validate_deployment.sh
│   └── rollback.sh
├── testing/                     # Test automation
│   ├── run_tests.sh
│   ├── test_auth_flow.sh
│   ├── test_webui_ssl.py
│   └── validate_ssl_fix.py
├── maintenance/                 # System maintenance
│   ├── cleanup.sh
│   ├── log_rotation.sh
│   └── health_check.sh
└── utilities/                   # General utilities
    ├── environment_setup.sh
    ├── configuration_check.sh
    └── system_info.sh
```

## 🚨 Critical Security Scripts

### **mTLS Infrastructure Setup** (MANDATORY)
```bash
# Setup complete mTLS infrastructure
./scripts/security/setup_mtls_infrastructure.sh setup

# Regenerate certificates
./scripts/security/setup_mtls_infrastructure.sh regenerate

# Validate security configuration
./scripts/security/setup_mtls_infrastructure.sh validate
```

### **Certificate Management**
```bash
# Generate development certificates
./scripts/generate_dev_certificates.sh

# Validate SSL configuration
./scripts/validate_ssl_configuration.sh

# Emergency certificate renewal
./scripts/security/emergency_cert_renewal.sh
```

## 🗄️ Database Management Scripts

### **Migration Management**
```bash
# Generate new migration (REQUIRED after model changes)
./scripts/database/_generate_migration.sh "description of changes"

# Apply migrations
./scripts/database/apply_migrations.sh

# Rollback migration
./scripts/database/rollback_migration.sh
```

### **Database Maintenance**
```bash
# Backup database
./scripts/database/backup_database.sh

# Restore from backup
./scripts/database/restore_database.sh backup_file.sql

# Database cleanup and optimization
./scripts/database/maintenance.sh
```

## 🚀 Deployment Scripts

### **Environment Deployment**
```bash
# Deploy security enhancements
./scripts/deploy_security_enhancements.sh

# Deploy SSL fixes
./scripts/deploy_ssl_fixes.sh

# Deploy performance optimizations
./scripts/deploy_performance_optimizations.sh
```

### **Validation Scripts**
```bash
# Validate complete deployment
./scripts/validate_deployment.sh

# Validate SSL configuration
./scripts/validate_ssl_configuration.sh

# Health check validation
./scripts/health_check.sh
```

## 🧪 Testing Scripts

### **Authentication Testing**
```bash
# Test complete authentication flow
./scripts/test_auth_flow.sh

# Test WebUI authentication
python scripts/test_webui_ssl.py

# Validate authentication fixes
python validate_auth_fixes.py
```

### **Integration Testing**
```bash
# Run complete test suite
./scripts/testing/run_tests.sh

# Test WebUI with Playwright
python scripts/test_webui_playwright.py

# Performance testing
./scripts/testing/performance_test.sh
```

## 🔧 Utility Scripts

### **Environment Management**
```bash
# Setup development environment
./scripts/utilities/environment_setup.sh

# Check system configuration
./scripts/utilities/configuration_check.sh

# Display system information
./scripts/utilities/system_info.sh
```

### **MCP Server Management**
```bash
# Start MCP Redis server
./scripts/mcp-redis-start.sh

# Stop MCP Redis server
./scripts/mcp-redis-stop.sh

# MCP session management
./scripts/mcp-session-manager.sh
```

## 📋 Script Usage Conventions

### **Standard Parameters**
Most scripts support these common parameters:
- `--help` or `-h`: Display help information
- `--verbose` or `-v`: Enable verbose output
- `--dry-run`: Show what would be done without executing
- `--force`: Force execution without prompts
- `--quiet` or `-q`: Suppress non-essential output

### **Script Execution Pattern**
```bash
# Make script executable (if needed)
chmod +x scripts/script_name.sh

# Run with proper permissions
./scripts/script_name.sh [options] [arguments]

# Check exit code
echo $?  # 0 = success, non-zero = error
```

### **Environment Variables**
Scripts respect these environment variables:
```bash
export ENVIRONMENT=development|staging|production
export DOCKER_COMPOSE_FILE=docker-compose-mtls.yml
export BACKUP_DIR=/path/to/backups
export LOG_LEVEL=DEBUG|INFO|WARN|ERROR
```

## 🔒 Security Script Requirements

### **Mandatory Security Setup**
Before running the application, you MUST run:
```bash
./scripts/security/setup_mtls_infrastructure.sh setup
```

### **Development Environment**
For development, ALWAYS use:
```bash
docker-compose -f docker-compose-mtls.yml up
```

### **Certificate Validation**
Regularly validate certificates:
```bash
./scripts/validate_ssl_configuration.sh
```

## 📊 Script Monitoring & Logging

### **Script Logging**
All scripts generate logs in `/logs/scripts/`:
```bash
# View script logs
ls -la logs/scripts/
tail -f logs/scripts/security_setup.log
```

### **Error Handling**
Scripts implement consistent error handling:
- Exit codes indicate success (0) or failure (non-zero)
- Error messages written to stderr
- Critical errors logged to system logs
- Rollback procedures for failed operations

### **Script Validation**
```bash
# Test script syntax
bash -n scripts/script_name.sh

# Run shellcheck (if available)
shellcheck scripts/script_name.sh

# Test script execution (dry run)
./scripts/script_name.sh --dry-run
```

## 🔄 Automation Integration

### **CI/CD Integration**
Scripts are integrated into CI/CD pipelines:
```yaml
# GitHub Actions example
- name: Setup Security Infrastructure
  run: ./scripts/security/setup_mtls_infrastructure.sh setup

- name: Run Tests
  run: ./scripts/testing/run_tests.sh

- name: Deploy Application
  run: ./scripts/deployment/deploy.sh
```

### **Cron Jobs**
Automated maintenance scripts:
```bash
# Daily database backup
0 2 * * * /path/to/project/scripts/database/backup_database.sh

# Weekly certificate check
0 1 * * 1 /path/to/project/scripts/security/check_certificates.sh

# Monthly cleanup
0 3 1 * * /path/to/project/scripts/maintenance/cleanup.sh
```

## 🔗 Related Documentation

- [Security Implementation](../security/overview.md)
- [Development Environment](../development/environment-setup.md)
- [Infrastructure Deployment](../infrastructure/deployment.md)
- [Testing Procedures](../testing/best-practices.md)
- [Troubleshooting Scripts](../troubleshooting/common-issues.md)

---

**⚠️ Security Reminder**: Always run the security setup script before starting development as mandated in [CLAUDE.md](../../CLAUDE.md).