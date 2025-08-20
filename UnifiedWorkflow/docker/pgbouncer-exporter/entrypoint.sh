#!/bin/sh
set -e

# Read password from Docker secret
PGPASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
export PGPASSWORD

# Override any existing connection string with one using the secret
unset PGBOUNCER_EXPORTER_CONNECTION_STRING
export PGBOUNCER_EXPORTER_CONNECTION_STRING="postgresql://app_user@pgbouncer:6432/pgbouncer?sslmode=require"

echo "Using PGPASSWORD authentication for pgbouncer exporter"

# Execute the exporter
exec /usr/local/bin/pgbouncer_exporter "$@"