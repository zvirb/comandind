"""
MCP Tool Registry Service - Centralized Tool Discovery and Management

Implements a centralized registry for MCP-compliant tool servers with:
- Dynamic tool discovery and capability management
- Service health monitoring and load balancing
- OAuth Resource Server integration for tool access control
- Performance metrics collection and optimization
- Fault tolerance and automatic failover
- Tool versioning and compatibility management

This service acts as the central hub for all MCP tool servers in the AI Workflow Engine,
providing intelligent routing, load balancing, and monitoring capabilities while maintaining
compatibility with the existing LangGraph Smart Router architecture.
"""

import asyncio
import json
import logging
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from pydantic import BaseModel, Field, validator
import httpx
import redis.asyncio as redis

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, MCPToolRequest, MCPToolResponse, MCPCapabilityAnnouncement,
    ToolCapability, MessageIntent, MessagePriority, ProtocolMetadata
)
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service
from shared.services.protocol_infrastructure import ProtocolServiceManager
from worker.services.mcp_calendar_server import MCPCalendarServer, create_mcp_calendar_server
from worker.services.mcp_task_server import MCPTaskServer, create_mcp_task_server
from worker.services.mcp_email_server import MCPEmailServer, create_mcp_email_server

logger = logging.getLogger(__name__)


# ================================
# MCP Registry Data Models
# ================================

class ToolServerStatus(str, Enum):
    """Tool server availability status."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies for tool servers."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_RESPONSE_TIME = "weighted_response_time"
    RESOURCE_BASED = "resource_based"


class ToolServerInstance(BaseModel):
    """Represents a single tool server instance."""
    server_id: str
    server_name: str
    server_version: str
    endpoint_url: str
    status: ToolServerStatus = ToolServerStatus.OFFLINE
    
    # Capabilities
    available_tools: List[ToolCapability] = Field(default_factory=list)
    supported_features: List[str] = Field(default_factory=list)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    # Health and Performance Metrics
    last_health_check: Optional[datetime] = None
    health_check_failures: int = 0
    average_response_time_ms: float = 0.0
    success_rate: float = 1.0
    current_connections: int = 0
    max_connections: int = 100
    
    # Load balancing metrics
    total_requests: int = 0
    requests_per_minute: int = 0
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    
    # Registration info
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Security
    authentication_required: bool = True
    allowed_scopes: List[str] = Field(default_factory=list)
    rate_limit_per_minute: Optional[int] = None


class ToolDiscoveryEntry(BaseModel):
    """Tool discovery index entry."""
    tool_name: str
    tool_description: str
    server_instances: List[str] = Field(default_factory=list)  # server_ids
    tool_category: str = ""
    security_level: str = "medium"
    required_permissions: List[str] = Field(default_factory=list)
    average_execution_time_ms: float = 0.0
    success_rate: float = 1.0
    popularity_score: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolExecutionMetrics(BaseModel):
    """Tool execution performance metrics."""
    tool_name: str
    server_id: str
    execution_count: int = 0
    total_execution_time_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    average_response_time_ms: float = 0.0
    last_execution: Optional[datetime] = None
    error_types: Dict[str, int] = Field(default_factory=dict)


class RegistryConfiguration(BaseModel):
    """Configuration for the MCP Registry Service."""
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 10
    max_health_check_failures: int = 3
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.WEIGHTED_RESPONSE_TIME
    enable_auto_discovery: bool = True
    enable_failover: bool = True
    metrics_retention_days: int = 30
    cache_ttl_seconds: int = 300
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_seconds: int = 60


# ================================
# Tool Server Discovery and Management
# ================================

class ToolServerDiscovery:
    """Handles discovery and registration of MCP tool servers."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.discovered_servers: Dict[str, ToolServerInstance] = {}
        
    async def discover_builtin_servers(self) -> List[ToolServerInstance]:
        """Discover built-in MCP tool servers."""
        
        builtin_servers = []
        
        try:
            # Calendar Server
            calendar_server = await create_mcp_calendar_server()
            calendar_capabilities = calendar_server.get_server_capabilities()
            
            calendar_instance = ToolServerInstance(
                server_id="builtin_calendar_server",
                server_name=calendar_capabilities.server_name,
                server_version=calendar_capabilities.server_version,
                endpoint_url="internal://calendar",
                status=ToolServerStatus.ONLINE,
                available_tools=calendar_capabilities.available_tools,
                supported_features=calendar_capabilities.supported_features,
                resource_requirements=calendar_capabilities.resource_requirements,
                allowed_scopes=calendar_capabilities.resource_requirements.get("permissions", [])
            )
            builtin_servers.append(calendar_instance)
            
            # Task Server
            task_server = await create_mcp_task_server()
            task_capabilities = task_server.get_server_capabilities()
            
            task_instance = ToolServerInstance(
                server_id="builtin_task_server",
                server_name=task_capabilities.server_name,
                server_version=task_capabilities.server_version,
                endpoint_url="internal://task",
                status=ToolServerStatus.ONLINE,
                available_tools=task_capabilities.available_tools,
                supported_features=task_capabilities.supported_features,
                resource_requirements=task_capabilities.resource_requirements,
                allowed_scopes=task_capabilities.resource_requirements.get("permissions", [])
            )
            builtin_servers.append(task_instance)
            
            # Email Server
            email_server = await create_mcp_email_server()
            email_capabilities = email_server.get_server_capabilities()
            
            email_instance = ToolServerInstance(
                server_id="builtin_email_server",
                server_name=email_capabilities.server_name,
                server_version=email_capabilities.server_version,
                endpoint_url="internal://email",
                status=ToolServerStatus.ONLINE,
                available_tools=email_capabilities.available_tools,
                supported_features=email_capabilities.supported_features,
                resource_requirements=email_capabilities.resource_requirements,
                allowed_scopes=email_capabilities.resource_requirements.get("permissions", [])
            )
            builtin_servers.append(email_instance)
            
            logger.info(f"Discovered {len(builtin_servers)} built-in MCP tool servers")
            
        except Exception as e:
            logger.error(f"Error discovering built-in servers: {e}", exc_info=True)
        
        return builtin_servers
    
    async def register_external_server(self, announcement: MCPCapabilityAnnouncement) -> bool:
        """Register an external MCP tool server."""
        
        try:
            server_instance = ToolServerInstance(
                server_id=announcement.server_id,
                server_name=announcement.server_name,
                server_version=announcement.server_version,
                endpoint_url=announcement.metadata.sender_id,
                available_tools=announcement.available_tools,
                supported_features=announcement.supported_features,
                resource_requirements=announcement.resource_requirements,
                status=ToolServerStatus.ONLINE
            )
            
            # Store in registry
            await self._persist_server_instance(server_instance)
            self.discovered_servers[announcement.server_id] = server_instance
            
            logger.info(f"Registered external MCP server: {announcement.server_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering external server: {e}", exc_info=True)
            return False
    
    async def _persist_server_instance(self, instance: ToolServerInstance) -> None:
        """Persist server instance to Redis."""
        key = f"mcp:registry:server:{instance.server_id}"
        await self.redis.setex(key, 86400, instance.json())  # 24 hour TTL


# ================================
# Tool Index and Search
# ================================

class ToolIndexManager:
    """Manages the searchable index of available tools."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.tool_index: Dict[str, ToolDiscoveryEntry] = {}
        
    async def build_tool_index(self, server_instances: List[ToolServerInstance]) -> None:
        """Build searchable index from available tool servers."""
        
        self.tool_index.clear()
        
        for server in server_instances:
            for tool_capability in server.available_tools:
                tool_name = tool_capability.name
                
                if tool_name not in self.tool_index:
                    # Create new index entry
                    self.tool_index[tool_name] = ToolDiscoveryEntry(
                        tool_name=tool_name,
                        tool_description=tool_capability.description,
                        server_instances=[server.server_id],
                        security_level=tool_capability.security_level,
                        required_permissions=tool_capability.required_permissions
                    )
                else:
                    # Add server to existing entry
                    entry = self.tool_index[tool_name]
                    if server.server_id not in entry.server_instances:
                        entry.server_instances.append(server.server_id)
        
        # Persist index to Redis
        await self._persist_tool_index()
        
        logger.info(f"Built tool index with {len(self.tool_index)} tools")
    
    async def search_tools(
        self,
        query: str = "",
        category: str = "",
        required_permissions: List[str] = None,
        max_response_time_ms: Optional[float] = None
    ) -> List[ToolDiscoveryEntry]:
        """Search for tools based on criteria."""
        
        results = []
        query_lower = query.lower()
        required_permissions = required_permissions or []
        
        for tool_name, entry in self.tool_index.items():
            # Text search
            if query and query_lower not in tool_name.lower() and query_lower not in entry.tool_description.lower():
                continue
            
            # Category filter
            if category and category.lower() != entry.tool_category.lower():
                continue
            
            # Permission filter
            if required_permissions:
                if not all(perm in entry.required_permissions for perm in required_permissions):
                    continue
            
            # Performance filter
            if max_response_time_ms and entry.average_execution_time_ms > max_response_time_ms:
                continue
            
            results.append(entry)
        
        # Sort by popularity and performance
        results.sort(key=lambda x: (x.popularity_score, -x.average_execution_time_ms), reverse=True)
        
        return results
    
    async def get_tool_by_name(self, tool_name: str) -> Optional[ToolDiscoveryEntry]:
        """Get tool entry by exact name."""
        return self.tool_index.get(tool_name)
    
    async def update_tool_metrics(self, tool_name: str, metrics: ToolExecutionMetrics) -> None:
        """Update tool performance metrics in the index."""
        
        if tool_name in self.tool_index:
            entry = self.tool_index[tool_name]
            entry.average_execution_time_ms = metrics.average_response_time_ms
            entry.success_rate = metrics.success_count / max(metrics.execution_count, 1)
            entry.last_updated = datetime.now(timezone.utc)
            
            # Update popularity score based on usage
            entry.popularity_score = min(100.0, metrics.execution_count * 0.1)
            
            await self._persist_tool_index()
    
    async def _persist_tool_index(self) -> None:
        """Persist tool index to Redis."""
        index_data = {name: entry.dict() for name, entry in self.tool_index.items()}
        await self.redis.setex("mcp:registry:tool_index", 3600, json.dumps(index_data))


# ================================
# Load Balancing and Routing
# ================================

class ToolLoadBalancer:
    """Handles load balancing and routing for tool execution requests."""
    
    def __init__(self, redis_client: redis.Redis, config: RegistryConfiguration):
        self.redis = redis_client
        self.config = config
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
    async def select_best_server(
        self,
        tool_name: str,
        available_servers: List[ToolServerInstance],
        user_requirements: Dict[str, Any] = None
    ) -> Optional[ToolServerInstance]:
        """Select the best server for tool execution based on load balancing strategy."""
        
        if not available_servers:
            return None
        
        # Filter servers by health and circuit breaker status
        healthy_servers = []
        for server in available_servers:
            if await self._is_server_healthy(server):
                healthy_servers.append(server)
        
        if not healthy_servers:
            logger.warning(f"No healthy servers available for tool: {tool_name}")
            return None
        
        # Apply load balancing strategy
        if self.config.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._round_robin_selection(tool_name, healthy_servers)
        elif self.config.load_balancing_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_selection(healthy_servers)
        elif self.config.load_balancing_strategy == LoadBalancingStrategy.WEIGHTED_RESPONSE_TIME:
            return await self._weighted_response_time_selection(healthy_servers)
        elif self.config.load_balancing_strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return await self._resource_based_selection(healthy_servers)
        else:
            # Default to least connections
            return await self._least_connections_selection(healthy_servers)
    
    async def _is_server_healthy(self, server: ToolServerInstance) -> bool:
        """Check if a server is healthy and not circuit broken."""
        
        # Check basic health status
        if server.status not in [ToolServerStatus.ONLINE, ToolServerStatus.DEGRADED]:
            return False
        
        # Check circuit breaker
        if self.config.enable_circuit_breaker:
            breaker_key = f"{server.server_id}:{server.endpoint_url}"
            if breaker_key in self.circuit_breakers:
                breaker = self.circuit_breakers[breaker_key]
                if breaker["state"] == "open":
                    # Check if recovery timeout has passed
                    if datetime.now(timezone.utc) > breaker["recovery_time"]:
                        breaker["state"] = "half_open"
                        logger.info(f"Circuit breaker for {server.server_id} moved to half-open state")
                    else:
                        return False
        
        # Check connection limits
        if server.current_connections >= server.max_connections:
            return False
        
        return True
    
    async def _round_robin_selection(self, tool_name: str, servers: List[ToolServerInstance]) -> ToolServerInstance:
        """Round-robin server selection."""
        
        # Get current round-robin index from Redis
        key = f"mcp:registry:rr_index:{tool_name}"
        current_index = await self.redis.get(key)
        current_index = int(current_index) if current_index else 0
        
        # Select server and update index
        selected_server = servers[current_index % len(servers)]
        next_index = (current_index + 1) % len(servers)
        await self.redis.setex(key, 300, str(next_index))  # 5 minute TTL
        
        return selected_server
    
    async def _least_connections_selection(self, servers: List[ToolServerInstance]) -> ToolServerInstance:
        """Select server with least connections."""
        return min(servers, key=lambda s: s.current_connections)
    
    async def _weighted_response_time_selection(self, servers: List[ToolServerInstance]) -> ToolServerInstance:
        """Select server based on weighted response time and success rate."""
        
        best_server = None
        best_score = float('inf')
        
        for server in servers:
            # Calculate weighted score (lower is better)
            # Factor in response time, success rate, and current load
            response_weight = server.average_response_time_ms
            load_weight = (server.current_connections / server.max_connections) * 1000
            success_penalty = (1.0 - server.success_rate) * 1000
            
            score = response_weight + load_weight + success_penalty
            
            if score < best_score:
                best_score = score
                best_server = server
        
        return best_server
    
    async def _resource_based_selection(self, servers: List[ToolServerInstance]) -> ToolServerInstance:
        """Select server based on resource utilization."""
        
        best_server = None
        best_score = float('inf')
        
        for server in servers:
            # Calculate resource utilization score (lower is better)
            cpu_score = server.cpu_usage_percent
            memory_score = server.memory_usage_percent
            connection_score = (server.current_connections / server.max_connections) * 100
            
            total_score = (cpu_score + memory_score + connection_score) / 3
            
            if total_score < best_score:
                best_score = total_score
                best_server = server
        
        return best_server
    
    async def record_execution_result(
        self,
        server: ToolServerInstance,
        tool_name: str,
        success: bool,
        response_time_ms: float,
        error_type: str = None
    ) -> None:
        """Record execution result for load balancing and circuit breaker logic."""
        
        # Update server metrics
        server.total_requests += 1
        server.last_seen = datetime.now(timezone.utc)
        
        if success:
            # Update response time (exponential moving average)
            if server.average_response_time_ms == 0:
                server.average_response_time_ms = response_time_ms
            else:
                server.average_response_time_ms = (
                    server.average_response_time_ms * 0.8 + response_time_ms * 0.2
                )
            
            # Update success rate
            total_executions = server.total_requests
            success_count = int(server.success_rate * (total_executions - 1)) + 1
            server.success_rate = success_count / total_executions
            
        else:
            # Handle failure
            total_executions = server.total_requests
            success_count = int(server.success_rate * (total_executions - 1))
            server.success_rate = success_count / total_executions
            
            # Update circuit breaker
            if self.config.enable_circuit_breaker:
                await self._update_circuit_breaker(server, success=False, error_type=error_type)
        
        # Update circuit breaker on success too
        if self.config.enable_circuit_breaker and success:
            await self._update_circuit_breaker(server, success=True)
    
    async def _update_circuit_breaker(
        self,
        server: ToolServerInstance,
        success: bool,
        error_type: str = None
    ) -> None:
        """Update circuit breaker state based on execution result."""
        
        breaker_key = f"{server.server_id}:{server.endpoint_url}"
        
        if breaker_key not in self.circuit_breakers:
            self.circuit_breakers[breaker_key] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "recovery_time": None
            }
        
        breaker = self.circuit_breakers[breaker_key]
        
        if success:
            if breaker["state"] == "half_open":
                # Success in half-open state - close the breaker
                breaker["state"] = "closed"
                breaker["failure_count"] = 0
                logger.info(f"Circuit breaker for {server.server_id} closed after successful execution")
            elif breaker["state"] == "closed":
                # Reset failure count on success
                breaker["failure_count"] = max(0, breaker["failure_count"] - 1)
        else:
            # Failure
            breaker["failure_count"] += 1
            breaker["last_failure_time"] = datetime.now(timezone.utc)
            
            if breaker["failure_count"] >= self.config.circuit_breaker_failure_threshold:
                # Open the circuit breaker
                breaker["state"] = "open"
                breaker["recovery_time"] = datetime.now(timezone.utc) + timedelta(
                    seconds=self.config.circuit_breaker_recovery_timeout_seconds
                )
                logger.warning(f"Circuit breaker for {server.server_id} opened after {breaker['failure_count']} failures")


# ================================
# Health Monitoring
# ================================

class HealthMonitor:
    """Monitors health of registered tool servers."""
    
    def __init__(self, redis_client: redis.Redis, config: RegistryConfiguration):
        self.redis = redis_client
        self.config = config
        self.health_check_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self, server_instances: Dict[str, ToolServerInstance]) -> None:
        """Start health monitoring for all servers."""
        
        self.server_instances = server_instances
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def _health_check_loop(self) -> None:
        """Main health check loop."""
        
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered servers."""
        
        health_check_tasks = []
        
        for server_id, server in self.server_instances.items():
            if server.status != ToolServerStatus.MAINTENANCE:
                task = asyncio.create_task(self._check_server_health(server))
                health_check_tasks.append(task)
        
        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)
    
    async def _check_server_health(self, server: ToolServerInstance) -> None:
        """Check health of a single server."""
        
        try:
            if server.endpoint_url.startswith("internal://"):
                # Built-in server - always healthy
                server.status = ToolServerStatus.ONLINE
                server.health_check_failures = 0
                server.last_health_check = datetime.now(timezone.utc)
                return
            
            # External server - perform HTTP health check
            async with httpx.AsyncClient(timeout=self.config.health_check_timeout_seconds) as client:
                response = await client.get(f"{server.endpoint_url}/health")
                
                if response.status_code == 200:
                    # Healthy response
                    server.status = ToolServerStatus.ONLINE
                    server.health_check_failures = 0
                    
                    # Update metrics if provided
                    if response.headers.get("content-type") == "application/json":
                        health_data = response.json()
                        server.cpu_usage_percent = health_data.get("cpu_usage_percent", 0.0)
                        server.memory_usage_percent = health_data.get("memory_usage_percent", 0.0)
                        server.current_connections = health_data.get("current_connections", 0)
                    
                else:
                    # Unhealthy response
                    await self._handle_health_check_failure(server, f"HTTP {response.status_code}")
                    
        except Exception as e:
            await self._handle_health_check_failure(server, str(e))
        
        finally:
            server.last_health_check = datetime.now(timezone.utc)
    
    async def _handle_health_check_failure(self, server: ToolServerInstance, error: str) -> None:
        """Handle health check failure."""
        
        server.health_check_failures += 1
        
        if server.health_check_failures >= self.config.max_health_check_failures:
            server.status = ToolServerStatus.ERROR
            logger.warning(f"Server {server.server_id} marked as ERROR after {server.health_check_failures} failures")
        elif server.health_check_failures >= 1:
            server.status = ToolServerStatus.DEGRADED
            logger.warning(f"Server {server.server_id} marked as DEGRADED after health check failure: {error}")


# ================================
# Main MCP Registry Service
# ================================

class MCPRegistryService:
    """Main MCP Registry Service for centralized tool discovery and management."""
    
    def __init__(self, redis_client: redis.Redis, config: RegistryConfiguration = None):
        self.redis = redis_client
        self.config = config or RegistryConfiguration()
        
        # Core components
        self.discovery = ToolServerDiscovery(redis_client)
        self.index_manager = ToolIndexManager(redis_client)
        self.load_balancer = ToolLoadBalancer(redis_client, self.config)
        self.health_monitor = HealthMonitor(redis_client, self.config)
        
        # State
        self.server_instances: Dict[str, ToolServerInstance] = {}
        self.metrics_store: Dict[str, ToolExecutionMetrics] = {}
        
        # Built-in server references
        self.builtin_servers: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize the MCP Registry Service."""
        
        logger.info("Initializing MCP Registry Service")
        
        # Discover and register built-in servers
        builtin_servers = await self.discovery.discover_builtin_servers()
        for server in builtin_servers:
            self.server_instances[server.server_id] = server
            
            # Store built-in server instances for direct execution
            if server.server_id == "builtin_calendar_server":
                self.builtin_servers["calendar"] = await create_mcp_calendar_server()
            elif server.server_id == "builtin_task_server":
                self.builtin_servers["task"] = await create_mcp_task_server()
            elif server.server_id == "builtin_email_server":
                self.builtin_servers["email"] = await create_mcp_email_server()
        
        # Build tool index
        await self.index_manager.build_tool_index(list(self.server_instances.values()))
        
        # Start health monitoring
        await self.health_monitor.start_monitoring(self.server_instances)
        
        logger.info(f"MCP Registry Service initialized with {len(self.server_instances)} servers")
    
    async def shutdown(self) -> None:
        """Shutdown the MCP Registry Service."""
        
        await self.health_monitor.stop_monitoring()
        logger.info("MCP Registry Service shutdown complete")
    
    async def register_external_server(self, announcement: MCPCapabilityAnnouncement) -> bool:
        """Register an external MCP tool server."""
        
        success = await self.discovery.register_external_server(announcement)
        if success:
            # Rebuild tool index
            await self.index_manager.build_tool_index(list(self.server_instances.values()))
        
        return success
    
    async def discover_tools(
        self,
        query: str = "",
        category: str = "",
        user_permissions: List[str] = None
    ) -> List[ToolDiscoveryEntry]:
        """Discover available tools based on search criteria."""
        
        return await self.index_manager.search_tools(
            query=query,
            category=category,
            required_permissions=user_permissions
        )
    
    async def execute_tool_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        authentication_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool request through the registry with load balancing."""
        
        start_time = time.time()
        
        try:
            # Find tool in index
            tool_entry = await self.index_manager.get_tool_by_name(tool_name)
            if not tool_entry:
                raise ValueError(f"Tool not found: {tool_name}")
            
            # Get available servers for this tool
            available_servers = [
                self.server_instances[server_id] 
                for server_id in tool_entry.server_instances 
                if server_id in self.server_instances
            ]
            
            if not available_servers:
                raise RuntimeError(f"No available servers for tool: {tool_name}")
            
            # Select best server using load balancing
            selected_server = await self.load_balancer.select_best_server(
                tool_name, available_servers
            )
            
            if not selected_server:
                raise RuntimeError(f"No healthy servers available for tool: {tool_name}")
            
            # Execute the tool request
            result = await self._execute_on_server(
                selected_server, tool_name, parameters, user_id, authentication_context
            )
            
            # Record successful execution
            execution_time_ms = (time.time() - start_time) * 1000
            await self.load_balancer.record_execution_result(
                selected_server, tool_name, True, execution_time_ms
            )
            
            # Update metrics
            await self._update_execution_metrics(
                tool_name, selected_server.server_id, True, execution_time_ms
            )
            
            # Log successful execution
            await security_audit_service.log_security_event(
                user_id=user_id,
                event_type="mcp_tool_execution_success",
                details={
                    "tool_name": tool_name,
                    "server_id": selected_server.server_id,
                    "execution_time_ms": execution_time_ms
                }
            )
            
            return {
                "success": True,
                "result": result,
                "server_id": selected_server.server_id,
                "execution_time_ms": execution_time_ms
            }
            
        except Exception as e:
            # Record failed execution
            execution_time_ms = (time.time() - start_time) * 1000
            
            if 'selected_server' in locals():
                await self.load_balancer.record_execution_result(
                    selected_server, tool_name, False, execution_time_ms, str(e)
                )
                
                await self._update_execution_metrics(
                    tool_name, selected_server.server_id, False, execution_time_ms, str(e)
                )
            
            # Log failed execution
            await security_audit_service.log_security_event(
                user_id=user_id,
                event_type="mcp_tool_execution_failure",
                details={
                    "tool_name": tool_name,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms
                }
            )
            
            logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": execution_time_ms
            }
    
    async def _execute_on_server(
        self,
        server: ToolServerInstance,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        authentication_context: Dict[str, Any]
    ) -> Any:
        """Execute tool request on a specific server."""
        
        if server.endpoint_url.startswith("internal://"):
            # Built-in server - direct execution
            return await self._execute_builtin_tool(
                server, tool_name, parameters, user_id, authentication_context
            )
        else:
            # External server - HTTP request
            return await self._execute_external_tool(
                server, tool_name, parameters, user_id, authentication_context
            )
    
    async def _execute_builtin_tool(
        self,
        server: ToolServerInstance,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        authentication_context: Dict[str, Any]
    ) -> Any:
        """Execute tool on built-in server."""
        
        # Create MCP tool request
        request = MCPToolRequest(
            metadata=ProtocolMetadata(
                sender_id=f"user:{user_id}",
                sender_type="user",
                protocol_layer="mcp",
                intent=MessageIntent.REQUEST,
                authentication_token=authentication_context.get("token")
            ),
            tool_name=tool_name,
            tool_parameters=parameters
        )
        
        # Route to appropriate built-in server
        if server.server_id == "builtin_calendar_server":
            response = await self.builtin_servers["calendar"].handle_tool_request(request)
        elif server.server_id == "builtin_task_server":
            response = await self.builtin_servers["task"].handle_tool_request(request)
        elif server.server_id == "builtin_email_server":
            response = await self.builtin_servers["email"].handle_tool_request(request)
        else:
            raise ValueError(f"Unknown built-in server: {server.server_id}")
        
        if not response.success:
            raise RuntimeError(response.error_message)
        
        return response.result
    
    async def _execute_external_tool(
        self,
        server: ToolServerInstance,
        tool_name: str,
        parameters: Dict[str, Any],
        user_id: str,
        authentication_context: Dict[str, Any]
    ) -> Any:
        """Execute tool on external server via HTTP."""
        
        request_data = {
            "tool_name": tool_name,
            "parameters": parameters,
            "user_id": user_id,
            "authentication_context": authentication_context
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{server.endpoint_url}/execute",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {authentication_context.get('token', '')}"
                }
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            if not result_data.get("success", False):
                raise RuntimeError(result_data.get("error", "Unknown external server error"))
            
            return result_data.get("result")
    
    async def _update_execution_metrics(
        self,
        tool_name: str,
        server_id: str,
        success: bool,
        execution_time_ms: float,
        error_type: str = None
    ) -> None:
        """Update execution metrics for analytics."""
        
        metrics_key = f"{tool_name}:{server_id}"
        
        if metrics_key not in self.metrics_store:
            self.metrics_store[metrics_key] = ToolExecutionMetrics(
                tool_name=tool_name,
                server_id=server_id
            )
        
        metrics = self.metrics_store[metrics_key]
        metrics.execution_count += 1
        metrics.total_execution_time_ms += execution_time_ms
        metrics.last_execution = datetime.now(timezone.utc)
        
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
            if error_type:
                metrics.error_types[error_type] = metrics.error_types.get(error_type, 0) + 1
        
        # Calculate average response time
        metrics.average_response_time_ms = (
            metrics.total_execution_time_ms / metrics.execution_count
        )
        
        # Update tool index with new metrics
        await self.index_manager.update_tool_metrics(tool_name, metrics)
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """Get comprehensive registry status and metrics."""
        
        total_servers = len(self.server_instances)
        online_servers = sum(1 for s in self.server_instances.values() if s.status == ToolServerStatus.ONLINE)
        total_tools = len(self.index_manager.tool_index)
        
        # Calculate aggregate metrics
        total_executions = sum(m.execution_count for m in self.metrics_store.values())
        total_successes = sum(m.success_count for m in self.metrics_store.values())
        overall_success_rate = total_successes / max(total_executions, 1)
        
        # Get top tools by usage
        top_tools = sorted(
            self.metrics_store.values(),
            key=lambda m: m.execution_count,
            reverse=True
        )[:10]
        
        return {
            "registry_info": {
                "total_servers": total_servers,
                "online_servers": online_servers,
                "total_tools": total_tools,
                "health_check_interval": self.config.health_check_interval_seconds,
                "load_balancing_strategy": self.config.load_balancing_strategy.value
            },
            "performance_metrics": {
                "total_executions": total_executions,
                "overall_success_rate": round(overall_success_rate, 3),
                "avg_response_time_ms": sum(m.average_response_time_ms for m in self.metrics_store.values()) / max(len(self.metrics_store), 1)
            },
            "server_status": [
                {
                    "server_id": server.server_id,
                    "server_name": server.server_name,
                    "status": server.status.value,
                    "current_connections": server.current_connections,
                    "success_rate": round(server.success_rate, 3),
                    "avg_response_time_ms": round(server.average_response_time_ms, 2),
                    "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None
                }
                for server in self.server_instances.values()
            ],
            "top_tools": [
                {
                    "tool_name": m.tool_name,
                    "server_id": m.server_id,
                    "execution_count": m.execution_count,
                    "success_rate": round(m.success_count / max(m.execution_count, 1), 3),
                    "avg_response_time_ms": round(m.average_response_time_ms, 2)
                }
                for m in top_tools
            ]
        }


# ================================
# Factory and Initialization
# ================================

# Global registry instance
_mcp_registry_service: Optional[MCPRegistryService] = None

async def create_mcp_registry_service(redis_client: redis.Redis, config: RegistryConfiguration = None) -> MCPRegistryService:
    """Create and initialize the MCP Registry Service."""
    
    global _mcp_registry_service
    
    if _mcp_registry_service is None:
        _mcp_registry_service = MCPRegistryService(redis_client, config)
        await _mcp_registry_service.initialize()
        logger.info("MCP Registry Service created and initialized")
    
    return _mcp_registry_service

async def get_mcp_registry_service() -> Optional[MCPRegistryService]:
    """Get the global MCP Registry Service instance."""
    return _mcp_registry_service