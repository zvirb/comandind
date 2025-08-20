# Agent Communication Protocol Specification

## Overview

This document defines the comprehensive communication protocol that enables direct inter-agent communication while preventing recursion loops and maintaining system stability. The protocol integrates with ML services for intelligent routing and coordination.

## Communication Architecture

### 1. Communication Layer Stack

```
┌─────────────────────────────────────────────┐
│              Application Layer              │
│  Agent Tasks, Workflows, User Interactions  │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│            Message Protocol Layer           │
│  Message Types, Serialization, Validation   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           Smart Routing Layer               │
│  ML-Driven Routing, Recursion Prevention    │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           Transport Layer                   │
│  WebSocket, HTTP, Message Queue             │
└─────────────────────────────────────────────┘
```

### 2. Core Components

**Message Router**: ML-enhanced routing with recursion prevention
**Communication Graph**: Real-time tracking of agent interactions
**Context Manager**: Shared context spaces for collaboration
**Conflict Resolver**: Resource and priority conflict resolution
**Performance Monitor**: Communication performance optimization

## Message Protocol

### 1. Message Structure

```python
@dataclass
class AgentMessage:
    message_id: str
    sender_agent: str
    recipient_agent: str
    message_type: MessageType
    priority: Priority
    payload: Dict[str, Any]
    context_reference: Optional[str]
    requires_response: bool
    timeout_seconds: int
    created_at: datetime
    routing_metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "sender_agent": self.sender_agent,
            "recipient_agent": self.recipient_agent,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "payload": self.payload,
            "context_reference": self.context_reference,
            "requires_response": self.requires_response,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "routing_metadata": self.routing_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentMessage':
        return cls(
            message_id=data["message_id"],
            sender_agent=data["sender_agent"],
            recipient_agent=data["recipient_agent"],
            message_type=MessageType(data["message_type"]),
            priority=Priority(data["priority"]),
            payload=data["payload"],
            context_reference=data.get("context_reference"),
            requires_response=data["requires_response"],
            timeout_seconds=data["timeout_seconds"],
            created_at=datetime.fromisoformat(data["created_at"]),
            routing_metadata=data["routing_metadata"]
        )

class MessageType(Enum):
    CONTEXT_REQUEST = "context_request"
    CONTEXT_RESPONSE = "context_response"
    COLLABORATION_PROPOSAL = "collaboration_proposal"
    COLLABORATION_RESPONSE = "collaboration_response"
    TASK_DELEGATION = "task_delegation"
    TASK_RESULT = "task_result"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_RESPONSE = "resource_response"
    STATUS_UPDATE = "status_update"
    ERROR_NOTIFICATION = "error_notification"
    COORDINATION_REQUEST = "coordination_request"
    COORDINATION_RESPONSE = "coordination_response"

class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"
```

### 2. Message Validation

```python
class MessageValidator:
    def __init__(self):
        self.validation_rules = {
            MessageType.CONTEXT_REQUEST: self.validate_context_request,
            MessageType.COLLABORATION_PROPOSAL: self.validate_collaboration_proposal,
            MessageType.TASK_DELEGATION: self.validate_task_delegation,
            MessageType.RESOURCE_REQUEST: self.validate_resource_request
        }
    
    async def validate_message(self, message: AgentMessage) -> ValidationResult:
        """Validate message structure and content"""
        
        # Basic structure validation
        if not all([message.sender_agent, message.recipient_agent, message.message_type]):
            return ValidationResult(
                valid=False,
                error="Missing required fields",
                error_code="INVALID_STRUCTURE"
            )
        
        # Agent existence validation
        if not await self.agent_exists(message.sender_agent):
            return ValidationResult(
                valid=False,
                error=f"Sender agent {message.sender_agent} does not exist",
                error_code="INVALID_SENDER"
            )
        
        if not await self.agent_exists(message.recipient_agent):
            return ValidationResult(
                valid=False,
                error=f"Recipient agent {message.recipient_agent} does not exist",
                error_code="INVALID_RECIPIENT"
            )
        
        # Message type specific validation
        if message.message_type in self.validation_rules:
            type_validation = await self.validation_rules[message.message_type](message)
            if not type_validation.valid:
                return type_validation
        
        return ValidationResult(valid=True)
    
    async def validate_context_request(self, message: AgentMessage) -> ValidationResult:
        """Validate context request message"""
        required_fields = ["context_type", "scope"]
        
        for field in required_fields:
            if field not in message.payload:
                return ValidationResult(
                    valid=False,
                    error=f"Missing required field: {field}",
                    error_code="MISSING_CONTEXT_FIELD"
                )
        
        # Validate context type
        valid_context_types = ["current_state", "historical_patterns", "capabilities", "resources"]
        if message.payload["context_type"] not in valid_context_types:
            return ValidationResult(
                valid=False,
                error=f"Invalid context type: {message.payload['context_type']}",
                error_code="INVALID_CONTEXT_TYPE"
            )
        
        return ValidationResult(valid=True)
    
    async def validate_collaboration_proposal(self, message: AgentMessage) -> ValidationResult:
        """Validate collaboration proposal message"""
        required_fields = ["collaboration_type", "task_description", "duration_estimate"]
        
        for field in required_fields:
            if field not in message.payload:
                return ValidationResult(
                    valid=False,
                    error=f"Missing required field: {field}",
                    error_code="MISSING_COLLABORATION_FIELD"
                )
        
        return ValidationResult(valid=True)
```

## Smart Routing System

### 1. ML-Enhanced Router

```python
class SmartRouter:
    def __init__(self, coordination_service: CoordinationServiceClient):
        self.coordination_service = coordination_service
        self.communication_graph = CommunicationGraph()
        self.routing_cache = RoutingCache()
        self.performance_monitor = RoutingPerformanceMonitor()
    
    async def route_message(self, message: AgentMessage) -> RoutingDecision:
        """Route message using ML-enhanced decision making"""
        
        # Check cache for recent routing decisions
        cached_decision = await self.routing_cache.get_routing_decision(
            message.sender_agent,
            message.recipient_agent,
            message.message_type
        )
        
        if cached_decision and cached_decision.is_valid():
            return cached_decision
        
        # Analyze current communication state
        communication_state = await self.communication_graph.get_current_state()
        
        # Check for potential recursion
        recursion_risk = await self.analyze_recursion_risk(
            message.sender_agent,
            message.recipient_agent,
            communication_state
        )
        
        # Get ML-enhanced routing decision
        routing_decision = await self.coordination_service.route_agent_message(
            sender=message.sender_agent,
            recipient=message.recipient_agent,
            message={
                "type": message.message_type.value,
                "priority": message.priority.value,
                "payload_size": len(str(message.payload)),
                "requires_response": message.requires_response
            }
        )
        
        # Apply recursion prevention if needed
        if recursion_risk.risk_level == "high":
            routing_decision = await self.apply_recursion_prevention(
                message, routing_decision, recursion_risk
            )
        
        # Cache decision for future use
        await self.routing_cache.cache_routing_decision(
            message.sender_agent,
            message.recipient_agent,
            message.message_type,
            routing_decision
        )
        
        return routing_decision
    
    async def analyze_recursion_risk(self, sender: str, recipient: str, comm_state: Dict) -> RecursionRisk:
        """Analyze risk of creating communication loops"""
        
        # Check direct recursion (A -> B -> A)
        if self.communication_graph.has_active_communication(recipient, sender):
            return RecursionRisk(
                risk_level="high",
                risk_type="direct_recursion",
                description=f"Direct recursion detected: {sender} -> {recipient} -> {sender}"
            )
        
        # Check indirect recursion (A -> B -> C -> A)
        path_exists = await self.communication_graph.has_path(recipient, sender, max_depth=5)
        if path_exists:
            return RecursionRisk(
                risk_level="medium",
                risk_type="indirect_recursion",
                description=f"Indirect recursion path detected from {recipient} to {sender}"
            )
        
        # Check communication frequency
        recent_communications = await self.communication_graph.get_recent_communications(
            sender, recipient, time_window=timedelta(minutes=5)
        )
        
        if len(recent_communications) > 10:
            return RecursionRisk(
                risk_level="medium",
                risk_type="high_frequency",
                description=f"High communication frequency detected: {len(recent_communications)} messages in 5 minutes"
            )
        
        return RecursionRisk(risk_level="low", risk_type="none", description="No recursion risk detected")
    
    async def apply_recursion_prevention(self, message: AgentMessage, routing_decision: RoutingDecision, risk: RecursionRisk) -> RoutingDecision:
        """Apply recursion prevention strategies"""
        
        if risk.risk_type == "direct_recursion":
            # Route through coordinator
            return RoutingDecision(
                route_type="coordinator_mediated",
                direct_allowed=False,
                coordinator_agent="message-coordinator",
                delay_seconds=0,
                reason="Direct recursion prevention"
            )
        
        elif risk.risk_type == "indirect_recursion":
            # Add delay to break synchronous loops
            return RoutingDecision(
                route_type="delayed_direct",
                direct_allowed=True,
                delay_seconds=random.randint(1, 5),
                reason="Indirect recursion prevention with delay"
            )
        
        elif risk.risk_type == "high_frequency":
            # Queue message for later delivery
            return RoutingDecision(
                route_type="queued",
                direct_allowed=False,
                queue_name=f"agent_queue_{message.recipient_agent}",
                delay_seconds=30,
                reason="High frequency communication throttling"
            )
        
        return routing_decision
```

### 2. Communication Graph Management

```python
class CommunicationGraph:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.graph_key = "communication_graph"
        self.active_communications_key = "active_communications"
    
    async def add_communication(self, sender: str, recipient: str, message_id: str):
        """Add communication edge to graph"""
        
        # Add to directed graph
        await self.redis.sadd(f"{self.graph_key}:{sender}:outgoing", recipient)
        await self.redis.sadd(f"{self.graph_key}:{recipient}:incoming", sender)
        
        # Track active communication
        communication_record = {
            "sender": sender,
            "recipient": recipient,
            "message_id": message_id,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        await self.redis.hset(
            f"{self.active_communications_key}:{message_id}",
            mapping=communication_record
        )
        
        # Set TTL for cleanup
        await self.redis.expire(f"{self.active_communications_key}:{message_id}", 3600)
    
    async def complete_communication(self, message_id: str):
        """Mark communication as completed"""
        await self.redis.hset(
            f"{self.active_communications_key}:{message_id}",
            "status", "completed"
        )
    
    async def has_path(self, start: str, end: str, max_depth: int = 5) -> bool:
        """Check if path exists from start to end agent"""
        if start == end:
            return True
        
        visited = set()
        queue = [(start, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Get outgoing connections
            outgoing = await self.redis.smembers(f"{self.graph_key}:{current}:outgoing")
            
            for neighbor in outgoing:
                if neighbor == end:
                    return True
                
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        
        return False
    
    async def has_active_communication(self, sender: str, recipient: str) -> bool:
        """Check if there's an active communication between agents"""
        
        # Search for active communications
        pattern = f"{self.active_communications_key}:*"
        communication_keys = await self.redis.keys(pattern)
        
        for key in communication_keys:
            comm_data = await self.redis.hgetall(key)
            
            if (comm_data.get("sender") == sender and 
                comm_data.get("recipient") == recipient and 
                comm_data.get("status") == "active"):
                return True
        
        return False
    
    async def get_recent_communications(self, sender: str, recipient: str, time_window: timedelta) -> List[Dict]:
        """Get recent communications between agents"""
        
        cutoff_time = datetime.now() - time_window
        recent_communications = []
        
        pattern = f"{self.active_communications_key}:*"
        communication_keys = await self.redis.keys(pattern)
        
        for key in communication_keys:
            comm_data = await self.redis.hgetall(key)
            
            if (comm_data.get("sender") == sender and 
                comm_data.get("recipient") == recipient):
                
                timestamp = datetime.fromisoformat(comm_data.get("timestamp"))
                if timestamp > cutoff_time:
                    recent_communications.append(comm_data)
        
        return recent_communications
    
    async def cleanup_old_communications(self):
        """Clean up old communication records"""
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        pattern = f"{self.active_communications_key}:*"
        communication_keys = await self.redis.keys(pattern)
        
        for key in communication_keys:
            comm_data = await self.redis.hgetall(key)
            timestamp = datetime.fromisoformat(comm_data.get("timestamp"))
            
            if timestamp < cutoff_time:
                await self.redis.delete(key)
```

## Agent Communication Interface

### 1. Agent Communication Client

```python
class AgentCommunicationClient:
    def __init__(self, agent_id: str, router: SmartRouter):
        self.agent_id = agent_id
        self.router = router
        self.message_handlers = {}
        self.active_collaborations = {}
        self.context_cache = {}
    
    async def send_message(self, recipient: str, message_type: MessageType, payload: Dict, priority: Priority = Priority.NORMAL) -> MessageResponse:
        """Send message to another agent"""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent=self.agent_id,
            recipient_agent=recipient,
            message_type=message_type,
            priority=priority,
            payload=payload,
            requires_response=message_type in [MessageType.CONTEXT_REQUEST, MessageType.COLLABORATION_PROPOSAL],
            timeout_seconds=300,
            created_at=datetime.now(),
            routing_metadata={}
        )
        
        # Validate message
        validation_result = await MessageValidator().validate_message(message)
        if not validation_result.valid:
            raise InvalidMessageError(validation_result.error)
        
        # Route message
        routing_decision = await self.router.route_message(message)
        
        # Send based on routing decision
        if routing_decision.direct_allowed:
            return await self.send_direct_message(message, routing_decision)
        else:
            return await self.send_mediated_message(message, routing_decision)
    
    async def request_context(self, from_agent: str, context_type: str, scope: str) -> ContextResponse:
        """Request context from another agent"""
        
        response = await self.send_message(
            recipient=from_agent,
            message_type=MessageType.CONTEXT_REQUEST,
            payload={
                "context_type": context_type,
                "scope": scope,
                "requester_capabilities": await self.get_my_capabilities(),
                "intended_use": "task_execution"
            },
            priority=Priority.HIGH
        )
        
        if response.success:
            context_data = response.payload.get("context_data")
            
            # Cache context for reuse
            cache_key = f"{from_agent}:{context_type}:{scope}"
            self.context_cache[cache_key] = {
                "data": context_data,
                "timestamp": datetime.now(),
                "ttl": 1800  # 30 minutes
            }
            
            return ContextResponse(
                success=True,
                context_data=context_data,
                metadata=response.payload.get("metadata", {}),
                source_agent=from_agent
            )
        else:
            return ContextResponse(
                success=False,
                error=response.error,
                source_agent=from_agent
            )
    
    async def propose_collaboration(self, with_agent: str, task_description: str, collaboration_type: str) -> CollaborationResponse:
        """Propose collaboration with another agent"""
        
        collaboration_id = str(uuid.uuid4())
        
        response = await self.send_message(
            recipient=with_agent,
            message_type=MessageType.COLLABORATION_PROPOSAL,
            payload={
                "collaboration_id": collaboration_id,
                "collaboration_type": collaboration_type,
                "task_description": task_description,
                "duration_estimate": await self.estimate_task_duration(task_description),
                "required_capabilities": await self.analyze_required_capabilities(task_description),
                "proposed_workload_split": await self.propose_workload_split(task_description, with_agent)
            },
            priority=Priority.HIGH
        )
        
        if response.success and response.payload.get("accepted"):
            # Store active collaboration
            self.active_collaborations[collaboration_id] = {
                "partner_agent": with_agent,
                "task_description": task_description,
                "collaboration_type": collaboration_type,
                "status": "active",
                "started_at": datetime.now()
            }
            
            return CollaborationResponse(
                success=True,
                collaboration_id=collaboration_id,
                accepted=True,
                partner_agent=with_agent,
                collaboration_details=response.payload.get("collaboration_details", {})
            )
        else:
            return CollaborationResponse(
                success=False,
                accepted=False,
                error=response.error if not response.success else "Collaboration declined",
                partner_agent=with_agent
            )
    
    async def delegate_task(self, to_agent: str, task_description: str, deadline: datetime) -> TaskDelegationResponse:
        """Delegate task to another agent"""
        
        task_id = str(uuid.uuid4())
        
        response = await self.send_message(
            recipient=to_agent,
            message_type=MessageType.TASK_DELEGATION,
            payload={
                "task_id": task_id,
                "task_description": task_description,
                "deadline": deadline.isoformat(),
                "required_capabilities": await self.analyze_required_capabilities(task_description),
                "context_package": await self.prepare_task_context(task_description),
                "success_criteria": await self.define_success_criteria(task_description),
                "priority": Priority.NORMAL.value
            },
            priority=Priority.HIGH
        )
        
        return TaskDelegationResponse(
            success=response.success,
            task_id=task_id if response.success else None,
            accepted=response.payload.get("accepted", False) if response.success else False,
            estimated_completion=response.payload.get("estimated_completion") if response.success else None,
            error=response.error if not response.success else None
        )
    
    def register_message_handler(self, message_type: MessageType, handler_func):
        """Register handler for incoming message type"""
        self.message_handlers[message_type] = handler_func
    
    async def handle_incoming_message(self, message: AgentMessage) -> MessageResponse:
        """Handle incoming message"""
        
        if message.message_type in self.message_handlers:
            try:
                response_payload = await self.message_handlers[message.message_type](message)
                return MessageResponse(
                    success=True,
                    message_id=message.message_id,
                    payload=response_payload
                )
            except Exception as e:
                return MessageResponse(
                    success=False,
                    message_id=message.message_id,
                    error=str(e)
                )
        else:
            return MessageResponse(
                success=False,
                message_id=message.message_id,
                error=f"No handler registered for message type: {message.message_type.value}"
            )
```

### 2. Standard Message Handlers

```python
class StandardMessageHandlers:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    async def handle_context_request(self, message: AgentMessage) -> Dict:
        """Handle context request from another agent"""
        
        context_type = message.payload["context_type"]
        scope = message.payload["scope"]
        
        # Determine what context to provide based on request
        if context_type == "current_state":
            context_data = await self.get_current_state_context(scope)
        elif context_type == "historical_patterns":
            context_data = await self.get_historical_patterns_context(scope)
        elif context_type == "capabilities":
            context_data = await self.get_capabilities_context(scope)
        elif context_type == "resources":
            context_data = await self.get_resources_context(scope)
        else:
            raise ValueError(f"Unknown context type: {context_type}")
        
        return {
            "context_data": context_data,
            "metadata": {
                "context_type": context_type,
                "scope": scope,
                "provider_agent": self.agent_id,
                "generated_at": datetime.now().isoformat(),
                "confidence_score": await self.calculate_context_confidence(context_data)
            }
        }
    
    async def handle_collaboration_proposal(self, message: AgentMessage) -> Dict:
        """Handle collaboration proposal from another agent"""
        
        collaboration_type = message.payload["collaboration_type"]
        task_description = message.payload["task_description"]
        
        # Analyze if collaboration is beneficial
        collaboration_analysis = await self.analyze_collaboration_benefit(
            partner_agent=message.sender_agent,
            collaboration_type=collaboration_type,
            task_description=task_description
        )
        
        if collaboration_analysis.beneficial:
            return {
                "accepted": True,
                "collaboration_details": {
                    "my_contribution": collaboration_analysis.my_contribution,
                    "expected_benefits": collaboration_analysis.benefits,
                    "estimated_duration": collaboration_analysis.duration,
                    "preferred_communication_frequency": "high"
                }
            }
        else:
            return {
                "accepted": False,
                "reason": collaboration_analysis.rejection_reason,
                "alternative_suggestions": collaboration_analysis.alternatives
            }
    
    async def handle_task_delegation(self, message: AgentMessage) -> Dict:
        """Handle task delegation from another agent"""
        
        task_description = message.payload["task_description"]
        deadline = datetime.fromisoformat(message.payload["deadline"])
        
        # Analyze task feasibility
        feasibility_analysis = await self.analyze_task_feasibility(
            task_description=task_description,
            deadline=deadline,
            delegator=message.sender_agent
        )
        
        if feasibility_analysis.feasible:
            # Accept task
            estimated_completion = await self.estimate_completion_time(task_description)
            
            return {
                "accepted": True,
                "estimated_completion": estimated_completion.isoformat(),
                "resource_requirements": feasibility_analysis.resources_needed,
                "confidence_score": feasibility_analysis.confidence
            }
        else:
            return {
                "accepted": False,
                "reason": feasibility_analysis.rejection_reason,
                "alternative_approaches": feasibility_analysis.alternatives,
                "suggested_agents": feasibility_analysis.better_suited_agents
            }
    
    async def handle_resource_request(self, message: AgentMessage) -> Dict:
        """Handle resource request from another agent"""
        
        resource_type = message.payload["resource_type"]
        quantity = message.payload["quantity"]
        duration = message.payload.get("duration", 3600)  # Default 1 hour
        
        # Check resource availability
        availability = await self.check_resource_availability(resource_type, quantity, duration)
        
        if availability.available:
            # Reserve resource
            reservation_id = await self.reserve_resource(
                resource_type=resource_type,
                quantity=quantity,
                duration=duration,
                requester=message.sender_agent
            )
            
            return {
                "granted": True,
                "reservation_id": reservation_id,
                "expiry_time": (datetime.now() + timedelta(seconds=duration)).isoformat(),
                "usage_guidelines": availability.usage_guidelines
            }
        else:
            return {
                "granted": False,
                "reason": availability.unavailable_reason,
                "available_at": availability.next_available_time.isoformat() if availability.next_available_time else None,
                "alternative_resources": availability.alternatives
            }
```

## Collaboration Patterns

### 1. Sequential Collaboration

```python
async def sequential_collaboration_pattern(agents: List[str], task_description: str) -> CollaborationResult:
    """Execute sequential collaboration pattern"""
    
    results = []
    current_context = await prepare_initial_context(task_description)
    
    for i, agent_id in enumerate(agents):
        # Get agent communication client
        agent_client = get_agent_client(agent_id)
        
        # Prepare context for current agent
        agent_context = await prepare_agent_context(
            agent_id=agent_id,
            base_context=current_context,
            previous_results=results,
            position_in_sequence=i
        )
        
        # Delegate task to current agent
        task_response = await agent_client.delegate_task(
            to_agent=agent_id,
            task_description=f"Sequential step {i+1}: {task_description}",
            deadline=datetime.now() + timedelta(hours=2)
        )
        
        if task_response.success and task_response.accepted:
            # Wait for completion
            result = await wait_for_task_completion(task_response.task_id)
            results.append(result)
            
            # Update context for next agent
            current_context = await update_context_with_result(current_context, result)
        else:
            # Handle failure in sequence
            return CollaborationResult(
                success=False,
                error=f"Agent {agent_id} rejected task: {task_response.error}",
                completed_steps=len(results),
                partial_results=results
            )
    
    return CollaborationResult(
        success=True,
        final_result=await synthesize_sequential_results(results),
        completed_steps=len(results),
        all_results=results
    )
```

### 2. Parallel Collaboration

```python
async def parallel_collaboration_pattern(agent_assignments: Dict[str, str], shared_context: Dict) -> CollaborationResult:
    """Execute parallel collaboration pattern"""
    
    # Prepare shared collaboration space
    collaboration_id = str(uuid.uuid4())
    shared_space = await create_shared_collaboration_space(collaboration_id, agent_assignments.keys())
    
    # Start all agents in parallel
    tasks = {}
    for agent_id, task_description in agent_assignments.items():
        agent_client = get_agent_client(agent_id)
        
        # Propose collaboration with shared space
        collaboration_response = await agent_client.propose_collaboration(
            with_agent="collaboration_coordinator",
            task_description=task_description,
            collaboration_type="parallel_shared_space"
        )
        
        if collaboration_response.success and collaboration_response.accepted:
            # Start agent task
            task_future = asyncio.create_task(
                execute_parallel_agent_task(
                    agent_id=agent_id,
                    task_description=task_description,
                    shared_space=shared_space,
                    collaboration_id=collaboration_id
                )
            )
            tasks[agent_id] = task_future
        else:
            return CollaborationResult(
                success=False,
                error=f"Agent {agent_id} declined collaboration: {collaboration_response.error}"
            )
    
    # Wait for all tasks to complete
    try:
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Process results
        successful_results = {}
        failed_agents = []
        
        for agent_id, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                failed_agents.append((agent_id, str(result)))
            else:
                successful_results[agent_id] = result
        
        # Synthesize parallel results
        if len(successful_results) >= len(agent_assignments) * 0.7:  # 70% success threshold
            final_result = await synthesize_parallel_results(successful_results, shared_space)
            return CollaborationResult(
                success=True,
                final_result=final_result,
                agent_results=successful_results,
                failed_agents=failed_agents
            )
        else:
            return CollaborationResult(
                success=False,
                error="Too many agents failed in parallel execution",
                agent_results=successful_results,
                failed_agents=failed_agents
            )
    
    finally:
        # Cleanup shared space
        await cleanup_shared_collaboration_space(collaboration_id)
```

### 3. Hierarchical Collaboration

```python
async def hierarchical_collaboration_pattern(coordinator_agent: str, subordinate_agents: List[str], task_description: str) -> CollaborationResult:
    """Execute hierarchical collaboration pattern"""
    
    coordinator_client = get_agent_client(coordinator_agent)
    
    # Coordinator analyzes task and creates work breakdown
    work_breakdown = await coordinator_client.send_message(
        recipient="task_analyzer",
        message_type=MessageType.COORDINATION_REQUEST,
        payload={
            "task_description": task_description,
            "available_agents": subordinate_agents,
            "breakdown_type": "hierarchical",
            "coordination_style": "direct_management"
        }
    )
    
    if not work_breakdown.success:
        return CollaborationResult(
            success=False,
            error="Failed to create work breakdown"
        )
    
    # Coordinator delegates subtasks to subordinates
    subtask_assignments = work_breakdown.payload["subtask_assignments"]
    active_delegations = {}
    
    for subtask in subtask_assignments:
        assigned_agent = subtask["assigned_agent"]
        
        delegation_response = await coordinator_client.delegate_task(
            to_agent=assigned_agent,
            task_description=subtask["description"],
            deadline=datetime.fromisoformat(subtask["deadline"])
        )
        
        if delegation_response.success and delegation_response.accepted:
            active_delegations[subtask["subtask_id"]] = {
                "agent": assigned_agent,
                "task_id": delegation_response.task_id,
                "status": "active"
            }
        else:
            # Coordinator handles delegation failure
            await coordinator_client.send_message(
                recipient="task_analyzer",
                message_type=MessageType.ERROR_NOTIFICATION,
                payload={
                    "error_type": "delegation_failure",
                    "failed_agent": assigned_agent,
                    "subtask_id": subtask["subtask_id"],
                    "error_details": delegation_response.error
                }
            )
    
    # Coordinator monitors progress and coordinates
    coordination_result = await monitor_hierarchical_execution(
        coordinator_client=coordinator_client,
        active_delegations=active_delegations,
        coordination_strategy=work_breakdown.payload["coordination_strategy"]
    )
    
    return coordination_result
```

## Performance Optimization

### 1. Message Batching

```python
class MessageBatcher:
    def __init__(self, batch_size: int = 10, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_messages = defaultdict(list)
        self.batch_timers = {}
    
    async def queue_message(self, message: AgentMessage):
        """Queue message for batching"""
        recipient = message.recipient_agent
        
        self.pending_messages[recipient].append(message)
        
        # Start timer if this is the first message for recipient
        if recipient not in self.batch_timers:
            self.batch_timers[recipient] = asyncio.create_task(
                self.batch_timeout_handler(recipient)
            )
        
        # Send batch if size threshold reached
        if len(self.pending_messages[recipient]) >= self.batch_size:
            await self.send_batch(recipient)
    
    async def batch_timeout_handler(self, recipient: str):
        """Handle batch timeout"""
        await asyncio.sleep(self.batch_timeout)
        await self.send_batch(recipient)
    
    async def send_batch(self, recipient: str):
        """Send batched messages to recipient"""
        if recipient not in self.pending_messages or not self.pending_messages[recipient]:
            return
        
        messages = self.pending_messages[recipient].copy()
        self.pending_messages[recipient].clear()
        
        # Cancel timeout timer
        if recipient in self.batch_timers:
            self.batch_timers[recipient].cancel()
            del self.batch_timers[recipient]
        
        # Send batch
        batch_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_agent="message_batcher",
            recipient_agent=recipient,
            message_type=MessageType.BATCH_DELIVERY,
            priority=Priority.NORMAL,
            payload={"batched_messages": [msg.to_dict() for msg in messages]},
            requires_response=False,
            timeout_seconds=300,
            created_at=datetime.now(),
            routing_metadata={"batch_size": len(messages)}
        )
        
        await self.send_direct_message(batch_message)
```

### 2. Connection Pooling

```python
class AgentConnectionPool:
    def __init__(self, max_connections_per_agent: int = 5):
        self.max_connections_per_agent = max_connections_per_agent
        self.connection_pools = defaultdict(list)
        self.active_connections = defaultdict(int)
        self.connection_lock = asyncio.Lock()
    
    async def get_connection(self, agent_id: str) -> AgentConnection:
        """Get connection to agent from pool"""
        async with self.connection_lock:
            if self.connection_pools[agent_id]:
                connection = self.connection_pools[agent_id].pop()
                if await connection.is_healthy():
                    return connection
                else:
                    await connection.close()
            
            # Create new connection if pool empty or unhealthy
            if self.active_connections[agent_id] < self.max_connections_per_agent:
                connection = await self.create_new_connection(agent_id)
                self.active_connections[agent_id] += 1
                return connection
            else:
                # Wait for connection to become available
                return await self.wait_for_available_connection(agent_id)
    
    async def return_connection(self, agent_id: str, connection: AgentConnection):
        """Return connection to pool"""
        async with self.connection_lock:
            if await connection.is_healthy():
                self.connection_pools[agent_id].append(connection)
            else:
                await connection.close()
                self.active_connections[agent_id] -= 1
    
    async def create_new_connection(self, agent_id: str) -> AgentConnection:
        """Create new connection to agent"""
        agent_info = await get_agent_info(agent_id)
        
        connection = AgentConnection(
            agent_id=agent_id,
            endpoint=agent_info.endpoint,
            protocol=agent_info.protocol,
            auth_token=agent_info.auth_token
        )
        
        await connection.connect()
        return connection
```

This comprehensive agent communication protocol specification provides the foundation for enabling direct inter-agent communication while maintaining system stability and preventing recursion loops through ML-enhanced routing and intelligent coordination.