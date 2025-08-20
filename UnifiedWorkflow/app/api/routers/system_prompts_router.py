"""
System Prompts API Router
API endpoints for managing user system prompts
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db, verify_csrf_token
from shared.database.models import User, SystemPrompt
from shared.services.system_prompt_service import SystemPromptService

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemPromptResponse(BaseModel):
    id: str
    prompt_key: str
    prompt_category: str
    prompt_name: str
    description: Optional[str]
    prompt_text: str
    variables: Optional[Dict[str, Any]]
    is_factory_default: bool
    is_active: bool
    version: int
    usage_count: int
    last_used_at: Optional[str]
    average_satisfaction: Optional[float]
    success_rate: Optional[float]
    created_at: str
    updated_at: str


class SystemPromptUpdateRequest(BaseModel):
    prompt_text: str
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True


class SystemPromptCreateRequest(BaseModel):
    prompt_key: str
    prompt_category: str
    prompt_name: str
    description: Optional[str] = None
    prompt_text: str
    variables: Optional[Dict[str, Any]] = None
    is_active: bool = True


@router.get("/prompts", response_model=List[SystemPromptResponse])
async def get_user_prompts(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all system prompts for the current user."""
    try:
        service = SystemPromptService()
        prompts = await service.get_user_prompts(db, current_user.id, category)
        
        return [
            SystemPromptResponse(
                id=str(prompt.id),
                prompt_key=prompt.prompt_key,
                prompt_category=prompt.prompt_category,
                prompt_name=prompt.prompt_name,
                description=prompt.description,
                prompt_text=prompt.prompt_text,
                variables=prompt.variables or {},
                is_factory_default=prompt.is_factory_default,
                is_active=prompt.is_active,
                version=prompt.version,
                usage_count=prompt.usage_count,
                last_used_at=prompt.last_used_at.isoformat() if prompt.last_used_at else None,
                average_satisfaction=prompt.average_satisfaction,
                success_rate=prompt.success_rate,
                created_at=prompt.created_at.isoformat(),
                updated_at=prompt.updated_at.isoformat()
            )
            for prompt in prompts
        ]
        
    except Exception as e:
        logger.error(f"Error fetching user prompts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user prompts: {str(e)}"
        )


@router.get("/prompts/categories")
async def get_prompt_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all available prompt categories."""
    try:
        service = SystemPromptService()
        categories = await service.get_available_categories(db, current_user.id)
        
        return {
            "categories": categories
        }
        
    except Exception as e:
        logger.error(f"Error fetching prompt categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prompt categories: {str(e)}"
        )


@router.get("/prompts/factory-defaults")
async def get_factory_defaults(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all factory default prompts."""
    try:
        service = SystemPromptService()
        defaults = await service.get_factory_defaults(db)
        
        return [
            SystemPromptResponse(
                id="factory-default",  # Factory defaults don't have individual IDs
                prompt_key=prompt["prompt_key"],
                prompt_category=prompt["prompt_category"],
                prompt_name=prompt["prompt_name"],
                description=prompt["description"],
                prompt_text=prompt["prompt_text"],
                variables=prompt.get("variables", {}),
                is_factory_default=True,
                is_active=True,
                version=1,  # Factory defaults are version 1
                usage_count=0,  # Factory defaults don't track usage
                last_used_at=None,
                average_satisfaction=None,
                success_rate=None,
                created_at="2025-01-01T00:00:00Z",  # Placeholder
                updated_at="2025-01-01T00:00:00Z"   # Placeholder
            )
            for prompt in defaults
        ]
        
    except Exception as e:
        logger.error(f"Error fetching factory defaults: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch factory defaults"
        )


@router.get("/prompts/{prompt_key}", response_model=SystemPromptResponse)
async def get_prompt(
    prompt_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific prompt for the current user."""
    try:
        service = SystemPromptService()
        prompt_text = await service.get_prompt_for_user(db, current_user.id, prompt_key)
        
        if not prompt_text:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt '{prompt_key}' not found"
            )
        
        # Get the full prompt object
        prompt = await service.get_user_prompt_object(db, current_user.id, prompt_key)
        
        return SystemPromptResponse(
            id=str(prompt.id),
            prompt_key=prompt.prompt_key,
            prompt_category=prompt.prompt_category,
            prompt_name=prompt.prompt_name,
            description=prompt.description,
            prompt_text=prompt.prompt_text,
            variables=prompt.variables or {},
            is_factory_default=prompt.is_factory_default,
            is_active=prompt.is_active,
            version=prompt.version,
            usage_count=prompt.usage_count,
            last_used_at=prompt.last_used_at.isoformat() if prompt.last_used_at else None,
            average_satisfaction=prompt.average_satisfaction,
            success_rate=prompt.success_rate,
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prompt {prompt_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prompt '{prompt_key}'"
        )


@router.post("/prompts", response_model=SystemPromptResponse, dependencies=[Depends(verify_csrf_token)])
async def create_prompt(
    request: SystemPromptCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new custom prompt for the user."""
    try:
        service = SystemPromptService()
        prompt = await service.create_user_prompt(
            db=db,
            user_id=current_user.id,
            prompt_key=request.prompt_key,
            prompt_category=request.prompt_category,
            prompt_name=request.prompt_name,
            prompt_text=request.prompt_text,
            description=request.description,
            variables=request.variables,
            is_active=request.is_active
        )
        
        return SystemPromptResponse(
            id=str(prompt.id),
            prompt_key=prompt.prompt_key,
            prompt_category=prompt.prompt_category,
            prompt_name=prompt.prompt_name,
            description=prompt.description,
            prompt_text=prompt.prompt_text,
            variables=prompt.variables or {},
            is_factory_default=prompt.is_factory_default,
            is_active=prompt.is_active,
            version=prompt.version,
            usage_count=prompt.usage_count,
            last_used_at=prompt.last_used_at.isoformat() if prompt.last_used_at else None,
            average_satisfaction=prompt.average_satisfaction,
            success_rate=prompt.success_rate,
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating prompt: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create prompt"
        )


@router.put("/prompts/{prompt_key}", response_model=SystemPromptResponse, dependencies=[Depends(verify_csrf_token)])
async def update_prompt(
    prompt_key: str,
    request: SystemPromptUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing prompt for the user."""
    try:
        service = SystemPromptService()
        prompt = await service.update_user_prompt(
            db=db,
            user_id=current_user.id,
            prompt_key=prompt_key,
            prompt_text=request.prompt_text,
            variables=request.variables,
            is_active=request.is_active
        )
        
        if not prompt:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt '{prompt_key}' not found"
            )
        
        return SystemPromptResponse(
            id=str(prompt.id),
            prompt_key=prompt.prompt_key,
            prompt_category=prompt.prompt_category,
            prompt_name=prompt.prompt_name,
            description=prompt.description,
            prompt_text=prompt.prompt_text,
            variables=prompt.variables or {},
            is_factory_default=prompt.is_factory_default,
            is_active=prompt.is_active,
            version=prompt.version,
            usage_count=prompt.usage_count,
            last_used_at=prompt.last_used_at.isoformat() if prompt.last_used_at else None,
            average_satisfaction=prompt.average_satisfaction,
            success_rate=prompt.success_rate,
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update prompt '{prompt_key}'"
        )


@router.delete("/prompts/{prompt_key}", dependencies=[Depends(verify_csrf_token)])
async def delete_prompt(
    prompt_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user's custom prompt."""
    try:
        service = SystemPromptService()
        success = await service.delete_user_prompt(db, current_user.id, prompt_key)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt '{prompt_key}' not found or cannot be deleted"
            )
        
        return {"message": f"Prompt '{prompt_key}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete prompt '{prompt_key}'"
        )


@router.post("/prompts/{prompt_key}/reset", response_model=SystemPromptResponse, dependencies=[Depends(verify_csrf_token)])
async def reset_prompt_to_factory(
    prompt_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset a prompt to its factory default."""
    try:
        service = SystemPromptService()
        prompt = await service.reset_to_factory_default(db, current_user.id, prompt_key)
        
        if not prompt:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt '{prompt_key}' not found or no factory default available"
            )
        
        return SystemPromptResponse(
            id=str(prompt.id),
            prompt_key=prompt.prompt_key,
            prompt_category=prompt.prompt_category,
            prompt_name=prompt.prompt_name,
            description=prompt.description,
            prompt_text=prompt.prompt_text,
            variables=prompt.variables or {},
            is_factory_default=prompt.is_factory_default,
            is_active=prompt.is_active,
            version=prompt.version,
            usage_count=prompt.usage_count,
            last_used_at=prompt.last_used_at.isoformat() if prompt.last_used_at else None,
            average_satisfaction=prompt.average_satisfaction,
            success_rate=prompt.success_rate,
            created_at=prompt.created_at.isoformat(),
            updated_at=prompt.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting prompt {prompt_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset prompt '{prompt_key}'"
        )


@router.post("/prompts/reset-all", dependencies=[Depends(verify_csrf_token)])
async def reset_all_prompts_to_factory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset all user prompts to factory defaults."""
    try:
        service = SystemPromptService()
        count = await service.reset_all_to_factory_defaults(db, current_user.id)
        
        return {
            "message": f"Successfully reset {count} prompts to factory defaults",
            "reset_count": count
        }
        
    except Exception as e:
        logger.error(f"Error resetting all prompts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to reset prompts to factory defaults"
        )