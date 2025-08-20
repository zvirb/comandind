#!/bin/sh
set -e

# This script runs as root, so it can read secrets.
# Export postgres password from Docker secret for libpq
export PGPASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)

echo "PgBouncer Exporter: Starting with Docker secret authentication"

# Set connection string without embedded password - password comes from PGPASSWORD env var
# Use the correct environment variable name for pgbouncer_exporter
export PGBOUNCER_EXPORTER_CONNECTION_STRING="postgresql://app_user@pgbouncer:6432/pgbouncer?sslmode=require"

# Execute the pgbouncer_exporter with explicit connection string flag
exec /usr/local/bin/pgbouncer_exporter --pgBouncer.connectionString="postgresql://app_user@pgbouncer:6432/pgbouncer?sslmode=require"