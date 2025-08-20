#!/bin/bash
set -euo pipefail

# Consolidated Monitoring Deployment Script
# Version: 2.1
# Purpose: Deploy and validate monitoring infrastructure

# Load common functions
if [ -f /home/marku/ai_workflow_engine/scripts/_common_functions.sh ]; then
    source /home/marku/ai_workflow_engine/scripts/_common_functions.sh
fi

# Validate monitoring configuration files
validate_config() {
    echo "Checking Prometheus configuration validity..."
    if docker run --rm -v /home/marku/ai_workflow_engine/config/prometheus:/config prom/prometheus:latest promtool check config /config/prometheus.yml; then
        echo "Prometheus configuration is valid."
    else
        echo "Error: Invalid Prometheus configuration"
        exit 1
    fi
}

# Restart monitoring services
restart_services() {
    echo "Stopping existing monitoring containers..."
    docker-compose -f /home/marku/ai_workflow_engine/docker-compose-mcp.yml down prometheus alertmanager grafana cadvisor node-exporter

    echo "Starting monitoring services..."
    docker-compose -f /home/marku/ai_workflow_engine/docker-compose-mcp.yml up -d prometheus alertmanager grafana cadvisor node-exporter
}

# Validate metrics endpoint health
validate_metrics_endpoints() {
    echo "Checking Prometheus metrics endpoint..."
    if curl -f http://localhost:9090/metrics > /dev/null 2>&1; then
        echo "Prometheus metrics endpoint is healthy."
    else
        echo "Error: Prometheus metrics endpoint failed"
        exit 1
    fi

    echo "Checking Node Exporter metrics endpoint..."
    if curl -f http://localhost:9100/metrics > /dev/null 2>&1; then
        echo "Node Exporter metrics endpoint is healthy."
    else
        echo "Error: Node Exporter metrics endpoint failed"
        exit 1
    fi
}

# Main deployment workflow
main() {
    trap 'echo "Error occurred during monitoring deployment"; exit 1' ERR

    validate_config
    restart_services
    sleep 15  # Wait for services to stabilize
    validate_metrics_endpoints

    echo "✅ Monitoring infrastructure successfully deployed and validated."
}

# Execute main function
main "$@"
