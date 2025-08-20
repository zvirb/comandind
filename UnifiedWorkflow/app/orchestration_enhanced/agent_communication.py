"""Agent Communication Protocol

Enables direct inter-agent communication with ML-enhanced routing,
context preservation, and intelligent coordination patterns.

Key Features:
- Direct agent-to-agent communication channels
- ML-enhanced message routing and priority management
- Context preservation across agent interactions
- Intelligent workflow coordination patterns
- Real-time collaboration and data sharing
- Conflict detection and resolution mechanisms
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Set, Callable, Union
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum
import json

import structlog
from prometheus_client import Counter, Histogram, Gauge

from .ml_service_bus import MLServiceBus, MLRequest, get_ml_service_bus

logger = structlog.get_logger(__name__)

# Metrics
AGENT_MESSAGES = Counter(
    'agent_communication_messages_total',
    'Total agent communication messages',
    ['from_agent', 'to_agent', 'message_type', 'status']
)
AGENT_MESSAGE_LATENCY = Histogram(
    'agent_communication_latency_seconds',
    'Agent message processing latency',
    ['message_type']
)
AGENT_WORKFLOW_COORDINATION = Counter(
    'agent_workflow_coordination_total',
    'Agent workflow coordination events',
    ['coordination_type', 'success']
)
ACTIVE_AGENT_SESSIONS = Gauge(
    'agent_communication_active_sessions',
    'Number of active agent communication sessions'
)

class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"           # Request for action or information
    RESPONSE = "response"         # Response to a request
    NOTIFICATION = "notification" # One-way notification
    COORDINATION = "coordination" # Workflow coordination message
    CONTEXT_SHARE = "context_share" # Context/data sharing
    ERROR = "error"              # Error notification
    HEARTBEAT = "heartbeat"      # Keep-alive message

class MessagePriority(Enum):
    """Message priority levels."""
    CRITICAL = 1    # Immediate processing required
    HIGH = 2        # High priority, process quickly
    NORMAL = 3      # Normal priority
    LOW = 4         # Low priority, process when convenient
    BACKGROUND = 5  # Background processing

class AgentRole(Enum):
    """Agent roles in orchestration hierarchy."""
    ORCHESTRATOR = "orchestrator"      # Top-level orchestration agents
    SPECIALIST = "specialist"          # Domain specialist agents
    VALIDATOR = "validator"            # Validation and quality agents
    COORDINATOR = "coordinator"        # Cross-domain coordination agents
    UTILITY = "utility"               # Utility and support agents

@dataclass
class AgentMessage:
    """Inter-agent communication message."""
    id: str = field(default_factory=lambda: str(uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    message_type: MessageType = MessageType.REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    content: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    workflow_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentInfo:
    """Information about an agent in the communication system."""
    agent_id: str
    agent_type: str
    role: AgentRole
    capabilities: List[str]
    specializations: List[str]
    max_concurrent_tasks: int = 3
    current_task_count: int = 0
    status: str = "available"  # available, busy, offline
    last_seen: float = field(default_factory=time.time)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    communication_preferences: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowContext:
    """Shared context for workflow coordination."""
    workflow_id: str
    phase: int
    current_step: str
    participating_agents: Set[str]
    shared_data: Dict[str, Any] = field(default_factory=dict)
    coordination_state: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    completion_status: Dict[str, bool] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

class AgentCommunicationHub:
    """Central hub for agent-to-agent communication and coordination."""
    
    def __init__(self, ml_service_bus: Optional[MLServiceBus] = None):
        """Initialize the communication hub."""
        self.ml_service_bus = ml_service_bus
        self.agents: Dict[str, AgentInfo] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = {}
        self.workflow_contexts: Dict[str, WorkflowContext] = {}
        self.routing_rules: Dict[str, List[str]] = {}
        self.running = False
        
        # Message processing
        self._message_processor_task: Optional[asyncio.Task] = None
        self._coordination_monitor_task: Optional[asyncio.Task] = None
        
        # ML-enhanced features
        self._enable_ml_routing = True
        self._enable_ml_prioritization = True
        self._enable_conflict_detection = True
        
        logger.info("Agent Communication Hub initialized")
    
    async def start(self):
        """Start the communication hub."""
        if self.ml_service_bus is None:
            self.ml_service_bus = await get_ml_service_bus()
        
        self.running = True
        
        # Start background tasks
        self._message_processor_task = asyncio.create_task(self._process_messages())
        self._coordination_monitor_task = asyncio.create_task(self._monitor_coordination())
        
        logger.info("Agent Communication Hub started")
    
    async def stop(self):
        """Stop the communication hub."""
        self.running = False
        
        # Cancel background tasks
        if self._message_processor_task:
            self._message_processor_task.cancel()
        if self._coordination_monitor_task:
            self._coordination_monitor_task.cancel()
        
        # Wait for tasks to complete
        tasks = [
            task for task in [self._message_processor_task, self._coordination_monitor_task]
            if task and not task.done()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Agent Communication Hub stopped")
    
    def register_agent(self, agent_info: AgentInfo) -> bool:
        """Register an agent with the communication hub."""
        try:
            self.agents[agent_info.agent_id] = agent_info
            
            # Create message queue for agent
            if agent_info.agent_id not in self.message_queues:
                self.message_queues[agent_info.agent_id] = asyncio.Queue()
            
            # Initialize message handlers
            if agent_info.agent_id not in self.message_handlers:
                self.message_handlers[agent_info.agent_id] = {}
            
            # Update metrics
            ACTIVE_AGENT_SESSIONS.inc()
            
            logger.info("Agent registered", 
                       agent_id=agent_info.agent_id,
                       agent_type=agent_info.agent_type,
                       role=agent_info.role.value,
                       capabilities=agent_info.capabilities)
            
            return True
            
        except Exception as e:
            logger.error("Failed to register agent", 
                        agent_id=agent_info.agent_id, error=str(e))
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the communication hub."""
        try:
            if agent_id in self.agents:
                del self.agents[agent_id]
            
            if agent_id in self.message_queues:
                del self.message_queues[agent_id]
            
            if agent_id in self.message_handlers:
                del self.message_handlers[agent_id]
            
            # Update metrics
            ACTIVE_AGENT_SESSIONS.dec()
            
            logger.info("Agent unregistered", agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error("Failed to unregister agent", 
                        agent_id=agent_id, error=str(e))
            return False
    
    def register_message_handler(self, agent_id: str, message_type: MessageType, 
                                handler: Callable[[AgentMessage], Any]):
        """Register a message handler for an agent."""
        if agent_id not in self.message_handlers:
            self.message_handlers[agent_id] = {}
        
        self.message_handlers[agent_id][message_type] = handler
        
        logger.debug("Message handler registered", 
                    agent_id=agent_id, message_type=message_type.value)
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message between agents."""
        start_time = time.time()
        
        try:
            # Validate message
            if not self._validate_message(message):
                AGENT_MESSAGES.labels(
                    from_agent=message.from_agent,
                    to_agent=message.to_agent,
                    message_type=message.message_type.value,
                    status='validation_error'
                ).inc()
                return False
            
            # ML-enhanced routing optimization
            if self._enable_ml_routing:
                await self._optimize_message_routing(message)
            
            # Check if target agent exists
            if message.to_agent not in self.agents:
                logger.warning("Target agent not found", 
                              to_agent=message.to_agent, message_id=message.id)
                AGENT_MESSAGES.labels(
                    from_agent=message.from_agent,
                    to_agent=message.to_agent,
                    message_type=message.message_type.value,
                    status='agent_not_found'
                ).inc()
                return False
            
            # Check agent capacity
            target_agent = self.agents[message.to_agent]
            if target_agent.current_task_count >= target_agent.max_concurrent_tasks:
                # Queue message for later processing
                logger.info("Agent at capacity, queueing message", 
                           to_agent=message.to_agent, message_id=message.id)
            
            # Add to message queue
            queue = self.message_queues[message.to_agent]
            await queue.put(message)
            
            # Update metrics
            AGENT_MESSAGES.labels(
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                message_type=message.message_type.value,
                status='sent'
            ).inc()
            
            latency = time.time() - start_time
            AGENT_MESSAGE_LATENCY.labels(
                message_type=message.message_type.value
            ).observe(latency)
            
            logger.info("Message sent", 
                       from_agent=message.from_agent,
                       to_agent=message.to_agent,
                       message_id=message.id,
                       message_type=message.message_type.value)
            
            return True
            
        except Exception as e:
            logger.error("Failed to send message", 
                        message_id=message.id, error=str(e))
            AGENT_MESSAGES.labels(
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                message_type=message.message_type.value,
                status='error'
            ).inc()
            return False
    
    async def receive_message(self, agent_id: str, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Receive a message for an agent."""
        try:
            if agent_id not in self.message_queues:
                return None
            
            queue = self.message_queues[agent_id]
            
            try:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
                
                # Update agent status
                if agent_id in self.agents:
                    self.agents[agent_id].last_seen = time.time()
                    self.agents[agent_id].current_task_count += 1
                
                logger.debug("Message received", 
                            agent_id=agent_id, message_id=message.id)
                
                return message
                
            except asyncio.TimeoutError:
                return None
                
        except Exception as e:
            logger.error("Failed to receive message", 
                        agent_id=agent_id, error=str(e))
            return None
    
    async def broadcast_message(self, message: AgentMessage, 
                              target_roles: Optional[List[AgentRole]] = None,
                              exclude_agents: Optional[List[str]] = None) -> int:
        """Broadcast a message to multiple agents."""
        exclude_agents = exclude_agents or []
        sent_count = 0
        
        for agent_id, agent_info in self.agents.items():
            # Skip excluded agents
            if agent_id in exclude_agents:
                continue
            
            # Filter by role if specified
            if target_roles and agent_info.role not in target_roles:
                continue
            
            # Create individual message
            agent_message = AgentMessage(
                from_agent=message.from_agent,
                to_agent=agent_id,
                message_type=message.message_type,
                priority=message.priority,
                content=message.content.copy(),
                context=message.context.copy(),
                workflow_id=message.workflow_id,
                metadata=message.metadata.copy()
            )
            
            if await self.send_message(agent_message):
                sent_count += 1
        
        logger.info("Message broadcasted", 
                   from_agent=message.from_agent,
                   target_roles=[r.value for r in target_roles] if target_roles else "all",
                   sent_count=sent_count)
        
        return sent_count
    
    async def create_workflow_context(self, workflow_id: str, 
                                    participating_agents: List[str],
                                    initial_data: Dict[str, Any] = None) -> WorkflowContext:
        """Create a shared workflow context for agent coordination."""
        context = WorkflowContext(
            workflow_id=workflow_id,
            phase=0,
            current_step="initialization",
            participating_agents=set(participating_agents),
            shared_data=initial_data or {},
            coordination_state={},
            dependencies={},
            completion_status={agent: False for agent in participating_agents}
        )
        
        self.workflow_contexts[workflow_id] = context
        
        # Notify participating agents
        notification = AgentMessage(
            from_agent="communication_hub",
            message_type=MessageType.COORDINATION,
            priority=MessagePriority.HIGH,
            content={
                "action": "workflow_created",
                "workflow_id": workflow_id,
                "participating_agents": participating_agents
            },
            workflow_id=workflow_id
        )
        
        await self.broadcast_message(
            notification,
            exclude_agents=["communication_hub"]
        )
        
        logger.info("Workflow context created", 
                   workflow_id=workflow_id,
                   participating_agents=participating_agents)
        
        return context
    
    async def update_workflow_context(self, workflow_id: str, 
                                    updates: Dict[str, Any],
                                    agent_id: str) -> bool:
        """Update shared workflow context."""
        try:
            if workflow_id not in self.workflow_contexts:
                logger.warning("Workflow context not found", workflow_id=workflow_id)
                return False
            
            context = self.workflow_contexts[workflow_id]
            
            # Apply updates
            for key, value in updates.items():
                if key == "shared_data":
                    context.shared_data.update(value)
                elif key == "coordination_state":
                    context.coordination_state.update(value)
                elif key == "completion_status":
                    context.completion_status.update(value)
                elif key == "phase":
                    context.phase = value
                elif key == "current_step":
                    context.current_step = value
            
            context.updated_at = time.time()
            
            # Check for conflicts using ML
            if self._enable_conflict_detection:
                await self._detect_workflow_conflicts(context, agent_id)
            
            # Notify other participating agents
            notification = AgentMessage(
                from_agent=agent_id,
                message_type=MessageType.COORDINATION,
                priority=MessagePriority.NORMAL,
                content={
                    "action": "context_updated",
                    "workflow_id": workflow_id,
                    "updates": updates
                },
                workflow_id=workflow_id
            )
            
            await self.broadcast_message(
                notification,
                exclude_agents=[agent_id, "communication_hub"]
            )
            
            AGENT_WORKFLOW_COORDINATION.labels(
                coordination_type="context_update",
                success="true"
            ).inc()
            
            logger.info("Workflow context updated", 
                       workflow_id=workflow_id, agent_id=agent_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to update workflow context", 
                        workflow_id=workflow_id, error=str(e))
            AGENT_WORKFLOW_COORDINATION.labels(
                coordination_type="context_update",
                success="false"
            ).inc()
            return False
    
    def _validate_message(self, message: AgentMessage) -> bool:
        """Validate message before sending."""
        if not message.from_agent or not message.to_agent:
            logger.warning("Message missing from_agent or to_agent", message_id=message.id)
            return False
        
        if message.from_agent == message.to_agent:
            logger.warning("Agent trying to send message to itself", 
                          agent_id=message.from_agent, message_id=message.id)
            return False
        
        # Check message expiration
        if message.expires_at and time.time() > message.expires_at:
            logger.warning("Message expired", message_id=message.id)
            return False
        
        return True
    
    async def _optimize_message_routing(self, message: AgentMessage):
        """Use ML to optimize message routing."""
        try:
            # Query reasoning service for routing optimization
            ml_request = MLRequest(
                service="reasoning",
                endpoint="decide/multi-criteria",
                data={
                    "options": [message.to_agent],  # For now, single option
                    "criteria": [
                        {"name": "agent_availability", "weight": 0.4},
                        {"name": "agent_specialization", "weight": 0.3},
                        {"name": "current_load", "weight": 0.3}
                    ],
                    "context": {
                        "message_type": message.message_type.value,
                        "priority": message.priority.value,
                        "content_summary": str(message.content)[:200]
                    }
                }
            )
            
            response = await self.ml_service_bus.request(ml_request)
            
            if response.success and response.confidence_score and response.confidence_score > 0.7:
                # Apply ML recommendations
                if "routing_suggestions" in response.data:
                    message.metadata["ml_routing_applied"] = True
                    message.metadata["ml_confidence"] = response.confidence_score
                    
        except Exception as e:
            logger.debug("ML routing optimization failed", error=str(e))
    
    async def _detect_workflow_conflicts(self, context: WorkflowContext, agent_id: str):
        """Use ML to detect potential workflow conflicts."""
        try:
            # Query reasoning service for conflict detection
            ml_request = MLRequest(
                service="reasoning",
                endpoint="validate/evidence",
                data={
                    "evidence": [
                        {
                            "source": "workflow_state",
                            "content": json.dumps(context.coordination_state),
                            "type": "state_data"
                        },
                        {
                            "source": "completion_status",
                            "content": json.dumps(context.completion_status),
                            "type": "completion_data"
                        }
                    ],
                    "validation_criteria": [
                        "consistency_check",
                        "dependency_validation",
                        "resource_conflict_detection"
                    ]
                }
            )
            
            response = await self.ml_service_bus.request(ml_request)
            
            if response.success and not response.data.get("meets_threshold", True):
                # Conflict detected
                logger.warning("Workflow conflict detected", 
                              workflow_id=context.workflow_id,
                              agent_id=agent_id,
                              conflict_details=response.data)
                
                # Notify workflow coordinator
                conflict_message = AgentMessage(
                    from_agent="communication_hub",
                    to_agent="orchestration-auditor-v2",
                    message_type=MessageType.ERROR,
                    priority=MessagePriority.CRITICAL,
                    content={
                        "conflict_type": "workflow_conflict",
                        "workflow_id": context.workflow_id,
                        "conflicting_agent": agent_id,
                        "conflict_details": response.data
                    }
                )
                
                await self.send_message(conflict_message)
                
        except Exception as e:
            logger.debug("Conflict detection failed", error=str(e))
    
    async def _process_messages(self):
        """Background task to process messages."""
        while self.running:
            try:
                # Process messages for all agents
                for agent_id in list(self.message_queues.keys()):
                    await self._process_agent_messages(agent_id)
                
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error("Message processing error", error=str(e))
                await asyncio.sleep(1.0)
    
    async def _process_agent_messages(self, agent_id: str):
        """Process messages for a specific agent."""
        try:
            if agent_id not in self.message_handlers:
                return
            
            queue = self.message_queues.get(agent_id)
            if not queue or queue.empty():
                return
            
            # Check agent availability
            agent_info = self.agents.get(agent_id)
            if not agent_info or agent_info.status != "available":
                return
            
            # Process up to max concurrent tasks
            messages_to_process = min(
                queue.qsize(),
                agent_info.max_concurrent_tasks - agent_info.current_task_count
            )
            
            for _ in range(messages_to_process):
                try:
                    message = queue.get_nowait()
                    await self._handle_message(agent_id, message)
                except asyncio.QueueEmpty:
                    break
                    
        except Exception as e:
            logger.error("Agent message processing error", 
                        agent_id=agent_id, error=str(e))
    
    async def _handle_message(self, agent_id: str, message: AgentMessage):
        """Handle a specific message for an agent."""
        try:
            handlers = self.message_handlers.get(agent_id, {})
            handler = handlers.get(message.message_type)
            
            if handler:
                # Execute handler
                result = await handler(message)
                
                # Update agent task count
                if agent_id in self.agents:
                    self.agents[agent_id].current_task_count = max(
                        0, self.agents[agent_id].current_task_count - 1
                    )
                
                logger.debug("Message handled", 
                            agent_id=agent_id, message_id=message.id)
            else:
                logger.warning("No handler found for message type", 
                              agent_id=agent_id, 
                              message_type=message.message_type.value)
                
        except Exception as e:
            logger.error("Message handling error", 
                        agent_id=agent_id, message_id=message.id, error=str(e))
    
    async def _monitor_coordination(self):
        """Monitor workflow coordination status."""
        while self.running:
            try:
                # Check workflow completion status
                for workflow_id, context in list(self.workflow_contexts.items()):
                    await self._check_workflow_completion(workflow_id, context)
                
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.error("Coordination monitoring error", error=str(e))
                await asyncio.sleep(10.0)
    
    async def _check_workflow_completion(self, workflow_id: str, context: WorkflowContext):
        """Check if workflow is complete and handle completion."""
        try:
            all_complete = all(context.completion_status.values())
            
            if all_complete:
                # Workflow is complete
                completion_message = AgentMessage(
                    from_agent="communication_hub",
                    message_type=MessageType.COORDINATION,
                    priority=MessagePriority.HIGH,
                    content={
                        "action": "workflow_completed",
                        "workflow_id": workflow_id,
                        "completion_time": time.time(),
                        "final_context": context.shared_data
                    },
                    workflow_id=workflow_id
                )
                
                await self.broadcast_message(
                    completion_message,
                    exclude_agents=["communication_hub"]
                )
                
                # Clean up workflow context
                del self.workflow_contexts[workflow_id]
                
                AGENT_WORKFLOW_COORDINATION.labels(
                    coordination_type="workflow_completion",
                    success="true"
                ).inc()
                
                logger.info("Workflow completed", workflow_id=workflow_id)
                
        except Exception as e:
            logger.error("Workflow completion check failed", 
                        workflow_id=workflow_id, error=str(e))

# Global communication hub instance
_communication_hub: Optional[AgentCommunicationHub] = None

async def get_communication_hub(ml_service_bus: Optional[MLServiceBus] = None) -> AgentCommunicationHub:
    """Get or create global communication hub instance."""
    global _communication_hub
    
    if _communication_hub is None:
        _communication_hub = AgentCommunicationHub(ml_service_bus)
        await _communication_hub.start()
    
    return _communication_hub

async def shutdown_communication_hub():
    """Shutdown global communication hub instance."""
    global _communication_hub
    
    if _communication_hub:
        await _communication_hub.stop()
        _communication_hub = None

# Context manager for communication hub
@asynccontextmanager
async def communication_hub_context(ml_service_bus: Optional[MLServiceBus] = None):
    """Context manager for communication hub lifecycle."""
    hub = AgentCommunicationHub(ml_service_bus)
    await hub.start()
    try:
        yield hub
    finally:
        await hub.stop()