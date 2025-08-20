"""
Focus Nudge API Router

Handles the AI feedback loop for desktop client focus management:
1. Receives usage/notification data from desktop client
2. Processes data through AI analysis
3. Sends Focus Nudge events back to client via WebSocket
"""

import logging
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import User
from ..progress_manager import progress_manager
from worker.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_mission_statement(user_id: int, db: Session) -> Optional[str]:
    user = db.query(User).filter(User.id == user_id).first()
    return user.mission_statement if user else None


# === Data Models ===

class NotificationInteraction(BaseModel):
    """Model for notification interaction data from desktop client"""
    notification_id: str
    action: str = Field(..., description="'clicked', 'dismissed', 'ignored', 'actioned'")
    timestamp: datetime
    response_time_ms: Optional[int] = Field(None, description="Time to respond in milliseconds")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class UsageData(BaseModel):
    """Model for desktop usage data from client"""
    timestamp: datetime
    active_application: Optional[str] = None
    window_title: Optional[str] = None
    session_duration_ms: int = Field(..., description="Duration of current session in milliseconds")
    idle_time_ms: int = Field(default=0, description="Idle time in milliseconds")
    focus_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Client-calculated focus score")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UIAction(BaseModel):
    """Model for UI actions to be performed by the client"""
    action_type: str
    target_package: Optional[str] = None
    destination_popup_name: Optional[str] = None
    payload: Optional[List[Dict[str, Any]]] = None

class FocusNudgeEvent(BaseModel):
    """Model for Focus Nudge events sent to desktop client"""
    nudge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = Field(..., description="'reminder', 'suggestion', 'warning', 'celebration', 'ui_action'")
    message: str = Field(..., description="Human-readable nudge message")
    priority: str = Field(default="medium", description="'low', 'medium', 'high', 'urgent'")
    action_required: bool = Field(default=False)
    suggested_actions: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ui_action: Optional[UIAction] = None


class BatchUsageReport(BaseModel):
    """Batch report of usage data and notification interactions"""
    client_id: str = Field(..., description="Unique client identifier")
    report_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    usage_data: List[UsageData] = Field(default_factory=list)
    notification_interactions: List[NotificationInteraction] = Field(default_factory=list)
    system_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

class NotificationData(BaseModel):
    package_name: str
    title: str
    text: str
    category: str

class ClassifyNotificationRequest(BaseModel):
    client_id: str
    notification: NotificationData

class NudgeFeedbackRequest(BaseModel):
    nudge_id: str
    action: str
    effectiveness_rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = None

# === API Endpoints ===

@router.post("/usage-data", response_model=Dict[str, Any])
async def submit_usage_data(
    usage_report: BatchUsageReport,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint for desktop client to submit usage data and notification interactions.
    
    This is the primary data ingestion endpoint for the AI feedback loop.
    The client should call this periodically (e.g., every 5-10 minutes) with 
    collected usage data and notification interaction history.
    """
    try:
        logger.info(f"Received usage data from user {current_user.id}, client {usage_report.client_id}")
        logger.debug(f"Usage data points: {len(usage_report.usage_data)}, "
                    f"Notification interactions: {len(usage_report.notification_interactions)}")
        
        # Process the data in background to avoid blocking the client
        background_tasks.add_task(
            process_usage_data_and_generate_nudges,
            user_id=current_user.id,
            usage_report=usage_report,
            db=db
        )
        
        return {
            "status": "received",
            "message": "Usage data received successfully",
            "report_id": str(uuid.uuid4()),
            "processed_usage_points": len(usage_report.usage_data),
            "processed_notifications": len(usage_report.notification_interactions),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing usage data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process usage data"
        )


@router.get("/nudge-history", response_model=List[Dict[str, Any]])
async def get_nudge_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent focus nudges sent to this user.
    Useful for desktop client to sync missed nudges after reconnection.
    """
    try:
        # In a real implementation, this would fetch from a nudge history table
        # For now, return empty list as placeholder
        logger.info(f"Fetching nudge history for user {current_user.id}")
        
        return []
        
    except Exception as e:
        logger.error(f"Error fetching nudge history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch nudge history"
        )


@router.post("/nudge-feedback", response_model=Dict[str, str])
async def submit_nudge_feedback(
    feedback: NudgeFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint for desktop client to provide feedback on Focus Nudges.
    
    This helps the AI learn what types of nudges are most effective for each user.
    
    Args:
        nudge_id: ID of the nudge being responded to
        action: User action ('acknowledged', 'dismissed', 'acted_upon', 'ignored')
        effectiveness_rating: Optional 1-5 rating of nudge effectiveness
        feedback_text: Optional free-form feedback
    """
    try:
        logger.info(f"Received nudge feedback from user {current_user.id}: "
                   f"nudge_id={feedback.nudge_id}, action={feedback.action}")
        
        # Store feedback for AI learning (would be implemented with a feedback table)
        # This helps improve future nudge generation
        
        return {
            "status": "received",
            "message": "Feedback recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error processing nudge feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process nudge feedback"
        )


@router.get("/focus-analytics", response_model=Dict[str, Any])
async def get_focus_analytics(
    timeframe_hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get focus analytics and insights for the user.
    
    This endpoint provides aggregated insights from the collected usage data,
    which can be displayed in the desktop client or web interface.
    """
    try:
        logger.info(f"Generating focus analytics for user {current_user.id}, timeframe: {timeframe_hours}h")
        
        # Placeholder analytics - in real implementation, this would analyze stored usage data
        analytics = {
            "timeframe_hours": timeframe_hours,
            "focus_score_average": 0.75,
            "productive_hours": 6.5,
            "distraction_incidents": 12,
            "top_distracting_apps": [
                {"app": "Social Media", "time_spent_minutes": 45},
                {"app": "News Websites", "time_spent_minutes": 30}
            ],
            "focus_trends": {
                "morning": 0.85,
                "afternoon": 0.70,
                "evening": 0.60
            },
            "nudge_effectiveness": {
                "total_nudges_sent": 8,
                "acknowledged": 6,
                "acted_upon": 4,
                "average_rating": 4.2
            }
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error generating focus analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate focus analytics"
        )


# === Background Processing ===

async def process_usage_data_and_generate_nudges(
    user_id: int,
    usage_report: BatchUsageReport,
    db: Session
):
    """
    Background task to process usage data and generate focus nudges.
    
    This is where the AI analysis happens:
    1. Analyze usage patterns
    2. Detect focus issues or opportunities
    3. Generate appropriate nudges
    4. Send nudges via WebSocket to desktop client
    """
    try:
        logger.info(f"Processing usage data for user {user_id}")
        
        mission_statement = await get_mission_statement(user_id, db)

        # Analyze usage patterns
        focus_issues = analyze_usage_patterns(usage_report.usage_data)
        
        # Generate nudges based on analysis
        nudges = await generate_focus_nudges(focus_issues, usage_report.notification_interactions, mission_statement)
        
        # Send nudges to client via WebSocket
        for nudge in nudges:
            await send_focus_nudge_to_client(user_id, usage_report.client_id, nudge)
        
        # Placeholder for app ranking generation
        ranked_apps = [
            "com.spotify.music",
            "com.google.android.apps.maps",
            "com.whatsapp"
        ]
        await progress_manager.send_app_ranking_update(usage_report.client_id, ranked_apps)
        
        logger.info(f"Generated and sent {len(nudges)} focus nudges for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing usage data for user {user_id}: {e}", exc_info=True)


def analyze_usage_patterns(usage_data: List[UsageData]) -> List[Dict[str, Any]]:
    """
    Analyze usage data to identify focus issues and opportunities.
    
    This is a simplified version - in production, this would use sophisticated
    AI models to detect patterns, predict focus lapses, and identify optimal
    intervention moments.
    """
    issues = []
    
    if not usage_data:
        return issues
    
    # Simple pattern detection examples
    total_idle_time = sum(data.idle_time_ms for data in usage_data)
    avg_focus_score = sum(data.focus_score or 0.5 for data in usage_data) / len(usage_data)
    
    if total_idle_time > 30 * 60 * 1000:  # More than 30 minutes idle
        issues.append({
            "type": "extended_idle",
            "severity": "medium",
            "data": {"idle_time_ms": total_idle_time}
        })
    
    if avg_focus_score < 0.4:  # Low focus score
        issues.append({
            "type": "low_focus",
            "severity": "high",
            "data": {"focus_score": avg_focus_score}
        })
    
    # Detect frequent app switching (distraction indicator)
    app_switches = len(set(data.active_application for data in usage_data if data.active_application))
    if app_switches > 10:
        issues.append({
            "type": "frequent_switching",
            "severity": "medium",
            "data": {"switch_count": app_switches}
        })
    
    return issues


async def generate_focus_nudges(
    focus_issues: List[Dict[str, Any]], 
    notification_history: List[NotificationInteraction],
    mission_statement: Optional[str]
) -> List[FocusNudgeEvent]:
    """
    Generate appropriate focus nudges based on detected issues.
    
    This would use AI to generate personalized, contextually appropriate nudges.
    """
    nudges = []
    ollama_service = OllamaService()
    
    for issue in focus_issues:
        issue_type = issue["type"]
        severity = issue["severity"]
        
        prompt = f"""You are a helpful AI assistant.
        Your task is to generate a focus nudge for a user based on their current focus issue and mission statement.
        The user's mission statement is: {mission_statement}
        The current focus issue is: {issue_type} with severity {severity}.
        Please generate a short, actionable nudge message and up to 3 suggested actions.
        The response should be in the following JSON format:
        {{
            "message": "<nudge message>",
            "suggested_actions": [
                "<action 1>",
                "<action 2>",
                "<action 3>"
            ]
        }}
        """
        
        response = await ollama_service.invoke_llm(prompt)
        try:
            nudge_data = json.loads(response)
            nudges.append(FocusNudgeEvent(
                type="suggestion",
                message=nudge_data["message"],
                priority=severity,
                suggested_actions=nudge_data["suggested_actions"]
            ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing LLM response for nudge generation: {e}")

    
    # Avoid overwhelming the user
    if len(nudges) > 2:
        nudges = nudges[:2]  # Limit to 2 nudges at a time
    
    return nudges


async def send_focus_nudge_to_client(user_id: int, client_id: str, nudge: FocusNudgeEvent):
    """
    Send a focus nudge to the desktop client via WebSocket.
    
    This uses the existing WebSocket infrastructure to push real-time nudges.
    """
    try:
        # Create the message to send via WebSocket
        message = {
            "type": "focus_nudge",
            "client_id": client_id,
            "nudge": nudge.dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send via WebSocket using the existing progress manager
        # The session_id would typically be the client_id or a derived session identifier
        session_id = f"focus_client_{client_id}"
        
        # Use the progress manager to send the nudge
        await progress_manager.send_update(session_id, message)
        
        logger.info(f"Sent focus nudge {nudge.nudge_id} to user {user_id}, client {client_id}")
        
    except Exception as e:
        logger.error(f"Error sending focus nudge to client: {e}", exc_info=True)


# === Health Check Endpoint ===

@router.get("/check-pending/{client_id}")
async def check_pending_nudges(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check for pending nudges and app ranking updates.
    """
    # This is a placeholder implementation.
    # In a real application, you would fetch this data from the database.
    return {
        "has_pending_nudges": False,
        "nudges": [],
        "ranked_favorites": [
            "com.spotify.music",
            "com.google.android.apps.maps",
            "com.whatsapp"
        ],
        "next_check_in_minutes": 15
    }

@router.post("/classify-notification")
async def classify_notification(
    request: ClassifyNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Classifies a notification as either 'SHOW_IMMEDIATELY' or 'SUMMARIZE'"""
    mission_statement = await get_mission_statement(current_user.id, db)
    ollama_service = OllamaService()

    prompt = f"""You are a helpful AI assistant.
    Your task is to classify a notification as either 'SHOW_IMMEDIATELY' or 'SUMMARIZE' based on the user's mission statement and the notification content.
    The user's mission statement is: {mission_statement}
    The notification is from the app: {request.notification.package_name}
    Title: {request.notification.title}
    Text: {request.notification.text}
    Category: {request.notification.category}
    Please respond with only 'SHOW_IMMEDIATELY' or 'SUMMARIZE'.
    """

    decision = await ollama_service.invoke_llm(prompt)
    
    return {"decision": decision.strip()}


@router.get("/health", response_model=Dict[str, str])
async def focus_nudge_health_check():
    """Health check endpoint for the Focus Nudge system"""
    return {
        "status": "healthy",
        "service": "focus_nudge_api",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }