#!/bin/bash
#
# Cognitive Services Deployment Monitor
# Real-time monitoring and evidence collection for container rebuilds
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service definitions
SERVICES=("hybrid-memory-service" "reasoning-service" "learning-service" "coordination-service")
PORTS=(8002 8003 8005 8004)

echo "=========================================="
echo "   COGNITIVE SERVICES DEPLOYMENT MONITOR"
echo "=========================================="
echo ""

# Function to check container status
check_container_status() {
    local service=$1
    local container_name="ai_workflow_engine-${service}-1"
    
    # Get container status
    local status=$(docker ps --filter "name=${container_name}" --format "{{.Status}}" 2>/dev/null)
    
    if [ -z "$status" ]; then
        echo -e "${RED}✗ Not Running${NC}"
    elif [[ "$status" == *"healthy"* ]]; then
        echo -e "${GREEN}✓ Healthy${NC} (${status})"
    elif [[ "$status" == *"unhealthy"* ]]; then
        echo -e "${RED}✗ Unhealthy${NC} (${status})"
    elif [[ "$status" == *"starting"* ]]; then
        echo -e "${YELLOW}⟳ Starting${NC} (${status})"
    elif [[ "$status" == *"restarting"* ]]; then
        echo -e "${YELLOW}⟲ Restarting${NC} (${status})"
    else
        echo -e "${BLUE}● Running${NC} (${status})"
    fi
}

# Function to check for SSL errors
check_ssl_errors() {
    local service=$1
    local container_name="ai_workflow_engine-${service}-1"
    
    # Count SSL-related errors in last 50 log lines
    local ssl_errors=$(docker logs "${container_name}" --tail 50 2>&1 | grep -c "sslmode\|SSL\|ssl" || echo 0)
    
    if [ "$ssl_errors" -eq 0 ]; then
        echo -e "${GREEN}✓ No SSL errors${NC}"
    else
        echo -e "${RED}✗ ${ssl_errors} SSL-related messages${NC}"
    fi
}

# Function to check endpoint health
check_endpoint() {
    local service=$1
    local port=$2
    
    # Try to reach the health endpoint
    if curl -s -f "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Endpoint responding${NC} (port ${port})"
    else
        echo -e "${RED}✗ Endpoint unreachable${NC} (port ${port})"
    fi
}

# Function to check environment variables
check_environment() {
    local service=$1
    local container_name="ai_workflow_engine-${service}-1"
    
    if [ "$service" == "learning-service" ]; then
        # Check for neo4j_auth
        local has_neo4j=$(docker inspect "${container_name}" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -c "NEO4J_AUTH" || echo 0)
        
        if [ "$has_neo4j" -gt 0 ]; then
            echo -e "${GREEN}✓ neo4j_auth configured${NC}"
        else
            echo -e "${RED}✗ neo4j_auth missing${NC}"
        fi
    else
        # Check for DATABASE_URL
        local has_db=$(docker inspect "${container_name}" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -c "DATABASE_URL" || echo 0)
        
        if [ "$has_db" -gt 0 ]; then
            echo -e "${GREEN}✓ DATABASE_URL configured${NC}"
        else
            echo -e "${YELLOW}⚠ DATABASE_URL not found${NC}"
        fi
    fi
}

# Main monitoring loop
monitor_services() {
    clear
    echo "=========================================="
    echo "   COGNITIVE SERVICES DEPLOYMENT MONITOR"
    echo "=========================================="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local port="${PORTS[$i]}"
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "${BLUE}▶ ${service}${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        echo -n "  Status:      "
        check_container_status "$service"
        
        echo -n "  SSL Errors:  "
        check_ssl_errors "$service"
        
        echo -n "  Endpoint:    "
        check_endpoint "$service" "$port"
        
        echo -n "  Environment: "
        check_environment "$service"
        
        echo ""
    done
    
    echo "=========================================="
    echo "Press Ctrl+C to exit | Refreshing in 5s..."
}

# Function to generate evidence report
generate_evidence_report() {
    local report_file=".claude/deployment/evidence_$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p .claude/deployment
    
    echo "Generating evidence report..."
    
    {
        echo "COGNITIVE SERVICES DEPLOYMENT EVIDENCE REPORT"
        echo "=============================================="
        echo "Generated: $(date)"
        echo ""
        
        for i in "${!SERVICES[@]}"; do
            local service="${SERVICES[$i]}"
            local container_name="ai_workflow_engine-${service}-1"
            
            echo "Service: ${service}"
            echo "------------------------"
            
            # Container details
            echo "Container Status:"
            docker ps --filter "name=${container_name}" --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
            echo ""
            
            # Health check
            echo "Health Status:"
            docker inspect "${container_name}" --format '{{.State.Health.Status}}' 2>/dev/null || echo "No health check"
            echo ""
            
            # Recent logs (last 10 lines)
            echo "Recent Logs:"
            docker logs "${container_name}" --tail 10 2>&1
            echo ""
            
            # Environment variables (filtered)
            echo "Key Environment Variables:"
            if [ "$service" == "learning-service" ]; then
                docker inspect "${container_name}" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep -E "NEO4J|DATABASE_URL" || echo "None found"
            else
                docker inspect "${container_name}" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | grep "DATABASE_URL" || echo "None found"
            fi
            echo ""
            echo "----------------------------------------"
            echo ""
        done
        
        # Overall system status
        echo "OVERALL SYSTEM STATUS"
        echo "====================="
        docker ps --filter "name=ai_workflow_engine" --format "table {{.Names}}\t{{.Status}}" | grep -E "memory|reasoning|learning|coordination"
        
    } > "$report_file"
    
    echo -e "${GREEN}✓ Evidence report saved to: ${report_file}${NC}"
}

# Parse command line arguments
case "$1" in
    report)
        generate_evidence_report
        ;;
    once)
        monitor_services
        ;;
    *)
        # Continuous monitoring mode
        echo "Starting continuous monitoring..."
        echo "Press Ctrl+C to stop"
        echo ""
        
        trap "echo 'Monitoring stopped'; exit 0" INT
        
        while true; do
            monitor_services
            sleep 5
        done
        ;;
esac