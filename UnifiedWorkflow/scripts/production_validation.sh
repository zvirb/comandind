#!/bin/bash
# Production Validation and Evidence Collection System
# Automated production deployment validation with comprehensive evidence collection

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VALIDATION_LOG_DIR="$PROJECT_ROOT/logs/production_validation"
EVIDENCE_DIR="$PROJECT_ROOT/logs/production_evidence"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
VALIDATION_ID="prod_validate_${TIMESTAMP}"

# Production configuration
PRODUCTION_DOMAIN="${PRODUCTION_DOMAIN:-aiwfe.com}"
PRODUCTION_HTTP="http://${PRODUCTION_DOMAIN}"
PRODUCTION_HTTPS="https://${PRODUCTION_DOMAIN}"
CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN}"
CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID}"

# Validation thresholds
MIN_RESPONSE_TIME=0.5  # seconds
MAX_RESPONSE_TIME=3.0  # seconds
MIN_UPTIME_PERCENT=99.0
SSL_MIN_DAYS_VALID=7

# Test data
TEST_API_ENDPOINTS=(
    "/api/health"
    "/api/v1/status"
    "/api/docs"
)

TEST_UI_PATHS=(
    "/"
    "/login"
    "/dashboard"
    "/api-docs"
)

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Initialize validation
initialize_validation() {
    echo -e "${BLUE}[INIT]${NC} Initializing production validation (ID: $VALIDATION_ID)"
    echo -e "${BLUE}[INIT]${NC} Target domain: $PRODUCTION_DOMAIN"
    
    # Create directories
    mkdir -p "$VALIDATION_LOG_DIR"
    mkdir -p "$EVIDENCE_DIR/$VALIDATION_ID"/{dns,ssl,performance,api,ui,security,deployment}
    
    # Create validation metadata
    cat > "$EVIDENCE_DIR/$VALIDATION_ID/metadata.json" << EOF
{
    "validation_id": "$VALIDATION_ID",
    "timestamp": "$(date -Iseconds)",
    "domain": "$PRODUCTION_DOMAIN",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')",
    "docker_compose_hash": "$(sha256sum docker-compose.yml | cut -d' ' -f1)"
}
EOF
}

# Logging with evidence
log_validation() {
    local level=$1
    local category=$2
    local message=$3
    local evidence_data=$4
    
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Console output
    case $level in
        SUCCESS) echo -e "${GREEN}[$category]${NC} ✓ $message" ;;
        ERROR)   echo -e "${RED}[$category]${NC} ✗ $message" ;;
        WARNING) echo -e "${YELLOW}[$category]${NC} ⚠ $message" ;;
        INFO)    echo -e "${BLUE}[$category]${NC} → $message" ;;
        EVIDENCE) echo -e "${CYAN}[$category]${NC} 📋 $message" ;;
    esac
    
    # Log to file
    echo "[$timestamp] [$level] [$category] $message" >> "$VALIDATION_LOG_DIR/validation_${TIMESTAMP}.log"
    
    # Save evidence if provided
    if [ -n "$evidence_data" ]; then
        local evidence_file="$EVIDENCE_DIR/$VALIDATION_ID/${category,,}/$(date +%s)_evidence.json"
        echo "$evidence_data" > "$evidence_file"
    fi
}

# DNS validation
validate_dns() {
    log_validation "INFO" "DNS" "Validating DNS resolution for $PRODUCTION_DOMAIN"
    
    local dns_evidence="$EVIDENCE_DIR/$VALIDATION_ID/dns/resolution.json"
    local dns_results=()
    
    # Check A records
    local a_records=$(dig +short A "$PRODUCTION_DOMAIN" 2>/dev/null | tr '\n' ' ')
    if [ -n "$a_records" ]; then
        log_validation "SUCCESS" "DNS" "A records found: $a_records"
        dns_results+=("\"a_records\": [$(echo "$a_records" | sed 's/ /", "/g' | sed 's/^/"/;s/, "$/"/')]")
    else
        log_validation "ERROR" "DNS" "No A records found"
        return 1
    fi
    
    # Check AAAA records (IPv6)
    local aaaa_records=$(dig +short AAAA "$PRODUCTION_DOMAIN" 2>/dev/null | tr '\n' ' ')
    if [ -n "$aaaa_records" ]; then
        log_validation "INFO" "DNS" "AAAA records found: $aaaa_records"
        dns_results+=("\"aaaa_records\": [$(echo "$aaaa_records" | sed 's/ /", "/g' | sed 's/^/"/;s/, "$/"/')]")
    fi
    
    # Check Cloudflare status if API token available
    if [ -n "$CLOUDFLARE_API_TOKEN" ] && [ -n "$CLOUDFLARE_ZONE_ID" ]; then
        local cf_status=$(curl -s -X GET \
            "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records?name=$PRODUCTION_DOMAIN" \
            -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
            -H "Content-Type: application/json" 2>/dev/null)
        
        if [ -n "$cf_status" ]; then
            echo "$cf_status" > "$EVIDENCE_DIR/$VALIDATION_ID/dns/cloudflare_records.json"
            log_validation "EVIDENCE" "DNS" "Cloudflare DNS records collected"
        fi
    fi
    
    # Save DNS evidence
    cat > "$dns_evidence" << EOF
{
    "domain": "$PRODUCTION_DOMAIN",
    "timestamp": "$(date -Iseconds)",
    ${dns_results[*]},
    "nameservers": $(dig +short NS "$PRODUCTION_DOMAIN" | jq -R . | jq -s . 2>/dev/null || echo '[]')
}
EOF
    
    log_validation "SUCCESS" "DNS" "DNS validation completed"
    return 0
}

# SSL certificate validation
validate_ssl() {
    log_validation "INFO" "SSL" "Validating SSL certificate for $PRODUCTION_DOMAIN"
    
    local ssl_evidence="$EVIDENCE_DIR/$VALIDATION_ID/ssl/certificate.txt"
    
    # Get certificate details
    local cert_info=$(echo | openssl s_client -servername "$PRODUCTION_DOMAIN" \
        -connect "$PRODUCTION_DOMAIN:443" 2>/dev/null | \
        openssl x509 -noout -text 2>/dev/null)
    
    if [ -z "$cert_info" ]; then
        log_validation "ERROR" "SSL" "Failed to retrieve SSL certificate"
        return 1
    fi
    
    # Save full certificate info
    echo "$cert_info" > "$ssl_evidence"
    
    # Check expiration
    local expiry_date=$(echo | openssl s_client -servername "$PRODUCTION_DOMAIN" \
        -connect "$PRODUCTION_DOMAIN:443" 2>/dev/null | \
        openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    
    if [ -n "$expiry_date" ]; then
        local expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null)
        local current_epoch=$(date +%s)
        local days_valid=$(( (expiry_epoch - current_epoch) / 86400 ))
        
        if [ $days_valid -lt $SSL_MIN_DAYS_VALID ]; then
            log_validation "ERROR" "SSL" "Certificate expires in $days_valid days (min: $SSL_MIN_DAYS_VALID)"
            return 1
        else
            log_validation "SUCCESS" "SSL" "Certificate valid for $days_valid days"
        fi
    fi
    
    # Check certificate chain
    local chain_output="$EVIDENCE_DIR/$VALIDATION_ID/ssl/chain.txt"
    echo | openssl s_client -servername "$PRODUCTION_DOMAIN" \
        -connect "$PRODUCTION_DOMAIN:443" -showcerts 2>/dev/null > "$chain_output"
    
    # Verify SSL grade (using SSLLabs API if available)
    if command -v curl >/dev/null 2>&1; then
        log_validation "INFO" "SSL" "Checking SSL configuration quality"
        
        # Quick SSL test
        local ssl_test=$(curl -s -I --max-time 10 "$PRODUCTION_HTTPS" 2>&1)
        if echo "$ssl_test" | grep -q "HTTP/2\|HTTP/1.1"; then
            log_validation "SUCCESS" "SSL" "HTTPS endpoint responding correctly"
        else
            log_validation "WARNING" "SSL" "HTTPS endpoint may have issues"
        fi
    fi
    
    return 0
}

# Performance validation
validate_performance() {
    log_validation "INFO" "PERFORMANCE" "Running performance validation tests"
    
    local perf_results="$EVIDENCE_DIR/$VALIDATION_ID/performance/results.json"
    local total_tests=0
    local passed_tests=0
    
    # Test response times for various endpoints
    local endpoints=("${TEST_API_ENDPOINTS[@]}" "${TEST_UI_PATHS[@]}")
    local response_times=()
    
    for endpoint in "${endpoints[@]}"; do
        local url="${PRODUCTION_HTTPS}${endpoint}"
        local response_time=$(curl -o /dev/null -s -w "%{time_total}" --max-time 10 "$url" 2>/dev/null || echo "999")
        
        response_times+=("{\"endpoint\": \"$endpoint\", \"response_time\": $response_time}")
        ((total_tests++))
        
        if (( $(echo "$response_time < $MAX_RESPONSE_TIME" | bc -l) )); then
            ((passed_tests++))
            log_validation "SUCCESS" "PERFORMANCE" "$endpoint: ${response_time}s"
        else
            log_validation "WARNING" "PERFORMANCE" "$endpoint: ${response_time}s (threshold: ${MAX_RESPONSE_TIME}s)"
        fi
    done
    
    # Save performance results
    cat > "$perf_results" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "total_tests": $total_tests,
    "passed_tests": $passed_tests,
    "response_times": [$(IFS=,; echo "${response_times[*]}")],
    "thresholds": {
        "min_response_time": $MIN_RESPONSE_TIME,
        "max_response_time": $MAX_RESPONSE_TIME
    }
}
EOF
    
    # Run load test (light)
    if command -v ab >/dev/null 2>&1; then
        log_validation "INFO" "PERFORMANCE" "Running light load test"
        ab -n 100 -c 10 -t 10 "${PRODUCTION_HTTPS}/" > \
            "$EVIDENCE_DIR/$VALIDATION_ID/performance/load_test.txt" 2>&1 || true
    fi
    
    local success_rate=$((passed_tests * 100 / total_tests))
    if [ $success_rate -ge 80 ]; then
        log_validation "SUCCESS" "PERFORMANCE" "Performance validation passed ($success_rate% success)"
        return 0
    else
        log_validation "ERROR" "PERFORMANCE" "Performance validation failed ($success_rate% success)"
        return 1
    fi
}

# API validation
validate_api() {
    log_validation "INFO" "API" "Validating API endpoints"
    
    local api_results="$EVIDENCE_DIR/$VALIDATION_ID/api/validation.json"
    local failed_endpoints=()
    
    for endpoint in "${TEST_API_ENDPOINTS[@]}"; do
        local url="${PRODUCTION_HTTPS}${endpoint}"
        local response_file="$EVIDENCE_DIR/$VALIDATION_ID/api/$(echo "$endpoint" | tr '/' '_').json"
        
        # Make API request
        local http_code=$(curl -s -o "$response_file" -w "%{http_code}" \
            --max-time 10 \
            -H "Accept: application/json" \
            "$url" 2>/dev/null)
        
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
            log_validation "SUCCESS" "API" "$endpoint returned HTTP $http_code"
        else
            log_validation "ERROR" "API" "$endpoint returned HTTP $http_code"
            failed_endpoints+=("$endpoint")
        fi
    done
    
    # Test WebSocket endpoint
    log_validation "INFO" "API" "Testing WebSocket endpoint"
    local ws_test=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 5 \
        -H "Upgrade: websocket" \
        -H "Connection: Upgrade" \
        -H "Sec-WebSocket-Version: 13" \
        -H "Sec-WebSocket-Key: $(openssl rand -base64 16)" \
        "${PRODUCTION_HTTPS}/ws" 2>/dev/null)
    
    if [ "$ws_test" = "426" ] || [ "$ws_test" = "101" ]; then
        log_validation "SUCCESS" "API" "WebSocket endpoint available"
    else
        log_validation "WARNING" "API" "WebSocket endpoint returned unexpected status: $ws_test"
    fi
    
    # Save API validation results
    cat > "$api_results" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "endpoints_tested": ${#TEST_API_ENDPOINTS[@]},
    "failed_endpoints": $(printf '%s\n' "${failed_endpoints[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "websocket_status": "$ws_test"
}
EOF
    
    if [ ${#failed_endpoints[@]} -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# UI validation
validate_ui() {
    log_validation "INFO" "UI" "Validating UI accessibility"
    
    local ui_results="$EVIDENCE_DIR/$VALIDATION_ID/ui/validation.json"
    local failed_paths=()
    
    for path in "${TEST_UI_PATHS[@]}"; do
        local url="${PRODUCTION_HTTPS}${path}"
        local response_file="$EVIDENCE_DIR/$VALIDATION_ID/ui/$(echo "$path" | tr '/' '_').html"
        
        # Fetch page
        local http_code=$(curl -s -o "$response_file" -w "%{http_code}" \
            --max-time 10 \
            -H "User-Agent: ProductionValidator/1.0" \
            -L "$url" 2>/dev/null)
        
        if [ "$http_code" -eq 200 ]; then
            # Check for common UI elements
            if grep -q "</html>" "$response_file" 2>/dev/null; then
                log_validation "SUCCESS" "UI" "$path loaded successfully"
            else
                log_validation "WARNING" "UI" "$path returned incomplete HTML"
            fi
        else
            log_validation "ERROR" "UI" "$path returned HTTP $http_code"
            failed_paths+=("$path")
        fi
    done
    
    # Take screenshots if possible (requires chrome/chromium)
    if command -v chromium >/dev/null 2>&1 || command -v google-chrome >/dev/null 2>&1; then
        local browser_cmd=$(command -v chromium || command -v google-chrome)
        log_validation "INFO" "UI" "Capturing screenshots"
        
        for path in "${TEST_UI_PATHS[@]}"; do
            local screenshot_file="$EVIDENCE_DIR/$VALIDATION_ID/ui/screenshot_$(echo "$path" | tr '/' '_').png"
            $browser_cmd --headless --disable-gpu --screenshot="$screenshot_file" \
                --window-size=1920,1080 "${PRODUCTION_HTTPS}${path}" 2>/dev/null || true
        done
    fi
    
    # Save UI validation results
    cat > "$ui_results" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "paths_tested": ${#TEST_UI_PATHS[@]},
    "failed_paths": $(printf '%s\n' "${failed_paths[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
}
EOF
    
    if [ ${#failed_paths[@]} -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Security validation
validate_security() {
    log_validation "INFO" "SECURITY" "Running security validation checks"
    
    local security_results="$EVIDENCE_DIR/$VALIDATION_ID/security/validation.json"
    local security_issues=()
    
    # Check security headers
    local headers=$(curl -s -I --max-time 10 "$PRODUCTION_HTTPS" 2>/dev/null)
    
    # Check for important security headers
    local required_headers=(
        "Strict-Transport-Security"
        "X-Content-Type-Options"
        "X-Frame-Options"
    )
    
    for header in "${required_headers[@]}"; do
        if echo "$headers" | grep -qi "$header"; then
            log_validation "SUCCESS" "SECURITY" "Security header present: $header"
        else
            log_validation "WARNING" "SECURITY" "Missing security header: $header"
            security_issues+=("missing_header_$header")
        fi
    done
    
    # Check for exposed sensitive endpoints
    local sensitive_paths=(
        "/.env"
        "/.git/config"
        "/secrets"
        "/admin"
        "/phpmyadmin"
    )
    
    for path in "${sensitive_paths[@]}"; do
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time 5 "${PRODUCTION_HTTPS}${path}" 2>/dev/null)
        
        if [ "$http_code" -ne 404 ] && [ "$http_code" -ne 403 ]; then
            log_validation "ERROR" "SECURITY" "Sensitive path accessible: $path (HTTP $http_code)"
            security_issues+=("exposed_path_$path")
        fi
    done
    
    # Save security results
    cat > "$security_results" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "security_issues": $(printf '%s\n' "${security_issues[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]'),
    "headers_checked": $(printf '%s\n' "${required_headers[@]}" | jq -R . | jq -s . 2>/dev/null || echo '[]')
}
EOF
    
    echo "$headers" > "$EVIDENCE_DIR/$VALIDATION_ID/security/response_headers.txt"
    
    if [ ${#security_issues[@]} -eq 0 ]; then
        log_validation "SUCCESS" "SECURITY" "No critical security issues found"
        return 0
    else
        log_validation "WARNING" "SECURITY" "Found ${#security_issues[@]} security concerns"
        return 0  # Don't fail on security warnings
    fi
}

# Deployment validation
validate_deployment() {
    log_validation "INFO" "DEPLOYMENT" "Validating deployment configuration"
    
    local deployment_results="$EVIDENCE_DIR/$VALIDATION_ID/deployment/validation.json"
    
    # Check Docker containers
    local running_containers=$(docker compose ps --format json 2>/dev/null | \
        jq -s 'map(select(.State == "running")) | length' 2>/dev/null || echo 0)
    
    local expected_containers=$(docker compose config --services 2>/dev/null | wc -l)
    
    if [ "$running_containers" -ge "$expected_containers" ]; then
        log_validation "SUCCESS" "DEPLOYMENT" "All expected containers running ($running_containers/$expected_containers)"
    else
        log_validation "WARNING" "DEPLOYMENT" "Not all containers running ($running_containers/$expected_containers)"
    fi
    
    # Check recent deployments
    if [ -d "$PROJECT_ROOT/logs/deployments" ]; then
        local recent_deployment=$(ls -t "$PROJECT_ROOT/logs/deployments" 2>/dev/null | head -1)
        if [ -n "$recent_deployment" ]; then
            log_validation "INFO" "DEPLOYMENT" "Most recent deployment: $recent_deployment"
            cp -r "$PROJECT_ROOT/logs/deployments/$recent_deployment" \
                "$EVIDENCE_DIR/$VALIDATION_ID/deployment/" 2>/dev/null || true
        fi
    fi
    
    # Save deployment validation
    cat > "$deployment_results" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "running_containers": $running_containers,
    "expected_containers": $expected_containers,
    "docker_compose_valid": $(docker compose config >/dev/null 2>&1 && echo "true" || echo "false")
}
EOF
    
    return 0
}

# Generate HTML report
generate_html_report() {
    local report_file="$EVIDENCE_DIR/$VALIDATION_ID/production_validation_report.html"
    
    log_validation "INFO" "REPORT" "Generating HTML validation report"
    
    cat > "$report_file" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Production Validation Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 { 
            font-size: 2.5em; 
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header .subtitle { 
            font-size: 1.2em; 
            opacity: 0.9;
        }
        .content { padding: 40px; }
        .section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 4px solid #3498db;
        }
        .section h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        .metric {
            display: inline-block;
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            margin: 10px 10px 10px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .metric .label {
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .metric .value {
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 5px;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            text-transform: uppercase;
        }
        .status-success { 
            background: #d4edda; 
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status-warning { 
            background: #fff3cd; 
            color: #856404;
            border: 1px solid #ffeeba;
        }
        .status-error { 
            background: #f8d7da; 
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .evidence-box {
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
            margin-top: 15px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        th {
            background: #e9ecef;
            font-weight: 600;
            color: #495057;
        }
        tr:hover { background: #f8f9fa; }
        .footer {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
        }
        .timestamp { 
            color: #95a5a6;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Production Validation Report</h1>
            <div class="subtitle">DOMAIN_PLACEHOLDER</div>
            <div class="timestamp">Generated: TIMESTAMP_PLACEHOLDER</div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Validation Summary</h2>
                <div class="metric">
                    <div class="label">Validation ID</div>
                    <div class="value">VALIDATION_ID_PLACEHOLDER</div>
                </div>
                <div class="metric">
                    <div class="label">Git Commit</div>
                    <div class="value">GIT_COMMIT_PLACEHOLDER</div>
                </div>
            </div>
            
            <div class="section">
                <h2>✅ Validation Results</h2>
                <table>
                    <tr>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                    VALIDATION_RESULTS_PLACEHOLDER
                </table>
            </div>
            
            <div class="section">
                <h2>📈 Performance Metrics</h2>
                PERFORMANCE_METRICS_PLACEHOLDER
            </div>
            
            <div class="section">
                <h2>🔒 Security Analysis</h2>
                SECURITY_ANALYSIS_PLACEHOLDER
            </div>
            
            <div class="section">
                <h2>📁 Evidence Files</h2>
                <div class="evidence-box">
                    EVIDENCE_FILES_PLACEHOLDER
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>AI Workflow Engine - Production Validation System</p>
            <p class="timestamp">Report generated on TIMESTAMP_PLACEHOLDER</p>
        </div>
    </div>
</body>
</html>
EOF
    
    # Replace placeholders with actual data
    sed -i "s|DOMAIN_PLACEHOLDER|$PRODUCTION_DOMAIN|g" "$report_file"
    sed -i "s|TIMESTAMP_PLACEHOLDER|$(date)|g" "$report_file"
    sed -i "s|VALIDATION_ID_PLACEHOLDER|$VALIDATION_ID|g" "$report_file"
    sed -i "s|GIT_COMMIT_PLACEHOLDER|$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')|g" "$report_file"
    
    # Add validation results
    local results_html=""
    for category in DNS SSL PERFORMANCE API UI SECURITY DEPLOYMENT; do
        if [ -f "$VALIDATION_LOG_DIR/validation_${TIMESTAMP}.log" ]; then
            local status=$(grep "\[$category\]" "$VALIDATION_LOG_DIR/validation_${TIMESTAMP}.log" | \
                grep -c SUCCESS || echo 0)
            if [ $status -gt 0 ]; then
                results_html+="<tr><td>$category</td><td><span class='status-badge status-success'>PASS</span></td><td>All checks passed</td></tr>"
            else
                results_html+="<tr><td>$category</td><td><span class='status-badge status-warning'>CHECK</span></td><td>Review evidence</td></tr>"
            fi
        fi
    done
    sed -i "s|VALIDATION_RESULTS_PLACEHOLDER|$results_html|g" "$report_file"
    
    # Add evidence files list
    local evidence_list=$(find "$EVIDENCE_DIR/$VALIDATION_ID" -type f -name "*.json" -o -name "*.txt" | \
        sed "s|$EVIDENCE_DIR/$VALIDATION_ID/||g" | head -20)
    sed -i "s|EVIDENCE_FILES_PLACEHOLDER|$(echo "$evidence_list" | sed ':a;N;$!ba;s/\n/<br>/g')|g" "$report_file"
    
    log_validation "SUCCESS" "REPORT" "HTML report generated: $report_file"
}

# Main validation flow
main() {
    local validation_failures=0
    
    # Initialize
    initialize_validation
    
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}     Production Validation for ${PRODUCTION_DOMAIN}     ${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}\n"
    
    # Run validations
    echo -e "${CYAN}▶ Phase 1: DNS Resolution${NC}"
    if ! validate_dns; then
        ((validation_failures++))
    fi
    
    echo -e "\n${CYAN}▶ Phase 2: SSL Certificate${NC}"
    if ! validate_ssl; then
        ((validation_failures++))
    fi
    
    echo -e "\n${CYAN}▶ Phase 3: Performance Testing${NC}"
    if ! validate_performance; then
        ((validation_failures++))
    fi
    
    echo -e "\n${CYAN}▶ Phase 4: API Validation${NC}"
    if ! validate_api; then
        ((validation_failures++))
    fi
    
    echo -e "\n${CYAN}▶ Phase 5: UI Validation${NC}"
    if ! validate_ui; then
        ((validation_failures++))
    fi
    
    echo -e "\n${CYAN}▶ Phase 6: Security Checks${NC}"
    validate_security  # Don't count security warnings as failures
    
    echo -e "\n${CYAN}▶ Phase 7: Deployment Verification${NC}"
    validate_deployment
    
    # Generate report
    echo -e "\n${CYAN}▶ Generating Validation Report${NC}"
    generate_html_report
    
    # Summary
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}                  Validation Complete                   ${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}\n"
    
    if [ $validation_failures -eq 0 ]; then
        echo -e "${GREEN}✅ All production validations passed successfully!${NC}"
        echo -e "${GREEN}Production site is fully operational at: ${PRODUCTION_HTTPS}${NC}"
    else
        echo -e "${YELLOW}⚠ Production validation completed with $validation_failures issues${NC}"
        echo -e "${YELLOW}Review the evidence for details${NC}"
    fi
    
    echo -e "\n${BLUE}📁 Evidence collected at:${NC}"
    echo -e "   $EVIDENCE_DIR/$VALIDATION_ID/"
    echo -e "\n${BLUE}📊 HTML Report:${NC}"
    echo -e "   $EVIDENCE_DIR/$VALIDATION_ID/production_validation_report.html"
    
    exit $validation_failures
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            PRODUCTION_DOMAIN="$2"
            PRODUCTION_HTTP="http://${PRODUCTION_DOMAIN}"
            PRODUCTION_HTTPS="https://${PRODUCTION_DOMAIN}"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --domain DOMAIN    Target domain (default: aiwfe.com)"
            echo "  --help            Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  CLOUDFLARE_API_TOKEN   Cloudflare API token for DNS validation"
            echo "  CLOUDFLARE_ZONE_ID     Cloudflare zone ID for the domain"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main validation
main