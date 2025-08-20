
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from shared.utils.database_setup import get_db
from api.dependencies import get_current_user

router = APIRouter()

# Available AI chat modes for the native client
AVAILABLE_MODES = [
    "Simple Chat",
    "Expert Group Chat", 
    "Smart Router",
    "Socratic Interview",
    "Reflective Coach",
    "Coding Assistant",
    "General Assistant"
]

class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    mode: str

@router.get("/modes", response_model=List[str])
def get_native_modes():
    """
    Returns a list of available AI chat modes.
    """
    return AVAILABLE_MODES

@router.post("/analyze")
def native_analyze(
    image: UploadFile = File(...),
    context: str = Form(...),
    mode: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Main analysis endpoint for the native client.
    Accepts an image, context string, and optional mode string.
    """
    # For now, just return a success message with the received data.
    # Later, this will integrate with LangGraph for actual analysis.
    return {
        "message": "Analysis request received",
        "filename": image.filename,
        "content_type": image.content_type,
        "context": context,
        "mode": mode,
        "user_id": current_user["id"],
    }

@router.post("/chat", response_model=ChatResponse)
def native_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Chat endpoint for the native client.
    Accepts a message and optional mode, returns AI response.
    """
    # For now, return a simple echo response
    # Later, this will integrate with your existing chat system
    mode = request.mode or "General Assistant"
    
    # Simple response for testing - replace with actual AI integration
    response_text = f"[{mode}] I received your message: '{request.message}'. This is a placeholder response from the native chat endpoint."
    
    return ChatResponse(
        response=response_text,
        mode=mode
    )
