"""
Calendar router for managing calendar events and Google Calendar synchronization.
Enhanced with comprehensive monitoring and error tracking.
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from shared.utils.database_setup import get_async_session
from shared.database.models import User, Calendar, Event, UserOAuthToken, GoogleService, UserCategory
from api.dependencies import get_current_user, verify_csrf_token
from shared.schemas.calendar_schemas import Event as EventSchema
from api.services.google_calendar_service import GoogleCalendarService
from api.services.ai_event_analysis_service import AIEventAnalysisService
from api.services.oauth_token_manager import get_oauth_token_manager
from shared.monitoring.calendar_sync_monitoring import (
    calendar_sync_monitor, start_calendar_sync_monitoring, finish_calendar_sync_monitoring,
    CalendarSyncStatus, ErrorPattern
)

logger = logging.getLogger(__name__)

router = APIRouter()

class CalendarSyncRequest(BaseModel):
    """Request model for calendar synchronization."""
    force_sync: bool = False

class CalendarSyncResponse(BaseModel):
    """Response model for calendar synchronization."""
    status: str
    events_synced: int
    last_sync: datetime
    errors: Optional[List[str]] = None

class ConversationMessage(BaseModel):
    """Model for conversation messages."""
    role: str
    content: str
    timestamp: datetime

class AIEventAnalysisRequest(BaseModel):
    """Request model for AI event analysis."""
    conversation: List[ConversationMessage]
    timeSlot: Dict[str, str]
    userCategories: List[Dict[str, Any]]

class AIEventAnalysisResponse(BaseModel):
    """Response model for AI event analysis."""
    needsMoreInfo: bool
    question: Optional[str] = None
    eventDetails: Optional[Dict[str, Any]] = None

class EventCreateRequest(BaseModel):
    """Request model for creating calendar events."""
    title: str
    description: Optional[str] = None
    start: str
    end: str
    category: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    priority: Optional[int] = 3

@router.get("/calendars")
async def get_user_calendars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """Get all calendars for the current user."""
    from sqlalchemy import select
    result = await db.execute(select(Calendar).filter(Calendar.user_id == current_user.id))
    calendars = result.scalars().all()
    
    return [
        {
            "id": calendar.id,
            "name": calendar.name,
            "description": calendar.description,
            "event_count": len(calendar.events)
        }
        for calendar in calendars
    ]

@router.get("/events")
async def get_calendar_events(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    """Get calendar events for the current user within a date range."""
    
    # Parse dates or use defaults
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start_dt = datetime.now(timezone.utc) - timedelta(days=30)
    
    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        end_dt = datetime.now(timezone.utc) + timedelta(days=30)
    
    # Get user's calendars
    from sqlalchemy import select
    result = await db.execute(select(Calendar).filter(Calendar.user_id == current_user.id))
    user_calendars = result.scalars().all()
    calendar_ids = [cal.id for cal in user_calendars]
    
    if not calendar_ids:
        return []
    
    # Get events within date range
    from sqlalchemy import select
    result = await db.execute(select(Event).filter(
        Event.calendar_id.in_(calendar_ids),
        Event.start_time >= start_dt,
        Event.end_time <= end_dt
    ).order_by(Event.start_time))
    events = result.scalars().all()
    
    # Get user's timezone preference (default to UTC if not set)
    user_timezone_str = current_user.timezone or "UTC"
    try:
        user_timezone = ZoneInfo(user_timezone_str)
    except ZoneInfoNotFoundError:
        logger.warning(f"Invalid timezone '{user_timezone_str}' for user {current_user.id}, using UTC")
        user_timezone = ZoneInfo("UTC")
    
    def convert_time_to_user_timezone(dt: datetime) -> str:
        """Convert datetime to user's timezone and return ISO string"""
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to user's timezone
        user_dt = dt.astimezone(user_timezone)
        return user_dt.isoformat()
    
    return [
        {
            "id": event.id,
            "title": event.summary,
            "start": convert_time_to_user_timezone(event.start_time),
            "end": convert_time_to_user_timezone(event.end_time),
            "description": event.description,
            "category": event.category.value,
            "is_movable": event.is_movable,
            "movability_score": event.movability_score,
            "google_event_id": event.google_event_id,
            "backgroundColor": await get_category_color(event.category.value, current_user.id, db),
            "textColor": "white"
        }
        for event in events
    ]

@router.post("/sync", dependencies=[Depends(verify_csrf_token)])
async def sync_google_calendar(
    request: CalendarSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> CalendarSyncResponse:
    """Synchronize events from Google Calendar with enhanced error handling and token refresh."""
    
    # Check if user has Google Calendar connected
    from sqlalchemy import select
    result = await db.execute(select(UserOAuthToken).filter(
        UserOAuthToken.user_id == current_user.id,
        UserOAuthToken.service == GoogleService.CALENDAR
    ))
    oauth_token = result.scalars().first()
    
    if not oauth_token:
        raise HTTPException(
            status_code=400,
            detail="Google Calendar is not connected. Please connect your Google Calendar first."
        )
    
    # Use OAuth token manager for proactive refresh and health checking
    token_manager = get_oauth_token_manager(db)
    healthy_token = await token_manager.get_healthy_token(
        user_id=current_user.id,
        service=GoogleService.CALENDAR,
        auto_refresh=True
    )
    
    if not healthy_token:
        raise HTTPException(
            status_code=401,
            detail="Your Google Calendar authentication has expired. Please reconnect your account."
        )
    
    # Update oauth_token reference to the healthy token
    oauth_token = healthy_token
    
    try:
        # Initialize Google Calendar service with enhanced error handling
        calendar_service = GoogleCalendarService(oauth_token, db)
        
        # Perform synchronization with resilience patterns
        sync_result = await _perform_resilient_sync(
            calendar_service, 
            current_user.id, 
            force_sync=request.force_sync
        )
        
        # Determine status based on errors
        has_errors = sync_result.get("errors") and len(sync_result["errors"]) > 0
        status = "success" if not has_errors else "partial_success"
        
        return CalendarSyncResponse(
            status=status,
            events_synced=sync_result.get("events_synced", 0),
            last_sync=datetime.now(timezone.utc),
            errors=sync_result.get("errors") if has_errors else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync Google Calendar for user {current_user.id}: {e}")
        
        # Classify error and provide user-friendly response
        error_type = _classify_error_type(e)
        error_message = _get_user_friendly_error_message(e)
        
        # Return appropriate status code based on error type
        if error_type == "authentication_expired":
            status_code = 401
        elif error_type == "rate_limited":
            status_code = 429
        elif error_type == "external_service_error":
            status_code = 502  # Bad Gateway
        elif error_type == "network_error":
            status_code = 503  # Service Unavailable
        else:
            status_code = 500  # Internal Server Error
        
        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )

@router.get("/sync/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """Get the status of Google Calendar synchronization."""
    
    # Check if user has Google Calendar connected
    from sqlalchemy import select
    result = await db.execute(select(UserOAuthToken).filter(
        UserOAuthToken.user_id == current_user.id,
        UserOAuthToken.service == GoogleService.CALENDAR
    ))
    oauth_token = result.scalars().first()
    
    if not oauth_token:
        return {
            "connected": False,
            "last_sync": None,
            "total_events": 0
        }
    
    # Get user's calendars and events
    result = await db.execute(select(Calendar).filter(Calendar.user_id == current_user.id))
    user_calendars = result.scalars().all()
    total_events = sum(len(cal.events) for cal in user_calendars)
    
    # Get last sync time from token update time
    last_sync = oauth_token.updated_at if oauth_token.updated_at else oauth_token.created_at
    
    return {
        "connected": True,
        "last_sync": last_sync.isoformat() if last_sync else None,
        "total_events": total_events,
        "calendars_count": len(user_calendars)
    }

@router.post("/sync/auto", dependencies=[Depends(verify_csrf_token)])
async def trigger_auto_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """Trigger automatic synchronization with enhanced monitoring and error detection."""
    
    # Start monitoring
    sync_metrics = start_calendar_sync_monitoring(
        user_id=current_user.id,
        endpoint="/api/v1/calendar/sync/auto"
    )
    
    try:
        # Check if user has Google Calendar connected
        from sqlalchemy import select
        result = await db.execute(select(UserOAuthToken).filter(
            UserOAuthToken.user_id == current_user.id,
            UserOAuthToken.service == GoogleService.CALENDAR
        ))
        oauth_token = result.scalars().first()
        
        if not oauth_token:
            finish_calendar_sync_monitoring(
                sync_metrics, 
                CalendarSyncStatus.FAILURE, 
                "Google Calendar not connected"
            )
            return {"status": "no_connection", "message": "Google Calendar not connected"}
        
        # Use OAuth token manager for proactive refresh and health checking
        token_manager = get_oauth_token_manager(db)
        healthy_token = await token_manager.get_healthy_token(
            user_id=current_user.id,
            service=GoogleService.CALENDAR,
            auto_refresh=True
        )
        
        if not healthy_token:
            finish_calendar_sync_monitoring(
                sync_metrics, 
                CalendarSyncStatus.AUTH_ERROR, 
                "OAuth token unavailable or expired"
            )
            return {
                "status": "token_unavailable",
                "message": "Please reconnect your Google Calendar - authentication expired or unavailable"
            }
    
        # Update oauth_token reference to the healthy token
        oauth_token = healthy_token
        
        # Check if sync is needed (last sync more than 1 hour ago)
        last_sync = oauth_token.updated_at if oauth_token.updated_at else oauth_token.created_at
        now = datetime.now(timezone.utc)
        
        if last_sync and (now - last_sync).total_seconds() < 3600:  # 1 hour
            finish_calendar_sync_monitoring(
                sync_metrics, 
                CalendarSyncStatus.SUCCESS, 
                "Recently synced, skipping"
            )
            return {"status": "recent_sync", "message": "Recently synced, skipping"}
        
        # Circuit breaker pattern - check for recent failures
        failure_count = await _get_sync_failure_count(current_user.id, db)
        if failure_count >= 3:
            last_failure = await _get_last_sync_failure_time(current_user.id, db)
            if last_failure and (now - last_failure).total_seconds() < 1800:  # 30 minutes
                finish_calendar_sync_monitoring(
                    sync_metrics, 
                    CalendarSyncStatus.CIRCUIT_BREAKER_OPEN, 
                    f"Circuit breaker open due to {failure_count} consecutive failures"
                )
                return {
                    "status": "circuit_breaker_open",
                    "message": "Sync temporarily disabled due to repeated failures. Try again later."
                }
            else:
                # Reset failure count after cooldown period
                await _reset_sync_failure_count(current_user.id, db)
        
        # Initialize Google Calendar service with improved error handling
        calendar_service = GoogleCalendarService(oauth_token, db)
        
        # Perform background sync with retry logic
        sync_result = await _perform_resilient_sync(
            calendar_service, current_user.id, force_sync=False
        )
        
        # Reset failure count on success
        await _reset_sync_failure_count(current_user.id, db)
        
        # Finish monitoring with success
        finish_calendar_sync_monitoring(
            sync_metrics,
            CalendarSyncStatus.SUCCESS,
            events_synced=sync_result.get("events_synced", 0),
            retry_count=sync_result.get("retry_count", 0)
        )
        
        return {
            "status": "synced",
            "message": f"Synced {sync_result['events_synced']} events",
            "details": {
                "events_synced": sync_result.get("events_synced", 0),
                "errors": sync_result.get("errors", [])
            }
        }
        
    except Exception as e:
        # Enhanced error detection and classification
        error_message = str(e)
        
        # Detect specific database schema errors
        status = CalendarSyncStatus.FAILURE
        if "column" in error_message.lower() and "does not exist" in error_message.lower():
            status = CalendarSyncStatus.SCHEMA_ERROR
        elif "user_oauth_tokens.scope" in error_message.lower():
            status = CalendarSyncStatus.SCHEMA_ERROR
        elif "undefinedcolumn" in error_message.lower() or "programmingerror" in error_message.lower():
            status = CalendarSyncStatus.SCHEMA_ERROR
        elif "expired" in error_message.lower() or "unauthorized" in error_message.lower():
            status = CalendarSyncStatus.AUTH_ERROR
        elif "timeout" in error_message.lower():
            status = CalendarSyncStatus.TIMEOUT
        
        # Record failure for circuit breaker
        await _record_sync_failure(current_user.id, error_message, db)
        
        # Finish monitoring with error
        finish_calendar_sync_monitoring(
            sync_metrics,
            status,
            error_message
        )
        
        logger.error(f"Auto-sync failed for user {current_user.id}: {e}")
        
        # Provide helpful error messages instead of generic 500 error
        user_friendly_message = _get_user_friendly_error_message(e)
        
        return {
            "status": "error",
            "message": user_friendly_message,
            "error_type": _classify_error_type(e)
        }


@router.get("/sync/health")
async def get_calendar_sync_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get calendar sync health statistics and monitoring data."""
    try:
        # Get overall health statistics
        health_stats = calendar_sync_monitor.get_sync_statistics(hours=24)
        
        # Get user-specific statistics
        user_stats = calendar_sync_monitor.get_sync_statistics(
            user_id=current_user.id, 
            hours=24
        )
        
        # Get recent schema errors
        recent_schema_errors = calendar_sync_monitor.get_recent_schema_errors(limit=5)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_health": health_stats,
            "user_health": user_stats,
            "recent_schema_errors": recent_schema_errors,
            "monitoring_active": True
        }
    
    except Exception as e:
        logger.error(f"Failed to get calendar sync health: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "monitoring_active": False
        }


@router.get("/sync/metrics")
async def get_calendar_sync_metrics(
    hours: int = Query(24, ge=1, le=168, description="Hours of data to retrieve"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed calendar sync metrics for monitoring dashboard."""
    try:
        # Get comprehensive statistics
        metrics_data = calendar_sync_monitor.get_sync_statistics(
            user_id=current_user.id,
            hours=hours
        )
        
        # Add circuit breaker status
        failure_count = calendar_sync_monitor.user_failure_counts.get(current_user.id, 0)
        circuit_breaker_open = failure_count >= 3
        
        metrics_data.update({
            "circuit_breaker": {
                "open": circuit_breaker_open,
                "consecutive_failures": failure_count,
                "threshold": 3
            },
            "time_window_hours": hours,
            "user_id": current_user.id
        })
        
        return metrics_data
    
    except Exception as e:
        logger.error(f"Failed to get calendar sync metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


async def _refresh_oauth_token(oauth_token: UserOAuthToken, db: AsyncSession) -> Dict[str, Any]:
    """Refresh an expired or expiring OAuth token."""
    try:
        from shared.utils.config import get_settings
        import httpx
        
        settings = get_settings()
        settings.load_google_oauth_from_secrets()
        
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return {"success": False, "error": "OAuth configuration missing"}
        
        if not oauth_token.refresh_token:
            return {"success": False, "error": "No refresh token available"}
        
        refresh_params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            "refresh_token": oauth_token.refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=refresh_params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Update token atomically
                from sqlalchemy import update
                await db.execute(
                    update(UserOAuthToken)
                    .where(UserOAuthToken.id == oauth_token.id)
                    .values(
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token", oauth_token.refresh_token),
                        token_expiry=datetime.now(timezone.utc) + timedelta(
                            seconds=token_data.get("expires_in", 3600)
                        ),
                        updated_at=datetime.now(timezone.utc)
                    )
                )
                await db.commit()
                
                logger.info(f"Successfully refreshed OAuth token for user {oauth_token.user_id}")
                return {"success": True, "message": "Token refreshed successfully"}
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"Refresh failed: {response.status_code}"}
                
    except Exception as e:
        logger.error(f"Error refreshing OAuth token: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _perform_resilient_sync(calendar_service, user_id: int, force_sync: bool) -> Dict[str, Any]:
    """Perform calendar sync with exponential backoff and retry logic."""
    max_retries = 3
    base_delay = 1.0  # Base delay in seconds
    
    for attempt in range(max_retries):
        try:
            return await calendar_service.sync_events(user_id=user_id, force_sync=force_sync)
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                raise e
            
            # Calculate delay with exponential backoff and jitter
            delay = base_delay * (2 ** attempt)
            jitter = delay * 0.1 * (2 * (hash(str(user_id)) % 100) / 100 - 1)  # ±10% jitter
            total_delay = delay + jitter
            
            logger.warning(f"Sync attempt {attempt + 1} failed for user {user_id}: {e}. Retrying in {total_delay:.1f}s")
            await asyncio.sleep(total_delay)


async def _get_sync_failure_count(user_id: int, db: AsyncSession) -> int:
    """Get the number of recent sync failures for circuit breaker."""
    # For now, use a simple in-memory approach
    # In production, consider using Redis or database table
    failure_key = f"sync_failures_{user_id}"
    
    # This is a simplified implementation - in production use Redis
    if not hasattr(_get_sync_failure_count, 'failures'):
        _get_sync_failure_count.failures = {}
    
    return _get_sync_failure_count.failures.get(failure_key, 0)


async def _get_last_sync_failure_time(user_id: int, db: AsyncSession) -> Optional[datetime]:
    """Get the timestamp of the last sync failure."""
    failure_time_key = f"last_failure_{user_id}"
    
    if not hasattr(_get_last_sync_failure_time, 'failure_times'):
        _get_last_sync_failure_time.failure_times = {}
    
    return _get_last_sync_failure_time.failure_times.get(failure_time_key)


async def _record_sync_failure(user_id: int, error_msg: str, db: AsyncSession):
    """Record a sync failure for circuit breaker pattern."""
    failure_key = f"sync_failures_{user_id}"
    failure_time_key = f"last_failure_{user_id}"
    
    if not hasattr(_record_sync_failure, 'failures'):
        _record_sync_failure.failures = {}
    if not hasattr(_record_sync_failure, 'failure_times'):
        _record_sync_failure.failure_times = {}
    
    _record_sync_failure.failures[failure_key] = _record_sync_failure.failures.get(failure_key, 0) + 1
    _record_sync_failure.failure_times[failure_time_key] = datetime.now(timezone.utc)
    
    logger.error(f"Recorded sync failure for user {user_id}: {error_msg}")


async def _reset_sync_failure_count(user_id: int, db: AsyncSession):
    """Reset sync failure count after successful sync."""
    failure_key = f"sync_failures_{user_id}"
    failure_time_key = f"last_failure_{user_id}"
    
    if hasattr(_reset_sync_failure_count, 'failures'):
        _reset_sync_failure_count.failures.pop(failure_key, None)
    if hasattr(_reset_sync_failure_count, 'failure_times'):
        _reset_sync_failure_count.failure_times.pop(failure_time_key, None)


def _get_user_friendly_error_message(error: Exception) -> str:
    """Convert technical errors into user-friendly messages."""
    error_str = str(error).lower()
    
    if "expired" in error_str or "unauthorized" in error_str or "401" in error_str:
        return "Your Google Calendar connection has expired. Please reconnect your account."
    elif "rate limit" in error_str or "quota" in error_str or "429" in error_str:
        return "Google Calendar is temporarily busy. Please try again in a few minutes."
    elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
        return "Network connection issue. Please check your internet and try again."
    elif "server error" in error_str or "500" in error_str:
        return "Google Calendar service is temporarily unavailable. Please try again later."
    elif "forbidden" in error_str or "403" in error_str:
        return "Access denied to Google Calendar. Please check your permissions and reconnect."
    else:
        return "Calendar sync encountered an issue. Please try again or reconnect your Google Calendar."


def _classify_error_type(error: Exception) -> str:
    """Classify error types for better handling."""
    error_str = str(error).lower()
    
    if "expired" in error_str or "unauthorized" in error_str or "401" in error_str:
        return "authentication_expired"
    elif "rate limit" in error_str or "quota" in error_str or "429" in error_str:
        return "rate_limited"
    elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
        return "network_error"
    elif "server error" in error_str or "500" in error_str:
        return "external_service_error"
    elif "forbidden" in error_str or "403" in error_str:
        return "permission_denied"
    else:
        return "unknown_error"


async def get_category_color(category: str, user_id: int = None, db: AsyncSession = None) -> str:
    """Get color for event category from user's custom categories or fallback to defaults."""
    
    # If we have user context, try to fetch their custom category color
    if user_id and db:
        try:
            from sqlalchemy import select
            result = await db.execute(select(UserCategory).filter(
                UserCategory.user_id == user_id,
                UserCategory.category_name == category
            ))
            user_category = result.scalars().first()
            
            if user_category and user_category.color:
                return user_category.color
        except Exception:
            pass  # Fall back to default colors
    
    # Fallback color map (matches the default categories)
    color_map = {
        # Original categories
        "Work": "#3b82f6",      # Blue
        "Personal": "#10b981",  # Emerald
        "Health": "#ef4444",    # Red
        "Learning": "#8b5cf6",  # Purple
        "Social": "#f59e0b",    # Amber
        
        # Admin calendar event types (now user-customizable)
        "Meeting": "#0ea5e9",   # Sky blue
        "Appointment": "#06b6d4", # Cyan
        "Task": "#84cc16",      # Lime green
        "Reminder": "#f97316",  # Orange
        "Event": "#a855f7",     # Purple
        
        # Legacy/fallback
        "Leisure": "#8b5cf6",   # Purple
        "Family": "#f59e0b",    # Amber
        "Fitness": "#10b981",   # Emerald
        "Default": "#6b7280"    # Gray
    }
    return color_map.get(category, "#6b7280")

@router.post("/analyze-event", dependencies=[Depends(verify_csrf_token)])
async def analyze_event_with_ai(
    request: AIEventAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> AIEventAnalysisResponse:
    """Analyze event conversation with AI to extract event details."""
    
    try:
        # Initialize AI event analysis service
        ai_service = AIEventAnalysisService()
        
        # Get user's categories from database
        from sqlalchemy import select
        result = await db.execute(select(UserCategory).filter(
            UserCategory.user_id == current_user.id
        ))
        user_categories = result.scalars().all()
        
        # Convert to format expected by AI service
        categories_for_ai = []
        for cat in user_categories:
            categories_for_ai.append({
                "id": str(cat.id),
                "name": cat.category_name,
                "type": cat.category_type,
                "color": cat.color or "#6b7280",
                "description": cat.description or "",
                "emoji": "📋",  # Default emoji - would be stored in a new field
                "priority": int(cat.weight * 5)  # Convert weight to priority 1-5
            })
        
        # If no categories exist, use the userCategories from the request as fallback
        if not categories_for_ai:
            categories_for_ai = request.userCategories
        
        # Convert conversation to proper format
        conversation_history = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in request.conversation
        ]
        
        # Analyze the conversation
        analysis_result = await ai_service.analyze_conversation(
            conversation=conversation_history,
            time_slot=request.timeSlot,
            user_categories=categories_for_ai,
            user_id=current_user.id
        )
        
        return AIEventAnalysisResponse(
            needsMoreInfo=analysis_result.get("needs_more_info", False),
            question=analysis_result.get("question"),
            eventDetails=analysis_result.get("event_details")
        )
        
    except Exception as e:
        logger.error(f"AI event analysis failed for user {current_user.id}: {e}")
        
        # Return fallback response
        return AIEventAnalysisResponse(
            needsMoreInfo=True,
            question="I apologize, but I encountered an error processing your request. Could you please provide more details about your event?"
        )

@router.post("/events")
async def create_calendar_event(
    request: EventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """Create a new calendar event."""
    
    try:
        # Parse datetime strings
        start_time = datetime.fromisoformat(request.start.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(request.end.replace('Z', '+00:00'))
        
        # Create event in database
        # Get or create default calendar for user
        from sqlalchemy import select
        result = await db.execute(select(Calendar).filter(Calendar.user_id == current_user.id))
        calendar = result.scalars().first()
        if not calendar:
            calendar = Calendar(user_id=current_user.id, name="Default Calendar")
            db.add(calendar)
            await db.flush()  # Get the calendar ID
        
        new_event = Event(
            summary=request.title,
            description=request.description,
            start_time=start_time,
            end_time=end_time,
            location=request.location,
            calendar_id=calendar.id,
            category=request.category,
            movability_score=0.5,  # Default movability score
            is_movable=True  # Default to movable
        )
        
        # Add attendees as a JSON field if provided
        if request.attendees:
            new_event.attendees = request.attendees
        
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        
        logger.info(f"Created event '{request.title}' for user {current_user.id}")
        
        # Return event data in format expected by frontend
        return {
            "id": str(new_event.id),
            "title": new_event.summary,
            "description": new_event.description,
            "start": new_event.start_time.isoformat(),
            "end": new_event.end_time.isoformat(),
            "location": getattr(new_event, 'location', None),
            "category": new_event.category.value if new_event.category else "Default",
            "priority": getattr(new_event, 'priority', 3),
            "attendees": getattr(new_event, 'attendees', []) or [],
            "backgroundColor": await get_category_color(new_event.category.value if new_event.category else "Default", current_user.id, db),
            "textColor": "white"
        }
        
    except Exception as e:
        logger.error(f"Failed to create event for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create event. Please try again."
        )