"""
Router for managing user categories/types for events and opportunities.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.utils.database_setup import get_db
from shared.database.models import User, UserCategory
from api.dependencies import get_current_user, verify_csrf_token
from api.services.ai_category_service import AICategoryService

logger = logging.getLogger(__name__)

router = APIRouter()

class CategoryCreate(BaseModel):
    """Request model for creating a new category."""
    name: str
    type: str  # 'event', 'opportunity', or 'both'
    color: str
    emoji: str
    priority: int = 3
    description: Optional[str] = None
    weights: Optional[Dict[str, float]] = None

class CategoryUpdate(BaseModel):
    """Request model for updating a category."""
    name: Optional[str] = None
    type: Optional[str] = None
    color: Optional[str] = None
    emoji: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    weights: Optional[Dict[str, float]] = None

class CategoryResponse(BaseModel):
    """Response model for category data."""
    id: str
    name: str
    type: str
    color: str
    emoji: str
    priority: int
    description: Optional[str]
    is_default: bool = False
    ai_generated: bool = False
    weights: Optional[Dict[str, float]] = None

class AISuggestionRequest(BaseModel):
    """Request model for AI category suggestions."""
    missionStatement: Optional[Dict[str, Any]] = None
    workStyle: Optional[Dict[str, Any]] = None
    productivityPatterns: Optional[Dict[str, Any]] = None
    existingCategories: Optional[List[Dict[str, Any]]] = None

class AIColorEmojiRequest(BaseModel):
    """Request model for AI color and emoji assignment."""
    categoryName: str
    categoryType: str
    description: Optional[str] = None
    userContext: Optional[Dict[str, Any]] = None

@router.get("", response_model=List[CategoryResponse])
async def get_user_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all categories for the current user."""
    
    categories = db.query(UserCategory).filter(
        UserCategory.user_id == current_user.id
    ).all()
    
    # If no categories exist, initialize with defaults
    if not categories:
        categories = await initialize_default_categories(db, current_user.id)
    
    return [
        CategoryResponse(
            id=str(cat.id),
            name=cat.category_name,
            type=cat.category_type,
            color=cat.color or "#6b7280",
            emoji=cat.emoji or "📋",
            priority=int(cat.weight * 5),  # Convert weight to priority 1-5
            description=cat.description,
            is_default=cat.category_type == "default",
            ai_generated=cat.ai_generated or False,
            weights=cat.weights or {
                "importance": cat.weight,
                "urgency": cat.weight * 0.8,
                "complexity": cat.weight * 0.6,
                "flexibility": 1.0 - (cat.weight * 0.5)
            }
        )
        for cat in categories
    ]

@router.post("", response_model=CategoryResponse, dependencies=[Depends(verify_csrf_token)])
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new category for the current user."""
    
    # Check if category name already exists for this user
    existing = db.query(UserCategory).filter(
        UserCategory.user_id == current_user.id,
        UserCategory.category_name == category_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category_data.name}' already exists"
        )
    
    # Create new category
    new_category = UserCategory(
        id=uuid4(),
        user_id=current_user.id,
        category_name=category_data.name,
        category_type=category_data.type,
        weight=category_data.priority / 5.0,  # Convert priority to weight
        color=category_data.color,
        emoji=category_data.emoji,
        description=category_data.description,
        weights=category_data.weights,
        ai_generated=False
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    logger.info(f"Created category '{category_data.name}' for user {current_user.id}")
    
    return CategoryResponse(
        id=str(new_category.id),
        name=new_category.category_name,
        type=new_category.category_type,
        color=new_category.color,
        emoji=category_data.emoji,
        priority=category_data.priority,
        description=new_category.description,
        is_default=False,
        ai_generated=False,
        weights=category_data.weights or {
            "importance": new_category.weight,
            "urgency": new_category.weight * 0.8,
            "complexity": new_category.weight * 0.6,
            "flexibility": 1.0 - (new_category.weight * 0.5)
        }
    )

@router.put("/{category_id}", response_model=CategoryResponse, dependencies=[Depends(verify_csrf_token)])
async def update_category(
    category_id: str,
    update_data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing category."""
    
    try:
        category_uuid = UUID(category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category ID format")
    
    category = db.query(UserCategory).filter(
        UserCategory.id == category_uuid,
        UserCategory.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )
    
    # Update fields if provided
    if update_data.name is not None:
        category.category_name = update_data.name
    if update_data.type is not None:
        category.category_type = update_data.type
    if update_data.color is not None:
        category.color = update_data.color
    if update_data.emoji is not None:
        category.emoji = update_data.emoji
    if update_data.priority is not None:
        category.weight = update_data.priority / 5.0
    if update_data.description is not None:
        category.description = update_data.description
    if update_data.weights is not None:
        category.weights = update_data.weights
    
    db.commit()
    db.refresh(category)
    
    logger.info(f"Updated category '{category.category_name}' for user {current_user.id}")
    
    return CategoryResponse(
        id=str(category.id),
        name=category.category_name,
        type=category.category_type,
        color=category.color,
        emoji=category.emoji or "📋",
        priority=int(category.weight * 5),
        description=category.description,
        is_default=category.category_type == "default",
        ai_generated=category.ai_generated or False,
        weights=category.weights or {
            "importance": category.weight,
            "urgency": category.weight * 0.8,
            "complexity": category.weight * 0.6,
            "flexibility": 1.0 - (category.weight * 0.5)
        }
    )

@router.delete("/{category_id}", dependencies=[Depends(verify_csrf_token)])
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a category."""
    
    try:
        category_uuid = UUID(category_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category ID format")
    
    category = db.query(UserCategory).filter(
        UserCategory.id == category_uuid,
        UserCategory.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )
    
    # Don't allow deletion of default categories
    if category.category_type == "default":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default categories"
        )
    
    db.delete(category)
    db.commit()
    
    logger.info(f"Deleted category '{category.category_name}' for user {current_user.id}")
    
    return {"message": "Category deleted successfully"}

@router.post("/generate-ai-suggestions", dependencies=[Depends(verify_csrf_token)])
async def generate_ai_suggestions(
    request_data: AISuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered category suggestions based on user profile."""
    
    try:
        # Initialize AI category service
        ai_service = AICategoryService()
        
        # Get existing categories for this user
        existing_categories = db.query(UserCategory).filter(
            UserCategory.user_id == current_user.id
        ).all()
        
        # Convert to format expected by AI service
        existing_categories_data = []
        for cat in existing_categories:
            existing_categories_data.append({
                "id": str(cat.id),
                "name": cat.category_name,
                "type": cat.category_type,
                "color": cat.color,
                "description": cat.description,
                "weight": cat.weight
            })
        
        # Extract user profile data
        user_profile = {
            "missionStatement": request_data.missionStatement or {},
            "workStyle": request_data.workStyle or {},
            "productivityPatterns": request_data.productivityPatterns or {}
        }
        
        # Generate AI suggestions
        suggestions = await ai_service.generate_category_suggestions(
            user_profile=user_profile,
            existing_categories=existing_categories_data,
            user_id=current_user.id
        )
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Error generating AI suggestions for user {current_user.id}: {e}")
        
        # Return fallback suggestions
        return {
            "suggestions": [
                {
                    "id": "fallback-1",
                    "action": "create",
                    "category": {
                        "name": "Focus Time",
                        "type": "both",
                        "color": "#8b5cf6",
                        "emoji": "🧠",
                        "priority": 4,
                        "description": "Dedicated time for deep, focused work",
                        "weights": {
                            "importance": 0.8,
                            "urgency": 0.6,
                            "complexity": 0.7
                        }
                    },
                    "reasoning": "Focused work sessions are essential for productivity."
                }
            ]
        }

@router.post("/assign-color-emoji", dependencies=[Depends(verify_csrf_token)])
async def assign_color_emoji(
    request_data: AIColorEmojiRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered color and emoji assignment for a category."""
    
    try:
        # Initialize AI category service
        ai_service = AICategoryService()
        
        # Get user context (optional)
        user_context = request_data.userContext or {}
        
        # Generate color and emoji assignment
        assignment = await ai_service.assign_color_and_emoji(
            category_name=request_data.categoryName,
            category_type=request_data.categoryType,
            description=request_data.description or "",
            user_context=user_context
        )
        
        return {
            "color": assignment.get("color", "#6b7280"),
            "emoji": assignment.get("emoji", "📋"),
            "reasoning": assignment.get("reasoning", "AI-generated assignment")
        }
        
    except Exception as e:
        logger.error(f"Error assigning color/emoji for user {current_user.id}: {e}")
        
        # Return fallback assignment
        return {
            "color": "#6b7280",
            "emoji": "📋",
            "reasoning": "Fallback assignment due to error"
        }

async def initialize_default_categories(db: Session, user_id: int) -> List[UserCategory]:
    """Initialize default categories for a new user."""
    
    default_categories = [
        # Original categories
        {
            "name": "Work",
            "type": "both",
            "color": "#3b82f6",
            "weight": 0.8,
            "description": "Work-related tasks and meetings"
        },
        {
            "name": "Personal",
            "type": "both",
            "color": "#10b981",
            "weight": 0.6,
            "description": "Personal tasks and appointments"
        },
        {
            "name": "Health",
            "type": "both",
            "color": "#ef4444",
            "weight": 1.0,
            "description": "Health and wellness activities"
        },
        {
            "name": "Learning",
            "type": "both",
            "color": "#8b5cf6",
            "weight": 0.6,
            "description": "Learning and development activities"
        },
        {
            "name": "Social",
            "type": "both",
            "color": "#f59e0b",
            "weight": 0.4,
            "description": "Social events and gatherings"
        },
        
        # Admin calendar event types converted to user categories
        {
            "name": "Meeting",
            "type": "both",
            "color": "#0ea5e9",
            "weight": 1.0,  # Admin weight 1.0 = highest priority
            "description": "Business meetings and conferences"
        },
        {
            "name": "Appointment",
            "type": "both",
            "color": "#06b6d4",
            "weight": 0.9,  # Admin weight 0.9 = high priority
            "description": "Personal appointments and services"
        },
        {
            "name": "Task",
            "type": "both",
            "color": "#84cc16",
            "weight": 0.8,  # Admin weight 0.8 = high priority
            "description": "To-do items and deadlines"
        },
        {
            "name": "Reminder",
            "type": "event",
            "color": "#f97316",
            "weight": 0.7,  # Admin weight 0.7 = medium priority
            "description": "Reminders and notifications"
        },
        {
            "name": "Event",
            "type": "event",
            "color": "#a855f7",
            "weight": 0.6,  # Admin weight 0.6 = medium priority
            "description": "Social events and celebrations"
        }
    ]
    
    created_categories = []
    for cat_data in default_categories:
        category = UserCategory(
            id=uuid4(),
            user_id=user_id,
            category_name=cat_data["name"],
            category_type=cat_data["type"],
            weight=cat_data["weight"],
            color=cat_data["color"],
            description=cat_data["description"]
        )
        db.add(category)
        created_categories.append(category)
    
    db.commit()
    
    for cat in created_categories:
        db.refresh(cat)
    
    logger.info(f"Initialized {len(created_categories)} default categories for user {user_id}")
    return created_categories