#!/bin/bash

# AlertManager mTLS Certificate Management Entrypoint Wrapper
# This script handles certificate setup for AlertManager with mTLS security isolation

set -euo pipefail

# Logging function with service identification
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [alertmanager-mtls-wrapper] $*" >&2
}

log "Starting AlertManager mTLS entrypoint wrapper"

# Validate required environment variables
SERVICE_NAME="${SERVICE_NAME:-alertmanager}"
CERTS_SOURCE_DIR="/tmp/certs-volume"
CERTS_TARGET_DIR="/etc/certs/${SERVICE_NAME}"

# mTLS Configuration
MTLS_ENABLED="${MTLS_ENABLED:-false}"
MTLS_CA_CERT_FILE="${MTLS_CA_CERT_FILE:-}"
MTLS_CERT_FILE="${MTLS_CERT_FILE:-}"
MTLS_KEY_FILE="${MTLS_KEY_FILE:-}"

log "Service name: ${SERVICE_NAME}"
log "mTLS enabled: ${MTLS_ENABLED}"
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

# Copy root CA certificate
if [[ -f "${CERTS_SOURCE_DIR}/rootCA.pem" ]]; then
    cp "${CERTS_SOURCE_DIR}/rootCA.pem" "${CERTS_TARGET_DIR}/rootCA.pem"
    chmod 644 "${CERTS_TARGET_DIR}/rootCA.pem"
    log "Copied root CA certificate"
else
    log "WARNING: Root CA certificate not found"
fi

# Handle mTLS certificates if enabled
if [[ "${MTLS_ENABLED}" == "true" ]]; then
    log "Configuring mTLS certificates"
    
    # Copy mTLS CA certificate
    if [[ -n "${MTLS_CA_CERT_FILE}" && -f "${MTLS_CA_CERT_FILE}" ]]; then
        cp "${MTLS_CA_CERT_FILE}" "${CERTS_TARGET_DIR}/mtls-ca.pem"
        chmod 644 "${CERTS_TARGET_DIR}/mtls-ca.pem"
        log "Copied mTLS CA certificate"
    fi
    
    # Copy service mTLS certificate
    if [[ -n "${MTLS_CERT_FILE}" && -f "${MTLS_CERT_FILE}" ]]; then
        cp "${MTLS_CERT_FILE}" "${CERTS_TARGET_DIR}/mtls-cert.pem"
        chmod 644 "${CERTS_TARGET_DIR}/mtls-cert.pem"
        log "Copied mTLS service certificate"
    fi
    
    # Copy service mTLS private key
    if [[ -n "${MTLS_KEY_FILE}" && -f "${MTLS_KEY_FILE}" ]]; then
        cp "${MTLS_KEY_FILE}" "${CERTS_TARGET_DIR}/mtls-key.pem"
        chmod 600 "${CERTS_TARGET_DIR}/mtls-key.pem"
        log "Copied mTLS service private key"
    fi
    
    # Create unified certificate for TLS termination
    if [[ -f "${CERTS_TARGET_DIR}/mtls-cert.pem" ]]; then
        cp "${CERTS_TARGET_DIR}/mtls-cert.pem" "${CERTS_TARGET_DIR}/unified-cert.pem"
        
        # Append intermediate certificates if they exist
        if [[ -f "${CERTS_TARGET_DIR}/mtls-ca.pem" ]]; then
            cat "${CERTS_TARGET_DIR}/mtls-ca.pem" >> "${CERTS_TARGET_DIR}/unified-cert.pem"
        fi
        
        chmod 644 "${CERTS_TARGET_DIR}/unified-cert.pem"
        log "Created unified certificate chain"
    fi
    
    # Create unified private key
    if [[ -f "${CERTS_TARGET_DIR}/mtls-key.pem" ]]; then
        cp "${CERTS_TARGET_DIR}/mtls-key.pem" "${CERTS_TARGET_DIR}/unified-key.pem"
        chmod 600 "${CERTS_TARGET_DIR}/unified-key.pem"
        log "Created unified private key"
    fi
fi

# Copy standard service certificates
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
    chown -R root:root "${CERTS_TARGET_DIR}"
    find "${CERTS_TARGET_DIR}" -type f -name "*.pem" -exec chmod 644 {} \;
    find "${CERTS_TARGET_DIR}" -type f -name "*-key.pem" -exec chmod 600 {} \;
    find "${CERTS_TARGET_DIR}" -type f -name "unified-key.pem" -exec chmod 600 {} \;
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
    log "Validating AlertManager configuration"
    if ! /bin/alertmanager --config.file="${ALERTMANAGER_CONFIG}" --check.config; then
        log "ERROR: AlertManager configuration validation failed"
        exit 1
    fi
    log "AlertManager configuration validation successful"
else
    log "WARNING: AlertManager configuration file not found: ${ALERTMANAGER_CONFIG}"
fi

# Set up environment for AlertManager
export ALERTMANAGER_CERTS_DIR="${CERTS_TARGET_DIR}"

# Configure TLS settings for AlertManager if mTLS is enabled
if [[ "${MTLS_ENABLED}" == "true" && -f "${CERTS_TARGET_DIR}/unified-cert.pem" && -f "${CERTS_TARGET_DIR}/unified-key.pem" ]]; then
    export ALERTMANAGER_TLS_CERT_FILE="${CERTS_TARGET_DIR}/unified-cert.pem"
    export ALERTMANAGER_TLS_KEY_FILE="${CERTS_TARGET_DIR}/unified-key.pem"
    log "Configured TLS settings for AlertManager"
fi

log "Certificate setup completed successfully"
log "Starting AlertManager with command: $*"

# Execute AlertManager with provided arguments
exec "$@"