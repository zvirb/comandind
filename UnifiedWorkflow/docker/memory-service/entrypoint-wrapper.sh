#!/bin/bash
# Memory Service Entrypoint Wrapper
# Handles mTLS certificate setup and service initialization

set -euo pipefail

# Service configuration
SERVICE_NAME=${SERVICE_NAME:-"memory-service"}
MTLS_ENABLED=${MTLS_ENABLED:-"false"}

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [${SERVICE_NAME}] $1" >&2
}

log "Starting ${SERVICE_NAME} entrypoint wrapper..."

# Handle mTLS setup if enabled
if [ "${MTLS_ENABLED}" = "true" ]; then
    log "mTLS enabled, setting up certificates..."
    
    # Certificate file paths
    MTLS_CA_CERT_FILE=${MTLS_CA_CERT_FILE:-"/run/secrets/mtls_ca_cert"}
    MTLS_CERT_FILE=${MTLS_CERT_FILE:-"/run/secrets/memory_service_cert_bundle"}
    MTLS_KEY_FILE=${MTLS_KEY_FILE:-"/run/secrets/memory_service_private_key"}
    
    # Target certificate directory
    CERT_DIR="/etc/certs/${SERVICE_NAME}"
    mkdir -p "${CERT_DIR}"
    
    # Copy certificates if they exist
    if [ -f "${MTLS_CA_CERT_FILE}" ]; then
        cp "${MTLS_CA_CERT_FILE}" "${CERT_DIR}/rootCA.pem"
        log "Copied CA certificate"
    else
        log "WARNING: CA certificate not found at ${MTLS_CA_CERT_FILE}"
    fi
    
    if [ -f "${MTLS_CERT_FILE}" ]; then
        cp "${MTLS_CERT_FILE}" "${CERT_DIR}/unified-cert.pem"
        log "Copied service certificate"
    else
        log "WARNING: Service certificate not found at ${MTLS_CERT_FILE}"
    fi
    
    if [ -f "${MTLS_KEY_FILE}" ]; then
        cp "${MTLS_KEY_FILE}" "${CERT_DIR}/unified-key.pem"
        chmod 600 "${CERT_DIR}/unified-key.pem"
        log "Copied service private key"
    else
        log "WARNING: Service private key not found at ${MTLS_KEY_FILE}"
    fi
    
    # Set environment variables for certificate paths
    export CERT_DIR_PATH="${CERT_DIR}"
    export CA_CERT_PATH="${CERT_DIR}/rootCA.pem"
    export SERVICE_CERT_PATH="${CERT_DIR}/unified-cert.pem"
    export SERVICE_KEY_PATH="${CERT_DIR}/unified-key.pem"
    
    log "mTLS certificates configured"
else
    log "mTLS disabled, skipping certificate setup"
fi

# Wait for dependencies
log "Checking dependencies..."

# Wait for PostgreSQL
if [ -n "${POSTGRES_HOST:-}" ]; then
    log "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
    timeout=60
    while ! nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}" && [ $timeout -gt 0 ]; do
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log "ERROR: PostgreSQL not available after 60 seconds"
        exit 1
    fi
    log "PostgreSQL is available"
fi

# Wait for Qdrant
if [ -n "${QDRANT_URL:-}" ]; then
    QDRANT_HOST=$(echo "${QDRANT_URL}" | sed -E 's|^https?://([^:]+)(:[0-9]+)?.*|\1|')
    QDRANT_PORT=$(echo "${QDRANT_URL}" | sed -E 's|^https?://[^:]+:?([0-9]+)?.*|\1|')
    QDRANT_PORT=${QDRANT_PORT:-6333}
    
    log "Waiting for Qdrant at ${QDRANT_HOST}:${QDRANT_PORT}..."
    timeout=60
    while ! nc -z "${QDRANT_HOST}" "${QDRANT_PORT}" && [ $timeout -gt 0 ]; do
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log "ERROR: Qdrant not available after 60 seconds"
        exit 1
    fi
    log "Qdrant is available"
fi

# Wait for Ollama
if [ -n "${OLLAMA_URL:-}" ]; then
    OLLAMA_HOST=$(echo "${OLLAMA_URL}" | sed -E 's|^https?://([^:]+)(:[0-9]+)?.*|\1|')
    OLLAMA_PORT=$(echo "${OLLAMA_URL}" | sed -E 's|^https?://[^:]+:?([0-9]+)?.*|\1|')
    OLLAMA_PORT=${OLLAMA_PORT:-11434}
    
    log "Waiting for Ollama at ${OLLAMA_HOST}:${OLLAMA_PORT}..."
    timeout=60
    while ! nc -z "${OLLAMA_HOST}" "${OLLAMA_PORT}" && [ $timeout -gt 0 ]; do
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log "ERROR: Ollama not available after 60 seconds"
        exit 1
    fi
    log "Ollama is available"
fi

# Wait for Redis if specified
if [ -n "${REDIS_URL:-}" ]; then
    REDIS_HOST=$(echo "${REDIS_URL}" | sed -E 's|^redis://[^@]*@?([^:]+)(:[0-9]+)?.*|\1|')
    REDIS_PORT=$(echo "${REDIS_URL}" | sed -E 's|^redis://[^@]*@?[^:]+:?([0-9]+)?.*|\1|')
    REDIS_PORT=${REDIS_PORT:-6379}
    
    log "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT}..."
    timeout=30
    while ! nc -z "${REDIS_HOST}" "${REDIS_PORT}" && [ $timeout -gt 0 ]; do
        sleep 1
        timeout=$((timeout - 1))
    done
    
    if [ $timeout -eq 0 ]; then
        log "WARNING: Redis not available after 30 seconds"
    else
        log "Redis is available"
    fi
fi

log "All dependencies are ready"

# Run database migrations if needed
log "Running database initialization..."
python -c "
import asyncio
from memory_service.database import init_database

async def main():
    try:
        await init_database()
        print('Database initialization completed successfully')
    except Exception as e:
        print(f'Database initialization failed: {e}')
        exit(1)

asyncio.run(main())
"

# Set up memory service specific environment
export MEMORY_SERVICE_READY="true"
export SERVICE_START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log "Starting ${SERVICE_NAME} with command: $*"

# Execute the main command
exec "$@"