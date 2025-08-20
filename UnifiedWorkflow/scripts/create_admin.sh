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
export PYTHONPATH=/app/app

# Set database URL with SSL disabled
export DATABASE_URL="postgresql+psycopg2://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db?sslmode=disable"

# Wait for the main postgres database to be healthy and accepting connections.
# This script connects directly to PostgreSQL, bypassing PgBouncer, to ensure reliability
# during initial setup.
echo "--- create_admin.sh: Waiting for PostgreSQL ---"
until PGPASSWORD=$POSTGRES_PASSWORD psql "host=postgres port=5432 dbname=ai_workflow_db user=app_user sslmode=disable" -c '\q' --quiet -w; do
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
    from sqlalchemy import text
    
    # Check if user exists using raw SQL to avoid model issues
    result = session.execute(
        text('SELECT id, email, role, hashed_password FROM users WHERE email = :email'),
        {'email': email}
    )
    existing_user = result.fetchone()
    
    if existing_user:
        logger.warning('User with email %s already exists.', email)
        current_hash = existing_user[3]  # hashed_password column
        hashed_password = get_password_hash(password)
        
        # Debug logging
        logger.info('Current hash: %s', current_hash[:20] + '...' if current_hash else 'None')
        logger.info('Hash starts with $2b$: %s', current_hash and current_hash.startswith('$2b$'))
        logger.info('Full check result: %s', bool(current_hash and current_hash.startswith('$2b$')))
        logger.info('Current role: %s', existing_user[2])
        
        # Check if password hash needs updating (old bcrypt format)
        # Force update password hash since we're migrating from bcrypt to pwdlib
        needs_password_update = True  # Force update for migration
        needs_role_update = existing_user[2] != 'admin'  # role column
        
        if needs_password_update:
            logger.warning('User has old bcrypt password hash. Updating to new pwdlib format...')
        
        if needs_role_update:
            logger.info('Updating existing user %s to ADMIN role.', email)
        
        if needs_password_update or needs_role_update:
            session.execute(
                text('UPDATE users SET role = :role, status = :status, hashed_password = :hashed_password WHERE email = :email'),
                {'role': 'admin', 'status': 'active', 'hashed_password': hashed_password, 'email': email}
            )
            session.commit()
            if needs_password_update:
                logger.info('Password hash updated to new pwdlib format.')
            logger.info('Admin user check/update complete for: %s', email)
        else:
            logger.info('User is already an admin with modern password hash.')
        return
    
    # Create new admin user using raw SQL to avoid model column issues
    logger.info('Creating new admin user: %s', email)
    hashed_password = get_password_hash(password)
    session.execute(
        text('''
            INSERT INTO users (email, hashed_password, role, status, tfa_enabled, created_at)
            VALUES (:email, :hashed_password, :role, :status, :tfa_enabled, NOW())
        '''),
        {
            'email': email,
            'hashed_password': hashed_password,
            'role': 'admin',
            'status': 'active',
            'tfa_enabled': False
        }
    )
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
    
    # Use sync engine with proper psycopg3 URL 
    # The database_url should already be postgresql+psycopg:// format which is correct for psycopg3
    engine = create_engine(settings.database_url)
    # Skip metadata.create_all to avoid foreign key issues with incomplete migrations
    # Base.metadata.create_all(engine)
    
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