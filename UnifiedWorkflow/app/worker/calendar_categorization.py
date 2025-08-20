#!/usr/bin/env python3
"""
Calendar categorization and color mapping utilities.
Handles automatic categorization of events and mapping categories to Google Calendar colors.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

from shared.database.models._models import UserCategory, User
from worker.services.ollama_service import invoke_llm
from worker.celery_app import _db_state
from worker.shared_constants import AVAILABLE_CATEGORIES

logger = logging.getLogger(__name__)


def get_user_categories_for_categorization(user_id: Optional[int] = None) -> Tuple[List[str], Dict[str, Dict[str, float]]]:
    """
    Get user's categories for event categorization.
    
    Args:
        user_id: User ID for personalized categories
    
    Returns:
        Tuple of (category_names_list, category_weights_dict)
    """
    if not user_id:
        # Return default categories
        default_categories = list(AVAILABLE_CATEGORIES)
        default_weights = {cat: {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5} 
                          for cat in default_categories}
        return default_categories, default_weights
    
    try:
        with get_db_session() as db:
            # Get user's custom categories
            user_categories = db.query(UserCategory).filter(
                UserCategory.user_id == user_id,
                UserCategory.category_type.in_(["event", "both"])  # Only event-applicable categories
            ).all()
            
            if not user_categories:
                # User has no custom categories, return defaults
                default_categories = list(AVAILABLE_CATEGORIES)
                default_weights = {cat: {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5} 
                                  for cat in default_categories}
                return default_categories, default_weights
            
            categories = []
            weights = {}
            
            for cat in user_categories:
                categories.append(cat.category_name)
                
                # Extract weights, with defaults if not set
                cat_weights = cat.weights or {}
                weights[cat.category_name] = {
                    "flexibility": cat_weights.get("flexibility", 0.5),
                    "importance": cat_weights.get("importance", 0.5), 
                    "urgency": cat_weights.get("urgency", 0.5),
                    "complexity": cat_weights.get("complexity", 0.5)
                }
            
            # Always ensure "Default" category exists as fallback
            if "Default" not in categories:
                categories.append("Default")
                weights["Default"] = {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5}
            
            return categories, weights
            
    except Exception as e:
        logger.error(f"Error getting user categories: {e}")
        # Fallback to default categories
        default_categories = list(AVAILABLE_CATEGORIES)
        default_weights = {cat: {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5} 
                          for cat in default_categories}
        return default_categories, default_weights


def create_dynamic_categorization_prompt(categories: List[str]) -> str:
    """
    Create a dynamic system prompt that includes user's actual categories.
    
    Args:
        categories: List of category names
    
    Returns:
        Dynamic system prompt string
    """
    categories_text = "\n".join([f"- {cat}" for cat in sorted(categories)])
    
    return f"""You are an expert event categorizer. Your task is to analyze the summary and description of a calendar event and assign it to one of the following categories.

Output ONLY the category name. Do not add any other text, explanation, or punctuation.

Available Categories:
{categories_text}

CRITICAL CONSTRAINTS:
- Your response must consist of ONLY the category name from the list above
- Choose the single most appropriate category based on the event content
- If the event does not clearly fit into any specific category, use "Default"
- Do not create new categories or modify existing ones"""


@contextmanager
def get_db_session():
    """Provides a transactional scope around a series of database operations."""
    if "session_factory" not in _db_state:
        raise RuntimeError("Database session factory not initialized in worker.")

    session = _db_state["session_factory"]()
    try:
        yield session
    finally:
        session.close()


# Google Calendar color ID mapping
# These are the standard Google Calendar color IDs that users can see in the UI
GOOGLE_CALENDAR_COLORS = {
    # Standard colors
    "1": "#a4bdfc",   # Lavender (light blue)
    "2": "#7ae7bf",   # Sage (light green)
    "3": "#dbadff",   # Grape (light purple)
    "4": "#ff887c",   # Flamingo (light red)
    "5": "#fbd75b",   # Banana (yellow)
    "6": "#ffb878",   # Tangerine (orange)
    "7": "#46d6db",   # Peacock (cyan)
    "8": "#e1e1e1",   # Graphite (gray)
    "9": "#5484ed",   # Blueberry (blue)
    "10": "#51b749",  # Basil (green)
    "11": "#dc2127",  # Tomato (red)
}

# Category to Google Calendar color mapping
CATEGORY_COLOR_MAPPING = {
    "Work": "9",        # Blueberry (professional blue)
    "Health": "11",     # Tomato (attention-grabbing red)
    "Leisure": "3",     # Grape (relaxing purple)
    "Family": "5",      # Banana (warm yellow)
    "Fitness": "10",    # Basil (energetic green)
    "Default": "8",     # Graphite (neutral gray)
    
    # Additional user-defined categories - fallback colors
    "Meeting": "9",     # Blueberry (professional)
    "Appointment": "7", # Peacock (distinguishable)
    "Task": "10",       # Basil (actionable)
    "Reminder": "6",    # Tangerine (attention)
    "Event": "2",       # Sage (social)
    "Personal": "1",    # Lavender (personal)
    "Learning": "4",    # Flamingo (engaging)
    "Social": "6",      # Tangerine (social)
}


async def categorize_event(summary: str, description: str = "", user_id: Optional[int] = None) -> Tuple[str, str, Dict[str, float]]:
    """
    Categorize an event based on its summary and description.
    
    Args:
        summary: Event title/summary
        description: Event description (optional)
        user_id: User ID for personalized categorization (optional)
    
    Returns:
        Tuple of (category_name, color_id, category_weights)
    """
    logger.info(f"Categorizing event: '{summary}'")
    
    try:
        # Get user's categories and weights
        user_categories, category_weights = get_user_categories_for_categorization(user_id)
        
        # Get user's selected model if available
        selected_model = "llama3.2:3b"  # Default
        
        if user_id:
            try:
                with get_db_session() as db:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user and user.settings and user.settings.get("selected_model"):
                        selected_model = user.settings.get("selected_model")
            except Exception as e:
                logger.warning(f"Could not get user model preference: {e}")
        
        # Create dynamic system prompt with user's categories
        dynamic_prompt = create_dynamic_categorization_prompt(user_categories)
        
        # Use LLM to categorize
        messages = [
            {"role": "system", "content": dynamic_prompt},
            {
                "role": "user",
                "content": f"Event Summary: {summary}\nEvent Description: {description or 'No description provided'}",
            },
        ]
        
        try:
            llm_response = await asyncio.wait_for(
                invoke_llm(messages, model_name=selected_model),
                timeout=10.0
            )
            category = llm_response.strip()
            
            # Validate category against user's categories
            if category in user_categories:
                color_id = get_color_for_category(category, user_id)
                weights = category_weights.get(category, {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5})
                logger.info(f"LLM categorized event '{summary}' as: {category} (color: {color_id}, flexibility: {weights['flexibility']:.2f})")
                return category, color_id, weights
        except asyncio.TimeoutError:
            logger.warning(f"LLM categorization timeout for event '{summary}'")
        except Exception as e:
            logger.warning(f"LLM categorization failed for event '{summary}': {e}")
        
        # Fallback to keyword-based categorization
        category = categorize_by_keywords(summary, description, user_categories)
        color_id = get_color_for_category(category, user_id)
        weights = category_weights.get(category, {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5})
        
        logger.info(f"Keyword-based categorization: '{summary}' -> {category} (color: {color_id}, flexibility: {weights['flexibility']:.2f})")
        return category, color_id, weights
        
    except Exception as e:
        logger.error(f"Error categorizing event '{summary}': {e}")
        default_weights = {"flexibility": 0.5, "importance": 0.5, "urgency": 0.5, "complexity": 0.5}
        return "Default", get_color_for_category("Default", user_id), default_weights


def categorize_by_keywords(summary: str, description: str = "", user_categories: List[str] = None) -> str:
    """
    Fallback keyword-based categorization using user's categories.
    
    Args:
        summary: Event title
        description: Event description
        user_categories: List of user's categories
    
    Returns:
        Category name
    """
    if not user_categories:
        user_categories = list(AVAILABLE_CATEGORIES)
        
    text = f"{summary} {description}".lower()
    
    # Default keyword mappings (fallback to common patterns)
    default_keywords = {
        "work": ["meeting", "conference", "call", "standup", "review", "project", 
                 "client", "team", "work", "business", "office", "deadline"],
        "health": ["doctor", "dentist", "appointment", "medical", "therapy", 
                   "checkup", "hospital", "clinic", "prescription"],
        "fitness": ["gym", "workout", "exercise", "run", "yoga", "fitness", 
                    "training", "sport", "swimming", "cycling"],
        "family": ["family", "kids", "children", "school", "parent", "dinner", 
                   "birthday", "anniversary", "wedding"],
        "leisure": ["movie", "concert", "party", "vacation", "travel", "hobby", 
                    "game", "entertainment", "fun", "relaxation"]
    }
    
    # Map user categories to keyword sets (case-insensitive matching)
    category_scores = {}
    
    for category in user_categories:
        if category.lower() == "default":
            continue
            
        # Try to match with default keyword sets
        matched_keywords = default_keywords.get(category.lower(), [])
        
        # If no default keywords, use the category name itself as keyword
        if not matched_keywords:
            matched_keywords = [category.lower()]
        
        # Count matches
        score = sum(1 for keyword in matched_keywords if keyword in text)
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score, or Default if no matches
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        return best_category
    else:
        return "Default"


def get_color_for_category(category: str, user_id: Optional[int] = None) -> str:
    """
    Get Google Calendar color ID for a category.
    
    Args:
        category: Category name
        user_id: User ID for personalized colors (optional)
    
    Returns:
        Google Calendar color ID (string)
    """
    try:
        # First try user-specific custom categories if user_id provided
        if user_id:
            user_color = get_user_category_color(category, user_id)
            if user_color:
                return user_color
        
        # Fall back to default mapping
        return CATEGORY_COLOR_MAPPING.get(category, CATEGORY_COLOR_MAPPING["Default"])
        
    except Exception as e:
        logger.error(f"Error getting color for category '{category}': {e}")
        return CATEGORY_COLOR_MAPPING["Default"]


def get_user_category_color(category: str, user_id: int) -> Optional[str]:
    """
    Get user-specific color for a category from their custom categories.
    
    Args:
        category: Category name
        user_id: User ID
    
    Returns:
        Google Calendar color ID or None if not found
    """
    try:
        with get_db_session() as db:
            user_category = db.query(UserCategory).filter(
                UserCategory.user_id == user_id,
                UserCategory.category_name == category
            ).first()
            
            if user_category and user_category.color:
                # Convert hex color to closest Google Calendar color ID
                return hex_to_google_color_id(user_category.color)
                
    except Exception as e:
        logger.error(f"Error getting user category color: {e}")
    
    return None


def hex_to_google_color_id(hex_color: str) -> str:
    """
    Convert a hex color to the closest Google Calendar color ID.
    
    Args:
        hex_color: Hex color code (e.g., "#3b82f6")
    
    Returns:
        Google Calendar color ID
    """
    if not hex_color or not hex_color.startswith("#"):
        return CATEGORY_COLOR_MAPPING["Default"]
    
    # Simple color mapping based on common colors
    hex_lower = hex_color.lower()
    
    # Blue family
    if hex_lower in ["#3b82f6", "#0ea5e9", "#2563eb", "#1d4ed8"]:
        return "9"  # Blueberry
    
    # Green family  
    elif hex_lower in ["#10b981", "#84cc16", "#059669", "#16a34a"]:
        return "10"  # Basil
    
    # Red family
    elif hex_lower in ["#ef4444", "#dc2626", "#b91c1c", "#991b1b"]:
        return "11"  # Tomato
    
    # Purple family
    elif hex_lower in ["#8b5cf6", "#a855f7", "#7c3aed", "#6d28d9"]:
        return "3"  # Grape
    
    # Orange family
    elif hex_lower in ["#f97316", "#fb923c", "#ea580c", "#c2410c"]:
        return "6"  # Tangerine
    
    # Yellow family
    elif hex_lower in ["#fbbf24", "#eab308", "#ca8a04", "#a16207"]:
        return "5"  # Banana
    
    # Cyan family
    elif hex_lower in ["#06b6d4", "#0891b2", "#0e7490", "#155e75"]:
        return "7"  # Peacock
    
    # Pink family
    elif hex_lower in ["#ec4899", "#f472b6", "#db2777", "#be185d"]:
        return "4"  # Flamingo
    
    # Light colors
    elif hex_lower in ["#a4bdfc", "#7ae7bf"]:
        return "1"  # Lavender or Sage
    
    # Default gray
    else:
        return "8"  # Graphite


def create_event_description_with_category(original_description: str, category: str) -> str:
    """
    Add category tag to event description for identification.
    
    Args:
        original_description: Original event description
        category: Category name
    
    Returns:
        Description with category tag
    """
    category_tag = f"[Category: {category}]"
    
    if original_description:
        return f"{original_description}\n\n{category_tag}"
    else:
        return category_tag


def extract_category_from_description(description: str) -> Optional[str]:
    """
    Extract category from event description if it exists.
    
    Args:
        description: Event description
    
    Returns:
        Category name or None if not found
    """
    if not description:
        return None
    
    # Look for category tag
    import re
    match = re.search(r'\[Category:\s*([^\]]+)\]', description)
    
    if match:
        return match.group(1).strip()
    
    return None