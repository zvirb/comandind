"""
Weighted Scoring Service - Intelligent task prioritization using user insights
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from shared.database.models import Task, Event, User, SemanticInsight, MissionInterview
from shared.schemas.interview_schemas import InterviewAnalysisResult

# Import the calendar categorization system for flexibility scores
try:
    from worker.calendar_categorization import get_user_categories_for_categorization
except ImportError:
    # Fallback when calendar categorization is not available
    def get_user_categories_for_categorization(user_id=None):
        return [], {}

logger = logging.getLogger(__name__)


class WeightedScoringService:
    """Service for calculating weighted scores for tasks and events based on user insights."""
    
    # Default scoring weights
    DEFAULT_TASK_WEIGHTS = {
        'priority_level': 0.20,
        'semantic_category': 0.18,
        'goal_alignment': 0.18,
        'work_style_match': 0.15,
        'flexibility_score': 0.12,
        'complexity_level': 0.09,
        'deadline_proximity': 0.08
    }
    
    DEFAULT_EVENT_WEIGHTS = {
        'importance_level': 0.25,
        'semantic_category': 0.20,
        'goal_alignment': 0.15,
        'flexibility_score': 0.15,
        'attendee_count': 0.15,
        'time_proximity': 0.10
    }
    
    # Category priorities based on common productivity frameworks
    CATEGORY_PRIORITIES = {
        'urgent': 1.0,
        'strategic': 0.9,
        'work': 0.8,
        'deadline': 0.85,
        'meeting': 0.75,
        'creative': 0.7,
        'administrative': 0.6,
        'social': 0.5,
        'personal': 0.4,
        'maintenance': 0.3,
        'general': 0.2
    }
    
    # Priority level multipliers
    PRIORITY_MULTIPLIERS = {
        'urgent': 1.0,
        'high': 0.8,
        'medium': 0.6,
        'low': 0.4
    }
    
    # Complexity level adjustments
    COMPLEXITY_ADJUSTMENTS = {
        'high': 0.9,  # Slightly lower score for high complexity (might be procrastinated)
        'medium': 1.0,
        'low': 1.1   # Slightly higher score for low complexity (easy wins)
    }

    @staticmethod
    def calculate_task_weighted_score(
        db: Session,
        task_id: str,
        user_id: int,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate weighted score for a specific task.
        
        Args:
            db: Database session
            task_id: Task ID
            user_id: User ID
            custom_weights: Optional custom scoring weights
            
        Returns:
            Dictionary with score and breakdown
        """
        try:
            # Get task
            task = db.query(Task).filter(
                and_(Task.id == task_id, Task.user_id == user_id)
            ).first()
            
            if not task:
                logger.warning(f"Task {task_id} not found for user {user_id}")
                return WeightedScoringService._get_default_score_result()
            
            # Get user profile and insights
            user = db.query(User).filter(User.id == user_id).first()
            user_insights = WeightedScoringService._get_user_insights(db, user_id)
            
            # Use custom weights or defaults
            weights = custom_weights or WeightedScoringService.DEFAULT_TASK_WEIGHTS
            
            # Calculate individual score components
            components = {}
            
            # 1. Priority Level Score
            components['priority_level'] = WeightedScoringService._calculate_priority_score(
                task.priority.value if task.priority else 'medium'
            )
            
            # 2. Semantic Category Score  
            components['semantic_category'] = WeightedScoringService._calculate_category_score(
                task.semantic_category or 'general'
            )
            
            # 3. Goal Alignment Score
            components['goal_alignment'] = WeightedScoringService._calculate_goal_alignment_score(
                task, user_insights
            )
            
            # 4. Work Style Match Score
            components['work_style_match'] = WeightedScoringService._calculate_work_style_score(
                task, user_insights
            )
            
            # 5. Flexibility Score (based on user's category flexibility settings)
            components['flexibility_score'] = WeightedScoringService._calculate_flexibility_score(
                task.semantic_category, user_id
            )
            
            # 6. Complexity Level Score
            components['complexity_level'] = WeightedScoringService._calculate_complexity_score(
                task.semantic_summary
            )
            
            # 7. Deadline Proximity Score
            components['deadline_proximity'] = WeightedScoringService._calculate_deadline_score(
                task.due_date
            )
            
            # Calculate weighted total
            weighted_score = sum(
                components.get(component, 0) * weights.get(component, 0)
                for component in weights.keys()
            )
            
            # Apply semantic confidence modifier
            if hasattr(task, 'semantic_keywords') and task.semantic_keywords:
                semantic_insight = db.query(SemanticInsight).filter(
                    and_(
                        SemanticInsight.user_id == user_id,
                        SemanticInsight.content_id == str(task.id),
                        SemanticInsight.content_type == 'task'
                    )
                ).first()
                
                if semantic_insight and semantic_insight.confidence_score:
                    # Higher confidence means more reliable scoring
                    confidence_modifier = 0.9 + (semantic_insight.confidence_score * 0.2)
                    weighted_score *= confidence_modifier
                    components['confidence_modifier'] = confidence_modifier
            
            # Normalize score to 0-1 range
            weighted_score = max(0.0, min(1.0, weighted_score))
            
            result = {
                'task_id': str(task.id),
                'weighted_score': weighted_score,
                'score_breakdown': components,
                'weights_used': weights,
                'calculation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Calculated weighted score {weighted_score:.3f} for task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating task weighted score: {e}")
            return WeightedScoringService._get_default_score_result()

    @staticmethod
    def calculate_event_weighted_score(
        db: Session,
        event_id: str,
        user_id: int,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate weighted score for a specific event.
        
        Args:
            db: Database session
            event_id: Event ID
            user_id: User ID
            custom_weights: Optional custom scoring weights
            
        Returns:
            Dictionary with score and breakdown
        """
        try:
            # Get event through calendar relationship
            event = db.query(Event).join(Event.calendar).filter(
                and_(Event.id == event_id, Event.calendar.has(user_id=user_id))
            ).first()
            
            if not event:
                logger.warning(f"Event {event_id} not found for user {user_id}")
                return WeightedScoringService._get_default_score_result()
            
            # Get user insights
            user_insights = WeightedScoringService._get_user_insights(db, user_id)
            
            # Use custom weights or defaults
            weights = custom_weights or WeightedScoringService.DEFAULT_EVENT_WEIGHTS
            
            # Calculate individual score components
            components = {}
            
            # 1. Importance Level Score
            components['importance_level'] = WeightedScoringService._calculate_priority_score(
                'medium'  # Default since events don't have explicit priority
            )
            
            # 2. Semantic Category Score
            components['semantic_category'] = WeightedScoringService._calculate_category_score(
                event.semantic_category or 'general'
            )
            
            # 3. Goal Alignment Score
            components['goal_alignment'] = WeightedScoringService._calculate_event_goal_alignment(
                event, user_insights
            )
            
            # 4. Attendee Count Score (higher for important meetings)
            components['attendee_count'] = WeightedScoringService._calculate_attendee_score(
                event.attendees
            )
            
            # 5. Flexibility Score (based on user's category flexibility settings)
            components['flexibility_score'] = WeightedScoringService._calculate_flexibility_score(
                event.semantic_category, user_id
            )
            
            # 6. Time Proximity Score
            components['time_proximity'] = WeightedScoringService._calculate_time_proximity_score(
                event.start_time
            )
            
            # Calculate weighted total
            weighted_score = sum(
                components.get(component, 0) * weights.get(component, 0)
                for component in weights.keys()
            )
            
            # Normalize score to 0-1 range
            weighted_score = max(0.0, min(1.0, weighted_score))
            
            result = {
                'event_id': str(event.id),
                'weighted_score': weighted_score,
                'score_breakdown': components,
                'weights_used': weights,
                'calculation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Calculated weighted score {weighted_score:.3f} for event {event_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating event weighted score: {e}")
            return WeightedScoringService._get_default_score_result()

    @staticmethod
    def rank_tasks_by_score(
        db: Session,
        user_id: int,
        limit: Optional[int] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        filter_completed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank user's tasks by weighted score.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Optional limit on number of tasks
            custom_weights: Optional custom scoring weights
            filter_completed: Whether to filter out completed tasks
            
        Returns:
            List of tasks with scores, sorted by score descending
        """
        try:
            # Get user's tasks
            query = db.query(Task).filter(Task.user_id == user_id)
            
            if filter_completed:
                from shared.database.models import TaskStatus
                query = query.filter(Task.status != TaskStatus.COMPLETED)
            
            if limit:
                query = query.limit(limit * 2)  # Get extra to account for scoring failures
            
            tasks = query.all()
            
            # Calculate scores for all tasks
            scored_tasks = []
            for task in tasks:
                score_result = WeightedScoringService.calculate_task_weighted_score(
                    db, str(task.id), user_id, custom_weights
                )
                
                if score_result['weighted_score'] > 0:
                    scored_tasks.append({
                        'task': {
                            'id': str(task.id),
                            'title': task.title,
                            'description': task.description,
                            'due_date': task.due_date.isoformat() if task.due_date else None,
                            'priority': task.priority.value if task.priority else None,
                            'status': task.status.value if task.status else None,
                            'semantic_category': task.semantic_category,
                            'semantic_tags': task.semantic_tags or []
                        },
                        'score_data': score_result,
                        'weighted_score': score_result['weighted_score']
                    })
            
            # Sort by weighted score descending
            scored_tasks.sort(key=lambda x: x['weighted_score'], reverse=True)
            
            # Apply limit after sorting
            if limit:
                scored_tasks = scored_tasks[:limit]
            
            # Add ranking
            for i, task_data in enumerate(scored_tasks):
                task_data['ranking'] = i + 1
            
            logger.info(f"Ranked {len(scored_tasks)} tasks for user {user_id}")
            return scored_tasks
            
        except Exception as e:
            logger.error(f"Error ranking tasks by score: {e}")
            return []

    @staticmethod
    def get_recommended_tasks(
        db: Session,
        user_id: int,
        recommendation_type: str = 'next_actions',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get task recommendations based on scoring and recommendation type.
        
        Args:
            db: Database session
            user_id: User ID
            recommendation_type: Type of recommendation ('next_actions', 'quick_wins', 'important')
            limit: Number of recommendations
            
        Returns:
            List of recommended tasks
        """
        try:
            # Get user insights for personalized weights
            user_insights = WeightedScoringService._get_user_insights(db, user_id)
            
            # Adjust weights based on recommendation type
            if recommendation_type == 'quick_wins':
                # Favor low complexity, high completion probability
                weights = WeightedScoringService.DEFAULT_TASK_WEIGHTS.copy()
                weights['complexity_level'] = 0.35  # Increase complexity weight (low complexity gets higher score)
                weights['priority_level'] = 0.15    # Decrease priority weight
            elif recommendation_type == 'important':
                # Favor high priority and goal alignment
                weights = WeightedScoringService.DEFAULT_TASK_WEIGHTS.copy()
                weights['priority_level'] = 0.35
                weights['goal_alignment'] = 0.30
                weights['complexity_level'] = 0.05
            else:  # next_actions
                # Balanced approach
                weights = WeightedScoringService.DEFAULT_TASK_WEIGHTS
            
            # Get ranked tasks
            ranked_tasks = WeightedScoringService.rank_tasks_by_score(
                db, user_id, limit * 2, weights, filter_completed=True
            )
            
            # Apply additional filters based on recommendation type
            filtered_tasks = []
            for task_data in ranked_tasks:
                task = task_data['task']
                score_breakdown = task_data['score_data']['score_breakdown']
                
                if recommendation_type == 'quick_wins':
                    # Only include tasks with reasonable complexity
                    if score_breakdown.get('complexity_level', 0) >= 0.6:
                        filtered_tasks.append(task_data)
                elif recommendation_type == 'important':
                    # Only include high priority or high goal alignment tasks
                    if (score_breakdown.get('priority_level', 0) >= 0.7 or 
                        score_breakdown.get('goal_alignment', 0) >= 0.7):
                        filtered_tasks.append(task_data)
                else:
                    # Include all for next_actions
                    filtered_tasks.append(task_data)
                
                if len(filtered_tasks) >= limit:
                    break
            
            # Add recommendation reason
            for task_data in filtered_tasks:
                task_data['recommendation_reason'] = WeightedScoringService._get_recommendation_reason(
                    task_data, recommendation_type
                )
            
            logger.info(f"Generated {len(filtered_tasks)} {recommendation_type} recommendations for user {user_id}")
            return filtered_tasks
            
        except Exception as e:
            logger.error(f"Error getting task recommendations: {e}")
            return []

    # Helper methods
    
    @staticmethod
    def _get_user_insights(db: Session, user_id: int) -> Dict[str, Any]:
        """Extract user insights from interviews and profile."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            insights = {
                'mission_statement': user.mission_statement,
                'personal_goals': user.personal_goals,
                'work_style_preferences': user.work_style_preferences,
                'productivity_patterns': user.productivity_patterns,
                'interview_insights': user.interview_insights
            }
            
            # Get latest interview analysis
            latest_interview = db.query(MissionInterview).filter(
                and_(
                    MissionInterview.user_id == user_id,
                    MissionInterview.status == 'analyzed'
                )
            ).order_by(MissionInterview.created_at.desc()).first()
            
            if latest_interview and latest_interview.analysis_results:
                insights['latest_analysis'] = latest_interview.analysis_results
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting user insights: {e}")
            return {}

    @staticmethod
    def _calculate_priority_score(priority_level: str) -> float:
        """Calculate score based on priority level."""
        return WeightedScoringService.PRIORITY_MULTIPLIERS.get(priority_level.lower(), 0.6)

    @staticmethod
    def _calculate_category_score(category: str) -> float:
        """Calculate score based on semantic category."""
        return WeightedScoringService.CATEGORY_PRIORITIES.get(category.lower(), 0.2)

    @staticmethod
    def _calculate_goal_alignment_score(task: Task, user_insights: Dict[str, Any]) -> float:
        """Calculate score based on alignment with user goals."""
        try:
            if not user_insights.get('personal_goals'):
                return 0.5  # Default when no goals defined
            
            goals = user_insights['personal_goals']
            if isinstance(goals, dict) and 'goals' in goals:
                goal_keywords = ' '.join(goals['goals']).lower()
                
                # Check task title and description for goal keywords
                task_text = (task.title or '').lower()
                if task.description:
                    task_text += ' ' + task.description.lower()
                
                # Simple keyword matching - could be enhanced with semantic similarity
                matches = sum(1 for goal_word in goal_keywords.split() 
                             if len(goal_word) > 3 and goal_word in task_text)
                
                # Normalize based on number of goal keywords
                goal_word_count = len([w for w in goal_keywords.split() if len(w) > 3])
                if goal_word_count > 0:
                    return min(1.0, matches / goal_word_count + 0.2)
            
            return 0.5
            
        except Exception:
            return 0.5

    @staticmethod
    def _calculate_work_style_score(task: Task, user_insights: Dict[str, Any]) -> float:
        """Calculate score based on work style preferences."""
        try:
            work_style = user_insights.get('work_style_preferences')
            if not work_style:
                return 0.5
            
            score = 0.5
            
            # Check collaboration preference
            if work_style.get('collaboration_preference') == 'team-oriented':
                if task.semantic_category in ['meeting', 'social', 'work']:
                    score += 0.2
            elif work_style.get('collaboration_preference') == 'independent':
                if task.semantic_category in ['creative', 'strategic', 'personal']:
                    score += 0.2
            
            # Check communication style
            if work_style.get('communication_style') == 'direct':
                if task.semantic_category in ['administrative', 'urgent']:
                    score += 0.1
            
            return min(1.0, score)
            
        except Exception:
            return 0.5

    @staticmethod
    def _calculate_complexity_score(semantic_summary: Optional[str]) -> float:
        """Calculate score based on task complexity."""
        if not semantic_summary:
            return 0.6
        
        summary_lower = semantic_summary.lower()
        
        # Detect complexity indicators
        if any(word in summary_lower for word in ['high priority', 'complex', 'difficult']):
            return WeightedScoringService.COMPLEXITY_ADJUSTMENTS['high']
        elif any(word in summary_lower for word in ['low priority', 'simple', 'easy', 'quick']):
            return WeightedScoringService.COMPLEXITY_ADJUSTMENTS['low']
        else:
            return WeightedScoringService.COMPLEXITY_ADJUSTMENTS['medium']

    @staticmethod
    def _calculate_deadline_score(due_date: Optional[datetime]) -> float:
        """Calculate score based on deadline proximity."""
        if not due_date:
            return 0.3  # No deadline = lower urgency
        
        now = datetime.now(timezone.utc)
        days_until_due = (due_date - now).days
        
        if days_until_due < 0:
            return 1.0  # Overdue = highest urgency
        elif days_until_due == 0:
            return 0.95  # Due today
        elif days_until_due <= 1:
            return 0.9   # Due tomorrow
        elif days_until_due <= 3:
            return 0.7   # Due within 3 days
        elif days_until_due <= 7:
            return 0.5   # Due within a week
        else:
            return 0.2   # Due later

    @staticmethod
    def _calculate_event_goal_alignment(event: Event, user_insights: Dict[str, Any]) -> float:
        """Calculate goal alignment score for events."""
        try:
            if not user_insights.get('personal_goals'):
                return 0.5
            
            # Similar to task goal alignment but considering event context
            goals = user_insights['personal_goals']
            if isinstance(goals, dict) and 'goals' in goals:
                goal_keywords = ' '.join(goals['goals']).lower()
                
                event_text = (event.summary or '').lower()
                if event.description:
                    event_text += ' ' + event.description.lower()
                
                matches = sum(1 for goal_word in goal_keywords.split() 
                             if len(goal_word) > 3 and goal_word in event_text)
                
                goal_word_count = len([w for w in goal_keywords.split() if len(w) > 3])
                if goal_word_count > 0:
                    return min(1.0, matches / goal_word_count + 0.3)
            
            return 0.5
            
        except Exception:
            return 0.5

    @staticmethod
    def _calculate_attendee_score(attendees: Optional[str]) -> float:
        """Calculate score based on number of attendees."""
        if not attendees:
            return 0.3
        
        # Simple heuristic - more attendees = more important
        attendee_count = len(attendees.split(',')) if attendees else 0
        
        if attendee_count >= 5:
            return 0.9
        elif attendee_count >= 3:
            return 0.7
        elif attendee_count >= 2:
            return 0.5
        else:
            return 0.3

    @staticmethod
    def _calculate_time_proximity_score(start_time: Optional[datetime]) -> float:
        """Calculate score based on event time proximity."""
        if not start_time:
            return 0.5
        
        now = datetime.now(timezone.utc)
        hours_until_event = (start_time - now).total_seconds() / 3600
        
        if hours_until_event < 0:
            return 0.1  # Past event
        elif hours_until_event <= 1:
            return 1.0  # Very soon
        elif hours_until_event <= 4:
            return 0.8  # Today
        elif hours_until_event <= 24:
            return 0.6  # Tomorrow
        else:
            return 0.3  # Later

    @staticmethod
    def _calculate_flexibility_score(category: Optional[str], user_id: int) -> float:
        """Calculate flexibility score based on user's category flexibility settings."""
        try:
            if not category or not user_id:
                return 0.5  # Default flexibility when no category or user
            
            # Get user's categories and their weights (including flexibility)
            user_categories, category_weights = get_user_categories_for_categorization(user_id)
            
            # Look for the category in user's custom categories first
            if category in category_weights:
                flexibility = category_weights[category].get('flexibility', 0.5)
                # Return flexibility score directly - higher flexibility = higher score for scheduling
                return flexibility
            
            # Fallback to default flexibility patterns if category not found
            category_lower = category.lower()
            
            # Fixed events (low flexibility)
            if category_lower in ['appointment', 'meeting', 'class', 'booking', 'interview']:
                return 0.1  # Very inflexible
            elif category_lower in ['deadline', 'commitment', 'scheduled']:
                return 0.2  # Low flexibility
            
            # Moderately flexible events
            elif category_lower in ['work', 'project', 'task']:
                return 0.6  # Moderate flexibility
            
            # Highly flexible events
            elif category_lower in ['study', 'exercise', 'personal', 'leisure']:
                return 0.8  # High flexibility
            
            # Default flexibility for unknown categories
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error calculating flexibility score: {e}")
            return 0.5  # Default on error

    @staticmethod
    def _get_recommendation_reason(task_data: Dict[str, Any], recommendation_type: str) -> str:
        """Generate explanation for why task was recommended."""
        score_breakdown = task_data['score_data']['score_breakdown']
        
        if recommendation_type == 'quick_wins':
            return f"Quick win: {score_breakdown.get('complexity_level', 0):.0%} completion confidence"
        elif recommendation_type == 'important':
            return f"High priority: {score_breakdown.get('priority_level', 0):.0%} priority, {score_breakdown.get('goal_alignment', 0):.0%} goal alignment"
        else:
            highest_component = max(score_breakdown.items(), key=lambda x: x[1])
            return f"Recommended: Strong {highest_component[0].replace('_', ' ')} ({highest_component[1]:.0%})"

    @staticmethod
    def _get_default_score_result() -> Dict[str, Any]:
        """Return default score result when calculation fails."""
        return {
            'weighted_score': 0.5,
            'score_breakdown': {},
            'weights_used': {},
            'calculation_timestamp': datetime.now(timezone.utc).isoformat()
        }