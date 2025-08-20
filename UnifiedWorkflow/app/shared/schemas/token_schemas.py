"""Pydantic models (schemas) for token-related data."""
from typing import Optional

from pydantic import BaseModel

# The UserRole enum is in the top-level database_models.py file.
# The original relative import was incorrect, causing a ModuleNotFoundError.
# This absolute import assumes the app's root directory ('/app') is in the Python path.
from shared.database.models import UserRole


# --- Token Schemas ---
class Token(BaseModel):
    """Schema for the token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for data stored within a JWT."""
    id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None