#!/bin/bash

# AlertManager Certificate Management Entrypoint Wrapper
# This script handles certificate setup for AlertManager with security isolation

set -euo pipefail

# Logging function with service identification
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [alertmanager-wrapper] $*" >&2
}

log "Starting AlertManager entrypoint wrapper"

# Validate required environment variables
SERVICE_NAME="${SERVICE_NAME:-alertmanager}"
CERTS_SOURCE_DIR="/tmp/certs-volume"
CERTS_TARGET_DIR="/tmp/certs/${SERVICE_NAME}"

log "Service name: ${SERVICE_NAME}"
log "Certificates source: ${CERTS_SOURCE_DIR}"
log "Certificates target: ${CERTS_TARGET_DIR}"

# Validate source certificates directory
if [[ ! -d "${CERTS_SOURCE_DIR}" ]]; then
    log "ERROR: Certificates source directory does not exist: ${CERTS_SOURCE_DIR}"
    exit 1
fi

# Create target certificate directory with secure permissions
log "Creating certificate directory: ${CERTS_TARGET_DIR}"
mkdir -p "${CERTS_TARGET_DIR}"
chmod 755 "${CERTS_TARGET_DIR}"

# Copy certificates from shared volume to isolated location
log "Copying certificates for service isolation"

# Copy all certificate files for AlertManager
if [[ -f "${CERTS_SOURCE_DIR}/rootCA.pem" ]]; then
    cp "${CERTS_SOURCE_DIR}/rootCA.pem" "${CERTS_TARGET_DIR}/rootCA.pem"
    chmod 644 "${CERTS_TARGET_DIR}/rootCA.pem"
    log "Copied root CA certificate"
else
    log "WARNING: Root CA certificate not found"
fi

if [[ -f "${CERTS_SOURCE_DIR}/${SERVICE_NAME}-cert.pem" ]]; then
    cp "${CERTS_SOURCE_DIR}/${SERVICE_NAME}-cert.pem" "${CERTS_TARGET_DIR}/${SERVICE_NAME}-cert.pem"
    chmod 644 "${CERTS_TARGET_DIR}/${SERVICE_NAME}-cert.pem"
    log "Copied service certificate"
fi

if [[ -f "${CERTS_SOURCE_DIR}/${SERVICE_NAME}-key.pem" ]]; then
    cp "${CERTS_SOURCE_DIR}/${SERVICE_NAME}-key.pem" "${CERTS_TARGET_DIR}/${SERVICE_NAME}-key.pem"
    chmod 600 "${CERTS_TARGET_DIR}/${SERVICE_NAME}-key.pem"
    log "Copied service private key"
fi

# Set up certificate permissions for AlertManager
log "Setting certificate permissions for AlertManager security"
if [[ -d "${CERTS_TARGET_DIR}" ]]; then
    find "${CERTS_TARGET_DIR}" -type f -name "*.pem" -exec chmod 644 {} \; 2>/dev/null || true
    find "${CERTS_TARGET_DIR}" -type f -name "*-key.pem" -exec chmod 600 {} \; 2>/dev/null || true
fi

# Create AlertManager data directory with proper permissions
ALERTMANAGER_DATA_DIR="/alertmanager"
if [[ ! -d "${ALERTMANAGER_DATA_DIR}" ]]; then
    log "Creating AlertManager data directory: ${ALERTMANAGER_DATA_DIR}"
    mkdir -p "${ALERTMANAGER_DATA_DIR}"
fi

# Ensure AlertManager user can access data directory
chown -R nobody:nobody "${ALERTMANAGER_DATA_DIR}" 2>/dev/null || {
    log "WARNING: Could not change ownership of AlertManager data directory"
}

# Validate AlertManager configuration
ALERTMANAGER_CONFIG="/etc/alertmanager/alertmanager.yml"
if [[ -f "${ALERTMANAGER_CONFIG}" ]]; then
    log "AlertManager configuration file found: ${ALERTMANAGER_CONFIG}"
else
    log "WARNING: AlertManager configuration file not found: ${ALERTMANAGER_CONFIG}"
fi

# Set up environment for AlertManager
export ALERTMANAGER_CERTS_DIR="${CERTS_TARGET_DIR}"

log "Certificate setup completed successfully"
log "Starting AlertManager with command: $*"

# Execute AlertManager with provided arguments
exec "$@"