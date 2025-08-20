# Setup Scripts Documentation

Setup scripts are responsible for initial environment configuration, dependency management, and service preparation. These scripts prepare the system for running the AI Workflow Engine.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `_setup.sh` | Complete environment setup | `./scripts/_setup.sh [options]` |
| `_setup_soft.sh` | Soft setup without certificates | `./scripts/_setup_soft.sh` |
| `_setup_secrets_and_certs.sh` | Generate secrets and certificates | `./scripts/_setup_secrets_and_certs.sh` |
| `_setup_server.sh` | Server-specific setup | `./scripts/_setup_server.sh` |
| `_setup_client_access.sh` | Client access configuration | `./scripts/_setup_client_access.sh` |
| `_setup_remote_access.sh` | Remote access setup | `./scripts/_setup_remote_access.sh` |
| `_make_scripts_executable.sh` | Fix script permissions | `./scripts/_make_scripts_executable.sh` |
| `lock_dependencies.sh` | Lock Python dependencies | `./scripts/lock_dependencies.sh` |

---

## scripts/_setup.sh

**Location:** `/scripts/_setup.sh`  
**Purpose:** Comprehensive setup script that handles dependency checks, secret generation, Docker builds, and service startup preparation.

### Description
The main setup script that orchestrates the complete environment preparation. It ensures all dependencies are installed, secrets are generated, certificates are created, and Docker images are built.

### Usage
```bash
./scripts/_setup.sh [OPTIONS]
```

### Options
- `--full-teardown` - Removes all containers and volumes before setup
- `--no-cache` - Disables Docker build cache for fresh builds

### Examples
```bash
# Standard setup
./scripts/_setup.sh

# Fresh setup with teardown
./scripts/_setup.sh --full-teardown

# Setup without build cache
./scripts/_setup.sh --no-cache

# Complete clean setup
./scripts/_setup.sh --full-teardown --no-cache
```

### What It Does
1. **Permission Setup:** Makes all scripts executable
2. **Teardown (optional):** Removes existing containers and volumes
3. **Secrets & Certificates:** Generates required security materials
4. **Dependency Check:** Validates poetry.lock consistency
5. **Docker Build:** Builds all Docker images with appropriate caching
6. **Validation:** Confirms successful setup completion

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ available for dependency checks
- Sufficient disk space for Docker images
- Write permissions in project directory

### Output
```
INFO: Starting AI Workflow Engine setup...
SUCCESS: ✅ All scripts are now executable.
INFO: Setting up secrets and certificates...
SUCCESS: ✅ Secrets and certificates setup complete.
INFO: Checking if poetry.lock is consistent with pyproject.toml...
SUCCESS: ✅ poetry.lock is consistent with pyproject.toml.
INFO: Building all Docker images. This may take some time on the first run...
SUCCESS: ✅ Setup complete. Docker images are built.
INFO: You can now start the application by running './run.sh'.
```

### Troubleshooting
- **"Permission denied"**: Run `sudo ./scripts/fix_permissions.sh` first
- **"Poetry lock inconsistent"**: Script will automatically regenerate
- **"Docker build failed"**: Check Docker installation and disk space
- **"Secrets generation failed"**: Ensure write permissions in secrets directory

---

## scripts/_setup_soft.sh

**Location:** `/scripts/_setup_soft.sh`  
**Purpose:** Lightweight setup that rebuilds Docker images without regenerating certificates and secrets.

### Description
A faster setup option that preserves existing certificates and secrets while rebuilding Docker images. Ideal for development when you need to update code but don't want to regenerate security materials.

### Usage
```bash
./scripts/_setup_soft.sh
```

### What It Does
1. **Skip Certificate Generation:** Uses existing certificates
2. **Skip Secret Generation:** Preserves existing secrets
3. **Dependency Check:** Validates poetry.lock consistency
4. **Docker Build:** Rebuilds images with cache
5. **Validation:** Confirms setup completion

### When to Use
- Development iterations where certificates are still valid
- Code updates that don't require new secrets
- Quick rebuilds after dependency changes
- CI/CD pipelines where secrets are externally managed

---

## scripts/_setup_secrets_and_certs.sh

**Location:** `/scripts/_setup_secrets_and_certs.sh`  
**Purpose:** Generates all required secrets, API keys, and SSL/TLS certificates for the application.

### Description
Creates the complete security infrastructure including database passwords, JWT tokens, API keys, and SSL certificates. This script is the foundation of the application's security model.

### Usage
```bash
./scripts/_setup_secrets_and_certs.sh
```

### Generated Files
```
secrets/
├── postgres_user.txt           # Database username
├── postgres_password.txt       # Database password  
├── postgres_db.txt            # Database name
├── jwt_secret_key.txt         # JWT signing key
├── api_key.txt                # API authentication key
├── qdrant_api_key.txt         # Vector database key
├── admin_email.txt            # Default admin email
├── admin_password.txt         # Default admin password
└── session_secret.txt         # Session encryption key

certs/
├── ca/                        # Certificate Authority
├── api/                       # API service certificates
├── worker/                    # Worker service certificates
├── postgres/                  # Database certificates
├── pgbouncer/                 # Connection pooler certificates
├── redis/                     # Cache service certificates
├── qdrant/                    # Vector DB certificates
├── ollama/                    # AI model service certificates
├── caddy_reverse_proxy/       # Reverse proxy certificates
├── webui/                     # Web UI certificates
├── prometheus/                # Monitoring certificates
└── grafana/                   # Dashboard certificates
```

### Security Features
- **Strong Password Generation:** Using cryptographically secure random generators
- **JWT Key Security:** 256-bit secret keys for token signing
- **Certificate Authority:** Self-signed CA for internal mTLS
- **Service Certificates:** Individual certificates for each service
- **Proper Permissions:** Restrictive file permissions (600/700)

### Customization
Edit these files after generation if needed:
- `secrets/admin_email.txt` - Change default admin email
- `secrets/admin_password.txt` - Set custom admin password

---

## scripts/_setup_server.sh

**Location:** `/scripts/_setup_server.sh`  
**Purpose:** Server-specific configuration for production deployments.

### Description
Configures server-specific settings including networking, firewall rules, and production optimizations.

### Usage
```bash
./scripts/_setup_server.sh
```

### Features
- Network interface configuration
- Firewall rule setup
- Production security hardening
- Performance optimizations
- Service monitoring setup

---

## scripts/_setup_client_access.sh

**Location:** `/scripts/_setup_client_access.sh`  
**Purpose:** Configures client access to the AI Workflow Engine services.

### Description
Sets up client certificates and access configurations for external clients to connect securely to the services.

### Usage
```bash
./scripts/_setup_client_access.sh
```

### What It Does
1. **Client Certificates:** Generates client-specific certificates
2. **Access Profiles:** Creates connection profiles
3. **Network Configuration:** Sets up client networking
4. **Validation:** Tests client connectivity

---

## scripts/_setup_remote_access.sh

**Location:** `/scripts/_setup_remote_access.sh`  
**Purpose:** Enables secure remote access to the AI Workflow Engine.

### Description
Configures remote access capabilities including VPN setup, SSH key management, and secure tunneling.

### Usage
```bash
./scripts/_setup_remote_access.sh
```

### Features
- SSH key generation and deployment
- VPN configuration
- Secure tunnel setup
- Remote monitoring access
- Authentication setup

---

## scripts/_make_scripts_executable.sh

**Location:** `/scripts/_make_scripts_executable.sh`  
**Purpose:** Ensures all shell scripts in the project have executable permissions.

### Description
A utility script that finds all `.sh` files in the project and makes them executable. Essential for preventing "Permission denied" errors.

### Usage
```bash
./scripts/_make_scripts_executable.sh
```

### What It Does
```bash
find . -type f -name "*.sh" -exec sudo chmod +x {} +
```

### When to Use
- After cloning the repository
- After permission issues with Docker operations
- Before running any other scripts
- In CI/CD pipelines

---

## scripts/lock_dependencies.sh

**Location:** `/scripts/lock_dependencies.sh`  
**Purpose:** Regenerates poetry.lock file to ensure dependency consistency.

### Description
Uses a clean Python environment to regenerate the poetry.lock file, ensuring all dependencies are properly resolved and consistent across environments.

### Usage
```bash
./scripts/lock_dependencies.sh
```

### What It Does
1. **Clean Environment:** Uses Docker for consistent Python environment
2. **Dependency Resolution:** Runs `poetry lock` to resolve all dependencies
3. **Validation:** Checks the generated lock file
4. **Backup:** Preserves the old lock file as backup

### When It Runs
- Automatically during `_setup.sh` if lock file is inconsistent
- Manually when dependencies are updated
- In CI/CD when dependency changes are detected

### Output
```
INFO: Regenerating poetry.lock in a clean environment...
INFO: This ensures consistent dependencies across all environments.
SUCCESS: ✅ poetry.lock regenerated successfully.
```

---

## Setup Workflow

### Initial Setup (New Environment)
```bash
# 1. Make scripts executable
./scripts/_make_scripts_executable.sh

# 2. Complete setup
./scripts/_setup.sh

# 3. Start application
./run.sh
```

### Development Setup (Existing Environment)
```bash
# Quick setup preserving certificates
./scripts/_setup_soft.sh

# Or start with soft reset
./run.sh --soft-reset
```

### Production Setup
```bash
# 1. Full setup with server configuration
./scripts/_setup.sh --no-cache
./scripts/_setup_server.sh

# 2. Configure client access
./scripts/_setup_client_access.sh

# 3. Enable remote access (if needed)
./scripts/_setup_remote_access.sh
```

---

## Common Issues and Solutions

### Permission Problems
```bash
# Fix all permission issues
sudo ./scripts/fix_permissions.sh

# Make scripts executable
./scripts/_make_scripts_executable.sh
```

### Dependency Issues
```bash
# Regenerate lock file
./scripts/lock_dependencies.sh

# Clean setup
./scripts/_setup.sh --full-teardown
```

### Certificate Problems
```bash
# Regenerate all certificates
rm -rf certs/ secrets/
./scripts/_setup_secrets_and_certs.sh
```

### Docker Build Issues
```bash
# Clean rebuild
./scripts/_setup.sh --no-cache

# Full clean setup
./scripts/_setup.sh --full-teardown --no-cache
```

---

*For troubleshooting specific setup issues, see the [Troubleshooting Guide](./workflows/troubleshooting.md).*