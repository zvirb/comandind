"""Router for user settings."""
from fastapi import APIRouter, Depends, Request, HTTPException
import httpx
import os
from json import JSONDecodeError
from typing import List, Dict, Any
import logging

from api.dependencies import get_current_user, verify_csrf_token, get_db
from shared.database.models import User
from shared.schemas.user_schemas import UserSettings
from shared.utils.config import get_settings
from shared.utils.error_handler import (
    create_error_context, internal_server_error, 
    validation_error, service_unavailable_error
)
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.utils.database_setup import get_async_session

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

@router.get("/settings", response_model=UserSettings)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves the settings for the currently authenticated user.
    """
    try:
        # Try to refresh user from database to get latest settings
        result = await db.execute(
            select(User).where(User.id == current_user.id)
        )
        user_from_db = result.scalar_one_or_none()
        
        if user_from_db:
            current_user = user_from_db
    except Exception as e:
        logger.warning(f"Database refresh failed for settings, using current user object: {e}")
        # Fall back to using the current_user from JWT without fresh DB lookup
    
    default_event_weights = {
        "meeting": 1.0,
        "appointment": 0.9,
        "reminder": 0.7,
        "task": 0.8,
        "event": 0.6
    }
    
    return UserSettings(
        theme=current_user.theme or "dark", 
        notifications_enabled=current_user.notifications_enabled if current_user.notifications_enabled is not None else True, 
        selected_model=current_user.selected_model or "llama3.2:3b",
        timezone=current_user.timezone or "UTC",
        chat_model=current_user.chat_model or "llama3.2:3b",
        initial_assessment_model=current_user.initial_assessment_model or "llama3.2:3b", 
        tool_selection_model=current_user.tool_selection_model or "llama3.2:3b",
        embeddings_model=current_user.embeddings_model or "llama3.2:3b",
        coding_model=current_user.coding_model or "llama3.2:3b",
        # Granular Node-Specific Models
        executive_assessment_model=current_user.executive_assessment_model or "llama3.2:3b",
        confidence_assessment_model=current_user.confidence_assessment_model or "llama3.2:3b",
        tool_routing_model=current_user.tool_routing_model or "llama3.2:3b",
        simple_planning_model=current_user.simple_planning_model or "llama3.2:3b",
        wave_function_specialist_model=current_user.wave_function_specialist_model or "llama3.2:1b",
        wave_function_refinement_model=current_user.wave_function_refinement_model or "llama3.1:8b",
        plan_validation_model=current_user.plan_validation_model or "llama3.2:3b",
        plan_comparison_model=current_user.plan_comparison_model or "llama3.2:3b",
        reflection_model=current_user.reflection_model or "llama3.2:3b",
        final_response_model=current_user.final_response_model or "llama3.2:3b",
        fast_conversational_model=current_user.fast_conversational_model or "llama3.2:1b",
        # Expert Group Model Configuration
        project_manager_model=current_user.project_manager_model or "llama3.2:3b",
        technical_expert_model=current_user.technical_expert_model or "llama3.1:8b",
        business_analyst_model=current_user.business_analyst_model or "llama3.2:3b",
        creative_director_model=current_user.creative_director_model or "llama3.2:3b",
        research_specialist_model=current_user.research_specialist_model or "llama3.1:8b",
        planning_expert_model=current_user.planning_expert_model or "llama3.2:3b",
        socratic_expert_model=current_user.socratic_expert_model or "llama3.2:3b",
        wellbeing_coach_model=current_user.wellbeing_coach_model or "llama3.2:3b",
        personal_assistant_model=current_user.personal_assistant_model or "mistral:7b",
        data_analyst_model=current_user.data_analyst_model or "qwen2.5:7b",
        output_formatter_model=current_user.output_formatter_model or "llama3.2:3b",
        quality_assurance_model=current_user.quality_assurance_model or "llama3.2:3b",
        calendar_event_weights=current_user.calendar_event_weights or default_event_weights
    )

@router.post("/settings", response_model=UserSettings)  # TEMPORARY: CSRF dependency removed
async def update_user_settings(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Updates the settings for the currently authenticated user.
    """
    try:
        body = await request.json()
    except Exception:
        context = create_error_context(request, user_id=current_user.id)
        raise validation_error(
            message="Invalid JSON in request body",
            field_errors={"body": "Request body must be valid JSON"},
            context=context
        )
    
    # Basic validation
    if not body or not isinstance(body, dict):
        context = create_error_context(request, user_id=current_user.id)
        raise validation_error(
            message="Request body must be a valid JSON object",
            field_errors={"body": "Expected JSON object, got other type"},
            context=context
        )
    
    # Update user settings in database using dependency injection
    try:
        # Update user settings in database
        if "theme" in body:
            current_user.theme = body["theme"]
        # Handle both field names for compatibility
        if "notifications_enabled" in body:
            current_user.notifications_enabled = body["notifications_enabled"]
        elif "email_notifications" in body:
            # Frontend sends email_notifications, map to notifications_enabled
            current_user.notifications_enabled = body["email_notifications"]
        if "selected_model" in body:
            current_user.selected_model = body["selected_model"]
        if "timezone" in body:
            current_user.timezone = body["timezone"]
        if "chat_model" in body:
            current_user.chat_model = body["chat_model"]
        if "initial_assessment_model" in body:
            current_user.initial_assessment_model = body["initial_assessment_model"]
        if "tool_selection_model" in body:
            current_user.tool_selection_model = body["tool_selection_model"]
        if "embeddings_model" in body:
            current_user.embeddings_model = body["embeddings_model"]
        if "coding_model" in body:
            current_user.coding_model = body["coding_model"]
        # Granular Node-Specific Models
        if "executive_assessment_model" in body:
            current_user.executive_assessment_model = body["executive_assessment_model"]
        if "confidence_assessment_model" in body:
            current_user.confidence_assessment_model = body["confidence_assessment_model"]
        if "tool_routing_model" in body:
            current_user.tool_routing_model = body["tool_routing_model"]
        if "simple_planning_model" in body:
            current_user.simple_planning_model = body["simple_planning_model"]
        if "wave_function_specialist_model" in body:
            current_user.wave_function_specialist_model = body["wave_function_specialist_model"]
        if "wave_function_refinement_model" in body:
            current_user.wave_function_refinement_model = body["wave_function_refinement_model"]
        if "plan_validation_model" in body:
            current_user.plan_validation_model = body["plan_validation_model"]
        if "plan_comparison_model" in body:
            current_user.plan_comparison_model = body["plan_comparison_model"]
        if "reflection_model" in body:
            current_user.reflection_model = body["reflection_model"]
        if "final_response_model" in body:
            current_user.final_response_model = body["final_response_model"]
        if "fast_conversational_model" in body:
            current_user.fast_conversational_model = body["fast_conversational_model"]
        # Expert Group Model Configuration
        if "project_manager_model" in body:
            current_user.project_manager_model = body["project_manager_model"]
        if "technical_expert_model" in body:
            current_user.technical_expert_model = body["technical_expert_model"]
        if "business_analyst_model" in body:
            current_user.business_analyst_model = body["business_analyst_model"]
        if "creative_director_model" in body:
            current_user.creative_director_model = body["creative_director_model"]
        if "research_specialist_model" in body:
            current_user.research_specialist_model = body["research_specialist_model"]
        if "planning_expert_model" in body:
            current_user.planning_expert_model = body["planning_expert_model"]
        if "socratic_expert_model" in body:
            current_user.socratic_expert_model = body["socratic_expert_model"]
        if "wellbeing_coach_model" in body:
            current_user.wellbeing_coach_model = body["wellbeing_coach_model"]
        if "personal_assistant_model" in body:
            current_user.personal_assistant_model = body["personal_assistant_model"]
        if "data_analyst_model" in body:
            current_user.data_analyst_model = body["data_analyst_model"]
        if "output_formatter_model" in body:
            current_user.output_formatter_model = body["output_formatter_model"]
        if "quality_assurance_model" in body:
            current_user.quality_assurance_model = body["quality_assurance_model"]
        if "calendar_event_weights" in body:
            current_user.calendar_event_weights = body["calendar_event_weights"]
        
        # Save changes to database
        await db.commit()
        
        # Refresh the user object to get the updated values
        await db.refresh(current_user)
    except Exception as db_error:
        logger.error(f"Database error updating settings: {db_error}")
        await db.rollback()
        context = create_error_context(request, user_id=current_user.id)
        raise internal_server_error(
            message="Failed to update user settings - database connection issue",
            details={"error": str(db_error)},
            context=context
        )
    
    default_event_weights = {
        "meeting": 1.0,
        "appointment": 0.9,
        "reminder": 0.7,
        "task": 0.8,
        "event": 0.6
    }
    
    return UserSettings(
        theme=current_user.theme or "dark",
        notifications_enabled=current_user.notifications_enabled if current_user.notifications_enabled is not None else True,
        selected_model=current_user.selected_model or "llama3.2:3b",
        timezone=current_user.timezone or "UTC",
        chat_model=current_user.chat_model or "llama3.2:3b",
        initial_assessment_model=current_user.initial_assessment_model or "llama3.2:3b",
        tool_selection_model=current_user.tool_selection_model or "llama3.2:3b",
        embeddings_model=current_user.embeddings_model or "llama3.2:3b",
        coding_model=current_user.coding_model or "llama3.2:3b",
        # Granular Node-Specific Models
        executive_assessment_model=current_user.executive_assessment_model or "llama3.2:3b",
        confidence_assessment_model=current_user.confidence_assessment_model or "llama3.2:3b",
        tool_routing_model=current_user.tool_routing_model or "llama3.2:3b",
        simple_planning_model=current_user.simple_planning_model or "llama3.2:3b",
        wave_function_specialist_model=current_user.wave_function_specialist_model or "llama3.2:1b",
        wave_function_refinement_model=current_user.wave_function_refinement_model or "llama3.1:8b",
        plan_validation_model=current_user.plan_validation_model or "llama3.2:3b",
        plan_comparison_model=current_user.plan_comparison_model or "llama3.2:3b",
        reflection_model=current_user.reflection_model or "llama3.2:3b",
        final_response_model=current_user.final_response_model or "llama3.2:3b",
        fast_conversational_model=current_user.fast_conversational_model or "llama3.2:1b",
        # Expert Group Model Configuration
        project_manager_model=current_user.project_manager_model or "llama3.2:3b",
        technical_expert_model=current_user.technical_expert_model or "llama3.1:8b",
        business_analyst_model=current_user.business_analyst_model or "llama3.2:3b",
        creative_director_model=current_user.creative_director_model or "llama3.2:3b",
        research_specialist_model=current_user.research_specialist_model or "llama3.1:8b",
        planning_expert_model=current_user.planning_expert_model or "llama3.2:3b",
        socratic_expert_model=current_user.socratic_expert_model or "llama3.2:3b",
        wellbeing_coach_model=current_user.wellbeing_coach_model or "llama3.2:3b",
        personal_assistant_model=current_user.personal_assistant_model or "mistral:7b",
        data_analyst_model=current_user.data_analyst_model or "qwen2.5:7b",
        output_formatter_model=current_user.output_formatter_model or "llama3.2:3b",
        quality_assurance_model=current_user.quality_assurance_model or "llama3.2:3b",
        calendar_event_weights=current_user.calendar_event_weights or default_event_weights
    )

@router.put("/settings", response_model=UserSettings)  # TEMPORARY: CSRF dependency removed
async def update_user_settings_put(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Updates the settings for the currently authenticated user using RESTful PUT method.
    
    This endpoint provides the same functionality as POST /settings but follows 
    RESTful conventions where PUT is used for resource updates.
    """
    # Reuse the same logic as the POST endpoint
    return await update_user_settings(request, current_user, db)

@router.get("/settings/models")
async def get_available_models(
    # This endpoint is now nested under /settings for better RESTful consistency.
    _current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get list of available Ollama models with metadata.
    """
    # The Ollama URL is now reliably sourced from the settings object, which
    # consolidates various environment variables into a single source of truth.
    ollama_url = settings.OLLAMA_API_BASE_URL
    if not ollama_url:
        logger.error("Ollama API base URL is not configured.")
        context = create_error_context(request)
        raise service_unavailable_error(
            service="Ollama",
            message="Ollama service is not configured",
            context=context
        )

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Attempting to fetch models from Ollama at: {ollama_url}")
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            
            try:
                data = response.json()
            except JSONDecodeError:
                logger.error(f"Failed to decode JSON from Ollama. Response text: {response.text}")
                context = create_error_context(request)
                raise internal_server_error(
                    message="Received non-JSON response from Ollama",
                    details={"response_text": response.text[:500]},
                    context=context
                )
            models = []
            
            # Define which models support tool calling
            tool_compatible_models = {
                "llama3.2:3b", "llama3.1:8b", "llama3.1:70b", "llama3:8b", "llama3:70b",
                "mistral:7b", "mistral:latest", "mixtral:8x7b", "mixtral:8x22b",
                "codellama:7b", "codellama:13b", "codellama:34b"
            }
            
            for model in data.get("models", []):
                model_name = model.get("name", "")
                models.append({
                    "name": model_name,
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                    "supports_tools": model_name in tool_compatible_models,
                    "recommended": model_name == "llama3.2:3b"  # Our recommended model
                })
            
            # Sort by recommended first, then tool support, then by name
            models.sort(key=lambda x: (not x["recommended"], not x["supports_tools"], x["name"]))
            
            return models
            
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch models from Ollama at {ollama_url}: {e}")
        context = create_error_context(request)
        raise service_unavailable_error(
            service="Ollama Model Service",
            message="Unable to fetch available models",
            context=context
        )
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Unexpected error fetching models: {e}")
        context = create_error_context(request)
        raise internal_server_error(
            message="Unexpected error occurred while fetching models",
            details={"error": str(e)},
            context=context
        )