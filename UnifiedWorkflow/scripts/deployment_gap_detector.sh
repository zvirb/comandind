#!/bin/bash
# Deployment Gap Detection and Automated Resolution System
# Identifies gaps between implementation and production deployment and provides automated fixes

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GAP_LOG_DIR="$PROJECT_ROOT/logs/deployment_gaps"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
GAP_ID="gap_${TIMESTAMP}"

# Production configuration
PRODUCTION_DOMAIN="${PRODUCTION_DOMAIN:-aiwfe.com}"
PRODUCTION_URL="https://${PRODUCTION_DOMAIN}"

# Gap detection thresholds
MAX_IMAGE_AGE_DAYS=7
MAX_CONFIG_DRIFT_ITEMS=5
MIN_SERVICE_COVERAGE=90  # percentage

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Gap types
declare -A GAP_TYPES
GAP_TYPES["CONFIG"]="Configuration mismatch"
GAP_TYPES["IMAGE"]="Container image outdated"
GAP_TYPES["SERVICE"]="Service not deployed"
GAP_TYPES["ENV"]="Environment variable missing"
GAP_TYPES["SECRET"]="Secret not configured"
GAP_TYPES["VOLUME"]="Volume not mounted"
GAP_TYPES["NETWORK"]="Network configuration issue"
GAP_TYPES["HEALTH"]="Health check failing"
GAP_TYPES["VERSION"]="Version mismatch"
GAP_TYPES["DEPENDENCY"]="Dependency not satisfied"

# Initialize gap detection
initialize_gap_detection() {
    echo -e "${BLUE}[INIT]${NC} Initializing deployment gap detection (ID: $GAP_ID)"
    
    mkdir -p "$GAP_LOG_DIR/$GAP_ID"/{config,services,environment,resolution}
    
    # Create metadata
    cat > "$GAP_LOG_DIR/$GAP_ID/metadata.json" << EOF
{
    "gap_id": "$GAP_ID",
    "timestamp": "$(date -Iseconds)",
    "production_domain": "$PRODUCTION_DOMAIN",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git branch --show-current 2>/dev/null || echo 'unknown')"
}
EOF
}

# Log gap detection
log_gap() {
    local type=$1
    local severity=$2
    local message=$3
    local details=$4
    
    case $severity in
        CRITICAL) echo -e "${RED}[CRITICAL]${NC} $message" ;;
        HIGH)     echo -e "${YELLOW}[HIGH]${NC} $message" ;;
        MEDIUM)   echo -e "${CYAN}[MEDIUM]${NC} $message" ;;
        LOW)      echo -e "${BLUE}[LOW]${NC} $message" ;;
        FIXED)    echo -e "${GREEN}[FIXED]${NC} $message" ;;
    esac
    
    # Log to file
    cat >> "$GAP_LOG_DIR/$GAP_ID/gaps.jsonl" << EOF
{"timestamp":"$(date -Iseconds)","type":"$type","severity":"$severity","message":"$message","details":$details}
EOF
}

# Check configuration gaps
check_config_gaps() {
    echo -e "\n${CYAN}▶ Checking Configuration Gaps${NC}"
    
    local gaps_found=0
    
    # Check docker-compose.yml consistency
    if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        local compose_hash=$(sha256sum "$PROJECT_ROOT/docker-compose.yml" | cut -d' ' -f1)
        local deployed_hash=""
        
        # Check if there's a deployed version marker
        if [ -f "$PROJECT_ROOT/.deployed/compose.hash" ]; then
            deployed_hash=$(cat "$PROJECT_ROOT/.deployed/compose.hash")
        fi
        
        if [ "$compose_hash" != "$deployed_hash" ]; then
            log_gap "CONFIG" "HIGH" "docker-compose.yml has uncommitted changes" \
                '{"current_hash":"'$compose_hash'","deployed_hash":"'$deployed_hash'"}'
            ((gaps_found++))
        fi
    fi
    
    # Check for configuration files
    local config_files=(
        "config/caddy/Caddyfile"
        "config/prometheus/prometheus.yml"
        "config/alertmanager/alertmanager.yml"
        "config/grafana/provisioning/datasources/prometheus.yml"
    )
    
    for config_file in "${config_files[@]}"; do
        if [ ! -f "$PROJECT_ROOT/$config_file" ]; then
            log_gap "CONFIG" "MEDIUM" "Missing configuration file: $config_file" \
                '{"file":"'$config_file'"}'
            ((gaps_found++))
        else
            # Check if config file has been modified
            if [ -n "$(git status --porcelain "$PROJECT_ROOT/$config_file" 2>/dev/null)" ]; then
                log_gap "CONFIG" "MEDIUM" "Uncommitted changes in $config_file" \
                    '{"file":"'$config_file'"}'
                ((gaps_found++))
            fi
        fi
    done
    
    echo -e "Configuration gaps found: $gaps_found"
    return $gaps_found
}

# Check container image gaps
check_image_gaps() {
    echo -e "\n${CYAN}▶ Checking Container Image Gaps${NC}"
    
    local gaps_found=0
    local images_info="$GAP_LOG_DIR/$GAP_ID/services/images.json"
    
    # Get all service images
    docker compose images --format json > "$images_info" 2>/dev/null || echo '[]' > "$images_info"
    
    # Check for outdated images
    while IFS= read -r image_json; do
        local repository=$(echo "$image_json" | jq -r '.Repository // ""')
        local tag=$(echo "$image_json" | jq -r '.Tag // ""')
        local created=$(echo "$image_json" | jq -r '.CreatedSince // ""')
        
        if [ "$tag" = "latest" ] && [ -n "$repository" ]; then
            log_gap "IMAGE" "MEDIUM" "Service using 'latest' tag: $repository" \
                '{"repository":"'$repository'","tag":"'$tag'"}'
            ((gaps_found++))
        fi
        
        # Check image age (if created date available)
        if [[ "$created" =~ "months" ]] || [[ "$created" =~ "years" ]]; then
            log_gap "IMAGE" "LOW" "Potentially outdated image: $repository:$tag ($created old)" \
                '{"repository":"'$repository'","tag":"'$tag'","age":"'$created'"}'
            ((gaps_found++))
        fi
    done < <(jq -c '.[]' "$images_info" 2>/dev/null)
    
    # Check for missing images
    local expected_services=$(docker compose config --services 2>/dev/null)
    for service in $expected_services; do
        if ! docker compose images "$service" --quiet 2>/dev/null | grep -q .; then
            log_gap "IMAGE" "HIGH" "Service image not built: $service" \
                '{"service":"'$service'"}'
            ((gaps_found++))
        fi
    done
    
    echo -e "Image gaps found: $gaps_found"
    return $gaps_found
}

# Check service deployment gaps
check_service_gaps() {
    echo -e "\n${CYAN}▶ Checking Service Deployment Gaps${NC}"
    
    local gaps_found=0
    local expected_services=$(docker compose config --services 2>/dev/null | wc -l)
    local running_services=$(docker compose ps --services --filter "status=running" 2>/dev/null | wc -l)
    
    local coverage=$((running_services * 100 / expected_services))
    
    if [ $coverage -lt $MIN_SERVICE_COVERAGE ]; then
        log_gap "SERVICE" "CRITICAL" "Low service coverage: $coverage% (minimum: $MIN_SERVICE_COVERAGE%)" \
            '{"running":'$running_services',"expected":'$expected_services',"coverage":'$coverage'}'
        ((gaps_found++))
    fi
    
    # Check individual services
    local all_services=$(docker compose config --services 2>/dev/null)
    for service in $all_services; do
        local status=$(docker compose ps "$service" --format json 2>/dev/null | \
            jq -r '.[0].State // "not_found"' 2>/dev/null)
        
        if [ "$status" != "running" ]; then
            log_gap "SERVICE" "HIGH" "Service not running: $service (status: $status)" \
                '{"service":"'$service'","status":"'$status'"}'
            ((gaps_found++))
        fi
    done
    
    echo -e "Service gaps found: $gaps_found"
    return $gaps_found
}

# Check environment gaps
check_environment_gaps() {
    echo -e "\n${CYAN}▶ Checking Environment Gaps${NC}"
    
    local gaps_found=0
    
    # Check .env file
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_gap "ENV" "CRITICAL" "Missing .env file" '{"file":".env"}'
        ((gaps_found++))
    else
        # Check for required environment variables
        local required_vars=(
            "DOMAIN"
            "ADMIN_EMAIL"
            "DATABASE_URL"
            "REDIS_URL"
            "API_URL"
        )
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^$var=" "$PROJECT_ROOT/.env" 2>/dev/null; then
                log_gap "ENV" "HIGH" "Missing environment variable: $var" \
                    '{"variable":"'$var'"}'
                ((gaps_found++))
            fi
        done
    fi
    
    # Check secrets
    local required_secrets=(
        "postgres_password.txt"
        "jwt_secret_key.txt"
        "api_key.txt"
        "admin_email.txt"
        "admin_password.txt"
        "redis_password.txt"
    )
    
    for secret in "${required_secrets[@]}"; do
        if [ ! -f "$PROJECT_ROOT/secrets/$secret" ]; then
            log_gap "SECRET" "CRITICAL" "Missing secret file: $secret" \
                '{"secret":"'$secret'"}'
            ((gaps_found++))
        fi
    done
    
    echo -e "Environment gaps found: $gaps_found"
    return $gaps_found
}

# Check health and connectivity gaps
check_health_gaps() {
    echo -e "\n${CYAN}▶ Checking Health and Connectivity Gaps${NC}"
    
    local gaps_found=0
    
    # Check production endpoint
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$PRODUCTION_URL" 2>/dev/null)
    
    if [ "$http_code" -ne 200 ] && [ "$http_code" -ne 301 ] && [ "$http_code" -ne 302 ]; then
        log_gap "HEALTH" "CRITICAL" "Production endpoint not accessible (HTTP $http_code)" \
            '{"url":"'$PRODUCTION_URL'","http_code":'$http_code'}'
        ((gaps_found++))
    fi
    
    # Check API health
    local api_health=$(curl -s --max-time 10 "$PRODUCTION_URL/api/health" 2>/dev/null | \
        jq -r '.status // "unknown"' 2>/dev/null)
    
    if [ "$api_health" != "healthy" ] && [ "$api_health" != "ok" ]; then
        log_gap "HEALTH" "HIGH" "API health check failing" \
            '{"endpoint":"/api/health","status":"'$api_health'"}'
        ((gaps_found++))
    fi
    
    # Check database connectivity
    if ! docker compose exec -T postgres pg_isready -U app_user -d ai_workflow_db >/dev/null 2>&1; then
        log_gap "HEALTH" "CRITICAL" "Database connectivity issue" \
            '{"service":"postgres","check":"pg_isready"}'
        ((gaps_found++))
    fi
    
    echo -e "Health gaps found: $gaps_found"
    return $gaps_found
}

# Automated gap resolution
resolve_gaps() {
    echo -e "\n${MAGENTA}▶ Attempting Automated Gap Resolution${NC}"
    
    local resolved_count=0
    local failed_count=0
    
    # Read gaps and attempt resolution
    while IFS= read -r gap_json; do
        local gap_type=$(echo "$gap_json" | jq -r '.type')
        local severity=$(echo "$gap_json" | jq -r '.severity')
        local message=$(echo "$gap_json" | jq -r '.message')
        
        case $gap_type in
            SERVICE)
                echo -e "${BLUE}[RESOLVE]${NC} Attempting to start stopped services..."
                if bash "$SCRIPT_DIR/service_recovery.sh" --recover >/dev/null 2>&1; then
                    log_gap "SERVICE" "FIXED" "Services recovered successfully" '{}'
                    ((resolved_count++))
                else
                    ((failed_count++))
                fi
                ;;
                
            ENV)
                if [[ "$message" == "Missing .env file" ]]; then
                    echo -e "${BLUE}[RESOLVE]${NC} Creating .env from template..."
                    if [ -f "$PROJECT_ROOT/.env.example" ]; then
                        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
                        log_gap "ENV" "FIXED" "Created .env from template" '{}'
                        ((resolved_count++))
                    else
                        ((failed_count++))
                    fi
                fi
                ;;
                
            SECRET)
                # For demo purposes, create placeholder secrets (in production, use vault)
                local secret_file=$(echo "$message" | grep -oP 'secrets/\K[^"]+')
                if [ -n "$secret_file" ]; then
                    echo -e "${BLUE}[RESOLVE]${NC} Generating placeholder secret: $secret_file"
                    mkdir -p "$PROJECT_ROOT/secrets"
                    openssl rand -base64 32 > "$PROJECT_ROOT/secrets/$secret_file"
                    log_gap "SECRET" "FIXED" "Generated placeholder secret: $secret_file" \
                        '{"secret":"'$secret_file'"}'
                    ((resolved_count++))
                fi
                ;;
                
            IMAGE)
                if [[ "$message" == *"not built"* ]]; then
                    local service=$(echo "$gap_json" | jq -r '.details.service')
                    echo -e "${BLUE}[RESOLVE]${NC} Building image for service: $service"
                    if docker compose build "$service" >/dev/null 2>&1; then
                        log_gap "IMAGE" "FIXED" "Built image for service: $service" \
                            '{"service":"'$service'"}'
                        ((resolved_count++))
                    else
                        ((failed_count++))
                    fi
                fi
                ;;
        esac
    done < <(cat "$GAP_LOG_DIR/$GAP_ID/gaps.jsonl" 2>/dev/null)
    
    echo -e "\n${GREEN}Resolved: $resolved_count gaps${NC}"
    echo -e "${RED}Failed to resolve: $failed_count gaps${NC}"
    
    return $failed_count
}

# Generate gap report
generate_gap_report() {
    local report_file="$GAP_LOG_DIR/$GAP_ID/gap_report.json"
    
    echo -e "\n${CYAN}▶ Generating Gap Analysis Report${NC}"
    
    # Count gaps by type and severity
    local gap_summary=$(cat "$GAP_LOG_DIR/$GAP_ID/gaps.jsonl" 2>/dev/null | \
        jq -s 'group_by(.type) | map({type: .[0].type, count: length, 
            severities: group_by(.severity) | map({severity: .[0].severity, count: length})})' \
        2>/dev/null || echo '[]')
    
    # Generate comprehensive report
    cat > "$report_file" << EOF
{
    "gap_id": "$GAP_ID",
    "timestamp": "$(date -Iseconds)",
    "production_domain": "$PRODUCTION_DOMAIN",
    "summary": $gap_summary,
    "total_gaps": $(cat "$GAP_LOG_DIR/$GAP_ID/gaps.jsonl" 2>/dev/null | wc -l || echo 0),
    "critical_gaps": $(grep '"severity":"CRITICAL"' "$GAP_LOG_DIR/$GAP_ID/gaps.jsonl" 2>/dev/null | wc -l || echo 0),
    "resolved_gaps": $(grep '"severity":"FIXED"' "$GAP_LOG_DIR/$GAP_ID/gaps.jsonl" 2>/dev/null | wc -l || echo 0)
}
EOF
    
    echo -e "${GREEN}Gap report generated: $report_file${NC}"
}

# Generate deployment script
generate_deployment_script() {
    local script_file="$GAP_LOG_DIR/$GAP_ID/resolution/deploy_fixes.sh"
    
    echo -e "\n${CYAN}▶ Generating Deployment Fix Script${NC}"
    
    cat > "$script_file" << 'EOF'
#!/bin/bash
# Auto-generated deployment fix script
# Generated by gap detection system

set -e

echo "Starting automated deployment fixes..."

# Fix configuration gaps
fix_config() {
    echo "Fixing configuration gaps..."
    
    # Ensure all config directories exist
    mkdir -p config/{caddy,prometheus,alertmanager,grafana/provisioning/datasources}
    
    # Generate missing configs from templates if available
    for template in config/**/*.example; do
        if [ -f "$template" ]; then
            target="${template%.example}"
            if [ ! -f "$target" ]; then
                cp "$template" "$target"
                echo "Created $target from template"
            fi
        fi
    done
}

# Fix service gaps
fix_services() {
    echo "Fixing service gaps..."
    
    # Build missing images
    docker compose build --pull
    
    # Start all services
    docker compose up -d
    
    # Wait for health
    sleep 30
    
    # Verify all services are running
    docker compose ps
}

# Fix environment gaps
fix_environment() {
    echo "Fixing environment gaps..."
    
    # Create .env if missing
    if [ ! -f .env ] && [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from template"
    fi
    
    # Ensure secrets directory exists
    mkdir -p secrets
    
    # Note: In production, secrets should be managed securely
    echo "Please ensure all required secrets are properly configured"
}

# Main execution
main() {
    fix_config
    fix_environment
    fix_services
    
    echo "Deployment fixes completed!"
    echo "Run production validation to verify: ./scripts/production_validation.sh"
}

main "$@"
EOF
    
    chmod +x "$script_file"
    echo -e "${GREEN}Deployment fix script generated: $script_file${NC}"
}

# Main gap detection flow
main() {
    local total_gaps=0
    local auto_fix=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-fix)
                auto_fix=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --auto-fix    Attempt to automatically fix detected gaps"
                echo "  --help       Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Initialize
    initialize_gap_detection
    
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}        Deployment Gap Detection & Analysis         ${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    
    # Run gap checks
    local config_gaps=0
    check_config_gaps || config_gaps=$?
    total_gaps=$((total_gaps + config_gaps))
    
    local image_gaps=0
    check_image_gaps || image_gaps=$?
    total_gaps=$((total_gaps + image_gaps))
    
    local service_gaps=0
    check_service_gaps || service_gaps=$?
    total_gaps=$((total_gaps + service_gaps))
    
    local env_gaps=0
    check_environment_gaps || env_gaps=$?
    total_gaps=$((total_gaps + env_gaps))
    
    local health_gaps=0
    check_health_gaps || health_gaps=$?
    total_gaps=$((total_gaps + health_gaps))
    
    # Attempt auto-fix if requested
    if [ "$auto_fix" = true ] && [ $total_gaps -gt 0 ]; then
        resolve_gaps
    fi
    
    # Generate reports
    generate_gap_report
    generate_deployment_script
    
    # Summary
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}                   Gap Analysis Summary                 ${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════${NC}\n"
    
    if [ $total_gaps -eq 0 ]; then
        echo -e "${GREEN}✅ No deployment gaps detected!${NC}"
        echo -e "${GREEN}System is fully deployed and operational${NC}"
    else
        echo -e "${YELLOW}⚠ Found $total_gaps deployment gaps${NC}"
        echo -e "${YELLOW}Review the gap report for details${NC}"
        
        if [ "$auto_fix" != true ]; then
            echo -e "\n${BLUE}To attempt automatic fixes, run:${NC}"
            echo -e "  $0 --auto-fix"
        fi
        
        echo -e "\n${BLUE}To manually fix gaps, run:${NC}"
        echo -e "  $GAP_LOG_DIR/$GAP_ID/resolution/deploy_fixes.sh"
    fi
    
    echo -e "\n${BLUE}📁 Gap analysis results:${NC}"
    echo -e "   $GAP_LOG_DIR/$GAP_ID/"
    
    exit $([ $total_gaps -eq 0 ] && echo 0 || echo 1)
}

# Run main
main "$@"