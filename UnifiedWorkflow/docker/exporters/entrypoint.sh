#!/bin/sh
set -e

# This is a principled entrypoint script as described in the project's
# architectural documents. It performs a single, essential task: securely
# loading a secret into the environment for the main application process.

# Default path for the secret if not provided by the environment
: "${POSTGRES_PASSWORD_FILE:=/run/secrets/POSTGRES_PASSWORD}"

if [ -f "$POSTGRES_PASSWORD_FILE" ]; then
    # Export the password to PGPASSWORD. The postgres-exporter and pgbouncer-exporter
    # both use the standard Go pq driver, which respects this environment variable.
    export PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE")
else
    echo "ERROR: Secret file not found at $POSTGRES_PASSWORD_FILE" >&2
    exit 1
fi

# Cede control to the main command passed to the container (e.g., /postgres_exporter)
exec "$@"