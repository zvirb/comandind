"""
This service manages interactions with the Google Calendar API, including creating,
updating, and retrieving events. It also uses an LLM to categorize events.
"""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncio
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource # type: ignore
from googleapiclient.errors import HttpError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState,
)

# --- Local Imports ---
from shared.database.models._models import Event as DBEvent, User, UserOAuthToken, GoogleService
from worker.celery_app import _db_state
from shared.utils.config import get_settings
from contextlib import contextmanager
from worker.event_models import (
    Event,
    Movability,
    TimePreferences,
)
from worker.services.ollama_service import invoke_llm
from worker.shared_constants import (
    SYSTEM_PROMPT_CATEGORIZE,
    DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY,
)

# --- Logging Setup ---
logger = logging.getLogger(__name__)

@contextmanager
def get_db_session():
    """Provides a transactional scope around a series of database operations."""
    if "session_factory" not in _db_state:
        raise RuntimeError("Database session factory not initialized in worker.")

    session = _db_state["session_factory"]()
    try:
        yield session
    finally:
        session.close()

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]


def _handle_retry_error(retry_state: RetryCallState) -> None:
    """Log the exception and re-raise to fail the task."""
    exception = (
        retry_state.outcome.exception() if retry_state.outcome else "Unknown error"
    )
    logger.error(
        "Google Calendar API call failed after %d attempts. Last exception: %s",
        retry_state.attempt_number,
        exception,
        exc_info=exception if isinstance(exception, BaseException) else None,
    )
    if isinstance(exception, BaseException):
        raise exception


async def get_calendar_service(user_id: int) -> Optional[Resource]:
    """
    Builds and returns a Google Calendar service object authenticated
    with the user's OAuth credentials.
    """
    logger.info("Building Google Calendar service for user_id: %s", user_id)
    try:
        # Get the user's OAuth token for Google Calendar
        logger.info("Opening database session to retrieve OAuth token for user_id: %s", user_id)
        with get_db_session() as db:
            oauth_token = db.query(UserOAuthToken).filter(
                UserOAuthToken.user_id == user_id,
                UserOAuthToken.service == GoogleService.CALENDAR
            ).first()
            
            logger.info("OAuth token query completed for user_id: %s, token found: %s", user_id, oauth_token is not None)
            
            if not oauth_token:
                logger.error(
                    "No Google Calendar OAuth token found for user_id: %s. "
                    "User needs to connect their Google Calendar first.",
                    user_id
                )
                return None
            
            # Check if token is expired and needs refresh
            now = datetime.now(timezone.utc)
            if oauth_token.token_expiry and oauth_token.token_expiry <= now:
                if oauth_token.refresh_token:
                    logger.info("OAuth token expired, attempting refresh for user_id: %s", user_id)
                    # Refresh the token
                    creds = Credentials(
                        token=oauth_token.access_token,
                        refresh_token=oauth_token.refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=get_settings().GOOGLE_CLIENT_ID,
                        client_secret=get_settings().GOOGLE_CLIENT_SECRET.get_secret_value()
                    )
                    await asyncio.to_thread(creds.refresh, Request())
                    
                    # Update the stored token
                    oauth_token.access_token = creds.token
                    oauth_token.token_expiry = creds.expiry
                    db.commit()
                    
                    logger.info("Successfully refreshed OAuth token for user_id: %s", user_id)
                else:
                    logger.error(
                        "OAuth token expired and no refresh token available for user_id: %s. "
                        "User needs to reconnect their Google Calendar.",
                        user_id
                    )
                    return None
            else:
                # Token is still valid
                creds = Credentials(
                    token=oauth_token.access_token,
                    refresh_token=oauth_token.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=get_settings().GOOGLE_CLIENT_ID,
                    client_secret=get_settings().GOOGLE_CLIENT_SECRET.get_secret_value()
                )
            
            service: Resource = build("calendar", "v3", credentials=creds)  # type: ignore
            logger.info("Successfully built Google Calendar service with OAuth credentials.")
            return service
            
    except Exception as e:
        logger.error("Failed to build Google Calendar service: %s", e, exc_info=True)
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError),
    retry_error_callback=_handle_retry_error,
)
async def list_calendar_events(
    service: Resource, calendar_id: str, time_min: str, time_max: str
) -> List[Dict[str, Any]]:
    """Lists events from a specified Google Calendar."""
    logger.info(
        "Listing events from calendar '%s' between %s and %s.",
        calendar_id,
        time_min,
        time_max,
    )
    events_result = await asyncio.to_thread( # type: ignore
        service.events()  # type: ignore
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute
    )
    return events_result.get("items", []) # type: ignore


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError),
    retry_error_callback=_handle_retry_error,
)
async def create_calendar_event(
    service: Resource, calendar_id: str, event_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Creates a new event in the specified Google Calendar."""
    logger.info("Creating new event in calendar '%s'.", calendar_id)
    created_event = await asyncio.to_thread( # type: ignore
        service.events().insert(calendarId=calendar_id, body=event_data).execute  # type: ignore
    )
    logger.info("Successfully created event with ID: %s", created_event.get("id")) #type: ignore
    return created_event # type: ignore


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError),
    retry_error_callback=_handle_retry_error,
)
async def update_calendar_event(
    service: Resource, calendar_id: str, event_id: str, event_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Updates an existing event in the specified Google Calendar."""
    logger.info("Updating event %s in calendar '%s'.", event_id, calendar_id)
    updated_event = await asyncio.to_thread( # type: ignore
        service.events()  # type: ignore
        .update(calendarId=calendar_id, eventId=event_id, body=event_data)
        .execute
    )
    logger.info("Successfully updated event with ID: %s", updated_event.get("id")) # type: ignore
    return updated_event # type: ignore

async def sync_events_from_google(user_id: int, calendar_id: str = "primary") -> None:
    """
    Fetches events from Google Calendar and syncs them with the local database.
    """
    logger.info(
        "Starting event sync for user_id: %s, calendar_id: %s.", user_id, calendar_id
    )
    service = await get_calendar_service(user_id)
    if not service:
        logger.error(
            "Could not get calendar service for user %s. Aborting sync.", user_id
        )
        return

    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=30)).isoformat()
    time_max = (now + timedelta(days=30)).isoformat()

    try:
        google_events = await list_calendar_events(
            service, calendar_id, time_min, time_max
        )
        if not google_events:
            logger.info("No events found in Google Calendar for the specified time range.")
            return

        with get_db_session() as db:
            try:
                for g_event in google_events:
                    event_id = g_event.get("id")
                    if not event_id:
                        continue

                    db_event = (
                        db.query(DBEvent)
                        .filter(DBEvent.google_event_id == event_id)
                        .first()
                    )
                    if not db_event:
                        logger.info(
                            "New Google event found: %s. Creating local record.", event_id
                        )
                        new_event = await _create_db_event_from_google_event(
                            g_event, user_id, calendar_id
                        )
                        db.add(new_event)
                db.commit()
            except SQLAlchemyError as e:
                logger.error("Error during database sync: %s", e, exc_info=True)
                db.rollback()
    except HttpError as e:
        logger.error("Failed to list calendar events: %s", e, exc_info=True)


async def _create_db_event_from_google_event(
    g_event: Dict[str, Any], user_id: int, calendar_id: str
) -> DBEvent:
    """Creates a local DBEvent object from a Google Calendar event dictionary."""
    start_time_dict = g_event.get("start", {})
    end_time_dict = g_event.get("end", {})

    start_time_str = start_time_dict.get("dateTime") or start_time_dict.get("date")
    end_time_str = end_time_dict.get("dateTime") or end_time_dict.get("date")
    duration_minutes = None
    start_time, end_time = None, None

    if start_time_str and end_time_str:
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        if start_time.tzinfo:
            start_time = start_time.astimezone(timezone.utc)
        if end_time.tzinfo:
            end_time = end_time.astimezone(timezone.utc)
        duration_delta = end_time - start_time
        duration_minutes = int(duration_delta.total_seconds() / 60)

    summary = g_event.get("summary", "No Title")
    description = g_event.get("description", "")

    # Get user's selected model
    settings = get_settings()
    selected_model = settings.OLLAMA_GENERATION_MODEL_NAME
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.settings and user.settings.get("selected_model"):
            selected_model = user.settings.get("selected_model")

    category = await _categorize_event(summary, description, selected_model)
    pref_window = DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY.get(category, {})
    time_prefs = TimePreferences(
        preferred_window_start=pref_window.get("start"),
        preferred_window_end=pref_window.get("end"),
    )
    movability = await _assess_movability(
        summary, description, time_prefs, duration_minutes
    )

    return DBEvent(
        user_id=user_id,
        calendar_id=calendar_id,
        google_event_id=g_event["id"],
        summary=summary,
        description=description,
        start_time=start_time,
        end_time=end_time,
        category=category,
        movability_score=movability.score,
        is_movable=movability.is_movable,
    )


async def _categorize_event(summary: str, description: str, selected_model: str) -> str:
    """Uses an LLM to categorize an event based on its summary and description."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_CATEGORIZE},
        {
            "role": "user",
            "content": f"Event Summary: {summary}\nEvent Description: {description}",
        },
    ]
    try:
        llm_response_raw = await invoke_llm(messages, model_name=selected_model)
        llm_guessed_category = llm_response_raw.strip().title()

        if llm_guessed_category in Event.get_available_categories():
            logger.info(
                "LLM categorized event '%s' as: %s", summary, llm_guessed_category
            )
            return llm_guessed_category
    except Exception as e:
        logger.warning(
            "LLM categorization failed for event '%s': %s. Falling back to Default.",
            summary,
            e,
        )
    return "Default"


async def _assess_movability(
    summary: str,
    description: str,
    time_prefs: TimePreferences,
    duration_minutes: Optional[int],
) -> Movability:
    """Uses an LLM to assess the movability of an event."""
    logger.info(
        "Assessing movability for event: '%s' (Duration: %s mins, Prefs: %s)",
        summary,
        duration_minutes,
        time_prefs,
    )
    # Suppress unused argument warnings for this placeholder function
    _ = description
    return Movability(score=0.5, is_movable=True, reason="Default movability assessment.")
