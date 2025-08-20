#!/bin/bash

# Circuit Breaker Authentication Flow Validation Script
# Tests the complete authentication flow with circuit breaker protection

BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3001"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}🧪 Testing: ${test_name}${NC}"
    
    # Execute the test command
    local result=$(eval "$test_command" 2>&1)
    local exit_code=$?
    
    # Check if test passed
    if [ $exit_code -eq 0 ] && echo "$result" | grep -q "$expected_pattern"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✅ PASSED: ${test_name}${NC}"
        return 0
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}❌ FAILED: ${test_name}${NC}"
        echo -e "${RED}   Command: ${test_command}${NC}"
        echo -e "${RED}   Result: ${result}${NC}"
        return 1
    fi
}

# Function to run JSON test
run_json_test() {
    local test_name="$1"
    local test_command="$2"
    local json_field="$3"
    local expected_value="$4"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "\n${BLUE}🧪 Testing: ${test_name}${NC}"
    
    # Execute the test command and extract JSON field
    local result=$(eval "$test_command" 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        local field_value=$(echo "$result" | jq -r "$json_field" 2>/dev/null)
        
        if [ "$field_value" = "$expected_value" ]; then
            PASSED_TESTS=$((PASSED_TESTS + 1))
            echo -e "${GREEN}✅ PASSED: ${test_name}${NC}"
            echo -e "${GREEN}   Expected: ${expected_value}, Got: ${field_value}${NC}"
            return 0
        else
            FAILED_TESTS=$((FAILED_TESTS + 1))
            echo -e "${RED}❌ FAILED: ${test_name}${NC}"
            echo -e "${RED}   Expected: ${expected_value}, Got: ${field_value}${NC}"
            return 1
        fi
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}❌ FAILED: ${test_name} (Command failed)${NC}"
        echo -e "${RED}   Result: ${result}${NC}"
        return 1
    fi
}

echo -e "${BLUE}🚀 Starting Circuit Breaker Authentication Flow Tests${NC}\n"

# Test 1: Circuit Breaker Status Check
run_json_test \
    "Circuit Breaker Status Check" \
    "curl -s '${BASE_URL}/api/v1/auth-circuit-breaker/status'" \
    ".circuit_breaker.state" \
    "closed"

# Test 2: Session Validation Still Works
run_json_test \
    "Session Validation Still Works" \
    "curl -s -X POST '${BASE_URL}/api/v1/session/validate' -H 'Content-Type: application/json'" \
    ".valid" \
    "false"

# Test 3: WebGL Context Lost Event Processing
run_json_test \
    "WebGL Context Lost Event Processing" \
    "curl -s -X POST '${BASE_URL}/api/v1/auth-circuit-breaker/notifications/webgl-context-lost' -H 'Content-Type: application/json' -d '{\"event_type\": \"context_lost\", \"additional_info\": \"Test event\"}'" \
    ".status" \
    "success"

# Test 4: Performance Issue Handling
run_json_test \
    "Performance Issue Handling" \
    "curl -s -X POST '${BASE_URL}/api/v1/auth-circuit-breaker/notifications/performance-issue' -H 'Content-Type: application/json' -d '{\"issue_type\": \"auth_flooding\", \"severity\": \"medium\", \"pause_duration\": 3}'" \
    ".status" \
    "success"

# Test 5: Check Performance Pause is Active
run_json_test \
    "Performance Pause Active After Events" \
    "curl -s '${BASE_URL}/api/v1/auth-circuit-breaker/status'" \
    ".circuit_breaker.is_performance_paused" \
    "true"

# Test 6: Circuit Breaker Reset
run_json_test \
    "Circuit Breaker Reset" \
    "curl -s -X POST '${BASE_URL}/api/v1/auth-circuit-breaker/reset'" \
    ".status" \
    "success"

# Test 7: Performance Pause Cleared After Reset
run_json_test \
    "Performance Pause Cleared After Reset" \
    "curl -s '${BASE_URL}/api/v1/auth-circuit-breaker/status'" \
    ".circuit_breaker.is_performance_paused" \
    "false"

# Test 8: Circuit Breaker Health Check
run_json_test \
    "Circuit Breaker Health Check" \
    "curl -s '${BASE_URL}/api/v1/auth-circuit-breaker/health'" \
    ".status" \
    "healthy"

# Test 9: Frontend Proxy Access
run_json_test \
    "Frontend Proxy Access to Circuit Breaker" \
    "curl -s '${FRONTEND_URL}/api/v1/auth-circuit-breaker/status'" \
    ".circuit_breaker.state" \
    "closed"

# Test 10: Multiple Auth Attempts (No Flooding)
echo -e "\n${BLUE}🧪 Testing: Multiple Auth Attempts (No Flooding)${NC}"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

auth_success_count=0
for i in {1..5}; do
    response=$(curl -s -w "%{http_code}" -X POST "${BASE_URL}/api/v1/session/validate" -H "Content-Type: application/json")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        auth_success_count=$((auth_success_count + 1))
    fi
    
    sleep 0.1  # Small delay between attempts
done

if [ $auth_success_count -eq 5 ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "${GREEN}✅ PASSED: Multiple Auth Attempts (${auth_success_count}/5 successful)${NC}"
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "${RED}❌ FAILED: Multiple Auth Attempts (${auth_success_count}/5 successful)${NC}"
fi

# Print Summary
echo -e "\n${YELLOW}📊 TEST SUMMARY${NC}"
echo "================"
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}✅ Passed: $PASSED_TESTS${NC}"
echo -e "${RED}❌ Failed: $FAILED_TESTS${NC}"

# Calculate success rate
if [ $TOTAL_TESTS -gt 0 ]; then
    success_rate=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)
    echo "Success Rate: ${success_rate}%"
fi

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL TESTS PASSED! Circuit Breaker Authentication Flow is working correctly.${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  Some tests failed. Please review the issues above.${NC}"
    exit 1
fi