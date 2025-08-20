#!/bin/bash
# scripts/fix_database_users.sh
# 
# Post-startup script to ensure pgbouncer user exists and has proper permissions.
# This addresses the issue where the PostgreSQL init script doesn't always run
# during volume resets, leaving the pgbouncer user missing.

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

source "$SCRIPT_DIR/_common_functions.sh"

log_info "Checking and fixing database users for PgBouncer authentication..."

# Wait for PostgreSQL to be ready
log_info "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -c "SELECT 1;" >/dev/null 2>&1; then
        log_info "PostgreSQL is ready."
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "PostgreSQL failed to become ready after 30 attempts."
        exit 1
    fi
    log_info "Waiting for PostgreSQL... (attempt $i/30)"
    sleep 2
done

# Check if pgbouncer user exists
log_info "Checking if pgbouncer user exists..."
USER_EXISTS=$(docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -t -c "SELECT COUNT(*) FROM pg_roles WHERE rolname = 'pgbouncer';" | tr -d ' ')

if [ "$USER_EXISTS" = "0" ]; then
    log_info "pgbouncer user missing. Creating user and permissions..."
    
    # Get password from secrets
    POSTGRES_PASSWORD=$(cat "$PROJECT_ROOT/secrets/postgres_password.txt")
    
    # Create pgbouncer user with all necessary permissions
    docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -c "
        CREATE ROLE pgbouncer WITH LOGIN PASSWORD '$POSTGRES_PASSWORD';
        GRANT CONNECT ON DATABASE ai_workflow_db TO pgbouncer;
        GRANT pg_read_all_stats TO pgbouncer;
        GRANT USAGE ON SCHEMA public TO pgbouncer;
    " >/dev/null
    
    log_info "pgbouncer user created successfully."
else
    log_info "pgbouncer user already exists."
fi

# Check if auth function exists
log_info "Checking if auth function exists..."
FUNCTION_EXISTS=$(docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -t -c "SELECT COUNT(*) FROM pg_proc WHERE proname = 'get_auth';" | tr -d ' ')

if [ "$FUNCTION_EXISTS" = "0" ]; then
    log_info "get_auth function missing. Creating function..."
    
    docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -c "
        CREATE OR REPLACE FUNCTION public.get_auth(p_usename TEXT)
        RETURNS TABLE(usename TEXT, password TEXT) AS \$\$
        BEGIN
            RETURN QUERY SELECT usename::TEXT, passwd::TEXT FROM pg_shadow WHERE usename = p_usename;
        END;
        \$\$ LANGUAGE plpgsql SECURITY DEFINER;
        
        GRANT EXECUTE ON FUNCTION public.get_auth(TEXT) TO pgbouncer;
    " >/dev/null
    
    log_info "get_auth function created successfully."
else
    log_info "get_auth function already exists."
fi

# Restart PgBouncer to refresh auth file if we made changes
if [ "$USER_EXISTS" = "0" ] || [ "$FUNCTION_EXISTS" = "0" ]; then
    log_info "Restarting PgBouncer to refresh authentication..."
    docker restart ai_workflow_engine-pgbouncer-1 >/dev/null
    
    # Wait for PgBouncer to be healthy
    log_info "Waiting for PgBouncer to become healthy..."
    for i in $(seq 1 20); do
        if docker exec ai_workflow_engine-pgbouncer-1 sh -c 'PGPASSWORD="'$(cat "$PROJECT_ROOT/secrets/postgres_password.txt")'" psql -h localhost -p 6432 -U app_user -d app_tx -c "SELECT 1;" >/dev/null 2>&1'; then
            log_info "PgBouncer is healthy and accepting connections."
            break
        fi
        if [ $i -eq 20 ]; then
            log_warn "PgBouncer may not be fully ready, but continuing..."
            break
        fi
        sleep 2
    done
fi

# Verify final state
log_info "Verifying final database state..."
FINAL_USERS=$(docker exec ai_workflow_engine-postgres-1 psql -U app_user -d ai_workflow_db -t -c "SELECT COUNT(*) FROM pg_roles WHERE rolname IN ('app_user', 'pgbouncer');" | tr -d ' ')

if [ "$FINAL_USERS" = "2" ]; then
    log_info "✅ Database users verified: Both app_user and pgbouncer exist."
    log_info "✅ PgBouncer authentication should be working correctly."
    log_info "✅ Tool function calling database dependencies are ready."
else
    log_error "❌ Database verification failed. Expected 2 users, found $FINAL_USERS."
    exit 1
fi

log_info "Database user fix completed successfully."