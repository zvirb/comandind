# Security Scripts Documentation

Security scripts handle SSL/TLS certificate management, mTLS infrastructure, and security validation. These scripts implement the project's comprehensive security architecture.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `security/setup_mtls_infrastructure.sh` | Complete mTLS setup | `./scripts/security/setup_mtls_infrastructure.sh [command]` |
| `security/generate_mtls_certificates.sh` | Generate mTLS certificates | `./scripts/security/generate_mtls_certificates.sh` |
| `security/rotate_certificates.sh` | Certificate rotation | `./scripts/security/rotate_certificates.sh` |
| `security/validate_security_implementation.sh` | Security validation | `./scripts/security/validate_security_implementation.sh` |
| `generate_certificates.sh` | Legacy certificate generation | `./scripts/generate_certificates.sh` |
| `generate_dev_certificates.sh` | Development certificates | `./scripts/generate_dev_certificates.sh` |
| `validate_ssl_configuration.sh` | SSL configuration validation | `./scripts/validate_ssl_configuration.sh` |
| `validate_ssl_fix.py` | SSL fix validation | `./scripts/validate_ssl_fix.py` |

---

## security/setup_mtls_infrastructure.sh

**Location:** `/scripts/security/setup_mtls_infrastructure.sh`  
**Purpose:** Comprehensive mTLS (mutual TLS) certificate infrastructure setup for all services.

### Description
The primary security script that implements a complete Certificate Authority (CA) and generates service-specific certificates for all components in the AI Workflow Engine. This script establishes the foundation for secure inter-service communication.

### Usage
```bash
./scripts/security/setup_mtls_infrastructure.sh [COMMAND] [OPTIONS]
```

### Commands
- `setup` - Complete mTLS infrastructure setup (default)
- `generate-ca` - Generate only the Certificate Authority
- `generate-service <name>` - Generate certificate for specific service
- `generate-all` - Generate certificates for all services
- `rotate-service <name>` - Rotate certificate for specific service
- `rotate-all` - Rotate all service certificates
- `validate` - Validate all certificates
- `info <cert_file>` - Display certificate information
- `cleanup` - Remove all certificates (destructive)

### Examples
```bash
# Complete setup (recommended)
./scripts/security/setup_mtls_infrastructure.sh setup

# Generate certificate for API service
./scripts/security/setup_mtls_infrastructure.sh generate-service api

# Rotate all certificates
./scripts/security/setup_mtls_infrastructure.sh rotate-all

# Validate certificate infrastructure
./scripts/security/setup_mtls_infrastructure.sh validate

# Show certificate details
./scripts/security/setup_mtls_infrastructure.sh info /path/to/cert.pem
```

### Certificate Architecture

#### Services with Certificates
- **api** - API service with REST endpoints
- **worker** - Background task worker
- **postgres** - PostgreSQL database
- **pgbouncer** - Connection pooler
- **redis** - Cache and session store
- **qdrant** - Vector database
- **ollama** - AI model service
- **caddy_reverse_proxy** - Reverse proxy and load balancer
- **webui** - Web user interface
- **prometheus** - Monitoring system
- **grafana** - Metrics dashboard

#### Certificate Authority Structure
```
certs/ca/
├── private/
│   └── ca-key.pem          # CA private key (4096-bit RSA)
├── certs/
│   └── ca-cert.pem         # CA certificate (10-year validity)
├── newcerts/               # Signed certificate copies
├── crl/                    # Certificate revocation lists
├── index.txt               # Certificate database
├── serial                  # Certificate serial numbers
└── openssl.cnf            # OpenSSL configuration
```

#### Service Certificate Structure
```
certs/{service}/
├── {service}-key.pem       # Service private key
├── {service}-cert.pem      # Service certificate
├── {service}-csr.pem       # Certificate signing request
├── unified-cert.pem        # Certificate + CA chain
├── unified-key.pem         # Private key (copy)
├── rootCA.pem             # CA certificate (copy)
├── server.crt             # Legacy filename compatibility
├── server.key             # Legacy filename compatibility
└── root.crt               # Legacy CA certificate
```

### Certificate Configuration
- **Key Size:** 4096-bit RSA
- **CA Validity:** 10 years (3650 days)
- **Service Validity:** 1 year (365 days)
- **Hash Algorithm:** SHA-256
- **Extensions:** Server Auth, Client Auth

### Subject Alternative Names (SAN)
Each service certificate includes multiple SAN entries:
- Service hostname (e.g., `api.ai-workflow-engine.local`)
- `localhost`
- `127.0.0.1`
- Docker service name
- External domain names (for Caddy)

### Security Features
- **Self-Signed CA:** Internal certificate authority for secure communication
- **Mutual TLS:** Both client and server authentication
- **Certificate Validation:** Automatic validation against CA
- **Expiration Monitoring:** Alerts for certificates nearing expiration
- **Rotation Support:** Safe certificate renewal without downtime

### Integration with Docker
The script creates Docker secrets for seamless container integration:
```
secrets/
├── mtls_ca_cert.pem                    # CA certificate
├── {service}_cert_bundle.pem           # Service certificate + CA chain
└── {service}_private_key.pem           # Service private key
```

### Prerequisites
- OpenSSL installed
- Write permissions to `certs/` and `secrets/` directories
- Sufficient entropy for key generation

### Troubleshooting
- **"OpenSSL not found"**: Install OpenSSL package
- **"Permission denied"**: Run `sudo ./scripts/fix_permissions.sh`
- **"Certificate validation failed"**: Check CA certificate integrity
- **"SAN validation failed"**: Verify service name configuration

---

## security/generate_mtls_certificates.sh

**Location:** `/scripts/security/generate_mtls_certificates.sh`  
**Purpose:** Specialized script for generating mTLS certificates with specific configurations.

### Description
A focused script that generates mTLS certificates with predefined configurations optimized for the AI Workflow Engine's security requirements.

### Usage
```bash
./scripts/security/generate_mtls_certificates.sh [SERVICE_NAME]
```

### Features
- Pre-configured SAN lists for each service
- Optimized certificate extensions
- Automatic Docker secret generation
- Validation of generated certificates

---

## security/rotate_certificates.sh

**Location:** `/scripts/security/rotate_certificates.sh`  
**Purpose:** Automated certificate rotation for maintaining security without service interruption.

### Description
Implements safe certificate rotation procedures that minimize service downtime while maintaining security standards.

### Usage
```bash
./scripts/security/rotate_certificates.sh [SERVICE_NAME|all]
```

### Features
- **Graceful Rotation:** Minimizes service interruption
- **Backup Management:** Preserves old certificates
- **Validation:** Ensures new certificates are valid
- **Service Restart:** Coordinates container restarts

### Rotation Process
1. **Backup:** Current certificates backed up with timestamp
2. **Generate:** New certificates created with fresh keys
3. **Validate:** New certificates verified against CA
4. **Deploy:** New certificates deployed to services
5. **Restart:** Services restarted to load new certificates
6. **Verify:** End-to-end connectivity tested

---

## security/validate_security_implementation.sh

**Location:** `/scripts/security/validate_security_implementation.sh`  
**Purpose:** Comprehensive validation of the security implementation.

### Description
Performs thorough security validation including certificate integrity, mTLS connectivity, and security policy compliance.

### Usage
```bash
./scripts/security/validate_security_implementation.sh
```

### Validation Checks
- **Certificate Integrity:** All certificates valid and properly signed
- **Expiration Status:** No certificates near expiration
- **mTLS Connectivity:** Inter-service communication working
- **Security Policies:** Compliance with security requirements
- **Key Security:** Private key permissions and security
- **CA Integrity:** Certificate authority not compromised

### Output Example
```
INFO: Validating mTLS certificate infrastructure...
SUCCESS: Certificate valid: api
SUCCESS: Certificate valid: worker
SUCCESS: Certificate valid: postgres
INFO: Certificate api is valid for 364 days
INFO: Certificate worker is valid for 364 days
SUCCESS: All certificates validated successfully
INFO: mTLS connectivity test passed
SUCCESS: Security implementation validation complete
```

---

## Legacy Certificate Scripts

### generate_certificates.sh
**Purpose:** Legacy certificate generation script maintained for compatibility.

### generate_dev_certificates.sh
**Purpose:** Quick development certificate generation without full CA setup.

### validate_ssl_configuration.sh
**Purpose:** SSL/TLS configuration validation for web services.

### validate_ssl_fix.py
**Purpose:** Python-based SSL validation with detailed diagnostics.

---

## Certificate Management Workflows

### Initial Setup
```bash
# Complete mTLS infrastructure setup
./scripts/security/setup_mtls_infrastructure.sh setup

# Validate setup
./scripts/security/setup_mtls_infrastructure.sh validate
```

### Development Environment
```bash
# Quick development certificates
./scripts/generate_dev_certificates.sh

# Validate SSL configuration
./scripts/validate_ssl_configuration.sh
```

### Certificate Rotation
```bash
# Rotate specific service certificate
./scripts/security/setup_mtls_infrastructure.sh rotate-service api

# Rotate all certificates
./scripts/security/setup_mtls_infrastructure.sh rotate-all

# Validate after rotation
./scripts/security/setup_mtls_infrastructure.sh validate
```

### Troubleshooting Certificates
```bash
# Check certificate details
./scripts/security/setup_mtls_infrastructure.sh info certs/api/api-cert.pem

# Validate specific certificate
openssl verify -CAfile certs/ca/certs/ca-cert.pem certs/api/api-cert.pem

# Test mTLS connectivity
./scripts/security/validate_security_implementation.sh
```

---

## Security Best Practices

### Certificate Management
1. **Regular Rotation:** Rotate certificates before expiration
2. **Backup Strategy:** Maintain secure backups of CA keys
3. **Access Control:** Restrict access to private keys
4. **Monitoring:** Monitor certificate expiration dates
5. **Validation:** Regularly validate certificate integrity

### Development vs Production
- **Development:** Use `generate_dev_certificates.sh` for quick setup
- **Production:** Always use full mTLS infrastructure
- **Testing:** Validate certificates after any changes
- **Deployment:** Use certificate rotation for zero-downtime updates

### Common Issues
- **Clock Skew:** Ensure system clocks are synchronized
- **DNS Resolution:** Verify service names resolve correctly
- **Firewall Rules:** Allow mTLS traffic on required ports
- **Container Networking:** Ensure Docker networks support mTLS

---

## Integration Points

### Docker Compose
Certificates are automatically integrated with Docker services through:
- Volume mounts for certificate files
- Environment variables for certificate paths
- Health checks validating certificate validity

### Application Services
Services are configured to use mTLS through:
- SSL context configuration
- Certificate validation settings
- Mutual authentication requirements
- Connection security policies

### Monitoring
Certificate status is monitored through:
- Expiration date tracking
- Validation health checks
- Security audit logging
- Performance impact monitoring

---

*For advanced certificate management and troubleshooting, see the [Security Guide](../security.md).*