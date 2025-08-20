"""Container State Manager for real-time container tracking."""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import docker
import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ContainerState:
    """Container state information."""
    container_id: str
    name: str
    status: str  # running, stopped, restarting, paused, dead
    health_status: str  # healthy, unhealthy, starting, none
    image: str
    created: float
    started: Optional[float]
    ports: Dict[str, Any]
    labels: Dict[str, str]
    networks: List[str]
    mounts: List[Dict[str, Any]]
    resource_usage: Dict[str, Any]
    last_updated: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ContainerOperation:
    """Container operation tracking."""
    operation_id: str
    container_id: str
    container_name: str
    operation_type: str  # restart, stop, start, update, scale, backup
    status: str  # pending, in_progress, completed, failed, cancelled
    priority: int  # 1-5, where 1 is highest
    requested_by: str  # agent or service that requested operation
    requested_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    estimated_duration: Optional[float]
    actual_duration: Optional[float]
    error_message: Optional[str]
    dependencies: List[str]  # Other operation IDs this depends on
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ContainerStateManager:
    """Manages real-time container state tracking and monitoring."""
    
    def __init__(self, config, redis_client: redis.Redis):
        self.config = config
        self.redis = redis_client
        self.docker_client = docker.from_env()
        
        # State tracking
        self.container_states: Dict[str, ContainerState] = {}
        self.container_operations: Dict[str, ContainerOperation] = {}
        self.operation_history: List[ContainerOperation] = []
        
        # Monitoring
        self.monitoring_active = False
        self.state_update_task = None
        self.cleanup_task = None
        
        # Redis keys
        self.redis_prefix = "container_coordination"
        self.states_key = f"{self.redis_prefix}:states"
        self.operations_key = f"{self.redis_prefix}:operations"
        self.history_key = f"{self.redis_prefix}:history"
        self.locks_key = f"{self.redis_prefix}:locks"
        
    async def initialize(self):
        """Initialize container state manager."""
        logger.info("Initializing Container State Manager")
        
        try:
            # Load existing state from Redis
            await self._load_state_from_redis()
            
            # Start monitoring tasks
            await self.start_monitoring()
            
            # Initial container scan
            await self._scan_all_containers()
            
            logger.info(
                "Container State Manager initialized",
                managed_containers=len(self.container_states)
            )
            
        except Exception as e:
            logger.error("Failed to initialize Container State Manager", error=str(e))
            raise
    
    async def start_monitoring(self):
        """Start container state monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        # Start state update task
        self.state_update_task = asyncio.create_task(self._state_update_loop())
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Container monitoring started")
    
    async def stop_monitoring(self):
        """Stop container state monitoring."""
        self.monitoring_active = False
        
        if self.state_update_task:
            self.state_update_task.cancel()
            try:
                await self.state_update_task
            except asyncio.CancelledError:
                pass
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Container monitoring stopped")
    
    async def get_container_state(self, container_id: str) -> Optional[ContainerState]:
        """Get current state of a container."""
        return self.container_states.get(container_id)
    
    async def get_container_by_name(self, name: str) -> Optional[ContainerState]:
        """Get container state by name."""
        for state in self.container_states.values():
            if state.name == name:
                return state
        return None
    
    async def list_managed_containers(self) -> List[ContainerState]:
        """List all managed containers."""
        return list(self.container_states.values())
    
    async def is_container_managed(self, container_name: str) -> bool:
        """Check if container is under management."""
        # Check against managed patterns
        for pattern in self.config.managed_containers:
            if self._matches_pattern(container_name, pattern):
                # Check if not excluded
                for exclude_pattern in self.config.excluded_containers:
                    if self._matches_pattern(container_name, exclude_pattern):
                        return False
                return True
        return False
    
    async def get_container_operations(self, container_id: str) -> List[ContainerOperation]:
        """Get all operations for a container."""
        return [
            op for op in self.container_operations.values()
            if op.container_id == container_id
        ]
    
    async def get_active_operations(self) -> List[ContainerOperation]:
        """Get all active operations."""
        return [
            op for op in self.container_operations.values()
            if op.status in ["pending", "in_progress"]
        ]
    
    async def register_operation(self, operation: ContainerOperation) -> bool:
        """Register a new container operation."""
        try:
            # Store operation
            self.container_operations[operation.operation_id] = operation
            
            # Persist to Redis
            await self.redis.hset(
                self.operations_key,
                operation.operation_id,
                json.dumps(operation.to_dict())
            )
            
            logger.info(
                "Operation registered",
                operation_id=operation.operation_id,
                container=operation.container_name,
                operation_type=operation.operation_type,
                priority=operation.priority
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to register operation",
                operation_id=operation.operation_id,
                error=str(e)
            )
            return False
    
    async def update_operation_status(
        self,
        operation_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """Update operation status."""
        try:
            operation = self.container_operations.get(operation_id)
            if not operation:
                logger.warning("Operation not found", operation_id=operation_id)
                return False
            
            # Update status
            operation.status = status
            if error_message:
                operation.error_message = error_message
            
            # Update timestamps
            current_time = time.time()
            if status == "in_progress" and not operation.started_at:
                operation.started_at = current_time
            elif status in ["completed", "failed", "cancelled"]:
                operation.completed_at = current_time
                if operation.started_at:
                    operation.actual_duration = current_time - operation.started_at
                
                # Move to history
                self.operation_history.append(operation)
                del self.container_operations[operation_id]
                
                # Clean up from Redis operations
                await self.redis.hdel(self.operations_key, operation_id)
                
                # Add to history in Redis
                await self.redis.lpush(
                    self.history_key,
                    json.dumps(operation.to_dict())
                )
                
                # Trim history
                await self.redis.ltrim(self.history_key, 0, 999)  # Keep last 1000
            else:
                # Update in Redis
                await self.redis.hset(
                    self.operations_key,
                    operation_id,
                    json.dumps(operation.to_dict())
                )
            
            logger.info(
                "Operation status updated",
                operation_id=operation_id,
                status=status,
                container=operation.container_name
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update operation status",
                operation_id=operation_id,
                error=str(e)
            )
            return False
    
    async def get_container_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all managed containers."""
        summary = {
            "total_containers": len(self.container_states),
            "healthy": 0,
            "unhealthy": 0,
            "starting": 0,
            "no_health_check": 0,
            "running": 0,
            "stopped": 0,
            "restarting": 0,
            "active_operations": len(self.container_operations),
            "last_updated": time.time()
        }
        
        for state in self.container_states.values():
            # Health status
            if state.health_status == "healthy":
                summary["healthy"] += 1
            elif state.health_status == "unhealthy":
                summary["unhealthy"] += 1
            elif state.health_status == "starting":
                summary["starting"] += 1
            else:
                summary["no_health_check"] += 1
            
            # Container status
            if state.status == "running":
                summary["running"] += 1
            elif state.status == "exited":
                summary["stopped"] += 1
            elif state.status == "restarting":
                summary["restarting"] += 1
        
        return summary
    
    async def _scan_all_containers(self):
        """Scan all containers and update state."""
        try:
            containers = self.docker_client.containers.list(all=True)
            current_time = time.time()
            
            for container in containers:
                if not await self.is_container_managed(container.name):
                    continue
                
                await self._update_container_state(container, current_time)
            
            # Save state to Redis
            await self._save_state_to_redis()
            
        except Exception as e:
            logger.error("Container scan failed", error=str(e))
    
    async def _update_container_state(self, container, current_time: float):
        """Update state for a single container."""
        try:
            # Get container info
            container.reload()
            attrs = container.attrs
            
            # Extract port information
            ports = {}
            if attrs.get("NetworkSettings", {}).get("Ports"):
                for container_port, host_bindings in attrs["NetworkSettings"]["Ports"].items():
                    if host_bindings:
                        ports[container_port] = host_bindings[0]["HostPort"]
            
            # Extract network information
            networks = list(attrs.get("NetworkSettings", {}).get("Networks", {}).keys())
            
            # Extract mount information
            mounts = attrs.get("Mounts", [])
            
            # Get resource usage (basic info)
            resource_usage = {
                "memory_limit": attrs.get("HostConfig", {}).get("Memory", 0),
                "cpu_limit": attrs.get("HostConfig", {}).get("CpuQuota", 0)
            }
            
            # Determine health status
            health_status = "none"
            if attrs.get("State", {}).get("Health"):
                health_status = attrs["State"]["Health"]["Status"]
            
            # Create or update container state
            state = ContainerState(
                container_id=container.id,
                name=container.name,
                status=container.status,
                health_status=health_status,
                image=attrs["Config"]["Image"],
                created=datetime.fromisoformat(
                    attrs["Created"].replace("Z", "+00:00")
                ).timestamp(),
                started=datetime.fromisoformat(
                    attrs["State"]["StartedAt"].replace("Z", "+00:00")
                ).timestamp() if attrs["State"]["StartedAt"] != "0001-01-01T00:00:00Z" else None,
                ports=ports,
                labels=attrs["Config"].get("Labels", {}),
                networks=networks,
                mounts=mounts,
                resource_usage=resource_usage,
                last_updated=current_time
            )
            
            self.container_states[container.id] = state
            
        except Exception as e:
            logger.error(
                "Failed to update container state",
                container_id=container.id,
                container_name=container.name,
                error=str(e)
            )
    
    async def _state_update_loop(self):
        """Continuous state update loop."""
        while self.monitoring_active:
            try:
                await self._scan_all_containers()
                await asyncio.sleep(self.config.state_update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("State update loop error", error=str(e))
                await asyncio.sleep(self.config.state_update_interval)
    
    async def _cleanup_loop(self):
        """Cleanup old operations and states."""
        while self.monitoring_active:
            try:
                current_time = time.time()
                cutoff_time = current_time - self.config.operation_history_retention
                
                # Clean up operation history
                self.operation_history = [
                    op for op in self.operation_history
                    if op.completed_at and op.completed_at > cutoff_time
                ]
                
                # Clean up Redis history
                await self._cleanup_redis_history(cutoff_time)
                
                # Wait for next cleanup cycle
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup loop error", error=str(e))
                await asyncio.sleep(3600)
    
    async def _cleanup_redis_history(self, cutoff_time: float):
        """Clean up old entries from Redis history."""
        try:
            # Get all history entries
            history_entries = await self.redis.lrange(self.history_key, 0, -1)
            
            # Filter out old entries
            valid_entries = []
            for entry in history_entries:
                try:
                    operation_data = json.loads(entry)
                    if operation_data.get("completed_at", 0) > cutoff_time:
                        valid_entries.append(entry)
                except json.JSONDecodeError:
                    continue
            
            # Replace history with valid entries
            if len(valid_entries) != len(history_entries):
                await self.redis.delete(self.history_key)
                if valid_entries:
                    await self.redis.lpush(self.history_key, *valid_entries)
                
                logger.info(
                    "Cleaned up operation history",
                    removed_count=len(history_entries) - len(valid_entries),
                    remaining_count=len(valid_entries)
                )
                
        except Exception as e:
            logger.error("Redis history cleanup failed", error=str(e))
    
    async def _save_state_to_redis(self):
        """Save current state to Redis."""
        try:
            # Save container states
            state_data = {
                container_id: json.dumps(state.to_dict())
                for container_id, state in self.container_states.items()
            }
            
            if state_data:
                await self.redis.hset(self.states_key, mapping=state_data)
            
        except Exception as e:
            logger.error("Failed to save state to Redis", error=str(e))
    
    async def _load_state_from_redis(self):
        """Load state from Redis."""
        try:
            # Load container states
            state_data = await self.redis.hgetall(self.states_key)
            for container_id, state_json in state_data.items():
                try:
                    state_dict = json.loads(state_json)
                    state = ContainerState(**state_dict)
                    self.container_states[container_id] = state
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        "Failed to load container state",
                        container_id=container_id,
                        error=str(e)
                    )
            
            # Load active operations
            operations_data = await self.redis.hgetall(self.operations_key)
            for operation_id, operation_json in operations_data.items():
                try:
                    operation_dict = json.loads(operation_json)
                    operation = ContainerOperation(**operation_dict)
                    self.container_operations[operation_id] = operation
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        "Failed to load operation",
                        operation_id=operation_id,
                        error=str(e)
                    )
            
            logger.info(
                "State loaded from Redis",
                containers=len(self.container_states),
                active_operations=len(self.container_operations)
            )
            
        except Exception as e:
            logger.error("Failed to load state from Redis", error=str(e))
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if container name matches pattern."""
        import fnmatch
        return fnmatch.fnmatch(name, pattern)
    
    async def shutdown(self):
        """Shutdown container state manager."""
        logger.info("Shutting down Container State Manager")
        
        await self.stop_monitoring()
        
        # Save final state
        await self._save_state_to_redis()
        
        # Close Docker client
        if hasattr(self.docker_client, 'close'):
            self.docker_client.close()
        
        logger.info("Container State Manager shutdown complete")