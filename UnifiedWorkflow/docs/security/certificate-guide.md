# Automatic Certificate Generation System

This system provides automated mTLS certificate generation for the AI Workflow Engine using Docker Compose.

## Quick Start

### Generate Certificates
```bash
# Using the script (recommended)
./scripts/generate_certificates.sh

# Or using Docker Compose directly
docker compose -f docker-compose-certs.yaml up
```

### Start Services with mTLS
```bash
# After certificate generation
docker compose -f docker-compose-mtls.yml up
```

## Architecture

The certificate system generates:

1. **Certificate Authority (CA)**
   - Root CA for signing all service certificates
   - Location: `certs/ca/ca-cert.pem`
   - Validity: 10 years

2. **Service Certificates**
   - API (`certs/api/`)
   - WebUI (`certs/webui/`)
   - Caddy Reverse Proxy (`certs/caddy_reverse_proxy/`)
   - PostgreSQL (`certs/postgres/`)
   - Redis (`certs/redis/`)

3. **Certificate Types**
   - Individual certificates: `{service}-cert.pem`, `{service}-key.pem`
   - Unified certificates: `unified-cert.pem` (cert + CA chain), `unified-key.pem`

## Domain Support

All certificates support multiple domains:
- Service names: `api`, `webui`, etc.
- Localhost: `localhost`, `127.0.0.1`
- Project domains: `*.ai-workflow-engine.local`
- Production domain: `aiwfe.com`, `*.aiwfe.com`

## Certificate Management Script

### Commands

```bash
# Generate certificates (default)
./scripts/generate_certificates.sh
./scripts/generate_certificates.sh generate

# Validate existing certificates  
./scripts/generate_certificates.sh validate

# Show certificate information
./scripts/generate_certificates.sh info

# Renew all certificates (with backup)
./scripts/generate_certificates.sh renew

# Clean up all certificates
./scripts/generate_certificates.sh clean

# Show help
./scripts/generate_certificates.sh help
```

### Features

- **Automatic Validation**: Checks certificate validity and expiration
- **Backup on Renewal**: Creates timestamped backups before renewal
- **Detailed Logging**: Color-coded output for easy monitoring
- **Error Handling**: Proper error detection and reporting

## Files Created

### Certificate Generation
- `docker-compose-certs.yaml` - Docker Compose for certificate generation
- `scripts/generate_certificates.sh` - Certificate management script
- `README-CERTIFICATES.md` - This documentation

### Directory Structure
```
certs/
├── ca/
│   ├── private/
│   │   └── ca-key.pem        # CA private key
│   ├── ca-cert.pem           # CA certificate
│   ├── index.txt             # CA database
│   └── serial                # Certificate serial number
├── api/
│   ├── api-cert.pem          # API certificate
│   ├── api-key.pem           # API private key
│   ├── unified-cert.pem      # API cert + CA chain
│   └── unified-key.pem       # API private key (copy)
├── webui/
├── caddy_reverse_proxy/
├── postgres/
└── redis/
```

## Integration with Existing Infrastructure

This system integrates with:
- Existing mTLS setup in `scripts/security/setup_mtls_infrastructure.sh`
- Docker Compose mTLS configuration in `docker-compose-mtls.yml`
- Container entrypoint wrappers for certificate isolation

## Security Features

- 4096-bit RSA keys for all certificates
- Subject Alternative Names (SAN) for multiple domain support
- Proper file permissions (600 for private keys, 644 for certificates)
- Certificate chain validation
- Expiration monitoring

## Usage Examples

### Initial Setup
```bash
# 1. Generate certificates
./scripts/generate_certificates.sh

# 2. Validate generation
./scripts/generate_certificates.sh validate

# 3. Start services
docker compose -f docker-compose-mtls.yml up
```

### Monitoring and Maintenance
```bash
# Check certificate status
./scripts/generate_certificates.sh info

# Validate certificates (check expiration)
./scripts/generate_certificates.sh validate

# Renew certificates before expiration
./scripts/generate_certificates.sh renew
```

### Troubleshooting
```bash
# Clean up and regenerate if issues occur
./scripts/generate_certificates.sh clean
./scripts/generate_certificates.sh generate
```

## Automation Integration

The certificate generation can be integrated into CI/CD pipelines:

```bash
# In deployment scripts
./scripts/generate_certificates.sh generate
./scripts/generate_certificates.sh validate || exit 1
```

## Security Considerations

1. **Private Key Protection**: All private keys have restrictive permissions (600)
2. **CA Security**: CA private key is protected with 400 permissions
3. **Certificate Validation**: Automatic validation prevents use of expired certificates
4. **Backup Strategy**: Automatic backups during renewal prevent data loss
5. **Domain Validation**: SAN extensions ensure proper domain validation

## Support

For issues with certificate generation:
1. Check Docker is running: `docker --version`
2. Validate permissions: `ls -la certs/`
3. Check logs: Review Docker Compose output
4. Clean and regenerate: `./scripts/generate_certificates.sh clean && ./scripts/generate_certificates.sh generate`