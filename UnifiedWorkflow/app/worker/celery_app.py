import logging

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# This will hold the engine and session factory unique to each worker process
# to prevent sharing connections across forked processes.
_db_state = {}


def get_db_session_factory():
    """Creates a new SQLAlchemy session factory."""
    # The worker should connect to the database via the URL specified in settings.
    # This URL should point to PgBouncer for connection pooling.
    db_url = str(settings.DATABASE_URL)
    if not db_url:
        logger.critical("DATABASE_URL not configured for Celery worker. Database operations will fail.")
        raise ValueError("DATABASE_URL not configured for Celery worker.")

    # SSL connection arguments for pgbouncer (same as API)
    connect_args = {}
    if "pgbouncer" in db_url:
        import os
        # Detect service name from environment or default to 'worker'
        service_name = os.getenv('SERVICE_NAME', 'worker')
        cert_path = f"/etc/certs/{service_name}"
        
        connect_args = {
            "sslmode": "require",
            "sslcert": f"{cert_path}/unified-cert.pem", 
            "sslkey": f"{cert_path}/unified-key.pem"
        }
        logger.info(f"Worker using SSL certificates from {cert_path}")

    engine = create_engine(db_url, connect_args=connect_args)
    _db_state["engine"] = engine
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@worker_process_init.connect(weak=False)
def init_worker_db_connection(**_kwargs):
    """Create a unique DB session factory for each worker process."""
    logger.info("Initializing DB connection for Celery worker process...")
    _db_state["session_factory"] = get_db_session_factory()


@worker_process_shutdown.connect(weak=False)
def shutdown_worker_db_connection(**_kwargs):
    """Dispose of the DB engine in each worker process on shutdown."""
    if "engine" in _db_state:
        logger.info("Disposing DB connection for Celery worker process...")
        _db_state["engine"].dispose()

# Define the Celery application instance
celery_app = Celery(
    "worker",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=["worker.tasks"]  # List of modules to import when the worker starts
)

celery_app.conf.update(
    task_track_started=True,
)

# Initialize protocol worker service
async def initialize_protocol_worker():
    """Initialize protocol worker service."""
    try:
        from worker.services.protocol_worker_service import initialize_protocol_worker
        await initialize_protocol_worker(celery_app)
        logger.info("Protocol worker service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize protocol worker: {e}", exc_info=True)

# Initialize protocol worker on worker startup
import asyncio
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

if not loop.is_running():
    loop.run_until_complete(initialize_protocol_worker())