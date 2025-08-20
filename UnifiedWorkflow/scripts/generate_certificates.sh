#!/bin/bash

# =============================================================================
# Automatic Certificate Generation Script
# AI Workflow Engine - mTLS Certificate Automation
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

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

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to generate certificates using Docker Compose
generate_certificates() {
    log_info "Starting automatic certificate generation..."
    
    cd "${PROJECT_ROOT}"
    
    # Check if docker-compose-certs.yaml exists
    if [ ! -f "docker-compose-certs.yaml" ]; then
        log_error "docker-compose-certs.yaml not found!"
        exit 1
    fi
    
    # Run certificate generation
    log_info "Running certificate generation containers..."
    docker compose -f docker-compose-certs.yaml up --remove-orphans
    
    # Clean up containers
    log_info "Cleaning up certificate generation containers..."
    docker compose -f docker-compose-certs.yaml down --remove-orphans
    
    log_success "Automatic certificate generation completed!"
}

# Function to validate generated certificates
validate_certificates() {
    log_info "Validating generated certificates..."
    
    local cert_dir="${PROJECT_ROOT}/certs"
    local validation_failed=0
    
    # Services to validate
    local services=("api" "webui" "caddy_reverse_proxy" "postgres" "redis")
    
    # Check CA certificate
    if [ -f "${cert_dir}/ca/ca-cert.pem" ]; then
        log_success "CA certificate exists"
        
        # Validate CA certificate
        if openssl x509 -in "${cert_dir}/ca/ca-cert.pem" -noout -checkend 86400 > /dev/null 2>&1; then
            log_success "CA certificate is valid and not expiring within 24 hours"
        else
            log_warn "CA certificate may be expiring soon or invalid"
            validation_failed=1
        fi
    else
        log_error "CA certificate not found!"
        validation_failed=1
    fi
    
    # Check service certificates
    for service in "${services[@]}"; do
        local cert_file="${cert_dir}/${service}/${service}-cert.pem"
        local key_file="${cert_dir}/${service}/${service}-key.pem"
        local unified_cert="${cert_dir}/${service}/unified-cert.pem"
        local unified_key="${cert_dir}/${service}/unified-key.pem"
        
        if [ -f "${cert_file}" ] && [ -f "${key_file}" ]; then
            log_success "${service} certificates exist"
            
            # Validate certificate
            if openssl x509 -in "${cert_file}" -noout -checkend 86400 > /dev/null 2>&1; then
                log_success "${service} certificate is valid"
            else
                log_warn "${service} certificate may be expiring soon or invalid"
                validation_failed=1
            fi
            
            # Check unified certificates
            if [ -f "${unified_cert}" ] && [ -f "${unified_key}" ]; then
                log_success "${service} unified certificates exist"
            else
                log_warn "${service} unified certificates missing"
                validation_failed=1
            fi
        else
            log_error "${service} certificates not found!"
            validation_failed=1
        fi
    done
    
    if [ $validation_failed -eq 0 ]; then
        log_success "All certificate validation checks passed!"
        return 0
    else
        log_error "Some certificate validation checks failed!"
        return 1
    fi
}

# Function to show certificate information
show_certificate_info() {
    log_info "Certificate Information:"
    echo ""
    
    local cert_dir="${PROJECT_ROOT}/certs"
    
    # Show CA certificate info
    if [ -f "${cert_dir}/ca/ca-cert.pem" ]; then
        echo "=== CA Certificate ==="
        openssl x509 -in "${cert_dir}/ca/ca-cert.pem" -noout -subject -issuer -dates
        echo ""
    fi
    
    # Show service certificate info
    local services=("api" "webui" "caddy_reverse_proxy" "postgres" "redis")
    for service in "${services[@]}"; do
        local cert_file="${cert_dir}/${service}/${service}-cert.pem"
        if [ -f "${cert_file}" ]; then
            echo "=== ${service} Certificate ==="
            openssl x509 -in "${cert_file}" -noout -subject -issuer -dates
            echo ""
        fi
    done
}

# Function to renew certificates (regenerate all)
renew_certificates() {
    log_info "Renewing all certificates..."
    
    # Backup existing certificates
    local backup_dir="${PROJECT_ROOT}/certs_backup_$(date +%Y%m%d_%H%M%S)"
    if [ -d "${PROJECT_ROOT}/certs" ]; then
        log_info "Backing up existing certificates to ${backup_dir}"
        cp -r "${PROJECT_ROOT}/certs" "${backup_dir}"
    fi
    
    # Generate new certificates
    generate_certificates
    
    # Validate new certificates
    if validate_certificates; then
        log_success "Certificate renewal completed successfully!"
        log_info "Backup saved to: ${backup_dir}"
    else
        log_error "Certificate renewal validation failed!"
        log_info "Backup available at: ${backup_dir}"
        exit 1
    fi
}

# Function to clean up certificates
cleanup_certificates() {
    log_warn "Cleaning up all certificates..."
    
    local cert_dir="${PROJECT_ROOT}/certs"
    if [ -d "${cert_dir}" ]; then
        rm -rf "${cert_dir}"
        log_success "Certificates cleaned up!"
    else
        log_info "No certificates to clean up."
    fi
}

# Main function
main() {
    case "${1:-generate}" in
        "generate"|"g")
            generate_certificates
            validate_certificates
            ;;
        "validate"|"v")
            validate_certificates
            ;;
        "info"|"i")
            show_certificate_info
            ;;
        "renew"|"r")
            renew_certificates
            ;;
        "clean"|"c")
            cleanup_certificates
            ;;
        "help"|"h"|*)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  generate, g    Generate certificates (default)"
            echo "  validate, v    Validate existing certificates"
            echo "  info, i        Show certificate information"
            echo "  renew, r       Renew all certificates"
            echo "  clean, c       Clean up all certificates"
            echo "  help, h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Generate certificates"
            echo "  $0 generate        # Generate certificates"
            echo "  $0 validate        # Validate certificates"
            echo "  $0 renew           # Renew certificates"
            ;;
    esac
}

# Run main function with all arguments
main "$@"