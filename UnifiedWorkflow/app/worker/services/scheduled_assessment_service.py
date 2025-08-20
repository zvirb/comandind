# worker/services/scheduled_assessment_service.py
"""
Scheduled Assessment Service - Background task system for user assessments.
Moves resource-intensive assessments away from real-time chat processing.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from shared.database.models import User
from shared.utils.config import get_settings
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)
settings = get_settings()


class AssessmentType(Enum):
    MISSION_ALIGNMENT = "mission_alignment"
    WORK_STYLE_EVOLUTION = "work_style_evolution"
    PRODUCTIVITY_PATTERNS = "productivity_patterns"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    TASK_COMPLEXITY_ANALYSIS = "task_complexity_analysis"


@dataclass
class AssessmentSchedule:
    user_id: int
    assessment_type: AssessmentType
    frequency_hours: int  # How often to run (in hours)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True


@dataclass
class AssessmentResult:
    user_id: int
    assessment_type: AssessmentType
    timestamp: datetime
    results: Dict[str, Any]
    confidence_score: float
    insights: List[str]
    recommendations: List[str]


class ScheduledAssessmentService:
    """
    Service for running periodic assessments in the background.
    Replaces real-time assessments that were causing chat bottlenecks.
    """
    
    def __init__(self):
        self.schedules: Dict[int, List[AssessmentSchedule]] = {}
        self.results_cache: Dict[int, List[AssessmentResult]] = {}
        self.running = False
        self.task_handle = None
        self.qdrant_service = QdrantService()
    
    def add_user_schedule(self, user_id: int, assessment_configs: List[Dict[str, Any]]):
        """
        Add assessment schedules for a user.
        """
        if user_id not in self.schedules:
            self.schedules[user_id] = []
        
        for config in assessment_configs:
            schedule = AssessmentSchedule(
                user_id=user_id,
                assessment_type=AssessmentType(config["type"]),
                frequency_hours=config.get("frequency_hours", 24),
                last_run=None,
                next_run=datetime.now(),
                enabled=config.get("enabled", True)
            )
            self.schedules[user_id].append(schedule)
        
        logger.info(f"Added {len(assessment_configs)} assessment schedules for user {user_id}")
    
    def get_default_schedules(self) -> List[Dict[str, Any]]:
        """
        Get default assessment schedules for new users.
        """
        return [
            {
                "type": "mission_alignment",
                "frequency_hours": 168,  # Weekly
                "enabled": True
            },
            {
                "type": "productivity_patterns", 
                "frequency_hours": 72,   # Every 3 days
                "enabled": True
            },
            {
                "type": "confidence_calibration",
                "frequency_hours": 24,   # Daily
                "enabled": True
            }
        ]
    
    async def start_scheduler(self):
        """
        Start the background assessment scheduler.
        """
        if self.running:
            logger.warning("Assessment scheduler already running")
            return
        
        self.running = True
        self.task_handle = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduled assessment service started")
    
    async def stop_scheduler(self):
        """
        Stop the background assessment scheduler.
        """
        if not self.running:
            return
        
        self.running = False
        if self.task_handle:
            self.task_handle.cancel()
            try:
                await self.task_handle
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduled assessment service stopped")
    
    async def _scheduler_loop(self):
        """
        Main scheduler loop that runs assessments at scheduled times.
        """
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check all user schedules
                for user_id, user_schedules in self.schedules.items():
                    for schedule in user_schedules:
                        if (schedule.enabled and 
                            schedule.next_run and 
                            current_time >= schedule.next_run):
                            
                            try:
                                # Run the assessment
                                result = await self._run_assessment(user_id, schedule.assessment_type)
                                if result:
                                    # Store result
                                    if user_id not in self.results_cache:
                                        self.results_cache[user_id] = []
                                    self.results_cache[user_id].append(result)
                                    
                                    # Keep only last 50 results per user
                                    self.results_cache[user_id] = self.results_cache[user_id][-50:]
                                
                                # Update schedule for next run
                                schedule.last_run = current_time
                                schedule.next_run = current_time + timedelta(hours=schedule.frequency_hours)
                                
                                logger.info(f"Completed {schedule.assessment_type.value} assessment for user {user_id}")
                                
                            except Exception as e:
                                logger.error(f"Error running assessment {schedule.assessment_type.value} for user {user_id}: {e}")
                                # Still update next run time to avoid continuous failures
                                schedule.next_run = current_time + timedelta(hours=1)  # Retry in 1 hour
                
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _run_assessment(self, user_id: int, assessment_type: AssessmentType) -> Optional[AssessmentResult]:
        """
        Run a specific assessment for a user.
        """
        try:
            # Get user's recent activity/context from Qdrant
            user_context = await self._get_user_context(user_id)
            
            # Run assessment based on type
            if assessment_type == AssessmentType.MISSION_ALIGNMENT:
                result_data = await self._assess_mission_alignment(user_id, user_context)
            elif assessment_type == AssessmentType.PRODUCTIVITY_PATTERNS:
                result_data = await self._assess_productivity_patterns(user_id, user_context)
            elif assessment_type == AssessmentType.CONFIDENCE_CALIBRATION:
                result_data = await self._assess_confidence_calibration(user_id, user_context)
            else:
                logger.warning(f"Unknown assessment type: {assessment_type}")
                return None
            
            if result_data:
                return AssessmentResult(
                    user_id=user_id,
                    assessment_type=assessment_type,
                    timestamp=datetime.now(),
                    results=result_data["results"],
                    confidence_score=result_data["confidence_score"],
                    insights=result_data["insights"],
                    recommendations=result_data["recommendations"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error running {assessment_type.value} assessment for user {user_id}: {e}")
            return None
    
    async def _get_user_context(self, user_id: int) -> Dict[str, Any]:
        """
        Get user context from recent interactions.
        """
        try:
            # Get recent interactions from Qdrant
            recent_interactions = await self.qdrant_service.search_similar(
                query_vector=[0.0] * 384,  # Placeholder - would use actual embedding
                filter_conditions={"user_id": user_id},
                limit=20
            )
            
            return {
                "recent_interactions": len(recent_interactions),
                "interaction_topics": [],  # Would analyze topics from interactions
                "usage_patterns": {},      # Would analyze usage patterns
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}")
            return {"error": str(e)}
    
    async def _assess_mission_alignment(self, user_id: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess how well user's activities align with their stated mission.
        """
        prompt = f"""
        Analyze user alignment with their personal mission based on their recent activity patterns:
        
        Context: {context}
        
        Provide assessment in JSON format:
        {{
            "alignment_score": 0.0-1.0,
            "alignment_areas": ["area1", "area2"],
            "misalignment_areas": ["area1", "area2"],
            "confidence_score": 0.0-1.0,
            "insights": ["insight1", "insight2"],
            "recommendations": ["rec1", "rec2"]
        }}
        """
        
        try:
            response, _ = await invoke_llm_with_tokens(
                model="llama3.2:3b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            import json
            result_data = json.loads(response)
            
            return {
                "results": result_data,
                "confidence_score": result_data.get("confidence_score", 0.5),
                "insights": result_data.get("insights", []),
                "recommendations": result_data.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error(f"Error in mission alignment assessment: {e}")
            return {
                "results": {"error": str(e)},
                "confidence_score": 0.0,
                "insights": [],
                "recommendations": []
            }
    
    async def _assess_productivity_patterns(self, user_id: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess user's productivity patterns and suggest optimizations.
        """
        # Simplified assessment - in production would analyze actual usage data
        return {
            "results": {
                "productivity_score": 0.7,
                "peak_hours": ["9-11", "14-16"],
                "efficiency_trends": "improving",
                "bottlenecks": ["email", "meetings"]
            },
            "confidence_score": 0.6,
            "insights": [
                "Productivity peaks in morning hours",
                "Afternoon efficiency could be improved"
            ],
            "recommendations": [
                "Schedule important tasks during peak hours",
                "Consider time-blocking for deep work"
            ]
        }
    
    async def _assess_confidence_calibration(self, user_id: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess how well-calibrated the user's confidence is with actual outcomes.
        """
        # Simplified assessment - would analyze prediction vs outcome data
        return {
            "results": {
                "calibration_score": 0.65,
                "overconfidence_areas": ["time estimation"],
                "underconfidence_areas": ["technical skills"],
                "prediction_accuracy": 0.72
            },
            "confidence_score": 0.5,
            "insights": [
                "Slight overconfidence in time estimation",
                "Underestimates technical capabilities"
            ],
            "recommendations": [
                "Use time tracking to improve estimates",
                "Keep achievement log to build confidence"
            ]
        }
    
    def get_user_assessment_results(
        self, 
        user_id: int, 
        assessment_type: Optional[AssessmentType] = None,
        limit: int = 10
    ) -> List[AssessmentResult]:
        """
        Get recent assessment results for a user.
        """
        if user_id not in self.results_cache:
            return []
        
        results = self.results_cache[user_id]
        
        if assessment_type:
            results = [r for r in results if r.assessment_type == assessment_type]
        
        return sorted(results, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_user_schedules(self, user_id: int) -> List[AssessmentSchedule]:
        """
        Get assessment schedules for a user.
        """
        return self.schedules.get(user_id, [])
    
    def update_schedule(self, user_id: int, assessment_type: AssessmentType, **updates):
        """
        Update a specific assessment schedule.
        """
        if user_id not in self.schedules:
            return False
        
        for schedule in self.schedules[user_id]:
            if schedule.assessment_type == assessment_type:
                for key, value in updates.items():
                    if hasattr(schedule, key):
                        setattr(schedule, key, value)
                return True
        
        return False


# Global service instance
scheduled_assessment_service = ScheduledAssessmentService()