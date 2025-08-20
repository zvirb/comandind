#!/bin/bash
# Redis Health Monitoring Script
# Checks Redis connectivity and alerts on failures

set -e

# Configuration
REDIS_CONTAINER="ai_workflow_engine-redis-1"
API_CONTAINER="ai_workflow_engine-api-1"
NETWORK_NAME="ai_workflow_engine_ai_workflow_engine_net"
HEALTH_ENDPOINT="https://aiwfe.com/api/v1/health"
LOG_FILE="${LOG_FILE:-/tmp/redis_health_monitor.log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if Redis container is running
check_redis_container() {
    if docker ps --format "table {{.Names}}" | grep -q "$REDIS_CONTAINER"; then
        echo -e "${GREEN}✓${NC} Redis container is running"
        return 0
    else
        echo -e "${RED}✗${NC} Redis container is not running"
        log_message "ERROR: Redis container not running"
        return 1
    fi
}

# Check Redis network connectivity
check_redis_network() {
    REDIS_NETWORK=$(docker inspect "$REDIS_CONTAINER" --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}' 2>/dev/null || echo "")
    API_NETWORK=$(docker inspect "$API_CONTAINER" --format='{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}' 2>/dev/null || echo "")
    
    if [ "$REDIS_NETWORK" = "$API_NETWORK" ]; then
        echo -e "${GREEN}✓${NC} Redis and API are on the same network"
        return 0
    else
        echo -e "${RED}✗${NC} Network mismatch detected!"
        log_message "ERROR: Redis and API on different networks"
        echo "  Redis network: $REDIS_NETWORK"
        echo "  API network: $API_NETWORK"
        
        # Attempt to fix
        echo -e "${YELLOW}⚠${NC} Attempting to fix network configuration..."
        docker network connect "$NETWORK_NAME" "$REDIS_CONTAINER" 2>/dev/null || true
        log_message "INFO: Attempted network fix"
        return 1
    fi
}

# Check Redis ACL configuration
check_redis_acl() {
    # Use authenticated connection to check ACL
    ACL_CHECK=$(docker exec "$REDIS_CONTAINER" sh -c 'redis-cli -u redis://lwe-app:$(cat /run/secrets/REDIS_PASSWORD)@localhost:6379 ping 2>/dev/null' || echo "FAIL")
    
    if [ "$ACL_CHECK" = "PONG" ]; then
        echo -e "${GREEN}✓${NC} Redis ACL properly configured"
        return 0
    else
        echo -e "${RED}✗${NC} Redis ACL not configured"
        log_message "ERROR: Redis ACL misconfigured"
        return 1
    fi
}

# Check API health endpoint
check_api_health() {
    HEALTH_RESPONSE=$(curl -k -s "$HEALTH_ENDPOINT" 2>/dev/null || echo "{}")
    
    if echo "$HEALTH_RESPONSE" | grep -q '"redis_connection":"ok"'; then
        echo -e "${GREEN}✓${NC} API reports Redis connection OK"
        return 0
    else
        echo -e "${RED}✗${NC} API reports Redis connection failed"
        log_message "ERROR: API cannot connect to Redis"
        echo "  Response: $HEALTH_RESPONSE"
        return 1
    fi
}

# Check CSRF token endpoint
check_csrf_endpoint() {
    CSRF_RESPONSE=$(curl -k -s "https://aiwfe.com/api/v1/auth/csrf-token" 2>/dev/null || echo "")
    
    if echo "$CSRF_RESPONSE" | grep -q "csrf_token"; then
        echo -e "${GREEN}✓${NC} CSRF token endpoint working"
        return 0
    else
        echo -e "${RED}✗${NC} CSRF token endpoint not responding"
        log_message "ERROR: CSRF endpoint failure"
        return 1
    fi
}

# Main monitoring function
main() {
    echo "=== Redis Health Monitor ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    ISSUES=0
    
    # Run all checks
    check_redis_container || ((ISSUES++))
    check_redis_network || ((ISSUES++))
    check_redis_acl || ((ISSUES++))
    check_api_health || ((ISSUES++))
    check_csrf_endpoint || ((ISSUES++))
    
    echo ""
    echo "==========================="
    
    if [ $ISSUES -eq 0 ]; then
        echo -e "${GREEN}All checks passed!${NC}"
        log_message "INFO: All health checks passed"
        exit 0
    else
        echo -e "${RED}$ISSUES issue(s) detected${NC}"
        log_message "WARNING: $ISSUES health check failures"
        
        # Send alert (customize this for your alerting system)
        # Example: Send to Slack, PagerDuty, email, etc.
        # alert_ops_team "Redis health check failed with $ISSUES issues"
        
        exit 1
    fi
}

# Run with error handling
main "$@"