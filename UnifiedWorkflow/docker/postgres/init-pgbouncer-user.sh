#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO
    \$do\$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'pgbouncer') THEN
          CREATE ROLE pgbouncer WITH LOGIN PASSWORD '$(cat $POSTGRES_PASSWORD_FILE)';
       END IF;
    END
    \$do\$;
    GRANT pg_read_all_stats TO pgbouncer;
EOSQL
