#!/bin/sh
# docker/postgres/docker-entrypoint-wrapper.sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "INFO: Postgres entrypoint wrapper started."

# --- Certificate Isolation ---
# This logic runs before the main postgres entrypoint. It copies certificates
# from a shared volume to a private, service-specific location to enforce
# the principle of least privilege. This avoids placing certs in the PGDATA
# directory, which can interfere with the initdb process on first run.

SHARED_CERTS_DIR="/tmp/certs-volume/postgres"
PRIVATE_CERTS_DIR="/etc/certs/postgres"

echo "INFO: Checking for shared certificates in ${SHARED_CERTS_DIR}..."

# Check if the shared certs directory and key files exist
if [ ! -d "$SHARED_CERTS_DIR" ] || [ ! -f "$SHARED_CERTS_DIR/unified-key.pem" ] || [ ! -f "$SHARED_CERTS_DIR/unified-cert.pem" ]; then
    echo "WARN: Shared certificates not found in ${SHARED_CERTS_DIR}. Skipping certificate setup."
else
    echo "INFO: Found shared certificates. Copying to private location: ${PRIVATE_CERTS_DIR}"
    mkdir -p "$PRIVATE_CERTS_DIR"

    cp "$SHARED_CERTS_DIR/unified-cert.pem" "$PRIVATE_CERTS_DIR/server.crt"
    cp "$SHARED_CERTS_DIR/unified-key.pem" "$PRIVATE_CERTS_DIR/server.key"
    cp "$SHARED_CERTS_DIR/rootCA.pem" "$PRIVATE_CERTS_DIR/root.crt"

    # Set permissions (skip chown if it fails in container)
    chown -R postgres:postgres "$PRIVATE_CERTS_DIR" 2>/dev/null || true
    chmod 600 "$PRIVATE_CERTS_DIR/server.key" 2>/dev/null || chmod 644 "$PRIVATE_CERTS_DIR/server.key"
    echo "INFO: Certificate isolation complete."
fi

# --- Handover to Official Entrypoint ---
# Use 'exec' to replace this script with the official postgres entrypoint.
# This is critical for ensuring that PostgreSQL becomes PID 1 and handles signals correctly.
echo "INFO: Handing over control to official postgres entrypoint..."
exec docker-entrypoint.sh "$@"