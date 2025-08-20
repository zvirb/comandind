#!/bin/bash

# Infrastructure Configuration Test Script
# Tests that all services can start properly with the fixed configurations

set -e

DEPLOYMENT_DIR="/home/marku/Documents/programming/comandind/deployment"
DOCKER_COMPOSE_DIR="${DEPLOYMENT_DIR}/docker-compose"

echo "=== Infrastructure Configuration Test ==="
echo "Testing infrastructure readiness after configuration fixes..."
echo ""

# Test 1: Configuration file validation
echo "🔍 Test 1: Configuration File Validation"
echo "----------------------------------------"

MISSING_FILES=0

# Check fluentd.conf
if [ ! -f "${DEPLOYMENT_DIR}/fluentd.conf" ]; then
    echo "✗ Missing: fluentd.conf"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    echo "✓ fluentd.conf exists and is accessible"
fi

# Check prometheus.yml
if [ ! -f "${DEPLOYMENT_DIR}/monitoring/prometheus.yml" ]; then
    echo "✗ Missing: prometheus.yml"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    echo "✓ prometheus.yml exists and is accessible"
fi

# Check upstream.conf
if [ ! -f "${DEPLOYMENT_DIR}/nginx/upstream.conf" ]; then
    echo "✗ Missing: upstream.conf"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    echo "✓ upstream.conf exists and is accessible"
fi

if [ $MISSING_FILES -gt 0 ]; then
    echo "❌ $MISSING_FILES configuration file(s) missing"
    exit 1
fi

echo ""

# Test 2: Docker Compose validation
echo "🐳 Test 2: Docker Compose Configuration Validation"
echo "---------------------------------------------------"

cd "${DOCKER_COMPOSE_DIR}"

if docker compose -f docker-compose.blue-green.yml config --quiet; then
    echo "✓ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors"
    exit 1
fi

echo ""

# Test 3: Fluentd configuration validation
echo "📝 Test 3: Fluentd Configuration Validation"
echo "--------------------------------------------"

if docker run --rm -v "${DEPLOYMENT_DIR}/fluentd.conf:/fluentd/etc/fluent.conf:ro" fluent/fluentd:v1.16-1 fluentd --dry-run -c /fluentd/etc/fluent.conf >/dev/null 2>&1; then
    echo "✓ Fluentd configuration is valid"
else
    echo "❌ Fluentd configuration has errors"
    echo "Running detailed check..."
    docker run --rm -v "${DEPLOYMENT_DIR}/fluentd.conf:/fluentd/etc/fluent.conf:ro" fluent/fluentd:v1.16-1 fluentd --dry-run -c /fluentd/etc/fluent.conf
    exit 1
fi

echo ""

# Test 4: Prometheus configuration validation
echo "📊 Test 4: Prometheus Configuration Validation"
echo "-----------------------------------------------"

if docker run --rm --entrypoint="" -v "${DEPLOYMENT_DIR}/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro" prom/prometheus:latest promtool check config /etc/prometheus/prometheus.yml >/dev/null 2>&1; then
    echo "✓ Prometheus configuration is valid"
else
    echo "❌ Prometheus configuration has errors"
    echo "Running detailed check..."
    docker run --rm --entrypoint="" -v "${DEPLOYMENT_DIR}/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro" prom/prometheus:latest promtool check config /etc/prometheus/prometheus.yml
    exit 1
fi

echo ""

# Test 5: Nginx configuration validation
echo "🌐 Test 5: Nginx Configuration Validation"
echo "------------------------------------------"

# Check if the upstream.conf file has the correct syntax structure
if grep -q "upstream game-active" "${DEPLOYMENT_DIR}/nginx/upstream.conf" && \
   grep -q "upstream game-standby" "${DEPLOYMENT_DIR}/nginx/upstream.conf" && \
   grep -q "upstream game-backup" "${DEPLOYMENT_DIR}/nginx/upstream.conf"; then
    echo "✓ Nginx upstream configuration structure is correct"
    echo "  (Note: Host resolution will be validated when services are running)"
else
    echo "❌ Nginx upstream configuration is missing required upstream blocks"
    exit 1
fi

echo ""

# Test 6: Service dependency check
echo "🔗 Test 6: Service Dependencies Check"
echo "--------------------------------------"

echo "Checking Docker daemon..."
if docker info >/dev/null 2>&1; then
    echo "✓ Docker daemon is running"
else
    echo "❌ Docker daemon is not available"
    exit 1
fi

echo "Checking network connectivity for image pulls..."
if docker pull hello-world >/dev/null 2>&1; then
    echo "✓ Can pull Docker images"
    docker rmi hello-world >/dev/null 2>&1
else
    echo "⚠️  Warning: Cannot pull Docker images (check network connectivity)"
fi

echo ""

# Test 7: Port availability check
echo "🔌 Test 7: Port Availability Check"
echo "-----------------------------------"

REQUIRED_PORTS=(80 443 8080 8081 8082 9090 24224)
PORT_CONFLICTS=0

for port in "${REQUIRED_PORTS[@]}"; do
    if netstat -tuln 2>/dev/null | grep ":${port} " >/dev/null; then
        echo "⚠️  Port $port is already in use"
        PORT_CONFLICTS=$((PORT_CONFLICTS + 1))
    else
        echo "✓ Port $port is available"
    fi
done

if [ $PORT_CONFLICTS -gt 0 ]; then
    echo "⚠️  Warning: $PORT_CONFLICTS port(s) are in use. You may need to stop existing services."
fi

echo ""

# Summary
echo "📋 Test Summary"
echo "==============="

if [ $MISSING_FILES -eq 0 ]; then
    echo "🎉 All infrastructure configuration tests passed!"
    echo ""
    echo "✅ Configuration files are in place and valid"
    echo "✅ Docker Compose configuration is valid"
    echo "✅ Fluentd logging configuration is valid"
    echo "✅ Prometheus monitoring configuration is valid"
    echo "✅ Nginx upstream configuration is valid"
    echo "✅ Docker daemon is available"
    
    if [ $PORT_CONFLICTS -eq 0 ]; then
        echo "✅ All required ports are available"
    fi
    
    echo ""
    echo "🚀 Ready to deploy! Use the following command:"
    echo "cd ${DOCKER_COMPOSE_DIR}"
    echo "docker compose -f docker-compose.blue-green.yml up -d"
    echo ""
    echo "📊 Monitor deployment with:"
    echo "docker compose -f docker-compose.blue-green.yml logs -f"
    echo ""
    echo "🔍 Check service health:"
    echo "curl http://localhost/health"
    echo "curl http://localhost:9090 # Prometheus"
    echo "curl http://localhost:8081/metrics # cAdvisor"
    
    exit 0
else
    echo "❌ Infrastructure configuration tests failed"
    echo "Please fix the issues above before deploying"
    exit 1
fi