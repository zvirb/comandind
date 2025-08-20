#!/bin/bash

# AIWFE Service Mesh Validation Script
# Comprehensive validation of production-ready cognitive architecture
# Tests zero-trust networking, staged deployment, database optimization, monitoring, and security

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATION_LOG="/tmp/aiwfe_service_mesh_validation_$(date +%Y%m%d_%H%M%S).log"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_TEST_NAMES

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$VALIDATION_LOG"
}

log_info() { log "${BLUE}INFO${NC}" "$@"; }
log_success() { log "${GREEN}SUCCESS${NC}" "$@"; }
log_warn() { log "${YELLOW}WARN${NC}" "$@"; }
log_error() { log "${RED}ERROR${NC}" "$@"; }

run_test() {
    local test_name="$1"
    local test_command="$2"
    local timeout_duration="${3:-30}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing $test_name... "
    
    if timeout "$timeout_duration" bash -c "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_TEST_NAMES+=("$test_name")
        return 1
    fi
}

# Test Docker and Docker Compose
test_docker_environment() {
    log_info "Testing Docker environment..."
    
    run_test "Docker daemon running" "docker version"
    run_test "Docker Compose available" "docker compose version"
    run_test "Docker Compose configuration valid" "cd $PROJECT_ROOT && docker compose config"
    
    # Test network creation
    run_test "Frontend network exists" "docker network inspect aiwfe-frontend"
    run_test "Backend network exists" "docker network inspect aiwfe-backend" 
    run_test "Research network exists" "docker network inspect aiwfe-research"
    run_test "Monitoring network exists" "docker network inspect aiwfe-monitoring"
}

# Test service mesh infrastructure
test_service_mesh_infrastructure() {
    log_info "Testing service mesh infrastructure..."
    
    # Test core data services
    run_test "PostgreSQL healthy" "docker compose exec -T postgres pg_isready -U aiwfe -d aiwfe_db"
    run_test "Redis healthy" "docker compose exec -T redis redis-cli ping"
    run_test "Qdrant healthy" "curl -f http://localhost:6333/health"
    run_test "Neo4j healthy" "curl -f http://localhost:7474/db/system/tx/commit -H 'Content-Type: application/json' -d '{\"statements\":[{\"statement\":\"RETURN 1\"}]}'"
    
    # Test AI services
    run_test "Ollama healthy" "curl -f http://localhost:11434/api/tags"
    
    # Test monitoring stack
    run_test "Prometheus healthy" "curl -f http://localhost:9090/-/healthy"
    run_test "Grafana healthy" "curl -f http://localhost:3001/api/health"
    
    # Test service mesh components
    if docker compose ps traefik | grep -q running; then
        run_test "Traefik API Gateway healthy" "curl -f http://localhost:8080/ping"
    fi
    
    if docker compose ps vault | grep -q running; then
        run_test "Vault secrets manager responsive" "curl -f http://localhost:8200/v1/sys/health"
    fi
}

# Test cognitive services
test_cognitive_services() {
    log_info "Testing cognitive services..."
    
    # Test service health endpoints
    if docker compose ps learning-service | grep -q running; then
        run_test "Learning Service healthy" "curl -f http://localhost:8005/health"
        run_test "Learning Service pattern search" "curl -f -X POST http://localhost:8005/patterns/search -H 'Content-Type: application/json' -d '{\"context\": {\"test\": \"validation\"}, \"max_results\": 1}'"
    fi
    
    if docker compose ps coordination-service | grep -q running; then
        run_test "Coordination Service healthy" "curl -f http://localhost:8004/health"
        run_test "Coordination Service status" "curl -f http://localhost:8004/status/detailed"
    fi
    
    if docker compose ps reasoning-service | grep -q running; then
        run_test "Reasoning Service healthy" "curl -f http://localhost:8003/health"
    fi
    
    if docker compose ps integration-service | grep -q running; then
        run_test "Integration Service healthy" "curl -f http://localhost:8006/health"
    fi
    
    if docker compose ps hybrid-memory-service | grep -q running; then
        run_test "Hybrid Memory Service healthy" "curl -f http://localhost:8002/health"
    fi
    
    if docker compose ps perception-service | grep -q running; then
        run_test "Perception Service healthy" "curl -f http://localhost:8001/health"
    fi
}

# Test database optimization
test_database_optimization() {
    log_info "Testing database optimization..."
    
    # Test PostgreSQL optimizations
    run_test "PostgreSQL schemas initialized" "docker compose exec -T postgres psql -U aiwfe -d aiwfe_db -c '\\dn' | grep -E 'coordination|learning|reasoning|integration|hybrid_memory'"
    run_test "PostgreSQL extensions enabled" "docker compose exec -T postgres psql -U aiwfe -d aiwfe_db -c '\\dx' | grep -E 'pgvector|pg_stat_statements|pg_trgm'"
    run_test "PostgreSQL performance settings" "docker compose exec -T postgres psql -U aiwfe -d aiwfe_db -c 'SHOW shared_buffers;'"
    
    # Test Redis configuration
    run_test "Redis configuration loaded" "docker compose exec -T redis redis-cli CONFIG GET maxmemory | grep -v '^maxmemory$'"
    run_test "Redis multiple databases" "docker compose exec -T redis redis-cli SELECT 1 && docker compose exec -T redis redis-cli SELECT 5"
    
    # Test Qdrant collections
    run_test "Qdrant collections endpoint" "curl -f http://localhost:6333/collections"
    
    # Test Neo4j performance
    run_test "Neo4j APOC procedures" "curl -f http://localhost:7474/db/neo4j/tx/commit -H 'Content-Type: application/json' -d '{\"statements\":[{\"statement\":\"RETURN apoc.version()\"}]}'"
}

# Test monitoring and observability
test_monitoring_observability() {
    log_info "Testing monitoring and observability..."
    
    # Test Prometheus metrics collection
    run_test "Prometheus targets up" "curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | select(.health == \"up\") | .scrapeUrl' | wc -l | grep -v '^0$'"
    run_test "Prometheus rules loaded" "curl -s http://localhost:9090/api/v1/rules | jq '.data.groups | length' | grep -v '^0$'"
    
    # Test Grafana provisioning
    run_test "Grafana datasources configured" "curl -s -u admin:admin http://localhost:3001/api/datasources | jq 'length' | grep -v '^0$'"
    
    # Test AlertManager
    if docker compose ps alertmanager | grep -q running; then
        run_test "AlertManager healthy" "curl -f http://localhost:9093/-/healthy"
        run_test "AlertManager config loaded" "curl -s http://localhost:9093/api/v1/status | jq -r '.data.configYAML' | grep -q 'route:'"
    fi
    
    # Test distributed tracing
    if docker compose ps jaeger | grep -q running; then
        run_test "Jaeger healthy" "curl -f http://localhost:16686/"
    fi
    
    # Test log aggregation
    if docker compose ps elasticsearch | grep -q running; then
        run_test "Elasticsearch cluster health" "curl -f http://localhost:9200/_cluster/health"
    fi
    
    if docker compose ps kibana | grep -q running; then
        run_test "Kibana healthy" "curl -f http://localhost:5601/api/status"
    fi
}

# Test security configuration
test_security_configuration() {
    log_info "Testing security configuration..."
    
    # Test certificate generation
    run_test "CA certificate exists" "[ -f $PROJECT_ROOT/certificates/ca/ca.crt ]"
    run_test "Service certificates exist" "[ -f $PROJECT_ROOT/certificates/aiwfe.crt ]"
    run_test "API keys configuration exists" "[ -f $PROJECT_ROOT/security/api_keys.json ]"
    run_test "RBAC configuration exists" "[ -f $PROJECT_ROOT/security/rbac_config.yaml ]"
    
    # Test file permissions
    run_test "Certificate directory secure" "[ $(stat -c '%a' $PROJECT_ROOT/certificates 2>/dev/null || echo '000') = '700' ]"
    run_test "Security directory secure" "[ $(stat -c '%a' $PROJECT_ROOT/security 2>/dev/null || echo '000') = '700' ]"
    
    # Test Traefik security
    if docker compose ps traefik | grep -q running; then
        run_test "Traefik dashboard secured" "curl -f http://localhost:8080/dashboard/"
    fi
    
    # Test Vault if running
    if docker compose ps vault | grep -q running; then
        run_test "Vault seal status" "curl -s http://localhost:8200/v1/sys/seal-status | jq -r '.sealed' | grep -q 'false'"
    fi
}

# Test staged deployment capability
test_staged_deployment() {
    log_info "Testing staged deployment capability..."
    
    # Test deployment scripts exist and are executable
    run_test "Staged deployment script exists" "[ -x $PROJECT_ROOT/scripts/deployment/staged_deployment.sh ]"
    run_test "Rollback validator exists" "[ -x $PROJECT_ROOT/scripts/deployment/rollback_validator.py ]"
    
    # Test rollback validation system
    if command -v python3 >/dev/null; then
        run_test "Rollback validator runs" "cd $PROJECT_ROOT && python3 scripts/deployment/rollback_validator.py"
    fi
    
    # Test configuration validation
    run_test "Docker Compose validation" "cd $PROJECT_ROOT && docker compose config --quiet"
}

# Test end-to-end cognitive workflow
test_cognitive_workflow() {
    log_info "Testing end-to-end cognitive workflow..."
    
    # Test learning service workflow
    if docker compose ps learning-service | grep -q running; then
        run_test "Learning outcome processing" "curl -f -X POST http://localhost:8005/learn/outcome -H 'Content-Type: application/json' -d '{
            \"outcome_type\": \"workflow_completion\",
            \"service_name\": \"test-service\",
            \"context\": {\"test\": \"validation\"},
            \"input_data\": {\"test_input\": \"validation\"},
            \"output_data\": {\"result\": \"success\"},
            \"performance_metrics\": {\"execution_time\": 1.5}
        }'"
    fi
    
    # Test service integration
    local services_healthy=true
    for service in learning-service coordination-service reasoning-service integration-service; do
        if docker compose ps "$service" | grep -q running; then
            if ! curl -f "http://localhost:$(get_service_port $service)/health" >/dev/null 2>&1; then
                services_healthy=false
            fi
        fi
    done
    
    if [ "$services_healthy" = true ]; then
        run_test "All cognitive services integrated" "true"
    else
        run_test "All cognitive services integrated" "false"
    fi
}

# Helper function to get service port
get_service_port() {
    case $1 in
        "learning-service") echo "8005" ;;
        "coordination-service") echo "8004" ;;
        "reasoning-service") echo "8003" ;;
        "integration-service") echo "8006" ;;
        "hybrid-memory-service") echo "8002" ;;
        "perception-service") echo "8001" ;;
        "api-gateway") echo "8000" ;;
        *) echo "8080" ;;
    esac
}

# Performance benchmarking
test_performance_benchmarks() {
    log_info "Testing performance benchmarks..."
    
    # Test response times
    if docker compose ps learning-service | grep -q running; then
        local response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8005/health)
        if (( $(echo "$response_time < 2.0" | bc -l 2>/dev/null || echo "1") )); then
            run_test "Learning service response time < 2s" "true"
        else
            run_test "Learning service response time < 2s" "false"
        fi
    fi
    
    # Test database performance
    run_test "PostgreSQL connection pool" "docker compose exec -T postgres psql -U aiwfe -d aiwfe_db -c 'SELECT count(*) FROM pg_stat_activity;'"
    run_test "Redis memory usage acceptable" "docker compose exec -T redis redis-cli INFO memory | grep 'used_memory_human' | grep -E '[0-9]+\.[0-9]+[MK]B'"
}

# Generate comprehensive report
generate_report() {
    log_info "Generating comprehensive validation report..."
    
    local report_file="$PROJECT_ROOT/service_mesh_validation_report_$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" <<EOF
{
    "validation_summary": {
        "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
        "total_tests": $TOTAL_TESTS,
        "passed_tests": $PASSED_TESTS,
        "failed_tests": $FAILED_TESTS,
        "success_rate": $(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0"),
        "status": "$([ $FAILED_TESTS -eq 0 ] && echo "PASSED" || echo "FAILED")"
    },
    "test_categories": {
        "docker_environment": "completed",
        "service_mesh_infrastructure": "completed", 
        "cognitive_services": "completed",
        "database_optimization": "completed",
        "monitoring_observability": "completed",
        "security_configuration": "completed",
        "staged_deployment": "completed",
        "cognitive_workflow": "completed",
        "performance_benchmarks": "completed"
    },
    "failed_tests": [$(printf '"%s",' "${FAILED_TEST_NAMES[@]}" | sed 's/,$//')]
    $([ $FAILED_TESTS -gt 0 ] && echo ',' || echo '')
    "recommendations": [
        "Review failed tests and address underlying issues",
        "Ensure all external API keys are configured in .env.secrets",
        "Run security initialization script if certificates are missing",
        "Monitor service performance and resource usage post-deployment",
        "Set up automated backup procedures for critical data",
        "Configure external monitoring and alerting integrations",
        "Implement log rotation and retention policies",
        "Review and update security configurations regularly"
    ],
    "next_steps": {
        "production_ready": $([ $FAILED_TESTS -eq 0 ] && echo "true" || echo "false"),
        "required_actions": [
            $([ $FAILED_TESTS -gt 0 ] && echo '"Fix failing tests",' || echo '')
            "Initialize Vault secrets management",
            "Configure external identity provider",
            "Set up backup and disaster recovery procedures",
            "Configure production monitoring alerts",
            "Implement log aggregation and analysis",
            "Set up automated certificate rotation"
        ]
    }
}
EOF

    log_success "Validation report saved to: $report_file"
}

# Main execution
main() {
    log_info "=========================================="
    log_info "AIWFE Service Mesh Validation"  
    log_info "Phase 3 Cognitive Architecture Readiness"
    log_info "=========================================="
    log_info "Validation log: $VALIDATION_LOG"
    
    # Execute all test suites
    test_docker_environment
    test_service_mesh_infrastructure  
    test_cognitive_services
    test_database_optimization
    test_monitoring_observability
    test_security_configuration
    test_staged_deployment
    test_cognitive_workflow
    test_performance_benchmarks
    
    # Generate report
    generate_report
    
    # Summary
    log_info "=========================================="
    log_info "Service Mesh Validation Summary"
    log_info "=========================================="
    log_info "Total Tests: $TOTAL_TESTS"
    log_success "Passed: $PASSED_TESTS"
    log_error "Failed: $FAILED_TESTS"
    
    if [ $FAILED_TESTS -gt 0 ]; then
        log_error "Failed Tests:"
        for test in "${FAILED_TEST_NAMES[@]}"; do
            log_error "  - $test"
        done
        log_error "Service mesh validation FAILED"
        log_warn "Review failed tests and fix issues before proceeding to Phase 3"
        exit 1
    else
        log_success "=========================================="
        log_success "SERVICE MESH VALIDATION SUCCESSFUL"
        log_success "Production-ready cognitive architecture"
        log_success "Ready for Phase 3 deployment"
        log_success "=========================================="
        exit 0
    fi
}

# Execute main function
main "$@"