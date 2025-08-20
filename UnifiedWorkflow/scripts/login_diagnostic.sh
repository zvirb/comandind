#!/bin/bash

# Authentication Diagnostic Script
# Comprehensive login flow investigation and validation

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TEST_EMAIL="${TEST_EMAIL:-test@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-temporarypassword}"
BASE_URL="${BASE_URL:-http://localhost:8000}"

# Logging function
log() {
    echo -e "${YELLOW}[LOGIN DIAGNOSTIC]${NC} $1"
}

# Error handling function
handle_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Validate required tools
validate_tools() {
    for tool in curl jq; do
        if ! command -v $tool &> /dev/null; then
            handle_error "$tool is not installed"
        fi
    done
}

# Test token generation
test_token_generation() {
    log "Testing Token Generation..."
    
    token_response=$(curl -s -X POST "${BASE_URL}/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${TEST_EMAIL}" \
        -d "password=${TEST_PASSWORD}")
    
    access_token=$(echo "$token_response" | jq -r '.access_token // empty')
    
    if [ -z "$access_token" ]; then
        handle_error "Token generation failed. Response: $token_response"
    fi
    
    echo -e "${GREEN}✓ Token Generated Successfully${NC}"
    echo "Access Token: ${access_token:0:20}..."  # Partially mask token
}

# Test authentication middleware
test_auth_middleware() {
    log "Testing Authentication Middleware..."
    
    # Attempt to access a protected endpoint
    protected_response=$(curl -s -X GET "${BASE_URL}/protected-endpoint" \
        -H "Authorization: Bearer $access_token")
    
    # Add specific checks based on your application's middleware
    if [[ "$protected_response" == *"Unauthorized"* ]]; then
        handle_error "Authentication middleware blocked request"
    fi
    
    echo -e "${GREEN}✓ Authentication Middleware Validated${NC}"
}

# Main diagnostic flow
main() {
    validate_tools
    test_token_generation
    test_auth_middleware
    
    log "Authentication Diagnostic Complete"
}

# Execute main function
main