#!/bin/bash

# Script to fix missing configuration files for infrastructure deployment
# This script handles the copying of configuration files with proper permissions

set -e

DEPLOYMENT_DIR="/home/marku/Documents/programming/comandind/deployment"
DOCKER_COMPOSE_DIR="${DEPLOYMENT_DIR}/docker-compose"

echo "=== Infrastructure Configuration Fix Script ==="
echo "Fixing missing configuration files..."

# Remove empty directories and recreate as files
echo "Removing empty configuration directories..."
if [ -d "${DOCKER_COMPOSE_DIR}/monitoring/fluentd.conf" ]; then
    rm -rf "${DOCKER_COMPOSE_DIR}/monitoring/fluentd.conf" 2>/dev/null || {
        echo "Warning: Could not remove fluentd.conf directory (may need sudo)"
        echo "Please manually remove: ${DOCKER_COMPOSE_DIR}/monitoring/fluentd.conf"
    }
fi

if [ -d "${DOCKER_COMPOSE_DIR}/monitoring/prometheus.yml" ]; then
    rm -rf "${DOCKER_COMPOSE_DIR}/monitoring/prometheus.yml" 2>/dev/null || {
        echo "Warning: Could not remove prometheus.yml directory (may need sudo)"
        echo "Please manually remove: ${DOCKER_COMPOSE_DIR}/monitoring/prometheus.yml"
    }
fi

if [ -d "${DOCKER_COMPOSE_DIR}/nginx/upstream.conf" ]; then
    rm -rf "${DOCKER_COMPOSE_DIR}/nginx/upstream.conf" 2>/dev/null || {
        echo "Warning: Could not remove upstream.conf directory (may need sudo)"
        echo "Please manually remove: ${DOCKER_COMPOSE_DIR}/nginx/upstream.conf"
    }
fi

# Copy fluentd configuration
echo "Copying fluentd configuration..."
if [ -f "${DEPLOYMENT_DIR}/fluentd.conf" ]; then
    cp "${DEPLOYMENT_DIR}/fluentd.conf" "${DOCKER_COMPOSE_DIR}/monitoring/fluentd.conf" || {
        echo "Error: Could not copy fluentd.conf"
        exit 1
    }
    echo "✓ fluentd.conf copied successfully"
else
    echo "Error: Source fluentd.conf not found"
    exit 1
fi

# Copy prometheus configuration
echo "Copying prometheus configuration..."
if [ -f "${DEPLOYMENT_DIR}/monitoring/prometheus.yml" ]; then
    cp "${DEPLOYMENT_DIR}/monitoring/prometheus.yml" "${DOCKER_COMPOSE_DIR}/monitoring/prometheus.yml" || {
        echo "Error: Could not copy prometheus.yml"
        exit 1
    }
    echo "✓ prometheus.yml copied successfully"
else
    echo "Error: Source prometheus.yml not found"
    exit 1
fi

# Copy upstream configuration
echo "Copying upstream configuration..."
if [ -f "${DEPLOYMENT_DIR}/nginx/upstream.conf" ]; then
    cp "${DEPLOYMENT_DIR}/nginx/upstream.conf" "${DOCKER_COMPOSE_DIR}/nginx/upstream.conf" || {
        echo "Error: Could not copy upstream.conf"
        exit 1
    }
    echo "✓ upstream.conf copied successfully"
else
    echo "Error: Source upstream.conf not found"
    exit 1
fi

# Verify all files are in place
echo ""
echo "=== Configuration Verification ==="
echo "Checking required configuration files..."

MISSING_FILES=0

if [ ! -f "${DOCKER_COMPOSE_DIR}/monitoring/fluentd.conf" ]; then
    echo "✗ Missing: fluentd.conf"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    echo "✓ fluentd.conf present"
fi

if [ ! -f "${DOCKER_COMPOSE_DIR}/monitoring/prometheus.yml" ]; then
    echo "✗ Missing: prometheus.yml"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    echo "✓ prometheus.yml present"
fi

if [ ! -f "${DOCKER_COMPOSE_DIR}/nginx/upstream.conf" ]; then
    echo "✗ Missing: upstream.conf"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    echo "✓ upstream.conf present"
fi

if [ $MISSING_FILES -eq 0 ]; then
    echo ""
    echo "🎉 All configuration files are now in place!"
    echo ""
    echo "You can now start the deployment with:"
    echo "cd ${DOCKER_COMPOSE_DIR}"
    echo "docker-compose -f docker-compose.blue-green.yml up -d"
    exit 0
else
    echo ""
    echo "❌ $MISSING_FILES configuration file(s) still missing"
    echo "Please check file permissions and copy manually if needed"
    exit 1
fi