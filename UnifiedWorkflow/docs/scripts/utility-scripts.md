# Utility Scripts Documentation

Utility scripts provide maintenance, cleanup, and helper functionality for the AI Workflow Engine. These scripts handle routine operations, system maintenance, and developer utilities.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `fix_permissions.sh` | Fix file permission issues | `sudo ./scripts/fix_permissions.sh` |
| `auto_update.sh` | Automatic system updates | `./scripts/auto_update.sh` |
| `post_startup_fixes.sh` | Post-startup issue resolution | `./scripts/post_startup_fixes.sh` |
| `debug_worker_env.sh` | Worker environment debugging | `./scripts/debug_worker_env.sh` |
| `diagnose_worker.sh` | Worker diagnostic tool | `./scripts/diagnose_worker.sh` |
| `fix_worker_database.sh` | Worker database fixes | `./scripts/fix_worker_database.sh` |
| `fix_worker_healthcheck.sh` | Worker health check fixes | `./scripts/fix_worker_healthcheck.sh` |
| `worker_universal_fix.sh` | Universal worker problem solver | `./scripts/worker_universal_fix.sh` |
| `test_worker_healthcheck.sh` | Worker health test | `./scripts/test_worker_healthcheck.sh` |
| `pull_models_if_needed.sh` | AI model management | `./scripts/pull_models_if_needed.sh` |
| `_dev_restart.sh` | Development restart utility | `./scripts/_dev_restart.sh` |
| `_start_services.sh` | Service startup coordinator | `./scripts/_start_services.sh` |
| `_start_services_with_retry.sh` | Resilient service startup | `./scripts/_start_services_with_retry.sh` |
| `_docker_watch.sh` | Docker event monitoring | `./scripts/_docker_watch.sh` |
| `_watch_events.sh` | System event monitoring | `./scripts/_watch_events.sh` |

---

## scripts/fix_permissions.sh

**Location:** `/scripts/fix_permissions.sh`  
**Purpose:** Comprehensive file permission repair for Docker-related issues.

### Description
Fixes common permission problems caused by Docker operations, including files owned by root, incorrect permissions, and access issues that prevent normal operation.

### Usage
```bash
sudo ./scripts/fix_permissions.sh
```

### What It Fixes
```bash
# Ownership Issues
- Files owned by root due to Docker operations
- Incorrect group ownership
- Mixed ownership across project files

# Permission Issues  
- Non-executable script files
- Overly restrictive directory permissions
- Incorrect file permissions (644 for files, 755 for directories)
- Secrets with insufficient security (600 for sensitive files)

# Specific Targets
- scripts/ directory and all .sh files
- docker/ configuration directory
- config/ application configuration
- app/ application source code
- logs/ directory for log files
- secrets/ directory with secure permissions (700/600)
```

### Process
```bash
# Target user determination
TARGET_USER="${SUDO_USER:-$(whoami)}"
TARGET_GROUP=$(id -gn "$TARGET_USER")

# Permission fixing process
1. Change ownership to target user:group
2. Set directory permissions to 755
3. Set file permissions to 644  
4. Make .sh scripts executable (755)
5. Secure secrets directory (700 for dir, 600 for files)
6. Fix any root-owned files
7. Restore executable permissions where needed
```

### Output
```
🔧 Fixing File Permissions
==========================
Target user: username
Target group: usergroup
Project root: /home/user/ai_workflow_engine

Fixing scripts directory...
✅ Fixed scripts directory

Fixing docker directory...
✅ Fixed docker directory

Setting restrictive permissions for secrets directory...
✅ Secrets directory permissions secured

🎯 Permission fix complete!

You should now be able to run scripts without sudo:
  ./run.sh
  ./scripts/worker_universal_fix.sh
  ./scripts/_setup_secrets_and_certs.sh
```

### When to Use
- After cloning the repository
- When encountering "Permission denied" errors
- After Docker operations that change file ownership
- Before running any scripts for the first time
- In CI/CD pipelines to ensure correct permissions

---

## scripts/auto_update.sh

**Location:** `/scripts/auto_update.sh`  
**Purpose:** Automated system and dependency updates.

### Description
Performs automated updates of system components, Docker images, and application dependencies with safety checks and rollback capabilities.

### Usage
```bash
./scripts/auto_update.sh [OPTIONS]
```

### Update Components
- **Docker Images:** Updates base images and application images
- **System Packages:** Updates OS packages (with approval)
- **Python Dependencies:** Updates Python packages via poetry
- **Security Updates:** Priority updates for security patches
- **Configuration:** Updates configuration templates

### Safety Features
- **Backup Creation:** Automatic backups before updates
- **Rollback Capability:** Can rollback failed updates
- **Testing:** Validates updates before applying
- **Approval Required:** Interactive approval for major changes

---

## scripts/post_startup_fixes.sh

**Location:** `/scripts/post_startup_fixes.sh`  
**Purpose:** Resolves common post-startup issues and performs initialization tasks.

### Description
Runs after service startup to fix non-fatal issues, optimize configurations, and ensure all services are properly initialized.

### What It Fixes
```bash
# Database Issues
- Authentication connection issues
- Migration inconsistencies  
- User role assignments
- Connection pool optimization

# Service Configuration
- Service discovery problems
- Network connectivity issues
- Certificate validation problems
- Cache initialization

# Performance Optimization
- Resource allocation adjustments
- Connection pool tuning
- Cache warming
- Index optimization
```

### Process
1. **Service Health Check:** Verifies all services are responding
2. **Database Fixes:** Resolves authentication and connection issues  
3. **Network Fixes:** Ensures proper inter-service communication
4. **Cache Initialization:** Warms up caches and connection pools
5. **Performance Tuning:** Applies performance optimizations
6. **Validation:** Confirms all fixes were successful

### Integration
- Automatically called by `run.sh` after reset operations
- Can be run manually for troubleshooting
- Integrated with monitoring for proactive fixes

---

## Worker Management Scripts

### scripts/debug_worker_env.sh
**Purpose:** Debug worker service environment and configuration.

**Capabilities:**
- Environment variable inspection
- Service dependency analysis
- Network connectivity testing
- Resource availability checking

### scripts/diagnose_worker.sh
**Purpose:** Comprehensive worker service diagnostics.

**Features:**
- Health status analysis
- Performance metrics collection
- Error log analysis
- Resource usage evaluation

### scripts/fix_worker_database.sh
**Purpose:** Resolve worker-specific database connection issues.

**What It Fixes:**
- Database connection configuration
- Authentication credential issues
- Connection pool problems
- SSL/TLS certificate issues

### scripts/fix_worker_healthcheck.sh
**Purpose:** Fix worker health check failures.

**Solutions:**
- Health check endpoint configuration
- Timeout adjustments
- Dependency validation
- Service registration fixes

### scripts/worker_universal_fix.sh
**Purpose:** Universal problem solver for worker service issues.

**Description:**
Comprehensive script that attempts to resolve any worker-related issues through a systematic approach.

**Process:**
1. **Diagnostic Phase:** Identifies specific worker problems
2. **Environment Fixes:** Resolves environment and configuration issues
3. **Service Fixes:** Addresses service-specific problems
4. **Network Fixes:** Resolves connectivity and communication issues
5. **Database Fixes:** Handles database-related problems
6. **Validation:** Confirms all fixes were successful

**Usage:**
```bash
./scripts/worker_universal_fix.sh
```

### scripts/test_worker_healthcheck.sh
**Purpose:** Test and validate worker health check functionality.

**Testing:**
- Health endpoint availability
- Response time validation
- Dependency status verification
- Error condition handling

---

## Service Management Scripts

### scripts/_dev_restart.sh
**Purpose:** Development-friendly service restart with optimization.

**Features:**
- Selective service restart
- Development optimizations
- Fast restart without full rebuild
- Preservation of development state

### scripts/_start_services.sh
**Purpose:** Coordinated service startup with dependency management.

**Capabilities:**
- Dependency-aware startup order
- Service health validation
- Startup optimization
- Error handling and recovery

### scripts/_start_services_with_retry.sh
**Purpose:** Resilient service startup with retry logic.

**Features:**
- Automatic retry on failure
- Exponential backoff
- Service dependency validation
- Comprehensive error logging

**Process:**
```bash
# Retry configuration
MAX_RETRIES=3
RETRY_DELAY=5
BACKOFF_MULTIPLIER=2

# Retry logic
for attempt in $(seq 1 $MAX_RETRIES); do
    if start_service "$service"; then
        log_success "Service $service started successfully"
        break
    else
        delay=$((RETRY_DELAY * BACKOFF_MULTIPLIER ** (attempt - 1)))
        log_warn "Service $service failed to start, retrying in ${delay}s (attempt $attempt/$MAX_RETRIES)"
        sleep $delay
    fi
done
```

---

## Model Management Scripts

### scripts/pull_models_if_needed.sh
**Purpose:** Intelligent AI model download and management.

**Description:**
Manages AI model downloads, updates, and storage optimization for the Ollama service.

**Features:**
- **Conditional Downloads:** Only downloads missing models
- **Storage Management:** Optimizes disk usage
- **Version Management:** Handles model versioning
- **Progress Tracking:** Shows download progress
- **Error Recovery:** Handles failed downloads

**Usage:**
```bash
./scripts/pull_models_if_needed.sh [MODEL_NAME]
```

**Model Management:**
```bash
# Check required models
REQUIRED_MODELS=("llama2:7b" "codellama:7b" "mistral:7b")

# Download logic
for model in "${REQUIRED_MODELS[@]}"; do
    if ! ollama list | grep -q "$model"; then
        log_info "Downloading model: $model"
        ollama pull "$model"
    else
        log_info "Model already available: $model"
    fi
done
```

---

## Monitoring and Event Scripts

### scripts/_docker_watch.sh
**Purpose:** Real-time Docker event monitoring and response.

**Capabilities:**
- Container lifecycle monitoring
- Image update detection
- Volume and network events
- Automatic response to events

**Event Types:**
```bash
# Container events
- start, stop, restart, kill
- die, oom (out of memory)
- health_status changes

# Image events  
- pull, push, delete
- build completion
- layer updates

# Volume events
- create, mount, unmount
- destroy, prune

# Network events
- create, connect, disconnect
- destroy, prune
```

### scripts/_watch_events.sh
**Purpose:** System-wide event monitoring and logging.

**Features:**
- Multi-source event aggregation
- Event filtering and categorization
- Real-time alerting
- Historical event tracking

---

## Development Utilities

### Development Workflow Scripts
These scripts optimize the development experience:

```bash
# Quick development restart
./scripts/_dev_restart.sh

# Start services with development optimizations  
./scripts/_start_services.sh --dev-mode

# Monitor development changes
./scripts/_watch_events.sh --dev-filter
```

### Debugging Utilities
For troubleshooting and diagnostics:

```bash
# Debug worker environment
./scripts/debug_worker_env.sh

# Comprehensive worker diagnosis
./scripts/diagnose_worker.sh

# Universal worker fixes
./scripts/worker_universal_fix.sh
```

### Maintenance Operations
For regular maintenance tasks:

```bash
# Fix permissions after Docker operations
sudo ./scripts/fix_permissions.sh

# Apply post-startup fixes
./scripts/post_startup_fixes.sh

# Update system components
./scripts/auto_update.sh
```

---

## Common Utility Patterns

### Error Handling Pattern
```bash
# Standard error handling
set -e
trap cleanup EXIT

cleanup() {
    # Cleanup operations
    log_info "Cleaning up..."
}

# Operation with error handling
if ! operation_command; then
    log_error "Operation failed"
    exit 1
fi
```

### Retry Pattern
```bash
# Retry with exponential backoff
retry_with_backoff() {
    local cmd="$1"
    local max_attempts="$2"
    local delay="$3"
    
    for attempt in $(seq 1 $max_attempts); do
        if eval "$cmd"; then
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            sleep $((delay * 2**(attempt-1)))
        fi
    done
    
    return 1
}
```

### Service Health Check Pattern
```bash
# Health check with timeout
wait_for_service() {
    local service="$1"
    local timeout="${2:-120}"
    local interval="${3:-5}"
    
    for ((i=0; i<timeout; i+=interval)); do
        if docker compose ps "$service" | grep -q "healthy"; then
            return 0
        fi
        sleep $interval
    done
    
    return 1
}
```

---

## Best Practices

### Permission Management
1. **Principle of Least Privilege:** Only grant necessary permissions
2. **Secure Secrets:** Use restrictive permissions (600/700) for sensitive files
3. **Regular Fixes:** Run permission fixes after Docker operations
4. **User Awareness:** Understand when sudo is required vs. regular user

### Service Management
1. **Dependency Awareness:** Start services in correct dependency order
2. **Health Validation:** Always validate service health after startup
3. **Retry Logic:** Implement appropriate retry mechanisms
4. **Resource Management:** Monitor and manage resource usage

### Development Efficiency
1. **Selective Restarts:** Only restart services that need updates
2. **Development Modes:** Use development-specific optimizations
3. **Quick Diagnostics:** Use targeted diagnostic tools
4. **Automation:** Automate repetitive maintenance tasks

### Maintenance Strategy
1. **Proactive Fixes:** Address issues before they become problems
2. **Regular Updates:** Keep systems and dependencies updated
3. **Monitoring Integration:** Integrate utilities with monitoring systems
4. **Documentation:** Document utility usage and troubleshooting steps

---

*For specific troubleshooting scenarios, see the [Troubleshooting Guide](./workflows/troubleshooting.md).*