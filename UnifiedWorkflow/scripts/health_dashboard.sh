#!/bin/bash

# Health Dashboard Script
# Provides a comprehensive view of all service health statuses

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check service health
check_service_health() {
    local service=$1
    local port=$2
    local endpoint=${3:-/health}
    local protocol=${4:-http}
    
    if [ "$protocol" = "tcp" ]; then
        if nc -z localhost "$port" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    else
        if curl -s -f "${protocol}://localhost:${port}${endpoint}" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
}

# Function to get container status
get_container_status() {
    local service=$1
    local status=$(docker compose ps "$service" --format json 2>/dev/null | jq -r '.State' || echo "not deployed")
    
    case "$status" in
        "running")
            echo -e "${GREEN}Running${NC}"
            ;;
        "exited")
            echo -e "${RED}Exited${NC}"
            ;;
        "restarting")
            echo -e "${YELLOW}Restarting${NC}"
            ;;
        *)
            echo -e "${YELLOW}Not Deployed${NC}"
            ;;
    esac
}

clear

echo "=================================================="
echo "       AI Workflow Engine Health Dashboard"
echo "=================================================="
echo "Timestamp: $(date)"
echo ""

# Core Services
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}CORE SERVICES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "%-30s %-15s %-10s\n" "Service" "Status" "Health"
echo "--------------------------------------------------"

# Check core services
printf "%-30s %-15s %-10s\n" "PostgreSQL" "$(get_container_status postgres)" "$(check_service_health postgres 5432 '' tcp)"
printf "%-30s %-15s %-10s\n" "Redis" "$(get_container_status redis)" "$(check_service_health redis 6379 '' tcp)"
printf "%-30s %-15s %-10s\n" "Qdrant Vector DB" "$(get_container_status qdrant)" "$(check_service_health qdrant 6333 /healthz https)"
printf "%-30s %-15s %-10s\n" "Ollama LLM" "$(get_container_status ollama)" "$(check_service_health ollama 11434 /)"
printf "%-30s %-15s %-10s\n" "Main API" "$(get_container_status api)" "$(check_service_health api 8000 /health)"
printf "%-30s %-15s %-10s\n" "WebUI" "$(get_container_status webui)" "$(check_service_health webui 3001 /)"

# Cognitive Services
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}COGNITIVE SERVICES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "%-30s %-15s %-10s\n" "Service" "Status" "Health"
echo "--------------------------------------------------"

printf "%-30s %-15s %-10s\n" "Coordination Service" "$(get_container_status coordination-service)" "$(check_service_health coordination-service 8001 /health)"
printf "%-30s %-15s %-10s\n" "Memory Service" "$(get_container_status hybrid-memory-service)" "$(check_service_health hybrid-memory-service 8002 /health)"
printf "%-30s %-15s %-10s\n" "Learning Service" "$(get_container_status learning-service)" "$(check_service_health learning-service 8003 /health)"
printf "%-30s %-15s %-10s\n" "Perception Service" "$(get_container_status perception-service)" "$(check_service_health perception-service 8004 /health)"
printf "%-30s %-15s %-10s\n" "Reasoning Service" "$(get_container_status reasoning-service)" "$(check_service_health reasoning-service 8005 /health)"

# Intelligent Services
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}INTELLIGENT SERVICES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "%-30s %-15s %-10s\n" "Service" "Status" "Health"
echo "--------------------------------------------------"

printf "%-30s %-15s %-10s\n" "Chat Service" "$(get_container_status chat-service)" "$(check_service_health chat-service 8007 /health)"
printf "%-30s %-15s %-10s\n" "Voice Interaction" "$(get_container_status voice-interaction-service)" "$(check_service_health voice-interaction-service 8006 /health)"
printf "%-30s %-15s %-10s\n" "Nudge Service" "$(get_container_status nudge-service)" "$(check_service_health nudge-service 8008 /health)"
printf "%-30s %-15s %-10s\n" "Recommendation Engine" "$(get_container_status recommendation-service)" "$(check_service_health recommendation-service 8009 /health)"
printf "%-30s %-15s %-10s\n" "External API Service" "$(get_container_status external-api-service)" "$(check_service_health external-api-service 8012 /health)"

# Monitoring & Observability
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}MONITORING & OBSERVABILITY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "%-30s %-15s %-10s\n" "Service" "Status" "Health"
echo "--------------------------------------------------"

printf "%-30s %-15s %-10s\n" "Monitoring Aggregator" "$(get_container_status monitoring-service)" "$(check_service_health monitoring-service 8020 /health)"
printf "%-30s %-15s %-10s\n" "Prometheus" "$(get_container_status prometheus)" "$(check_service_health prometheus 9090 /-/healthy)"
printf "%-30s %-15s %-10s\n" "Grafana" "$(get_container_status grafana)" "$(check_service_health grafana 3000 /api/health)"
printf "%-30s %-15s %-10s\n" "AlertManager" "$(get_container_status alertmanager)" "$(check_service_health alertmanager 9093 /-/healthy)"
printf "%-30s %-15s %-10s\n" "Health Monitor" "$(get_container_status health-monitor)" "$(check_service_health health-monitor 8888 /health)"

# Message Queue Services
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}MESSAGE QUEUE SERVICES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "%-30s %-15s %-10s\n" "Service" "Status" "Health"
echo "--------------------------------------------------"

printf "%-30s %-15s %-10s\n" "RabbitMQ" "$(get_container_status rabbitmq)" "$(check_service_health rabbitmq 15672 /api/health/checks/alarms)"
printf "%-30s %-15s %-10s\n" "Kafka" "$(get_container_status kafka)" "$(check_service_health kafka 9092 '' tcp)"
printf "%-30s %-15s %-10s\n" "Zookeeper" "$(get_container_status zookeeper)" "$(check_service_health zookeeper 2181 '' tcp)"

# System Resources
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}SYSTEM RESOURCES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# CPU Usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
echo -e "CPU Usage: ${YELLOW}${CPU_USAGE}%${NC}"

# Memory Usage
MEM_INFO=$(free -h | awk 'NR==2{printf "Memory: %s/%s (%.1f%%)", $3, $2, $3*100/$2}')
echo -e "${MEM_INFO}"

# Disk Usage
DISK_INFO=$(df -h / | awk 'NR==2{printf "Disk: %s/%s (%s)", $3, $2, $5}')
echo -e "${DISK_INFO}"

# Docker Stats
echo ""
CONTAINER_COUNT=$(docker ps -q | wc -l)
echo -e "Running Containers: ${GREEN}${CONTAINER_COUNT}${NC}"

# Summary
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}SUMMARY${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

HEALTHY_COUNT=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.Health == "healthy")' | wc -l || echo "0")
UNHEALTHY_COUNT=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.Health == "unhealthy")' | wc -l || echo "0")
RUNNING_COUNT=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.State == "running")' | wc -l || echo "0")

echo -e "Healthy Services: ${GREEN}${HEALTHY_COUNT}${NC}"
echo -e "Unhealthy Services: ${RED}${UNHEALTHY_COUNT}${NC}"
echo -e "Running Services: ${GREEN}${RUNNING_COUNT}${NC}"

# Production Endpoints
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PRODUCTION ENDPOINTS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check production URLs
if curl -s -f -o /dev/null -w "%{http_code}" https://aiwfe.com | grep -q "200\|301\|302"; then
    echo -e "https://aiwfe.com: ${GREEN}✓ Accessible${NC}"
else
    echo -e "https://aiwfe.com: ${RED}✗ Not Accessible${NC}"
fi

if curl -s -f -o /dev/null -w "%{http_code}" http://aiwfe.com | grep -q "200\|301\|302"; then
    echo -e "http://aiwfe.com: ${GREEN}✓ Accessible${NC}"
else
    echo -e "http://aiwfe.com: ${RED}✗ Not Accessible${NC}"
fi

echo ""
echo "=================================================="
echo "Dashboard refreshed at $(date)"
echo "=================================================="