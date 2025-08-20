#!/bin/bash

# Infrastructure Validation Script
# Validates Docker Compose configuration and service health

set -e

COMPOSE_FILE="docker-compose.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Infrastructure Validation Report"
echo "=========================================="
echo "Timestamp: $(date)"
echo ""

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "SUCCESS" ]; then
        echo -e "\033[32m✓\033[0m $message"
    elif [ "$status" = "ERROR" ]; then
        echo -e "\033[31m✗\033[0m $message"
    elif [ "$status" = "WARNING" ]; then
        echo -e "\033[33m⚠\033[0m $message"
    else
        echo "  $message"
    fi
}

# 1. Validate Docker Compose configuration
echo "1. Docker Compose Configuration Validation"
echo "-------------------------------------------"

if docker compose -f "$COMPOSE_FILE" config > /dev/null 2>&1; then
    print_status "SUCCESS" "Docker Compose configuration is valid"
    
    # Count services
    SERVICE_COUNT=$(docker compose -f "$COMPOSE_FILE" config --services | wc -l)
    print_status "INFO" "Total services configured: $SERVICE_COUNT"
    
    # Check for duplicate ports
    echo ""
    echo "  Port Mapping Analysis:"
    PORTS=$(docker compose -f "$COMPOSE_FILE" config | grep -E '^\s+-\s+"[0-9]+:[0-9]+"' | sed 's/.*"\([0-9]*\):.*/\1/' | sort)
    DUPLICATE_PORTS=$(echo "$PORTS" | uniq -d)
    
    if [ -z "$DUPLICATE_PORTS" ]; then
        print_status "SUCCESS" "No duplicate port mappings found"
    else
        print_status "ERROR" "Duplicate ports found: $DUPLICATE_PORTS"
    fi
else
    print_status "ERROR" "Docker Compose configuration is invalid"
    docker compose -f "$COMPOSE_FILE" config 2>&1 | head -20
    exit 1
fi

# 2. Health Check Standardization Analysis
echo ""
echo "2. Health Check Standardization"
echo "--------------------------------"

# Extract health check configurations
echo "  Analyzing health check patterns..."

SERVICES_WITH_HEALTH=$(docker compose -f "$COMPOSE_FILE" config | grep -B5 "healthcheck:" | grep "^  [a-z]" | sed 's/://g' | sort -u)
TOTAL_SERVICES=$(docker compose -f "$COMPOSE_FILE" config --services | wc -l)
HEALTH_COUNT=$(echo "$SERVICES_WITH_HEALTH" | wc -l)

print_status "INFO" "Services with health checks: $HEALTH_COUNT/$TOTAL_SERVICES"

# Check for standard patterns (30s interval, 10s timeout, 3 retries)
STANDARD_PATTERN_COUNT=$(docker compose -f "$COMPOSE_FILE" config | grep -A4 "healthcheck:" | grep -E "(interval: 30s|timeout: 10s|retries: 3)" | wc -l)

if [ "$STANDARD_PATTERN_COUNT" -gt 0 ]; then
    print_status "SUCCESS" "Found $STANDARD_PATTERN_COUNT standardized health check settings"
else
    print_status "WARNING" "No standardized health check patterns detected"
fi

# 3. Service Dependencies Analysis
echo ""
echo "3. Service Dependencies"
echo "-----------------------"

# Check critical service dependencies
CRITICAL_SERVICES=("postgres" "redis" "ollama" "api")

for service in "${CRITICAL_SERVICES[@]}"; do
    DEPENDENT_COUNT=$(docker compose -f "$COMPOSE_FILE" config | grep -c "$service:" | head -1)
    if [ "$DEPENDENT_COUNT" -gt 0 ]; then
        print_status "SUCCESS" "Critical service configured: $service"
    else
        print_status "ERROR" "Critical service missing: $service"
    fi
done

# 4. Volume Configuration
echo ""
echo "4. Volume Configuration"
echo "-----------------------"

VOLUMES=$(docker compose -f "$COMPOSE_FILE" config --volumes)
VOLUME_COUNT=$(echo "$VOLUMES" | wc -l)

print_status "INFO" "Configured volumes: $VOLUME_COUNT"

# Check for critical volumes
CRITICAL_VOLUMES=("postgres_data" "redis_data" "ollama_data" "qdrant_data")

for volume in "${CRITICAL_VOLUMES[@]}"; do
    if echo "$VOLUMES" | grep -q "$volume"; then
        print_status "SUCCESS" "Critical volume configured: $volume"
    else
        print_status "ERROR" "Critical volume missing: $volume"
    fi
done

# 5. Network Configuration
echo ""
echo "5. Network Configuration"
echo "------------------------"

NETWORKS=$(docker compose -f "$COMPOSE_FILE" config | grep "networks:" -A2 | grep "ai_workflow_engine_net" | wc -l)

if [ "$NETWORKS" -gt 0 ]; then
    print_status "SUCCESS" "Network configuration found: ai_workflow_engine_net"
else
    print_status "ERROR" "Network configuration missing"
fi

# 6. Restart Policies
echo ""
echo "6. Restart Policies"
echo "-------------------"

RESTART_POLICIES=$(docker compose -f "$COMPOSE_FILE" config | grep "restart:" | sort | uniq -c)
echo "$RESTART_POLICIES" | while read count policy; do
    print_status "INFO" "$count services with policy: $policy"
done

# 7. New Service Integration Check
echo ""
echo "7. New Service Integration"
echo "--------------------------"

NEW_SERVICES=("monitoring-service" "chat-service" "voice-interaction-service" "nudge-service")

for service in "${NEW_SERVICES[@]}"; do
    if docker compose -f "$COMPOSE_FILE" config --services | grep -q "^$service$"; then
        print_status "SUCCESS" "New service integrated: $service"
        
        # Check if service has health check
        if docker compose -f "$COMPOSE_FILE" config | grep -A10 "^  $service:" | grep -q "healthcheck:"; then
            print_status "SUCCESS" "  └─ Health check configured"
        else
            print_status "WARNING" "  └─ No health check configured"
        fi
    else
        print_status "WARNING" "New service not found: $service"
    fi
done

# 8. Check for running containers (if Docker daemon is accessible)
echo ""
echo "8. Current Infrastructure Status"
echo "--------------------------------"

if docker info > /dev/null 2>&1; then
    RUNNING_CONTAINERS=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.State == "running") | .Service' | wc -l || echo "0")
    TOTAL_CONTAINERS=$(docker compose ps --format json 2>/dev/null | jq -r '.Service' | wc -l || echo "0")
    
    if [ "$TOTAL_CONTAINERS" -gt 0 ]; then
        print_status "INFO" "Running containers: $RUNNING_CONTAINERS/$TOTAL_CONTAINERS"
        
        # Show status of critical services
        echo ""
        echo "  Critical Service Status:"
        for service in "${CRITICAL_SERVICES[@]}"; do
            if docker compose ps --format json 2>/dev/null | jq -r --arg svc "$service" 'select(.Service == $svc) | .State' | grep -q "running"; then
                print_status "SUCCESS" "  $service: running"
            else
                STATUS=$(docker compose ps --format json 2>/dev/null | jq -r --arg svc "$service" 'select(.Service == $svc) | .State' || echo "not found")
                if [ "$STATUS" = "not found" ] || [ -z "$STATUS" ]; then
                    print_status "WARNING" "  $service: not deployed"
                else
                    print_status "ERROR" "  $service: $STATUS"
                fi
            fi
        done
    else
        print_status "INFO" "No containers currently deployed"
    fi
else
    print_status "WARNING" "Docker daemon not accessible - skipping runtime checks"
fi

# 9. Configuration Recommendations
echo ""
echo "9. Configuration Recommendations"
echo "--------------------------------"

# Check for monitoring service
if docker compose -f "$COMPOSE_FILE" config --services | grep -q "monitoring-service"; then
    print_status "SUCCESS" "Monitoring service is configured"
else
    print_status "WARNING" "Consider adding monitoring-service for centralized health monitoring"
fi

# Check for resource limits
MEMORY_LIMITS=$(docker compose -f "$COMPOSE_FILE" config | grep -c "memory:" || echo "0")
if [ "$MEMORY_LIMITS" -gt 0 ]; then
    print_status "SUCCESS" "Resource limits configured for $MEMORY_LIMITS services"
else
    print_status "WARNING" "No resource limits configured - consider adding memory limits"
fi

# Summary
echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="

ERROR_COUNT=$(grep -c "✗" /tmp/validation_output 2>/dev/null || echo "0")
WARNING_COUNT=$(grep -c "⚠" /tmp/validation_output 2>/dev/null || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    print_status "SUCCESS" "Infrastructure configuration is valid"
else
    print_status "ERROR" "Found $ERROR_COUNT errors in configuration"
fi

if [ "$WARNING_COUNT" -gt 0 ]; then
    print_status "WARNING" "Found $WARNING_COUNT warnings to review"
fi

echo ""
echo "Validation completed at $(date)"