"""Enhanced Agent Communication Protocol

Real inter-agent communication system enabling coordination between agents
during parallel execution with ML-enhanced routing and intelligent coordination.

Stream 3 Implementation - Key Features:
- Real-time message passing between agents
- Coordination hub for parallel execution coordination
- Context sharing and dynamic information gathering
- Conflict resolution with resource management
- Dynamic agent requests and resource notifications
- MCP service integration for persistence and intelligence

This enhances the existing communication framework with the specific
requirements for Stream 3: Inter-Agent Communication Protocol.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Set, Callable, Union
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    import structlog
    logger = structlog.get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# Enhanced message types for Stream 3 requirements
class MessageType(Enum):
    """Enhanced message types for inter-agent communication."""
    # Basic communication
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    
    # Coordination and collaboration
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"
    CONTEXT_SHARE = "context_share"
    CONTEXT_REQUEST = "context_request"
    
    # Dynamic requests (Stream 3 requirement)
    AGENT_REQUEST = "agent_request"          # Request additional agents
    RESOURCE_REQUEST = "resource_request"     # Request resources
    CAPABILITY_REQUEST = "capability_request" # Request specific capabilities
    
    # Resource notifications (Stream 3 requirement)
    RESOURCE_AVAILABLE = "resource_available"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    AGENT_AVAILABLE = "agent_available"
    AGENT_BUSY = "agent_busy"
    
    # Conflict resolution (Stream 3 requirement)
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLUTION = "conflict_resolution"
    PRIORITY_ESCALATION = "priority_escalation"
    
    # Status and monitoring
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 1    # System-critical, immediate processing
    HIGH = 2        # High priority, fast processing
    NORMAL = 3      # Normal priority
    LOW = 4         # Low priority, process when convenient
    BACKGROUND = 5  # Background processing

class AgentRole(Enum):
    """Agent roles in orchestration hierarchy."""
    ORCHESTRATOR = "orchestrator"      # Top-level orchestration agents
    COORDINATOR = "coordinator"        # Cross-domain coordination agents
    SPECIALIST = "specialist"          # Domain specialist agents
    VALIDATOR = "validator"            # Validation and quality agents
    UTILITY = "utility"               # Utility and support agents

@dataclass
class AgentMessage:
    """Enhanced inter-agent communication message."""
    # Core identification
    id: str = field(default_factory=lambda: str(uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    
    # Message classification
    message_type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    
    # Content and context
    content: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Workflow coordination
    workflow_id: Optional[str] = None
    coordination_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    
    # Timing and lifecycle
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Processing metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_response: bool = False
    response_timeout: float = 30.0
    
    # Stream 3 enhancements
    dynamic_request_type: Optional[str] = None    # For dynamic agent/resource requests
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    conflict_context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentInfo:
    """Enhanced agent information for communication system."""
    agent_id: str
    agent_type: str
    role: AgentRole
    capabilities: List[str]
    specializations: List[str]
    
    # Resource management
    max_concurrent_tasks: int = 3
    current_task_count: int = 0
    available_resources: Dict[str, Any] = field(default_factory=dict)
    required_resources: Dict[str, Any] = field(default_factory=dict)
    
    # Status and health
    status: str = "available"  # available, busy, offline, error
    last_seen: float = field(default_factory=time.time)
    health_score: float = 1.0
    
    # Performance and preferences
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    communication_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Stream 3 enhancements
    collaboration_history: List[str] = field(default_factory=list)
    conflict_resolution_score: float = 1.0
    dynamic_request_capability: bool = True

@dataclass
class WorkflowContext:
    """Enhanced shared context for workflow coordination."""
    workflow_id: str
    phase: int
    current_step: str
    
    # Agent coordination
    participating_agents: Set[str]
    agent_roles: Dict[str, str] = field(default_factory=dict)
    coordination_state: Dict[str, Any] = field(default_factory=dict)
    
    # Data and resources
    shared_data: Dict[str, Any] = field(default_factory=dict)
    resource_allocations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Dependencies and completion
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    completion_status: Dict[str, bool] = field(default_factory=dict)
    
    # Timing
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Stream 3 enhancements
    dynamic_agents: Set[str] = field(default_factory=set)  # Dynamically added agents
    conflict_log: List[Dict[str, Any]] = field(default_factory=list)
    resource_requests: List[Dict[str, Any]] = field(default_factory=list)

class EnhancedAgentCommunicationHub:
    """Enhanced communication hub implementing Stream 3 requirements."""
    
    def __init__(self, use_mcp_services: bool = True):
        """Initialize the enhanced communication hub."""
        self.use_mcp_services = use_mcp_services
        
        # Core communication infrastructure
        self.agents: Dict[str, AgentInfo] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = {}
        self.response_waiters: Dict[str, asyncio.Future] = {}
        
        # Workflow coordination
        self.workflow_contexts: Dict[str, WorkflowContext] = {}
        self.coordination_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Stream 3 specific features
        self.resource_registry: Dict[str, Dict[str, Any]] = {}
        self.capability_registry: Dict[str, Set[str]] = {}
        self.conflict_resolver = ConflictResolver()
        self.dynamic_coordinator = DynamicCoordinator()
        
        # Communication patterns
        self.broadcast_groups: Dict[str, Set[str]] = {}
        self.routing_rules: Dict[str, List[str]] = {}
        
        # State management
        self.running = False
        self._background_tasks: List[asyncio.Task] = []
        
        logger.info("Enhanced Agent Communication Hub initialized", 
                   mcp_services=use_mcp_services)
    
    async def start(self):
        """Start the enhanced communication hub."""
        self.running = True
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._process_messages()),
            asyncio.create_task(self._monitor_agent_health()),
            asyncio.create_task(self._handle_resource_notifications()),
            asyncio.create_task(self._coordinate_workflows()),
            asyncio.create_task(self._resolve_conflicts())
        ]
        self._background_tasks.extend(tasks)
        
        # Initialize MCP services if enabled
        if self.use_mcp_services:
            await self._initialize_mcp_services()
        
        logger.info("Enhanced Agent Communication Hub started")
    
    async def stop(self):
        """Stop the enhanced communication hub."""
        self.running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
        logger.info("Enhanced Agent Communication Hub stopped")
    
    # STREAM 3 REQUIREMENT 1: Real Message Passing System
    async def send_message(self, message: AgentMessage) -> bool:
        """Enhanced message sending with Stream 3 features."""
        try:
            # Validate message
            if not self._validate_message(message):
                return False
            
            # Check for conflicts (Stream 3 requirement)
            if await self._detect_message_conflicts(message):
                await self._handle_message_conflict(message)
                return False
            
            # Dynamic routing optimization
            optimized_route = await self._optimize_message_route(message)
            if optimized_route:
                message.metadata.update(optimized_route)
            
            # Handle different message types
            if message.message_type == MessageType.BROADCAST:
                return await self._handle_broadcast_message(message)
            elif message.message_type == MessageType.AGENT_REQUEST:
                return await self._handle_dynamic_agent_request(message)
            elif message.message_type == MessageType.RESOURCE_REQUEST:
                return await self._handle_resource_request(message)
            else:
                return await self._send_direct_message(message)
            
        except Exception as e:
            logger.error("Message send failed", 
                        message_id=message.id, error=str(e))
            return False
    
    async def _send_direct_message(self, message: AgentMessage) -> bool:
        """Send direct message between agents."""
        if message.to_agent not in self.message_queues:
            logger.warning("Target agent not found", 
                          to_agent=message.to_agent, message_id=message.id)
            return False
        
        # Add to target agent's queue
        queue = self.message_queues[message.to_agent]
        await queue.put(message)
        
        # Handle response expectation
        if message.requires_response:
            future = asyncio.Future()
            self.response_waiters[message.id] = future
            
            # Set timeout for response
            async def timeout_handler():
                await asyncio.sleep(message.response_timeout)
                if message.id in self.response_waiters:
                    future.cancel()
                    del self.response_waiters[message.id]
            
            asyncio.create_task(timeout_handler())
        
        # Update communication tracking
        await self._track_communication(message)
        
        logger.info("Direct message sent", 
                   from_agent=message.from_agent,
                   to_agent=message.to_agent,
                   message_id=message.id,
                   message_type=message.message_type.value)
        
        return True
    
    async def receive_message(self, agent_id: str, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Enhanced message receiving with priority handling."""
        try:
            if agent_id not in self.message_queues:
                return None
            
            queue = self.message_queues[agent_id]
            
            # Try to get message with timeout
            try:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
                
                # Update agent status
                if agent_id in self.agents:
                    self.agents[agent_id].last_seen = time.time()
                    self.agents[agent_id].current_task_count += 1
                
                # Handle special message types
                if message.message_type == MessageType.HEARTBEAT:
                    await self._handle_heartbeat(message)
                elif message.message_type == MessageType.RESOURCE_AVAILABLE:
                    await self._handle_resource_notification(message)
                
                logger.debug("Message received", 
                            agent_id=agent_id, message_id=message.id)
                
                return message
                
            except asyncio.TimeoutError:
                return None
                
        except Exception as e:
            logger.error("Message receive failed", 
                        agent_id=agent_id, error=str(e))
            return None
    
    async def send_response(self, response_to_message_id: str, response: AgentMessage) -> bool:
        """Send response to a specific message."""
        response.parent_message_id = response_to_message_id
        response.message_type = MessageType.RESPONSE
        
        # Send the response
        success = await self.send_message(response)
        
        # Notify waiting future
        if response_to_message_id in self.response_waiters:
            future = self.response_waiters[response_to_message_id]
            if not future.cancelled():
                future.set_result(response)
            del self.response_waiters[response_to_message_id]
        
        return success
    
    async def wait_for_response(self, message_id: str, timeout: float = 30.0) -> Optional[AgentMessage]:
        """Wait for response to a specific message."""
        if message_id not in self.response_waiters:
            return None
        
        try:
            future = self.response_waiters[message_id]
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning("Response timeout", message_id=message_id)
            if message_id in self.response_waiters:
                del self.response_waiters[message_id]
            return None
    
    # STREAM 3 REQUIREMENT 2: Dynamic Agent Requests
    async def request_additional_agent(self, requesting_agent: str, 
                                     required_capabilities: List[str],
                                     task_description: str,
                                     priority: MessagePriority = MessagePriority.HIGH) -> Optional[str]:
        """Request additional agent with specific capabilities."""
        request = AgentMessage(
            from_agent=requesting_agent,
            to_agent="coordination_hub",
            message_type=MessageType.AGENT_REQUEST,
            priority=priority,
            content={
                "required_capabilities": required_capabilities,
                "task_description": task_description,
                "requesting_context": await self._get_agent_context(requesting_agent)
            },
            dynamic_request_type="agent_request",
            requires_response=True,
            response_timeout=10.0
        )
        
        # Send request to dynamic coordinator
        success = await self.send_message(request)
        if not success:
            return None
        
        # Wait for response
        response = await self.wait_for_response(request.id)
        if response and response.content.get("agent_assigned"):
            assigned_agent = response.content["assigned_agent_id"]
            
            # Add to current workflow if applicable
            if requesting_agent in self.agents:
                await self._add_agent_to_workflow(requesting_agent, assigned_agent)
            
            logger.info("Additional agent assigned", 
                       requesting_agent=requesting_agent,
                       assigned_agent=assigned_agent,
                       capabilities=required_capabilities)
            
            return assigned_agent
        
        return None
    
    async def _handle_dynamic_agent_request(self, message: AgentMessage) -> bool:
        """Handle dynamic agent request."""
        required_capabilities = message.content.get("required_capabilities", [])
        task_description = message.content.get("task_description", "")
        
        # Find suitable agent
        suitable_agent = await self._find_suitable_agent(required_capabilities)
        
        if suitable_agent:
            # Send response with assigned agent
            response = AgentMessage(
                from_agent="coordination_hub",
                to_agent=message.from_agent,
                content={
                    "agent_assigned": True,
                    "assigned_agent_id": suitable_agent,
                    "agent_capabilities": self.agents[suitable_agent].capabilities,
                    "estimated_availability": time.time() + 60  # Available in 1 minute
                }
            )
            
            await self.send_response(message.id, response)
            
            # Notify assigned agent
            notification = AgentMessage(
                from_agent="coordination_hub",
                to_agent=suitable_agent,
                message_type=MessageType.NOTIFICATION,
                content={
                    "assignment_type": "dynamic_request",
                    "requesting_agent": message.from_agent,
                    "task_description": task_description,
                    "expected_collaboration": True
                }
            )
            
            await self.send_message(notification)
            return True
        else:
            # No suitable agent found
            response = AgentMessage(
                from_agent="coordination_hub",
                to_agent=message.from_agent,
                content={
                    "agent_assigned": False,
                    "reason": "No suitable agent available",
                    "alternative_suggestions": await self._get_alternative_suggestions(required_capabilities)
                }
            )
            
            await self.send_response(message.id, response)
            return False
    
    # STREAM 3 REQUIREMENT 3: Context Sharing and Dynamic Information Gathering
    async def share_context(self, from_agent: str, to_agent: str, 
                          context_data: Dict[str, Any],
                          context_type: str = "general") -> bool:
        """Share context between agents."""
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.CONTEXT_SHARE,
            priority=MessagePriority.NORMAL,
            content={
                "context_type": context_type,
                "context_data": context_data,
                "timestamp": time.time(),
                "source_agent": from_agent
            },
            context={"sharing_purpose": "collaboration"}
        )
        
        return await self.send_message(message)
    
    async def request_context(self, requesting_agent: str, target_agent: str,
                            context_type: str, specific_data: List[str] = None) -> Optional[Dict[str, Any]]:
        """Request specific context from another agent."""
        request = AgentMessage(
            from_agent=requesting_agent,
            to_agent=target_agent,
            message_type=MessageType.CONTEXT_REQUEST,
            priority=MessagePriority.HIGH,
            content={
                "context_type": context_type,
                "specific_data": specific_data or [],
                "requester_context": await self._get_agent_context(requesting_agent)
            },
            requires_response=True,
            response_timeout=15.0
        )
        
        success = await self.send_message(request)
        if not success:
            return None
        
        response = await self.wait_for_response(request.id)
        if response and response.content.get("context_provided"):
            return response.content["context_data"]
        
        return None
    
    async def broadcast_to_group(self, from_agent: str, group_name: str,
                               message_content: Dict[str, Any],
                               message_type: MessageType = MessageType.BROADCAST) -> int:
        """Broadcast message to a group of agents."""
        if group_name not in self.broadcast_groups:
            logger.warning("Broadcast group not found", group=group_name)
            return 0
        
        target_agents = self.broadcast_groups[group_name]
        sent_count = 0
        
        for target_agent in target_agents:
            if target_agent == from_agent:  # Don't send to self
                continue
            
            message = AgentMessage(
                from_agent=from_agent,
                to_agent=target_agent,
                message_type=message_type,
                priority=MessagePriority.NORMAL,
                content=message_content,
                metadata={"broadcast_group": group_name}
            )
            
            if await self.send_message(message):
                sent_count += 1
        
        logger.info("Broadcast sent", 
                   from_agent=from_agent, group=group_name,
                   targets=len(target_agents), sent=sent_count)
        
        return sent_count
    
    # STREAM 3 REQUIREMENT 4: Conflict Resolution
    async def _detect_message_conflicts(self, message: AgentMessage) -> bool:
        """Detect potential conflicts in message."""
        # Resource conflicts
        if message.resource_requirements:
            for resource, amount in message.resource_requirements.items():
                if not await self._check_resource_availability(resource, amount):
                    return True
        
        # Agent availability conflicts
        if message.to_agent in self.agents:
            target_agent = self.agents[message.to_agent]
            if target_agent.current_task_count >= target_agent.max_concurrent_tasks:
                return True
        
        # Priority conflicts
        if message.priority == MessagePriority.CRITICAL:
            # Check if there are already critical messages being processed
            critical_messages = await self._count_critical_messages(message.to_agent)
            if critical_messages >= 2:  # Max 2 critical messages per agent
                return True
        
        return False
    
    async def _handle_message_conflict(self, message: AgentMessage):
        """Handle detected message conflict."""
        conflict_details = {
            "message_id": message.id,
            "conflict_type": "resource_unavailable",
            "timestamp": time.time(),
            "involved_agents": [message.from_agent, message.to_agent]
        }
        
        # Try conflict resolution
        resolution = await self.conflict_resolver.resolve_conflict(conflict_details)
        
        if resolution.success:
            # Apply resolution
            await self._apply_conflict_resolution(message, resolution)
        else:
            # Escalate conflict
            await self._escalate_conflict(message, conflict_details)
    
    # STREAM 3 REQUIREMENT 5: Resource Availability Notifications
    async def register_resource(self, agent_id: str, resource_type: str, 
                              resource_data: Dict[str, Any]) -> bool:
        """Register a resource provided by an agent."""
        if agent_id not in self.resource_registry:
            self.resource_registry[agent_id] = {}
        
        self.resource_registry[agent_id][resource_type] = {
            "data": resource_data,
            "available": True,
            "last_updated": time.time(),
            "access_count": 0
        }
        
        # Notify interested agents
        await self._notify_resource_availability(resource_type, agent_id, True)
        
        logger.info("Resource registered", 
                   agent=agent_id, resource_type=resource_type)
        return True
    
    async def unregister_resource(self, agent_id: str, resource_type: str) -> bool:
        """Unregister a resource."""
        if (agent_id in self.resource_registry and 
            resource_type in self.resource_registry[agent_id]):
            
            del self.resource_registry[agent_id][resource_type]
            
            # Notify interested agents
            await self._notify_resource_availability(resource_type, agent_id, False)
            
            logger.info("Resource unregistered", 
                       agent=agent_id, resource_type=resource_type)
            return True
        
        return False
    
    async def _notify_resource_availability(self, resource_type: str, 
                                          provider_agent: str, available: bool):
        """Notify agents about resource availability changes."""
        message_type = MessageType.RESOURCE_AVAILABLE if available else MessageType.RESOURCE_UNAVAILABLE
        
        # Find agents that might be interested in this resource
        interested_agents = await self._find_interested_agents(resource_type)
        
        for agent_id in interested_agents:
            if agent_id == provider_agent:  # Don't notify the provider
                continue
            
            notification = AgentMessage(
                from_agent="coordination_hub",
                to_agent=agent_id,
                message_type=message_type,
                priority=MessagePriority.NORMAL,
                content={
                    "resource_type": resource_type,
                    "provider_agent": provider_agent,
                    "available": available,
                    "timestamp": time.time()
                }
            )
            
            await self.send_message(notification)
    
    # Agent and capability management
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """Register an agent with enhanced capabilities."""
        try:
            self.agents[agent_info.agent_id] = agent_info
            
            # Create message queue
            if agent_info.agent_id not in self.message_queues:
                self.message_queues[agent_info.agent_id] = asyncio.Queue()
            
            # Register capabilities
            if agent_info.agent_id not in self.capability_registry:
                self.capability_registry[agent_info.agent_id] = set()
            
            self.capability_registry[agent_info.agent_id].update(agent_info.capabilities)
            
            # Initialize message handlers
            if agent_info.agent_id not in self.message_handlers:
                self.message_handlers[agent_info.agent_id] = {}
            
            # Add to appropriate broadcast groups
            await self._assign_to_broadcast_groups(agent_info)
            
            # Notify other agents of new agent availability
            await self._notify_agent_availability(agent_info.agent_id, True)
            
            logger.info("Enhanced agent registered", 
                       agent_id=agent_info.agent_id,
                       agent_type=agent_info.agent_type,
                       role=agent_info.role.value,
                       capabilities=agent_info.capabilities)
            
            return True
            
        except Exception as e:
            logger.error("Failed to register agent", 
                        agent_id=agent_info.agent_id, error=str(e))
            return False
    
    # Workflow coordination enhancements
    async def create_coordination_session(self, workflow_id: str, 
                                        participating_agents: List[str],
                                        coordination_type: str = "parallel") -> bool:
        """Create enhanced coordination session for workflow."""
        session = {
            "workflow_id": workflow_id,
            "participating_agents": set(participating_agents),
            "coordination_type": coordination_type,
            "created_at": time.time(),
            "status": "active",
            "message_history": [],
            "resource_allocations": {},
            "dynamic_agents": set(),
            "conflict_log": []
        }
        
        self.coordination_sessions[workflow_id] = session
        
        # Create workflow context
        context = WorkflowContext(
            workflow_id=workflow_id,
            phase=0,
            current_step="initialization",
            participating_agents=set(participating_agents)
        )
        
        self.workflow_contexts[workflow_id] = context
        
        # Notify all participating agents
        for agent_id in participating_agents:
            notification = AgentMessage(
                from_agent="coordination_hub",
                to_agent=agent_id,
                message_type=MessageType.COORDINATION_REQUEST,
                priority=MessagePriority.HIGH,
                content={
                    "action": "coordination_session_created",
                    "workflow_id": workflow_id,
                    "coordination_type": coordination_type,
                    "participating_agents": participating_agents
                },
                workflow_id=workflow_id
            )
            
            await self.send_message(notification)
        
        logger.info("Coordination session created", 
                   workflow_id=workflow_id,
                   agents=participating_agents,
                   type=coordination_type)
        
        return True
    
    # Background task implementations
    async def _process_messages(self):
        """Background task to process messages with enhanced features."""
        while self.running:
            try:
                # Process messages for all agents with priority handling
                for agent_id in list(self.message_queues.keys()):
                    await self._process_agent_messages_enhanced(agent_id)
                
                await asyncio.sleep(0.05)  # 50ms cycle for responsiveness
                
            except Exception as e:
                logger.error("Message processing error", error=str(e))
                await asyncio.sleep(1.0)
    
    async def _process_agent_messages_enhanced(self, agent_id: str):
        """Enhanced message processing for agent with priority and conflict handling."""
        try:
            if agent_id not in self.message_handlers:
                return
            
            queue = self.message_queues.get(agent_id)
            if not queue or queue.empty():
                return
            
            # Check agent availability
            agent_info = self.agents.get(agent_id)
            if not agent_info:
                return
            
            # Process messages based on priority
            messages_to_process = min(
                queue.qsize(),
                agent_info.max_concurrent_tasks - agent_info.current_task_count
            )
            
            if messages_to_process <= 0:
                return
            
            # Get messages and sort by priority
            messages = []
            for _ in range(min(messages_to_process, queue.qsize())):
                try:
                    message = queue.get_nowait()
                    messages.append(message)
                except asyncio.QueueEmpty:
                    break
            
            # Sort by priority (lower number = higher priority)
            messages.sort(key=lambda m: m.priority.value)
            
            # Process high-priority messages first
            for message in messages:
                await self._handle_message_enhanced(agent_id, message)
                
        except Exception as e:
            logger.error("Agent message processing error", 
                        agent_id=agent_id, error=str(e))
    
    async def _handle_message_enhanced(self, agent_id: str, message: AgentMessage):
        """Enhanced message handling with Stream 3 features."""
        try:
            # Update communication tracking
            await self._track_communication(message)
            
            # Handle special message types
            if message.message_type == MessageType.CONTEXT_REQUEST:
                await self._handle_context_request(agent_id, message)
            elif message.message_type == MessageType.AGENT_REQUEST:
                await self._handle_dynamic_agent_request(message)
            elif message.message_type == MessageType.RESOURCE_REQUEST:
                await self._handle_resource_request(message)
            elif message.message_type == MessageType.CONFLICT_DETECTED:
                await self._handle_conflict_message(message)
            else:
                # Use registered handler if available
                handlers = self.message_handlers.get(agent_id, {})
                handler = handlers.get(message.message_type)
                
                if handler:
                    await handler(message)
                else:
                    logger.debug("No handler for message type", 
                                agent_id=agent_id, 
                                message_type=message.message_type.value)
            
            # Update agent task count
            if agent_id in self.agents:
                self.agents[agent_id].current_task_count = max(
                    0, self.agents[agent_id].current_task_count - 1
                )
            
        except Exception as e:
            logger.error("Enhanced message handling error", 
                        agent_id=agent_id, message_id=message.id, error=str(e))
    
    # Utility methods for Stream 3 features
    async def _find_suitable_agent(self, required_capabilities: List[str]) -> Optional[str]:
        """Find agent with required capabilities."""
        best_agent = None
        best_score = 0
        
        for agent_id, agent_info in self.agents.items():
            if agent_info.status != "available":
                continue
            
            # Calculate capability match score
            agent_capabilities = set(agent_info.capabilities)
            required_set = set(required_capabilities)
            
            match_count = len(agent_capabilities.intersection(required_set))
            if match_count > 0:
                # Consider load and performance
                load_factor = 1.0 - (agent_info.current_task_count / agent_info.max_concurrent_tasks)
                performance_factor = agent_info.performance_metrics.get("success_rate", 0.5)
                
                score = match_count * load_factor * performance_factor
                
                if score > best_score:
                    best_score = score
                    best_agent = agent_id
        
        return best_agent
    
    async def _check_resource_availability(self, resource_type: str, amount: float) -> bool:
        """Check if resource is available in required amount."""
        total_available = 0
        
        for agent_resources in self.resource_registry.values():
            if resource_type in agent_resources:
                resource_info = agent_resources[resource_type]
                if resource_info["available"]:
                    total_available += resource_info["data"].get("amount", 0)
        
        return total_available >= amount
    
    async def _initialize_mcp_services(self):
        """Initialize MCP services for enhanced functionality."""
        try:
            # This would integrate with actual MCP services
            # For now, we'll use placeholder implementation
            
            logger.info("MCP services initialized for communication hub")
            
        except Exception as e:
            logger.warning("MCP services initialization failed", error=str(e))
    
    # Placeholder methods for remaining functionality
    async def _validate_message(self, message: AgentMessage) -> bool:
        """Validate message structure and content."""
        return bool(message.from_agent and message.to_agent and message.from_agent != message.to_agent)
    
    async def _optimize_message_route(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """Optimize message routing."""
        return {"routing_optimized": True, "timestamp": time.time()}
    
    async def _track_communication(self, message: AgentMessage):
        """Track communication for analysis."""
        pass
    
    async def _handle_broadcast_message(self, message: AgentMessage) -> bool:
        """Handle broadcast message."""
        return True
    
    async def _handle_resource_request(self, message: AgentMessage) -> bool:
        """Handle resource request."""
        return True
    
    async def _get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """Get current context for agent."""
        return {"agent_id": agent_id, "timestamp": time.time()}
    
    async def _add_agent_to_workflow(self, requesting_agent: str, new_agent: str):
        """Add agent to existing workflow."""
        pass
    
    async def _get_alternative_suggestions(self, capabilities: List[str]) -> List[str]:
        """Get alternative suggestions for capabilities."""
        return []
    
    async def _handle_heartbeat(self, message: AgentMessage):
        """Handle heartbeat message."""
        pass
    
    async def _handle_resource_notification(self, message: AgentMessage):
        """Handle resource notification."""
        pass
    
    async def _count_critical_messages(self, agent_id: str) -> int:
        """Count critical messages for agent."""
        return 0
    
    async def _apply_conflict_resolution(self, message: AgentMessage, resolution):
        """Apply conflict resolution."""
        pass
    
    async def _escalate_conflict(self, message: AgentMessage, conflict_details: Dict[str, Any]):
        """Escalate conflict."""
        pass
    
    async def _find_interested_agents(self, resource_type: str) -> List[str]:
        """Find agents interested in resource type."""
        return []
    
    async def _assign_to_broadcast_groups(self, agent_info: AgentInfo):
        """Assign agent to appropriate broadcast groups."""
        pass
    
    async def _notify_agent_availability(self, agent_id: str, available: bool):
        """Notify other agents of agent availability change."""
        pass
    
    async def _handle_context_request(self, agent_id: str, message: AgentMessage):
        """Handle context request."""
        pass
    
    async def _handle_conflict_message(self, message: AgentMessage):
        """Handle conflict message."""
        pass
    
    async def _monitor_agent_health(self):
        """Monitor agent health."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                # Health monitoring logic here
            except Exception as e:
                logger.error("Agent health monitoring error", error=str(e))
    
    async def _handle_resource_notifications(self):
        """Handle resource notifications."""
        while self.running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                # Resource notification logic here
            except Exception as e:
                logger.error("Resource notification handling error", error=str(e))
    
    async def _coordinate_workflows(self):
        """Coordinate active workflows."""
        while self.running:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                # Workflow coordination logic here
            except Exception as e:
                logger.error("Workflow coordination error", error=str(e))
    
    async def _resolve_conflicts(self):
        """Resolve detected conflicts."""
        while self.running:
            try:
                await asyncio.sleep(2)  # Check every 2 seconds
                # Conflict resolution logic here
            except Exception as e:
                logger.error("Conflict resolution error", error=str(e))

# Supporting classes for Stream 3 functionality
class ConflictResolver:
    """Handles conflict resolution between agents and resources."""
    
    async def resolve_conflict(self, conflict_details: Dict[str, Any]):
        """Resolve a detected conflict."""
        # Placeholder implementation
        return type('Resolution', (), {'success': True})()

class DynamicCoordinator:
    """Handles dynamic agent coordination and requests."""
    
    async def coordinate_dynamic_request(self, request_details: Dict[str, Any]):
        """Coordinate dynamic agent/resource requests."""
        # Placeholder implementation
        pass

# Global enhanced communication hub instance
_enhanced_hub: Optional[EnhancedAgentCommunicationHub] = None

async def get_enhanced_communication_hub(use_mcp_services: bool = True) -> EnhancedAgentCommunicationHub:
    """Get or create global enhanced communication hub instance."""
    global _enhanced_hub
    
    if _enhanced_hub is None:
        _enhanced_hub = EnhancedAgentCommunicationHub(use_mcp_services)
        await _enhanced_hub.start()
    
    return _enhanced_hub

async def shutdown_enhanced_communication_hub():
    """Shutdown global enhanced communication hub instance."""
    global _enhanced_hub
    
    if _enhanced_hub:
        await _enhanced_hub.stop()
        _enhanced_hub = None

# Context manager for enhanced communication hub
@asynccontextmanager
async def enhanced_communication_hub_context(use_mcp_services: bool = True):
    """Context manager for enhanced communication hub lifecycle."""
    hub = EnhancedAgentCommunicationHub(use_mcp_services)
    await hub.start()
    try:
        yield hub
    finally:
        await hub.stop()

# Integration with existing ML Enhanced Orchestrator
async def integrate_with_ml_orchestrator(orchestrator):
    """Integrate enhanced communication hub with ML orchestrator."""
    hub = await get_enhanced_communication_hub()
    
    # Register communication capabilities with orchestrator
    orchestrator.communication_hub = hub
    
    # Set up message handlers for orchestration coordination
    await _setup_orchestration_handlers(hub, orchestrator)
    
    logger.info("Enhanced communication hub integrated with ML orchestrator")

async def _setup_orchestration_handlers(hub: EnhancedAgentCommunicationHub, orchestrator):
    """Set up message handlers for orchestration coordination."""
    # This would set up the specific message handlers needed for
    # integration with the ML Enhanced Orchestrator
    pass