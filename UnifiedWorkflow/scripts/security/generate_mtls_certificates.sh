#!/bin/bash

# =============================================================================
# mTLS Certificate Generation Script for AI Workflow Engine
# =============================================================================
# 
# This script generates a complete mTLS certificate infrastructure for secure
# inter-service communication in the AI Workflow Engine.
#
# Generated Certificates:
# - Root CA (Certificate Authority)
# - Service-specific certificates for each microservice
# - Client certificates for authorized access
# 
# Security Features:
# - RSA 4096-bit keys for maximum security
# - 365-day certificate validity with rotation capability
# - Subject Alternative Names (SANs) for service discovery
# - Proper certificate extensions for mTLS usage
#
# Usage: ./generate_mtls_certificates.sh [domain_name]
# Example: ./generate_mtls_certificates.sh aiwfe.local
#
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/certs"
MTLS_DIR="${CERTS_DIR}/mtls"
DOMAIN="${1:-aiwfe.local}"
KEY_SIZE=4096
DAYS=365

# Service list for certificate generation
SERVICES=(
    "api"
    "worker" 
    "postgres"
    "pgbouncer"
    "redis"
    "qdrant"
    "ollama"
    "caddy_reverse_proxy"
    "prometheus"
    "grafana"
)

# Client types for mTLS access
CLIENTS=(
    "admin_client"
    "monitoring_client"
    "service_mesh_client"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# =============================================================================
# Certificate Authority (CA) Generation
# =============================================================================

generate_ca() {
    log "Generating mTLS Certificate Authority..."
    
    # Create CA directories
    mkdir -p "${MTLS_DIR}/ca"
    cd "${MTLS_DIR}/ca"
    
    # Generate CA private key
    log "Generating CA private key..."
    openssl genrsa -out ca-key.pem $KEY_SIZE
    chmod 400 ca-key.pem
    
    # Generate CA certificate
    log "Generating CA certificate..."
    cat > ca.conf << EOF
[req]
distinguished_name = req_distinguished_name
prompt = no
x509_extensions = v3_ca

[req_distinguished_name]
C = US
ST = California
L = San Francisco
O = AI Workflow Engine
OU = Security Team
CN = AI Workflow Engine mTLS CA

[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
EOF

    openssl req -new -x509 -days $DAYS -key ca-key.pem \
        -out ca-cert.pem -config ca.conf
    
    # Create CA serial number file
    echo 1000 > ca.srl
    
    log "Certificate Authority generated successfully"
    info "CA Certificate: ${MTLS_DIR}/ca/ca-cert.pem"
    info "CA Private Key: ${MTLS_DIR}/ca/ca-key.pem"
}

# =============================================================================
# Service Certificate Generation
# =============================================================================

generate_service_certificate() {
    local service_name="$1"
    log "Generating certificate for service: $service_name"
    
    # Create service directory
    mkdir -p "${MTLS_DIR}/services/${service_name}"
    cd "${MTLS_DIR}/services/${service_name}"
    
    # Generate service private key
    openssl genrsa -out ${service_name}-key.pem $KEY_SIZE
    chmod 400 ${service_name}-key.pem
    
    # Create service certificate configuration
    cat > ${service_name}.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = California
L = San Francisco
O = AI Workflow Engine
OU = ${service_name} Service
CN = ${service_name}.${DOMAIN}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth,clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${service_name}
DNS.2 = ${service_name}.${DOMAIN}
DNS.3 = ${service_name}.ai_workflow_engine_net
DNS.4 = localhost
IP.1 = 127.0.0.1
EOF

    # Add service-specific SANs
    case "$service_name" in
        "api")
            cat >> ${service_name}.conf << EOF
DNS.5 = api.internal
DNS.6 = backend.${DOMAIN}
EOF
            ;;
        "postgres")
            cat >> ${service_name}.conf << EOF
DNS.5 = database.${DOMAIN}
DNS.6 = db.internal
EOF
            ;;
        "redis")
            cat >> ${service_name}.conf << EOF
DNS.5 = cache.${DOMAIN}
DNS.6 = redis.internal
EOF
            ;;
        "caddy_reverse_proxy")
            cat >> ${service_name}.conf << EOF
DNS.5 = proxy.${DOMAIN}
DNS.6 = gateway.internal
DNS.7 = ${DOMAIN}
DNS.8 = *.${DOMAIN}
EOF
            ;;
    esac
    
    # Generate certificate signing request
    openssl req -new -key ${service_name}-key.pem \
        -out ${service_name}-csr.pem -config ${service_name}.conf
    
    # Sign the certificate with CA
    openssl x509 -req -in ${service_name}-csr.pem \
        -CA "${MTLS_DIR}/ca/ca-cert.pem" \
        -CAkey "${MTLS_DIR}/ca/ca-key.pem" \
        -CAserial "${MTLS_DIR}/ca/ca.srl" \
        -out ${service_name}-cert.pem \
        -days $DAYS \
        -extensions v3_req \
        -extfile ${service_name}.conf
    
    # Create certificate bundle
    cat ${service_name}-cert.pem "${MTLS_DIR}/ca/ca-cert.pem" > ${service_name}-bundle.pem
    
    # Set proper permissions
    chmod 644 ${service_name}-cert.pem ${service_name}-bundle.pem
    chmod 444 ${service_name}-csr.pem
    
    log "Certificate generated for $service_name"
}

# =============================================================================
# Client Certificate Generation
# =============================================================================

generate_client_certificate() {
    local client_name="$1"
    log "Generating client certificate for: $client_name"
    
    # Create client directory
    mkdir -p "${MTLS_DIR}/clients/${client_name}"
    cd "${MTLS_DIR}/clients/${client_name}"
    
    # Generate client private key
    openssl genrsa -out ${client_name}-key.pem $KEY_SIZE
    chmod 400 ${client_name}-key.pem
    
    # Create client certificate configuration
    cat > ${client_name}.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = California
L = San Francisco
O = AI Workflow Engine
OU = Client Access
CN = ${client_name}

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation,digitalSignature,keyEncipherment
extendedKeyUsage = clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${client_name}
DNS.2 = ${client_name}.${DOMAIN}
EOF

    # Generate certificate signing request
    openssl req -new -key ${client_name}-key.pem \
        -out ${client_name}-csr.pem -config ${client_name}.conf
    
    # Sign the certificate with CA
    openssl x509 -req -in ${client_name}-csr.pem \
        -CA "${MTLS_DIR}/ca/ca-cert.pem" \
        -CAkey "${MTLS_DIR}/ca/ca-key.pem" \
        -CAserial "${MTLS_DIR}/ca/ca.srl" \
        -out ${client_name}-cert.pem \
        -days $DAYS \
        -extensions v3_req \
        -extfile ${client_name}.conf
    
    # Create PKCS#12 bundle for easy client import
    openssl pkcs12 -export -out ${client_name}.p12 \
        -inkey ${client_name}-key.pem \
        -in ${client_name}-cert.pem \
        -certfile "${MTLS_DIR}/ca/ca-cert.pem" \
        -password pass:mtls-client-${client_name}
    
    # Set proper permissions
    chmod 644 ${client_name}-cert.pem ${client_name}.p12
    chmod 444 ${client_name}-csr.pem
    
    log "Client certificate generated for $client_name"
}

# =============================================================================
# Service Integration
# =============================================================================

integrate_with_existing_certs() {
    log "Integrating mTLS certificates with existing certificate structure..."
    
    # Create symbolic links in the existing certs structure
    for service in "${SERVICES[@]}"; do
        if [[ -d "${CERTS_DIR}/${service}" ]]; then
            info "Creating mTLS certificate links for $service"
            
            # Link mTLS certificates alongside existing ones
            ln -sf "../../mtls/services/${service}/${service}-cert.pem" \
                "${CERTS_DIR}/${service}/mtls-cert.pem"
            ln -sf "../../mtls/services/${service}/${service}-key.pem" \
                "${CERTS_DIR}/${service}/mtls-key.pem"
            ln -sf "../../mtls/services/${service}/${service}-bundle.pem" \
                "${CERTS_DIR}/${service}/mtls-bundle.pem"
            ln -sf "../../mtls/ca/ca-cert.pem" \
                "${CERTS_DIR}/${service}/mtls-ca.pem"
        fi
    done
    
    log "Certificate integration completed"
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_certificates() {
    log "Validating generated certificates..."
    
    # Validate CA certificate
    if openssl x509 -in "${MTLS_DIR}/ca/ca-cert.pem" -noout -text > /dev/null; then
        info "✓ CA certificate is valid"
    else
        error "✗ CA certificate is invalid"
    fi
    
    # Validate service certificates
    for service in "${SERVICES[@]}"; do
        local cert_file="${MTLS_DIR}/services/${service}/${service}-cert.pem"
        if openssl x509 -in "$cert_file" -noout -text > /dev/null; then
            info "✓ $service certificate is valid"
        else
            warn "✗ $service certificate is invalid"
        fi
        
        # Verify certificate against CA
        if openssl verify -CAfile "${MTLS_DIR}/ca/ca-cert.pem" "$cert_file" > /dev/null 2>&1; then
            info "✓ $service certificate verified against CA"
        else
            warn "✗ $service certificate verification failed"
        fi
    done
    
    # Validate client certificates
    for client in "${CLIENTS[@]}"; do
        local cert_file="${MTLS_DIR}/clients/${client}/${client}-cert.pem"
        if openssl x509 -in "$cert_file" -noout -text > /dev/null; then
            info "✓ $client certificate is valid"
        else
            warn "✗ $client certificate is invalid"
        fi
    done
    
    log "Certificate validation completed"
}

# =============================================================================
# Documentation Generation
# =============================================================================

generate_documentation() {
    log "Generating mTLS certificate documentation..."
    
    cat > "${MTLS_DIR}/README.md" << EOF
# mTLS Certificate Infrastructure

This directory contains the complete mTLS certificate infrastructure for the AI Workflow Engine.

## Generated on: $(date)
## Domain: $DOMAIN
## Certificate Validity: $DAYS days

## Directory Structure

\`\`\`
mtls/
├── ca/                    # Certificate Authority
│   ├── ca-cert.pem       # CA Certificate (public)
│   ├── ca-key.pem        # CA Private Key (protected)
│   └── ca.srl            # Serial number tracker
├── services/             # Service certificates
$(for service in "${SERVICES[@]}"; do echo "│   ├── ${service}/           # ${service} service certificates"; done)
└── clients/              # Client certificates
$(for client in "${CLIENTS[@]}"; do echo "    ├── ${client}/        # ${client} access certificates"; done)
\`\`\`

## Certificate Usage

### Service Certificates
Each service has the following files:
- \`{service}-cert.pem\`: Service certificate
- \`{service}-key.pem\`: Service private key
- \`{service}-bundle.pem\`: Certificate + CA bundle
- \`{service}-csr.pem\`: Certificate signing request

### Client Certificates
Each client has the following files:
- \`{client}-cert.pem\`: Client certificate
- \`{client}-key.pem\`: Client private key
- \`{client}.p12\`: PKCS#12 bundle for browser import

## Docker Compose Integration

The certificates are automatically integrated with the existing certificate structure via symbolic links.

## Certificate Rotation

To rotate certificates:
1. Run this script again with the same domain
2. Restart affected services
3. Update any hardcoded certificate paths

## Validation

To validate certificates:
\`\`\`bash
# Verify service certificate
openssl verify -CAfile ca/ca-cert.pem services/{service}/{service}-cert.pem

# Check certificate details
openssl x509 -in services/{service}/{service}-cert.pem -text -noout

# Test mTLS connection
openssl s_client -connect {service}:port -cert clients/{client}/{client}-cert.pem -key clients/{client}/{client}-key.pem -CAfile ca/ca-cert.pem
\`\`\`

## Security Notes

- Private keys are protected with 400 permissions
- Certificates are valid for $DAYS days
- All certificates support both server and client authentication
- Subject Alternative Names (SANs) include service discovery hostnames

EOF

    log "Documentation generated: ${MTLS_DIR}/README.md"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    log "Starting mTLS certificate generation for domain: $DOMAIN"
    
    # Create directory structure
    mkdir -p "$MTLS_DIR"
    
    # Generate CA
    generate_ca
    
    # Generate service certificates
    for service in "${SERVICES[@]}"; do
        generate_service_certificate "$service"
    done
    
    # Generate client certificates
    for client in "${CLIENTS[@]}"; do
        generate_client_certificate "$client"
    done
    
    # Integrate with existing certificate structure
    integrate_with_existing_certs
    
    # Validate all certificates
    validate_certificates
    
    # Generate documentation
    generate_documentation
    
    log "mTLS certificate generation completed successfully!"
    info "Certificate directory: $MTLS_DIR"
    info "Next steps:"
    info "1. Update Docker Compose with mTLS configuration"
    info "2. Configure services for mTLS authentication"
    info "3. Test mTLS connections between services"
    info "4. Set up certificate rotation schedule"
}

# Check if OpenSSL is available
if ! command -v openssl &> /dev/null; then
    error "OpenSSL is required but not installed. Please install OpenSSL and try again."
fi

# Run main function
main "$@"