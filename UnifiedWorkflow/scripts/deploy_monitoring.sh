#!/bin/bash

# Deploy Monitoring Service Script
# Safely deploys the new monitoring aggregation service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Monitoring Service Deployment"
echo "=========================================="
echo "Starting deployment at $(date)"
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

# 1. Build monitoring service image
echo "Step 1: Building monitoring service image"
echo "-----------------------------------------"

if docker compose build monitoring-service; then
    print_status "SUCCESS" "Monitoring service image built successfully"
else
    print_status "ERROR" "Failed to build monitoring service image"
    exit 1
fi

# 2. Deploy monitoring service
echo ""
echo "Step 2: Deploying monitoring service"
echo "------------------------------------"

if docker compose up -d monitoring-service; then
    print_status "SUCCESS" "Monitoring service deployed"
else
    print_status "ERROR" "Failed to deploy monitoring service"
    exit 1
fi

# 3. Wait for service to be healthy
echo ""
echo "Step 3: Waiting for service health"
echo "----------------------------------"

MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s -f http://localhost:8020/health > /dev/null 2>&1; then
        print_status "SUCCESS" "Monitoring service is healthy"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        print_status "ERROR" "Monitoring service health check failed after $MAX_ATTEMPTS attempts"
        echo "Checking logs..."
        docker compose logs monitoring-service --tail=20
        exit 1
    fi
    
    echo "  Waiting for service to be ready... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

# 4. Test monitoring endpoints
echo ""
echo "Step 4: Testing monitoring endpoints"
echo "------------------------------------"

# Test health endpoint
if curl -s -f http://localhost:8020/health > /dev/null 2>&1; then
    print_status "SUCCESS" "/health endpoint is responsive"
else
    print_status "ERROR" "/health endpoint failed"
fi

# Test status endpoint
if curl -s -f http://localhost:8020/status > /dev/null 2>&1; then
    print_status "SUCCESS" "/status endpoint is responsive"
    
    # Show overall system status
    OVERALL_STATUS=$(curl -s http://localhost:8020/status | jq -r '.overall_status' 2>/dev/null || echo "unknown")
    print_status "INFO" "Overall system status: $OVERALL_STATUS"
else
    print_status "WARNING" "/status endpoint not responsive"
fi

# Test metrics endpoint
if curl -s -f http://localhost:8020/metrics > /dev/null 2>&1; then
    print_status "SUCCESS" "/metrics endpoint is responsive"
else
    print_status "WARNING" "/metrics endpoint not responsive"
fi

# Test critical services endpoint
if curl -s -f http://localhost:8020/critical > /dev/null 2>&1; then
    print_status "SUCCESS" "/critical endpoint is responsive"
    
    # Show critical services status
    CRITICAL_HEALTHY=$(curl -s http://localhost:8020/critical | jq -r '.all_critical_healthy' 2>/dev/null || echo "unknown")
    if [ "$CRITICAL_HEALTHY" = "true" ]; then
        print_status "SUCCESS" "All critical services are healthy"
    else
        print_status "WARNING" "Some critical services may be unhealthy"
    fi
else
    print_status "WARNING" "/critical endpoint not responsive"
fi

# 5. Show service information
echo ""
echo "Step 5: Service Information"
echo "---------------------------"

# Get container status
CONTAINER_STATUS=$(docker compose ps monitoring-service --format json 2>/dev/null | jq -r '.State' || echo "unknown")
print_status "INFO" "Container status: $CONTAINER_STATUS"

# Get port mapping
PORT_MAPPING=$(docker compose ps monitoring-service --format json 2>/dev/null | jq -r '.Publishers[0].PublishedPort' || echo "unknown")
print_status "INFO" "Service accessible on port: $PORT_MAPPING"

# Show monitored services count
SERVICE_COUNT=$(curl -s http://localhost:8020/services 2>/dev/null | jq '.services | length' || echo "0")
print_status "INFO" "Monitoring $SERVICE_COUNT services"

# 6. Integration with Prometheus
echo ""
echo "Step 6: Prometheus Integration"
echo "------------------------------"

if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_status "SUCCESS" "Prometheus is running"
    
    # Check if monitoring service metrics are being scraped
    if curl -s http://localhost:9090/api/v1/targets 2>/dev/null | grep -q "monitoring-service"; then
        print_status "SUCCESS" "Monitoring service metrics integrated with Prometheus"
    else
        print_status "INFO" "Monitoring service metrics not yet in Prometheus (may need configuration)"
    fi
else
    print_status "WARNING" "Prometheus not accessible"
fi

# Summary
echo ""
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="

if [ "$CONTAINER_STATUS" = "running" ]; then
    print_status "SUCCESS" "Monitoring service successfully deployed and running"
    echo ""
    echo "Access the monitoring service at:"
    echo "  - Health: http://localhost:8020/health"
    echo "  - Status: http://localhost:8020/status"
    echo "  - Metrics: http://localhost:8020/metrics"
    echo "  - Critical Services: http://localhost:8020/critical"
    echo "  - All Services: http://localhost:8020/services"
else
    print_status "ERROR" "Deployment completed with issues"
fi

echo ""
echo "Deployment completed at $(date)"