#!/bin/sh
set -e

# --- Certificate Isolation ---
SHARED_CERTS_DIR="/tmp/certs-volume/pgbouncer"
PRIVATE_CERTS_DIR="/etc/pgbouncer/certs"
echo "PGBouncer Wrapper: Isolating certificates..."
if [ -d "${SHARED_CERTS_DIR}" ]; then
    mkdir -p "${PRIVATE_CERTS_DIR}"
    cp -p -R "${SHARED_CERTS_DIR}/." "${PRIVATE_CERTS_DIR}/"
    echo "PGBouncer Wrapper: Certificates copied to ${PRIVATE_CERTS_DIR}."
else
    echo "PGBouncer Wrapper: No specific certificate directory found at ${SHARED_CERTS_DIR}. Skipping."
fi

# --- Auth File Generation ---
# The host-side _setup_secrets_and_certs.sh script generates a userlist with plaintext passwords.
# We need to query the database to get the actual SCRAM hashes for secure authentication.
# This approach ensures the userlist always matches the database state.
echo "PGBouncer Wrapper: Preparing auth file with SCRAM hashes from database..."
mkdir -p "$(dirname "${PGBOUNCER_AUTH_FILE}")"

# Wait for PostgreSQL to be ready
echo "PGBouncer Wrapper: Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if PGPASSWORD="$(cat /run/secrets/POSTGRES_PASSWORD)" psql -h "${POSTGRES_HOST}" -U "${POSTGRES_SUPERUSER}" -d "${POSTGRES_DB}" -c "SELECT 1;" >/dev/null 2>&1; then
        echo "PGBouncer Wrapper: PostgreSQL is ready."
        break
    fi
    echo "PGBouncer Wrapper: Waiting for PostgreSQL... (attempt $i/30)"
    sleep 2
done

# Query database for SCRAM hashes and generate the auth file
echo "PGBouncer Wrapper: Querying database for SCRAM hashes..."
PGPASSWORD="$(cat /run/secrets/POSTGRES_PASSWORD)" psql -h "${POSTGRES_HOST}" -U "${POSTGRES_SUPERUSER}" -d "${POSTGRES_DB}" -t -c "
SELECT '\"' || usename || '\" \"' || passwd || '\"' 
FROM pg_shadow 
WHERE usename IN ('pgbouncer', 'app_user')
ORDER BY usename;
" | sed '/^$/d' > "${PGBOUNCER_AUTH_FILE}"

echo "PGBouncer Wrapper: Auth file generated with SCRAM hashes from database."

# --- Set Permissions ---
echo "PGBouncer Wrapper: Setting final permissions..."
PGBOUNCER_UID=$(grep '^pgbouncer:' /etc/passwd | cut -d: -f3)
PGBOUNCER_GID=$(grep '^pgbouncer:' /etc/passwd | cut -d: -f4)

if [ -z "${PGBOUNCER_UID}" ] || [ -z "${PGBOUNCER_GID}" ]; then
    echo "PGBouncer Wrapper: FATAL - Could not find pgbouncer user/group in /etc/passwd."
    exit 1
fi

if [ -d "${PRIVATE_CERTS_DIR}" ]; then
    echo "PGBouncer Wrapper: Setting permissions on certificate directory..."
    chown -R "${PGBOUNCER_UID}:${PGBOUNCER_GID}" "${PRIVATE_CERTS_DIR}"
    # The private key must be readable only by the owner.
    chmod 0600 "${PRIVATE_CERTS_DIR}/unified-key.pem"
fi

chown -R "${PGBOUNCER_UID}:${PGBOUNCER_GID}" /etc/pgbouncer/generated
chmod 0700 /etc/pgbouncer/generated
chmod 0600 "${PGBOUNCER_AUTH_FILE}"

# --- Config Substitution ---
PROCESSED_CONFIG_FILE="/tmp/pgbouncer.processed.ini"
echo "PGBouncer Wrapper: Substituting environment variables in config..."
envsubst < /etc/pgbouncer/pgbouncer.ini > "${PROCESSED_CONFIG_FILE}"
echo "PGBouncer Wrapper: Config processed."

# --- PID File Cleanup ---
echo "PGBouncer Wrapper: Cleaning up stale PID file..."
# Remove any stale PID file from previous runs to prevent restart loops
rm -f /tmp/pgbouncer.pid

# --- Handover to pgbouncer ---
echo "PGBouncer Wrapper: Handing over to main pgbouncer process..."
# The entrypoint's job is to prepare the environment. It now hands over
# control to the command specified in the docker-compose.yml file (`$@`),
# which is responsible for starting the actual pgbouncer process.
exec "$@"