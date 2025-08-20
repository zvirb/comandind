#!/bin/bash

# Security Monitoring Validation Script
# This script validates the deployment and functionality of the comprehensive security monitoring infrastructure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running in correct directory
if [[ ! -f "docker-compose.yml" ]]; then
    error "This script must be run from the project root directory"
    exit 1
fi

log "Starting security monitoring infrastructure validation..."

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    ((TESTS_RUN++))
    log "Running test: $test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        success "✓ $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        error "✗ $test_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

# 1. Validate Docker Compose Configuration
log "Validating Docker Compose configuration..."

run_test "Docker Compose file syntax" "docker-compose config"
run_test "AlertManager service defined" "docker-compose config | grep -q 'alertmanager:'"
run_test "Security metrics router integration" "grep -q 'security_metrics_router' app/api/main.py"

# 2. Validate Security Service Files
log "Validating security service files..."

run_test "Security metrics service exists" "test -f app/shared/services/security_metrics_service.py"
run_test "Security event processor exists" "test -f app/shared/services/security_event_processor.py"
run_test "Automated security response service exists" "test -f app/shared/services/automated_security_response_service.py"
run_test "Threat detection service exists" "test -f app/shared/services/threat_detection_service.py"
run_test "Security models updated" "grep -q 'SecurityAction' app/shared/database/models/security_models.py"

# 3. Validate Configuration Files
log "Validating configuration files..."

run_test "AlertManager configuration exists" "test -f config/alertmanager/alertmanager.yml"
run_test "Prometheus security rules exist" "test -f config/prometheus/security_rules.yml"
run_test "Grafana security dashboards exist" "test -d config/grafana/provisioning/dashboards/security"
run_test "AlertManager entrypoint wrapper exists" "test -f docker/alertmanager/entrypoint-wrapper.sh"

# 4. Check for required dependencies
log "Checking Python dependencies..."

run_test "Prometheus client available" "python3 -c 'import prometheus_client'"
run_test "NumPy available for threat detection" "python3 -c 'import numpy'"
run_test "Redis client available" "python3 -c 'import redis.asyncio'"

# 5. Validate service startup integration
log "Validating service startup integration..."

run_test "Security services in API startup" "grep -q 'threat_detection_service.start_detection_service' app/api/main.py"
run_test "Security services in API shutdown" "grep -q 'threat_detection_service.stop_detection_service' app/api/main.py"
run_test "Security metrics router included" "grep -q 'security_metrics_router' app/api/main.py"

# 6. Validate Grafana dashboard structure
log "Validating Grafana dashboard structure..."

run_test "Security overview dashboard" "test -f config/grafana/provisioning/dashboards/security/security-overview.json"
run_test "Authentication dashboard" "test -f config/grafana/provisioning/dashboards/security/authentication-dashboard.json"
run_test "Threat detection dashboard" "test -f config/grafana/provisioning/dashboards/security/threat-detection-dashboard.json"
run_test "System health dashboard" "test -f config/grafana/provisioning/dashboards/system/system-health-dashboard.json"

# 7. Check AlertManager template and routing
log "Validating AlertManager configuration..."

run_test "AlertManager routing configured" "grep -q 'security-team' config/alertmanager/alertmanager.yml"
run_test "Critical alert routing" "grep -q 'security-critical' config/alertmanager/alertmanager.yml"
run_test "Webhook integration configured" "grep -q 'webhook_configs' config/alertmanager/alertmanager.yml"

# 8. Validate Prometheus rules
log "Validating Prometheus security rules..."

if [[ -f "config/prometheus/security_rules.yml" ]]; then
    run_test "Security rules syntax" "docker run --rm -v $(pwd)/config/prometheus:/config prom/prometheus:latest promtool check rules /config/security_rules.yml"
else
    warning "Security rules file not found, skipping syntax check"
fi

# 9. Test container startup (if Docker is running)
if docker info >/dev/null 2>&1; then
    log "Testing container startup..."
    
    # Test AlertManager container startup
    if run_test "AlertManager container starts" "docker-compose up -d alertmanager && sleep 5 && docker-compose ps alertmanager | grep -q 'Up'"; then
        # Test health endpoint if container is running
        if docker-compose ps alertmanager | grep -q "Up"; then
            run_test "AlertManager health endpoint" "docker-compose exec -T alertmanager wget -q --spider http://localhost:9093/-/healthy"
        fi
        
        # Clean up
        docker-compose down alertmanager >/dev/null 2>&1 || true
    fi
else
    warning "Docker not available, skipping container startup tests"
fi

# 10. API endpoint validation (if API is running)
log "Checking API endpoints..."

if curl -s http://localhost:8000/api/v1/security/health >/dev/null 2>&1; then
    run_test "Security health endpoint accessible" "curl -s http://localhost:8000/api/v1/security/health | grep -q 'overall_status'"
    run_test "Metrics endpoint accessible" "curl -s http://localhost:8000/api/v1/security/metrics | grep -q 'prometheus'"
else
    warning "API not running, skipping endpoint tests"
fi

# Summary
log "Validation Summary:"
log "Tests Run: $TESTS_RUN"
success "Tests Passed: $TESTS_PASSED"
if [[ $TESTS_FAILED -gt 0 ]]; then
    error "Tests Failed: $TESTS_FAILED"
else
    success "Tests Failed: $TESTS_FAILED"
fi

echo ""
if [[ $TESTS_FAILED -eq 0 ]]; then
    success "🎉 All security monitoring infrastructure validation tests passed!"
    log "Your security monitoring system is ready for deployment."
    echo ""
    log "Next steps:"
    log "1. Deploy with: docker-compose up -d"
    log "2. Access Grafana at: http://localhost:3000"
    log "3. Access AlertManager at: http://localhost:9093"
    log "4. Check metrics at: http://localhost:8000/api/v1/security/metrics"
    echo ""
else
    error "❌ Some validation tests failed. Please review the errors above before deployment."
    exit 1
fi

log "Security monitoring validation completed successfully!"