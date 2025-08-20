#!/bin/sh
set -e

echo "--- create_admin.sh: Script starting ---"

# This script runs after the database migrations to create the initial admin user.

# Export secrets to environment variables for Pydantic and other tools to load.
echo "--- create_admin.sh: Exporting secrets ---"
export POSTGRES_PASSWORD=$(cat /run/secrets/POSTGRES_PASSWORD)
export JWT_SECRET_KEY=$(cat /run/secrets/JWT_SECRET_KEY)
export API_KEY=$(cat /run/secrets/API_KEY)
export QDRANT_API_KEY=$(cat /run/secrets/QDRANT_API_KEY)
export ADMIN_EMAIL=$(cat /run/secrets/admin_email)
export ADMIN_PASSWORD=$(cat /run/secrets/admin_password)
echo "--- create_admin.sh: Secrets exported ---"

# Set the PYTHONPATH to ensure the application modules can be found.
export PYTHONPATH=/app

# Wait for the main postgres database to be healthy and accepting connections.
# This script connects directly to PostgreSQL, bypassing PgBouncer, to ensure reliability
# during initial setup.
echo "--- create_admin.sh: Waiting for PostgreSQL ---"
until PGPASSWORD=$POSTGRES_PASSWORD psql "host=postgres port=5432 dbname=ai_workflow_db user=app_user sslmode=verify-full sslrootcert=/etc/certs/api/rootCA.pem" -c '\q' --quiet -w; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done
echo "--- create_admin.sh: PostgreSQL is available ---"

>&2 echo "Postgres is up - executing admin creation script"

# Run the Python script to create the admin user. This script will use the
# environment variables set above to connect to the database and create the user.
echo "--- create_admin.sh: Running python create_admin.py ---"
cd /app && python -c "
import sys
import logging
from pwdlib import PasswordHash
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from shared.utils.config import get_settings
from shared.database.models import User
from shared.utils.database_setup import Base

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Modern password hashing using pwdlib with Argon2id
pwd_hasher = PasswordHash.recommended()

def get_password_hash(password: str) -> str:
    return pwd_hasher.hash(password)

def _log_before_retry(retry_state: RetryCallState):
    logger.warning('Database connection failed. Retrying in %s seconds... (attempt %d)', retry_state.next_action.sleep, retry_state.attempt_number)

def create_admin_user(session, email: str, password: str):
    # Check if user exists
    result = session.execute(select(User).where(User.email == email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning('User with email %s already exists.', email)
        if not existing_user.is_superuser:
            logger.info('Updating existing user %s to ADMIN role.', email)
            session.execute(
                update(User).where(User.email == email).values(is_superuser=True)
            )
            session.commit()
            logger.info('Admin user check/update complete for: %s', email)
        else:
            logger.info('User is already an admin.')
        return
    
    # Create new admin user directly
    logger.info('Creating new admin user: %s', email)
    hashed_password = get_password_hash(password)
    new_user = User(
        email=email,
        hashed_password=hashed_password,
        is_superuser=True,
        is_active=True,
        is_verified=True
    )
    session.add(new_user)
    session.commit()
    logger.info('Admin user created successfully: %s', email)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(Exception), before_sleep=_log_before_retry)
def main():
    settings = get_settings()
    ADMIN_EMAIL = settings.ADMIN_EMAIL
    ADMIN_PASSWORD = settings.ADMIN_PASSWORD
    if not ADMIN_EMAIL or str(ADMIN_EMAIL) == 'PLEASE_REPLACE' or not ADMIN_PASSWORD or ADMIN_PASSWORD.get_secret_value() == 'PLEASE_REPLACE':
        logger.error('Admin email or password not configured. Please update secrets/admin_email.txt and secrets/admin_password.txt.')
        sys.exit(1)
    
    # Use sync engine with proper psycopg URL
    sync_db_url = settings.database_url.replace('postgresql+psycopg://', 'postgresql://')
    engine = create_engine(sync_db_url)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        try:
            create_admin_user(session, ADMIN_EMAIL, ADMIN_PASSWORD.get_secret_value())
        except Exception as e:
            logger.error('An error occurred during admin creation: %s', e, exc_info=True)
            session.rollback()
            raise

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical('An unexpected error occurred during admin creation: %s', e, exc_info=True)
        sys.exit(1)
"
echo "--- create_admin.sh: Script finished ---"