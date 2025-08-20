#!/bin/bash
set -e

# This script is a copy of _generate_migration.sh, but it reads the password from the secret file
# and exports it as an environment variable before running the Alembic command.

# Get the migration message from the first argument
migration_message="$1"
if [ -z "$migration_message" ]; then
    echo "ERROR: Migration message is required."
    echo "Usage: ./scripts/_generate_migration_with_password.sh \"Your descriptive message\""
    exit 1
fi

# Export the password from the secret file
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)

# Run the migration generation command
docker compose exec api alembic revision --autogenerate -m "$migration_message"

