"""
API router for native client endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from api.dependencies import get_db, get_current_user
from shared.database.models import User

router = APIRouter()

@router.post("/login")
def native_login(user: User = Depends(get_current_user)):
    """
    Validates user credentials over mTLS.
    """
    # The get_current_user dependency already handles authentication.
    # If we get here, the user is authenticated.
    return {"message": "Login successful"}

@router.post("/verify-2fa")
def native_verify_2fa(user: User = Depends(get_current_user)):
    """
    Validates the TOTP code and returns a JWT.
    """
    # This is a placeholder. The actual implementation would involve the
    # two_factor_auth_router logic, but for now, we'll just return a message.
    return {"message": "2FA verification successful. JWT would be returned here."}

@router.get("/modes")
def get_modes(db: Session = Depends(get_db)):
    """
    Returns a list of available AI chat modes.
    """
    # This is a placeholder. The actual implementation would fetch these from the database.
    return ["Reflective Coach", "Coding Assistant", "General AI"]

@router.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    context: str = Form(...),
    mode: str = Form(None),
    user: User = Depends(get_current_user)
):
    """
    Analyzes an image and context from the native client.
    """
    # This is a placeholder. The actual implementation would send this data
    # to the LangGraph router.
    return {
        "message": "Analysis request received.",
        "context": context,
        "mode": mode,
        "image_filename": image.filename
    }
