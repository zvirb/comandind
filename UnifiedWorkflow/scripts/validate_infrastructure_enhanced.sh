#!/bin/bash

# Enhanced AIWFE Infrastructure Validation Script
# Comprehensive validation including PYTHONPATH, imports, and health checks

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# Test result tracking
declare -a FAILED_TEST_NAMES
declare -a WARNING_TEST_NAMES

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2
    local allow_warning=${3:-false}
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "  $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        if [ "$allow_warning" = "true" ]; then
            echo -e "${YELLOW}⚠ WARNING${NC}"
            WARNING_TESTS=$((WARNING_TESTS + 1))
            WARNING_TEST_NAMES+=("$test_name")
            return 1
        else
            echo -e "${RED}✗ FAILED${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            FAILED_TEST_NAMES+=("$test_name")
            return 1
        fi
    fi
}

# Function to check service health with details
check_service_health_detailed() {
    local service_name=$1
    local port=$2
    
    echo -e "\n  ${CYAN}$service_name:${NC}"
    
    # Check container status
    echo -n "    Container: "
    if docker compose ps $service_name 2>/dev/null | grep -q "Up"; then
        if docker compose ps $service_name 2>/dev/null | grep -q "healthy"; then
            echo -e "${GREEN}UP (healthy)${NC}"
        else
            echo -e "${YELLOW}UP (no health check)${NC}"
        fi
    else
        echo -e "${RED}DOWN${NC}"
        return 1
    fi
    
    # Check PYTHONPATH
    echo -n "    PYTHONPATH: "
    pythonpath=$(docker compose exec -T $service_name env 2>/dev/null | grep PYTHONPATH | cut -d= -f2 || echo "")
    if [[ "$pythonpath" == *"/app/shared"* ]]; then
        echo -e "${GREEN}Configured${NC}"
    else
        echo -e "${RED}Missing /app/shared${NC}"
    fi
    
    # Check health endpoint
    echo -n "    Health endpoint: "
    mapped_port=$(docker compose port $service_name $port 2>/dev/null | cut -d: -f2 || echo "")
    if [ -n "$mapped_port" ]; then
        response=$(curl -s http://localhost:$mapped_port/health 2>/dev/null || echo "{}")
        status=$(echo $response | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "error")
        
        if [ "$status" = "healthy" ]; then
            echo -e "${GREEN}Healthy${NC}"
        elif [ "$status" = "degraded" ]; then
            echo -e "${YELLOW}Degraded${NC}"
        else
            echo -e "${RED}Unhealthy${NC}"
        fi
        
        # Check for import errors
        import_status=$(echo $response | python3 -c "import sys, json; d=json.load(sys.stdin); c=d.get('checks',{}); i=c.get('imports',{}); print('ok' if i.get('all_imports_ok', False) else 'failed')" 2>/dev/null || echo "unknown")
        if [ "$import_status" = "ok" ]; then
            echo -e "    Imports: ${GREEN}All OK${NC}"
        elif [ "$import_status" = "failed" ]; then
            echo -e "    Imports: ${RED}Failed${NC}"
        fi
    else
        echo -e "${YELLOW}Port not mapped${NC}"
    fi
}

echo "================================================"
echo "Enhanced AIWFE Infrastructure Validation"
echo "================================================"
echo ""

# 1. Docker Environment
echo -e "${BLUE}1. Docker Environment${NC}"
run_test "Docker installed" "docker --version"
run_test "Docker Compose installed" "docker compose version"
run_test "Docker daemon running" "docker ps"
echo ""

# 2. Core Services Status
echo -e "${BLUE}2. Core Services Status${NC}"
run_test "API container running" "docker compose ps api | grep -q Up"
run_test "Worker container running" "docker compose ps worker | grep -q Up"
run_test "PostgreSQL running" "docker compose ps postgres | grep -q Up"
run_test "Redis running" "docker compose ps redis | grep -q Up"
run_test "Qdrant running" "docker compose ps qdrant | grep -q Up"
echo ""

# 3. Cognitive Services Status
echo -e "${BLUE}3. Cognitive Services Status${NC}"
run_test "Perception Service" "docker compose ps perception-service 2>/dev/null | grep -q Up" true
run_test "Memory Service" "docker compose ps memory-service 2>/dev/null | grep -q Up" true
run_test "Reasoning Service" "docker compose ps reasoning-service 2>/dev/null | grep -q Up" true
run_test "Coordination Service" "docker compose ps coordination-service 2>/dev/null | grep -q Up" true
run_test "Learning Service" "docker compose ps learning-service 2>/dev/null | grep -q Up" true
echo ""

# 4. PYTHONPATH Configuration
echo -e "${BLUE}4. PYTHONPATH Configuration${NC}"
for service in api worker; do
    if docker compose ps $service 2>/dev/null | grep -q "Up"; then
        run_test "$service PYTHONPATH" "docker compose exec -T $service env | grep -q 'PYTHONPATH.*shared'"
    fi
done
echo ""

# 5. Import Validation
echo -e "${BLUE}5. Import Validation${NC}"
for service in api worker; do
    if docker compose ps $service 2>/dev/null | grep -q "Up"; then
        run_test "$service shared imports" "docker compose exec -T $service python -c 'from shared.utils import get_logger'"
    fi
done
echo ""

# 6. Health Endpoints
echo -e "${BLUE}6. Service Health Endpoints${NC}"
run_test "API health check" "curl -sf http://localhost:8000/health"
run_test "API metrics endpoint" "curl -sf http://localhost:8000/metrics"
echo ""

# 7. Database Connectivity
echo -e "${BLUE}7. Database Connectivity${NC}"
run_test "PostgreSQL responding" "docker compose exec -T postgres pg_isready -U postgres"
run_test "Redis responding" "docker compose exec -T redis redis-cli ping | grep -q PONG"
run_test "Qdrant responding" "curl -sf http://localhost:6333/"
echo ""

# 8. Network Connectivity
echo -e "${BLUE}8. Network Connectivity${NC}"
run_test "Internal network exists" "docker network ls | grep -q ai_workflow_engine"
run_test "Caddy reverse proxy" "docker compose ps caddy_reverse_proxy 2>/dev/null | grep -q Up" true
echo ""

# 9. Monitoring Stack
echo -e "${BLUE}9. Monitoring Stack${NC}"
run_test "Prometheus running" "docker compose ps prometheus 2>/dev/null | grep -q Up" true
run_test "Grafana running" "docker compose ps grafana 2>/dev/null | grep -q Up" true
run_test "Loki running" "docker compose ps loki 2>/dev/null | grep -q Up" true
echo ""

# 10. External Access
echo -e "${BLUE}10. External Access${NC}"
run_test "HTTP redirect (aiwfe.com)" "curl -sI http://aiwfe.com | grep -q '30[1-3]'" true
run_test "HTTPS access (aiwfe.com)" "curl -sf https://aiwfe.com >/dev/null" true
echo ""

# 11. Log Analysis
echo -e "${BLUE}11. Recent Log Analysis (5 min)${NC}"
echo -n "  Checking for import errors... "
import_errors=$(docker compose logs --since 5m 2>&1 | grep -i "importerror\|no module named" | wc -l || echo 0)
if [ "$import_errors" -eq 0 ]; then
    echo -e "${GREEN}None found${NC}"
else
    echo -e "${RED}$import_errors errors found${NC}"
    echo "  Recent import errors:"
    docker compose logs --since 5m 2>&1 | grep -i "importerror\|no module named" | head -3 | sed 's/^/    /'
fi
echo ""

# 12. Detailed Service Health
echo -e "${BLUE}12. Detailed Service Health${NC}"
check_service_health_detailed "api" 8000
check_service_health_detailed "perception-service" 8001
check_service_health_detailed "memory-service" 8002
check_service_health_detailed "reasoning-service" 8003
echo ""

# Summary
echo "================================================"
echo -e "${BLUE}Validation Summary${NC}"
echo "================================================"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Warnings: ${YELLOW}$WARNING_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ ${#FAILED_TEST_NAMES[@]} -gt 0 ]; then
    echo -e "${RED}Failed Tests:${NC}"
    for test in "${FAILED_TEST_NAMES[@]}"; do
        echo "  - $test"
    done
    echo ""
fi

if [ ${#WARNING_TEST_NAMES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Warning Tests:${NC}"
    for test in "${WARNING_TEST_NAMES[@]}"; do
        echo "  - $test"
    done
    echo ""
fi

# Overall status
if [ $FAILED_TESTS -eq 0 ]; then
    if [ $WARNING_TESTS -eq 0 ]; then
        echo -e "${GREEN}✓ Infrastructure is fully operational${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Infrastructure is operational with warnings${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Infrastructure has critical issues${NC}"
    echo ""
    echo "Recommended actions:"
    echo "1. Check failed services: docker compose ps"
    echo "2. Review logs: docker compose logs --tail=50 [service-name]"
    echo "3. Rebuild if needed: docker compose build [service-name]"
    echo "4. Restart services: docker compose restart [service-name]"
    echo "5. Check PYTHONPATH in Dockerfiles"
    exit 1
fi