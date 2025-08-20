import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy.pool import NullPool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Path Correction ---
# Add the project's root directory to the Python path.
# This allows Alembic to find your application's modules.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now that the path is corrected, we can import your application's modules
# using the full path from the project root.
from shared.utils.config import get_settings
from shared.database.models import Base

# Get application settings to retrieve the database URL
settings = get_settings()

# Construct the database URL from environment variables
def read_secret(secret_name):
    """Read from a Docker secret file, or fallback to environment variable."""
    secret_path = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    return os.getenv(secret_name, "")

postgres_user = read_secret("POSTGRES_USER") or "app_user"
postgres_password = read_secret("POSTGRES_PASSWORD") or ""
postgres_server = os.getenv("POSTGRES_SERVER", "postgres")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "ai_workflow_engine")

database_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


# Add your model's MetaData object here for 'autogenerate' support.
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()