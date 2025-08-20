#!/bin/bash

# =============================================================================
# mTLS Certificate Infrastructure Setup
# AI Workflow Engine Security Enhancement
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/certs"
SECRETS_DIR="${PROJECT_ROOT}/secrets"
CA_DIR="${CERTS_DIR}/ca"

# Certificate configuration
CA_VALIDITY_DAYS=3650  # 10 years for CA
CERT_VALIDITY_DAYS=365 # 1 year for service certificates
KEY_SIZE=4096
COUNTRY="US"
STATE="California"
CITY="San Francisco"
ORG="AI Workflow Engine"
OU="Security"

# Service definitions for certificate generation
declare -A SERVICES=(
    ["api"]="api,localhost,127.0.0.1,api.ai-workflow-engine.local"
    ["worker"]="worker,localhost,127.0.0.1,worker.ai-workflow-engine.local"
    ["postgres"]="postgres,localhost,127.0.0.1,postgres.ai-workflow-engine.local"
    ["pgbouncer"]="pgbouncer,localhost,127.0.0.1,pgbouncer.ai-workflow-engine.local"
    ["redis"]="redis,localhost,127.0.0.1,redis.ai-workflow-engine.local"
    ["qdrant"]="qdrant,localhost,127.0.0.1,qdrant.ai-workflow-engine.local"
    ["ollama"]="ollama,localhost,127.0.0.1,ollama.ai-workflow-engine.local"
    ["caddy_reverse_proxy"]="caddy,localhost,127.0.0.1,*.ai-workflow-engine.local,aiwfe.com,*.aiwfe.com"
    ["webui"]="webui,localhost,127.0.0.1,webui.ai-workflow-engine.local"
    ["prometheus"]="prometheus,localhost,127.0.0.1,prometheus.ai-workflow-engine.local"
    ["grafana"]="grafana,localhost,127.0.0.1,grafana.ai-workflow-engine.local"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# CA Certificate Authority Setup
# =============================================================================

setup_ca() {
    log_info "Setting up Certificate Authority..."
    
    # Create CA directory structure
    mkdir -p "${CA_DIR}"/{private,certs,newcerts,crl}
    touch "${CA_DIR}/index.txt"
    echo 1000 > "${CA_DIR}/serial"
    echo 1000 > "${CA_DIR}/crlnumber"
    
    # Generate CA private key
    if [[ ! -f "${CA_DIR}/private/ca-key.pem" ]]; then
        log_info "Generating CA private key..."
        openssl genrsa -out "${CA_DIR}/private/ca-key.pem" ${KEY_SIZE}
        chmod 400 "${CA_DIR}/private/ca-key.pem"
        log_success "CA private key generated"
    else
        log_warning "CA private key already exists, skipping..."
    fi
    
    # Generate CA certificate
    if [[ ! -f "${CA_DIR}/certs/ca-cert.pem" ]]; then
        log_info "Generating CA certificate..."
        
        # Create CA certificate request
        openssl req -new -x509 -key "${CA_DIR}/private/ca-key.pem" \
            -days ${CA_VALIDITY_DAYS} \
            -out "${CA_DIR}/certs/ca-cert.pem" \
            -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${OU}/CN=AI Workflow Engine Root CA"
        
        chmod 444 "${CA_DIR}/certs/ca-cert.pem"
        log_success "CA certificate generated"
    else
        log_warning "CA certificate already exists, skipping..."
    fi
    
    # Create OpenSSL CA configuration
    create_ca_config
    
    # Copy CA cert to project secrets for Docker secrets
    cp "${CA_DIR}/certs/ca-cert.pem" "${SECRETS_DIR}/ca_cert.pem"
    
    log_success "Certificate Authority setup complete"
}

create_ca_config() {
    cat > "${CA_DIR}/openssl.cnf" << 'EOF'
[ ca ]
default_ca = CA_default

[ CA_default ]
dir               = REPLACE_CA_DIR
certs             = $dir/certs
crl_dir           = $dir/crl
new_certs_dir     = $dir/newcerts
database          = $dir/index.txt
serial            = $dir/serial
RANDFILE          = $dir/private/.rand

private_key       = $dir/private/ca-key.pem
certificate       = $dir/certs/ca-cert.pem

crlnumber         = $dir/crlnumber
crl               = $dir/crl/ca.crl.pem
crl_extensions    = crl_ext
default_crl_days  = 30

default_md        = sha256
name_opt          = ca_default
cert_opt          = ca_default
default_days      = 365
preserve          = no
policy            = policy_strict

[ policy_strict ]
countryName             = match
stateOrProvinceName     = match
organizationName        = match
organizationalUnitName  = optional
commonName              = supplied
emailAddress            = optional

[ req ]
default_bits        = 4096
distinguished_name  = req_distinguished_name
string_mask         = utf8only
default_md          = sha256
x509_extensions     = v3_ca

[ req_distinguished_name ]
countryName                     = Country Name (2 letter code)
stateOrProvinceName             = State or Province Name
localityName                    = Locality Name
0.organizationName              = Organization Name
organizationalUnitName          = Organizational Unit Name
commonName                      = Common Name
emailAddress                    = Email Address

[ v3_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, cRLSign, keyCertSign

[ server_cert ]
basicConstraints = CA:FALSE
nsCertType = server
nsComment = "OpenSSL Generated Server Certificate"
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer:always
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth

[ client_cert ]
basicConstraints = CA:FALSE
nsCertType = client, email
nsComment = "OpenSSL Generated Client Certificate"
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
keyUsage = critical, nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth, emailProtection

[ crl_ext ]
authorityKeyIdentifier=keyid:always

[ ocsp ]
basicConstraints = CA:FALSE
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, OCSPSigning
EOF

    # Replace placeholder with actual CA directory
    sed -i "s|REPLACE_CA_DIR|${CA_DIR}|g" "${CA_DIR}/openssl.cnf"
}

# =============================================================================
# Service Certificate Generation
# =============================================================================

generate_service_certificate() {
    local service_name="$1"
    local san_list="$2"
    local service_cert_dir="${CERTS_DIR}/${service_name}"
    
    log_info "Generating certificates for service: ${service_name}"
    
    # Create service certificate directory
    mkdir -p "${service_cert_dir}"
    
    # Generate service private key
    if [[ ! -f "${service_cert_dir}/${service_name}-key.pem" ]]; then
        log_info "Generating private key for ${service_name}..."
        openssl genrsa -out "${service_cert_dir}/${service_name}-key.pem" ${KEY_SIZE}
        chmod 400 "${service_cert_dir}/${service_name}-key.pem"
    fi
    
    # Generate certificate signing request
    if [[ ! -f "${service_cert_dir}/${service_name}-csr.pem" ]]; then
        log_info "Generating CSR for ${service_name}..."
        
        # Create SAN extension file
        create_san_extension "${service_name}" "${san_list}"
        
        openssl req -new \
            -key "${service_cert_dir}/${service_name}-key.pem" \
            -out "${service_cert_dir}/${service_name}-csr.pem" \
            -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${OU}/CN=${service_name}.ai-workflow-engine.local" \
            -config "${service_cert_dir}/${service_name}-ext.cnf"
    fi
    
    # Sign certificate with CA
    if [[ ! -f "${service_cert_dir}/${service_name}-cert.pem" ]]; then
        log_info "Signing certificate for ${service_name}..."
        
        openssl ca -batch \
            -config "${CA_DIR}/openssl.cnf" \
            -extensions server_cert \
            -days ${CERT_VALIDITY_DAYS} \
            -notext \
            -md sha256 \
            -in "${service_cert_dir}/${service_name}-csr.pem" \
            -out "${service_cert_dir}/${service_name}-cert.pem"
        
        chmod 444 "${service_cert_dir}/${service_name}-cert.pem"
    fi
    
    # Create unified certificate file (cert + CA chain)
    cat "${service_cert_dir}/${service_name}-cert.pem" \
        "${CA_DIR}/certs/ca-cert.pem" > \
        "${service_cert_dir}/unified-cert.pem"
    
    # Create unified key file (for compatibility)
    cp "${service_cert_dir}/${service_name}-key.pem" \
       "${service_cert_dir}/unified-key.pem"
    
    # Copy CA cert to service directory
    cp "${CA_DIR}/certs/ca-cert.pem" "${service_cert_dir}/rootCA.pem"
    
    # Legacy filename compatibility
    cp "${service_cert_dir}/${service_name}-cert.pem" "${service_cert_dir}/server.crt"
    cp "${service_cert_dir}/${service_name}-key.pem" "${service_cert_dir}/server.key"
    cp "${CA_DIR}/certs/ca-cert.pem" "${service_cert_dir}/root.crt"
    
    # Set appropriate permissions
    chmod 400 "${service_cert_dir}"/*-key.pem "${service_cert_dir}/unified-key.pem" "${service_cert_dir}/server.key"
    chmod 444 "${service_cert_dir}"/*-cert.pem "${service_cert_dir}/unified-cert.pem" "${service_cert_dir}"/*.crt
    
    log_success "Certificates generated for ${service_name}"
}

create_san_extension() {
    local service_name="$1"
    local san_list="$2"
    local service_cert_dir="${CERTS_DIR}/${service_name}"
    
    # Convert comma-separated SAN list to proper format
    local san_entries=""
    local counter=1
    
    IFS=',' read -ra SANS <<< "$san_list"
    for san in "${SANS[@]}"; do
        san=$(echo "$san" | xargs)  # Trim whitespace
        if [[ $san =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            # IP address
            san_entries="${san_entries}IP.${counter} = ${san}\n"
        else
            # DNS name
            san_entries="${san_entries}DNS.${counter} = ${san}\n"
        fi
        ((counter++))
    done
    
    # Create extension file
    cat > "${service_cert_dir}/${service_name}-ext.cnf" << EOF
[ req ]
default_bits = 4096
prompt = no
distinguished_name = req_distinguished_name
req_extensions = v3_req

[ req_distinguished_name ]
C=${COUNTRY}
ST=${STATE}
L=${CITY}
O=${ORG}
OU=${OU}
CN=${service_name}.ai-workflow-engine.local

[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[ alt_names ]
$(echo -e "$san_entries")
EOF
}

# =============================================================================
# Client Certificate Generation
# =============================================================================

generate_client_certificate() {
    local client_name="$1"
    local client_cert_dir="${CERTS_DIR}/clients/${client_name}"
    
    log_info "Generating client certificate for: ${client_name}"
    
    # Create client certificate directory
    mkdir -p "${client_cert_dir}"
    
    # Generate client private key
    openssl genrsa -out "${client_cert_dir}/${client_name}-key.pem" ${KEY_SIZE}
    chmod 400 "${client_cert_dir}/${client_name}-key.pem"
    
    # Generate certificate signing request
    openssl req -new \
        -key "${client_cert_dir}/${client_name}-key.pem" \
        -out "${client_cert_dir}/${client_name}-csr.pem" \
        -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${OU}/CN=${client_name}"
    
    # Sign certificate with CA
    openssl ca -batch \
        -config "${CA_DIR}/openssl.cnf" \
        -extensions client_cert \
        -days ${CERT_VALIDITY_DAYS} \
        -notext \
        -md sha256 \
        -in "${client_cert_dir}/${client_name}-csr.pem" \
        -out "${client_cert_dir}/${client_name}-cert.pem"
    
    chmod 444 "${client_cert_dir}/${client_name}-cert.pem"
    
    # Copy CA cert to client directory
    cp "${CA_DIR}/certs/ca-cert.pem" "${client_cert_dir}/ca-cert.pem"
    
    log_success "Client certificate generated for ${client_name}"
}

# =============================================================================
# Certificate Validation and Management
# =============================================================================

validate_certificate() {
    local cert_file="$1"
    local ca_file="$2"
    
    if openssl verify -CAfile "$ca_file" "$cert_file" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_certificate_expiry() {
    local cert_file="$1"
    local days_threshold="${2:-30}"
    
    local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry_date" +%s)
    local current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    if [[ $days_until_expiry -lt $days_threshold ]]; then
        log_warning "Certificate $cert_file expires in $days_until_expiry days"
        return 1
    else
        log_info "Certificate $cert_file is valid for $days_until_expiry days"
        return 0
    fi
}

# =============================================================================
# Certificate Rotation
# =============================================================================

rotate_service_certificate() {
    local service_name="$1"
    local san_list="${SERVICES[$service_name]}"
    local service_cert_dir="${CERTS_DIR}/${service_name}"
    
    log_info "Rotating certificate for service: ${service_name}"
    
    # Backup existing certificates
    if [[ -f "${service_cert_dir}/${service_name}-cert.pem" ]]; then
        local backup_dir="${service_cert_dir}/backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "$backup_dir"
        cp "${service_cert_dir}"/*.pem "$backup_dir/" 2>/dev/null || true
        log_info "Backed up existing certificates to $backup_dir"
    fi
    
    # Remove existing certificates
    rm -f "${service_cert_dir}/${service_name}"-{cert,csr}.pem
    rm -f "${service_cert_dir}/unified-cert.pem"
    rm -f "${service_cert_dir}/server.crt"
    
    # Generate new certificate
    generate_service_certificate "$service_name" "$san_list"
    
    log_success "Certificate rotation completed for ${service_name}"
}

# =============================================================================
# Docker Secrets Integration
# =============================================================================

setup_docker_secrets() {
    log_info "Setting up Docker secrets for mTLS..."
    
    # Ensure secrets directory exists
    mkdir -p "${SECRETS_DIR}"
    
    # Copy CA certificate to secrets
    cp "${CA_DIR}/certs/ca-cert.pem" "${SECRETS_DIR}/mtls_ca_cert.pem"
    
    # Create service certificate bundles for Docker secrets
    for service_name in "${!SERVICES[@]}"; do
        local service_cert_dir="${CERTS_DIR}/${service_name}"
        
        if [[ -f "${service_cert_dir}/${service_name}-cert.pem" ]]; then
            # Create certificate bundle
            cat "${service_cert_dir}/${service_name}-cert.pem" \
                "${CA_DIR}/certs/ca-cert.pem" > \
                "${SECRETS_DIR}/${service_name}_cert_bundle.pem"
            
            # Copy private key
            cp "${service_cert_dir}/${service_name}-key.pem" \
               "${SECRETS_DIR}/${service_name}_private_key.pem"
            
            # Set appropriate permissions
            chmod 400 "${SECRETS_DIR}/${service_name}_private_key.pem"
            chmod 444 "${SECRETS_DIR}/${service_name}_cert_bundle.pem"
        fi
    done
    
    log_success "Docker secrets setup complete"
}

# =============================================================================
# Certificate Information Display
# =============================================================================

display_certificate_info() {
    local cert_file="$1"
    
    echo "Certificate Information for: $cert_file"
    echo "========================================="
    
    # Subject and issuer
    echo "Subject: $(openssl x509 -in "$cert_file" -noout -subject | sed 's/subject=//')"
    echo "Issuer: $(openssl x509 -in "$cert_file" -noout -issuer | sed 's/issuer=//')"
    
    # Validity dates
    echo "Valid From: $(openssl x509 -in "$cert_file" -noout -startdate | cut -d= -f2)"
    echo "Valid Until: $(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)"
    
    # Subject Alternative Names
    local sans=$(openssl x509 -in "$cert_file" -noout -text | grep -A1 "Subject Alternative Name" | tail -1 | sed 's/^[[:space:]]*//')
    if [[ -n "$sans" ]]; then
        echo "Subject Alternative Names: $sans"
    fi
    
    # Key usage
    local key_usage=$(openssl x509 -in "$cert_file" -noout -text | grep -A1 "Key Usage:" | tail -1 | sed 's/^[[:space:]]*//')
    if [[ -n "$key_usage" ]]; then
        echo "Key Usage: $key_usage"
    fi
    
    echo ""
}

# =============================================================================
# Main Execution Functions
# =============================================================================

generate_all_certificates() {
    log_info "Generating certificates for all services..."
    
    # Generate certificates for each service
    for service_name in "${!SERVICES[@]}"; do
        local san_list="${SERVICES[$service_name]}"
        generate_service_certificate "$service_name" "$san_list"
    done
    
    # Generate client certificates for admin access
    generate_client_certificate "admin"
    generate_client_certificate "monitoring"
    
    log_success "All service certificates generated"
}

validate_all_certificates() {
    log_info "Validating all certificates..."
    
    local ca_cert="${CA_DIR}/certs/ca-cert.pem"
    local validation_failed=0
    
    # Validate service certificates
    for service_name in "${!SERVICES[@]}"; do
        local service_cert="${CERTS_DIR}/${service_name}/${service_name}-cert.pem"
        
        if [[ -f "$service_cert" ]]; then
            if validate_certificate "$service_cert" "$ca_cert"; then
                log_success "Certificate valid: ${service_name}"
                check_certificate_expiry "$service_cert"
            else
                log_error "Certificate validation failed: ${service_name}"
                validation_failed=1
            fi
        else
            log_warning "Certificate not found: ${service_name}"
        fi
    done
    
    return $validation_failed
}

display_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup                   Setup complete mTLS infrastructure
    generate-ca             Generate only the Certificate Authority
    generate-service <name> Generate certificate for specific service
    generate-all            Generate certificates for all services
    rotate-service <name>   Rotate certificate for specific service
    rotate-all              Rotate all service certificates
    validate                Validate all certificates
    info <cert_file>        Display certificate information
    cleanup                 Remove all certificates (use with caution)

Options:
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output

Examples:
    $0 setup                # Complete setup
    $0 generate-service api # Generate API service certificate
    $0 rotate-service api   # Rotate API service certificate
    $0 validate             # Validate all certificates
    $0 info /path/to/cert   # Show certificate details

EOF
}

cleanup_certificates() {
    log_warning "This will remove ALL certificates and CA infrastructure!"
    read -p "Are you sure? Type 'YES' to confirm: " confirm
    
    if [[ "$confirm" == "YES" ]]; then
        log_info "Cleaning up certificates..."
        rm -rf "${CERTS_DIR}"
        rm -f "${SECRETS_DIR}"/mtls_*.pem
        rm -f "${SECRETS_DIR}"/*_{cert_bundle,private_key}.pem
        log_success "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    # Ensure required directories exist
    mkdir -p "${CERTS_DIR}" "${SECRETS_DIR}"
    
    case "${1:-setup}" in
        "setup")
            log_info "Setting up complete mTLS infrastructure..."
            setup_ca
            generate_all_certificates
            setup_docker_secrets
            validate_all_certificates
            log_success "mTLS infrastructure setup complete!"
            ;;
        "generate-ca")
            setup_ca
            ;;
        "generate-service")
            if [[ -z "${2:-}" ]]; then
                log_error "Service name required for generate-service command"
                exit 1
            fi
            if [[ -z "${SERVICES[$2]:-}" ]]; then
                log_error "Unknown service: $2"
                log_info "Available services: ${!SERVICES[*]}"
                exit 1
            fi
            setup_ca  # Ensure CA exists
            generate_service_certificate "$2" "${SERVICES[$2]}"
            ;;
        "generate-all")
            setup_ca  # Ensure CA exists
            generate_all_certificates
            setup_docker_secrets
            ;;
        "rotate-service")
            if [[ -z "${2:-}" ]]; then
                log_error "Service name required for rotate-service command"
                exit 1
            fi
            if [[ -z "${SERVICES[$2]:-}" ]]; then
                log_error "Unknown service: $2"
                exit 1
            fi
            rotate_service_certificate "$2"
            ;;
        "rotate-all")
            for service_name in "${!SERVICES[@]}"; do
                rotate_service_certificate "$service_name"
            done
            setup_docker_secrets
            ;;
        "validate")
            validate_all_certificates
            ;;
        "info")
            if [[ -z "${2:-}" ]]; then
                log_error "Certificate file path required for info command"
                exit 1
            fi
            if [[ ! -f "$2" ]]; then
                log_error "Certificate file not found: $2"
                exit 1
            fi
            display_certificate_info "$2"
            ;;
        "cleanup")
            cleanup_certificates
            ;;
        "-h"|"--help"|"help")
            display_usage
            exit 0
            ;;
        *)
            log_error "Unknown command: $1"
            display_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"