#!/bin/sh
# This is a generic wrapper script for service entrypoints.
# It performs two main functions:
# 1. Certificate Isolation: Copies service-specific certificates from a shared
#    volume to a private, in-container location.
# 2. Privilege Dropping: If the RUN_AS_USER environment variable is set, it
#    executes the final command as that user, adhering to the principle of
#    least privilege.

set -e

# --- Configuration ---
# SERVICE_NAME: The name of the service, used to find its certs in the shared volume.
# RUN_AS_USER: Optional. The user:group to run the final command as (e.g., "nobody:nogroup").
SERVICE_NAME="${SERVICE_NAME:-default}"
RUN_AS_USER="${RUN_AS_USER:-}"
SHARED_CERTS_DIR="/tmp/certs-volume/${SERVICE_NAME}"
PRIVATE_CERTS_DIR="/etc/certs/${SERVICE_NAME}"

# --- Certificate Isolation ---
# This block must be run as root to create directories in /etc and chown them.
if [ -d "${SHARED_CERTS_DIR}" ]; then
    echo "Wrapper: [${SERVICE_NAME}] Isolating certificates..."
    mkdir -p "${PRIVATE_CERTS_DIR}"
    # Use cp -a to preserve permissions from the source, then chown if needed.
    cp -a "${SHARED_CERTS_DIR}/." "${PRIVATE_CERTS_DIR}/"
    echo "Wrapper: [${SERVICE_NAME}] Certificates copied to ${PRIVATE_CERTS_DIR}."
fi

# --- Handover to Main Process ---
echo "Wrapper: [${SERVICE_NAME}] Handing over to main process..."

exec "$@"