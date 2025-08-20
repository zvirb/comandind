#!/bin/bash
# Comprehensive Deployment Verification and Evidence Collection System
# Provides automated deployment validation, service health monitoring, and evidence collection
# Addresses the critical gap between implementation and production validation

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERIFICATION_LOG_DIR="$PROJECT_ROOT/logs/deployment_verification"
EVIDENCE_DIR="$PROJECT_ROOT/logs/deployment_evidence"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
VERIFICATION_ID="verify_${TIMESTAMP}"

# Production endpoints
PRODUCTION_DOMAIN="aiwfe.com"
PRODUCTION_HTTP="http://${PRODUCTION_DOMAIN}"
PRODUCTION_HTTPS="https://${PRODUCTION_DOMAIN}"

# Service health thresholds
HEALTH_CHECK_TIMEOUT=10
MAX_RETRY_ATTEMPTS=3
SERVICE_START_TIMEOUT=180

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize verification directories
initialize_verification() {
    echo -e "${BLUE}[INIT]${NC} Initializing deployment verification (ID: $VERIFICATION_ID)"
    
    # Create verification directories
    mkdir -p "$VERIFICATION_LOG_DIR"
    mkdir -p "$EVIDENCE_DIR/$VERIFICATION_ID"
    mkdir -p "$EVIDENCE_DIR/$VERIFICATION_ID/services"
    mkdir -p "$EVIDENCE_DIR/$VERIFICATION_ID/endpoints"
    mkdir -p "$EVIDENCE_DIR/$VERIFICATION_ID/ssl"
    mkdir -p "$EVIDENCE_DIR/$VERIFICATION_ID/database"
    
    # Initialize verification metadata
    cat > "$EVIDENCE_DIR/$VERIFICATION_ID/metadata.json" << EOF
{
    "verification_id": "$VERIFICATION_ID",
    "timestamp": "$(date -Iseconds)",
    "domain": "$PRODUCTION_DOMAIN",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
    "docker_version": "$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'unknown')"
}
EOF
}

# Log function with timestamp and evidence capture
log_evidence() {
    local level=$1
    local message=$2
    local evidence_file=$3
    
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local log_entry="[$timestamp] [$level] $message"
    
    # Console output with color
    case $level in
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
        ERROR)   echo -e "${RED}[ERROR]${NC} $message" ;;
        WARNING) echo -e "${YELLOW}[WARNING]${NC} $message" ;;
        INFO)    echo -e "${BLUE}[INFO]${NC} $message" ;;
    esac
    
    # Log to file
    echo "$log_entry" >> "$VERIFICATION_LOG_DIR/verification_${TIMESTAMP}.log"
    
    # Save evidence if provided
    if [ -n "$evidence_file" ] && [ -f "$evidence_file" ]; then
        cp "$evidence_file" "$EVIDENCE_DIR/$VERIFICATION_ID/"
    fi
}

# Check Docker service status with evidence collection
check_docker_service() {
    local service_name=$1
    local evidence_file="$EVIDENCE_DIR/$VERIFICATION_ID/services/${service_name}_status.json"
    
    log_evidence "INFO" "Checking Docker service: $service_name"
    
    # Get container status
    local container_id=$(docker compose ps -q "$service_name" 2>/dev/null || echo "")
    
    if [ -z "$container_id" ]; then
        echo "{\"service\": \"$service_name\", \"status\": \"not_found\", \"timestamp\": \"$(date -Iseconds)\"}" > "$evidence_file"
        log_evidence "ERROR" "Service $service_name not found"
        return 1
    fi
    
    # Collect detailed container information
    docker inspect "$container_id" > "$evidence_file" 2>/dev/null || true
    
    # Check container health
    local health_status=$(docker inspect "$container_id" --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    local running_status=$(docker inspect "$container_id" --format='{{.State.Running}}' 2>/dev/null || echo "false")
    
    # Save compact status
    cat > "$EVIDENCE_DIR/$VERIFICATION_ID/services/${service_name}_health.json" << EOF
{
    "service": "$service_name",
    "container_id": "$container_id",
    "running": $running_status,
    "health_status": "$health_status",
    "timestamp": "$(date -Iseconds)"
}
EOF
    
    if [ "$running_status" = "true" ]; then
        if [ "$health_status" = "healthy" ] || [ "$health_status" = "unknown" ]; then
            log_evidence "SUCCESS" "Service $service_name is running (health: $health_status)"
            return 0
        else
            log_evidence "WARNING" "Service $service_name is running but unhealthy: $health_status"
            return 1
        fi
    else
        log_evidence "ERROR" "Service $service_name is not running"
        return 1
    fi
}

# Restart Docker service with monitoring
restart_docker_service() {
    local service_name=$1
    local max_wait=$SERVICE_START_TIMEOUT
    
    log_evidence "INFO" "Restarting service: $service_name"
    
    # Stop the service
    docker compose stop "$service_name" 2>&1 | tee "$EVIDENCE_DIR/$VERIFICATION_ID/services/${service_name}_stop.log"
    sleep 2
    
    # Start the service
    docker compose up -d "$service_name" 2>&1 | tee "$EVIDENCE_DIR/$VERIFICATION_ID/services/${service_name}_start.log"
    
    # Wait for service to become healthy
    local start_time=$(date +%s)
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $max_wait ]; then
            log_evidence "ERROR" "Service $service_name failed to start within ${max_wait}s"
            return 1
        fi
        
        if check_docker_service "$service_name"; then
            log_evidence "SUCCESS" "Service $service_name restarted successfully"
            return 0
        fi
        
        sleep 5
    done
}

# Verify HTTP/HTTPS endpoints with curl evidence
verify_endpoint() {
    local url=$1
    local endpoint_name=$2
    local evidence_file="$EVIDENCE_DIR/$VERIFICATION_ID/endpoints/${endpoint_name}.txt"
    
    log_evidence "INFO" "Verifying endpoint: $url"
    
    # Perform curl with detailed output
    local curl_output=$(mktemp)
    local http_code=$(curl -s -o "$curl_output" -w "%{http_code}" \
        --max-time $HEALTH_CHECK_TIMEOUT \
        --connect-timeout $HEALTH_CHECK_TIMEOUT \
        -H "User-Agent: Deployment-Verification/$VERIFICATION_ID" \
        "$url" 2>&1)
    
    # Save curl evidence
    {
        echo "=== Endpoint Verification: $endpoint_name ==="
        echo "URL: $url"
        echo "Timestamp: $(date -Iseconds)"
        echo "HTTP Status Code: $http_code"
        echo ""
        echo "=== Response Headers ==="
        curl -I -s --max-time $HEALTH_CHECK_TIMEOUT "$url" 2>&1 || echo "Failed to get headers"
        echo ""
        echo "=== Response Body (first 1000 chars) ==="
        head -c 1000 "$curl_output"
    } > "$evidence_file"
    
    rm -f "$curl_output"
    
    # Validate response
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
        log_evidence "SUCCESS" "Endpoint $endpoint_name responding with HTTP $http_code" "$evidence_file"
        return 0
    else
        log_evidence "ERROR" "Endpoint $endpoint_name failed with HTTP $http_code" "$evidence_file"
        return 1
    fi
}

# Verify SSL certificate
verify_ssl_certificate() {
    local domain=$1
    local evidence_file="$EVIDENCE_DIR/$VERIFICATION_ID/ssl/certificate_info.txt"
    
    log_evidence "INFO" "Verifying SSL certificate for $domain"
    
    # Get certificate information
    {
        echo "=== SSL Certificate Information ==="
        echo "Domain: $domain"
        echo "Timestamp: $(date -Iseconds)"
        echo ""
        echo "=== Certificate Details ==="
        echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | \
            openssl x509 -noout -text 2>/dev/null || echo "Failed to retrieve certificate"
        echo ""
        echo "=== Certificate Chain ==="
        echo | openssl s_client -servername "$domain" -connect "$domain:443" -showcerts 2>/dev/null || \
            echo "Failed to retrieve certificate chain"
    } > "$evidence_file"
    
    # Check certificate expiration
    local cert_expiry=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | \
        openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    
    if [ -n "$cert_expiry" ]; then
        local cert_expiry_epoch=$(date -d "$cert_expiry" +%s 2>/dev/null || echo 0)
        local current_epoch=$(date +%s)
        local days_until_expiry=$(( (cert_expiry_epoch - current_epoch) / 86400 ))
        
        echo "Certificate expires: $cert_expiry (${days_until_expiry} days)" >> "$evidence_file"
        
        if [ $days_until_expiry -gt 7 ]; then
            log_evidence "SUCCESS" "SSL certificate valid for $days_until_expiry days" "$evidence_file"
            return 0
        else
            log_evidence "WARNING" "SSL certificate expires in $days_until_expiry days" "$evidence_file"
            return 1
        fi
    else
        log_evidence "ERROR" "Failed to verify SSL certificate" "$evidence_file"
        return 1
    fi
}

# Verify database connectivity
verify_database() {
    local evidence_file="$EVIDENCE_DIR/$VERIFICATION_ID/database/connectivity.txt"
    
    log_evidence "INFO" "Verifying database connectivity"
    
    # Test database connection
    {
        echo "=== Database Connectivity Test ==="
        echo "Timestamp: $(date -Iseconds)"
        echo ""
        
        # Check PostgreSQL
        if docker compose exec -T postgres pg_isready -U app_user -d ai_workflow_db 2>&1; then
            echo "PostgreSQL: CONNECTED"
            
            # Get database size and table count
            docker compose exec -T postgres psql -U app_user -d ai_workflow_db -c \
                "SELECT pg_database_size('ai_workflow_db') as size_bytes;" 2>&1 || true
            
            docker compose exec -T postgres psql -U app_user -d ai_workflow_db -c \
                "SELECT count(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';" 2>&1 || true
        else
            echo "PostgreSQL: FAILED"
        fi
        
        echo ""
        
        # Check Redis
        if docker compose exec -T redis redis-cli ping 2>&1; then
            echo "Redis: CONNECTED"
            
            # Get Redis info
            docker compose exec -T redis redis-cli INFO server 2>&1 | head -20 || true
        else
            echo "Redis: FAILED"
        fi
        
        echo ""
        
        # Check Qdrant
        if curl -s -k "https://localhost:6333/healthz" --max-time 5 2>&1; then
            echo "Qdrant: CONNECTED"
        else
            echo "Qdrant: FAILED"
        fi
    } > "$evidence_file"
    
    log_evidence "INFO" "Database connectivity test completed" "$evidence_file"
}

# Check all critical services
verify_all_services() {
    local critical_services=(
        "postgres"
        "redis"
        "qdrant"
        "api"
        "worker"
        "webui"
        "caddy_reverse_proxy"
        "prometheus"
        "grafana"
        "ollama"
    )
    
    local failed_services=()
    
    log_evidence "INFO" "Starting comprehensive service verification"
    
    for service in "${critical_services[@]}"; do
        if ! check_docker_service "$service"; then
            failed_services+=("$service")
        fi
    done
    
    # Report results
    if [ ${#failed_services[@]} -eq 0 ]; then
        log_evidence "SUCCESS" "All critical services are running"
        return 0
    else
        log_evidence "ERROR" "Failed services: ${failed_services[*]}"
        
        # Attempt to restart failed services
        for service in "${failed_services[@]}"; do
            log_evidence "INFO" "Attempting to restart failed service: $service"
            if restart_docker_service "$service"; then
                log_evidence "SUCCESS" "Service $service recovered after restart"
            else
                log_evidence "ERROR" "Service $service failed to recover"
            fi
        done
        
        return 1
    fi
}

# Verify production endpoints
verify_production_endpoints() {
    local endpoints_verified=0
    local endpoints_failed=0
    
    log_evidence "INFO" "Starting production endpoint verification"
    
    # Test HTTP redirect
    if verify_endpoint "$PRODUCTION_HTTP" "http_redirect"; then
        ((endpoints_verified++))
    else
        ((endpoints_failed++))
    fi
    
    # Test HTTPS homepage
    if verify_endpoint "$PRODUCTION_HTTPS" "https_homepage"; then
        ((endpoints_verified++))
    else
        ((endpoints_failed++))
    fi
    
    # Test API health
    if verify_endpoint "${PRODUCTION_HTTPS}/api/health" "api_health"; then
        ((endpoints_verified++))
    else
        ((endpoints_failed++))
    fi
    
    # Test WebSocket endpoint
    local ws_test=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time $HEALTH_CHECK_TIMEOUT \
        -H "Upgrade: websocket" \
        -H "Connection: Upgrade" \
        "${PRODUCTION_HTTPS}/ws" 2>&1)
    
    if [ "$ws_test" = "426" ] || [ "$ws_test" = "101" ]; then
        log_evidence "SUCCESS" "WebSocket endpoint responding"
        ((endpoints_verified++))
    else
        log_evidence "WARNING" "WebSocket endpoint may not be configured"
    fi
    
    # Test monitoring endpoints
    if verify_endpoint "http://localhost:9090/-/healthy" "prometheus_health"; then
        ((endpoints_verified++))
    else
        ((endpoints_failed++))
    fi
    
    if verify_endpoint "http://localhost:3000/api/health" "grafana_health"; then
        ((endpoints_verified++))
    else
        ((endpoints_failed++))
    fi
    
    log_evidence "INFO" "Endpoint verification complete: $endpoints_verified passed, $endpoints_failed failed"
    
    return $([ $endpoints_failed -eq 0 ])
}

# Detect deployment gaps
detect_deployment_gaps() {
    local gaps_found=0
    local gaps_report="$EVIDENCE_DIR/$VERIFICATION_ID/deployment_gaps.json"
    
    log_evidence "INFO" "Detecting deployment gaps"
    
    local gaps=()
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        gaps+=("uncommitted_changes")
        log_evidence "WARNING" "Uncommitted changes detected in repository"
        ((gaps_found++))
    fi
    
    # Check for outdated images
    local outdated_images=$(docker compose images --format json | \
        jq -r '.[] | select(.Repository != "<none>") | select(.Tag == "latest") | .Repository' 2>/dev/null)
    
    if [ -n "$outdated_images" ]; then
        gaps+=("outdated_images")
        log_evidence "WARNING" "Services using 'latest' tag detected: potential version mismatch"
        ((gaps_found++))
    fi
    
    # Check for missing environment variables
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        gaps+=("missing_env_file")
        log_evidence "ERROR" "Missing .env file"
        ((gaps_found++))
    fi
    
    # Check for missing secrets
    local required_secrets=(
        "postgres_password.txt"
        "jwt_secret_key.txt"
        "api_key.txt"
        "admin_email.txt"
        "admin_password.txt"
    )
    
    for secret in "${required_secrets[@]}"; do
        if [ ! -f "$PROJECT_ROOT/secrets/$secret" ]; then
            gaps+=("missing_secret_$secret")
            log_evidence "ERROR" "Missing required secret: $secret"
            ((gaps_found++))
        fi
    done
    
    # Generate gaps report
    cat > "$gaps_report" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "gaps_found": $gaps_found,
    "gaps": $(printf '%s\n' "${gaps[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "verification_id": "$VERIFICATION_ID"
}
EOF
    
    if [ $gaps_found -eq 0 ]; then
        log_evidence "SUCCESS" "No deployment gaps detected"
        return 0
    else
        log_evidence "WARNING" "Found $gaps_found deployment gaps" "$gaps_report"
        return 1
    fi
}

# Generate comprehensive verification report
generate_verification_report() {
    local report_file="$EVIDENCE_DIR/$VERIFICATION_ID/verification_report.html"
    
    log_evidence "INFO" "Generating verification report"
    
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Deployment Verification Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .section { background: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .success { color: #27ae60; font-weight: bold; }
        .error { color: #e74c3c; font-weight: bold; }
        .warning { color: #f39c12; font-weight: bold; }
        .evidence { background: #ecf0f1; padding: 10px; border-radius: 3px; margin: 10px 0; font-family: monospace; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #34495e; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Deployment Verification Report</h1>
        <p>Verification ID: VERIFICATION_ID_PLACEHOLDER</p>
        <p>Generated: TIMESTAMP_PLACEHOLDER</p>
    </div>
EOF
    
    # Add services status section
    echo '<div class="section"><h2>Service Status</h2><table>' >> "$report_file"
    echo '<tr><th>Service</th><th>Status</th><th>Health</th></tr>' >> "$report_file"
    
    for service_file in "$EVIDENCE_DIR/$VERIFICATION_ID/services"/*_health.json; do
        if [ -f "$service_file" ]; then
            local service=$(jq -r .service "$service_file" 2>/dev/null)
            local running=$(jq -r .running "$service_file" 2>/dev/null)
            local health=$(jq -r .health_status "$service_file" 2>/dev/null)
            
            local status_class="error"
            [ "$running" = "true" ] && status_class="success"
            
            echo "<tr><td>$service</td><td class='$status_class'>$running</td><td>$health</td></tr>" >> "$report_file"
        fi
    done
    
    echo '</table></div>' >> "$report_file"
    
    # Add endpoints section
    echo '<div class="section"><h2>Endpoint Verification</h2>' >> "$report_file"
    
    for endpoint_file in "$EVIDENCE_DIR/$VERIFICATION_ID/endpoints"/*.txt; do
        if [ -f "$endpoint_file" ]; then
            local endpoint_name=$(basename "$endpoint_file" .txt)
            echo "<h3>$endpoint_name</h3>" >> "$report_file"
            echo '<div class="evidence">' >> "$report_file"
            head -20 "$endpoint_file" | sed 's/</\&lt;/g; s/>/\&gt;/g' >> "$report_file"
            echo '</div>' >> "$report_file"
        fi
    done
    
    echo '</div>' >> "$report_file"
    
    # Close HTML
    echo '</body></html>' >> "$report_file"
    
    # Replace placeholders
    sed -i "s/VERIFICATION_ID_PLACEHOLDER/$VERIFICATION_ID/g" "$report_file"
    sed -i "s/TIMESTAMP_PLACEHOLDER/$(date)/g" "$report_file"
    
    log_evidence "SUCCESS" "Verification report generated: $report_file"
}

# Main verification flow
main() {
    local exit_code=0
    
    # Initialize
    initialize_verification
    
    # Run verifications
    echo -e "\n${BLUE}=== Phase 1: Service Verification ===${NC}"
    if ! verify_all_services; then
        exit_code=1
    fi
    
    echo -e "\n${BLUE}=== Phase 2: Database Verification ===${NC}"
    verify_database
    
    echo -e "\n${BLUE}=== Phase 3: Production Endpoint Verification ===${NC}"
    if ! verify_production_endpoints; then
        exit_code=1
    fi
    
    echo -e "\n${BLUE}=== Phase 4: SSL Certificate Verification ===${NC}"
    if ! verify_ssl_certificate "$PRODUCTION_DOMAIN"; then
        exit_code=1
    fi
    
    echo -e "\n${BLUE}=== Phase 5: Deployment Gap Detection ===${NC}"
    if ! detect_deployment_gaps; then
        exit_code=1
    fi
    
    # Generate report
    echo -e "\n${BLUE}=== Generating Verification Report ===${NC}"
    generate_verification_report
    
    # Final summary
    echo -e "\n${BLUE}=== Verification Summary ===${NC}"
    if [ $exit_code -eq 0 ]; then
        log_evidence "SUCCESS" "Deployment verification completed successfully"
        echo -e "${GREEN}All verification checks passed!${NC}"
    else
        log_evidence "ERROR" "Deployment verification completed with failures"
        echo -e "${RED}Some verification checks failed. Review the evidence at:${NC}"
        echo -e "${YELLOW}$EVIDENCE_DIR/$VERIFICATION_ID/${NC}"
    fi
    
    echo -e "\n${BLUE}Evidence collected at: $EVIDENCE_DIR/$VERIFICATION_ID/${NC}"
    echo -e "${BLUE}Verification report: $EVIDENCE_DIR/$VERIFICATION_ID/verification_report.html${NC}"
    
    exit $exit_code
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            PRODUCTION_DOMAIN="$2"
            PRODUCTION_HTTP="http://${PRODUCTION_DOMAIN}"
            PRODUCTION_HTTPS="https://${PRODUCTION_DOMAIN}"
            shift 2
            ;;
        --quick)
            # Quick mode - skip some time-consuming checks
            QUICK_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --domain DOMAIN    Specify production domain (default: aiwfe.com)"
            echo "  --quick           Run quick verification (skip some checks)"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main verification
main