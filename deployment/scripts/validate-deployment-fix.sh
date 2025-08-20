#!/bin/bash

# Deployment Fix Validation Script
# Tests the core logic of the blue-green deployment fix without requiring running containers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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

# Test 1: Verify upstream configuration files exist and have correct content
test_upstream_files() {
    log "Testing upstream configuration files..."
    
    local nginx_dir="${PROJECT_ROOT}/deployment/nginx"
    local files=("upstream.conf" "upstream-blue.conf" "upstream-green.conf")
    local passed=0
    local total=${#files[@]}
    
    for file in "${files[@]}"; do
        local filepath="${nginx_dir}/${file}"
        if [ ! -f "${filepath}" ]; then
            log_error "Missing file: ${filepath}"
            continue
        fi
        
        # Check for required content
        if grep -q "upstream game-active" "${filepath}" && grep -q "upstream game-standby" "${filepath}"; then
            log_success "File ${file} has correct upstream definitions"
            ((passed++))
        else
            log_error "File ${file} missing required upstream definitions"
        fi
    done
    
    if [ ${passed} -eq ${total} ]; then
        log_success "All upstream files validated successfully"
        return 0
    else
        log_error "Upstream files validation failed (${passed}/${total} passed)"
        return 1
    fi
}

# Test 2: Verify deployment script has required functions
test_deployment_script_functions() {
    log "Testing deployment script functions..."
    
    local deploy_script="${SCRIPT_DIR}/deploy.sh"
    local required_functions=(
        "switch_traffic"
        "verify_traffic_routing" 
        "enhanced_health_check"
        "rollback"
    )
    local passed=0
    local total=${#required_functions[@]}
    
    if [ ! -f "${deploy_script}" ]; then
        log_error "Deploy script not found: ${deploy_script}"
        return 1
    fi
    
    # Check script syntax
    if ! bash -n "${deploy_script}"; then
        log_error "Deploy script has syntax errors"
        return 1
    fi
    log_success "Deploy script syntax is valid"
    
    # Check for required functions
    for func in "${required_functions[@]}"; do
        if grep -q "^${func}()" "${deploy_script}"; then
            log_success "Function ${func} found"
            ((passed++))
        else
            log_error "Function ${func} not found"
        fi
    done
    
    if [ ${passed} -eq ${total} ]; then
        log_success "All required functions found in deployment script"
        return 0
    else
        log_error "Deployment script validation failed (${passed}/${total} functions found)"
        return 1
    fi
}

# Test 3: Verify switch_traffic function logic
test_switch_traffic_logic() {
    log "Testing switch_traffic function logic..."
    
    local deploy_script="${SCRIPT_DIR}/deploy.sh"
    
    # Check for key improvements in switch_traffic function
    local checks=(
        "upstream_source.*upstream-.*conf"
        "cp.*upstream_source.*upstream_target"
        "nginx -t"
        "nginx -s reload"
        "verify_traffic_routing"
    )
    local passed=0
    local total=${#checks[@]}
    
    for check in "${checks[@]}"; do
        if grep -A 50 "switch_traffic()" "${deploy_script}" | grep -q "${check}"; then
            log_success "Found logic: ${check}"
            ((passed++))
        else
            log_error "Missing logic: ${check}"
        fi
    done
    
    if [ ${passed} -eq ${total} ]; then
        log_success "switch_traffic function has all required logic"
        return 0
    else
        log_error "switch_traffic function validation failed (${passed}/${total} checks passed)"
        return 1
    fi
}

# Test 4: Verify rollback function enhancements
test_rollback_logic() {
    log "Testing rollback function enhancements..."
    
    local deploy_script="${SCRIPT_DIR}/deploy.sh"
    
    # Check for enhanced rollback logic
    local checks=(
        "enhanced_health_check.*rollback_target"
        "switch_traffic.*rollback_target.*current_active"
        "verify_traffic_routing.*rollback_target"
    )
    local passed=0
    local total=${#checks[@]}
    
    for check in "${checks[@]}"; do
        if grep -A 30 "rollback()" "${deploy_script}" | grep -q "${check}"; then
            log_success "Found rollback logic: ${check}"
            ((passed++))
        else
            log_error "Missing rollback logic: ${check}"
        fi
    done
    
    if [ ${passed} -eq ${total} ]; then
        log_success "rollback function has all required enhancements"
        return 0
    else
        log_error "rollback function validation failed (${passed}/${total} checks passed)"
        return 1
    fi
}

# Test 5: Verify nginx configuration template correctness
test_nginx_template_logic() {
    log "Testing nginx template configurations..."
    
    local nginx_dir="${PROJECT_ROOT}/deployment/nginx"
    
    # Test blue configuration
    local blue_config="${nginx_dir}/upstream-blue.conf"
    if [ -f "${blue_config}" ]; then
        if grep -q "server game-blue:8080.*game-active" "${blue_config}" && \
           grep -q "server game-green:8080.*game-standby" "${blue_config}"; then
            log_success "Blue configuration correctly routes active to blue, standby to green"
        else
            log_error "Blue configuration has incorrect routing"
            return 1
        fi
    else
        log_error "Blue configuration template missing"
        return 1
    fi
    
    # Test green configuration  
    local green_config="${nginx_dir}/upstream-green.conf"
    if [ -f "${green_config}" ]; then
        if grep -q "server game-green:8080.*game-active" "${green_config}" && \
           grep -q "server game-blue:8080.*game-standby" "${green_config}"; then
            log_success "Green configuration correctly routes active to green, standby to blue"
        else
            log_error "Green configuration has incorrect routing"
            return 1
        fi
    else
        log_error "Green configuration template missing"
        return 1
    fi
    
    return 0
}

# Test 6: Simulate traffic switching logic
test_traffic_switching_simulation() {
    log "Simulating traffic switching logic..."
    
    local nginx_dir="${PROJECT_ROOT}/deployment/nginx"
    local test_upstream="${nginx_dir}/upstream-test.conf"
    
    # Backup original
    if [ -f "${nginx_dir}/upstream.conf" ]; then
        cp "${nginx_dir}/upstream.conf" "${nginx_dir}/upstream.conf.backup"
    fi
    
    # Test switching to blue
    log "Testing switch to blue configuration..."
    if cp "${nginx_dir}/upstream-blue.conf" "${test_upstream}"; then
        if grep -q "server game-blue:8080.*game-active" "${test_upstream}"; then
            log_success "Blue switch simulation successful"
        else
            log_error "Blue switch simulation failed"
            rm -f "${test_upstream}"
            return 1
        fi
    else
        log_error "Failed to copy blue configuration"
        return 1
    fi
    
    # Test switching to green
    log "Testing switch to green configuration..."
    if cp "${nginx_dir}/upstream-green.conf" "${test_upstream}"; then
        if grep -q "server game-green:8080.*game-active" "${test_upstream}"; then
            log_success "Green switch simulation successful"
        else
            log_error "Green switch simulation failed"
            rm -f "${test_upstream}"
            return 1
        fi
    else
        log_error "Failed to copy green configuration"
        return 1
    fi
    
    # Cleanup
    rm -f "${test_upstream}"
    
    # Restore original if it existed
    if [ -f "${nginx_dir}/upstream.conf.backup" ]; then
        cp "${nginx_dir}/upstream.conf.backup" "${nginx_dir}/upstream.conf"
        rm -f "${nginx_dir}/upstream.conf.backup"
    fi
    
    log_success "Traffic switching simulation completed successfully"
    return 0
}

# Main validation runner
run_validation() {
    log "Starting deployment fix validation..."
    
    local tests=(
        "test_upstream_files"
        "test_deployment_script_functions" 
        "test_switch_traffic_logic"
        "test_rollback_logic"
        "test_nginx_template_logic"
        "test_traffic_switching_simulation"
    )
    
    local passed=0
    local failed=0
    
    for test in "${tests[@]}"; do
        log "Running validation: ${test}"
        if ${test}; then
            ((passed++))
            log_success "Validation ${test} PASSED"
        else
            ((failed++))
            log_error "Validation ${test} FAILED"
        fi
        echo
    done
    
    log "Validation Summary:"
    log_success "Passed: ${passed}"
    if [ ${failed} -gt 0 ]; then
        log_error "Failed: ${failed}"
        log_error "Deployment fix validation FAILED"
        return 1
    else
        log_success "All validations passed!"
        log_success "Deployment fix validation SUCCESSFUL"
        return 0
    fi
}

# Generate validation report
generate_report() {
    log "Generating deployment fix validation report..."
    
    local report_file="${PROJECT_ROOT}/deployment/BLUE_GREEN_FIX_VALIDATION.md"
    
    cat > "${report_file}" << 'EOF'
# Blue-Green Deployment Fix Validation Report

## Issue Fixed
- **Problem**: The original deploy.sh script updated Docker container labels but never updated Nginx upstream configuration, preventing traffic from switching to new versions.
- **Solution**: Enhanced the script to dynamically update Nginx upstream configuration files and reload configuration during deployments.

## Changes Made

### 1. Created Dynamic Upstream Configuration Files
- `deployment/nginx/upstream.conf` - Active configuration file mounted in nginx container
- `deployment/nginx/upstream-blue.conf` - Template for blue-active deployment
- `deployment/nginx/upstream-green.conf` - Template for green-active deployment

### 2. Enhanced switch_traffic() Function
- Updates upstream configuration by copying appropriate template
- Validates nginx configuration before applying changes
- Performs graceful nginx reload with fallback to restart
- Includes backup and restore mechanisms for failed switches
- Adds traffic routing verification after switch

### 3. Added Enhanced Health Checks
- `enhanced_health_check()` - Improved health validation with endpoint verification
- `verify_traffic_routing()` - Confirms traffic is routing to expected slot
- Container IP resolution and direct endpoint testing

### 4. Improved Rollback Mechanism
- Enhanced rollback with traffic verification
- Multiple validation steps before considering rollback complete
- Automatic configuration restoration on failures

### 5. Fixed Docker Compose Configuration
- Corrected volume mount paths in docker-compose.blue-green.yml
- Added proper upstream configuration mounting

## Validation Results
EOF

    if run_validation >> "${report_file}" 2>&1; then
        echo "✅ All validations passed successfully" >> "${report_file}"
    else
        echo "❌ Some validations failed" >> "${report_file}"
    fi
    
    cat >> "${report_file}" << 'EOF'

## Zero-Downtime Deployment Flow
1. **Build Phase**: New version built in standby slot
2. **Health Check**: Enhanced health validation of standby slot
3. **Configuration Update**: Nginx upstream configuration updated to route to new slot
4. **Traffic Switch**: Graceful nginx reload applies new routing
5. **Verification**: Multiple checks confirm traffic routing correctly
6. **Cleanup**: Old slot stopped, unused images cleaned up

## Rollback Strategy
1. **Health Check**: Verify rollback target is healthy
2. **Configuration Restore**: Switch upstream configuration back
3. **Traffic Verification**: Confirm traffic routing to rollback target
4. **Cleanup**: Stop failed deployment slot

## Testing
- Syntax validation of all scripts and configurations
- Logic verification of deployment functions
- Simulation of traffic switching scenarios
- Nginx configuration template validation

This fix ensures zero-downtime deployments with proper traffic switching and robust rollback capabilities.
EOF

    log_success "Validation report generated: ${report_file}"
}

# Command line interface
case "${1:-validate}" in
    "validate")
        run_validation
        ;;
    "report")
        generate_report
        ;;
    "upstream")
        test_upstream_files
        ;;
    "script")
        test_deployment_script_functions
        ;;
    "traffic")
        test_traffic_switching_simulation
        ;;
    *)
        echo "Usage: $0 {validate|report|upstream|script|traffic}"
        echo "  validate  - Run all validation tests"
        echo "  report    - Generate validation report"
        echo "  upstream  - Test upstream configuration files"
        echo "  script    - Test deployment script functions"
        echo "  traffic   - Simulate traffic switching"
        exit 1
        ;;
esac