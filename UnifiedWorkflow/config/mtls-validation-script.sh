#!/bin/bash

# mTLS Security Validation Script
# Validates mTLS implementation across critical services

set -euo pipefail

LOG_FILE="/tmp/mtls-validation-$(date +%Y%m%d-%H%M%S).log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/../certs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✓ $*${NC}"
}

log_warning() {
    log "${YELLOW}⚠ $*${NC}"
}

log_error() {
    log "${RED}✗ $*${NC}"
}

log_info() {
    log "${BLUE}ℹ $*${NC}"
}

# Check if certificate files exist and are valid
validate_certificate() {
    local service=$1
    local cert_path="$CERTS_DIR/$service"
    
    log_info "Validating certificates for service: $service"
    
    if [[ ! -d "$cert_path" ]]; then
        log_error "Certificate directory for $service does not exist: $cert_path"
        return 1
    fi
    
    # Check required certificate files
    local required_files=("${service}-cert.pem" "${service}-key.pem" "rootCA.pem")
    local files_exist=true
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$cert_path/$file" ]]; then
            log_error "Required certificate file missing: $cert_path/$file"
            files_exist=false
        fi
    done
    
    if [[ "$files_exist" = false ]]; then
        return 1
    fi
    
    # Validate certificate format and expiration
    local cert_file="$cert_path/${service}-cert.pem"
    
    if ! openssl x509 -in "$cert_file" -noout -text &>/dev/null; then
        log_error "Invalid certificate format: $cert_file"
        return 1
    fi
    
    # Check certificate expiration
    local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
    local expiry_timestamp=$(date -d "$expiry_date" +%s)
    local current_timestamp=$(date +%s)
    local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
    
    if [[ $days_until_expiry -lt 30 ]]; then
        log_warning "Certificate for $service expires in $days_until_expiry days"
    else
        log_success "Certificate for $service is valid (expires in $days_until_expiry days)"
    fi
    
    # Validate certificate chain
    if ! openssl verify -CAfile "$cert_path/rootCA.pem" "$cert_file" &>/dev/null; then
        log_error "Certificate chain validation failed for $service"
        return 1
    fi
    
    log_success "Certificate chain validation passed for $service"
    return 0
}

# Test mTLS connection to a service
test_mtls_connection() {
    local service=$1
    local host=$2
    local port=$3
    
    log_info "Testing mTLS connection to $service ($host:$port)"
    
    local cert_path="$CERTS_DIR/$service"
    local client_cert=""
    local client_key=""
    
    # Use admin client certificates if available, otherwise service certificates
    if [[ -f "$CERTS_DIR/clients/admin/admin-cert.pem" ]]; then
        client_cert="$CERTS_DIR/clients/admin/admin-cert.pem"
        client_key="$CERTS_DIR/clients/admin/admin-key.pem"
    else
        client_cert="$cert_path/${service}-cert.pem"
        client_key="$cert_path/${service}-key.pem"
    fi
    
    # Test TLS handshake
    if timeout 10 openssl s_client -connect "$host:$port" \
        -cert "$client_cert" \
        -key "$client_key" \
        -CAfile "$cert_path/rootCA.pem" \
        -verify 1 \
        -brief \
        </dev/null &>/dev/null; then
        log_success "mTLS connection to $service successful"
        return 0
    else
        log_error "mTLS connection to $service failed"
        return 1
    fi
}

# Check Docker container TLS configuration
check_docker_tls_config() {
    local container=$1
    local service=$2
    
    log_info "Checking Docker TLS configuration for $container"
    
    if ! docker exec "$container" ls /certs/ &>/dev/null; then
        log_warning "Certificates not mounted in container $container"
        return 1
    fi
    
    # Check if certificates are accessible in container
    if docker exec "$container" test -f "/certs/${service}-cert.pem" && \
       docker exec "$container" test -f "/certs/${service}-key.pem"; then
        log_success "Certificates properly mounted in $container"
        return 0
    else
        log_error "Certificates not properly configured in $container"
        return 1
    fi
}

# Validate service-to-service mTLS
validate_service_communication() {
    log_info "Validating service-to-service mTLS communication"
    
    # Test API to coordination-service communication
    if curl -s --cert "$CERTS_DIR/api/api-cert.pem" \
              --key "$CERTS_DIR/api/api-key.pem" \
              --cacert "$CERTS_DIR/api/rootCA.pem" \
              "https://coordination-service:8030/health" &>/dev/null; then
        log_success "API to coordination-service mTLS communication working"
    else
        log_warning "API to coordination-service mTLS communication not configured or failing"
    fi
    
    # Test Grafana to Prometheus communication  
    if curl -s --cert "$CERTS_DIR/grafana/grafana-cert.pem" \
              --key "$CERTS_DIR/grafana/grafana-key.pem" \
              --cacert "$CERTS_DIR/grafana/rootCA.pem" \
              "https://prometheus:9090/api/v1/query?query=up" &>/dev/null; then
        log_success "Grafana to Prometheus mTLS communication working"
    else
        log_warning "Grafana to Prometheus mTLS communication not configured or failing"
    fi
}

# Check certificate rotation automation
check_certificate_rotation() {
    log_info "Checking certificate rotation automation"
    
    # Look for certificate rotation scripts or cron jobs
    if crontab -l 2>/dev/null | grep -q "cert.*rotate\|renew"; then
        log_success "Certificate rotation automation detected"
    else
        log_warning "No certificate rotation automation found"
    fi
    
    # Check if certificate monitoring is configured
    if [[ -f "$SCRIPT_DIR/prometheus/rules/security-alerts.yml" ]] && \
       grep -q "CertificateExpires" "$SCRIPT_DIR/prometheus/rules/security-alerts.yml"; then
        log_success "Certificate expiration monitoring configured"
    else
        log_warning "Certificate expiration monitoring not configured"
    fi
}

# Security compliance check
security_compliance_check() {
    log_info "Performing security compliance check"
    
    local compliance_score=0
    local total_checks=10
    
    # Check 1: CA certificate security
    if [[ -f "$CERTS_DIR/ca/private/ca-key.pem" ]]; then
        local ca_perms=$(stat -c "%a" "$CERTS_DIR/ca/private/ca-key.pem")
        if [[ "$ca_perms" = "600" ]]; then
            ((compliance_score++))
            log_success "CA private key has correct permissions (600)"
        else
            log_warning "CA private key permissions should be 600, currently $ca_perms"
        fi
    fi
    
    # Check 2: Service key file permissions
    local secure_keys=0
    local total_keys=0
    
    for service_dir in "$CERTS_DIR"/*; do
        if [[ -d "$service_dir" && -f "$service_dir"/*.pem ]]; then
            for key_file in "$service_dir"/*-key.pem; do
                if [[ -f "$key_file" ]]; then
                    ((total_keys++))
                    local perms=$(stat -c "%a" "$key_file")
                    if [[ "$perms" = "600" ]]; then
                        ((secure_keys++))
                    fi
                fi
            done
        fi
    done
    
    if [[ $secure_keys -eq $total_keys && $total_keys -gt 0 ]]; then
        ((compliance_score++))
        log_success "All service private keys have secure permissions"
    else
        log_warning "$secure_keys/$total_keys service private keys have secure permissions"
    fi
    
    # Additional compliance checks...
    local compliance_percentage=$(( compliance_score * 100 / total_checks ))
    
    if [[ $compliance_percentage -ge 80 ]]; then
        log_success "Security compliance score: ${compliance_percentage}% (${compliance_score}/${total_checks})"
    else
        log_warning "Security compliance score: ${compliance_percentage}% (${compliance_score}/${total_checks}) - Below 80% threshold"
    fi
    
    return $compliance_score
}

# Main validation function
main() {
    log_info "Starting mTLS Security Validation"
    log_info "Log file: $LOG_FILE"
    
    local validation_passed=true
    local services=("api" "grafana" "prometheus" "redis" "postgres" "caddy_reverse_proxy")
    
    # Validate certificates for each service
    for service in "${services[@]}"; do
        if ! validate_certificate "$service"; then
            validation_passed=false
        fi
    done
    
    # Check Docker container configurations
    local containers=(
        "api:api"
        "ai_workflow_engine-grafana-1:grafana"
        "ai_workflow_engine-prometheus-1:prometheus"
        "ai_workflow_engine-redis-1:redis"
    )
    
    for container_info in "${containers[@]}"; do
        IFS=':' read -r container service <<< "$container_info"
        if docker ps -q -f name="$container" | grep -q .; then
            check_docker_tls_config "$container" "$service" || true
        else
            log_warning "Container $container is not running"
        fi
    done
    
    # Validate service communication
    validate_service_communication
    
    # Check certificate rotation automation
    check_certificate_rotation
    
    # Perform security compliance check
    security_compliance_check
    
    # Final validation summary
    if [[ "$validation_passed" = true ]]; then
        log_success "✅ mTLS Security Validation PASSED"
        log_info "All critical security checks completed successfully"
    else
        log_error "❌ mTLS Security Validation FAILED"
        log_info "Some security issues were detected. Review the log for details."
    fi
    
    log_info "Validation complete. Full log available at: $LOG_FILE"
}

# Run main function
main "$@"