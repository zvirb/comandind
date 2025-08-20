#!/bin/bash

# =============================================================================
# SSL Certificate Validation Script
# AI Workflow Engine - Validate SSL configuration for both mTLS and non-mTLS modes
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/certs"

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
# Certificate Validation Functions
# =============================================================================

check_certificate_exists() {
    local cert_path="$1"
    local service_name="$2"
    
    if [[ -f "$cert_path" ]]; then
        log_success "Certificate found for $service_name: $cert_path"
        return 0
    else
        log_warning "Certificate not found for $service_name: $cert_path"
        return 1
    fi
}

validate_certificate() {
    local cert_path="$1"
    local service_name="$2"
    
    if [[ ! -f "$cert_path" ]]; then
        log_error "Certificate file not found: $cert_path"
        return 1
    fi
    
    # Check certificate validity
    local expiry_seconds
    if expiry_seconds=$(openssl x509 -in "$cert_path" -noout -checkend 0 2>/dev/null); then
        local expiry_date
        expiry_date=$(openssl x509 -in "$cert_path" -noout -enddate | cut -d= -f2)
        
        # Check if certificate expires within 30 days
        if openssl x509 -in "$cert_path" -noout -checkend 2592000 >/dev/null 2>&1; then
            log_success "$service_name certificate is valid until: $expiry_date"
        else
            log_warning "$service_name certificate expires within 30 days: $expiry_date"
        fi
        
        # Show subject and SAN
        local subject
        subject=$(openssl x509 -in "$cert_path" -noout -subject | sed 's/subject=//')
        log_info "$service_name certificate subject: $subject"
        
        # Check Subject Alternative Names
        local sans
        if sans=$(openssl x509 -in "$cert_path" -noout -text | grep -A1 "Subject Alternative Name" | tail -1 | sed 's/^[[:space:]]*//' 2>/dev/null); then
            log_info "$service_name certificate SANs: $sans"
        fi
        
        return 0
    else
        log_error "$service_name certificate is expired or invalid"
        return 1
    fi
}

check_mtls_infrastructure() {
    log_info "Checking mTLS infrastructure..."
    
    local ca_cert="${CERTS_DIR}/ca/certs/ca-cert.pem"
    local mtls_services=(
        "api"
        "webui"
        "caddy_reverse_proxy"
        "postgres"
        "pgbouncer"
        "qdrant"
        "prometheus"
    )
    
    local mtls_ready=true
    
    # Check CA certificate
    if check_certificate_exists "$ca_cert" "Certificate Authority"; then
        if validate_certificate "$ca_cert" "CA"; then
            log_success "CA certificate is valid"
        else
            log_error "CA certificate validation failed"
            mtls_ready=false
        fi
    else
        log_error "CA certificate not found - mTLS infrastructure not set up"
        mtls_ready=false
    fi
    
    # Check service certificates
    for service in "${mtls_services[@]}"; do
        local service_cert="${CERTS_DIR}/${service}/${service}-cert.pem"
        local unified_cert="${CERTS_DIR}/${service}/unified-cert.pem"
        
        if check_certificate_exists "$service_cert" "$service"; then
            if validate_certificate "$service_cert" "$service"; then
                log_success "$service certificate is valid"
            else
                log_error "$service certificate validation failed"
                mtls_ready=false
            fi
        elif check_certificate_exists "$unified_cert" "$service (unified)"; then
            if validate_certificate "$unified_cert" "$service (unified)"; then
                log_success "$service unified certificate is valid"
            else
                log_error "$service unified certificate validation failed"
                mtls_ready=false
            fi
        else
            log_warning "$service certificate not found"
            mtls_ready=false
        fi
    done
    
    if $mtls_ready; then
        log_success "mTLS infrastructure is ready"
        return 0
    else
        log_warning "mTLS infrastructure is incomplete or has issues"
        return 1
    fi
}

check_dev_certificates() {
    log_info "Checking development certificates..."
    
    local dev_services=("api" "webui" "caddy_reverse_proxy")
    local dev_ready=true
    
    for service in "${dev_services[@]}"; do
        local server_cert="${CERTS_DIR}/${service}/server.crt"
        local server_key="${CERTS_DIR}/${service}/server.key"
        
        if check_certificate_exists "$server_cert" "$service (dev)"; then
            if validate_certificate "$server_cert" "$service (dev)"; then
                log_success "$service development certificate is valid"
                
                # Check if private key exists
                if [[ -f "$server_key" ]]; then
                    log_success "$service private key found"
                else
                    log_warning "$service private key not found"
                    dev_ready=false
                fi
            else
                log_error "$service development certificate validation failed"
                dev_ready=false
            fi
        else
            log_warning "$service development certificate not found"
            dev_ready=false
        fi
    done
    
    if $dev_ready; then
        log_success "Development certificates are ready"
        return 0
    else
        log_warning "Development certificates are incomplete or have issues"
        return 1
    fi
}

test_ssl_connectivity() {
    local host="${1:-localhost}"
    local port="${2:-443}"
    
    log_info "Testing SSL connectivity to $host:$port..."
    
    # Test SSL connection
    if timeout 10 openssl s_client -connect "$host:$port" -verify_return_error >/dev/null 2>&1; then
        log_success "SSL connection to $host:$port successful"
        return 0
    else
        log_warning "SSL connection to $host:$port failed (this may be expected in development)"
        
        # Try to get more information about the failure
        if timeout 5 openssl s_client -connect "$host:$port" </dev/null 2>&1 | grep -q "certificate verify failed"; then
            log_info "Certificate verification failed (expected for self-signed certificates)"
        elif timeout 5 openssl s_client -connect "$host:$port" </dev/null 2>&1 | grep -q "Connection refused"; then
            log_warning "Connection refused - service may not be running"
        fi
        
        return 1
    fi
}

check_service_health() {
    local service_url="$1"
    local service_name="$2"
    
    log_info "Checking health of $service_name..."
    
    # Test HTTP health check
    if curl -s -f -m 10 "$service_url" >/dev/null 2>&1; then
        log_success "$service_name health check passed"
        return 0
    else
        log_warning "$service_name health check failed"
        return 1
    fi
}

generate_ssl_report() {
    local output_file="${PROJECT_ROOT}/ssl_validation_report.txt"
    
    log_info "Generating SSL validation report..."
    
    {
        echo "SSL Certificate Validation Report"
        echo "Generated on: $(date)"
        echo "========================================"
        echo
        
        echo "1. mTLS Infrastructure Status"
        echo "-----------------------------"
        if check_mtls_infrastructure >/dev/null 2>&1; then
            echo "✅ mTLS infrastructure is ready"
        else
            echo "❌ mTLS infrastructure needs setup"
        fi
        echo
        
        echo "2. Development Certificates Status"
        echo "----------------------------------"
        if check_dev_certificates >/dev/null 2>&1; then
            echo "✅ Development certificates are ready"
        else
            echo "❌ Development certificates need generation"
        fi
        echo
        
        echo "3. Certificate Details"
        echo "----------------------"
        
        # List all certificates found
        if [[ -d "$CERTS_DIR" ]]; then
            find "$CERTS_DIR" -name "*.pem" -o -name "*.crt" | while read -r cert_file; do
                if [[ -f "$cert_file" ]]; then
                    echo "Certificate: $cert_file"
                    local subject
                    subject=$(openssl x509 -in "$cert_file" -noout -subject 2>/dev/null | sed 's/subject=//' || echo "Invalid certificate")
                    echo "  Subject: $subject"
                    local expiry
                    expiry=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "Cannot determine expiry")
                    echo "  Expires: $expiry"
                    echo
                fi
            done
        else
            echo "No certificates directory found"
        fi
        
        echo "4. Recommendations"
        echo "------------------"
        
        if ! check_mtls_infrastructure >/dev/null 2>&1; then
            echo "• Run 'scripts/security/setup_mtls_infrastructure.sh setup' for full mTLS"
        fi
        
        if ! check_dev_certificates >/dev/null 2>&1; then
            echo "• Run 'scripts/generate_dev_certificates.sh generate' for development certificates"
        fi
        
        echo "• Use 'docker-compose -f docker-compose-mtls.yml' for mTLS mode"
        echo "• Use 'docker-compose -f docker-compose.yml -f docker-compose.override-nossl.yml' for SSL-less development"
        
    } > "$output_file"
    
    log_success "SSL validation report generated: $output_file"
}

display_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    check-mtls           Check mTLS infrastructure status
    check-dev            Check development certificates status
    check-all            Check both mTLS and development certificates
    test-connectivity    Test SSL connectivity to localhost
    health-check         Check service health endpoints
    generate-report      Generate comprehensive SSL validation report
    help                 Show this help message

Options:
    --host HOST          Specify host for connectivity tests (default: localhost)
    --port PORT          Specify port for connectivity tests (default: 443)
    --verbose            Enable verbose output

Examples:
    $0 check-all                    # Check all certificate configurations
    $0 test-connectivity --host api --port 8000  # Test API SSL connectivity
    $0 health-check                 # Check service health endpoints
    $0 generate-report              # Generate comprehensive report

EOF
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    local command="${1:-check-all}"
    local host="localhost"
    local port="443"
    local verbose=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                host="$2"
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            -h|--help|help)
                display_usage
                exit 0
                ;;
            check-mtls|check-dev|check-all|test-connectivity|health-check|generate-report)
                command="$1"
                shift
                ;;
            *)
                if [[ "$1" != "${command}" ]]; then
                    log_error "Unknown option: $1"
                    display_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    case "$command" in
        "check-mtls")
            check_mtls_infrastructure
            ;;
        "check-dev")
            check_dev_certificates
            ;;
        "check-all")
            log_info "Performing comprehensive SSL certificate validation..."
            echo
            
            local mtls_status=0
            local dev_status=0
            
            check_mtls_infrastructure || mtls_status=1
            echo
            check_dev_certificates || dev_status=1
            echo
            
            if [[ $mtls_status -eq 0 ]]; then
                log_success "Recommendation: Use docker-compose-mtls.yml for production-like environment"
            elif [[ $dev_status -eq 0 ]]; then
                log_success "Recommendation: Use standard docker-compose.yml with development certificates"
            else
                log_warning "Recommendation: Use docker-compose.override-nossl.yml for SSL-less development"
                log_info "Or generate certificates with:"
                log_info "  scripts/security/setup_mtls_infrastructure.sh setup    # For full mTLS"
                log_info "  scripts/generate_dev_certificates.sh generate          # For development"
            fi
            ;;
        "test-connectivity")
            test_ssl_connectivity "$host" "$port"
            ;;
        "health-check")
            log_info "Checking service health endpoints..."
            check_service_health "http://localhost:8000/health" "API (HTTP)"
            check_service_health "https://localhost:8000/health" "API (HTTPS)"
            check_service_health "http://localhost:3000" "WebUI (HTTP)"
            check_service_health "https://localhost" "WebUI via Caddy (HTTPS)"
            ;;
        "generate-report")
            generate_ssl_report
            ;;
        *)
            log_error "Unknown command: $command"
            display_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"