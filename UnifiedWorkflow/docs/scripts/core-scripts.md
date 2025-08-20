# Core Scripts Documentation

Core scripts are the main entry points and essential system scripts that control the overall application lifecycle. These are the primary interfaces developers use to interact with the AI Workflow Engine.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `run.sh` | Main application launcher | `./run.sh [options]` |
| `scripts/_common_functions.sh` | Shared utility functions | Sourced by other scripts |
| `install.sh` | System installation script | `./install.sh` |

---

## run.sh

**Location:** `/run.sh`  
**Purpose:** Primary entrypoint for starting the AI Workflow Engine services with various reset and build options.

### Description
The main application launcher that handles service startup, environment resets, and build operations. It provides different reset levels to balance between clean environments and preserving valuable data.

### Usage
```bash
./run.sh [OPTIONS]
```

### Options
- `--reset` - Full system reset (removes ALL data including user accounts, AI models)
- `--soft-reset` - Preserves user data, AI models, certificates, and secrets
- `--build` - Rebuild Docker images without reset
- `--no-cache` - Disable Docker build cache

### Examples
```bash
# Start application normally
./run.sh

# Soft reset (recommended for development)
./run.sh --soft-reset

# Full reset (use with caution)
./run.sh --reset

# Rebuild images only
./run.sh --build

# Fresh build without cache
./run.sh --build --no-cache
```

### Reset Comparison

| Operation | Full Reset | Soft Reset | Build Only |
|-----------|------------|------------|------------|
| User accounts | ❌ Removed | ✅ Preserved | ✅ Preserved |
| AI models | ❌ Removed | ✅ Preserved | ✅ Preserved |
| Chat history | ❌ Removed | ✅ Preserved | ✅ Preserved |
| Certificates | ❌ Removed | ✅ Preserved | ✅ Preserved |
| Docker images | ❌ Rebuilt | ❌ Rebuilt | ❌ Rebuilt |
| Build cache | ❌ Cleared | ✅ Used | ✅ Used |

### Prerequisites
- Docker and Docker Compose installed
- Project properly set up with `scripts/_setup.sh`
- Sufficient disk space for Docker operations

### What It Does
1. **Validation:** Checks Docker installation and permissions
2. **Reset Operations:** Performs requested reset level
3. **Image Management:** Rebuilds Docker images if needed
4. **Service Startup:** Starts all services with `docker compose up -d`
5. **Post-Setup:** Runs post-startup fixes and cleanup
6. **Monitoring:** Provides status and log information

### Error Handling
- Comprehensive error logging to `logs/error_log.txt`
- Automatic cleanup on failures
- User confirmation for destructive operations
- Detailed progress reporting

### Troubleshooting
- **"Permission denied"**: Run `sudo ./scripts/fix_permissions.sh`
- **"Docker not found"**: Install Docker and Docker Compose
- **"Services failed to start"**: Check `logs/error_log.txt` for details
- **"Out of disk space"**: Clean up Docker with `docker system prune`

---

## scripts/_common_functions.sh

**Location:** `/scripts/_common_functions.sh`  
**Purpose:** Provides shared utility functions used across all scripts in the project.

### Description
A library of common functions that standardizes logging, error handling, and utility operations across all scripts. This ensures consistent behavior and reduces code duplication.

### Key Functions

#### Logging Functions
```bash
log_info "Information message"     # Blue info messages
log_success "Success message"      # Green success messages  
log_warn "Warning message"         # Yellow warning messages
log_error "Error message"          # Red error messages
log_debug "Debug message"          # Cyan debug messages
```

#### Utility Functions
```bash
check_command "docker"             # Verify command availability
select_profile                     # GPU profile selection (hardcoded to gpu-nvidia)
nuke_and_pave                     # Complete system wipe
```

#### Error Logging Functions
```bash
log_build_failure "service" "log_file"      # Log Docker build failures
log_container_failure "service" "deps"      # Log container runtime failures
_trigger_gemini_assistant                   # Trigger AI diagnostics
```

### Usage
```bash
# Source in other scripts
source "$(dirname "$0")/_common_functions.sh"

# Use logging functions
log_info "Starting operation..."
log_success "Operation completed!"
```

### Features
- **Colored Output:** Different colors for different log levels
- **Error Tracking:** Detailed failure logging with context
- **Command Validation:** Ensures required tools are available
- **AI Integration:** Automatic diagnostic assistance on errors

---

## install.sh

**Location:** `/install.sh`  
**Purpose:** System-level installation script for setting up the AI Workflow Engine on a new system.

### Description
Handles the initial installation of the AI Workflow Engine, including system dependencies, Docker setup, and initial configuration.

### Usage
```bash
./install.sh
```

### What It Does
1. **System Check:** Verifies OS compatibility
2. **Dependencies:** Installs required system packages
3. **Docker Setup:** Installs and configures Docker
4. **Project Setup:** Initializes project structure
5. **Permissions:** Sets up correct file permissions
6. **Validation:** Verifies installation success

### Prerequisites
- Ubuntu/Debian-based system (primary support)
- Sudo access for system package installation
- Internet connection for downloading dependencies

### Troubleshooting
- **"Package not found"**: Update system package lists
- **"Permission denied"**: Ensure sudo access
- **"Docker installation failed"**: Check system compatibility

---

## Common Patterns

### Error Handling
All core scripts implement:
- Exit on error (`set -e`)
- Comprehensive logging
- User confirmations for destructive operations
- Automatic cleanup on failures

### Logging Standards
- Consistent color coding across all scripts
- Structured error messages with context
- Automatic log file generation
- Integration with monitoring systems

### User Experience
- Clear progress indicators
- Helpful error messages with suggested solutions
- Confirmation prompts for dangerous operations
- Comprehensive status reporting

---

*For detailed workflow examples, see the [Development Workflow](./workflows/development.md) guide.*