#!/bin/bash

# =============================================================================
# Automated Certificate Rotation for AI Workflow Engine
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERTS_DIR="${PROJECT_ROOT}/certs"
LOGS_DIR="${PROJECT_ROOT}/logs"
ROTATION_LOG="${LOGS_DIR}/certificate_rotation.log"

# Certificate thresholds
EXPIRY_WARNING_DAYS=30
EXPIRY_CRITICAL_DAYS=7
ROTATION_THRESHOLD_DAYS=30

# Service definitions (must match setup script)
declare -A SERVICES=(
    ["api"]="api,localhost,127.0.0.1,api.ai-workflow-engine.local"
    ["worker"]="worker,localhost,127.0.0.1,worker.ai-workflow-engine.local"
    ["postgres"]="postgres,localhost,127.0.0.1,postgres.ai-workflow-engine.local"
    ["pgbouncer"]="pgbouncer,localhost,127.0.0.1,pgbouncer.ai-workflow-engine.local"
    ["redis"]="redis,localhost,127.0.0.1,redis.ai-workflow-engine.local"
    ["qdrant"]="qdrant,localhost,127.0.0.1,qdrant.ai-workflow-engine.local"
    ["ollama"]="ollama,localhost,127.0.0.1,ollama.ai-workflow-engine.local"
    ["caddy_reverse_proxy"]="caddy,localhost,127.0.0.1,*.ai-workflow-engine.local"
    ["webui"]="webui,localhost,127.0.0.1,webui.ai-workflow-engine.local"
    ["prometheus"]="prometheus,localhost,127.0.0.1,prometheus.ai-workflow-engine.local"
    ["grafana"]="grafana,localhost,127.0.0.1,grafana.ai-workflow-engine.local"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    local message="$1"
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]${NC} $message" | tee -a "$ROTATION_LOG"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $message" | tee -a "$ROTATION_LOG"
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING]${NC} $message" | tee -a "$ROTATION_LOG"
}

log_error() {
    local message="$1"
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $message" | tee -a "$ROTATION_LOG"
}

# =============================================================================
# Certificate Expiry Checking
# =============================================================================

get_certificate_expiry_days() {
    local cert_file="$1"
    
    if [[ ! -f "$cert_file" ]]; then
        echo "-1"  # Certificate doesn't exist
        return
    fi
    
    local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
    local current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    echo "$days_until_expiry"
}

check_certificate_status() {
    local service_name="$1"
    local cert_file="${CERTS_DIR}/${service_name}/${service_name}-cert.pem"
    local days_until_expiry
    
    days_until_expiry=$(get_certificate_expiry_days "$cert_file")
    
    if [[ "$days_until_expiry" -eq -1 ]]; then
        echo "MISSING"
        return 2
    elif [[ "$days_until_expiry" -le 0 ]]; then
        echo "EXPIRED"
        return 3
    elif [[ "$days_until_expiry" -le $EXPIRY_CRITICAL_DAYS ]]; then
        echo "CRITICAL"
        return 1
    elif [[ "$days_until_expiry" -le $EXPIRY_WARNING_DAYS ]]; then
        echo "WARNING"
        return 1
    else
        echo "VALID"
        return 0
    fi
}

# =============================================================================
# Certificate Rotation Logic
# =============================================================================

needs_rotation() {
    local service_name="$1"
    local cert_file="${CERTS_DIR}/${service_name}/${service_name}-cert.pem"
    local days_until_expiry
    
    days_until_expiry=$(get_certificate_expiry_days "$cert_file")
    
    # Rotate if certificate is missing, expired, or within rotation threshold
    if [[ "$days_until_expiry" -eq -1 ]] || \
       [[ "$days_until_expiry" -le 0 ]] || \
       [[ "$days_until_expiry" -le $ROTATION_THRESHOLD_DAYS ]]; then
        return 0  # Needs rotation
    else
        return 1  # No rotation needed
    fi
}

rotate_service_certificate() {
    local service_name="$1"
    local force="${2:-false}"
    
    log_info "Checking rotation need for service: $service_name"
    
    if [[ "$force" == "true" ]] || needs_rotation "$service_name"; then
        log_info "Rotating certificate for service: $service_name"
        
        # Call the main setup script to rotate the certificate
        if "${SCRIPT_DIR}/setup_mtls_infrastructure.sh" rotate-service "$service_name"; then
            log_success "Certificate rotation completed for $service_name"
            return 0
        else
            log_error "Certificate rotation failed for $service_name"
            return 1
        fi
    else
        local days_until_expiry=$(get_certificate_expiry_days "${CERTS_DIR}/${service_name}/${service_name}-cert.pem")
        log_info "Certificate for $service_name is valid for $days_until_expiry days - no rotation needed"
        return 0
    fi
}

# =============================================================================
# Docker Service Management
# =============================================================================

get_service_container_name() {
    local service_name="$1"
    
    # Map service names to Docker container names
    case "$service_name" in
        "caddy_reverse_proxy") echo "ai_workflow_engine-caddy_reverse_proxy-1" ;;
        *) echo "ai_workflow_engine-${service_name}-1" ;;
    esac
}

restart_service_after_rotation() {
    local service_name="$1"
    local container_name
    
    container_name=$(get_service_container_name "$service_name")
    
    log_info "Restarting service $service_name (container: $container_name)"
    
    # Check if container exists and is running
    if docker ps --format "table {{.Names}}" | grep -q "^$container_name$"; then
        if docker restart "$container_name"; then
            log_success "Service $service_name restarted successfully"
            
            # Wait for service to be healthy
            local max_wait=60
            local wait_count=0
            
            while [[ $wait_count -lt $max_wait ]]; do
                if docker ps --filter "name=$container_name" --filter "health=healthy" --format "{{.Names}}" | grep -q "^$container_name$"; then
                    log_success "Service $service_name is healthy after restart"
                    return 0
                fi
                
                sleep 2
                ((wait_count += 2))
            done
            
            log_warning "Service $service_name restart completed but health check timeout"
            return 0
        else
            log_error "Failed to restart service $service_name"
            return 1
        fi
    else
        log_warning "Container $container_name is not running - skipping restart"
        return 0
    fi
}

# =============================================================================
# Monitoring and Alerting
# =============================================================================

send_rotation_notification() {
    local service_name="$1"
    local status="$2"
    local days_until_expiry="$3"
    
    # Create notification message
    local message="Certificate Rotation Alert - Service: $service_name, Status: $status"
    if [[ "$days_until_expiry" != "-1" ]]; then
        message="$message, Days until expiry: $days_until_expiry"
    fi
    
    # Log the notification
    case "$status" in
        "EXPIRED"|"CRITICAL"|"MISSING")
            log_error "$message"
            ;;
        "WARNING")
            log_warning "$message"
            ;;
        *)
            log_info "$message"
            ;;
    esac
    
    # Here you could add integration with external alerting systems
    # Examples: Slack, Discord, email, PagerDuty, etc.
    # send_slack_notification "$message"
    # send_email_notification "$message"
}

generate_rotation_report() {
    local report_file="${LOGS_DIR}/certificate_rotation_report_$(date +%Y%m%d_%H%M%S).json"
    
    log_info "Generating certificate rotation report..."
    
    # Start JSON report
    echo "{" > "$report_file"
    echo "  \"timestamp\": \"$(date -Iseconds)\"," >> "$report_file"
    echo "  \"certificates\": {" >> "$report_file"
    
    local first_service=true
    local total_services=0
    local services_rotated=0
    local services_warning=0
    local services_critical=0
    
    for service_name in "${!SERVICES[@]}"; do
        ((total_services++))
        
        local cert_file="${CERTS_DIR}/${service_name}/${service_name}-cert.pem"
        local days_until_expiry=$(get_certificate_expiry_days "$cert_file")
        local status=$(check_certificate_status "$service_name")
        
        # Add comma for all but first service
        if [[ "$first_service" == "false" ]]; then
            echo "," >> "$report_file"
        fi
        first_service=false
        
        # Count status types
        case "$status" in
            "EXPIRED"|"CRITICAL"|"MISSING") ((services_critical++)) ;;
            "WARNING") ((services_warning++)) ;;
        esac
        
        # Add service to report
        echo -n "    \"$service_name\": {" >> "$report_file"
        echo -n "\"status\": \"$status\", " >> "$report_file"
        echo -n "\"days_until_expiry\": $days_until_expiry, " >> "$report_file"
        echo -n "\"cert_file\": \"$cert_file\"" >> "$report_file"
        echo -n "}" >> "$report_file"
    done
    
    echo "" >> "$report_file"
    echo "  }," >> "$report_file"
    echo "  \"summary\": {" >> "$report_file"
    echo "    \"total_services\": $total_services," >> "$report_file"
    echo "    \"services_critical\": $services_critical," >> "$report_file"
    echo "    \"services_warning\": $services_warning," >> "$report_file"
    echo "    \"services_rotated\": $services_rotated" >> "$report_file"
    echo "  }" >> "$report_file"
    echo "}" >> "$report_file"
    
    log_success "Certificate rotation report generated: $report_file"
    
    # Display summary
    echo ""
    echo "Certificate Status Summary:"
    echo "=========================="
    echo "Total Services: $total_services"
    echo "Critical/Expired: $services_critical"
    echo "Warning: $services_warning"
    echo "Healthy: $((total_services - services_critical - services_warning))"
    echo ""
}

# =============================================================================
# Main Rotation Functions
# =============================================================================

check_all_certificates() {
    log_info "Checking certificate status for all services..."
    
    local services_needing_rotation=()
    
    for service_name in "${!SERVICES[@]}"; do
        local cert_file="${CERTS_DIR}/${service_name}/${service_name}-cert.pem"
        local days_until_expiry=$(get_certificate_expiry_days "$cert_file")
        local status=$(check_certificate_status "$service_name")
        
        # Send notification for problematic certificates
        case "$status" in
            "EXPIRED"|"CRITICAL"|"MISSING"|"WARNING")
                send_rotation_notification "$service_name" "$status" "$days_until_expiry"
                
                # Add to rotation list if needed
                if needs_rotation "$service_name"; then
                    services_needing_rotation+=("$service_name")
                fi
                ;;
        esac
        
        # Display status
        printf "%-25s %-10s %s days\n" "$service_name" "$status" "$days_until_expiry"
    done
    
    if [[ ${#services_needing_rotation[@]} -gt 0 ]]; then
        log_warning "Services needing rotation: ${services_needing_rotation[*]}"
        return 1
    else
        log_success "All certificates are within acceptable expiry windows"
        return 0
    fi
}

rotate_all_needed() {
    log_info "Starting automatic certificate rotation for all services needing rotation..."
    
    local rotation_failures=0
    local services_rotated=0
    
    for service_name in "${!SERVICES[@]}"; do
        if needs_rotation "$service_name"; then
            ((services_rotated++))
            
            if rotate_service_certificate "$service_name"; then
                # Restart service after successful rotation
                restart_service_after_rotation "$service_name" || true
            else
                ((rotation_failures++))
            fi
        fi
    done
    
    if [[ $rotation_failures -eq 0 ]]; then
        log_success "Certificate rotation completed successfully for $services_rotated services"
    else
        log_error "Certificate rotation completed with $rotation_failures failures"
    fi
    
    return $rotation_failures
}

force_rotate_all() {
    log_info "Starting forced certificate rotation for all services..."
    
    local rotation_failures=0
    
    for service_name in "${!SERVICES[@]}"; do
        if rotate_service_certificate "$service_name" "true"; then
            restart_service_after_rotation "$service_name" || true
        else
            ((rotation_failures++))
        fi
    done
    
    if [[ $rotation_failures -eq 0 ]]; then
        log_success "Forced certificate rotation completed successfully"
    else
        log_error "Forced certificate rotation completed with $rotation_failures failures"
    fi
    
    return $rotation_failures
}

# =============================================================================
# Cron Job Integration
# =============================================================================

setup_cron_job() {
    local cron_schedule="${1:-'0 2 * * 0'}"  # Default: 2 AM every Sunday
    local current_user=$(whoami)
    
    log_info "Setting up cron job for automatic certificate rotation..."
    
    # Create cron job entry
    local cron_entry="$cron_schedule $SCRIPT_DIR/rotate_certificates.sh auto-rotate >> $ROTATION_LOG 2>&1"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "rotate_certificates.sh"; then
        log_warning "Cron job for certificate rotation already exists"
        log_info "Current cron jobs for certificate rotation:"
        crontab -l 2>/dev/null | grep "rotate_certificates.sh" || true
    else
        # Add cron job
        (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
        log_success "Cron job added for automatic certificate rotation"
        log_info "Schedule: $cron_schedule"
        log_info "Command: $cron_entry"
    fi
}

remove_cron_job() {
    log_info "Removing cron job for automatic certificate rotation..."
    
    if crontab -l 2>/dev/null | grep -q "rotate_certificates.sh"; then
        # Remove cron job
        crontab -l 2>/dev/null | grep -v "rotate_certificates.sh" | crontab -
        log_success "Cron job removed for certificate rotation"
    else
        log_info "No cron job found for certificate rotation"
    fi
}

# =============================================================================
# Main Script Logic
# =============================================================================

display_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    check                   Check certificate status for all services
    auto-rotate            Rotate certificates that need rotation
    force-rotate-all       Force rotation of all certificates
    rotate-service <name>  Rotate specific service certificate
    report                 Generate detailed rotation report
    setup-cron [schedule]  Setup automatic rotation cron job
    remove-cron           Remove automatic rotation cron job
    
Options:
    -h, --help            Show this help message
    -v, --verbose         Enable verbose output
    -t, --threshold <days> Set rotation threshold (default: 30 days)

Examples:
    $0 check                          # Check all certificate status
    $0 auto-rotate                   # Rotate certificates needing rotation
    $0 rotate-service api            # Rotate API service certificate
    $0 setup-cron "0 2 * * 0"       # Setup weekly rotation at 2 AM Sunday
    $0 report                        # Generate rotation report

EOF
}

main() {
    # Ensure required directories exist
    mkdir -p "$LOGS_DIR"
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -t|--threshold)
                ROTATION_THRESHOLD_DAYS="$2"
                shift 2
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            -h|--help)
                display_usage
                exit 0
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Main command logic
    case "${1:-check}" in
        "check")
            log_info "Starting certificate status check..."
            check_all_certificates
            ;;
        "auto-rotate")
            log_info "Starting automatic certificate rotation..."
            rotate_all_needed
            generate_rotation_report
            ;;
        "force-rotate-all")
            log_info "Starting forced certificate rotation for all services..."
            force_rotate_all
            generate_rotation_report
            ;;
        "rotate-service")
            if [[ -z "${2:-}" ]]; then
                log_error "Service name required for rotate-service command"
                exit 1
            fi
            if [[ -z "${SERVICES[$2]:-}" ]]; then
                log_error "Unknown service: $2"
                log_info "Available services: ${!SERVICES[*]}"
                exit 1
            fi
            rotate_service_certificate "$2" "true"
            restart_service_after_rotation "$2"
            ;;
        "report")
            generate_rotation_report
            ;;
        "setup-cron")
            setup_cron_job "${2:-}"
            ;;
        "remove-cron")
            remove_cron_job
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