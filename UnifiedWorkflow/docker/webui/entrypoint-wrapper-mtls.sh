#!/bin/sh
# WebUI mTLS entrypoint wrapper
# Handles certificate isolation for non-root webui container

set -e

# Configuration
SERVICE_NAME="${SERVICE_NAME:-webui}"
SHARED_CERTS_DIR="/tmp/certs-volume/${SERVICE_NAME}"
PRIVATE_CERTS_DIR="/app/certs/${SERVICE_NAME}"

# Certificate Isolation (as root initially, then drop privileges)
if [ -d "${SHARED_CERTS_DIR}" ]; then
    echo "Wrapper: [${SERVICE_NAME}] Isolating certificates..."
    
    # Create certificates directory in /app instead of /etc (webui user owns /app)
    mkdir -p "${PRIVATE_CERTS_DIR}"
    
    # Copy certificates to app directory
    cp -a "${SHARED_CERTS_DIR}/." "${PRIVATE_CERTS_DIR}/"
    
    # Change ownership to webui user
    chown -R webui:nodejs "${PRIVATE_CERTS_DIR}"
    
    echo "Wrapper: [${SERVICE_NAME}] Certificates copied to ${PRIVATE_CERTS_DIR}."
fi

# Handover to Main Process
echo "Wrapper: [${SERVICE_NAME}] Handing over to main process..."

# Switch to webui user if running as root
if [ "$(id -u)" = "0" ]; then
    echo "Wrapper: [${SERVICE_NAME}] Switching to webui user..."
    exec su-exec webui:nodejs "$@"
else
    echo "Wrapper: [${SERVICE_NAME}] Executing as current user: $@"
    exec "$@"
fi