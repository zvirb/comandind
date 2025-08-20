#!/bin/sh
set -e

AUTH_FILE_SOURCE='/run/secrets/pgbouncer_users'
AUTH_FILE_DEST='/tmp/pgbouncer_users_processed'
PGBOUNCER_INI_TEMPLATE='/etc/pgbouncer/pgbouncer.ini'
PGBOUNCER_INI_PROCESSED='/tmp/pgbouncer.ini.processed'

# As root, copy the secret and set correct ownership/permissions for the postgres user
cp "$AUTH_FILE_SOURCE" "$AUTH_FILE_DEST"
chown postgres:postgres "$AUTH_FILE_DEST"
chmod 600 "$AUTH_FILE_DEST"

# As root, process the pgbouncer.ini template
envsubst < "$PGBOUNCER_INI_TEMPLATE" > "$PGBOUNCER_INI_PROCESSED"

# Drop privileges to the 'postgres' user and execute pgbouncer
exec su-exec postgres pgbouncer "$PGBOUNCER_INI_PROCESSED"
