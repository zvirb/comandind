"""
Protocol Worker Service

Integrates the three-layer communication protocol stack with Celery worker services,
enabling agents to communicate via MCP, A2A, and ACP protocols within the worker context.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

import redis.asyncio as redis
from celery import Celery

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, MCPToolRequest, A2ADirectMessage, ACPTaskDelegation,
    AgentProfile, AgentCapability, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.protocol_infrastructure import ProtocolServiceManager, ProtocolConfig
from shared.services.mcp_service import create_mcp_service
from shared.services.a2a_service import create_a2a_service
from shared.services.acp_service import create_acp_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global protocol services for worker
worker_protocol_manager: Optional[ProtocolServiceManager] = None
worker_mcp_service = None
worker_a2a_service = None
worker_acp_service = None


# ================================
# Protocol Worker Integration
# ================================

class ProtocolWorkerService:
    """Integrates protocol stack with Celery worker services."""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.protocol_manager: Optional[ProtocolServiceManager] = None
        self.mcp_service = None
        self.a2a_service = None
        self.acp_service = None
        self.registered_agents: Dict[str, AgentProfile] = {}
        self.message_queue_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize protocol services for worker."""
        global worker_protocol_manager, worker_mcp_service, worker_a2a_service, worker_acp_service
        
        try:
            # Create Redis connection
            redis_client = redis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True
            )
            
            # Create protocol service manager
            config = ProtocolConfig()
            self.protocol_manager = ProtocolServiceManager(config)
            self.protocol_manager.redis = redis_client
            await self.protocol_manager.initialize()
            
            # Initialize protocol services
            self.mcp_service = await create_mcp_service(self.protocol_manager)
            self.a2a_service = await create_a2a_service(self.protocol_manager)
            self.acp_service = await create_acp_service(self.protocol_manager, self.a2a_service, self.mcp_service)
            
            # Set global references
            worker_protocol_manager = self.protocol_manager
            worker_mcp_service = self.mcp_service
            worker_a2a_service = self.a2a_service
            worker_acp_service = self.acp_service
            
            # Start message processing
            self.message_queue_task = asyncio.create_task(self._process_message_queue())
            
            # Register built-in worker agents
            await self._register_worker_agents()
            
            logger.info("Protocol worker service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize protocol worker service: {e}", exc_info=True)
            raise
            
    async def shutdown(self) -> None:
        """Shutdown protocol services."""
        try:
            if self.message_queue_task:
                self.message_queue_task.cancel()
                try:
                    await self.message_queue_task
                except asyncio.CancelledError:
                    pass
                    
            if self.acp_service:
                await self.acp_service.shutdown()
            if self.a2a_service:
                await self.a2a_service.shutdown()
            if self.mcp_service:
                await self.mcp_service.shutdown()
            if self.protocol_manager:
                await self.protocol_manager.shutdown()
                
            logger.info("Protocol worker service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during protocol worker service shutdown: {e}", exc_info=True)
            
    async def register_agent(self, agent_profile: AgentProfile) -> bool:
        """Register a worker agent with the protocol system."""
        try:
            if not self.a2a_service:
                logger.error("A2A service not initialized")
                return False
                
            # Register with A2A service
            connection_endpoint = f"redis://worker_queue_{agent_profile.agent_id}"
            success = await self.a2a_service.register_agent(agent_profile, connection_endpoint)
            
            if success:
                self.registered_agents[agent_profile.agent_id] = agent_profile
                logger.info(f"Registered worker agent: {agent_profile.agent_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error registering worker agent: {e}", exc_info=True)
            return False
            
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        auth_context: Dict[str, Any]
    ) -> Any:
        """Execute a tool via MCP from worker context."""
        try:
            if not self.mcp_service:
                raise RuntimeError("MCP service not initialized")
                
            result = await self.mcp_service.execute_tool_request(
                tool_name=tool_name,
                parameters=parameters,
                user_id=user_id,
                auth_context=auth_context
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            raise
            
    async def send_agent_message(
        self,
        sender_agent_id: str,
        target_agent_id: str,
        message_content: str,
        conversation_id: Optional[str] = None
    ) -> bool:
        """Send message from one agent to another."""
        try:
            if not self.a2a_service:
                logger.error("A2A service not initialized")
                return False
                
            return await self.a2a_service.send_message(
                sender_id=sender_agent_id,
                target_agent_id=target_agent_id,
                message_content=message_content,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Error sending agent message: {e}", exc_info=True)
            return False
            
    async def delegate_task_to_agent(
        self,
        task_description: str,
        required_capabilities: List[str],
        task_parameters: Dict[str, Any],
        requester_id: str
    ) -> Optional[str]:
        """Delegate a task to another agent via ACP."""
        try:
            if not self.acp_service:
                logger.error("ACP service not initialized")
                return None
                
            return await self.acp_service.delegate_task(
                task_description=task_description,
                required_capabilities=required_capabilities,
                task_parameters=task_parameters,
                user_id=requester_id
            )
            
        except Exception as e:
            logger.error(f"Error delegating task: {e}", exc_info=True)
            return None
            
    async def _process_message_queue(self) -> None:
        """Process incoming protocol messages for worker agents."""
        while True:
            try:
                # Check for messages for each registered agent
                for agent_id in self.registered_agents.keys():
                    queue_key = f"a2a:queue:{agent_id}"
                    
                    if self.protocol_manager and self.protocol_manager.redis:
                        # Get message from queue
                        message_data = await self.protocol_manager.redis.rpop(queue_key)
                        
                        if message_data:
                            try:
                                message = json.loads(message_data)
                                await self._handle_agent_message(agent_id, message)
                            except Exception as e:
                                logger.error(f"Error processing message for agent {agent_id}: {e}", exc_info=True)
                                
                await asyncio.sleep(1)  # Check every second
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message queue processing: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
                
    async def _handle_agent_message(self, agent_id: str, message_data: Dict[str, Any]) -> None:
        """Handle incoming message for a specific agent."""
        try:
            message_type = message_data.get("message_type", message_data.get("@type"))
            
            if message_type == "a2a:direct_message":
                await self._handle_direct_message(agent_id, message_data)
            elif message_type == "acp:task_delegation":
                await self._handle_task_delegation(agent_id, message_data)
            elif message_type == "mcp:tool_request":
                await self._handle_tool_request(agent_id, message_data)
            else:
                logger.warning(f"Unknown message type for agent {agent_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message for agent {agent_id}: {e}", exc_info=True)
            
    async def _handle_direct_message(self, agent_id: str, message_data: Dict[str, Any]) -> None:
        """Handle direct message to agent."""
        try:
            message_content = message_data.get("message_content", "")
            sender_id = message_data.get("metadata", {}).get("sender_id", "unknown")
            
            logger.info(f"Agent {agent_id} received direct message from {sender_id}: {message_content}")
            
            # For now, just log the message
            # In production, route to appropriate agent handler
            
        except Exception as e:
            logger.error(f"Error handling direct message for agent {agent_id}: {e}", exc_info=True)
            
    async def _handle_task_delegation(self, agent_id: str, message_data: Dict[str, Any]) -> None:
        """Handle task delegation to agent."""
        try:
            task_description = message_data.get("task_description", "")
            task_parameters = message_data.get("input_data", {})
            
            logger.info(f"Agent {agent_id} received task delegation: {task_description}")
            
            # Queue Celery task for this agent
            task_name = f"agent_task_{agent_id}"
            
            # Create task parameters
            celery_task_params = {
                "agent_id": agent_id,
                "task_description": task_description,
                "task_parameters": task_parameters,
                "message_data": message_data
            }
            
            # Send to appropriate Celery task based on agent type
            agent_profile = self.registered_agents.get(agent_id)
            if agent_profile:
                if "research_specialist" in agent_profile.agent_type:
                    self.celery_app.send_task("tasks.research_specialist_task", args=[celery_task_params])
                elif "personal_assistant" in agent_profile.agent_type:
                    self.celery_app.send_task("tasks.personal_assistant_task", args=[celery_task_params])
                elif "project_manager" in agent_profile.agent_type:
                    self.celery_app.send_task("tasks.project_manager_task", args=[celery_task_params])
                else:
                    self.celery_app.send_task("tasks.generic_agent_task", args=[celery_task_params])
            else:
                logger.warning(f"Unknown agent type for {agent_id}, using generic task")
                self.celery_app.send_task("tasks.generic_agent_task", args=[celery_task_params])
                
        except Exception as e:
            logger.error(f"Error handling task delegation for agent {agent_id}: {e}", exc_info=True)
            
    async def _handle_tool_request(self, agent_id: str, message_data: Dict[str, Any]) -> None:
        """Handle tool request for agent."""
        try:
            tool_name = message_data.get("tool_name", "")
            tool_parameters = message_data.get("tool_parameters", {})
            
            logger.info(f"Agent {agent_id} received tool request: {tool_name}")
            
            # Execute tool request
            if self.mcp_service:
                # Create basic auth context for agent
                auth_context = {
                    "agent_id": agent_id,
                    "scopes": ["tool.execute"]
                }
                
                result = await self.mcp_service.execute_tool_request(
                    tool_name=tool_name,
                    parameters=tool_parameters,
                    user_id=agent_id,
                    auth_context=auth_context
                )
                
                # Send result back (implement response mechanism)
                logger.info(f"Tool execution result for agent {agent_id}: {result.success}")
                
        except Exception as e:
            logger.error(f"Error handling tool request for agent {agent_id}: {e}", exc_info=True)
            
    async def _register_worker_agents(self) -> None:
        """Register built-in worker agents."""
        try:
            # Research Specialist Agent
            research_agent = AgentProfile(
                agent_id="research_specialist_worker",
                agent_name="Research Specialist Worker",
                agent_type="research_specialist",
                version="1.0",
                capabilities=[
                    AgentCapability(
                        capability_id="web_search",
                        name="Web Search",
                        description="Search the web for information using Tavily API",
                        input_types=["text/query"],
                        output_types=["application/json"],
                        confidence_level=0.9
                    ),
                    AgentCapability(
                        capability_id="research_analysis",
                        name="Research Analysis",
                        description="Analyze and synthesize research findings",
                        input_types=["application/json"],
                        output_types=["text/markdown"],
                        confidence_level=0.85
                    )
                ],
                supported_domains=["research", "information_gathering", "web_search"],
                availability_status="available"
            )
            await self.register_agent(research_agent)
            
            # Personal Assistant Agent
            assistant_agent = AgentProfile(
                agent_id="personal_assistant_worker",
                agent_name="Personal Assistant Worker",
                agent_type="personal_assistant",
                version="1.0",
                capabilities=[
                    AgentCapability(
                        capability_id="calendar_management",
                        name="Calendar Management",
                        description="Manage Google Calendar events and scheduling",
                        input_types=["application/json"],
                        output_types=["application/json"],
                        confidence_level=0.95
                    ),
                    AgentCapability(
                        capability_id="email_processing",
                        name="Email Processing",
                        description="Process and manage emails",
                        input_types=["text/email"],
                        output_types=["application/json"],
                        confidence_level=0.9
                    )
                ],
                supported_domains=["productivity", "scheduling", "communication"],
                availability_status="available"
            )
            await self.register_agent(assistant_agent)
            
            # Project Manager Agent
            pm_agent = AgentProfile(
                agent_id="project_manager_worker",
                agent_name="Project Manager Worker",
                agent_type="project_manager",
                version="1.0",
                capabilities=[
                    AgentCapability(
                        capability_id="task_coordination",
                        name="Task Coordination",
                        description="Coordinate tasks across multiple agents",
                        input_types=["application/json"],
                        output_types=["application/json"],
                        confidence_level=0.9
                    ),
                    AgentCapability(
                        capability_id="workflow_management",
                        name="Workflow Management",
                        description="Manage complex multi-step workflows",
                        input_types=["application/json"],
                        output_types=["application/json"],
                        confidence_level=0.85
                    )
                ],
                supported_domains=["project_management", "coordination", "workflow"],
                availability_status="available"
            )
            await self.register_agent(pm_agent)
            
            logger.info("Registered built-in worker agents successfully")
            
        except Exception as e:
            logger.error(f"Error registering worker agents: {e}", exc_info=True)


# ================================
# Global Protocol Worker Instance
# ================================

protocol_worker_service: Optional[ProtocolWorkerService] = None


async def initialize_protocol_worker(celery_app: Celery) -> None:
    """Initialize protocol worker service."""
    global protocol_worker_service
    
    try:
        protocol_worker_service = ProtocolWorkerService(celery_app)
        await protocol_worker_service.initialize()
        logger.info("Protocol worker initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize protocol worker: {e}", exc_info=True)
        raise


async def shutdown_protocol_worker() -> None:
    """Shutdown protocol worker service."""
    global protocol_worker_service
    
    if protocol_worker_service:
        await protocol_worker_service.shutdown()
        protocol_worker_service = None
        logger.info("Protocol worker shutdown completed")


def get_protocol_worker() -> Optional[ProtocolWorkerService]:
    """Get the global protocol worker service instance."""
    return protocol_worker_service


# ================================
# Protocol-Aware Celery Tasks
# ================================

def protocol_tool_execution_task(
    tool_name: str,
    parameters: Dict[str, Any],
    user_id: str,
    auth_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Celery task for executing tools via MCP protocol."""
    async def execute_tool():
        worker = get_protocol_worker()
        if not worker:
            raise RuntimeError("Protocol worker not initialized")
            
        result = await worker.execute_tool(tool_name, parameters, user_id, auth_context)
        return result.dict()
        
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(execute_tool())
    finally:
        loop.close()


def protocol_agent_communication_task(
    sender_agent_id: str,
    target_agent_id: str,
    message_content: str,
    conversation_id: Optional[str] = None
) -> bool:
    """Celery task for agent-to-agent communication."""
    async def send_message():
        worker = get_protocol_worker()
        if not worker:
            raise RuntimeError("Protocol worker not initialized")
            
        return await worker.send_agent_message(
            sender_agent_id, target_agent_id, message_content, conversation_id
        )
        
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(send_message())
    finally:
        loop.close()


def protocol_task_delegation_task(
    task_description: str,
    required_capabilities: List[str],
    task_parameters: Dict[str, Any],
    requester_id: str
) -> Optional[str]:
    """Celery task for task delegation via ACP protocol."""
    async def delegate_task():
        worker = get_protocol_worker()
        if not worker:
            raise RuntimeError("Protocol worker not initialized")
            
        return await worker.delegate_task_to_agent(
            task_description, required_capabilities, task_parameters, requester_id
        )
        
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(delegate_task())
    finally:
        loop.close()


# ================================
# Integration Utilities
# ================================

def integrate_with_existing_services():
    """Integration hooks for existing worker services."""
    # This function can be called to enhance existing services with protocol capabilities
    
    # Example: Enhance existing Google Calendar service with MCP protocol
    from worker.services.google_calendar_service import GoogleCalendarService
    
    class ProtocolEnabledGoogleCalendarService(GoogleCalendarService):
        """Google Calendar service enhanced with protocol support."""
        
        async def get_events_via_protocol(self, user_id: str, **kwargs) -> Dict[str, Any]:
            """Get calendar events via MCP protocol."""
            worker = get_protocol_worker()
            if not worker:
                # Fallback to direct service call
                return await super().get_events(user_id, **kwargs)
                
            # Use MCP protocol for tool execution
            auth_context = {"user_id": user_id, "scopes": ["calendar.readonly"]}
            result = await worker.execute_tool(
                tool_name="google_calendar",
                parameters={"user_id": user_id, **kwargs},
                user_id=user_id,
                auth_context=auth_context
            )
            
            return result.result if result.success else None
            
    return ProtocolEnabledGoogleCalendarService