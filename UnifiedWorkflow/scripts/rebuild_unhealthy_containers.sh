#!/bin/bash
# Automated Container Rebuild Script for Unhealthy Services
# Focus: health-monitor and perception-service recovery

set -e

echo "🔧 Container Recovery and Rebuild Process Starting..."
echo "=================================================="
echo "Timestamp: $(date)"
echo ""

# Function to check container health
check_health() {
    local service=$1
    local status=$(docker ps --filter "name=$service" --format "{{.Status}}" | head -1)
    if [[ $status == *"healthy"* ]]; then
        echo "healthy"
    elif [[ $status == *"unhealthy"* ]]; then
        echo "unhealthy"
    elif [[ -z "$status" ]]; then
        echo "not_running"
    else
        echo "starting"
    fi
}

# Function to rebuild a service
rebuild_service() {
    local service=$1
    echo ""
    echo "🔄 Rebuilding $service..."
    echo "------------------------"
    
    # Stop the service
    echo "  → Stopping $service..."
    docker-compose stop $service 2>/dev/null || true
    
    # Remove the container (preserve volumes)
    echo "  → Removing old container..."
    docker-compose rm -f $service 2>/dev/null || true
    
    # Rebuild the image
    echo "  → Building new image..."
    docker-compose build --no-cache $service
    
    # Start the service
    echo "  → Starting service..."
    docker-compose up -d $service
    
    # Wait for health check
    echo "  → Waiting for health check..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        sleep 5
        local health=$(check_health "ai_workflow_engine-$service-1")
        
        if [ "$health" == "healthy" ]; then
            echo "  ✅ $service is now healthy!"
            return 0
        elif [ "$health" == "unhealthy" ]; then
            if [ $attempt -eq $max_attempts ]; then
                echo "  ⚠️ $service started but remains unhealthy"
                return 1
            fi
        fi
        
        echo "    Attempt $attempt/$max_attempts - Status: $health"
        attempt=$((attempt + 1))
    done
    
    echo "  ⚠️ $service health check timeout"
    return 1
}

# Change to project directory
cd /home/marku/ai_workflow_engine

echo "📊 Initial Container Status:"
echo "----------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(health-monitor|perception-service|NAMES)" || true

# Target services for rebuild
UNHEALTHY_SERVICES=("health-monitor" "perception-service")

echo ""
echo "🎯 Target Services for Rebuild:"
for service in "${UNHEALTHY_SERVICES[@]}"; do
    health=$(check_health "ai_workflow_engine-$service-1")
    echo "  • $service: $health"
done

# Rebuild unhealthy services
echo ""
echo "🚀 Starting Rebuild Process:"
echo "=============================="

REBUILD_SUCCESS=0
REBUILD_FAILED=0

for service in "${UNHEALTHY_SERVICES[@]}"; do
    health=$(check_health "ai_workflow_engine-$service-1")
    
    if [ "$health" == "unhealthy" ] || [ "$health" == "not_running" ]; then
        if rebuild_service $service; then
            REBUILD_SUCCESS=$((REBUILD_SUCCESS + 1))
        else
            REBUILD_FAILED=$((REBUILD_FAILED + 1))
        fi
    else
        echo ""
        echo "ℹ️ Skipping $service (status: $health)"
    fi
done

# Final status check
echo ""
echo "📊 Final Container Status:"
echo "--------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(health-monitor|perception-service|NAMES)" || true

echo ""
echo "📈 Recovery Summary:"
echo "--------------------"
echo "  • Services rebuilt successfully: $REBUILD_SUCCESS"
echo "  • Services failed to rebuild: $REBUILD_FAILED"

# Check overall system health
echo ""
echo "🏥 System Health Check:"
echo "-----------------------"
docker ps --filter "health=healthy" --format "{{.Names}}" | wc -l | xargs -I {} echo "  • Healthy containers: {}"
docker ps --filter "health=unhealthy" --format "{{.Names}}" | wc -l | xargs -I {} echo "  • Unhealthy containers: {}"
docker ps --filter "status=exited" --format "{{.Names}}" | wc -l | xargs -I {} echo "  • Exited containers: {}"

# Test health-monitor endpoint if rebuilt
if docker ps --filter "name=health-monitor" --filter "health=healthy" -q > /dev/null 2>&1; then
    echo ""
    echo "🔍 Testing health-monitor endpoints:"
    echo "------------------------------------"
    
    # Test internal health endpoint
    echo "  • Testing internal health endpoint..."
    curl -s -o /dev/null -w "    Response: %{http_code}\n" http://localhost:5016/health || echo "    Failed to connect"
    
    # Test metrics endpoint
    echo "  • Testing metrics endpoint..."
    curl -s -o /dev/null -w "    Response: %{http_code}\n" http://localhost:5016/metrics || echo "    Failed to connect"
fi

echo ""
echo "✅ Recovery process completed at $(date)"

# Exit with appropriate code
if [ $REBUILD_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi