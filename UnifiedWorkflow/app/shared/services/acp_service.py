"""
Agent Communication Protocol (ACP) Service - Layer 3

Implements high-level workflow orchestration, task delegation, and stateful session
management across multiple agents with enterprise observability and auditability.

Key Features:
- Multi-agent workflow orchestration
- Intelligent task delegation and assignment
- Stateful session management across conversations
- Workflow state persistence and recovery
- Enterprise-grade logging and audit trails
- Performance monitoring and optimization
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque

import redis.asyncio as redis
from pydantic import BaseModel, Field

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, ACPWorkflowControl, ACPTaskDelegation, ACPSessionManagement,
    WorkflowDefinition, WorkflowStep, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.protocol_infrastructure import ProtocolServiceManager
from shared.services.a2a_service import A2AService
from shared.services.mcp_service import MCPService
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ================================
# Workflow Engine
# ================================

class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class TaskStatus(str, Enum):
    """Individual task status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowInstance(BaseModel):
    """Running instance of a workflow."""
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_definition: WorkflowDefinition
    
    # Execution state
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_id: Optional[str] = None
    completed_steps: Set[str] = Field(default_factory=set)
    failed_steps: Set[str] = Field(default_factory=set)
    
    # Step results
    step_results: Dict[str, Any] = Field(default_factory=dict)
    step_assignments: Dict[str, str] = Field(default_factory=dict)  # step_id -> agent_id
    step_start_times: Dict[str, datetime] = Field(default_factory=dict)
    step_end_times: Dict[str, datetime] = Field(default_factory=dict)
    
    # Execution context
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metrics
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    # Error handling
    error_log: List[Dict[str, Any]] = Field(default_factory=list)
    retry_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            set: lambda s: list(s)
        }


class WorkflowEngine:
    """Orchestrates multi-agent workflows."""
    
    def __init__(self, redis_client: redis.Redis, a2a_service: A2AService, mcp_service: MCPService):
        self.redis = redis_client
        self.a2a_service = a2a_service
        self.mcp_service = mcp_service
        self.active_workflows: Dict[str, WorkflowInstance] = {}
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        self.executor_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the workflow engine."""
        await self._load_workflow_definitions()
        await self._load_active_workflows()
        self.executor_task = asyncio.create_task(self._workflow_executor())
        logger.info("Workflow engine initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the workflow engine."""
        if self.executor_task:
            self.executor_task.cancel()
            try:
                await self.executor_task
            except asyncio.CancelledError:
                pass
                
        # Persist active workflows
        for workflow in self.active_workflows.values():
            await self._persist_workflow(workflow)
            
        logger.info("Workflow engine shutdown")
        
    async def start_workflow(
        self,
        workflow_id: str,
        execution_parameters: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Start a new workflow instance."""
        try:
            # Get workflow definition
            workflow_def = self.workflow_definitions.get(workflow_id)
            if not workflow_def:
                raise ValueError(f"Workflow definition not found: {workflow_id}")
                
            # Create workflow instance
            instance = WorkflowInstance(
                workflow_definition=workflow_def,
                execution_context=execution_parameters,
                user_id=user_id,
                session_id=session_id,
                total_tasks=len(workflow_def.steps)
            )
            
            # Store and queue for execution
            self.active_workflows[instance.instance_id] = instance
            await self.execution_queue.put(("start", instance.instance_id))
            await self._persist_workflow(instance)
            
            logger.info(f"Started workflow {workflow_id} with instance ID {instance.instance_id}")
            return instance.instance_id
            
        except Exception as e:
            logger.error(f"Error starting workflow {workflow_id}: {e}", exc_info=True)
            raise
            
    async def pause_workflow(self, instance_id: str) -> bool:
        """Pause a running workflow."""
        if instance_id not in self.active_workflows:
            return False
            
        workflow = self.active_workflows[instance_id]
        if workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.PAUSED
            await self._persist_workflow(workflow)
            logger.info(f"Paused workflow {instance_id}")
            return True
            
        return False
        
    async def resume_workflow(self, instance_id: str) -> bool:
        """Resume a paused workflow."""
        if instance_id not in self.active_workflows:
            return False
            
        workflow = self.active_workflows[instance_id]
        if workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING
            await self.execution_queue.put(("resume", instance_id))
            await self._persist_workflow(workflow)
            logger.info(f"Resumed workflow {instance_id}")
            return True
            
        return False
        
    async def abort_workflow(self, instance_id: str) -> bool:
        """Abort a workflow."""
        if instance_id not in self.active_workflows:
            return False
            
        workflow = self.active_workflows[instance_id]
        workflow.status = WorkflowStatus.ABORTED
        workflow.completed_at = datetime.now(timezone.utc)
        await self._persist_workflow(workflow)
        
        logger.info(f"Aborted workflow {instance_id}")
        return True
        
    async def get_workflow_status(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status and progress."""
        if instance_id not in self.active_workflows:
            return None
            
        workflow = self.active_workflows[instance_id]
        progress = workflow.completed_tasks / max(1, workflow.total_tasks)
        
        return {
            "instance_id": instance_id,
            "status": workflow.status.value,
            "progress": progress,
            "current_step": workflow.current_step_id,
            "completed_steps": len(workflow.completed_steps),
            "failed_steps": len(workflow.failed_steps),
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at,
            "execution_time": self._calculate_execution_time(workflow),
            "error_count": len(workflow.error_log)
        }
        
    async def _workflow_executor(self) -> None:
        """Main workflow execution loop."""
        while True:
            try:
                # Get next workflow action
                action, instance_id = await self.execution_queue.get()
                
                if instance_id not in self.active_workflows:
                    continue
                    
                workflow = self.active_workflows[instance_id]
                
                if action == "start":
                    await self._execute_workflow_start(workflow)
                elif action == "resume":
                    await self._execute_workflow_resume(workflow)
                elif action == "step_completed":
                    await self._handle_step_completion(workflow)
                    
                self.execution_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in workflow executor: {e}", exc_info=True)
                
    async def _execute_workflow_start(self, workflow: WorkflowInstance) -> None:
        """Start executing a workflow."""
        try:
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now(timezone.utc)
            
            # Find and execute initial steps
            initial_steps = await self._find_ready_steps(workflow)
            for step in initial_steps:
                await self._execute_step(workflow, step)
                
            await self._persist_workflow(workflow)
            
        except Exception as e:
            await self._handle_workflow_error(workflow, f"Workflow start error: {e}")
            
    async def _execute_workflow_resume(self, workflow: WorkflowInstance) -> None:
        """Resume executing a paused workflow."""
        try:
            workflow.status = WorkflowStatus.RUNNING
            
            # Find steps that are ready to execute
            ready_steps = await self._find_ready_steps(workflow)
            for step in ready_steps:
                await self._execute_step(workflow, step)
                
            await self._persist_workflow(workflow)
            
        except Exception as e:
            await self._handle_workflow_error(workflow, f"Workflow resume error: {e}")
            
    async def _find_ready_steps(self, workflow: WorkflowInstance) -> List[WorkflowStep]:
        """Find steps that are ready to execute."""
        ready_steps = []
        
        for step in workflow.workflow_definition.steps:
            # Skip if already completed or failed
            if step.step_id in workflow.completed_steps or step.step_id in workflow.failed_steps:
                continue
                
            # Check if dependencies are satisfied
            dependencies_met = all(
                dep_id in workflow.completed_steps 
                for dep_id in step.depends_on
            )
            
            if dependencies_met and step.status == "pending":
                ready_steps.append(step)
                
        return ready_steps
        
    async def _execute_step(self, workflow: WorkflowInstance, step: WorkflowStep) -> None:
        """Execute a single workflow step."""
        try:
            step.status = "executing"
            step.start_time = datetime.now(timezone.utc)
            workflow.step_start_times[step.step_id] = step.start_time
            workflow.current_step_id = step.step_id
            
            # Find and assign agent for this step
            agent_id = await self._assign_agent_to_step(workflow, step)
            if not agent_id:
                raise Exception(f"No suitable agent found for step {step.step_id}")
                
            workflow.step_assignments[step.step_id] = agent_id
            
            # Execute step based on type
            if step.step_type == "sequential":
                result = await self._execute_sequential_step(workflow, step, agent_id)
            elif step.step_type == "parallel":
                result = await self._execute_parallel_step(workflow, step, agent_id)
            elif step.step_type == "conditional":
                result = await self._execute_conditional_step(workflow, step, agent_id)
            else:
                result = await self._execute_default_step(workflow, step, agent_id)
                
            # Record step completion
            step.status = "completed"
            step.completion_time = datetime.now(timezone.utc)
            step.result = result
            
            workflow.step_results[step.step_id] = result
            workflow.step_end_times[step.step_id] = step.completion_time
            workflow.completed_steps.add(step.step_id)
            workflow.completed_tasks += 1
            
            # Check if workflow is complete
            if await self._is_workflow_complete(workflow):
                await self._complete_workflow(workflow)
            else:
                # Queue next steps
                await self.execution_queue.put(("step_completed", workflow.instance_id))
                
        except Exception as e:
            await self._handle_step_error(workflow, step, str(e))
            
    async def _assign_agent_to_step(self, workflow: WorkflowInstance, step: WorkflowStep) -> Optional[str]:
        """Assign an agent to execute a step."""
        try:
            # Check if step has pre-assigned agent
            if step.assigned_agent:
                return step.assigned_agent
                
            # Find agents with required capabilities
            if step.required_capabilities:
                # Use A2A service to find suitable agents
                agents = await self.a2a_service.find_agents(
                    required_capabilities=step.required_capabilities,
                    selection_criteria={"strategy": "best_fit"}
                )
                
                if agents:
                    # For now, select the first available agent
                    # In production, implement more sophisticated selection logic
                    return agents[0].agent_id
                    
        except Exception as e:
            logger.error(f"Error assigning agent to step {step.step_id}: {e}", exc_info=True)
            
        return None
        
    async def _execute_default_step(self, workflow: WorkflowInstance, step: WorkflowStep, agent_id: str) -> Any:
        """Execute a default step by delegating to assigned agent."""
        # Create task delegation message
        task_delegation = {
            "task_description": step.step_name,
            "task_type": step.step_type,
            "input_data": step.input_requirements,
            "expected_output": step.output_specification,
            "execution_context": workflow.execution_context,
            "workflow_context": {
                "instance_id": workflow.instance_id,
                "step_id": step.step_id,
                "previous_results": workflow.step_results
            }
        }
        
        # Send task to agent via A2A
        success = await self.a2a_service.send_message(
            sender_id="acp_orchestrator",
            target_agent_id=agent_id,
            message_content=json.dumps(task_delegation),
            conversation_id=workflow.session_id
        )
        
        if not success:
            raise Exception(f"Failed to send task to agent {agent_id}")
            
        # For now, return a placeholder result
        # In production, implement proper result collection
        return {"status": "delegated", "agent_id": agent_id, "timestamp": datetime.now(timezone.utc).isoformat()}
        
    async def _execute_sequential_step(self, workflow: WorkflowInstance, step: WorkflowStep, agent_id: str) -> Any:
        """Execute a sequential step."""
        return await self._execute_default_step(workflow, step, agent_id)
        
    async def _execute_parallel_step(self, workflow: WorkflowInstance, step: WorkflowStep, agent_id: str) -> Any:
        """Execute a parallel step."""
        return await self._execute_default_step(workflow, step, agent_id)
        
    async def _execute_conditional_step(self, workflow: WorkflowInstance, step: WorkflowStep, agent_id: str) -> Any:
        """Execute a conditional step."""
        # Evaluate condition based on previous step results
        # This is a simplified implementation
        condition_met = True  # Placeholder condition evaluation
        
        if condition_met:
            return await self._execute_default_step(workflow, step, agent_id)
        else:
            # Skip step
            step.status = "skipped"
            return {"status": "skipped", "reason": "condition_not_met"}
            
    async def _is_workflow_complete(self, workflow: WorkflowInstance) -> bool:
        """Check if workflow is complete."""
        total_steps = len(workflow.workflow_definition.steps)
        processed_steps = len(workflow.completed_steps) + len(workflow.failed_steps)
        return processed_steps >= total_steps
        
    async def _complete_workflow(self, workflow: WorkflowInstance) -> None:
        """Complete a workflow."""
        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.now(timezone.utc)
        await self._persist_workflow(workflow)
        
        logger.info(f"Workflow {workflow.instance_id} completed successfully")
        
    async def _handle_workflow_error(self, workflow: WorkflowInstance, error_message: str) -> None:
        """Handle workflow-level errors."""
        workflow.status = WorkflowStatus.FAILED
        workflow.completed_at = datetime.now(timezone.utc)
        workflow.error_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "workflow",
            "message": error_message
        })
        
        await self._persist_workflow(workflow)
        logger.error(f"Workflow {workflow.instance_id} failed: {error_message}")
        
    async def _handle_step_error(self, workflow: WorkflowInstance, step: WorkflowStep, error_message: str) -> None:
        """Handle step-level errors."""
        step.status = "failed"
        step.completion_time = datetime.now(timezone.utc)
        
        workflow.failed_steps.add(step.step_id)
        workflow.failed_tasks += 1
        workflow.step_end_times[step.step_id] = step.completion_time
        workflow.error_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "step",
            "step_id": step.step_id,
            "message": error_message
        })
        
        # Check failure policy
        if step.failure_policy == "abort":
            await self._handle_workflow_error(workflow, f"Step {step.step_id} failed: {error_message}")
        elif step.failure_policy == "retry" and workflow.retry_count < 3:
            workflow.retry_count += 1
            step.status = "pending"
            workflow.failed_steps.discard(step.step_id)
            workflow.failed_tasks -= 1
            await self.execution_queue.put(("step_completed", workflow.instance_id))
        # else continue with next steps
        
        await self._persist_workflow(workflow)
        
    async def _calculate_execution_time(self, workflow: WorkflowInstance) -> Optional[float]:
        """Calculate workflow execution time in seconds."""
        if not workflow.started_at:
            return None
            
        end_time = workflow.completed_at or datetime.now(timezone.utc)
        return (end_time - workflow.started_at).total_seconds()
        
    async def _persist_workflow(self, workflow: WorkflowInstance) -> None:
        """Persist workflow instance to Redis."""
        workflow_key = f"acp:workflow:{workflow.instance_id}"
        await self.redis.setex(workflow_key, 86400, workflow.json())  # 24 hour TTL
        
    async def _load_workflow_definitions(self) -> None:
        """Load workflow definitions from storage."""
        # For now, define some basic workflow templates
        # In production, load from database or configuration files
        pass
        
    async def _load_active_workflows(self) -> None:
        """Load active workflows from Redis."""
        pattern = "acp:workflow:*"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            try:
                workflow_data = await self.redis.get(key)
                if workflow_data:
                    workflow = WorkflowInstance.parse_raw(workflow_data)
                    if workflow.status in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
                        self.active_workflows[workflow.instance_id] = workflow
            except Exception as e:
                logger.error(f"Error loading workflow from {key}: {e}", exc_info=True)
                
        logger.info(f"Loaded {len(self.active_workflows)} active workflows")


# ================================
# Task Delegation Manager
# ================================

class TaskDelegationManager:
    """Manages intelligent task delegation and assignment."""
    
    def __init__(self, redis_client: redis.Redis, a2a_service: A2AService):
        self.redis = redis_client
        self.a2a_service = a2a_service
        self.active_delegations: Dict[str, Dict[str, Any]] = {}
        self.agent_workloads: Dict[str, int] = defaultdict(int)
        
    async def delegate_task(
        self,
        task_description: str,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        delegation_criteria: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """Delegate a task to the most suitable agent."""
        try:
            task_id = str(uuid.uuid4())
            
            # Find suitable agents
            selection_strategy = delegation_criteria.get("selection_strategy", "best_fit")
            
            if selection_strategy == "negotiated":
                # Use capability negotiation
                result = await self.a2a_service.negotiate_capability(
                    requester_id="acp_task_delegator",
                    required_capabilities=required_capabilities,
                    task_parameters=task_parameters
                )
                
                if result:
                    negotiation_id, agent_id = result
                    self.active_delegations[task_id] = {
                        "task_description": task_description,
                        "agent_id": agent_id,
                        "negotiation_id": negotiation_id,
                        "status": "negotiated",
                        "created_at": datetime.now(timezone.utc)
                    }
                    return task_id
                    
            else:
                # Direct assignment
                agents = await self.a2a_service.find_agents(
                    required_capabilities=required_capabilities,
                    selection_criteria={"strategy": selection_strategy}
                )
                
                if agents:
                    selected_agent = await self._select_best_agent(agents, delegation_criteria)
                    
                    # Send task delegation message
                    success = await self.a2a_service.send_message(
                        sender_id="acp_task_delegator",
                        target_agent_id=selected_agent.agent_id,
                        message_content=json.dumps({
                            "task_id": task_id,
                            "task_description": task_description,
                            "task_parameters": task_parameters,
                            "user_id": user_id
                        })
                    )
                    
                    if success:
                        self.active_delegations[task_id] = {
                            "task_description": task_description,
                            "agent_id": selected_agent.agent_id,
                            "status": "delegated",
                            "created_at": datetime.now(timezone.utc)
                        }
                        
                        # Update agent workload
                        self.agent_workloads[selected_agent.agent_id] += 1
                        
                        return task_id
                        
        except Exception as e:
            logger.error(f"Error delegating task: {e}", exc_info=True)
            
        return None
        
    async def _select_best_agent(self, agents: List[Any], criteria: Dict[str, Any]) -> Any:
        """Select the best agent based on delegation criteria."""
        if not agents:
            return None
            
        strategy = criteria.get("selection_strategy", "best_fit")
        
        if strategy == "round_robin":
            # Simple round-robin selection
            return agents[len(self.active_delegations) % len(agents)]
        elif strategy == "least_loaded":
            # Select agent with lowest current workload
            return min(agents, key=lambda a: self.agent_workloads[a.agent_id])
        else:  # best_fit
            # Score-based selection (placeholder)
            return agents[0]


# ================================
# Session Manager
# ================================

class SessionManager:
    """Manages long-running conversation sessions across multiple agents."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def create_session(
        self,
        session_type: str,
        participants: List[str],
        initial_context: Dict[str, Any] = None
    ) -> str:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "session_type": session_type,
            "participants": participants,
            "shared_context": initial_context or {},
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "active_workflows": []
        }
        
        self.active_sessions[session_id] = session_data
        await self._persist_session(session_data)
        
        logger.info(f"Created session {session_id} with {len(participants)} participants")
        return session_id
        
    async def update_session_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """Update session shared context."""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        session["shared_context"].update(context_updates)
        session["last_activity"] = datetime.now(timezone.utc)
        
        await self._persist_session(session)
        return True
        
    async def add_participant(self, session_id: str, participant_id: str) -> bool:
        """Add a participant to a session."""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        if participant_id not in session["participants"]:
            session["participants"].append(participant_id)
            session["last_activity"] = datetime.now(timezone.utc)
            await self._persist_session(session)
            
        return True
        
    async def close_session(self, session_id: str) -> bool:
        """Close a session."""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        session["closed_at"] = datetime.now(timezone.utc)
        session["status"] = "closed"
        
        await self._persist_session(session)
        del self.active_sessions[session_id]
        
        logger.info(f"Closed session {session_id}")
        return True
        
    async def _persist_session(self, session_data: Dict[str, Any]) -> None:
        """Persist session to Redis."""
        session_key = f"acp:session:{session_data['session_id']}"
        # Convert datetime objects to ISO format for JSON serialization
        session_json = json.dumps(session_data, default=str)
        await self.redis.setex(session_key, 86400, session_json)  # 24 hour TTL


# ================================
# ACP Service Manager
# ================================

class ACPService:
    """Main ACP service for workflow orchestration and session management."""
    
    def __init__(self, protocol_manager: ProtocolServiceManager, a2a_service: A2AService, mcp_service: MCPService):
        self.protocol_manager = protocol_manager
        self.redis = protocol_manager.redis
        self.a2a_service = a2a_service
        self.mcp_service = mcp_service
        
        self.workflow_engine: Optional[WorkflowEngine] = None
        self.task_delegator: Optional[TaskDelegationManager] = None
        self.session_manager: Optional[SessionManager] = None
        
    async def initialize(self) -> None:
        """Initialize the ACP service."""
        # Initialize workflow engine
        self.workflow_engine = WorkflowEngine(self.redis, self.a2a_service, self.mcp_service)
        await self.workflow_engine.initialize()
        
        # Initialize task delegation manager
        self.task_delegator = TaskDelegationManager(self.redis, self.a2a_service)
        
        # Initialize session manager
        self.session_manager = SessionManager(self.redis)
        
        # Register message handlers
        await self.protocol_manager.router.register_handler("acp:workflow_control", self._handle_workflow_control)
        await self.protocol_manager.router.register_handler("acp:task_delegation", self._handle_task_delegation)
        await self.protocol_manager.router.register_handler("acp:session_management", self._handle_session_management)
        
        logger.info("ACP service initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the ACP service."""
        if self.workflow_engine:
            await self.workflow_engine.shutdown()
        logger.info("ACP service shutdown")
        
    async def start_workflow(
        self,
        workflow_id: str,
        parameters: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """Start a new workflow."""
        if not self.workflow_engine:
            raise RuntimeError("ACP service not initialized")
            
        return await self.workflow_engine.start_workflow(workflow_id, parameters, user_id, session_id)
        
    async def delegate_task(
        self,
        task_description: str,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """Delegate a task to a suitable agent."""
        if not self.task_delegator:
            raise RuntimeError("ACP service not initialized")
            
        return await self.task_delegator.delegate_task(
            task_description, required_capabilities, task_parameters, {}, user_id
        )
        
    async def create_session(
        self,
        session_type: str,
        participants: List[str],
        initial_context: Dict[str, Any] = None
    ) -> str:
        """Create a new collaboration session."""
        if not self.session_manager:
            raise RuntimeError("ACP service not initialized")
            
        return await self.session_manager.create_session(session_type, participants, initial_context)
        
    async def _handle_workflow_control(self, message: ACPWorkflowControl) -> None:
        """Handle workflow control messages."""
        logger.info(f"Received workflow control: {message.control_operation} for {message.workflow_instance_id}")
        
        if message.control_operation == "start" and message.workflow_definition:
            # Start new workflow
            instance_id = await self.start_workflow(
                message.workflow_definition.workflow_id,
                message.execution_parameters,
                message.metadata.sender_id
            )
            logger.info(f"Started workflow instance: {instance_id}")
            
    async def _handle_task_delegation(self, message: ACPTaskDelegation) -> None:
        """Handle task delegation messages."""
        logger.info(f"Received task delegation: {message.task_description}")
        
        task_id = await self.delegate_task(
            message.task_description,
            message.required_capabilities,
            message.input_data,
            message.metadata.sender_id
        )
        
        if task_id:
            logger.info(f"Delegated task with ID: {task_id}")
            
    async def _handle_session_management(self, message: ACPSessionManagement) -> None:
        """Handle session management messages."""
        logger.info(f"Received session management: {message.session_operation} for {message.session_id}")
        
        if message.session_operation == "create":
            session_id = await self.create_session(
                message.session_type,
                message.participants,
                message.shared_context
            )
            logger.info(f"Created session: {session_id}")


# ================================
# ACP Factory
# ================================

async def create_acp_service(
    protocol_manager: ProtocolServiceManager,
    a2a_service: A2AService,
    mcp_service: MCPService
) -> ACPService:
    """Create and initialize an ACP service."""
    service = ACPService(protocol_manager, a2a_service, mcp_service)
    await service.initialize()
    return service