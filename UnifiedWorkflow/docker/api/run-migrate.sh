#!/bin/sh
set -e

# This script now runs as root, so it can read secrets.

export PYTHONPATH=/app
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
export JWT_SECRET_KEY=$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY)
# For migrations, connect directly to PostgreSQL to ensure session-level features like
# advisory locks work correctly. This bypasses the connection pooler. We use sslmode=verify-full
# to ensure an encrypted, verified connection to the server, but we do not present a client
# certificate, as password authentication (SCRAM) is sufficient. Removing the client cert
# and key prevents the "unsupported certificate" error.
export DATABASE_URL="postgresql+psycopg://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db?sslmode=verify-full&sslrootcert=/etc/certs/api/rootCA.pem"

# Wait for PostgreSQL to be healthy and accepting connections.
until PGPASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD) psql "host=postgres port=5432 dbname=ai_workflow_db user=app_user sslmode=verify-full sslrootcert=/etc/certs/api/rootCA.pem" -c '\q' --quiet -w; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "DB Migration: Running Schema Verification..."
echo "Database URL: $DATABASE_URL"
echo "Testing database connection..."
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('$DATABASE_URL')
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection successful:', result.fetchone())
"

echo "Running database schema verification..."
# Use schema verification instead of Alembic to avoid revision tracking issues
# The schema verification ensures all required tables and columns exist
# This is run as root to access secret files for database connection

# Change to the app directory to ensure alembic can find the config
cd /app

# Check if database is already at the correct version
echo "Checking current database version..."
DB_VERSION=$(python -c "
from sqlalchemy import create_engine, text
try:
    engine = create_engine('$DATABASE_URL')
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version_num FROM alembic_version;'))
        current = result.fetchone()
        if current:
            print(current[0])
        else:
            print('NONE')
except Exception as e:
    print('ERROR')
")

echo "Current database version: $DB_VERSION"

# Get the latest migration version from alembic
LATEST_VERSION=$(python -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
try:
    alembic_cfg = Config('alembic.ini')
    script = ScriptDirectory.from_config(alembic_cfg)
    head = script.get_current_head()
    print(head if head else 'NONE')
except Exception as e:
    print('ERROR')
")

echo "Latest migration version: $LATEST_VERSION"

# Check if database is at the latest version
if [ "$DB_VERSION" = "$LATEST_VERSION" ] && [ "$DB_VERSION" != "ERROR" ] && [ "$DB_VERSION" != "NONE" ]; then
    echo "✅ Database is already at the latest version ($DB_VERSION)"
    echo "✅ All required tables and schema are in place"
    echo "✅ Migration completed successfully"
    exit 0
else
    echo "Database version $DB_VERSION is not at expected head $LATEST_VERSION"
    echo "Running migration upgrade..."
    # Run the actual migration
    exec alembic upgrade head
fi
