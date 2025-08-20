"""
Tools for managing user profile data, including settings and preferences.
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# This is a simplified mapping. A real implementation would be more sophisticated.
KEYWORD_TO_EVENT_TYPE_MAP = {
    "writing": ["Deep Work", "Writing Session"],
    "book": ["Deep Work", "Writing Session", "Research"],
    "fitness": ["Workout", "Gym", "Running"],
    "health": ["Workout", "Meal Prep", "Meditation"],
    "learn": ["Study", "Reading", "Coursework"],
    "research": ["Research", "Reading"],
    "development": ["Deep Work", "Coding", "Learning"],
    "meeting": ["Meeting", "Team Sync", "Discussion"],
    "creative": ["Creative Work", "Design", "Brainstorming"],
    "planning": ["Planning", "Strategy", "Review"],
}

def update_calendar_weights_from_goals(goals: List[str], current_weights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates calendar event weights based on user goals.

    Args:
        goals: A list of the user's personal goals.
        current_weights: The user's current calendar event weights.

    Returns:
        The updated calendar event weights.
    """
    logger.info(f"Updating calendar weights for goals: {goals}")
    new_weights = current_weights.copy()
    
    for goal in goals:
        goal_lower = goal.lower()
        logger.debug(f"Processing goal: {goal}")
        
        for keyword, event_types in KEYWORD_TO_EVENT_TYPE_MAP.items():
            if keyword in goal_lower:
                logger.debug(f"Found keyword '{keyword}' in goal '{goal}'")
                for event_type in event_types:
                    old_weight = new_weights.get(event_type, 1.0)
                    new_weights[event_type] = old_weight + 0.5  # Increase weight
                    logger.debug(f"Updated weight for '{event_type}': {old_weight} -> {new_weights[event_type]}")

    logger.info(f"Final calendar weights: {new_weights}")
    return new_weights


def get_profile_summary(profile_data: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of user profile data.

    Args:
        profile_data: Dictionary containing user profile information.

    Returns:
        A formatted string summarizing the profile.
    """
    summary_parts = []
    
    # Basic information
    if profile_data.get("display_name") or profile_data.get("first_name"):
        name = profile_data.get("display_name") or f"{profile_data.get('first_name', '')} {profile_data.get('last_name', '')}".strip()
        summary_parts.append(f"Name: {name}")
    
    # Professional information
    if profile_data.get("job_title"):
        job_info = profile_data["job_title"]
        if profile_data.get("company"):
            job_info += f" at {profile_data['company']}"
        summary_parts.append(f"Role: {job_info}")
    
    # Contact preferences
    if profile_data.get("preferred_contact_method"):
        summary_parts.append(f"Preferred contact: {profile_data['preferred_contact_method']}")
    
    # Location/timezone
    if profile_data.get("timezone"):
        summary_parts.append(f"Timezone: {profile_data['timezone']}")
    
    # Bio
    if profile_data.get("bio"):
        summary_parts.append(f"Bio: {profile_data['bio']}")
    
    return "\n".join(summary_parts) if summary_parts else "No profile information available"


def extract_goals_from_profile(profile_data: Dict[str, Any]) -> List[str]:
    """
    Extract goals from various profile fields.

    Args:
        profile_data: Dictionary containing user profile information.

    Returns:
        A list of extracted goals.
    """
    goals = []
    
    # Extract from bio
    if profile_data.get("bio"):
        bio = profile_data["bio"].lower()
        # Simple keyword extraction - in a real implementation, this would be more sophisticated
        goal_keywords = ["want to", "goal", "aim", "objective", "focus on", "improve", "learn", "develop"]
        for keyword in goal_keywords:
            if keyword in bio:
                # Extract context around the keyword
                sentences = bio.split('.')
                for sentence in sentences:
                    if keyword in sentence:
                        goals.append(sentence.strip())
    
    # Extract from job title/company (work-related goals)
    if profile_data.get("job_title"):
        job_title = profile_data["job_title"].lower()
        if any(tech in job_title for tech in ["developer", "engineer", "programmer"]):
            goals.append("improve technical skills")
        if any(mgmt in job_title for mgmt in ["manager", "lead", "director"]):
            goals.append("develop leadership skills")
    
    return goals


def validate_profile_completeness(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate profile completeness and suggest improvements.

    Args:
        profile_data: Dictionary containing user profile information.

    Returns:
        Dictionary with completeness score and suggestions.
    """
    required_fields = ["first_name", "last_name", "display_name"]
    important_fields = ["job_title", "company", "timezone", "preferred_contact_method"]
    optional_fields = ["bio", "website", "linkedin", "github", "phone_number"]
    
    total_fields = len(required_fields) + len(important_fields) + len(optional_fields)
    completed_fields = 0
    missing_required = []
    missing_important = []
    suggestions = []
    
    # Check required fields
    for field in required_fields:
        if profile_data.get(field):
            completed_fields += 1
        else:
            missing_required.append(field)
    
    # Check important fields
    for field in important_fields:
        if profile_data.get(field):
            completed_fields += 1
        else:
            missing_important.append(field)
    
    # Check optional fields
    for field in optional_fields:
        if profile_data.get(field):
            completed_fields += 1
    
    # Generate suggestions
    if missing_required:
        suggestions.append(f"Please complete required fields: {', '.join(missing_required)}")
    
    if missing_important:
        suggestions.append(f"Consider adding: {', '.join(missing_important)}")
    
    if not profile_data.get("bio"):
        suggestions.append("Add a bio to help the AI understand your goals and preferences")
    
    if not profile_data.get("timezone"):
        suggestions.append("Set your timezone for better calendar integration")
    
    completeness_score = (completed_fields / total_fields) * 100
    
    return {
        "completeness_score": round(completeness_score, 1),
        "completed_fields": completed_fields,
        "total_fields": total_fields,
        "missing_required": missing_required,
        "missing_important": missing_important,
        "suggestions": suggestions
    }
