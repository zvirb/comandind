"""
Blackboard Integration Service for LangGraph Workflows

Implements event-driven blackboard communication for the hybrid orchestration/choreography
model. Agents monitor the blackboard for opportunities to contribute and post structured
events for coordination.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator
from enum import Enum

from sqlalchemy.orm import Session
from shared.utils.database_setup import get_database_session
from shared.database.models.cognitive_state_models import (
    BlackboardEvent, 
    AgentContextState, 
    EventType, 
    Performative, 
    MemoryTier
)

logger = logging.getLogger(__name__)


class BlackboardEventBus:
    """Event bus for blackboard communication between agents."""
    
    def __init__(self):
        self._subscribers = {}
        self._event_processors = []
    
    def subscribe(self, agent_id: str, event_types: List[EventType], callback):
        """Subscribe an agent to specific event types."""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = {}
        
        for event_type in event_types:
            if event_type not in self._subscribers[agent_id]:
                self._subscribers[agent_id][event_type] = []
            self._subscribers[agent_id][event_type].append(callback)
    
    def unsubscribe(self, agent_id: str):
        """Unsubscribe an agent from all events."""
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]
    
    async def publish_event(self, event: BlackboardEvent):
        """Publish an event to all subscribers."""
        event_type = EventType(event.event_type)
        
        for agent_id, subscriptions in self._subscribers.items():
            if event_type in subscriptions:
                for callback in subscriptions[event_type]:
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Error in event callback for agent {agent_id}: {e}")


class BlackboardIntegrationService:
    """Service for integrating LangGraph workflows with blackboard communication."""
    
    def __init__(self):
        self.event_bus = BlackboardEventBus()
        self.active_sessions = {}
    
    async def post_blackboard_event(
        self,
        user_id: int,
        session_id: str,
        source_agent_id: str,
        agent_role: str,
        event_type: EventType,
        performative: Performative,
        event_payload: Dict[str, Any],
        target_agent_id: Optional[str] = None,
        semantic_context: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None
    ) -> BlackboardEvent:
        """Post an event to the blackboard and persist to database."""
        
        try:
            with get_database_session() as db:
                # Create blackboard event
                event = BlackboardEvent(
                    event_type=event_type,
                    performative=performative,
                    source_agent_id=source_agent_id,
                    target_agent_id=target_agent_id,
                    agent_role=agent_role,
                    user_id=user_id,
                    session_id=session_id,
                    event_payload=event_payload,
                    semantic_context=semantic_context or {},
                    parent_event_id=uuid.UUID(parent_event_id) if parent_event_id else None,
                    logical_timestamp=self._get_logical_timestamp(session_id),
                    causality_chain=[],
                    related_events=[]
                )
                
                db.add(event)
                db.commit()
                db.refresh(event)
                
                # Publish to event bus for real-time processing
                await self.event_bus.publish_event(event)
                
                logger.info(f"Posted blackboard event: {event_type.value} from {source_agent_id}")
                return event
                
        except Exception as e:
            logger.error(f"Failed to post blackboard event: {e}")
            raise
    
    async def get_recent_events(
        self,
        user_id: int,
        session_id: str,
        event_types: Optional[List[EventType]] = None,
        agent_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[BlackboardEvent]:
        """Retrieve recent blackboard events for context awareness."""
        
        try:
            with get_database_session() as db:
                query = db.query(BlackboardEvent).filter(
                    BlackboardEvent.user_id == user_id,
                    BlackboardEvent.session_id == session_id
                )
                
                if event_types:
                    query = query.filter(BlackboardEvent.event_type.in_([et.value for et in event_types]))
                
                if agent_filter:
                    query = query.filter(BlackboardEvent.source_agent_id == agent_filter)
                
                events = query.order_by(BlackboardEvent.created_at.desc()).limit(limit).all()
                return events
                
        except Exception as e:
            logger.error(f"Failed to retrieve blackboard events: {e}")
            return []
    
    async def store_agent_context(
        self,
        agent_id: str,
        agent_type: str,
        agent_role: str,
        user_id: int,
        session_id: str,
        context_key: str,
        context_value: Dict[str, Any],
        memory_tier: MemoryTier = MemoryTier.SHARED,
        is_shareable: bool = True,
        expires_at: Optional[datetime] = None
    ) -> AgentContextState:
        """Store agent context state for coordination."""
        
        try:
            with get_database_session() as db:
                # Check if context already exists
                existing_context = db.query(AgentContextState).filter(
                    AgentContextState.agent_id == agent_id,
                    AgentContextState.session_id == session_id,
                    AgentContextState.context_key == context_key
                ).first()
                
                if existing_context:
                    # Update existing context
                    existing_context.context_value = context_value
                    existing_context.version += 1
                    existing_context.updated_at = datetime.now(timezone.utc)
                    context_state = existing_context
                else:
                    # Create new context
                    context_state = AgentContextState(
                        agent_id=agent_id,
                        agent_type=agent_type,
                        agent_role=agent_role,
                        user_id=user_id,
                        session_id=session_id,
                        memory_tier=memory_tier,
                        context_key=context_key,
                        context_value=context_value,
                        is_shareable=is_shareable,
                        expires_at=expires_at,
                        access_permissions=[],
                        version=1
                    )
                    db.add(context_state)
                
                db.commit()
                db.refresh(context_state)
                
                logger.info(f"Stored agent context: {agent_id}:{context_key}")
                return context_state
                
        except Exception as e:
            logger.error(f"Failed to store agent context: {e}")
            raise
    
    async def get_agent_context(
        self,
        agent_id: str,
        session_id: str,
        context_key: Optional[str] = None,
        memory_tier: Optional[MemoryTier] = None
    ) -> List[AgentContextState]:
        """Retrieve agent context state for coordination."""
        
        try:
            with get_database_session() as db:
                query = db.query(AgentContextState).filter(
                    AgentContextState.agent_id == agent_id,
                    AgentContextState.session_id == session_id
                )
                
                if context_key:
                    query = query.filter(AgentContextState.context_key == context_key)
                
                if memory_tier:
                    query = query.filter(AgentContextState.memory_tier == memory_tier)
                
                contexts = query.all()
                return contexts
                
        except Exception as e:
            logger.error(f"Failed to retrieve agent context: {e}")
            return []
    
    async def get_shared_context(
        self,
        session_id: str,
        user_id: int,
        context_key: Optional[str] = None
    ) -> List[AgentContextState]:
        """Get shared context across all agents in session."""
        
        try:
            with get_database_session() as db:
                query = db.query(AgentContextState).filter(
                    AgentContextState.session_id == session_id,
                    AgentContextState.user_id == user_id,
                    AgentContextState.memory_tier == MemoryTier.SHARED,
                    AgentContextState.is_shareable == True
                )
                
                if context_key:
                    query = query.filter(AgentContextState.context_key == context_key)
                
                contexts = query.all()
                return contexts
                
        except Exception as e:
            logger.error(f"Failed to retrieve shared context: {e}")
            return []
    
    async def detect_contribution_opportunities(
        self,
        agent_id: str,
        agent_role: str,
        session_id: str,
        user_id: int,
        expertise_areas: List[str]
    ) -> List[Dict[str, Any]]:
        """Detect opportunities for agent contribution based on blackboard state."""
        
        opportunities = []
        
        try:
            # Get recent events to analyze contribution opportunities
            recent_events = await self.get_recent_events(
                user_id=user_id,
                session_id=session_id,
                limit=20
            )
            
            # Analyze events for contribution opportunities
            for event in recent_events:
                event_payload = event.event_payload
                
                # Check if agent can contribute based on expertise
                if self._matches_expertise(event_payload, expertise_areas):
                    opportunity = {
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "source_agent": event.source_agent_id,
                        "opportunity_type": self._determine_opportunity_type(event),
                        "suggested_contribution": self._suggest_contribution(event, agent_role),
                        "priority": self._calculate_priority(event, agent_role),
                        "created_at": event.created_at.isoformat()
                    }
                    opportunities.append(opportunity)
            
            # Sort by priority
            opportunities.sort(key=lambda x: x["priority"], reverse=True)
            
            logger.info(f"Found {len(opportunities)} contribution opportunities for {agent_id}")
            return opportunities[:5]  # Return top 5 opportunities
            
        except Exception as e:
            logger.error(f"Failed to detect contribution opportunities: {e}")
            return []
    
    def _get_logical_timestamp(self, session_id: str) -> int:
        """Get next logical timestamp for session."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {"logical_clock": 0}
        
        self.active_sessions[session_id]["logical_clock"] += 1
        return self.active_sessions[session_id]["logical_clock"]
    
    def _matches_expertise(self, event_payload: Dict[str, Any], expertise_areas: List[str]) -> bool:
        """Check if event matches agent's expertise areas."""
        event_content = json.dumps(event_payload).lower()
        
        for expertise in expertise_areas:
            if expertise.lower() in event_content:
                return True
        
        return False
    
    def _determine_opportunity_type(self, event: BlackboardEvent) -> str:
        """Determine the type of contribution opportunity."""
        event_type = event.event_type
        
        if event_type == EventType.AGENT_CONTRIBUTION:
            return "build_upon"
        elif event_type == EventType.CONFLICT_DETECTED:
            return "mediate"
        elif event_type == EventType.TASK_DELEGATED:
            return "assist"
        elif event_type == EventType.DECISION_MADE:
            return "validate"
        else:
            return "contribute"
    
    def _suggest_contribution(self, event: BlackboardEvent, agent_role: str) -> str:
        """Suggest specific contribution based on event and agent role."""
        event_type = event.event_type
        
        suggestions = {
            EventType.AGENT_CONTRIBUTION: f"As {agent_role}, provide additional insights",
            EventType.CONFLICT_DETECTED: f"Help resolve conflict using {agent_role} perspective",
            EventType.TASK_DELEGATED: f"Offer {agent_role} support for task execution",
            EventType.DECISION_MADE: f"Validate decision from {agent_role} viewpoint"
        }
        
        return suggestions.get(event_type, f"Contribute {agent_role} expertise")
    
    def _calculate_priority(self, event: BlackboardEvent, agent_role: str) -> float:
        """Calculate priority score for contribution opportunity."""
        base_priority = 0.5
        
        # Higher priority for recent events
        age_minutes = (datetime.now(timezone.utc) - event.created_at).total_seconds() / 60
        recency_factor = max(0.1, 1.0 - (age_minutes / 60))  # Decay over 1 hour
        
        # Role-specific priority adjustments
        role_priorities = {
            "Project Manager": 0.2,  # Lower base priority, higher for coordination events
            "Technical Expert": 0.3,
            "Business Analyst": 0.25,
            "Research Specialist": 0.3,
            "Quality Assurance": 0.4  # Higher priority for validation events
        }
        
        role_factor = role_priorities.get(agent_role, 0.25)
        
        # Event type priority
        event_type_priorities = {
            EventType.CONFLICT_DETECTED: 0.4,
            EventType.TASK_DELEGATED: 0.3,
            EventType.DECISION_MADE: 0.3,
            EventType.AGENT_CONTRIBUTION: 0.2
        }
        
        event_factor = event_type_priorities.get(EventType(event.event_type), 0.2)
        
        return base_priority + recency_factor + role_factor + event_factor


# Global service instance
blackboard_integration_service = BlackboardIntegrationService()