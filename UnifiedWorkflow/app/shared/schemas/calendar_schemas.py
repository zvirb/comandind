"""Pydantic models (schemas) for calendar-related data."""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from shared.database.models import EventCategory
 

# --- Event Schemas ---
class TimePreferences(BaseModel):
    """Schema for user's preferred time windows for events."""
    preferred_window_start: Optional[str] = None
    preferred_window_end: Optional[str] = None


class Movability(BaseModel):
    """Schema for an event's movability assessment."""
    is_movable: bool = True
    score: float = Field(0.0, ge=0.0, le=1.0)
    reason: Optional[str] = None


class Event(BaseModel):
    """Base schema for a calendar event."""
    summary: str
    description: Optional[str] = None
    start: Dict[str, str]
    end: Dict[str, str]
    category: EventCategory = EventCategory.DEFAULT
    movability: Movability = Field(default_factory=Movability)
    google_event_id: Optional[str] = None

    @classmethod
    def get_available_categories(cls) -> List[str]:
        """Returns a list of available event categories."""
        return [category.value for category in EventCategory]


DEFAULT_PREFERRED_WINDOWS_BY_CATEGORY: Dict[EventCategory, Dict[str, str]] = {
    EventCategory.WORK: {"start": "09:00", "end": "17:00"},
    EventCategory.HEALTH: {"start": "06:00", "end": "08:00"},
    EventCategory.LEISURE: {"start": "19:00", "end": "22:00"},
    EventCategory.FAMILY: {"start": "17:00", "end": "20:00"},
    EventCategory.FITNESS: {"start": "05:00", "end": "07:00"},
    EventCategory.DEFAULT: {"start": "09:00", "end": "17:00"},
}