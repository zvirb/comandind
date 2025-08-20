"""
Semantic Analysis Service - AI-powered content analysis for tasks and events
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_

from shared.database.models import Task, Event, User, SemanticInsight, AIAnalysisHistory
from shared.schemas.interview_schemas import InterviewAnalysisResult

logger = logging.getLogger(__name__)


class SemanticAnalysisService:
    """Service for AI-powered semantic analysis of tasks and events."""
    
    # Predefined semantic categories based on common productivity frameworks
    TASK_CATEGORIES = {
        'work': ['meeting', 'project', 'deadline', 'review', 'coding', 'development', 'design', 'planning'],
        'personal': ['health', 'family', 'exercise', 'hobby', 'learning', 'education', 'reading'],
        'administrative': ['email', 'filing', 'organizing', 'scheduling', 'banking', 'taxes'],
        'creative': ['writing', 'art', 'music', 'brainstorming', 'innovation', 'design'],
        'social': ['networking', 'collaboration', 'team', 'community', 'relationship'],
        'maintenance': ['cleaning', 'repair', 'update', 'backup', 'maintenance'],
        'urgent': ['asap', 'urgent', 'emergency', 'critical', 'immediate'],
        'strategic': ['planning', 'strategy', 'long-term', 'vision', 'goal'],
    }
    
    EVENT_CATEGORIES = {
        'meeting': ['meeting', 'call', 'conference', 'discussion', 'standup', 'review'],
        'appointment': ['appointment', 'doctor', 'dentist', 'interview', 'consultation'],
        'deadline': ['due', 'deadline', 'submission', 'delivery', 'launch'],
        'personal': ['birthday', 'anniversary', 'vacation', 'holiday', 'break'],
        'learning': ['training', 'workshop', 'course', 'seminar', 'class'],
        'social': ['party', 'dinner', 'lunch', 'networking', 'gathering'],
        'travel': ['flight', 'trip', 'travel', 'commute', 'journey'],
        'health': ['workout', 'gym', 'exercise', 'medical', 'therapy'],
    }
    
    PRIORITY_KEYWORDS = {
        'urgent': ['urgent', 'asap', 'emergency', 'critical', 'immediate', 'now'],
        'high': ['important', 'priority', 'key', 'critical', 'must', 'essential'],
        'medium': ['should', 'would', 'need', 'want', 'plan'],
        'low': ['maybe', 'consider', 'eventually', 'someday', 'optional'],
    }

    @staticmethod
    def analyze_task_semantics(
        task_text: str, 
        task_description: str = None,
        user_profile: Dict[str, Any] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze task text to extract semantic meaning and categorization.
        
        Args:
            task_text: Main task title/text
            task_description: Optional detailed description
            user_profile: User's profile data from interviews
            
        Returns:
            Dictionary with semantic analysis results
        """
        try:
            # Combine text for analysis
            full_text = task_text.lower()
            if task_description:
                full_text += " " + task_description.lower()
            
            # Extract keywords
            keywords = SemanticAnalysisService._extract_keywords(full_text)
            
            # Categorize based on content
            category = SemanticAnalysisService._categorize_content(full_text, SemanticAnalysisService.TASK_CATEGORIES)
            
            # Determine priority level
            priority_level = SemanticAnalysisService._analyze_priority(full_text)
            
            # Extract time-related information
            time_info = SemanticAnalysisService._extract_time_information(full_text)
            
            # Analyze complexity
            complexity = SemanticAnalysisService._analyze_complexity(full_text, task_description)
            
            # Generate tags
            tags = SemanticAnalysisService._generate_tags(full_text, category, keywords)
            
            # Create semantic summary
            summary = SemanticAnalysisService._generate_task_summary(task_text, category, priority_level)
            
            # Personalize based on user profile
            personalization = SemanticAnalysisService._personalize_analysis(
                category, keywords, user_profile
            )
            
            analysis_result = {
                'keywords': keywords,
                'semantic_category': category,
                'priority_level': priority_level,
                'complexity_level': complexity,
                'time_information': time_info,
                'tags': tags,
                'summary': summary,
                'personalization': personalization,
                'confidence_score': SemanticAnalysisService._calculate_confidence(
                    keywords, category, priority_level, user_id
                ),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Task semantic analysis completed: category={category}, priority={priority_level}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing task semantics: {e}")
            return SemanticAnalysisService._get_default_analysis()

    @staticmethod
    def analyze_event_semantics(
        event_title: str,
        event_description: str = None,
        event_location: str = None,
        user_profile: Dict[str, Any] = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze event text to extract semantic meaning and categorization.
        
        Args:
            event_title: Event title
            event_description: Optional event description
            event_location: Optional event location
            user_profile: User's profile data from interviews
            
        Returns:
            Dictionary with semantic analysis results
        """
        try:
            # Combine text for analysis
            full_text = event_title.lower()
            if event_description:
                full_text += " " + event_description.lower()
            if event_location:
                full_text += " " + event_location.lower()
            
            # Extract keywords
            keywords = SemanticAnalysisService._extract_keywords(full_text)
            
            # Categorize based on content
            category = SemanticAnalysisService._categorize_content(full_text, SemanticAnalysisService.EVENT_CATEGORIES)
            
            # Determine importance
            importance = SemanticAnalysisService._analyze_importance(full_text)
            
            # Extract attendee information
            attendee_info = SemanticAnalysisService._extract_attendee_info(full_text)
            
            # Generate tags
            tags = SemanticAnalysisService._generate_tags(full_text, category, keywords)
            
            # Create semantic summary
            summary = SemanticAnalysisService._generate_event_summary(event_title, category, importance)
            
            # Personalize based on user profile
            personalization = SemanticAnalysisService._personalize_analysis(
                category, keywords, user_profile
            )
            
            analysis_result = {
                'keywords': keywords,
                'semantic_category': category,
                'importance_level': importance,
                'attendee_information': attendee_info,
                'tags': tags,
                'summary': summary,
                'personalization': personalization,
                'confidence_score': SemanticAnalysisService._calculate_confidence(
                    keywords, category, importance, user_id
                ),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Event semantic analysis completed: category={category}, importance={importance}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing event semantics: {e}")
            return SemanticAnalysisService._get_default_analysis()

    @staticmethod
    def update_task_semantic_fields(
        db: Session,
        task_id: str,
        user_id: int,
        force_update: bool = False
    ) -> bool:
        """
        Update semantic fields for a specific task.
        
        Args:
            db: Database session
            task_id: Task ID
            user_id: User ID for personalization
            force_update: Force update even if already analyzed
            
        Returns:
            True if updated successfully
        """
        try:
            # Get task
            task = db.query(Task).filter(
                and_(Task.id == task_id, Task.user_id == user_id)
            ).first()
            
            if not task:
                logger.warning(f"Task {task_id} not found for user {user_id}")
                return False
            
            # Check if already analyzed
            if not force_update and task.semantic_keywords:
                logger.info(f"Task {task_id} already has semantic analysis")
                return True
            
            # Get user profile
            user = db.query(User).filter(User.id == user_id).first()
            user_profile = SemanticAnalysisService._extract_user_profile(user)
            
            # Perform semantic analysis
            analysis = SemanticAnalysisService.analyze_task_semantics(
                task.title,
                task.description,
                user_profile
            )
            
            # Update task fields
            task.semantic_keywords = analysis.get('keywords', {})
            task.semantic_category = analysis.get('semantic_category')
            task.semantic_tags = analysis.get('tags', [])
            task.semantic_summary = analysis.get('summary')
            
            # Store detailed analysis as semantic insight
            insight = SemanticInsight(
                user_id=user_id,
                content_type='task',
                content_id=task.id,
                insight_type='semantic_analysis',
                insight_value=analysis,
                confidence_score=analysis.get('confidence_score'),
                model_used='semantic_analysis_v1'
            )
            db.add(insight)
            
            # Record analysis history
            history = AIAnalysisHistory(
                user_id=user_id,
                analysis_type='task_semantic_analysis',
                input_data={
                    'task_id': str(task.id),
                    'title': task.title,
                    'description': task.description
                },
                output_data=analysis,
                model_used='semantic_analysis_v1',
                processing_time_ms=100  # Placeholder
            )
            db.add(history)
            
            db.commit()
            logger.info(f"Updated semantic fields for task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating task semantic fields: {e}")
            db.rollback()
            return False

    @staticmethod
    def update_event_semantic_fields(
        db: Session,
        event_id: str,
        user_id: int,
        force_update: bool = False
    ) -> bool:
        """
        Update semantic fields for a specific event.
        
        Args:
            db: Database session
            event_id: Event ID
            user_id: User ID for personalization
            force_update: Force update even if already analyzed
            
        Returns:
            True if updated successfully
        """
        try:
            # Get event through calendar relationship
            event = db.query(Event).join(Event.calendar).filter(
                and_(Event.id == event_id, Event.calendar.has(user_id=user_id))
            ).first()
            
            if not event:
                logger.warning(f"Event {event_id} not found for user {user_id}")
                return False
            
            # Check if already analyzed
            if not force_update and event.semantic_keywords:
                logger.info(f"Event {event_id} already has semantic analysis")
                return True
            
            # Get user profile
            user = db.query(User).filter(User.id == user_id).first()
            user_profile = SemanticAnalysisService._extract_user_profile(user)
            
            # Perform semantic analysis
            analysis = SemanticAnalysisService.analyze_event_semantics(
                event.summary,
                event.description,
                event.location,
                user_profile
            )
            
            # Update event fields
            event.semantic_keywords = analysis.get('keywords', {})
            event.semantic_category = analysis.get('semantic_category')
            event.semantic_tags = analysis.get('tags', [])
            
            # Store detailed analysis as semantic insight
            insight = SemanticInsight(
                user_id=user_id,
                content_type='event',
                content_id=event.id,
                insight_type='semantic_analysis',
                insight_value=analysis,
                confidence_score=analysis.get('confidence_score'),
                model_used='semantic_analysis_v1'
            )
            db.add(insight)
            
            # Record analysis history
            history = AIAnalysisHistory(
                user_id=user_id,
                analysis_type='event_semantic_analysis',
                input_data={
                    'event_id': str(event.id),
                    'summary': event.summary,
                    'description': event.description,
                    'location': event.location
                },
                output_data=analysis,
                model_used='semantic_analysis_v1',
                processing_time_ms=100  # Placeholder
            )
            db.add(history)
            
            db.commit()
            logger.info(f"Updated semantic fields for event {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating event semantic fields: {e}")
            db.rollback()
            return False

    @staticmethod
    def bulk_analyze_user_content(db: Session, user_id: int) -> Dict[str, int]:
        """
        Perform bulk semantic analysis for all user's tasks and events.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with analysis counts
        """
        try:
            stats = {'tasks_analyzed': 0, 'events_analyzed': 0, 'errors': 0}
            
            # Analyze all user tasks
            tasks = db.query(Task).filter(Task.user_id == user_id).all()
            for task in tasks:
                try:
                    if SemanticAnalysisService.update_task_semantic_fields(
                        db, str(task.id), user_id, force_update=False
                    ):
                        stats['tasks_analyzed'] += 1
                except Exception as e:
                    logger.error(f"Error analyzing task {task.id}: {e}")
                    stats['errors'] += 1
            
            # Analyze all user events
            events = db.query(Event).join(Event.calendar).filter(
                Event.calendar.has(user_id=user_id)
            ).all()
            for event in events:
                try:
                    if SemanticAnalysisService.update_event_semantic_fields(
                        db, str(event.id), user_id, force_update=False
                    ):
                        stats['events_analyzed'] += 1
                except Exception as e:
                    logger.error(f"Error analyzing event {event.id}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"Bulk analysis completed for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in bulk analysis for user {user_id}: {e}")
            return {'tasks_analyzed': 0, 'events_analyzed': 0, 'errors': 1}

    # Helper methods
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter out stop words and short words
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Return unique keywords
        return list(set(keywords))

    @staticmethod
    def _categorize_content(text: str, categories: Dict[str, List[str]]) -> str:
        """Categorize content based on keyword matching."""
        category_scores = {}
        
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return 'general'

    @staticmethod
    def _analyze_priority(text: str) -> str:
        """Analyze priority level based on keywords."""
        for priority, keywords in SemanticAnalysisService.PRIORITY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return priority
        return 'medium'

    @staticmethod
    def _analyze_importance(text: str) -> str:
        """Analyze importance level for events."""
        return SemanticAnalysisService._analyze_priority(text)

    @staticmethod
    def _analyze_complexity(text: str, description: str = None) -> str:
        """Analyze task complexity."""
        complexity_indicators = {
            'high': ['complex', 'difficult', 'challenging', 'multiple', 'phase', 'project'],
            'medium': ['moderate', 'several', 'some', 'review', 'update'],
            'low': ['simple', 'quick', 'easy', 'basic', 'small']
        }
        
        full_text = text
        if description:
            full_text += " " + description.lower()
        
        for level, indicators in complexity_indicators.items():
            if any(indicator in full_text for indicator in indicators):
                return level
        
        # Default based on text length
        if len(full_text.split()) > 10:
            return 'medium'
        return 'low'

    @staticmethod
    def _extract_time_information(text: str) -> Dict[str, Any]:
        """Extract time-related information from text."""
        time_info = {}
        
        # Look for time patterns
        time_patterns = {
            'duration': re.findall(r'(\d+)\s*(hour|minute|day|week|month)s?', text),
            'deadline': re.findall(r'(deadline|due|by)\s+(\w+)', text),
        }
        
        for key, matches in time_patterns.items():
            if matches:
                time_info[key] = matches
        
        return time_info

    @staticmethod
    def _extract_attendee_info(text: str) -> Dict[str, Any]:
        """Extract attendee information from event text."""
        attendee_info = {}
        
        # Look for attendee indicators
        if any(word in text for word in ['meeting', 'call', 'conference']):
            attendee_info['has_attendees'] = True
        
        if any(word in text for word in ['team', 'group', 'all']):
            attendee_info['group_event'] = True
        
        return attendee_info

    @staticmethod
    def _generate_tags(text: str, category: str, keywords: List[str]) -> List[str]:
        """Generate relevant tags for content."""
        tags = [category]
        
        # Add top keywords as tags
        tags.extend(keywords[:3])
        
        # Add special tags based on content
        if any(word in text for word in ['urgent', 'asap', 'emergency']):
            tags.append('urgent')
        
        if any(word in text for word in ['meeting', 'call']):
            tags.append('communication')
        
        return list(set(tags))

    @staticmethod
    def _generate_task_summary(title: str, category: str, priority: str) -> str:
        """Generate a summary for a task."""
        return f"A {priority} priority {category} task: {title[:50]}{'...' if len(title) > 50 else ''}"

    @staticmethod
    def _generate_event_summary(title: str, category: str, importance: str) -> str:
        """Generate a summary for an event."""
        return f"A {importance} importance {category} event: {title[:50]}{'...' if len(title) > 50 else ''}"

    @staticmethod
    def _personalize_analysis(
        category: str, 
        keywords: List[str], 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Personalize analysis based on user profile."""
        personalization = {}
        
        if not user_profile:
            return personalization
        
        # Check alignment with user goals
        if 'personal_goals' in user_profile:
            goals = user_profile['personal_goals']
            if isinstance(goals, dict) and 'goals' in goals:
                goal_keywords = ' '.join(goals['goals']).lower()
                alignment_score = sum(1 for keyword in keywords if keyword in goal_keywords)
                personalization['goal_alignment'] = alignment_score / max(len(keywords), 1)
        
        # Check alignment with work style
        if 'work_style_preferences' in user_profile:
            work_style = user_profile['work_style_preferences']
            if isinstance(work_style, dict):
                if category == 'work' and work_style.get('collaboration_preference') == 'team-oriented':
                    personalization['work_style_match'] = True
        
        return personalization

    @staticmethod
    def _extract_user_profile(user: Optional[User]) -> Dict[str, Any]:
        """Extract user profile data for personalization."""
        if not user:
            return {}
        
        profile = {}
        
        if user.personal_goals:
            profile['personal_goals'] = user.personal_goals
        
        if user.work_style_preferences:
            profile['work_style_preferences'] = user.work_style_preferences
        
        if user.productivity_patterns:
            profile['productivity_patterns'] = user.productivity_patterns
        
        return profile

    @staticmethod
    def _calculate_confidence(keywords: List[str], category: str, priority_or_importance: str, user_id: str = None) -> float:
        """
        Calculate confidence score for the analysis, incorporating user feedback patterns.
        """
        score = 0.5  # Base confidence
        
        # Increase confidence based on keyword count
        score += min(len(keywords) * 0.1, 0.3)
        
        # Increase confidence if category is not 'general'
        if category != 'general':
            score += 0.2
        
        # Adjust confidence based on user feedback history if available
        if user_id:
            try:
                from shared.services.confidence_calibration_service import confidence_calibration_service
                feedback_adjustment = confidence_calibration_service.get_user_confidence_adjustment(
                    user_id, category, keywords
                )
                score += feedback_adjustment
                logger.debug(f"Applied user feedback adjustment: {feedback_adjustment} for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not apply feedback adjustment: {e}")
        
        # Cap at 1.0
        return min(score, 1.0)

    @staticmethod
    def _get_default_analysis() -> Dict[str, Any]:
        """Return default analysis when processing fails."""
        return {
            'keywords': [],
            'semantic_category': 'general',
            'priority_level': 'medium',
            'complexity_level': 'medium',
            'time_information': {},
            'tags': ['general'],
            'summary': 'Content analysis unavailable',
            'personalization': {},
            'confidence_score': 0.1,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }