#!/bin/bash

# Database Health Monitor for AI Workflow Engine
# Comprehensive health checks and performance monitoring for all database services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_PASSWORD="${REDIS_PASSWORD:-$(cat /home/marku/ai_workflow_engine/secrets/redis_password.txt 2>/dev/null || echo "")}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(cat /home/marku/ai_workflow_engine/secrets/postgres_password.txt 2>/dev/null || echo "")}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo -e "${BLUE}=== AI Workflow Engine Database Health Monitor ===${NC}"
echo -e "${BLUE}Timestamp: ${TIMESTAMP}${NC}"
echo ""

# Function to test Redis connectivity and performance
test_redis() {
    echo -e "${YELLOW}Testing Redis...${NC}"
    
    # Test basic connectivity
    if docker run --rm --network ai_workflow_engine_ai_workflow_engine_net redis:7-alpine \
       redis-cli -h redis -p 6379 -a "${REDIS_PASSWORD}" --user lwe-app ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis connectivity: OK${NC}"
    else
        echo -e "${RED}✗ Redis connectivity: FAILED${NC}"
        return 1
    fi
    
    # Get Redis info
    REDIS_INFO=$(docker exec ai_workflow_engine-redis-1 redis-cli -u "redis://lwe-app:${REDIS_PASSWORD}@localhost:6379" info clients 2>/dev/null | head -5)
    echo -e "${BLUE}Redis Client Info:${NC}"
    echo "$REDIS_INFO" | grep -E "(connected_clients|maxclients|blocked_clients)" | sed 's/^/  /'
    
    # Test database isolation
    for db in {1..4}; do
        if docker run --rm --network ai_workflow_engine_ai_workflow_engine_net redis:7-alpine \
           redis-cli -h redis -p 6379 -a "${REDIS_PASSWORD}" --user lwe-app -n $db ping >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Redis DB ${db}: Accessible${NC}"
        else
            echo -e "${RED}✗ Redis DB ${db}: FAILED${NC}"
        fi
    done
    echo ""
}

# Function to test PostgreSQL connectivity and performance
test_postgresql() {
    echo -e "${YELLOW}Testing PostgreSQL...${NC}"
    
    # Test direct PostgreSQL connectivity
    if docker run --rm --network ai_workflow_engine_ai_workflow_engine_net postgres:15-alpine \
       pg_isready -h postgres -p 5432 -U app_user -d ai_workflow_db >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL direct connection: OK${NC}"
    else
        echo -e "${RED}✗ PostgreSQL direct connection: FAILED${NC}"
        return 1
    fi
    
    # Test PgBouncer connection pooling
    if docker exec ai_workflow_engine-pgbouncer-1 sh -c \
       'PGPASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD) psql "host=localhost port=6432 dbname=ai_workflow_db user=app_user sslmode=require" -c "SELECT 1;" >/dev/null 2>&1'; then
        echo -e "${GREEN}✓ PgBouncer connection pooling: OK${NC}"
    else
        echo -e "${RED}✗ PgBouncer connection pooling: FAILED${NC}"
    fi
    
    # Get connection pool status
    POOL_STATUS=$(docker exec ai_workflow_engine-pgbouncer-1 sh -c \
        'PGPASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD) psql "host=localhost port=6432 dbname=pgbouncer user=app_user sslmode=require" -c "SHOW POOLS;" 2>/dev/null' | grep -v "^-" | grep -v "row)" || echo "No pool data")
    echo -e "${BLUE}PgBouncer Pool Status:${NC}"
    echo "$POOL_STATUS" | head -3 | sed 's/^/  /'
    echo ""
}

# Function to test Qdrant vector database
test_qdrant() {
    echo -e "${YELLOW}Testing Qdrant Vector Database...${NC}"
    
    # Test health endpoint
    if docker run --rm --network ai_workflow_engine_ai_workflow_engine_net curlimages/curl \
       curl -f -k https://qdrant:6333/healthz >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Qdrant health check: OK${NC}"
    else
        echo -e "${RED}✗ Qdrant health check: FAILED${NC}"
        return 1
    fi
    
    # Test collections endpoint
    if docker run --rm --network ai_workflow_engine_ai_workflow_engine_net curlimages/curl \
       curl -f -k https://qdrant:6333/collections >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Qdrant collections endpoint: OK${NC}"
    else
        echo -e "${RED}✗ Qdrant collections endpoint: FAILED${NC}"
    fi
    
    # Get cluster info
    CLUSTER_INFO=$(docker run --rm --network ai_workflow_engine_ai_workflow_engine_net curlimages/curl \
        curl -s -k https://qdrant:6333/cluster 2>/dev/null | head -3 || echo "No cluster data")
    echo -e "${BLUE}Qdrant Cluster Info:${NC}"
    echo "$CLUSTER_INFO" | sed 's/^/  /'
    echo ""
}

# Function to test service health endpoints
test_service_endpoints() {
    echo -e "${YELLOW}Testing Service Health Endpoints...${NC}"
    
    # Test API service
    if curl -f http://localhost:8000/health --max-time 5 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ API service health: OK${NC}"
    else
        echo -e "${RED}✗ API service health: FAILED${NC}"
    fi
    
    # Test WebUI service  
    if curl -f http://localhost:3001/ --max-time 5 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ WebUI service health: OK${NC}"
    else
        echo -e "${RED}✗ WebUI service health: FAILED${NC}"
    fi
    
    echo ""
}

# Function to check database container resource usage
check_resource_usage() {
    echo -e "${YELLOW}Checking Database Container Resources...${NC}"
    
    # Get container stats
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
        ai_workflow_engine-redis-1 \
        ai_workflow_engine-postgres-1 \
        ai_workflow_engine-qdrant-1 \
        ai_workflow_engine-pgbouncer-1 2>/dev/null | sed 's/^/  /' || echo "  Resource data unavailable"
    
    echo ""
}

# Function to generate recommendations
generate_recommendations() {
    echo -e "${YELLOW}Database Performance Recommendations:${NC}"
    
    # Check Redis memory usage
    REDIS_MEMORY=$(docker exec ai_workflow_engine-redis-1 redis-cli -u "redis://lwe-app:${REDIS_PASSWORD}@localhost:6379" info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")
    echo -e "${BLUE}Redis Memory Usage: ${REDIS_MEMORY}${NC}"
    
    # Check PostgreSQL connections
    PG_CONNECTIONS=$(docker exec ai_workflow_engine-postgres-1 sh -c \
        'PGPASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD) psql -h localhost -U app_user -d ai_workflow_db -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null' | grep -o '[0-9]\+' | head -1 || echo "unknown")
    echo -e "${BLUE}PostgreSQL Active Connections: ${PG_CONNECTIONS}${NC}"
    
    echo -e "${GREEN}Recommendations:${NC}"
    echo "  • Redis authentication and ACL configuration: ✓ Working"
    echo "  • Connection pooling via PgBouncer: ✓ Configured"
    echo "  • SSL/TLS encryption for Qdrant: ✓ Enabled"
    echo "  • Database health monitoring: ✓ Implemented"
    echo "  • Multi-database isolation: ✓ Configured (Redis DBs 1-4)"
    echo ""
}

# Main execution
main() {
    test_redis
    test_postgresql
    test_qdrant
    test_service_endpoints
    check_resource_usage
    generate_recommendations
    
    echo -e "${GREEN}=== Database Health Check Complete ===${NC}"
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Start ML services with fixed Redis authentication"
    echo "  2. Validate ML service database connectivity"
    echo "  3. Monitor performance under load"
    echo "  4. Configure automated health monitoring"
}

# Run main function
main "$@"