"""
Initializes and seeds the database.

This script is designed to be run as a standalone module to set up the database
schema and populate it with initial data, such as default category weights and
time budgets. It drops all existing tables before creating new ones.
"""

import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker
from shared.database.models import CategoryWeight, TimeBudget, EventCategory, SystemSetting
from shared.utils.database_setup import Base
from .utils.config import Settings


# Setup logging
logger = logging.getLogger(__name__)


load_dotenv()


def seed_initial_data(db: Session):
    """Seeds the database with initial category weights if they don't exist."""
    logger.info("Seeding initial data...")

    # Define default categories and their weights using the Enum
    default_weights = {
        EventCategory.WORK: 8.0,
        EventCategory.HEALTH: 9.0,
        EventCategory.LEISURE: 6.0,
        EventCategory.FAMILY: 7.0,
        EventCategory.FITNESS: 7.0,  # Added missing category
        EventCategory.DEFAULT: 5.0,
    }

    for category, weight in default_weights.items():
        # Check if the category already exists
        exists = db.query(CategoryWeight).filter(CategoryWeight.category_name == category.value).first()
        if not exists:
            new_weight = CategoryWeight(category_name=category.value, weight=weight)
            db.add(new_weight)
            logger.info("Added category: %s with weight %s", category.value, weight)

    # --- Add seeding for TimeBudget ---
    logger.info("Seeding initial time budgets...")
    default_budgets = {
        EventCategory.WORK: 40.0,
        EventCategory.HEALTH: 5.0,
        EventCategory.FITNESS: 3.0,
        EventCategory.LEISURE: 10.0,
        EventCategory.FAMILY: 10.0, # Added missing category
        EventCategory.DEFAULT: 0.0, # Added missing category
    }

    for category, hours in default_budgets.items():
        exists = (
            db.query(TimeBudget)
            .filter(TimeBudget.category_name == category.value, TimeBudget.period == "weekly")
            .first()
        )
        if not exists:
            new_budget = TimeBudget(category_name=category.value, budgeted_hours=hours, period="weekly")
            db.add(new_budget)
            logger.info("Added weekly budget for '%s': %s hours", category.value, hours)

    # --- Add seeding for SystemSettings ---
    logger.info("Seeding initial system settings...")
    default_settings = {
        "allow_registration": ("true", "Whether new user registration is allowed"),
        "require_approval": ("false", "Whether new users require admin approval"),
        "default_role": ("user", "Default role for new users"),
    }

    for key, (value, description) in default_settings.items():
        exists = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not exists:
            new_setting = SystemSetting(key=key, value=value, description=description)
            db.add(new_setting)
            logger.info("Added system setting: %s = %s", key, value)

    db.commit()


def main():
    """Main function to initialize and seed the database."""
    settings = Settings()  # type: ignore[call-arg]
    engine = create_engine(settings.database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # --- Main execution ---
    logger.info("Starting database initialization process...")

    # Log the target database information
    target_db_name_for_log = "unknown"
    try:
        # engine.url is a URL object from SQLAlchemy
        target_db_name_for_log = engine.url.database
        full_url_str = str(engine.url)

        # Mask password in the URL string for logging
        url_for_logging = make_url(full_url_str)  # Create a new URL object to safely modify
        if url_for_logging.password:
            url_for_logging = url_for_logging.set(password="********")

        logger.info("Using database configuration (password masked): %s", str(url_for_logging))
        logger.info("Target database for table creation: '%s'", target_db_name_for_log)
        logger.info(
            "IMPORTANT: Ensure this database ('%s') exists and is accessible "
            "by the provided credentials before running this script. "
            "This script creates tables, not the database itself.",
            target_db_name_for_log,
        )
    except (AttributeError, ValueError) as e:
        logger.error(
            "Could not determine database details from engine. Error: %s", e, exc_info=True
        )
        logger.info("Please check your DATABASE_URL environment variable in the .env file.")
        target_db_name_for_log = "unknown (error determining from engine)"

    logger.info(
        "Attempting to drop all existing tables (if any) in database: '%s'...",
        target_db_name_for_log,
    )
    Base.metadata.drop_all(bind=engine)  # Drop all tables
    logger.info("Tables successfully dropped from '%s'.", target_db_name_for_log)

    logger.info("Attempting to create all tables in database: '%s'...", target_db_name_for_log)
    Base.metadata.create_all(bind=engine)
    logger.info("Tables successfully created in '%s'.", target_db_name_for_log)

    # Get a database session and seed the data
    db_session = session_local()
    try:
        seed_initial_data(db_session)
    finally:
        db_session.close()

    logger.info("Database setup and seeding complete.")


if __name__ == "__main__":
    main()