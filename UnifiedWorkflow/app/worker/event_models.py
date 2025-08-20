# backend/api/app/event_models.py
"""
Pydantic models for calendar events and related data structures.
"""
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class TimePreferences(BaseModel):
    """Represents preferred time windows for scheduling."""
    preferred_window_start: Optional[str] = None
    preferred_window_end: Optional[str] = None

class Movability(BaseModel):
    """Represents the movability assessment of an event."""
    score: float
    is_movable: bool
    reason: str

class Event(BaseModel):
    """Represents a calendar event."""
    id: Optional[int] = None
    user_id: int
    calendar_id: str
    google_event_id: str
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    category: str
    movability_score: float
    is_movable: bool

    model_config = {"from_attributes": True}

    @staticmethod
    def get_available_categories() -> List[str]:
        """Returns the list of available event categories."""
        from worker.shared_constants import AVAILABLE_CATEGORIES
        return list(AVAILABLE_CATEGORIES)