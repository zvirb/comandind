"""
Model Context Protocol (MCP) Service - Layer 1

Implements standardized interface for agents to access external tools, APIs, and data sources
with secure permissioned access, dynamic context retrieval, and universal tool integration.

Key Features:
- Standardized tool interface following MCP specifications
- Secure authentication and authorization for external resources
- Dynamic context acquisition for grounding agent responses
- Tool registry and discovery system
- Performance monitoring and rate limiting
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

import httpx
from pydantic import BaseModel, Field, validator
import redis.asyncio as redis

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, MCPToolRequest, MCPToolResponse, MCPCapabilityAnnouncement,
    ToolCapability, ExternalResourceSpec, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.protocol_infrastructure import ProtocolServiceManager, ProtocolConfig
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ================================
# MCP Tool Registry
# ================================

class ToolStatus(str, Enum):
    """Tool availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ToolExecutionResult(BaseModel):
    """Result of tool execution."""
    success: bool
    result: Any = None
    error_message: Optional[str] = None
    execution_time_ms: float
    tokens_consumed: Optional[int] = None
    api_calls_made: int = 0
    resources_accessed: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RegisteredTool(BaseModel):
    """Registered tool in the MCP system."""
    tool_id: str
    capability: ToolCapability
    server_id: str
    endpoint_url: str
    status: ToolStatus = ToolStatus.AVAILABLE
    
    # Performance metrics
    average_execution_time: float = 0.0
    success_rate: float = 1.0
    last_used: Optional[datetime] = None
    usage_count: int = 0
    
    # Resource management
    max_concurrent_executions: int = 5
    current_executions: int = 0
    rate_limit_per_minute: Optional[int] = None
    
    # Health monitoring
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    
    # Security context
    required_auth_scopes: List[str] = Field(default_factory=list)
    allowed_users: Optional[List[str]] = None
    resource_quotas: Dict[str, Any] = Field(default_factory=dict)


class ToolRegistry:
    """Registry for managing available tools in the MCP system."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.tools: Dict[str, RegisteredTool] = {}
        self.tool_servers: Dict[str, Dict[str, Any]] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the tool registry."""
        await self._load_registered_tools()
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Tool registry initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the tool registry."""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Tool registry shutdown")
        
    async def register_tool(self, tool: RegisteredTool) -> bool:
        """Register a new tool in the registry."""
        try:
            # Validate tool capability
            if not await self._validate_tool_capability(tool):
                logger.error(f"Tool capability validation failed for {tool.tool_id}")
                return False
                
            # Store in memory and Redis
            self.tools[tool.tool_id] = tool
            await self._persist_tool(tool)
            
            logger.info(f"Tool registered: {tool.tool_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering tool {tool.tool_id}: {e}", exc_info=True)
            return False
            
    async def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool from the registry."""
        try:
            if tool_id in self.tools:
                del self.tools[tool_id]
                await self.redis.delete(f"mcp:tool:{tool_id}")
                logger.info(f"Tool unregistered: {tool_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unregistering tool {tool_id}: {e}", exc_info=True)
            return False
            
    async def get_tool(self, tool_id: str) -> Optional[RegisteredTool]:
        """Get a registered tool by ID."""
        return self.tools.get(tool_id)
        
    async def list_tools(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[RegisteredTool]:
        """List available tools, optionally filtered."""
        tools = list(self.tools.values())
        
        if filter_criteria:
            # Apply filters
            if "status" in filter_criteria:
                tools = [t for t in tools if t.status == filter_criteria["status"]]
            if "capabilities" in filter_criteria:
                required_caps = filter_criteria["capabilities"]
                tools = [t for t in tools if any(cap in t.capability.name for cap in required_caps)]
                
        return tools
        
    async def find_tools_by_capability(self, capability_name: str) -> List[RegisteredTool]:
        """Find tools that provide a specific capability."""
        return [tool for tool in self.tools.values() 
                if capability_name.lower() in tool.capability.name.lower()]
                
    async def update_tool_status(self, tool_id: str, status: ToolStatus) -> None:
        """Update tool status."""
        if tool_id in self.tools:
            self.tools[tool_id].status = status
            await self._persist_tool(self.tools[tool_id])
            
    async def record_tool_usage(self, tool_id: str, execution_result: ToolExecutionResult) -> None:
        """Record tool usage metrics."""
        if tool_id not in self.tools:
            return
            
        tool = self.tools[tool_id]
        tool.usage_count += 1
        tool.last_used = datetime.now(timezone.utc)
        
        # Update average execution time
        if tool.usage_count == 1:
            tool.average_execution_time = execution_result.execution_time_ms
        else:
            tool.average_execution_time = (
                (tool.average_execution_time * (tool.usage_count - 1) + execution_result.execution_time_ms) 
                / tool.usage_count
            )
            
        # Update success rate
        if execution_result.success:
            tool.success_rate = (tool.success_rate * (tool.usage_count - 1) + 1.0) / tool.usage_count
        else:
            tool.success_rate = (tool.success_rate * (tool.usage_count - 1)) / tool.usage_count
            
        await self._persist_tool(tool)
        
    async def _validate_tool_capability(self, tool: RegisteredTool) -> bool:
        """Validate tool capability definition."""
        # Basic validation
        if not tool.capability.name or not tool.capability.description:
            return False
            
        # Check if parameters schema is valid
        try:
            # Could validate JSON schema here
            if tool.capability.parameters and not isinstance(tool.capability.parameters, dict):
                return False
        except Exception:
            return False
            
        return True
        
    async def _persist_tool(self, tool: RegisteredTool) -> None:
        """Persist tool definition to Redis."""
        tool_key = f"mcp:tool:{tool.tool_id}"
        await self.redis.setex(tool_key, 86400, tool.json())  # 24 hour TTL
        
    async def _load_registered_tools(self) -> None:
        """Load registered tools from Redis."""
        pattern = "mcp:tool:*"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            try:
                tool_data = await self.redis.get(key)
                if tool_data:
                    tool = RegisteredTool.parse_raw(tool_data)
                    self.tools[tool.tool_id] = tool
            except Exception as e:
                logger.error(f"Error loading tool from {key}: {e}", exc_info=True)
                
        logger.info(f"Loaded {len(self.tools)} tools from registry")
        
    async def _health_check_loop(self) -> None:
        """Periodic health check of registered tools."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered tools."""
        for tool_id, tool in self.tools.items():
            try:
                # Skip health check for internal tools
                if tool.endpoint_url.startswith("internal://"):
                    # Internal tools are always available
                    tool.status = ToolStatus.AVAILABLE
                    tool.health_check_failures = 0
                else:
                    # Simple availability check for external tools
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.head(tool.endpoint_url)
                        if response.status_code < 400:
                            tool.status = ToolStatus.AVAILABLE
                            tool.health_check_failures = 0
                        else:
                            tool.health_check_failures += 1
                            if tool.health_check_failures >= 3:
                                tool.status = ToolStatus.ERROR
                            
                tool.last_health_check = datetime.now(timezone.utc)
                await self._persist_tool(tool)
                
            except Exception as e:
                logger.error(f"Health check failed for tool {tool_id}: {e}")
                tool.health_check_failures += 1
                if tool.health_check_failures >= 3:
                    tool.status = ToolStatus.ERROR


# ================================
# MCP Tool Executor
# ================================

class ToolExecutor:
    """Executes tool requests with security, monitoring, and error handling."""
    
    def __init__(self, tool_registry: ToolRegistry, redis_client: redis.Redis):
        self.registry = tool_registry
        self.redis = redis_client
        self.active_executions: Dict[str, asyncio.Task] = {}
        
    async def execute_tool(
        self,
        tool_request: MCPToolRequest,
        user_id: str,
        authentication_context: Dict[str, Any]
    ) -> ToolExecutionResult:
        """Execute a tool request with full security and monitoring."""
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Get tool from registry
            tool = await self.registry.get_tool(tool_request.tool_name)
            if not tool:
                return ToolExecutionResult(
                    success=False,
                    error_message=f"Tool '{tool_request.tool_name}' not found",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
            # Security validation
            auth_result = await self._validate_authentication(tool, user_id, authentication_context)
            if not auth_result["valid"]:
                return ToolExecutionResult(
                    success=False,
                    error_message=f"Authentication failed: {auth_result['reason']}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
            # Check tool availability and limits
            availability_check = await self._check_tool_availability(tool, user_id)
            if not availability_check["available"]:
                return ToolExecutionResult(
                    success=False,
                    error_message=f"Tool not available: {availability_check['reason']}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
            # Update tool state
            tool.current_executions += 1
            await self.registry.update_tool_status(tool.tool_id, ToolStatus.BUSY if tool.current_executions >= tool.max_concurrent_executions else ToolStatus.AVAILABLE)
            
            try:
                # Execute the tool
                result = await self._execute_tool_implementation(tool, tool_request, authentication_context)
                
                # Record successful execution
                await self.registry.record_tool_usage(tool.tool_id, result)
                
                return result
                
            finally:
                # Update tool state
                tool.current_executions = max(0, tool.current_executions - 1)
                await self.registry.update_tool_status(tool.tool_id, ToolStatus.AVAILABLE if tool.current_executions < tool.max_concurrent_executions else ToolStatus.BUSY)
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_request.tool_name}: {e}", exc_info=True)
            return ToolExecutionResult(
                success=False,
                error_message=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
    async def _validate_authentication(
        self, 
        tool: RegisteredTool, 
        user_id: str, 
        auth_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate authentication for tool access."""
        # Check user permissions
        if tool.allowed_users and user_id not in tool.allowed_users:
            return {"valid": False, "reason": "User not authorized for this tool"}
            
        # Check required scopes
        user_scopes = auth_context.get("scopes", [])
        missing_scopes = [scope for scope in tool.required_auth_scopes if scope not in user_scopes]
        if missing_scopes:
            return {"valid": False, "reason": f"Missing required scopes: {missing_scopes}"}
            
        return {"valid": True}
        
    async def _check_tool_availability(self, tool: RegisteredTool, user_id: str) -> Dict[str, Any]:
        """Check if tool is available for execution."""
        # Check tool status
        if tool.status != ToolStatus.AVAILABLE:
            return {"available": False, "reason": f"Tool status: {tool.status.value}"}
            
        # Check concurrent execution limits
        if tool.current_executions >= tool.max_concurrent_executions:
            return {"available": False, "reason": "Maximum concurrent executions reached"}
            
        # Check rate limits
        if tool.rate_limit_per_minute:
            rate_key = f"mcp:rate_limit:{tool.tool_id}:{user_id}:{int(time.time() // 60)}"
            current_usage = await self.redis.get(rate_key) or "0"
            if int(current_usage) >= tool.rate_limit_per_minute:
                return {"available": False, "reason": "Rate limit exceeded"}
                
        return {"available": True}
        
    async def _execute_tool_implementation(
        self,
        tool: RegisteredTool,
        tool_request: MCPToolRequest,
        auth_context: Dict[str, Any]
    ) -> ToolExecutionResult:
        """Execute the actual tool implementation."""
        start_time = time.time()
        
        try:
            # Prepare execution context
            execution_context = {
                "tool_id": tool.tool_id,
                "request_id": tool_request.metadata.message_id,
                "user_context": auth_context,
                "parameters": tool_request.tool_parameters,
                "execution_preferences": {
                    "async_execution": tool_request.async_execution,
                    "streaming_response": tool_request.streaming_response,
                    "result_format": tool_request.result_format
                }
            }
            
            # Route to appropriate tool implementation
            if tool.tool_id.startswith("google_"):
                result = await self._execute_google_tool(tool, execution_context)
            elif tool.tool_id.startswith("tavily_"):
                result = await self._execute_tavily_tool(tool, execution_context)
            elif tool.tool_id.startswith("ollama_"):
                result = await self._execute_ollama_tool(tool, execution_context)
            else:
                # Generic HTTP tool execution
                result = await self._execute_http_tool(tool, execution_context)
                
            execution_time = (time.time() - start_time) * 1000
            
            return ToolExecutionResult(
                success=True,
                result=result["data"],
                execution_time_ms=execution_time,
                tokens_consumed=result.get("tokens_consumed"),
                api_calls_made=result.get("api_calls_made", 1),
                resources_accessed=result.get("resources_accessed", []),
                metadata=result.get("metadata", {})
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            
            return ToolExecutionResult(
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            
    async def _execute_google_tool(self, tool: RegisteredTool, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Google service tools (Calendar, Drive, etc.)."""
        # Import and use existing Google service implementations
        from worker.services.google_calendar_service import GoogleCalendarService
        
        if "calendar" in tool.tool_id:
            service = GoogleCalendarService()
            if "get_events" in tool.capability.name:
                events = await service.get_events(
                    user_id=context["user_context"].get("user_id"),
                    **context["parameters"]
                )
                return {
                    "data": events,
                    "api_calls_made": 1,
                    "resources_accessed": ["google_calendar"],
                    "metadata": {"service": "google_calendar"}
                }
                
        raise NotImplementedError(f"Google tool {tool.tool_id} not implemented")
        
    async def _execute_tavily_tool(self, tool: RegisteredTool, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Tavily search tools."""
        # Import and use existing Tavily implementation
        from tavily import TavilyClient
        
        if "search" in tool.capability.name:
            tavily = TavilyClient(api_key=settings.TAVILY_API_KEY.get_secret_value())
            search_result = tavily.search(
                query=context["parameters"].get("query", ""),
                search_depth=context["parameters"].get("search_depth", "basic")
            )
            return {
                "data": search_result,
                "api_calls_made": 1,
                "resources_accessed": ["tavily_search"],
                "metadata": {"service": "tavily"}
            }
            
        raise NotImplementedError(f"Tavily tool {tool.tool_id} not implemented")
        
    async def _execute_ollama_tool(self, tool: RegisteredTool, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Ollama LLM tools."""
        # Import and use existing Ollama service
        from worker.services.ollama_service import invoke_llm
        
        if "generate" in tool.capability.name:
            messages = context["parameters"].get("messages", [])
            model = context["parameters"].get("model", "llama3.2:1b")
            
            response = await invoke_llm(messages, model)
            
            return {
                "data": {"response": response},
                "tokens_consumed": len(response.split()) * 1.3,  # Rough estimate
                "api_calls_made": 1,
                "resources_accessed": ["ollama_llm"],
                "metadata": {"model": model}
            }
            
        raise NotImplementedError(f"Ollama tool {tool.tool_id} not implemented")
        
    async def _execute_http_tool(self, tool: RegisteredTool, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute generic HTTP-based tools."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                tool.endpoint_url,
                json=context,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            return {
                "data": response.json(),
                "api_calls_made": 1,
                "resources_accessed": [tool.endpoint_url],
                "metadata": {"http_status": response.status_code}
            }


# ================================
# MCP Service Manager
# ================================

class MCPService:
    """Main MCP service for managing tools and execution."""
    
    def __init__(self, protocol_manager: ProtocolServiceManager):
        self.protocol_manager = protocol_manager
        self.redis = protocol_manager.redis
        self.tool_registry: Optional[ToolRegistry] = None
        self.tool_executor: Optional[ToolExecutor] = None
        
    async def initialize(self) -> None:
        """Initialize the MCP service."""
        # Initialize tool registry
        self.tool_registry = ToolRegistry(self.redis)
        await self.tool_registry.initialize()
        
        # Initialize tool executor
        self.tool_executor = ToolExecutor(self.tool_registry, self.redis)
        
        # Register built-in tools
        await self._register_builtin_tools()
        
        # Register message handlers
        await self.protocol_manager.router.register_handler("mcp:tool_request", self._handle_tool_request)
        await self.protocol_manager.router.register_handler("mcp:capability_announcement", self._handle_capability_announcement)
        
        logger.info("MCP service initialized")
        
    async def shutdown(self) -> None:
        """Shutdown the MCP service."""
        if self.tool_registry:
            await self.tool_registry.shutdown()
        logger.info("MCP service shutdown")
        
    async def execute_tool_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        auth_context: Dict[str, Any]
    ) -> ToolExecutionResult:
        """Execute a tool request directly (internal API)."""
        if not self.tool_executor:
            raise RuntimeError("MCP service not initialized")
            
        # Create tool request message
        tool_request = MCPToolRequest(
            metadata=ProtocolMetadata(
                sender_id=f"user:{user_id}",
                sender_type="user",
                protocol_layer="mcp",
                intent=MessageIntent.REQUEST,
                authentication_token=auth_context.get("token")
            ),
            tool_name=tool_name,
            tool_parameters=parameters
        )
        
        return await self.tool_executor.execute_tool(tool_request, user_id, auth_context)
        
    async def get_available_tools(self, user_id: str) -> List[ToolCapability]:
        """Get list of available tools for a user."""
        if not self.tool_registry:
            return []
            
        tools = await self.tool_registry.list_tools({"status": "available"})
        # Filter tools based on user permissions (implement your logic)
        return [tool.capability for tool in tools]
        
    async def _handle_tool_request(self, message: MCPToolRequest) -> None:
        """Handle incoming tool request messages."""
        if not self.tool_executor:
            logger.error("Tool executor not initialized")
            return
            
        # Extract user context from message
        user_id = message.metadata.sender_id.replace("user:", "")
        auth_context = {
            "token": message.metadata.authentication_token,
            "scopes": message.metadata.permission_scope
        }
        
        # Execute tool
        result = await self.tool_executor.execute_tool(message, user_id, auth_context)
        
        # Send response
        response = MCPToolResponse(
            metadata=ProtocolMetadata(
                sender_id="mcp_service",
                sender_type="service",
                protocol_layer="mcp",
                intent=MessageIntent.INFORM,
                recipients=[message.metadata.sender_id],
                parent_message_id=message.metadata.message_id
            ),
            tool_result=result.result,
            execution_status="success" if result.success else "error",
            execution_time_ms=result.execution_time_ms,
            tokens_consumed=result.tokens_consumed,
            api_calls_made=result.api_calls_made,
            resources_accessed=result.resources_accessed
        )
        
        await self.protocol_manager.send_message(response)
        
    async def _handle_capability_announcement(self, message: MCPCapabilityAnnouncement) -> None:
        """Handle tool capability announcements from external servers."""
        if not self.tool_registry:
            return
            
        # Register announced tools
        for tool_capability in message.available_tools:
            tool = RegisteredTool(
                tool_id=f"{message.server_id}:{tool_capability.name}",
                capability=tool_capability,
                server_id=message.server_id,
                endpoint_url=f"{message.metadata.sender_id}/execute/{tool_capability.name}"
            )
            await self.tool_registry.register_tool(tool)
            
        logger.info(f"Registered {len(message.available_tools)} tools from server {message.server_id}")
        
    async def _register_builtin_tools(self) -> None:
        """Register built-in tools with the registry."""
        if not self.tool_registry:
            return
            
        # Google Calendar Tool
        calendar_tool = RegisteredTool(
            tool_id="google_calendar",
            capability=ToolCapability(
                name="google_calendar_events",
                description="Access Google Calendar events",
                parameters={
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"},
                        "calendar_id": {"type": "string", "default": "primary"}
                    }
                },
                required_permissions=["calendar.readonly"]
            ),
            server_id="builtin",
            endpoint_url="internal://google_calendar"
        )
        await self.tool_registry.register_tool(calendar_tool)
        
        # Tavily Search Tool
        search_tool = RegisteredTool(
            tool_id="tavily_search",
            capability=ToolCapability(
                name="web_search",
                description="Search the web using Tavily API",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "search_depth": {"type": "string", "enum": ["basic", "advanced"], "default": "basic"}
                    },
                    "required": ["query"]
                },
                required_permissions=["search.web"]
            ),
            server_id="builtin",
            endpoint_url="internal://tavily_search"
        )
        await self.tool_registry.register_tool(search_tool)
        
        # Ollama LLM Tool
        llm_tool = RegisteredTool(
            tool_id="ollama_generate",
            capability=ToolCapability(
                name="llm_generation",
                description="Generate text using local LLM",
                parameters={
                    "type": "object",
                    "properties": {
                        "messages": {"type": "array"},
                        "model": {"type": "string", "default": "llama3.2:1b"},
                        "temperature": {"type": "number", "default": 0.7}
                    },
                    "required": ["messages"]
                },
                required_permissions=["llm.generate"]
            ),
            server_id="builtin",
            endpoint_url="internal://ollama_generate"
        )
        await self.tool_registry.register_tool(llm_tool)
        
        logger.info("Built-in tools registered successfully")


# ================================
# MCP Factory and Configuration
# ================================

async def create_mcp_service(protocol_manager: ProtocolServiceManager) -> MCPService:
    """Create and initialize an MCP service."""
    service = MCPService(protocol_manager)
    await service.initialize()
    return service