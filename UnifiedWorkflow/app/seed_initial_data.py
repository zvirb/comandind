"""
Seeds the database with initial data for development and testing.

This script is designed to be run as a one-off task during setup.
It populates the database with essential data like a default non-admin user,
and can be extended to seed other tables. It is idempotent.
"""
import sys
import logging
from typing import Dict

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from api.auth import get_password_hash, get_user_by_email
from api.utils.config import get_settings
from shared.database.models import (
    CategoryWeight,
    EventCategory,
    TimeBudget,
    User,
    UserRole,
    UserStatus,
)
from api.database_setup import Base

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _log_before_retry(retry_state: RetryCallState):
    """Logs a message before a retry attempt."""
    if retry_state.next_action is not None:
        logger.warning(
            "Database connection failed for seeder. Retrying in %s seconds... (attempt %d)",
            retry_state.next_action.sleep,
            retry_state.attempt_number,
        )


def seed_test_user(db: Session):
    """Creates a default non-admin user if one doesn't exist."""
    test_user_email = "user@example.com"
    if get_user_by_email(db, email=test_user_email):
        logger.info("Test user '%s' already exists. Skipping.", test_user_email)
        return

    logger.info("Creating test user: %s", test_user_email)
    hashed_password = get_password_hash("password")
    test_user = User(
        email=test_user_email,
        hashed_password=hashed_password,
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    db.add(test_user)
    logger.info("Successfully created test user: %s", test_user_email)


def seed_category_weights(db: Session):
    """Seeds the database with default category weights if they don't exist."""
    logger.info("Seeding category weights...")
    default_weights: Dict[EventCategory, float] = {
        EventCategory.WORK: 8.0,
        EventCategory.HEALTH: 9.0,
        EventCategory.LEISURE: 6.0,
        EventCategory.FAMILY: 7.0,
        EventCategory.FITNESS: 7.0,
        EventCategory.DEFAULT: 5.0,
    }
    for category, weight in default_weights.items():
        exists = (
            db.query(CategoryWeight).filter(CategoryWeight.category_name == category.value).first()
        )
        if not exists:
            new_weight = CategoryWeight(category_name=category.value, weight=weight)
            db.add(new_weight)
            logger.info("Added category weight: %s with weight %s", category.value, weight)
    logger.info("Category weight seeding check complete.")


def seed_time_budgets(db: Session):
    """Seeds the database with default weekly time budgets."""
    logger.info("Seeding time budgets...")
    default_budgets = {
        EventCategory.WORK: 40.0,
        EventCategory.HEALTH: 5.0,
        EventCategory.FITNESS: 3.0,
        EventCategory.LEISURE: 10.0,
        EventCategory.FAMILY: 10.0,
        EventCategory.DEFAULT: 0.0,
    }
    for category, hours in default_budgets.items():
        exists = (
            db.query(TimeBudget)
            .filter(TimeBudget.category_name == category.value, TimeBudget.period == "weekly")
            .first()
        )
        if not exists:
            new_budget = TimeBudget(
                category_name=category.value, budgeted_hours=hours, period="weekly"
            )
            db.add(new_budget)
            logger.info("Added weekly budget for '%s': %s hours", category.value, hours)
    logger.info("Time budget seeding check complete.")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(OperationalError),
    before_sleep=_log_before_retry,
)
def main():
    """
    Main function to initialize DB and seed initial data.
    """
    settings = get_settings()
    engine = create_engine(settings.database_url)

    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = session_local()
    try:
        logger.info("Seeding initial data...")
        seed_test_user(db_session)
        seed_category_weights(db_session)
        seed_time_budgets(db_session)
        db_session.commit()
        logger.info("Initial data seeding and commit complete.")
    except SQLAlchemyError as e:
        logger.error("An error occurred during data seeding: %s", e, exc_info=True)
        db_session.rollback()
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    try:
        main()
    except OperationalError as e:
        logger.critical(
            "Database connection failed for seeder after multiple retries: %s", e
        )
        sys.exit(1)
    except SQLAlchemyError as e:
        logger.critical(
            "A database error occurred during data seeding: %s", e, exc_info=True
        )
        sys.exit(1)