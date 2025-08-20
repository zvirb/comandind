"""A script to initialize and seed the database."""

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .init_db import logger, seed_initial_data
from .utils.config import Settings

# Load environment variables from .env file, which is crucial for standalone script execution.
load_dotenv()

if __name__ == "__main__":
    logger.info("Starting database seeding via run_init_db.py...")

    # Pydantic's BaseSettings loads from the environment, which Pylance can't see.
    # We ignore the "missing arguments" error as we know it's configured correctly.
    settings = Settings()  # type: ignore[call-arg]
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        seed_initial_data(db)
        logger.info("Database seeding completed successfully.")
    except SQLAlchemyError as e:
        logger.error("Database seeding failed: %s", e, exc_info=True)
    finally:
        db.close()