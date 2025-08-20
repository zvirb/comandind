from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

# This defines the data the frontend will send when submitting feedback
class TaskFeedbackCreate(BaseModel):
    feeling: str
    difficulty: int = Field(..., ge=1, le=10) # Ensures value is between 1 and 10
    energy: int = Field(..., ge=1, le=10)
    category: Optional[str] = None
    notes: Optional[str] = None
    blockers_encountered: Optional[bool] = False

# This defines the data that will be returned by the API after creation
class TaskFeedback(TaskFeedbackCreate):
    id: int
    user_id: int
    opportunity_id: uuid.UUID
    completed_at: datetime

    model_config = {"from_attributes": True}