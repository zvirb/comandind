"""
Confidence Calibration Service

This service integrates user feedback (thumbs up/down) with the AI confidence rating system
to improve confidence predictions and adapt to user preferences over time.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from shared.utils.database_setup import get_db
from shared.database.models import MessageFeedback, ChatMessage, User

logger = logging.getLogger(__name__)

class ConfidenceCalibrationService:
    """
    Service for calibrating confidence scores based on user feedback patterns.
    
    This service learns from user thumbs up/down feedback to:
    1. Adjust confidence scores for specific users and categories
    2. Identify patterns where AI confidence mismatches user satisfaction
    3. Provide personalized confidence thresholds
    4. Track confidence calibration accuracy over time
    """
    
    def __init__(self):
        self.cache_duration = timedelta(hours=1)  # Cache feedback patterns for 1 hour
        self._user_adjustments_cache = {}
        self._cache_timestamps = {}
    
    def get_user_confidence_adjustment(
        self, 
        user_id: str, 
        category: str, 
        keywords: List[str]
    ) -> float:
        """
        Get confidence adjustment factor based on user's feedback history.
        
        Args:
            user_id: User identifier
            category: Semantic category of the content
            keywords: Keywords from the content
            
        Returns:
            Float adjustment factor (-0.3 to +0.3) to apply to base confidence
        """
        try:
            cache_key = f"{user_id}_{category}"
            
            # Check cache first
            if self._is_cache_valid(cache_key):
                return self._user_adjustments_cache.get(cache_key, 0.0)
            
            # Calculate adjustment from database
            adjustment = self._calculate_user_adjustment(user_id, category, keywords)
            
            # Cache the result
            self._user_adjustments_cache[cache_key] = adjustment
            self._cache_timestamps[cache_key] = datetime.utcnow()
            
            return adjustment
            
        except Exception as e:
            logger.error(f"Error calculating confidence adjustment for user {user_id}: {e}")
            return 0.0
    
    def _calculate_user_adjustment(
        self, 
        user_id: str, 
        category: str, 
        keywords: List[str]
    ) -> float:
        """Calculate confidence adjustment based on user feedback patterns."""
        try:
            with next(get_db()) as db:
                # Get recent feedback for this user (last 30 days)
                recent_cutoff = datetime.utcnow() - timedelta(days=30)
                
                # Join feedback with messages to get confidence scores and categories
                feedback_query = db.query(
                    MessageFeedback.feedback,
                    ChatMessage.confidence_score,
                    ChatMessage.content
                ).join(
                    ChatMessage, 
                    MessageFeedback.message_id == ChatMessage.message_id
                ).filter(
                    ChatMessage.user_id == user_id,
                    ChatMessage.timestamp >= recent_cutoff,
                    ChatMessage.confidence_score.isnot(None)
                ).all()
                
                if not feedback_query:
                    return 0.0
                
                # Analyze feedback patterns
                positive_feedback = []
                negative_feedback = []
                
                for feedback, confidence, content in feedback_query:
                    # Check if content matches category or keywords
                    content_lower = content.lower() if content else ""
                    category_match = category.lower() in content_lower
                    keyword_match = any(kw.lower() in content_lower for kw in keywords)
                    
                    if category_match or keyword_match:
                        if feedback == "thumbs_up":
                            positive_feedback.append(confidence)
                        elif feedback == "thumbs_down":
                            negative_feedback.append(confidence)
                
                # Calculate adjustment based on feedback patterns
                adjustment = 0.0
                
                if positive_feedback or negative_feedback:
                    # Calculate average confidence for positive vs negative feedback
                    avg_positive = statistics.mean(positive_feedback) if positive_feedback else 0.5
                    avg_negative = statistics.mean(negative_feedback) if negative_feedback else 0.5
                    
                    # If user gives thumbs down to high confidence predictions,
                    # we should be more conservative (negative adjustment)
                    if negative_feedback and avg_negative > 0.7:
                        adjustment -= 0.2
                    
                    # If user gives thumbs up to lower confidence predictions,
                    # we can be more confident (positive adjustment)
                    if positive_feedback and avg_positive < 0.6:
                        adjustment += 0.15
                    
                    # Consider feedback frequency
                    total_feedback = len(positive_feedback) + len(negative_feedback)
                    positive_ratio = len(positive_feedback) / total_feedback if total_feedback > 0 else 0.5
                    
                    # Adjust based on overall satisfaction
                    if positive_ratio > 0.8:  # Very satisfied
                        adjustment += 0.1
                    elif positive_ratio < 0.3:  # Often dissatisfied
                        adjustment -= 0.15
                
                # Cap adjustment range
                adjustment = max(-0.3, min(0.3, adjustment))
                
                logger.debug(f"Calculated confidence adjustment for user {user_id}, category {category}: {adjustment}")
                return adjustment
                
        except Exception as e:
            logger.error(f"Error in _calculate_user_adjustment: {e}")
            return 0.0
    
    def update_confidence_based_on_feedback(
        self,
        message_id: str,
        feedback_type: str,
        original_confidence: float
    ) -> Dict[str, any]:
        """
        Update confidence calibration based on specific feedback.
        
        Args:
            message_id: ID of the message that received feedback
            feedback_type: 'thumbs_up' or 'thumbs_down'
            original_confidence: Original confidence score for the message
            
        Returns:
            Dictionary with calibration insights
        """
        try:
            with next(get_db()) as db:
                # Get message details
                message = db.query(ChatMessage).filter(
                    ChatMessage.message_id == message_id
                ).first()
                
                if not message:
                    return {"error": "Message not found"}
                
                # Analyze confidence vs feedback mismatch
                confidence_feedback_mismatch = False
                mismatch_severity = 0.0
                
                if feedback_type == "thumbs_down":
                    if original_confidence > 0.7:
                        confidence_feedback_mismatch = True
                        mismatch_severity = original_confidence - 0.7
                        logger.info(f"High confidence ({original_confidence}) received negative feedback")
                elif feedback_type == "thumbs_up":
                    if original_confidence < 0.4:
                        confidence_feedback_mismatch = True
                        mismatch_severity = 0.4 - original_confidence
                        logger.info(f"Low confidence ({original_confidence}) received positive feedback")
                
                # Clear cache for this user to force recalculation
                user_id = str(message.user_id)
                cache_keys_to_clear = [k for k in self._user_adjustments_cache.keys() if k.startswith(user_id)]
                for key in cache_keys_to_clear:
                    self._user_adjustments_cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)
                
                return {
                    "message_id": message_id,
                    "feedback_type": feedback_type,
                    "original_confidence": original_confidence,
                    "confidence_feedback_mismatch": confidence_feedback_mismatch,
                    "mismatch_severity": mismatch_severity,
                    "cache_cleared": len(cache_keys_to_clear)
                }
                
        except Exception as e:
            logger.error(f"Error updating confidence based on feedback: {e}")
            return {"error": str(e)}
    
    def get_user_confidence_stats(self, user_id: str) -> Dict[str, any]:
        """
        Get confidence calibration statistics for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with user's confidence statistics
        """
        try:
            with next(get_db()) as db:
                # Get all feedback with confidence scores for this user
                feedback_data = db.query(
                    MessageFeedback.feedback,
                    ChatMessage.confidence_score,
                    ChatMessage.timestamp
                ).join(
                    ChatMessage,
                    MessageFeedback.message_id == ChatMessage.message_id
                ).filter(
                    ChatMessage.user_id == user_id,
                    ChatMessage.confidence_score.isnot(None)
                ).all()
                
                if not feedback_data:
                    return {"message": "No feedback data available"}
                
                # Analyze patterns
                total_feedback = len(feedback_data)
                positive_feedback = [d for d in feedback_data if d.feedback == "thumbs_up"]
                negative_feedback = [d for d in feedback_data if d.feedback == "thumbs_down"]
                
                # Calculate accuracy metrics
                high_confidence_positive = len([d for d in positive_feedback if d.confidence_score > 0.7])
                high_confidence_negative = len([d for d in negative_feedback if d.confidence_score > 0.7])
                low_confidence_positive = len([d for d in positive_feedback if d.confidence_score < 0.4])
                low_confidence_negative = len([d for d in negative_feedback if d.confidence_score < 0.4])
                
                return {
                    "user_id": user_id,
                    "total_feedback": total_feedback,
                    "positive_feedback_count": len(positive_feedback),
                    "negative_feedback_count": len(negative_feedback),
                    "positive_ratio": len(positive_feedback) / total_feedback if total_feedback > 0 else 0,
                    "high_confidence_accuracy": high_confidence_positive / (high_confidence_positive + high_confidence_negative) if (high_confidence_positive + high_confidence_negative) > 0 else 0,
                    "low_confidence_surprises": low_confidence_positive / (low_confidence_positive + low_confidence_negative) if (low_confidence_positive + low_confidence_negative) > 0 else 0,
                    "confidence_calibration_quality": (
                        "good" if (high_confidence_positive + high_confidence_negative) > 0 and 
                                (high_confidence_positive / (high_confidence_positive + high_confidence_negative)) > 0.7
                        else "needs_improvement" if total_feedback > 10 
                        else "insufficient_data"
                    )
                }
                
        except Exception as e:
            logger.error(f"Error getting confidence stats for user {user_id}: {e}")
            return {"error": str(e)}
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached adjustment is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        return datetime.utcnow() - cache_time < self.cache_duration

# Global service instance
confidence_calibration_service = ConfidenceCalibrationService()