#!/bin/bash

# =============================================================================
# Development SSL Certificate Generator
# AI Workflow Engine - Simple SSL Setup for Non-mTLS Development
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/certs"

# Certificate configuration
CERT_VALIDITY_DAYS=365
KEY_SIZE=2048
COUNTRY="US"
STATE="California"
CITY="San Francisco"
ORG="AI Workflow Engine Dev"
OU="Development"

# Services that need certificates
SERVICES=(
    "api"
    "webui"
    "caddy_reverse_proxy"
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
# Simple Self-Signed Certificate Generation
# =============================================================================

generate_self_signed_cert() {
    local service_name="$1"
    local service_cert_dir="${CERTS_DIR}/${service_name}"
    
    log_info "Generating self-signed certificate for: ${service_name}"
    
    # Create service certificate directory
    mkdir -p "${service_cert_dir}"
    
    # Generate private key
    openssl genrsa -out "${service_cert_dir}/server.key" ${KEY_SIZE}
    chmod 400 "${service_cert_dir}/server.key"
    
    # Create certificate configuration with SAN
    cat > "${service_cert_dir}/cert.conf" << EOF
[req]
default_bits = ${KEY_SIZE}
prompt = no
distinguished_name = req_distinguished_name
req_extensions = v3_req

[req_distinguished_name]
C=${COUNTRY}
ST=${STATE}
L=${CITY}
O=${ORG}
OU=${OU}
CN=localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
DNS.3 = *.local
DNS.4 = ${service_name}
DNS.5 = ${service_name}.ai-workflow-engine.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

    # Generate self-signed certificate
    openssl req -new -x509 \
        -key "${service_cert_dir}/server.key" \
        -out "${service_cert_dir}/server.crt" \
        -days ${CERT_VALIDITY_DAYS} \
        -config "${service_cert_dir}/cert.conf" \
        -extensions v3_req
    
    chmod 444 "${service_cert_dir}/server.crt"
    
    # Create unified certificate files for compatibility
    cp "${service_cert_dir}/server.crt" "${service_cert_dir}/unified-cert.pem"
    cp "${service_cert_dir}/server.key" "${service_cert_dir}/unified-key.pem"
    
    # Create a simple root CA file (same as server cert for self-signed)
    cp "${service_cert_dir}/server.crt" "${service_cert_dir}/rootCA.pem"
    cp "${service_cert_dir}/server.crt" "${service_cert_dir}/root.crt"
    
    # Clean up temporary config
    rm "${service_cert_dir}/cert.conf"
    
    log_success "Self-signed certificate generated for ${service_name}"
}

# =============================================================================
# Certificate Validation
# =============================================================================

validate_certificate() {
    local cert_file="$1"
    
    if [[ ! -f "$cert_file" ]]; then
        log_error "Certificate file not found: $cert_file"
        return 1
    fi
    
    # Check if certificate is valid
    if openssl x509 -in "$cert_file" -noout -checkend 86400 >/dev/null 2>&1; then
        local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
        log_success "Certificate valid until: $expiry_date"
        return 0
    else
        log_error "Certificate is expired or will expire within 24 hours"
        return 1
    fi
}

# =============================================================================
# Main Functions
# =============================================================================

generate_all_dev_certificates() {
    log_info "Generating development certificates for all services..."
    
    for service in "${SERVICES[@]}"; do
        generate_self_signed_cert "$service"
    done
    
    log_success "All development certificates generated"
}

validate_all_certificates() {
    log_info "Validating all development certificates..."
    
    local validation_failed=0
    
    for service in "${SERVICES[@]}"; do
        local cert_file="${CERTS_DIR}/${service}/server.crt"
        
        if validate_certificate "$cert_file"; then
            log_success "Certificate valid: ${service}"
        else
            log_error "Certificate validation failed: ${service}"
            validation_failed=1
        fi
    done
    
    return $validation_failed
}

display_certificate_info() {
    local service_name="$1"
    local cert_file="${CERTS_DIR}/${service_name}/server.crt"
    
    if [[ ! -f "$cert_file" ]]; then
        log_error "Certificate not found for service: $service_name"
        return 1
    fi
    
    echo "Certificate Information for: $service_name"
    echo "========================================="
    
    # Subject and issuer
    echo "Subject: $(openssl x509 -in "$cert_file" -noout -subject | sed 's/subject=//')"
    echo "Issuer: $(openssl x509 -in "$cert_file" -noout -issuer | sed 's/issuer=//')"
    
    # Validity dates
    echo "Valid From: $(openssl x509 -in "$cert_file" -noout -startdate | cut -d= -f2)"
    echo "Valid Until: $(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)"
    
    # Subject Alternative Names
    local sans=$(openssl x509 -in "$cert_file" -noout -text | grep -A1 "Subject Alternative Name" | tail -1 | sed 's/^[[:space:]]*//' || echo "None")
    echo "Subject Alternative Names: $sans"
    
    echo ""
}

cleanup_certificates() {
    log_warning "This will remove ALL development certificates!"
    read -p "Are you sure? Type 'YES' to confirm: " confirm
    
    if [[ "$confirm" == "YES" ]]; then
        log_info "Cleaning up development certificates..."
        for service in "${SERVICES[@]}"; do
            rm -rf "${CERTS_DIR}/${service}"
        done
        log_success "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

check_existing_certificates() {
    log_info "Checking for existing certificates..."
    
    local has_certificates=false
    
    for service in "${SERVICES[@]}"; do
        local cert_file="${CERTS_DIR}/${service}/server.crt"
        if [[ -f "$cert_file" ]]; then
            if validate_certificate "$cert_file"; then
                log_success "Valid certificate found for: $service"
                has_certificates=true
            else
                log_warning "Expired certificate found for: $service"
            fi
        else
            log_info "No certificate found for: $service"
        fi
    done
    
    if $has_certificates; then
        log_info "Some valid certificates exist. Use 'regenerate' to force recreation."
        return 0
    else
        log_info "No valid certificates found. Generating new ones..."
        return 1
    fi
}

display_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    generate         Generate development certificates for all services (skip if valid certs exist)
    regenerate       Force regenerate all development certificates
    validate         Validate all existing certificates
    info <service>   Display certificate information for a service
    check            Check existing certificate status
    cleanup          Remove all development certificates
    help             Show this help message

Services: ${SERVICES[*]}

Examples:
    $0 generate              # Generate certificates if needed
    $0 regenerate            # Force regenerate all certificates
    $0 info api              # Show API certificate details
    $0 validate              # Check all certificate validity

Note: This script generates simple self-signed certificates for development.
For production or full mTLS setup, use scripts/security/setup_mtls_infrastructure.sh

EOF
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    # Ensure certs directory exists
    mkdir -p "${CERTS_DIR}"
    
    case "${1:-generate}" in
        "generate")
            if check_existing_certificates; then
                log_info "Valid certificates already exist. Use 'regenerate' to force recreation."
            else
                generate_all_dev_certificates
            fi
            ;;
        "regenerate")
            log_info "Force regenerating all development certificates..."
            generate_all_dev_certificates
            ;;
        "validate")
            validate_all_certificates
            ;;
        "info")
            if [[ -z "${2:-}" ]]; then
                log_error "Service name required for info command"
                log_info "Available services: ${SERVICES[*]}"
                exit 1
            fi
            display_certificate_info "$2"
            ;;
        "check")
            check_existing_certificates
            ;;
        "cleanup")
            cleanup_certificates
            ;;
        "help"|"-h"|"--help")
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