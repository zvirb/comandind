"""Standardized Inter-Agent Communication Protocols.

This module provides standardized communication protocols for efficient
inter-agent coordination with metadata tracking and handoff procedures.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger(__name__)

# Metrics
message_counter = Counter(
    'agent_messages_total',
    'Total agent communication messages',
    ['message_type', 'protocol', 'status']
)

message_latency = Histogram(
    'agent_message_latency_seconds',
    'Message delivery latency',
    ['protocol', 'priority']
)

handoff_duration = Histogram(
    'agent_handoff_duration_seconds',
    'Task handoff duration between agents',
    ['from_agent', 'to_agent']
)


class MessageType(str, Enum):
    """Types of inter-agent messages."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_GRANT = "resource_grant"
    COORDINATION_SYNC = "coordination_sync"
    HANDOFF_INITIATE = "handoff_initiate"
    HANDOFF_ACKNOWLEDGE = "handoff_acknowledge"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ERROR_REPORT = "error_report"


class MessagePriority(str, Enum):
    """Message priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class DeliveryMode(str, Enum):
    """Message delivery modes."""
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    FIRE_AND_FORGET = "fire_and_forget"
    GUARANTEED = "guaranteed"


@dataclass
class MessageMetadata:
    """Metadata for tracking message flow and coordination."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    sender_agent: str = ""
    recipient_agents: List[str] = field(default_factory=list)
    message_type: MessageType = MessageType.TASK_REQUEST
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.ASYNCHRONOUS
    ttl_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    requires_acknowledgment: bool = False
    tracking_enabled: bool = True
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.timestamp > self.ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class AgentMessage:
    """Standardized agent communication message."""
    metadata: MessageMetadata
    payload: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transmission."""
        return {
            "metadata": self.metadata.to_dict(),
            "payload": self.payload,
            "context": self.context,
            "attachments": self.attachments
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create from dictionary."""
        metadata = MessageMetadata(**data["metadata"])
        return cls(
            metadata=metadata,
            payload=data["payload"],
            context=data.get("context", {}),
            attachments=data.get("attachments", [])
        )


@dataclass
class HandoffContext:
    """Context for agent task handoffs."""
    handoff_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    task_id: str = ""
    task_state: Dict[str, Any] = field(default_factory=dict)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    resource_transfer: Dict[str, Any] = field(default_factory=dict)
    handoff_reason: str = ""
    priority: MessagePriority = MessagePriority.NORMAL
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def complete(self) -> None:
        """Mark handoff as completed."""
        self.completed_at = time.time()
    
    def duration(self) -> Optional[float]:
        """Get handoff duration."""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None


class CommunicationProtocol:
    """Manages standardized inter-agent communication protocols."""
    
    def __init__(
        self,
        agent_id: str,
        message_buffer_size: int = 1000,
        enable_tracking: bool = True
    ):
        self.agent_id = agent_id
        self.message_buffer_size = message_buffer_size
        self.enable_tracking = enable_tracking
        
        # Message handling
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.message_buffer: List[AgentMessage] = []
        self.pending_acknowledgments: Dict[str, AgentMessage] = {}
        
        # Handoff management
        self.active_handoffs: Dict[str, HandoffContext] = {}
        self.handoff_history: List[HandoffContext] = []
        
        # Communication channels
        self.channels: Dict[str, asyncio.Queue] = {}
        self.broadcast_channel: Optional[asyncio.Queue] = None
        
        # Performance tracking
        self.message_stats = {
            "sent": 0,
            "received": 0,
            "acknowledged": 0,
            "failed": 0,
            "expired": 0
        }
        
        self._running = False
        self._message_processor_task = None
    
    async def initialize(self) -> None:
        """Initialize communication protocol."""
        logger.info(f"Initializing communication protocol for agent: {self.agent_id}")
        
        # Create broadcast channel
        self.broadcast_channel = asyncio.Queue(maxsize=self.message_buffer_size)
        
        # Start message processor
        self._running = True
        self._message_processor_task = asyncio.create_task(self._process_messages())
        
        logger.info(f"Communication protocol initialized for agent: {self.agent_id}")
    
    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[AgentMessage], Any]
    ) -> None:
        """Register a message handler for specific message type."""
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type} on agent {self.agent_id}")
    
    async def send_message(
        self,
        recipient_agents: Union[str, List[str]],
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        delivery_mode: DeliveryMode = DeliveryMode.ASYNCHRONOUS,
        context: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
        requires_acknowledgment: bool = False
    ) -> Optional[str]:
        """Send a standardized message to recipient agents."""
        # Ensure recipients is a list
        if isinstance(recipient_agents, str):
            recipient_agents = [recipient_agents]
        
        # Create message metadata
        metadata = MessageMetadata(
            sender_agent=self.agent_id,
            recipient_agents=recipient_agents,
            message_type=message_type,
            priority=priority,
            delivery_mode=delivery_mode,
            ttl_seconds=ttl_seconds,
            requires_acknowledgment=requires_acknowledgment,
            tracking_enabled=self.enable_tracking
        )
        
        # Create message
        message = AgentMessage(
            metadata=metadata,
            payload=payload,
            context=context or {}
        )
        
        # Track message
        if self.enable_tracking:
            with message_latency.labels(
                protocol=delivery_mode,
                priority=priority
            ).time():
                await self._send_message_internal(message)
        else:
            await self._send_message_internal(message)
        
        # Update stats
        self.message_stats["sent"] += 1
        
        message_counter.labels(
            message_type=message_type,
            protocol=delivery_mode,
            status="sent"
        ).inc()
        
        logger.debug(
            f"Message sent from {self.agent_id}",
            message_id=metadata.message_id,
            recipients=recipient_agents,
            type=message_type
        )
        
        return metadata.message_id
    
    async def initiate_handoff(
        self,
        to_agent: str,
        task_id: str,
        task_state: Dict[str, Any],
        intermediate_results: Optional[Dict[str, Any]] = None,
        resource_transfer: Optional[Dict[str, Any]] = None,
        reason: str = "task_completion",
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """Initiate a task handoff to another agent."""
        handoff_context = HandoffContext(
            from_agent=self.agent_id,
            to_agent=to_agent,
            task_id=task_id,
            task_state=task_state,
            intermediate_results=intermediate_results or {},
            resource_transfer=resource_transfer or {},
            handoff_reason=reason,
            priority=priority
        )
        
        # Store handoff context
        self.active_handoffs[handoff_context.handoff_id] = handoff_context
        
        # Send handoff initiation message
        await self.send_message(
            recipient_agents=to_agent,
            message_type=MessageType.HANDOFF_INITIATE,
            payload={
                "handoff_id": handoff_context.handoff_id,
                "task_id": task_id,
                "task_state": task_state,
                "intermediate_results": intermediate_results,
                "resource_transfer": resource_transfer,
                "reason": reason
            },
            priority=priority,
            requires_acknowledgment=True,
            context={"handoff_context": handoff_context.handoff_id}
        )
        
        logger.info(
            f"Handoff initiated from {self.agent_id} to {to_agent}",
            handoff_id=handoff_context.handoff_id,
            task_id=task_id
        )
        
        return handoff_context.handoff_id
    
    async def acknowledge_handoff(
        self,
        handoff_id: str,
        accepted: bool,
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Acknowledge a handoff request."""
        # Send acknowledgment message
        await self.send_message(
            recipient_agents="*",  # Broadcast to notify all interested agents
            message_type=MessageType.HANDOFF_ACKNOWLEDGE,
            payload={
                "handoff_id": handoff_id,
                "accepted": accepted,
                "acknowledging_agent": self.agent_id,
                "response_data": response_data or {}
            },
            priority=MessagePriority.HIGH
        )
        
        logger.info(
            f"Handoff acknowledged by {self.agent_id}",
            handoff_id=handoff_id,
            accepted=accepted
        )
    
    async def broadcast(
        self,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Broadcast a message to all agents."""
        await self.send_message(
            recipient_agents="*",  # Special indicator for broadcast
            message_type=MessageType.BROADCAST,
            payload={
                "original_type": message_type,
                "broadcast_payload": payload
            },
            priority=priority,
            context=context
        )
        
        logger.debug(f"Broadcast sent from {self.agent_id}", type=message_type)
    
    async def send_status_update(
        self,
        task_id: str,
        status: str,
        progress: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send a status update for a task."""
        await self.broadcast(
            message_type=MessageType.STATUS_UPDATE,
            payload={
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "details": details or {},
                "timestamp": time.time()
            },
            priority=MessagePriority.LOW
        )
    
    async def request_resources(
        self,
        resource_type: str,
        amount: float,
        purpose: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """Request resources from resource manager."""
        request_id = str(uuid.uuid4())
        
        await self.send_message(
            recipient_agents="resource_manager",  # Special recipient
            message_type=MessageType.RESOURCE_REQUEST,
            payload={
                "request_id": request_id,
                "resource_type": resource_type,
                "amount": amount,
                "purpose": purpose,
                "requesting_agent": self.agent_id
            },
            priority=priority,
            requires_acknowledgment=True
        )
        
        return request_id
    
    async def get_handoff_status(self, handoff_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a handoff operation."""
        if handoff_id in self.active_handoffs:
            handoff = self.active_handoffs[handoff_id]
            return {
                "handoff_id": handoff_id,
                "status": "active",
                "from_agent": handoff.from_agent,
                "to_agent": handoff.to_agent,
                "task_id": handoff.task_id,
                "started_at": handoff.started_at,
                "duration": time.time() - handoff.started_at
            }
        
        # Check history
        for handoff in self.handoff_history:
            if handoff.handoff_id == handoff_id:
                return {
                    "handoff_id": handoff_id,
                    "status": "completed",
                    "from_agent": handoff.from_agent,
                    "to_agent": handoff.to_agent,
                    "task_id": handoff.task_id,
                    "started_at": handoff.started_at,
                    "completed_at": handoff.completed_at,
                    "duration": handoff.duration()
                }
        
        return None
    
    async def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            "agent_id": self.agent_id,
            "message_stats": self.message_stats,
            "active_handoffs": len(self.active_handoffs),
            "completed_handoffs": len(self.handoff_history),
            "pending_acknowledgments": len(self.pending_acknowledgments),
            "buffered_messages": len(self.message_buffer),
            "registered_handlers": {
                msg_type: len(handlers)
                for msg_type, handlers in self.message_handlers.items()
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown communication protocol."""
        logger.info(f"Shutting down communication protocol for agent: {self.agent_id}")
        
        self._running = False
        
        if self._message_processor_task:
            self._message_processor_task.cancel()
            try:
                await self._message_processor_task
            except asyncio.CancelledError:
                pass
        
        # Complete any active handoffs
        for handoff in self.active_handoffs.values():
            handoff.complete()
            self.handoff_history.append(handoff)
        
        self.active_handoffs.clear()
        
        logger.info(f"Communication protocol shutdown for agent: {self.agent_id}")
    
    # Private helper methods
    
    async def _send_message_internal(self, message: AgentMessage) -> None:
        """Internal message sending logic."""
        # Add to buffer if tracking enabled
        if self.enable_tracking:
            self.message_buffer.append(message)
            if len(self.message_buffer) > self.message_buffer_size:
                self.message_buffer.pop(0)
        
        # Handle acknowledgment tracking
        if message.metadata.requires_acknowledgment:
            self.pending_acknowledgments[message.metadata.message_id] = message
        
        # Route message based on delivery mode
        if message.metadata.delivery_mode == DeliveryMode.SYNCHRONOUS:
            await self._send_synchronous(message)
        elif message.metadata.delivery_mode == DeliveryMode.GUARANTEED:
            await self._send_guaranteed(message)
        else:
            await self._send_asynchronous(message)
    
    async def _send_synchronous(self, message: AgentMessage) -> None:
        """Send message synchronously."""
        # Implementation depends on actual transport mechanism
        # This is a placeholder for the pattern
        for recipient in message.metadata.recipient_agents:
            # Wait for delivery confirmation
            pass
    
    async def _send_asynchronous(self, message: AgentMessage) -> None:
        """Send message asynchronously."""
        # Implementation depends on actual transport mechanism
        # This is a placeholder for the pattern
        for recipient in message.metadata.recipient_agents:
            # Send without waiting
            pass
    
    async def _send_guaranteed(self, message: AgentMessage) -> None:
        """Send message with guaranteed delivery."""
        # Implement retry logic
        for attempt in range(message.metadata.max_retries):
            try:
                await self._send_asynchronous(message)
                break
            except Exception as e:
                message.metadata.retry_count += 1
                if attempt == message.metadata.max_retries - 1:
                    self.message_stats["failed"] += 1
                    logger.error(
                        f"Failed to deliver message after {message.metadata.max_retries} attempts",
                        message_id=message.metadata.message_id,
                        error=str(e)
                    )
                else:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _process_messages(self) -> None:
        """Background task to process incoming messages."""
        logger.info(f"Message processor started for agent: {self.agent_id}")
        
        while self._running:
            try:
                # Check for expired messages
                await self._cleanup_expired_messages()
                
                # Process pending acknowledgments
                await self._check_acknowledgments()
                
                # Sleep briefly
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
    
    async def _cleanup_expired_messages(self) -> None:
        """Clean up expired messages."""
        expired_ids = []
        
        for msg_id, message in self.pending_acknowledgments.items():
            if message.metadata.is_expired():
                expired_ids.append(msg_id)
                self.message_stats["expired"] += 1
        
        for msg_id in expired_ids:
            del self.pending_acknowledgments[msg_id]
            logger.debug(f"Message expired: {msg_id}")
    
    async def _check_acknowledgments(self) -> None:
        """Check for pending acknowledgments."""
        # Implementation depends on actual acknowledgment mechanism
        pass
    
    async def _handle_incoming_message(self, message: AgentMessage) -> None:
        """Handle an incoming message."""
        self.message_stats["received"] += 1
        
        message_counter.labels(
            message_type=message.metadata.message_type,
            protocol=message.metadata.delivery_mode,
            status="received"
        ).inc()
        
        # Route to appropriate handlers
        handlers = self.message_handlers.get(message.metadata.message_type, [])
        
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(
                    f"Error in message handler",
                    message_id=message.metadata.message_id,
                    error=str(e)
                )
        
        # Send acknowledgment if required
        if message.metadata.requires_acknowledgment:
            await self._send_acknowledgment(message.metadata.message_id)
    
    async def _send_acknowledgment(self, message_id: str) -> None:
        """Send acknowledgment for a message."""
        # Implementation depends on actual transport mechanism
        self.message_stats["acknowledged"] += 1