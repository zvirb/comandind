#!/bin/sh
set -e

echo "--- migrate_user_passwords.sh: Script starting ---"

# Export secrets to environment variables
echo "--- migrate_user_passwords.sh: Exporting secrets ---"
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
export JWT_SECRET_KEY=$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY)
echo "--- migrate_user_passwords.sh: Secrets exported ---"

# Set the PYTHONPATH to ensure the application modules can be found.
export PYTHONPATH=/app/app

# Wait for the main postgres database to be healthy and accepting connections.
echo "--- migrate_user_passwords.sh: Waiting for PostgreSQL ---"
until PGPASSWORD=$POSTGRES_PASSWORD psql "host=postgres port=5432 dbname=ai_workflow_db user=app_user sslmode=verify-full sslrootcert=/etc/certs/api/rootCA.pem" -c '\q' --quiet -w; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done
echo "--- migrate_user_passwords.sh: PostgreSQL is available ---"

>&2 echo "Postgres is up - executing password migration script"

# Run the Python migration script
echo "--- migrate_user_passwords.sh: Running password migration ---"
cd /app && python scripts/migrate_user_passwords.py

echo "--- migrate_user_passwords.sh: Script finished ---"