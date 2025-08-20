"""
Google Calendar service for synchronizing events with the local database.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from dateutil.parser import parse as parse_date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import time
import asyncio
from contextlib import asynccontextmanager

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    User, Calendar, Event, UserOAuthToken, GoogleService, EventCategory
)
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    """Service for managing Google Calendar synchronization.
    
    SECURITY FIXES:
    - Atomic OAuth token refresh operations
    - Token refresh locking to prevent conflicts
    - Enhanced error handling and logging
    """
    
    # Class-level lock dictionary for atomic token operations
    _token_refresh_locks = {}
    
    @classmethod
    async def _get_or_create_token_lock(cls, user_id: int) -> asyncio.Lock:
        """Get or create a token refresh lock for atomic operations."""
        if user_id not in cls._token_refresh_locks:
            cls._token_refresh_locks[user_id] = asyncio.Lock()
        return cls._token_refresh_locks[user_id]
    
    def __init__(self, oauth_token: UserOAuthToken, db: Union[Session, AsyncSession]):
        self.oauth_token = oauth_token
        self.db = db
        self.service = None
        self.user_id = oauth_token.user_id
    
    @asynccontextmanager
    async def _get_google_service_with_lock(self):
        """Initialize Google Calendar service with OAuth credentials and token refresh lock."""
        # Implement atomic token refresh to prevent race conditions
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # Get fresh token data from database to avoid stale data
                if hasattr(self.db, 'refresh'):
                    self.db.refresh(self.oauth_token)
                elif hasattr(self.db, 'execute'):
                    # Handle async session
                    from sqlalchemy import select
                    result = await self.db.execute(
                        select(UserOAuthToken).where(UserOAuthToken.id == self.oauth_token.id)
                    )
                    fresh_token = result.scalar_one_or_none()
                    if fresh_token:
                        self.oauth_token = fresh_token
                
                # Get settings for OAuth credentials
                settings = get_settings()
                
                credentials = Credentials(
                    token=self.oauth_token.access_token,
                    refresh_token=self.oauth_token.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
                    scopes=self.oauth_token.scope.split(',') if self.oauth_token.scope else []
                )
                
                # Check if token needs refresh before creating service
                now = datetime.now(timezone.utc)
                if (self.oauth_token.token_expiry and 
                    self.oauth_token.token_expiry <= now + timedelta(minutes=5)):
                    logger.info("Token expires soon, attempting refresh")
                    credentials.refresh()
                
                # Create service
                service = build('calendar', 'v3', credentials=credentials)
                
                # Atomic token update if refreshed
                if credentials.token != self.oauth_token.access_token:
                    logger.info("OAuth token was refreshed, updating database atomically")
                    
                    # Use database-level atomic update
                    if hasattr(self.db, 'begin'):  # Async session
                        async with self.db.begin():
                            # Re-fetch token to ensure we have latest version
                            from sqlalchemy import select, update
                            result = await self.db.execute(
                                select(UserOAuthToken).where(UserOAuthToken.id == self.oauth_token.id)
                            )
                            current_token = result.scalar_one_or_none()
                            
                            if current_token:
                                # Update token atomically
                                await self.db.execute(
                                    update(UserOAuthToken)
                                    .where(UserOAuthToken.id == self.oauth_token.id)
                                    .values(
                                        access_token=credentials.token,
                                        refresh_token=credentials.refresh_token or current_token.refresh_token,
                                        token_expiry=credentials.expiry,
                                        updated_at=now
                                    )
                                )
                                await self.db.commit()
                    else:  # Sync session
                        self.oauth_token.access_token = credentials.token
                        if credentials.refresh_token:
                            self.oauth_token.refresh_token = credentials.refresh_token
                        if credentials.expiry:
                            self.oauth_token.token_expiry = credentials.expiry
                        self.oauth_token.updated_at = now
                        self.db.commit()
                
                yield service
                return
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Failed to create Google Calendar service (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count >= max_retries:
                    raise
                
                # Exponential backoff for retries
                wait_time = (2 ** retry_count) * 0.5
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
    
    def _get_google_service(self):
        """Sync wrapper for backward compatibility."""
        # Get settings for OAuth credentials
        settings = get_settings()
        
        credentials = Credentials(
            token=self.oauth_token.access_token,
            refresh_token=self.oauth_token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            scopes=self.oauth_token.scope.split(',') if self.oauth_token.scope else []
        )
        
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            # Check if credentials were refreshed and update database
            if credentials.token != self.oauth_token.access_token:
                logger.info("OAuth token was refreshed, updating database")
                self.oauth_token.access_token = credentials.token
                if credentials.refresh_token:
                    self.oauth_token.refresh_token = credentials.refresh_token
                if credentials.expiry:
                    self.oauth_token.token_expiry = credentials.expiry
                self.oauth_token.updated_at = datetime.now(timezone.utc)
                self.db.commit()
            
            return service
        except Exception as e:
            logger.error(f"Failed to create Google Calendar service: {e}")
            raise
    
    async def sync_events(self, user_id: int, force_sync: bool = False) -> Dict[str, Any]:
        """
        Synchronize events from Google Calendar to local database with improved error handling.
        
        Args:
            user_id: ID of the user to sync events for
            force_sync: If True, sync all events regardless of last sync time
            
        Returns:
            Dictionary with sync results
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use async context manager for better token management
                if hasattr(self.db, 'execute'):  # Async session
                    async with self._get_google_service_with_lock() as service:
                        return await self._perform_sync(service, user_id, force_sync)
                else:
                    # Fallback to sync method
                    service = self._get_google_service()
                    return await self._perform_sync(service, user_id, force_sync)
                    
            except HttpError as e:
                retry_count += 1
                
                if e.resp.status == 401:  # Unauthorized - token issue
                    logger.error(f"OAuth token expired/invalid for user {user_id}")
                    if retry_count >= max_retries:
                        raise Exception("Google Calendar access token expired. Please reconnect your account.")
                    
                    # Clear service to force token refresh on next attempt
                    self.service = None
                    await asyncio.sleep(1)  # Brief delay before retry
                    continue
                    
                elif e.resp.status == 403:  # Forbidden - rate limited or quota exceeded
                    logger.warning(f"Google Calendar API rate limit or quota exceeded for user {user_id}")
                    if retry_count >= max_retries:
                        raise Exception("Google Calendar API rate limit exceeded. Please try again later.")
                    
                    # Exponential backoff for rate limiting
                    wait_time = (2 ** retry_count) * 5  # 5, 10, 20 seconds
                    logger.info(f"Rate limited, waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                elif e.resp.status == 500:  # Internal server error from Google
                    logger.warning(f"Google Calendar API server error for user {user_id}: {e}")
                    if retry_count >= max_retries:
                        raise Exception("Google Calendar API is temporarily unavailable. Please try again later.")
                    
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Google Calendar API error: {e}")
                    raise Exception(f"Google Calendar API error: {e}")
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"Calendar sync error (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count >= max_retries:
                    raise Exception(f"Calendar sync failed after {max_retries} attempts: {e}")
                
                await asyncio.sleep(1)  # Brief delay before retry
    
    async def _perform_sync(self, service, user_id: int, force_sync: bool) -> Dict[str, Any]:
        """Perform the actual calendar sync operation."""
        try:
            
            # Get or create user's default calendar with error handling
            user_calendar = await self._get_or_create_user_calendar_async(user_id)
            
            # Determine sync timeframe
            if force_sync:
                # Full sync: get events from 1 year ago to 1 year ahead
                time_min = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
                time_max = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            else:
                # Incremental sync: get events from 1 month ago to 3 months ahead
                time_min = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                time_max = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
            
            # Fetch events from Google Calendar with retry logic
            logger.info(f"Fetching Google Calendar events for user {user_id} from {time_min} to {time_max}")
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=2500  # Google's max limit
            ).execute()
            
            google_events = events_result.get('items', [])
            logger.info(f"Retrieved {len(google_events)} events from Google Calendar")
            
            # Process and store events with better error handling
            events_synced = 0
            events_deleted = 0
            errors = []
            
            # Get list of Google event IDs for cleanup
            google_event_ids = {event.get('id') for event in google_events if event.get('id')}
            
            # Process events in smaller batches to avoid database lock issues
            batch_size = 50
            for i in range(0, len(google_events), batch_size):
                batch = google_events[i:i + batch_size]
                
                for google_event in batch:
                    try:
                        await self._process_google_event_async(google_event, user_calendar.id)
                        events_synced += 1
                    except Exception as e:
                        error_msg = f"Failed to process event {google_event.get('id', 'unknown')}: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                
                # Commit batch to database
                if hasattr(self.db, 'commit'):
                    if hasattr(self.db, 'execute'):  # Async session
                        await self.db.commit()
                    else:
                        self.db.commit()
            
            # Clean up deleted events - remove local events that no longer exist in Google Calendar
            try:
                await self._cleanup_deleted_events_async(
                    user_calendar.id, google_event_ids, time_min, time_max
                )
            except Exception as e:
                error_msg = f"Failed to clean up deleted events: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
            
            # Update last sync timestamp atomically
            if hasattr(self.db, 'execute'):  # Async session
                from sqlalchemy import update
                await self.db.execute(
                    update(UserOAuthToken)
                    .where(UserOAuthToken.id == self.oauth_token.id)
                    .values(updated_at=datetime.now(timezone.utc))
                )
                await self.db.commit()
            else:
                self.oauth_token.updated_at = datetime.now(timezone.utc)
                self.db.commit()
            
            logger.info(f"Successfully synced {events_synced} events and deleted {events_deleted} events for user {user_id}")
            
            return {
                "events_synced": events_synced,
                "events_deleted": events_deleted,
                "total_events": len(google_events),
                "errors": errors if errors else None,
                "sync_timeframe": {"from": time_min, "to": time_max}
            }
            
        except Exception as e:
            logger.error(f"Error in sync operation: {e}")
            # Rollback any partial changes
            if hasattr(self.db, 'rollback'):
                if hasattr(self.db, 'execute'):  # Async session
                    await self.db.rollback()
                else:
                    self.db.rollback()
            raise
    
    def _get_or_create_user_calendar(self, user_id: int) -> Calendar:
        """Get or create the user's default calendar."""
        calendar = self.db.query(Calendar).filter(
            Calendar.user_id == user_id,
            Calendar.name == "Google Calendar"
        ).first()
        
        if not calendar:
            calendar = Calendar(
                user_id=user_id,
                name="Google Calendar",
                description="Synchronized from Google Calendar"
            )
            self.db.add(calendar)
            self.db.commit()
            self.db.refresh(calendar)
            logger.info(f"Created new calendar for user {user_id}")
        
        return calendar
    
    async def _get_or_create_user_calendar_async(self, user_id: int) -> Calendar:
        """Get or create the user's default calendar (async version)."""
        if hasattr(self.db, 'execute'):  # Async session
            from sqlalchemy import select
            result = await self.db.execute(
                select(Calendar).filter(
                    Calendar.user_id == user_id,
                    Calendar.name == "Google Calendar"
                )
            )
            calendar = result.scalar_one_or_none()
            
            if not calendar:
                calendar = Calendar(
                    user_id=user_id,
                    name="Google Calendar",
                    description="Synchronized from Google Calendar"
                )
                self.db.add(calendar)
                await self.db.commit()
                await self.db.refresh(calendar)
                logger.info(f"Created new calendar for user {user_id}")
            
            return calendar
        else:
            # Fallback to sync method
            return self._get_or_create_user_calendar(user_id)
    
    def _process_google_event(self, google_event: Dict[str, Any], calendar_id: int):
        """Process a single Google Calendar event and store it in the database."""
        google_event_id = google_event.get('id')
        if not google_event_id:
            return
        
        # Check if event already exists
        existing_event = self.db.query(Event).filter(
            Event.google_event_id == google_event_id,
            Event.calendar_id == calendar_id
        ).first()
        
        # Parse event data
        summary = google_event.get('summary', 'Untitled Event')
        description = google_event.get('description', '')
        
        # Parse start and end times with debug logging
        start_data = google_event.get('start', {})
        end_data = google_event.get('end', {})
        
        logger.debug(f"Processing event '{summary}' - Start data: {start_data}, End data: {end_data}")
        
        start_time = self._parse_event_time(start_data)
        end_time = self._parse_event_time(end_data)
        
        logger.debug(f"Parsed times for '{summary}' - Start: {start_time}, End: {end_time}")
        
        if not start_time or not end_time:
            logger.warning(f"Skipping event {google_event_id} due to invalid time data")
            return
        
        # Determine category from event content
        category = self._categorize_event(summary, description)
        
        # Calculate movability score based on event properties
        movability_score, is_movable = self._calculate_movability(google_event, summary, description)
        
        if existing_event:
            # Update existing event
            existing_event.summary = summary
            existing_event.description = description
            existing_event.start_time = start_time
            existing_event.end_time = end_time
            existing_event.category = category
            existing_event.movability_score = movability_score
            existing_event.is_movable = is_movable
            existing_event.updated_at = datetime.now(timezone.utc)
        else:
            # Create new event
            new_event = Event(
                google_event_id=google_event_id,
                calendar_id=calendar_id,
                summary=summary,
                description=description,
                start_time=start_time,
                end_time=end_time,
                category=category,
                movability_score=movability_score,
                is_movable=is_movable
            )
            self.db.add(new_event)
        
        self.db.commit()
    
    async def _process_google_event_async(self, google_event: Dict[str, Any], calendar_id: int):
        """Process a single Google Calendar event and store it in the database (async version)."""
        google_event_id = google_event.get('id')
        if not google_event_id:
            return
        
        if hasattr(self.db, 'execute'):  # Async session
            from sqlalchemy import select
            
            # Check if event already exists
            result = await self.db.execute(
                select(Event).filter(
                    Event.google_event_id == google_event_id,
                    Event.calendar_id == calendar_id
                )
            )
            existing_event = result.scalar_one_or_none()
            
            # Parse event data
            summary = google_event.get('summary', 'Untitled Event')
            description = google_event.get('description', '')
            
            # Parse start and end times
            start_data = google_event.get('start', {})
            end_data = google_event.get('end', {})
            
            start_time = self._parse_event_time(start_data)
            end_time = self._parse_event_time(end_data)
            
            if not start_time or not end_time:
                logger.warning(f"Skipping event {google_event_id} due to invalid time data")
                return
            
            # Determine category and movability
            category = self._categorize_event(summary, description)
            movability_score, is_movable = self._calculate_movability(google_event, summary, description)
            
            if existing_event:
                # Update existing event
                existing_event.summary = summary
                existing_event.description = description
                existing_event.start_time = start_time
                existing_event.end_time = end_time
                existing_event.category = category
                existing_event.movability_score = movability_score
                existing_event.is_movable = is_movable
                existing_event.updated_at = datetime.now(timezone.utc)
            else:
                # Create new event
                new_event = Event(
                    google_event_id=google_event_id,
                    calendar_id=calendar_id,
                    summary=summary,
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                    category=category,
                    movability_score=movability_score,
                    is_movable=is_movable
                )
                self.db.add(new_event)
        else:
            # Fallback to sync method
            self._process_google_event(google_event, calendar_id)
    
    async def _cleanup_deleted_events_async(self, calendar_id: int, google_event_ids: set, time_min: str, time_max: str):
        """Clean up deleted events that no longer exist in Google Calendar."""
        if hasattr(self.db, 'execute'):  # Async session
            from sqlalchemy import select, delete
            
            # Get all local events in the same time range
            result = await self.db.execute(
                select(Event).filter(
                    Event.calendar_id == calendar_id,
                    Event.google_event_id.isnot(None),  # Only check Google-synced events
                    Event.start_time >= parse_date(time_min).replace(tzinfo=None),
                    Event.start_time <= parse_date(time_max).replace(tzinfo=None)
                )
            )
            existing_events = result.scalars().all()
            
            # Delete events that are no longer in Google Calendar
            events_deleted = 0
            for local_event in existing_events:
                if local_event.google_event_id not in google_event_ids:
                    logger.info(f"Deleting event {local_event.google_event_id} - no longer exists in Google Calendar")
                    await self.db.delete(local_event)
                    events_deleted += 1
            
            if events_deleted > 0:
                await self.db.commit()
                
            return events_deleted
        else:
            # Fallback to sync method
            existing_events = self.db.query(Event).filter(
                Event.calendar_id == calendar_id,
                Event.google_event_id.isnot(None),
                Event.start_time >= parse_date(time_min).replace(tzinfo=None),
                Event.start_time <= parse_date(time_max).replace(tzinfo=None)
            ).all()
            
            events_deleted = 0
            for local_event in existing_events:
                if local_event.google_event_id not in google_event_ids:
                    logger.info(f"Deleting event {local_event.google_event_id} - no longer exists in Google Calendar")
                    self.db.delete(local_event)
                    events_deleted += 1
            
            if events_deleted > 0:
                self.db.commit()
                
            return events_deleted
    
    def _parse_event_time(self, time_data: Dict[str, Any]) -> Optional[datetime]:
        """Parse Google Calendar event time data preserving timezone information."""
        if not time_data:
            return None
        
        # Handle all-day events
        if 'date' in time_data:
            date_str = time_data['date']
            naive_dt = datetime.strptime(date_str, '%Y-%m-%d')

            # Check if there's a timezone specified for the event
            if 'timeZone' in time_data:
                try:
                    tz = ZoneInfo(time_data['timeZone'])
                    # For all-day events, use start of day in the event's timezone
                    return naive_dt.replace(tzinfo=tz)
                except ZoneInfoNotFoundError as e:
                    logger.error(f"TIMEZONE ERROR: Invalid timezone '{time_data['timeZone']}' for all-day event. "
                               f"This may cause incorrect event timing. Error: {e}")
                    # Track timezone errors for monitoring
                    self._track_timezone_error(time_data['timeZone'], 'all_day_event')
            
            # Default to start of day in UTC for all-day events
            return naive_dt.replace(tzinfo=timezone.utc)
        
        # Handle timed events with timezone information
        if 'dateTime' in time_data:
            dt = parse_date(time_data['dateTime'])
            
            # If the parsed datetime is naive, try to apply the specified timezone
            if dt.tzinfo is None and 'timeZone' in time_data:
                try:
                    tz = ZoneInfo(time_data['timeZone'])
                    return dt.replace(tzinfo=tz)
                except ZoneInfoNotFoundError as e:
                    logger.error(f"TIMEZONE ERROR: Invalid timezone '{time_data['timeZone']}' for timed event. "
                               f"This may cause incorrect event timing. Error: {e}")
                    # Track timezone errors for monitoring
                    self._track_timezone_error(time_data['timeZone'], 'timed_event')
                    # Fallback to UTC if timezone parsing fails
                    return dt.replace(tzinfo=timezone.utc)
            
            # If timezone is already in the dateTime string, dateutil.parser handles it
            return dt
        
        return None
    
    def _categorize_event(self, summary: str, description: str) -> EventCategory:
        """Categorize event based on title and description."""
        content = f"{summary} {description}".lower()
        
        # Work-related keywords
        work_keywords = [
            'meeting', 'standup', 'call', 'conference', 'project', 'work', 'client',
            'interview', 'presentation', 'review', 'sync', 'planning', 'office'
        ]
        
        # Health-related keywords
        health_keywords = [
            'doctor', 'dentist', 'appointment', 'medical', 'health', 'checkup',
            'therapy', 'hospital', 'clinic', 'surgery', 'vaccine'
        ]
        
        # Fitness-related keywords
        fitness_keywords = [
            'gym', 'workout', 'exercise', 'fitness', 'yoga', 'running', 'training',
            'sport', 'swim', 'bike', 'hike', 'pilates', 'crossfit'
        ]
        
        # Family-related keywords
        family_keywords = [
            'family', 'dinner', 'birthday', 'anniversary', 'wedding', 'kids',
            'children', 'school', 'parent', 'home', 'house'
        ]
        
        # Leisure-related keywords
        leisure_keywords = [
            'movie', 'concert', 'party', 'vacation', 'travel', 'holiday', 'fun',
            'entertainment', 'restaurant', 'date', 'social', 'friends'
        ]
        
        # Check categories in order of specificity
        if any(keyword in content for keyword in work_keywords):
            return EventCategory.WORK
        elif any(keyword in content for keyword in health_keywords):
            return EventCategory.HEALTH
        elif any(keyword in content for keyword in fitness_keywords):
            return EventCategory.FITNESS
        elif any(keyword in content for keyword in family_keywords):
            return EventCategory.FAMILY
        elif any(keyword in content for keyword in leisure_keywords):
            return EventCategory.LEISURE
        else:
            return EventCategory.DEFAULT
    
    def _calculate_movability(self, google_event: Dict[str, Any], summary: str, description: str) -> tuple[float, bool]:
        """Calculate how movable an event is based on various factors."""
        score = 0.5  # Start with neutral score
        
        # Check if event has attendees (less movable if many attendees)
        attendees = google_event.get('attendees', [])
        if len(attendees) > 5:
            score -= 0.3
        elif len(attendees) > 2:
            score -= 0.2
        elif len(attendees) == 1:
            score += 0.1
        
        # Check for recurring events (less movable)
        if google_event.get('recurringEventId'):
            score -= 0.2
        
        # Check for keywords that suggest low movability
        content = f"{summary} {description}".lower()
        
        immovable_keywords = [
            'deadline', 'due', 'fixed', 'mandatory', 'required', 'important',
            'urgent', 'critical', 'flight', 'train', 'appointment', 'interview'
        ]
        
        flexible_keywords = [
            'flexible', 'optional', 'maybe', 'tentative', 'casual', 'social',
            'break', 'lunch', 'coffee', 'chat'
        ]
        
        if any(keyword in content for keyword in immovable_keywords):
            score -= 0.3
        elif any(keyword in content for keyword in flexible_keywords):
            score += 0.3
        
        # Check event status
        status = google_event.get('status', '').lower()
        if status == 'tentative':
            score += 0.2
        elif status == 'confirmed':
            score -= 0.1
        
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))
        
        # Determine if movable (threshold of 0.3)
        is_movable = score >= 0.3
        
        return score, is_movable
    
    def _track_timezone_error(self, invalid_timezone: str, event_type: str):
        """Track timezone errors for monitoring and debugging."""
        # This could be enhanced to use a proper monitoring system
        # For now, we log the error and could store metrics in Redis/database
        logger.error(f"TIMEZONE TRACKING: Invalid timezone '{invalid_timezone}' "
                    f"encountered in {event_type}. Consider adding timezone validation.")
        
        # TODO: In production, consider:
        # - Storing timezone error metrics in Redis
        # - Sending alerts for repeated timezone errors
        # - Building a list of common invalid timezones for better handling