#!/bin/bash
set -e

# The POSTGRES_USER, POSTGRES_DB, and POSTGRES_PASSWORD_FILE env vars are available
# from the docker-compose environment.
APP_USER="$POSTGRES_USER"
APP_DB="$POSTGRES_DB"
APP_PASSWORD=$(cat "$POSTGRES_PASSWORD_FILE")

# This script is executed by the official postgres entrypoint as the 'postgres' OS user.
# We will use the 'postgres' DB superuser to perform all setup, ensuring it is
# robust and idempotent, regardless of what the main entrypoint does.
psql -v ON_ERROR_STOP=1 --username "$APP_USER" --dbname "postgres" -v APP_DB="$APP_DB" -v APP_USER="$APP_USER" <<-EOSQL
    -- Create the application user with SUPERUSER privileges if it doesn't exist.
    -- The official entrypoint should do this, but this is a safeguard.
    DO \$\$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$APP_USER') THEN
          CREATE ROLE "$APP_USER" WITH LOGIN SUPERUSER PASSWORD '$APP_PASSWORD';
       END IF;
    END
    \$\$;

    -- Create the application database if it doesn't exist, and set the app user as the owner.
    -- This is the primary fix for the "database does not exist" error.
    SELECT 'CREATE DATABASE ' || quote_ident(:'APP_DB') || ' WITH OWNER = ' || quote_ident(:'APP_USER')
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'APP_DB')\gexec
EOSQL

# Now, connect to the newly confirmed app_db to create the pgbouncer user and function,
# still using the 'postgres' superuser to guarantee permissions.
psql -v ON_ERROR_STOP=1 --username "$APP_USER" --dbname "$APP_DB" <<-EOSQL
    -- Create the unprivileged user for pgbouncer's auth_query.
    -- Its password is the same as the main postgres user for simplicity.
    DO \$\$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'pgbouncer') THEN
          CREATE ROLE pgbouncer WITH LOGIN PASSWORD '$APP_PASSWORD';
       END IF;
    END
    \$\$;

    -- Grant necessary privileges for the pgbouncer user.
    GRANT CONNECT ON DATABASE "$APP_DB" TO pgbouncer;
    -- Grant privilege to read monitoring statistics, used by pgbouncer_exporter.
    GRANT pg_read_all_stats TO pgbouncer;
    GRANT USAGE ON SCHEMA public TO pgbouncer;

    -- Create the security definer function for the auth_query.
    -- This function must be owned by a superuser (which 'postgres' is).
    CREATE OR REPLACE FUNCTION public.get_auth(p_usename TEXT)
    RETURNS TABLE(usename TEXT, password TEXT) AS \$\$
    BEGIN
        RETURN QUERY SELECT usename::TEXT, passwd::TEXT FROM pg_shadow WHERE usename = p_usename;
    END;
    \$\$ LANGUAGE plpgsql SECURITY DEFINER;

    -- Grant execute permission on the function to the pgbouncer auth_user.
    GRANT EXECUTE ON FUNCTION public.get_auth(p_usename TEXT) TO pgbouncer;
EOSQL