#!/bin/bash

# Test Script for Blue-Green Deployment Fix
# Validates that traffic switching works correctly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/deployment/docker-compose/docker-compose.blue-green.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC} - $1"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ✅ $1"
}

log_error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ❌ $1" >&2
}

log_warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC} - ⚠️  $1"
}

# Test upstream configuration files exist
test_upstream_files() {
    log "Testing upstream configuration files..."
    
    local nginx_dir="${PROJECT_ROOT}/deployment/nginx"
    local files=("upstream.conf" "upstream-blue.conf" "upstream-green.conf")
    
    for file in "${files[@]}"; do
        if [ ! -f "${nginx_dir}/${file}" ]; then
            log_error "Missing upstream file: ${nginx_dir}/${file}"
            return 1
        fi
        log_success "Found: ${nginx_dir}/${file}"
    done
    
    return 0
}

# Test nginx configuration syntax
test_nginx_syntax() {
    log "Testing nginx configuration syntax..."
    
    # Check if nginx container is running
    if ! docker compose -f "${COMPOSE_FILE}" ps nginx-lb | grep -q "Up"; then
        log_warning "Nginx container not running, starting for syntax test..."
        if ! docker compose -f "${COMPOSE_FILE}" up -d nginx-lb; then
            log_error "Failed to start nginx container"
            return 1
        fi
        sleep 5
    fi
    
    # Test current configuration
    if docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -t; then
        log_success "Nginx configuration syntax is valid"
        return 0
    else
        log_error "Nginx configuration syntax error"
        return 1
    fi
}

# Test upstream configuration switching
test_upstream_switching() {
    log "Testing upstream configuration switching..."
    
    local nginx_dir="${PROJECT_ROOT}/deployment/nginx"
    local original_config="${nginx_dir}/upstream.conf"
    local backup_config="${nginx_dir}/upstream.conf.test-backup"
    
    # Backup original config
    if [ -f "${original_config}" ]; then
        cp "${original_config}" "${backup_config}"
    fi
    
    # Test switching to blue
    log "Testing switch to blue configuration..."
    if cp "${nginx_dir}/upstream-blue.conf" "${original_config}"; then
        if docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -t >/dev/null 2>&1; then
            log_success "Blue configuration switch successful"
        else
            log_error "Blue configuration caused nginx syntax error"
            # Restore backup
            if [ -f "${backup_config}" ]; then
                cp "${backup_config}" "${original_config}"
            fi
            return 1
        fi
    else
        log_error "Failed to copy blue configuration"
        return 1
    fi
    
    # Test switching to green
    log "Testing switch to green configuration..."
    if cp "${nginx_dir}/upstream-green.conf" "${original_config}"; then
        if docker compose -f "${COMPOSE_FILE}" exec nginx-lb nginx -t >/dev/null 2>&1; then
            log_success "Green configuration switch successful"
        else
            log_error "Green configuration caused nginx syntax error"
            # Restore backup
            if [ -f "${backup_config}" ]; then
                cp "${backup_config}" "${original_config}"
            fi
            return 1
        fi
    else
        log_error "Failed to copy green configuration"
        return 1
    fi
    
    # Restore original configuration
    if [ -f "${backup_config}" ]; then
        cp "${backup_config}" "${original_config}"
        rm -f "${backup_config}"
        log_success "Original configuration restored"
    fi
    
    return 0
}

# Test deployment script functions
test_deployment_functions() {
    log "Testing deployment script functions..."
    
    local deploy_script="${SCRIPT_DIR}/deploy.sh"
    
    if [ ! -f "${deploy_script}" ]; then
        log_error "Deploy script not found: ${deploy_script}"
        return 1
    fi
    
    # Test script syntax
    if bash -n "${deploy_script}"; then
        log_success "Deploy script syntax is valid"
    else
        log_error "Deploy script has syntax errors"
        return 1
    fi
    
    # Test that required functions exist
    local required_functions=("switch_traffic" "verify_traffic_routing" "enhanced_health_check")
    
    for func in "${required_functions[@]}"; do
        if grep -q "^${func}()" "${deploy_script}"; then
            log_success "Function ${func} found in deploy script"
        else
            log_error "Function ${func} not found in deploy script"
            return 1
        fi
    done
    
    return 0
}

# Test static asset optimization
test_static_assets() {
    log "Testing static asset optimization..."
    
    local sync_script="${SCRIPT_DIR}/sync-static-assets.sh"
    
    if [ ! -f "${sync_script}" ]; then
        log_error "Static asset sync script not found: ${sync_script}"
        return 1
    fi
    
    # Test script syntax
    if bash -n "${sync_script}"; then
        log_success "Static asset sync script syntax is valid"
    else
        log_error "Static asset sync script has syntax errors"
        return 1
    fi
    
    # Test that script is executable
    if [ -x "${sync_script}" ]; then
        log_success "Static asset sync script is executable"
    else
        log_error "Static asset sync script is not executable"
        return 1
    fi
    
    # Check that docker-compose has static asset volumes
    if grep -q "game-static-assets" "${COMPOSE_FILE}"; then
        log_success "Static asset volume configuration found in docker-compose"
    else
        log_error "Static asset volume configuration not found in docker-compose"
        return 1
    fi
    
    # Check nginx cache volume
    if grep -q "nginx-cache" "${COMPOSE_FILE}"; then
        log_success "Nginx cache volume configuration found in docker-compose"
    else
        log_error "Nginx cache volume configuration not found in docker-compose"
        return 1
    fi
    
    return 0
}

# Test docker-compose configuration
test_docker_compose() {
    log "Testing docker-compose configuration..."
    
    if [ ! -f "${COMPOSE_FILE}" ]; then
        log_error "Docker compose file not found: ${COMPOSE_FILE}"
        return 1
    fi
    
    # Validate compose file syntax
    if docker compose -f "${COMPOSE_FILE}" config >/dev/null 2>&1; then
        log_success "Docker compose configuration is valid"
    else
        log_error "Docker compose configuration has errors"
        return 1
    fi
    
    # Check that required services are defined
    local required_services=("nginx-lb" "game-blue" "game-green")
    
    for service in "${required_services[@]}"; do
        if docker compose -f "${COMPOSE_FILE}" config --services | grep -q "^${service}$"; then
            log_success "Service ${service} found in compose configuration"
        else
            log_error "Service ${service} not found in compose configuration"
            return 1
        fi
    done
    
    return 0
}

# Main test runner
run_tests() {
    log "Starting blue-green deployment tests..."
    
    local tests=(
        "test_upstream_files"
        "test_docker_compose"
        "test_nginx_syntax"
        "test_upstream_switching"
        "test_deployment_functions"
        "test_static_assets"
    )
    
    local passed=0
    local failed=0
    
    for test in "${tests[@]}"; do
        log "Running test: ${test}"
        if ${test}; then
            ((passed++))
            log_success "Test ${test} PASSED"
        else
            ((failed++))
            log_error "Test ${test} FAILED"
        fi
        echo
    done
    
    log "Test Summary:"
    log_success "Passed: ${passed}"
    if [ ${failed} -gt 0 ]; then
        log_error "Failed: ${failed}"
        return 1
    else
        log_success "All tests passed!"
        return 0
    fi
}

# Command line interface
case "${1:-test}" in
    "test")
        run_tests
        ;;
    "upstream")
        test_upstream_files && test_upstream_switching
        ;;
    "nginx")
        test_nginx_syntax
        ;;
    "compose")
        test_docker_compose
        ;;
    "functions")
        test_deployment_functions
        ;;
    "static")
        test_static_assets
        ;;
    *)
        echo "Usage: $0 {test|upstream|nginx|compose|functions|static}"
        echo "  test      - Run all tests"
        echo "  upstream  - Test upstream configuration files"
        echo "  nginx     - Test nginx configuration syntax"
        echo "  compose   - Test docker-compose configuration"
        echo "  functions - Test deployment script functions"
        echo "  static    - Test static asset optimization"
        exit 1
        ;;
esac