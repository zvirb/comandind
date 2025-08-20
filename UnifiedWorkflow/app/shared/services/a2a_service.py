"""
Agent-to-Agent (A2A) Protocol Service - Layer 2

Implements peer-to-peer communication between agents with dynamic discovery,
capability negotiation, and secure messaging infrastructure.

Key Features:
- Agent discovery and registration system
- Capability negotiation and matching
- Direct peer-to-peer messaging
- Session management for ongoing conversations
- Load balancing and failover for agent selection
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

import redis.asyncio as redis
from pydantic import BaseModel, Field

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, A2ADirectMessage, A2ACapabilityNegotiation, A2AAgentDiscovery,
    AgentProfile, AgentCapability, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.protocol_infrastructure import ProtocolServiceManager
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ================================
# Agent Registry
# ================================

class AgentStatus(str, Enum):
    """Agent availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class RegisteredAgent(BaseModel):
    """Registered agent in the A2A system."""
    agent_id: str
    profile: AgentProfile
    
    # Connection information
    connection_endpoint: str
    connection_type: str = "redis"  # "redis", "websocket", "http"
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Performance metrics
    average_response_time: float = 0.0
    message_count: int = 0
    success_rate: float = 1.0
    
    # Reputation and trust
    reputation_score: float = Field(ge=0.0, le=1.0, default=0.8)
    trust_level: str = "medium"  # "low", "medium", "high"
    endorsements: List[str] = Field(default_factory=list)
    
    # Operational state
    current_conversations: Set[str] = Field(default_factory=set)
    active_negotiations: Set[str] = Field(default_factory=set)
    
    # Registration metadata
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    registration_ttl: int = 3600  # seconds


class AgentRegistry:
    """Registry for managing agent discovery and availability."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.agents: Dict[str, RegisteredAgent] = {}
        self.capability_index: Dict[str, Set[str]] = defaultdict(set)
        self.domain_index: Dict[str, Set[str]] = defaultdict(set)
        self.heartbeat_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the agent registry."""
        await self._load_registered_agents()
        await self._rebuild_indexes()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        logger.info("Agent registry initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the agent registry."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent registry shutdown")
        
    async def register_agent(self, agent: RegisteredAgent) -> bool:
        """Register a new agent in the registry."""
        try:
            # Validate agent profile
            if not await self._validate_agent_profile(agent.profile):
                logger.error(f"Agent profile validation failed for {agent.agent_id}")
                return False
                
            # Store agent
            self.agents[agent.agent_id] = agent
            await self._persist_agent(agent)
            
            # Update indexes
            await self._update_capability_index(agent)
            await self._update_domain_index(agent)
            
            logger.info(f"Agent registered: {agent.agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent.agent_id}: {e}", exc_info=True)
            return False
            
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry."""
        try:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                
                # Remove from indexes
                await self._remove_from_indexes(agent)
                
                # Remove from registry
                del self.agents[agent_id]
                await self.redis.delete(f"a2a:agent:{agent_id}")
                
                logger.info(f"Agent unregistered: {agent_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}", exc_info=True)
            return False
            
    async def find_agents_by_capability(self, capability_name: str) -> List[RegisteredAgent]:
        """Find agents that provide a specific capability."""
        agent_ids = self.capability_index.get(capability_name, set())
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
        
    async def find_agents_by_domain(self, domain: str) -> List[RegisteredAgent]:
        """Find agents that operate in a specific domain."""
        agent_ids = self.domain_index.get(domain, set())
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
        
    async def find_best_agent(
        self,
        required_capabilities: List[str],
        domain: Optional[str] = None,
        selection_criteria: Dict[str, Any] = None
    ) -> Optional[RegisteredAgent]:
        """Find the best agent matching the requirements."""
        candidates = []
        
        # Find agents with required capabilities
        for capability in required_capabilities:
            capable_agents = await self.find_agents_by_capability(capability)
            if not candidates:
                candidates = capable_agents
            else:
                # Intersection - agents must have ALL capabilities
                candidates = [agent for agent in candidates if agent in capable_agents]
                
        # Filter by domain if specified
        if domain:
            domain_agents = await self.find_agents_by_domain(domain)
            candidates = [agent for agent in candidates if agent in domain_agents]
            
        # Filter by availability
        candidates = [agent for agent in candidates 
                     if agent.profile.availability_status == "available"]
        
        if not candidates:
            return None
            
        # Apply selection strategy
        strategy = selection_criteria.get("strategy", "best_fit") if selection_criteria else "best_fit"
        
        if strategy == "least_loaded":
            return min(candidates, key=lambda a: a.profile.current_load)
        elif strategy == "fastest_response":
            return min(candidates, key=lambda a: a.average_response_time)
        elif strategy == "highest_reputation":
            return max(candidates, key=lambda a: a.reputation_score)
        else:  # best_fit (default)
            # Score based on multiple factors
            def score_agent(agent: RegisteredAgent) -> float:
                score = agent.reputation_score * 0.4
                score += (1.0 - agent.profile.current_load) * 0.3
                score += (1.0 / max(1.0, agent.average_response_time)) * 0.2
                score += agent.success_rate * 0.1
                return score
                
            return max(candidates, key=score_agent)
            
    async def get_agent(self, agent_id: str) -> Optional[RegisteredAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
        
    async def list_agents(self, status_filter: Optional[str] = None) -> List[RegisteredAgent]:
        """List all registered agents, optionally filtered by status."""
        agents = list(self.agents.values())
        if status_filter:
            agents = [agent for agent in agents 
                     if agent.profile.availability_status == status_filter]
        return agents
        
    async def update_agent_heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat timestamp."""
        if agent_id in self.agents:
            self.agents[agent_id].last_heartbeat = datetime.now(timezone.utc)
            await self._persist_agent(self.agents[agent_id])
            
    async def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update agent availability status."""
        if agent_id in self.agents:
            self.agents[agent_id].profile.availability_status = status
            await self._persist_agent(self.agents[agent_id])
            
    async def _validate_agent_profile(self, profile: AgentProfile) -> bool:
        """Validate agent profile."""
        if not profile.agent_id or not profile.agent_name:
            return False
        if not profile.capabilities:
            return False
        return True
        
    async def _persist_agent(self, agent: RegisteredAgent) -> None:
        """Persist agent to Redis."""
        agent_key = f"a2a:agent:{agent.agent_id}"
        await self.redis.setex(agent_key, agent.registration_ttl, agent.json())
        
    async def _load_registered_agents(self) -> None:
        """Load registered agents from Redis."""
        pattern = "a2a:agent:*"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            try:
                agent_data = await self.redis.get(key)
                if agent_data:
                    agent = RegisteredAgent.parse_raw(agent_data)
                    self.agents[agent.agent_id] = agent
            except Exception as e:
                logger.error(f"Error loading agent from {key}: {e}", exc_info=True)
                
        logger.info(f"Loaded {len(self.agents)} agents from registry")
        
    async def _rebuild_indexes(self) -> None:
        """Rebuild capability and domain indexes."""
        self.capability_index.clear()
        self.domain_index.clear()
        
        for agent in self.agents.values():
            await self._update_capability_index(agent)
            await self._update_domain_index(agent)
            
    async def _update_capability_index(self, agent: RegisteredAgent) -> None:
        """Update capability index for an agent."""
        for capability in agent.profile.capabilities:
            self.capability_index[capability.capability_id].add(agent.agent_id)
            self.capability_index[capability.name].add(agent.agent_id)
            
    async def _update_domain_index(self, agent: RegisteredAgent) -> None:
        """Update domain index for an agent."""
        for domain in agent.profile.supported_domains:
            self.domain_index[domain].add(agent.agent_id)
            
    async def _remove_from_indexes(self, agent: RegisteredAgent) -> None:
        """Remove agent from all indexes."""
        for capability in agent.profile.capabilities:
            self.capability_index[capability.capability_id].discard(agent.agent_id)
            self.capability_index[capability.name].discard(agent.agent_id)
            
        for domain in agent.profile.supported_domains:
            self.domain_index[domain].discard(agent.agent_id)
            
    async def _heartbeat_monitor(self) -> None:
        """Monitor agent heartbeats and mark offline agents."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                now = datetime.now(timezone.utc)
                offline_agents = []
                
                for agent_id, agent in self.agents.items():
                    time_since_heartbeat = (now - agent.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > 120:  # 2 minutes
                        offline_agents.append(agent_id)
                        agent.profile.availability_status = "offline"
                        await self._persist_agent(agent)
                        
                if offline_agents:
                    logger.info(f"Marked {len(offline_agents)} agents as offline")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}", exc_info=True)


# ================================
# Message Router for A2A
# ================================

class A2AMessageRouter:
    """Routes messages between agents in the A2A layer."""
    
    def __init__(self, agent_registry: AgentRegistry, redis_client: redis.Redis):
        self.registry = agent_registry
        self.redis = redis_client
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        
    async def send_direct_message(
        self,
        sender_id: str,
        target_agent_id: str,
        message_content: str,
        conversation_id: Optional[str] = None,
        expects_response: bool = False
    ) -> bool:
        """Send a direct message to another agent."""
        try:
            # Get target agent
            target_agent = await self.registry.get_agent(target_agent_id)
            if not target_agent:
                logger.error(f"Target agent {target_agent_id} not found")
                return False
                
            # Create conversation ID if not provided
            if not conversation_id:
                conversation_id = str(uuid.uuid4())
                
            # Create message
            message = A2ADirectMessage(
                metadata=ProtocolMetadata(
                    sender_id=sender_id,
                    sender_type="agent",
                    protocol_layer="a2a",
                    intent=MessageIntent.INFORM,
                    conversation_id=conversation_id,
                    requires_response=expects_response
                ),
                target_agent_id=target_agent_id,
                message_content=message_content,
                conversation_context=self.active_conversations.get(conversation_id, {}),
                expects_response=expects_response
            )
            
            # Route message to target
            return await self._deliver_message(target_agent, message)
            
        except Exception as e:
            logger.error(f"Error sending direct message: {e}", exc_info=True)
            return False
            
    async def negotiate_capability(
        self,
        requester_id: str,
        target_agent_id: str,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        negotiation_terms: Dict[str, Any]
    ) -> Optional[str]:
        """Initiate capability negotiation with another agent."""
        try:
            negotiation_id = str(uuid.uuid4())
            
            message = A2ACapabilityNegotiation(
                metadata=ProtocolMetadata(
                    sender_id=requester_id,
                    sender_type="agent",
                    protocol_layer="a2a",
                    intent=MessageIntent.REQUEST,
                    requires_response=True
                ),
                negotiation_id=negotiation_id,
                negotiation_type="request",
                required_capabilities=required_capabilities,
                task_parameters=task_parameters,
                proposed_terms=negotiation_terms
            )
            
            # Get target agent
            target_agent = await self.registry.get_agent(target_agent_id)
            if not target_agent:
                return None
                
            # Send negotiation request
            if await self._deliver_message(target_agent, message):
                return negotiation_id
                
        except Exception as e:
            logger.error(f"Error initiating capability negotiation: {e}", exc_info=True)
            
        return None
        
    async def discover_agents(
        self,
        requester_id: str,
        query_criteria: Dict[str, Any]
    ) -> List[AgentProfile]:
        """Discover agents matching criteria."""
        try:
            # Create discovery message
            message = A2AAgentDiscovery(
                metadata=ProtocolMetadata(
                    sender_id=requester_id,
                    sender_type="agent",
                    protocol_layer="a2a",
                    intent=MessageIntent.QUERY
                ),
                discovery_type="query",
                query_criteria=query_criteria
            )
            
            # Process discovery query locally
            discovered = []
            
            # Search by capabilities
            if "capabilities" in query_criteria:
                for capability in query_criteria["capabilities"]:
                    agents = await self.registry.find_agents_by_capability(capability)
                    discovered.extend([agent.profile for agent in agents])
                    
            # Search by domain
            if "domain" in query_criteria:
                agents = await self.registry.find_agents_by_domain(query_criteria["domain"])
                discovered.extend([agent.profile for agent in agents])
                
            # Search by agent type
            if "agent_type" in query_criteria:
                agent_type = query_criteria["agent_type"]
                all_agents = await self.registry.list_agents("available")
                matching = [agent for agent in all_agents 
                           if agent.profile.agent_type == agent_type]
                discovered.extend([agent.profile for agent in matching])
                
            # Remove duplicates
            unique_profiles = {}
            for profile in discovered:
                unique_profiles[profile.agent_id] = profile
                
            return list(unique_profiles.values())
            
        except Exception as e:
            logger.error(f"Error discovering agents: {e}", exc_info=True)
            return []
            
    async def _deliver_message(self, target_agent: RegisteredAgent, message: BaseProtocolMessage) -> bool:
        """Deliver a message to a target agent."""
        try:
            if target_agent.connection_type == "redis":
                # Send via Redis queue
                queue_key = f"a2a:queue:{target_agent.agent_id}"
                message_data = json.dumps(message.dict())
                await self.redis.lpush(queue_key, message_data)
                await self.redis.expire(queue_key, 3600)  # 1 hour TTL
                return True
                
            elif target_agent.connection_type == "websocket":
                # Send via WebSocket (implement WebSocket delivery)
                # This would integrate with the existing WebSocket infrastructure
                pass
                
            elif target_agent.connection_type == "http":
                # Send via HTTP POST
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        target_agent.connection_endpoint,
                        json=message.dict()
                    )
                    return response.status_code < 400
                    
        except Exception as e:
            logger.error(f"Error delivering message to {target_agent.agent_id}: {e}", exc_info=True)
            
        return False


# ================================
# Capability Negotiation Engine
# ================================

class CapabilityNegotiator:
    """Handles capability negotiation between agents."""
    
    def __init__(self, agent_registry: AgentRegistry, message_router: A2AMessageRouter):
        self.registry = agent_registry
        self.router = message_router
        self.active_negotiations: Dict[str, Dict[str, Any]] = {}
        
    async def initiate_negotiation(
        self,
        requester_id: str,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        selection_criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[str, str]]:  # Returns (negotiation_id, selected_agent_id)
        """Initiate capability negotiation process."""
        try:
            # Find candidate agents
            candidates = []
            for capability in required_capabilities:
                capable_agents = await self.registry.find_agents_by_capability(capability)
                candidates.extend(capable_agents)
                
            # Remove duplicates and filter available agents
            unique_candidates = {}
            for agent in candidates:
                if (agent.agent_id not in unique_candidates and 
                    agent.profile.availability_status == "available"):
                    unique_candidates[agent.agent_id] = agent
                    
            if not unique_candidates:
                logger.warning(f"No available agents found for capabilities: {required_capabilities}")
                return None
                
            # Score and rank candidates
            ranked_candidates = await self._rank_candidates(
                list(unique_candidates.values()),
                required_capabilities,
                task_parameters,
                selection_criteria
            )
            
            # Start negotiation with best candidate
            best_candidate = ranked_candidates[0]
            
            negotiation_terms = {
                "task_priority": task_parameters.get("priority", "normal"),
                "expected_duration": task_parameters.get("expected_duration"),
                "resource_constraints": task_parameters.get("constraints", {}),
                "quality_requirements": task_parameters.get("quality", {})
            }
            
            negotiation_id = await self.router.negotiate_capability(
                requester_id,
                best_candidate.agent_id,
                required_capabilities,
                task_parameters,
                negotiation_terms
            )
            
            if negotiation_id:
                # Track negotiation
                self.active_negotiations[negotiation_id] = {
                    "requester_id": requester_id,
                    "target_agent_id": best_candidate.agent_id,
                    "capabilities": required_capabilities,
                    "parameters": task_parameters,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc),
                    "fallback_candidates": ranked_candidates[1:5]  # Keep top 5 fallbacks
                }
                
                return negotiation_id, best_candidate.agent_id
                
        except Exception as e:
            logger.error(f"Error initiating negotiation: {e}", exc_info=True)
            
        return None
        
    async def handle_negotiation_response(
        self,
        negotiation_id: str,
        response_type: str,  # "accept", "reject", "counter"
        response_data: Dict[str, Any]
    ) -> bool:
        """Handle negotiation response from target agent."""
        if negotiation_id not in self.active_negotiations:
            logger.warning(f"Unknown negotiation ID: {negotiation_id}")
            return False
            
        negotiation = self.active_negotiations[negotiation_id]
        
        if response_type == "accept":
            # Negotiation successful
            negotiation["status"] = "accepted"
            negotiation["accepted_terms"] = response_data
            logger.info(f"Negotiation {negotiation_id} accepted")
            return True
            
        elif response_type == "reject":
            # Try fallback candidates
            fallback_candidates = negotiation.get("fallback_candidates", [])
            if fallback_candidates:
                next_candidate = fallback_candidates.pop(0)
                negotiation["fallback_candidates"] = fallback_candidates
                
                # Retry with next candidate
                new_negotiation_id = await self.router.negotiate_capability(
                    negotiation["requester_id"],
                    next_candidate.agent_id,
                    negotiation["capabilities"],
                    negotiation["parameters"],
                    response_data.get("suggested_terms", {})
                )
                
                if new_negotiation_id:
                    # Update negotiation tracking
                    negotiation["retry_negotiation_id"] = new_negotiation_id
                    logger.info(f"Retrying negotiation with fallback candidate: {next_candidate.agent_id}")
                    return True
                    
            # No more candidates, negotiation failed
            negotiation["status"] = "failed"
            logger.info(f"Negotiation {negotiation_id} failed - no suitable agents")
            return False
            
        elif response_type == "counter":
            # Handle counter-proposal
            counter_terms = response_data.get("counter_terms", {})
            
            # Evaluate counter-proposal (simplified logic)
            if await self._evaluate_counter_proposal(negotiation, counter_terms):
                # Accept counter-proposal
                negotiation["status"] = "accepted"
                negotiation["accepted_terms"] = counter_terms
                logger.info(f"Negotiation {negotiation_id} accepted with counter-terms")
                return True
            else:
                # Reject counter-proposal, try fallback
                return await self.handle_negotiation_response(negotiation_id, "reject", response_data)
                
        return False
        
    async def _rank_candidates(
        self,
        candidates: List[RegisteredAgent],
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        selection_criteria: Optional[Dict[str, Any]]
    ) -> List[RegisteredAgent]:
        """Rank candidate agents based on multiple criteria."""
        scored_candidates = []
        
        for candidate in candidates:
            score = await self._score_candidate(
                candidate, required_capabilities, task_parameters, selection_criteria
            )
            scored_candidates.append((score, candidate))
            
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        return [candidate for score, candidate in scored_candidates]
        
    async def _score_candidate(
        self,
        candidate: RegisteredAgent,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        selection_criteria: Optional[Dict[str, Any]]
    ) -> float:
        """Score a candidate agent for capability matching."""
        score = 0.0
        
        # Capability match score (40%)
        matched_capabilities = 0
        for req_cap in required_capabilities:
            for agent_cap in candidate.profile.capabilities:
                if req_cap in agent_cap.name or req_cap == agent_cap.capability_id:
                    matched_capabilities += 1
                    break
                    
        capability_score = matched_capabilities / len(required_capabilities)
        score += capability_score * 0.4
        
        # Availability score (20%)
        availability_score = 1.0 - candidate.profile.current_load
        score += availability_score * 0.2
        
        # Performance score (20%)
        performance_score = candidate.success_rate
        score += performance_score * 0.2
        
        # Reputation score (10%)
        score += candidate.reputation_score * 0.1
        
        # Response time score (10%)
        response_time_score = 1.0 / max(1.0, candidate.average_response_time)
        score += min(1.0, response_time_score) * 0.1
        
        return score
        
    async def _evaluate_counter_proposal(
        self,
        negotiation: Dict[str, Any],
        counter_terms: Dict[str, Any]
    ) -> bool:
        """Evaluate whether to accept a counter-proposal."""
        # Simplified evaluation logic
        original_priority = negotiation["parameters"].get("priority", "normal")
        proposed_priority = counter_terms.get("task_priority", "normal")
        
        # Accept if priority is maintained or improved
        priority_order = {"low": 1, "normal": 2, "high": 3, "critical": 4}
        return priority_order.get(proposed_priority, 2) >= priority_order.get(original_priority, 2)


# ================================
# A2A Service Manager
# ================================

class A2AService:
    """Main A2A service for agent-to-agent communication."""
    
    def __init__(self, protocol_manager: ProtocolServiceManager):
        self.protocol_manager = protocol_manager
        self.redis = protocol_manager.redis
        self.agent_registry: Optional[AgentRegistry] = None
        self.message_router: Optional[A2AMessageRouter] = None
        self.capability_negotiator: Optional[CapabilityNegotiator] = None
        
    async def initialize(self) -> None:
        """Initialize the A2A service."""
        # Initialize agent registry
        self.agent_registry = AgentRegistry(self.redis)
        await self.agent_registry.initialize()
        
        # Initialize message router
        self.message_router = A2AMessageRouter(self.agent_registry, self.redis)
        
        # Initialize capability negotiator
        self.capability_negotiator = CapabilityNegotiator(self.agent_registry, self.message_router)
        
        # Register message handlers
        await self.protocol_manager.router.register_handler("a2a:direct_message", self._handle_direct_message)
        await self.protocol_manager.router.register_handler("a2a:capability_negotiation", self._handle_capability_negotiation)
        await self.protocol_manager.router.register_handler("a2a:agent_discovery", self._handle_agent_discovery)
        
        logger.info("A2A service initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the A2A service."""
        if self.agent_registry:
            await self.agent_registry.shutdown()
        logger.info("A2A service shutdown")
        
    async def register_agent(self, agent_profile: AgentProfile, connection_endpoint: str) -> bool:
        """Register an agent with the A2A system."""
        if not self.agent_registry:
            raise RuntimeError("A2A service not initialized")
            
        agent = RegisteredAgent(
            agent_id=agent_profile.agent_id,
            profile=agent_profile,
            connection_endpoint=connection_endpoint
        )
        
        return await self.agent_registry.register_agent(agent)
        
    async def send_message(
        self,
        sender_id: str,
        target_agent_id: str,
        message_content: str,
        conversation_id: Optional[str] = None
    ) -> bool:
        """Send a direct message to another agent."""
        if not self.message_router:
            raise RuntimeError("A2A service not initialized")
            
        return await self.message_router.send_direct_message(
            sender_id, target_agent_id, message_content, conversation_id
        )
        
    async def find_agents(
        self,
        required_capabilities: List[str],
        domain: Optional[str] = None,
        selection_criteria: Optional[Dict[str, Any]] = None
    ) -> List[AgentProfile]:
        """Find agents matching specific criteria."""
        if not self.agent_registry:
            raise RuntimeError("A2A service not initialized")
            
        # Find by capabilities
        candidates = []
        for capability in required_capabilities:
            agents = await self.agent_registry.find_agents_by_capability(capability)
            candidates.extend(agents)
            
        # Filter by domain if specified
        if domain:
            domain_agents = await self.agent_registry.find_agents_by_domain(domain)
            candidates = [agent for agent in candidates if agent in domain_agents]
            
        # Remove duplicates and return profiles
        unique_agents = {}
        for agent in candidates:
            unique_agents[agent.agent_id] = agent.profile
            
        return list(unique_agents.values())
        
    async def negotiate_capability(
        self,
        requester_id: str,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any]
    ) -> Optional[Tuple[str, str]]:
        """Initiate capability negotiation."""
        if not self.capability_negotiator:
            raise RuntimeError("A2A service not initialized")
            
        return await self.capability_negotiator.initiate_negotiation(
            requester_id, required_capabilities, task_parameters
        )
        
    async def _handle_direct_message(self, message: A2ADirectMessage) -> None:
        """Handle incoming direct messages."""
        logger.info(f"Received direct message from {message.metadata.sender_id} to {message.target_agent_id}")
        # Forward to local agent or store for retrieval
        
    async def _handle_capability_negotiation(self, message: A2ACapabilityNegotiation) -> None:
        """Handle capability negotiation messages."""
        logger.info(f"Received capability negotiation: {message.negotiation_type} from {message.metadata.sender_id}")
        # Process negotiation request/response
        
    async def _handle_agent_discovery(self, message: A2AAgentDiscovery) -> None:
        """Handle agent discovery messages."""
        logger.info(f"Received agent discovery query from {message.metadata.sender_id}")
        # Process discovery query and send response


# ================================
# A2A Factory
# ================================

async def create_a2a_service(protocol_manager: ProtocolServiceManager) -> A2AService:
    """Create and initialize an A2A service."""
    service = A2AService(protocol_manager)
    await service.initialize()
    return service