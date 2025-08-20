#!/bin/bash

# =============================================================================
# AIWFE CONSOLIDATED MONITORING STACK VALIDATION
# Comprehensive validation script for monitoring optimization
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Validation results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# Test result arrays
declare -a PASSED_RESULTS=()
declare -a FAILED_RESULTS=()
declare -a WARNING_RESULTS=()

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    PASSED_RESULTS+=("✓ $1")
    ((PASSED_TESTS++))
}

failure() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    FAILED_RESULTS+=("✗ $1")
    ((FAILED_TESTS++))
}

warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    WARNING_RESULTS+=("⚠ $1")
    ((WARNING_TESTS++))
}

test_start() {
    ((TOTAL_TESTS++))
    log "Running test: $1"
}

# =============================================================================
# INFRASTRUCTURE HEALTH VALIDATION
# =============================================================================

validate_docker_services() {
    log "===== INFRASTRUCTURE HEALTH VALIDATION ====="
    
    test_start "Docker daemon connectivity"
    if docker ps >/dev/null 2>&1; then
        success "Docker daemon is running and accessible"
    else
        failure "Docker daemon not accessible or not running"
        return 1
    fi
    
    test_start "Monitoring containers health check"
    monitoring_services=("prometheus" "alertmanager" "grafana")
    
    for service in "${monitoring_services[@]}"; do
        container_name="ai_workflow_engine-${service}-1"
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
            # Get container health status
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no_health_check")
            if [ "$health_status" = "healthy" ] || [ "$health_status" = "no_health_check" ]; then
                success "$service container is running and healthy"
            else
                warning "$service container is running but health status: $health_status"
            fi
        else
            failure "$service container is not running"
        fi
    done
}

# =============================================================================
# PROMETHEUS METRICS VALIDATION
# =============================================================================

validate_prometheus_health() {
    log "===== PROMETHEUS METRICS VALIDATION ====="
    
    test_start "Prometheus endpoint accessibility"
    if curl -s http://localhost:9090/-/healthy >/dev/null; then
        success "Prometheus health endpoint is accessible"
    else
        failure "Prometheus health endpoint is not accessible"
        return 1
    fi
    
    test_start "Prometheus configuration reload"
    if curl -s -X POST http://localhost:9090/-/reload | grep -q "success\|OK" || [ $? -eq 0 ]; then
        success "Prometheus configuration is valid and reloadable"
    else
        warning "Prometheus configuration reload returned non-success status"
    fi
    
    test_start "Active target validation"
    targets_response=$(curl -s http://localhost:9090/api/v1/targets)
    if [ $? -eq 0 ]; then
        targets_up=$(echo "$targets_response" | jq '.data.activeTargets | map(select(.health == "up")) | length' 2>/dev/null || echo "0")
        targets_total=$(echo "$targets_response" | jq '.data.activeTargets | length' 2>/dev/null || echo "0")
        
        if [ "$targets_up" -gt 0 ]; then
            success "Prometheus collecting from $targets_up/$targets_total targets"
            
            # Validate specific critical targets
            essential_targets=("prometheus" "node-exporter" "cadvisor" "postgres-exporter" "redis-exporter")
            for target in "${essential_targets[@]}"; do
                target_health=$(echo "$targets_response" | jq -r ".data.activeTargets[] | select(.labels.job == \"$target\") | .health" 2>/dev/null || echo "")
                if [ "$target_health" = "up" ]; then
                    success "Essential target '$target' is healthy"
                else
                    warning "Essential target '$target' is not healthy or missing"
                fi
            done
        else
            failure "No healthy Prometheus targets found"
        fi
    else
        failure "Unable to fetch Prometheus targets"
    fi
    
    test_start "Metrics endpoint validation"
    metrics_endpoints=("http://localhost:9090/metrics")
    for endpoint in "${metrics_endpoints[@]}"; do
        if curl -s "$endpoint" | head -1 | grep -q "^# HELP\|^# TYPE\|^prometheus_"; then
            success "Metrics endpoint returns valid Prometheus metrics: $endpoint"
        else
            failure "Metrics endpoint does not return valid metrics: $endpoint"
        fi
    done
}

# =============================================================================
# NODE EXPORTER AND INFRASTRUCTURE VALIDATION
# =============================================================================

validate_node_exporter() {
    log "===== NODE EXPORTER STATUS VALIDATION ====="
    
    test_start "Node Exporter connectivity"
    if docker ps | grep -q "node_exporter"; then
        success "Node Exporter container is running"
        
        # Check for broken pipe errors in logs
        test_start "Node Exporter error log check"
        error_logs=$(docker logs ai_workflow_engine-node_exporter-1 2>&1 | tail -50 | grep -i "broken pipe\|error\|failed" || echo "")
        if [ -z "$error_logs" ]; then
            success "No broken pipe errors in Node Exporter logs"
        else
            warning "Found potential issues in Node Exporter logs: $(echo "$error_logs" | head -1)"
        fi
    else
        failure "Node Exporter container is not running"
    fi
}

# =============================================================================
# LOG INGESTION VALIDATION
# =============================================================================

validate_log_ingestion() {
    log "===== LOG INGESTION VALIDATION ====="
    
    test_start "Log shipping service status"
    # Check if Promtail or similar log shipper is configured
    if docker ps | grep -q "promtail\|loki\|fluentd"; then
        success "Log shipping service is running"
    else
        warning "No log shipping service detected (Promtail/Loki not running)"
    fi
    
    test_start "Container log accessibility"
    # Test if we can access container logs
    test_containers=("ai_workflow_engine-prometheus-1" "ai_workflow_engine-grafana-1")
    for container in "${test_containers[@]}"; do
        if docker logs "$container" --tail 1 >/dev/null 2>&1; then
            success "Can access logs for $container"
        else
            warning "Cannot access logs for $container"
        fi
    done
}

# =============================================================================
# CONSOLIDATED SERVICES MONITORING
# =============================================================================

validate_consolidated_services() {
    log "===== CONSOLIDATED SERVICES MONITORING ====="
    
    test_start "Kubernetes cluster connectivity"
    if kubectl get nodes >/dev/null 2>&1; then
        success "Kubernetes cluster is accessible"
        
        test_start "AIWFE namespace services"
        if kubectl get services -n aiwfe >/dev/null 2>&1; then
            service_count=$(kubectl get services -n aiwfe --no-headers | wc -l)
            success "Found $service_count services in aiwfe namespace"
            
            # Check specific consolidated services
            consolidated_services=("aiwfe-api-gateway" "aiwfe-webui" "integration-service" "reasoning-service" "metrics-aggregator")
            for service in "${consolidated_services[@]}"; do
                if kubectl get service "$service" -n aiwfe >/dev/null 2>&1; then
                    success "Consolidated service '$service' exists in cluster"
                else
                    warning "Consolidated service '$service' not found in cluster"
                fi
            done
        else
            warning "AIWFE namespace not accessible or doesn't exist"
        fi
    else
        failure "Kubernetes cluster is not accessible"
    fi
}

# =============================================================================
# PRODUCTION ENDPOINT VALIDATION
# =============================================================================

validate_production_endpoints() {
    log "===== PRODUCTION ENDPOINT VALIDATION ====="
    
    test_start "Production domain connectivity"
    if ping -c 2 aiwfe.com >/dev/null 2>&1; then
        success "Production domain aiwfe.com is reachable"
        
        test_start "HTTPS endpoint accessibility"
        https_response=$(curl -s -w "%{http_code}" -o /dev/null https://aiwfe.com --max-time 10 || echo "000")
        if [[ "$https_response" =~ ^[23][0-9][0-9]$ ]]; then
            success "Production HTTPS endpoint is accessible (HTTP $https_response)"
        else
            failure "Production HTTPS endpoint returned HTTP $https_response"
        fi
        
        test_start "Health endpoint validation"
        health_response=$(curl -s -w "%{http_code}" -o /dev/null https://aiwfe.com/health --max-time 10 || echo "000")
        if [[ "$health_response" =~ ^[23][0-9][0-9]$ ]]; then
            success "Production health endpoint is accessible (HTTP $health_response)"
        else
            warning "Production health endpoint returned HTTP $health_response"
        fi
    else
        failure "Production domain aiwfe.com is not reachable"
    fi
}

# =============================================================================
# WEBSOCKET PERFORMANCE VALIDATION
# =============================================================================

validate_websocket_performance() {
    log "===== WEBSOCKET PERFORMANCE VALIDATION ====="
    
    test_start "WebSocket monitoring configuration"
    # Check if WebSocket monitoring is configured in Prometheus
    if curl -s http://localhost:9090/api/v1/targets | grep -q "websocket-performance"; then
        success "WebSocket performance monitoring is configured"
        
        test_start "WebSocket target compliance rate"
        sleep 5  # Wait for potential metrics
        compliance_rate=$(curl -s "http://localhost:9090/api/v1/query?query=websocket:target_compliance_rate" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
        if (( $(echo "$compliance_rate >= 95" | bc -l 2>/dev/null || echo "0") )); then
            success "WebSocket performance target compliance: ${compliance_rate}%"
        elif [ "$compliance_rate" != "0" ]; then
            warning "WebSocket performance target compliance: ${compliance_rate}% (target: >95%)"
        else
            warning "WebSocket performance metrics not yet available"
        fi
    else
        warning "WebSocket performance monitoring not configured"
    fi
}

# =============================================================================
# SSL CERTIFICATE MONITORING VALIDATION
# =============================================================================

validate_ssl_monitoring() {
    log "===== SSL CERTIFICATE MONITORING VALIDATION ====="
    
    test_start "SSL certificate monitoring configuration"
    if curl -s http://localhost:9090/api/v1/targets | grep -q "ssl-certificate-monitoring"; then
        success "SSL certificate monitoring is configured"
        
        test_start "SSL certificate health check"
        # Test SSL certificate for production domain
        if echo | openssl s_client -connect aiwfe.com:443 -servername aiwfe.com 2>/dev/null | openssl x509 -noout -dates >/dev/null 2>&1; then
            expiry_date=$(echo | openssl s_client -connect aiwfe.com:443 -servername aiwfe.com 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
            expiry_timestamp=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
            current_timestamp=$(date +%s)
            days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
            
            if [ "$days_until_expiry" -gt 30 ]; then
                success "SSL certificate is healthy: $days_until_expiry days until expiry"
            elif [ "$days_until_expiry" -gt 0 ]; then
                warning "SSL certificate expires in $days_until_expiry days"
            else
                failure "SSL certificate appears to be expired"
            fi
        else
            warning "Unable to check SSL certificate for aiwfe.com"
        fi
    else
        warning "SSL certificate monitoring not configured"
    fi
}

# =============================================================================
# COST OPTIMIZATION MONITORING VALIDATION
# =============================================================================

validate_cost_optimization() {
    log "===== COST OPTIMIZATION MONITORING VALIDATION ====="
    
    test_start "Cost optimization metrics configuration"
    cost_metrics=("cost:total_daily_savings_usd" "cost:annual_savings_projection_usd" "cost:cpu_efficiency_percentage")
    
    for metric in "${cost_metrics[@]}"; do
        if curl -s "http://localhost:9090/api/v1/query?query=$metric" | jq -e '.data.result | length > 0' >/dev/null 2>&1; then
            success "Cost optimization metric '$metric' is configured"
        else
            warning "Cost optimization metric '$metric' not available yet"
        fi
    done
    
    test_start "$400K savings target tracking"
    annual_savings=$(curl -s "http://localhost:9090/api/v1/query?query=cost:annual_savings_projection_usd" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
    if [ "$annual_savings" != "0" ] && (( $(echo "$annual_savings > 0" | bc -l 2>/dev/null || echo "0") )); then
        if (( $(echo "$annual_savings >= 400000" | bc -l 2>/dev/null || echo "0") )); then
            success "Cost optimization target achieved: \$$(printf '%.0f' "$annual_savings") annual savings"
        else
            warning "Cost optimization progress: \$$(printf '%.0f' "$annual_savings") / \$400,000 target"
        fi
    else
        warning "Cost optimization savings calculation not yet available"
    fi
}

# =============================================================================
# ALERTMANAGER AND NOTIFICATION VALIDATION
# =============================================================================

validate_alertmanager() {
    log "===== ALERTMANAGER AND NOTIFICATION VALIDATION ====="
    
    test_start "AlertManager endpoint accessibility"
    if curl -s http://localhost:9093/-/healthy >/dev/null; then
        success "AlertManager health endpoint is accessible"
        
        test_start "AlertManager configuration validation"
        config_response=$(curl -s http://localhost:9093/api/v1/status)
        if echo "$config_response" | jq -e '.status == "success"' >/dev/null 2>&1; then
            success "AlertManager configuration is valid"
        else
            warning "AlertManager configuration validation unclear"
        fi
        
        test_start "Active alerts check"
        alerts_response=$(curl -s http://localhost:9093/api/v1/alerts)
        active_alerts=$(echo "$alerts_response" | jq '.data | length' 2>/dev/null || echo "0")
        if [ "$active_alerts" -eq 0 ]; then
            success "No active alerts (system is healthy)"
        else
            warning "$active_alerts active alerts found"
        fi
    else
        failure "AlertManager health endpoint is not accessible"
    fi
}

# =============================================================================
# GRAFANA DASHBOARD VALIDATION
# =============================================================================

validate_grafana_dashboards() {
    log "===== GRAFANA DASHBOARD VALIDATION ====="
    
    test_start "Grafana endpoint accessibility"
    if curl -s http://localhost:3000/api/health >/dev/null; then
        success "Grafana health endpoint is accessible"
        
        test_start "Consolidated dashboards validation"
        dashboards=("consolidated-services-overview" "cost-optimization-dashboard" "websocket-ssl-performance")
        
        for dashboard in "${dashboards[@]}"; do
            if [ -f "/home/marku/ai_workflow_engine/config/grafana/dashboards/${dashboard}.json" ]; then
                success "Dashboard file exists: $dashboard"
            else
                warning "Dashboard file missing: $dashboard"
            fi
        done
    else
        failure "Grafana health endpoint is not accessible"
    fi
}

# =============================================================================
# COMPREHENSIVE MONITORING VALIDATION SUMMARY
# =============================================================================

generate_validation_report() {
    log "===== VALIDATION SUMMARY REPORT ====="
    
    echo ""
    echo "======================================================================"
    echo "AIWFE CONSOLIDATED MONITORING VALIDATION REPORT"
    echo "======================================================================"
    echo "Validation Date: $(date)"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Warnings: $WARNING_TESTS"
    echo ""
    
    # Calculate success rate
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$(( PASSED_TESTS * 100 / TOTAL_TESTS ))
        echo "Success Rate: $success_rate%"
    fi
    
    echo ""
    echo "VALIDATION RESULTS:"
    echo "=================="
    
    if [ ${#PASSED_RESULTS[@]} -gt 0 ]; then
        echo ""
        echo "✅ PASSED TESTS:"
        printf '%s\n' "${PASSED_RESULTS[@]}"
    fi
    
    if [ ${#WARNING_RESULTS[@]} -gt 0 ]; then
        echo ""
        echo "⚠️  WARNING TESTS:"
        printf '%s\n' "${WARNING_RESULTS[@]}"
    fi
    
    if [ ${#FAILED_RESULTS[@]} -gt 0 ]; then
        echo ""
        echo "❌ FAILED TESTS:"
        printf '%s\n' "${FAILED_RESULTS[@]}"
    fi
    
    echo ""
    echo "MONITORING STACK STATUS:"
    echo "======================="
    
    if [ $FAILED_TESTS -eq 0 ]; then
        success "✅ MONITORING STACK IS OPERATIONAL"
        echo "   All critical components are functioning correctly."
    elif [ $FAILED_TESTS -le 2 ]; then
        warning "⚠️  MONITORING STACK NEEDS ATTENTION"
        echo "   Minor issues detected, but core functionality is available."
    else
        failure "❌ MONITORING STACK HAS SIGNIFICANT ISSUES"
        echo "   Multiple critical components are not functioning properly."
    fi
    
    echo ""
    echo "NEXT STEPS:"
    echo "==========="
    echo "1. Review any failed or warning tests above"
    echo "2. Access monitoring interfaces:"
    echo "   - Prometheus: http://localhost:9090"
    echo "   - AlertManager: http://localhost:9093"
    echo "   - Grafana: http://localhost:3000"
    echo "3. Monitor production endpoints and WebSocket performance"
    echo "4. Track cost optimization progress toward \$400K target"
    echo "5. Ensure SSL certificates are monitored and renewed"
    echo ""
    echo "======================================================================"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    log "Starting AIWFE Consolidated Monitoring Stack Validation"
    log "======================================================="
    echo ""
    
    # Execute all validation tests
    validate_docker_services
    echo ""
    validate_prometheus_health
    echo ""
    validate_node_exporter
    echo ""
    validate_log_ingestion
    echo ""
    validate_consolidated_services
    echo ""
    validate_production_endpoints
    echo ""
    validate_websocket_performance
    echo ""
    validate_ssl_monitoring
    echo ""
    validate_cost_optimization
    echo ""
    validate_alertmanager
    echo ""
    validate_grafana_dashboards
    echo ""
    
    # Generate comprehensive report
    generate_validation_report
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Execute main function
main "$@"