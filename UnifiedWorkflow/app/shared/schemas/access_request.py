"""
_summary_

_extended_summary_
"""
from pydantic import BaseModel, EmailStr

class AccessRequestCreate(BaseModel):
    """
    Schema for creating a new access request.
    """
    email: EmailStr

class AccessRequest(AccessRequestCreate):
    """
    Schema for an access request.
    """
    id: int
    status: str

    class Config:
        from_attributes = True
