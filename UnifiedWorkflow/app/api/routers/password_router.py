"""Password management router for changing user passwords."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import verify_password, get_password_hash
from api.dependencies import get_current_user
from shared.database.models import User
from shared.utils.database_setup import get_db

router = APIRouter()

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ChangePasswordResponse(BaseModel):
    message: str

@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the current user's password.
    Requires the current password for verification.
    """
    # Verify the current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password (basic validation)
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Hash the new password and update the user
    new_hashed_password = get_password_hash(request.new_password)
    current_user.hashed_password = new_hashed_password
    
    db.commit()
    db.refresh(current_user)
    
    return ChangePasswordResponse(
        message="Password changed successfully"
    )