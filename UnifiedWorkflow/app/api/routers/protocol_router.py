"""
Protocol Stack API Router

FastAPI router for the three-layer communication protocol stack, providing
HTTP and WebSocket endpoints for protocol message handling, agent registration,
tool execution, and workflow orchestration.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import redis.asyncio as redis

from api.dependencies import get_current_user
from shared.database.models import User
from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, MCPToolRequest, A2ADirectMessage, ACPWorkflowControl,
    MessageIntent, MessagePriority, ProtocolMetadata, AgentProfile, ToolCapability
)
from shared.services.protocol_infrastructure import ProtocolServiceManager, ProtocolFactory
from shared.services.mcp_service import create_mcp_service
from shared.services.a2a_service import create_a2a_service
from shared.services.acp_service import create_acp_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Global protocol services (initialized in main.py lifespan)
protocol_manager: Optional[ProtocolServiceManager] = None
mcp_service = None
a2a_service = None
acp_service = None


# ================================
# Request/Response Models
# ================================

class ToolExecutionRequest(BaseModel):
    """Request to execute a tool via MCP."""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_context: Dict[str, Any] = Field(default_factory=dict)
    async_execution: bool = True
    streaming_response: bool = False


class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    result: Any = None
    error_message: Optional[str] = None
    execution_time_ms: float
    tokens_consumed: Optional[int] = None
    api_calls_made: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentRegistrationRequest(BaseModel):
    """Request to register an agent."""
    agent_profile: AgentProfile
    connection_endpoint: str
    connection_type: str = "redis"


class DirectMessageRequest(BaseModel):
    """Request to send direct message to an agent."""
    target_agent_id: str
    message_content: str
    conversation_id: Optional[str] = None
    expects_response: bool = False


class WorkflowStartRequest(BaseModel):
    """Request to start a workflow."""
    workflow_id: str
    execution_parameters: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class TaskDelegationRequest(BaseModel):
    """Request to delegate a task."""
    task_description: str
    required_capabilities: List[str]
    task_parameters: Dict[str, Any] = Field(default_factory=dict)
    selection_criteria: Dict[str, Any] = Field(default_factory=dict)


class AgentDiscoveryRequest(BaseModel):
    """Request to discover agents."""
    required_capabilities: Optional[List[str]] = None
    domain: Optional[str] = None
    agent_type: Optional[str] = None
    selection_criteria: Dict[str, Any] = Field(default_factory=dict)


# ================================
# Protocol Service Initialization
# ================================

async def initialize_protocol_services(redis_client: redis.Redis) -> None:
    """Initialize protocol services (called from main.py lifespan)."""
    global protocol_manager, mcp_service, a2a_service, acp_service
    
    try:
        # Create protocol service manager
        protocol_manager = await ProtocolFactory.create_service_manager()
        protocol_manager.redis = redis_client
        
        # Initialize MCP service
        mcp_service = await create_mcp_service(protocol_manager)
        
        # Initialize A2A service
        a2a_service = await create_a2a_service(protocol_manager)
        
        # Initialize ACP service
        acp_service = await create_acp_service(protocol_manager, a2a_service, mcp_service)
        
        logger.info("Protocol services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize protocol services: {e}", exc_info=True)
        raise


async def shutdown_protocol_services() -> None:
    """Shutdown protocol services (called from main.py lifespan)."""
    global protocol_manager, mcp_service, a2a_service, acp_service
    
    try:
        if acp_service:
            await acp_service.shutdown()
        if a2a_service:
            await a2a_service.shutdown()
        if mcp_service:
            await mcp_service.shutdown()
        if protocol_manager:
            await protocol_manager.shutdown()
            
        logger.info("Protocol services shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during protocol services shutdown: {e}", exc_info=True)


def get_protocol_services():
    """Get protocol services dependency."""
    if not protocol_manager or not mcp_service or not a2a_service or not acp_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol services not initialized"
        )
    return {
        "protocol_manager": protocol_manager,
        "mcp_service": mcp_service,
        "a2a_service": a2a_service,
        "acp_service": acp_service
    }


# ================================
# MCP Endpoints
# ================================

@router.get("/mcp/tools", response_model=List[ToolCapability])
async def list_available_tools(
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """List available tools in the MCP system."""
    try:
        tools = await services["mcp_service"].get_available_tools(str(current_user.id))
        return tools
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available tools"
        )


@router.post("/mcp/tools/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Execute a tool via the MCP system."""
    try:
        # Create authentication context
        auth_context = {
            "user_id": str(current_user.id),
            "email": current_user.email,
            "scopes": ["tool.execute"]  # Add appropriate scopes based on user role
        }
        
        # Execute tool
        result = await services["mcp_service"].execute_tool_request(
            tool_name=request.tool_name,
            parameters=request.parameters,
            user_id=str(current_user.id),
            auth_context=auth_context
        )
        
        return ToolExecutionResponse(
            success=result.success,
            result=result.result,
            error_message=result.error_message,
            execution_time_ms=result.execution_time_ms,
            tokens_consumed=result.tokens_consumed,
            api_calls_made=result.api_calls_made,
            metadata=result.metadata
        )
        
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.post("/mcp/tools/execute/stream")
async def execute_tool_streaming(
    request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Execute a tool with streaming response."""
    
    async def stream_tool_execution():
        try:
            # Create authentication context
            auth_context = {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "scopes": ["tool.execute"]
            }
            
            # For streaming, we'll execute the tool and yield progress updates
            yield f"data: {json.dumps({'type': 'start', 'tool_name': request.tool_name})}\n\n"
            
            # Execute tool
            result = await services["mcp_service"].execute_tool_request(
                tool_name=request.tool_name,
                parameters=request.parameters,
                user_id=str(current_user.id),
                auth_context=auth_context
            )
            
            # Yield final result
            yield f"data: {json.dumps({'type': 'result', 'data': result.dict()})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_tool_execution(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ================================
# A2A Endpoints
# ================================

@router.post("/a2a/agents/register")
async def register_agent(
    request: AgentRegistrationRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Register an agent in the A2A system."""
    try:
        success = await services["a2a_service"].register_agent(
            request.agent_profile,
            request.connection_endpoint
        )
        
        if success:
            return {"message": "Agent registered successfully", "agent_id": request.agent_profile.agent_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to register agent"
            )
            
    except Exception as e:
        logger.error(f"Error registering agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent registration failed: {str(e)}"
        )


@router.post("/a2a/messages/send")
async def send_direct_message(
    request: DirectMessageRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Send a direct message to another agent."""
    try:
        success = await services["a2a_service"].send_message(
            sender_id=f"user:{current_user.id}",
            target_agent_id=request.target_agent_id,
            message_content=request.message_content,
            conversation_id=request.conversation_id
        )
        
        if success:
            return {"message": "Message sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send message"
            )
            
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Message send failed: {str(e)}"
        )


@router.post("/a2a/agents/discover", response_model=List[AgentProfile])
async def discover_agents(
    request: AgentDiscoveryRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Discover agents matching specific criteria."""
    try:
        agents = await services["a2a_service"].find_agents(
            required_capabilities=request.required_capabilities or [],
            domain=request.domain,
            selection_criteria=request.selection_criteria
        )
        
        return agents
        
    except Exception as e:
        logger.error(f"Error discovering agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent discovery failed: {str(e)}"
        )


@router.post("/a2a/capabilities/negotiate")
async def negotiate_capability(
    required_capabilities: List[str],
    task_parameters: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Initiate capability negotiation with agents."""
    try:
        result = await services["a2a_service"].negotiate_capability(
            requester_id=f"user:{current_user.id}",
            required_capabilities=required_capabilities,
            task_parameters=task_parameters
        )
        
        if result:
            negotiation_id, agent_id = result
            return {
                "negotiation_id": negotiation_id,
                "selected_agent_id": agent_id,
                "status": "negotiation_started"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No suitable agents found for capability negotiation"
            )
            
    except Exception as e:
        logger.error(f"Error in capability negotiation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Capability negotiation failed: {str(e)}"
        )


# ================================
# ACP Endpoints
# ================================

@router.post("/acp/workflows/start")
async def start_workflow(
    request: WorkflowStartRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Start a new workflow."""
    try:
        instance_id = await services["acp_service"].start_workflow(
            workflow_id=request.workflow_id,
            parameters=request.execution_parameters,
            user_id=str(current_user.id),
            session_id=request.session_id
        )
        
        return {
            "workflow_instance_id": instance_id,
            "status": "started",
            "message": "Workflow started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow start failed: {str(e)}"
        )


@router.get("/acp/workflows/{instance_id}/status")
async def get_workflow_status(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Get workflow status and progress."""
    try:
        if not services["acp_service"].workflow_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow engine not available"
            )
            
        status_info = await services["acp_service"].workflow_engine.get_workflow_status(instance_id)
        
        if status_info:
            return status_info
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow instance not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workflow status: {str(e)}"
        )


@router.post("/acp/workflows/{instance_id}/control")
async def control_workflow(
    instance_id: str,
    action: str,  # "pause", "resume", "abort"
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Control workflow execution (pause, resume, abort)."""
    try:
        workflow_engine = services["acp_service"].workflow_engine
        if not workflow_engine:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow engine not available"
            )
        
        if action == "pause":
            success = await workflow_engine.pause_workflow(instance_id)
        elif action == "resume":
            success = await workflow_engine.resume_workflow(instance_id)
        elif action == "abort":
            success = await workflow_engine.abort_workflow(instance_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}"
            )
            
        if success:
            return {"message": f"Workflow {action} successful"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow instance not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow control failed: {str(e)}"
        )


@router.post("/acp/tasks/delegate")
async def delegate_task(
    request: TaskDelegationRequest,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Delegate a task to a suitable agent."""
    try:
        task_id = await services["acp_service"].delegate_task(
            task_description=request.task_description,
            required_capabilities=request.required_capabilities,
            task_parameters=request.task_parameters,
            user_id=str(current_user.id)
        )
        
        if task_id:
            return {
                "task_id": task_id,
                "status": "delegated",
                "message": "Task delegated successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No suitable agent found for task delegation"
            )
            
    except Exception as e:
        logger.error(f"Error delegating task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task delegation failed: {str(e)}"
        )


@router.post("/acp/sessions/create")
async def create_session(
    session_type: str,
    participants: List[str],
    initial_context: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Create a new collaboration session."""
    try:
        session_id = await services["acp_service"].create_session(
            session_type=session_type,
            participants=participants,
            initial_context=initial_context or {}
        )
        
        return {
            "session_id": session_id,
            "session_type": session_type,
            "participants": participants,
            "message": "Session created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {str(e)}"
        )


# ================================
# WebSocket Endpoints
# ================================

@router.websocket("/ws/protocol/{protocol_layer}")
async def protocol_websocket(
    websocket: WebSocket,
    protocol_layer: str,  # "mcp", "a2a", "acp"
    token: str = Query(...),
    services: Dict = Depends(get_protocol_services)
):
    """WebSocket endpoint for real-time protocol communication."""
    try:
        # Authenticate user (reuse existing WebSocket auth logic)
        from api.routers.websocket_router import authenticate_websocket
        user_id = await authenticate_websocket(token)
        
        await websocket.accept()
        logger.info(f"Protocol WebSocket connection established for layer {protocol_layer}, user {user_id}")
        
        # Create session for this connection
        session_id = str(uuid.uuid4())
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process based on protocol layer
                if protocol_layer == "mcp":
                    await handle_mcp_websocket_message(websocket, message_data, user_id, services)
                elif protocol_layer == "a2a":
                    await handle_a2a_websocket_message(websocket, message_data, user_id, services)
                elif protocol_layer == "acp":
                    await handle_acp_websocket_message(websocket, message_data, user_id, services)
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unsupported protocol layer: {protocol_layer}"
                    }))
                    
        except WebSocketDisconnect:
            logger.info(f"Protocol WebSocket client disconnected from {protocol_layer}")
        except Exception as e:
            logger.error(f"Error in protocol WebSocket: {e}", exc_info=True)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            
    except Exception as e:
        logger.error(f"Protocol WebSocket authentication failed: {e}", exc_info=True)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)


async def handle_mcp_websocket_message(
    websocket: WebSocket,
    message_data: Dict[str, Any],
    user_id: int,
    services: Dict
):
    """Handle MCP WebSocket messages."""
    try:
        message_type = message_data.get("type")
        
        if message_type == "tool_execute":
            # Execute tool and stream progress
            tool_name = message_data.get("tool_name")
            parameters = message_data.get("parameters", {})
            
            auth_context = {
                "user_id": str(user_id),
                "scopes": ["tool.execute"]
            }
            
            # Send start notification
            await websocket.send_text(json.dumps({
                "type": "tool_execution_start",
                "tool_name": tool_name
            }))
            
            # Execute tool
            result = await services["mcp_service"].execute_tool_request(
                tool_name=tool_name,
                parameters=parameters,
                user_id=str(user_id),
                auth_context=auth_context
            )
            
            # Send result
            await websocket.send_text(json.dumps({
                "type": "tool_execution_result",
                "result": result.dict()
            }))
            
        elif message_type == "list_tools":
            # Get available tools
            tools = await services["mcp_service"].get_available_tools(str(user_id))
            await websocket.send_text(json.dumps({
                "type": "tools_list",
                "tools": [tool.dict() for tool in tools]
            }))
            
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))


async def handle_a2a_websocket_message(
    websocket: WebSocket,
    message_data: Dict[str, Any],
    user_id: int,
    services: Dict
):
    """Handle A2A WebSocket messages."""
    try:
        message_type = message_data.get("type")
        
        if message_type == "send_message":
            # Send direct message to agent
            target_agent_id = message_data.get("target_agent_id")
            message_content = message_data.get("message_content")
            
            success = await services["a2a_service"].send_message(
                sender_id=f"user:{user_id}",
                target_agent_id=target_agent_id,
                message_content=message_content
            )
            
            await websocket.send_text(json.dumps({
                "type": "message_sent",
                "success": success
            }))
            
        elif message_type == "discover_agents":
            # Discover available agents
            capabilities = message_data.get("required_capabilities", [])
            domain = message_data.get("domain")
            
            agents = await services["a2a_service"].find_agents(
                required_capabilities=capabilities,
                domain=domain
            )
            
            await websocket.send_text(json.dumps({
                "type": "agents_discovered",
                "agents": [agent.dict() for agent in agents]
            }))
            
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))


async def handle_acp_websocket_message(
    websocket: WebSocket,
    message_data: Dict[str, Any],
    user_id: int,
    services: Dict
):
    """Handle ACP WebSocket messages."""
    try:
        message_type = message_data.get("type")
        
        if message_type == "start_workflow":
            # Start workflow
            workflow_id = message_data.get("workflow_id")
            parameters = message_data.get("parameters", {})
            
            instance_id = await services["acp_service"].start_workflow(
                workflow_id=workflow_id,
                parameters=parameters,
                user_id=str(user_id)
            )
            
            await websocket.send_text(json.dumps({
                "type": "workflow_started",
                "instance_id": instance_id
            }))
            
        elif message_type == "get_workflow_status":
            # Get workflow status
            instance_id = message_data.get("instance_id")
            
            status_info = await services["acp_service"].workflow_engine.get_workflow_status(instance_id)
            
            await websocket.send_text(json.dumps({
                "type": "workflow_status",
                "status": status_info
            }))
            
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))


# ================================
# Health and Status Endpoints
# ================================

@router.get("/protocol/health")
async def protocol_health_check(services: Dict = Depends(get_protocol_services)):
    """Check health of all protocol services."""
    try:
        health_status = {
            "protocol_manager": "healthy",
            "mcp_service": "healthy",
            "a2a_service": "healthy",
            "acp_service": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Could add more detailed health checks here
        
        return health_status
        
    except Exception as e:
        logger.error(f"Protocol health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol services unhealthy"
        )


@router.get("/protocol/metrics")
async def get_protocol_metrics(
    current_user: User = Depends(get_current_user),
    services: Dict = Depends(get_protocol_services)
):
    """Get protocol performance metrics."""
    try:
        # Get metrics from protocol manager
        if hasattr(services["protocol_manager"], "metrics_collector") and services["protocol_manager"].metrics_collector:
            metrics = await services["protocol_manager"].metrics_collector.get_metrics_summary()
            return metrics
        else:
            return {"message": "Metrics collection not enabled"}
            
    except Exception as e:
        logger.error(f"Error retrieving protocol metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )