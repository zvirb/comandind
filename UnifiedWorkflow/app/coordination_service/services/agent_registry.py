"""Agent Registry with capability-based routing and dynamic discovery.

This module manages the registry of 47+ specialist agents, their capabilities,
current status, and provides intelligent routing based on workload and performance.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

import asyncpg
import structlog

from config import AGENT_CAPABILITIES

logger = structlog.get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent status states."""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    name: str
    category: str
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.UNKNOWN
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    current_workload: int = 0
    max_concurrent: int = 1
    last_seen: float = field(default_factory=time.time)
    endpoint_url: Optional[str] = None
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        return (
            self.status in [AgentStatus.AVAILABLE, AgentStatus.BUSY] and
            self.current_workload < self.max_concurrent
        )
    
    @property
    def utilization_rate(self) -> float:
        """Get current utilization rate (0.0 to 1.0)."""
        if self.max_concurrent == 0:
            return 1.0
        return min(1.0, self.current_workload / self.max_concurrent)
    
    @property
    def priority_score(self) -> float:
        """Calculate priority score for routing (higher = better)."""
        # Base score from performance
        base_score = self.performance_metrics.get("success_rate", 0.5)
        
        # Adjust for current workload
        workload_penalty = self.utilization_rate * 0.3
        
        # Adjust for response time
        response_time = self.performance_metrics.get("avg_response_time", 300)
        response_score = max(0, 1.0 - (response_time / 600))  # Penalty after 10min
        
        return base_score + response_score - workload_penalty
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "category": self.category,
            "capabilities": self.capabilities,
            "status": self.status,
            "resource_requirements": self.resource_requirements,
            "performance_metrics": self.performance_metrics,
            "current_workload": self.current_workload,
            "max_concurrent": self.max_concurrent,
            "last_seen": self.last_seen,
            "endpoint_url": self.endpoint_url,
            "version": self.version,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentInfo':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            category=data["category"],
            capabilities=data.get("capabilities", []),
            status=AgentStatus(data.get("status", "unknown")),
            resource_requirements=data.get("resource_requirements", {}),
            performance_metrics=data.get("performance_metrics", {}),
            current_workload=data.get("current_workload", 0),
            max_concurrent=data.get("max_concurrent", 1),
            last_seen=data.get("last_seen", time.time()),
            endpoint_url=data.get("endpoint_url"),
            version=data.get("version", "1.0.0"),
            metadata=data.get("metadata", {})
        )


class AgentRegistry:
    """Registry for managing agent discovery, capabilities, and routing."""
    
    def __init__(
        self,
        database_url: str,
        redis_service,
        heartbeat_interval: int = 30,
        offline_threshold: int = 120,
        discovery_enabled: bool = True
    ):
        self.database_url = database_url
        self.redis_service = redis_service
        self.heartbeat_interval = heartbeat_interval
        self.offline_threshold = offline_threshold
        self.discovery_enabled = discovery_enabled
        
        # Database connection pool
        self._db_pool: Optional[asyncpg.Pool] = None
        
        # In-memory registry
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_index: Dict[str, Set[str]] = {}  # capability -> agent names
        self._category_index: Dict[str, Set[str]] = {}   # category -> agent names
        
        # Registry locks
        self._registry_lock = asyncio.Lock()
        self._discovery_running = False
        
        # Performance tracking
        self.registry_metrics = {
            "total_agents": 0,
            "available_agents": 0,
            "discovered_agents": 0,
            "routing_requests": 0,
            "successful_routes": 0,
            "avg_routing_time": 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize the agent registry."""
        logger.info("Initializing Agent Registry...")
        
        # Initialize database connection
        self._db_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=8,
            command_timeout=30
        )
        
        # Ensure database schema
        await self._ensure_database_schema()
        
        # Load agents from configuration
        await self._load_configured_agents()
        
        # Load persisted agents from database
        await self._load_persisted_agents()
        
        # Start discovery and heartbeat processes
        if self.discovery_enabled:
            asyncio.create_task(self._run_discovery_loop())
        
        asyncio.create_task(self._run_heartbeat_loop())
        
        logger.info(
            "Agent Registry initialized",
            total_agents=len(self._agents),
            discovery_enabled=self.discovery_enabled
        )
    
    async def register_agent(
        self,
        agent_info: Dict[str, Any],
        update_if_exists: bool = True
    ) -> bool:
        """Register or update an agent in the registry."""
        async with self._registry_lock:
            try:
                agent_name = agent_info["name"]
                
                logger.info("Registering agent", agent_name=agent_name)
                
                # Create or update agent info
                if agent_name in self._agents and not update_if_exists:
                    logger.warning("Agent already exists", agent_name=agent_name)
                    return False
                
                # Create agent info object
                if agent_name in self._agents:
                    # Update existing agent
                    existing_agent = self._agents[agent_name]
                    for key, value in agent_info.items():
                        if key in ["name"]:  # Skip immutable fields
                            continue
                        setattr(existing_agent, key, value)
                    
                    existing_agent.last_seen = time.time()
                    agent = existing_agent
                else:
                    # Create new agent
                    agent = AgentInfo.from_dict(agent_info)
                    self._agents[agent_name] = agent
                    self.registry_metrics["total_agents"] += 1
                
                # Update indexes
                self._update_capability_index(agent)
                self._update_category_index(agent)
                
                # Cache in Redis
                await self._cache_agent_info(agent)
                
                # Persist to database
                await self._persist_agent_info(agent)
                
                logger.info(
                    "Agent registered successfully",
                    agent_name=agent_name,
                    category=agent.category,
                    capabilities=len(agent.capabilities)
                )
                
                return True
                
            except Exception as e:
                logger.error("Failed to register agent", error=str(e))
                return False
    
    async def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent from the registry."""
        async with self._registry_lock:
            try:
                if agent_name not in self._agents:
                    logger.warning("Agent not found for unregistration", agent_name=agent_name)
                    return False
                
                agent = self._agents[agent_name]
                
                # Remove from indexes
                self._remove_from_capability_index(agent)
                self._remove_from_category_index(agent)
                
                # Remove from memory
                del self._agents[agent_name]
                
                # Remove from Redis cache
                await self._remove_agent_cache(agent_name)
                
                # Mark as deleted in database (soft delete)
                await self._soft_delete_agent(agent_name)
                
                self.registry_metrics["total_agents"] -= 1
                
                logger.info("Agent unregistered", agent_name=agent_name)
                return True
                
            except Exception as e:
                logger.error("Failed to unregister agent", agent_name=agent_name, error=str(e))
                return False
    
    async def update_agent_status(
        self,
        agent_name: str,
        status: AgentStatus,
        workload: Optional[int] = None,
        performance_update: Optional[Dict[str, float]] = None
    ) -> bool:
        """Update agent status and metrics."""
        try:
            if agent_name not in self._agents:
                logger.warning("Agent not found for status update", agent_name=agent_name)
                return False
            
            agent = self._agents[agent_name]
            agent.status = status
            agent.last_seen = time.time()
            
            if workload is not None:
                agent.current_workload = workload
            
            if performance_update:
                agent.performance_metrics.update(performance_update)
            
            # Update cache
            await self._cache_agent_info(agent)
            
            logger.debug(
                "Agent status updated",
                agent_name=agent_name,
                status=status,
                workload=agent.current_workload
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update agent status", agent_name=agent_name, error=str(e))
            return False
    
    async def find_agents_by_capability(
        self,
        capabilities: List[str],
        require_all: bool = True,
        max_results: int = 10,
        include_busy: bool = True
    ) -> List[AgentInfo]:
        """Find agents by capabilities with intelligent routing."""
        start_time = time.time()
        
        try:
            self.registry_metrics["routing_requests"] += 1
            
            logger.debug(
                "Finding agents by capability",
                capabilities=capabilities,
                require_all=require_all,
                max_results=max_results
            )
            
            candidate_agents = set()
            
            if require_all:
                # Find agents that have ALL capabilities
                for capability in capabilities:
                    if not candidate_agents:
                        # First capability
                        candidate_agents = self._capability_index.get(capability, set()).copy()
                    else:
                        # Intersect with existing candidates
                        candidate_agents &= self._capability_index.get(capability, set())
                        
                    if not candidate_agents:
                        break  # No agents have all capabilities
            else:
                # Find agents that have ANY of the capabilities
                for capability in capabilities:
                    candidate_agents |= self._capability_index.get(capability, set())
            
            # Filter and score candidates
            scored_agents = []
            
            for agent_name in candidate_agents:
                agent = self._agents.get(agent_name)
                if not agent:
                    continue
                
                # Filter by availability if requested
                if not include_busy and agent.status == AgentStatus.BUSY:
                    continue
                
                # Skip offline/error agents
                if agent.status in [AgentStatus.OFFLINE, AgentStatus.ERROR, AgentStatus.MAINTENANCE]:
                    continue
                
                # Skip overloaded agents
                if agent.status == AgentStatus.OVERLOADED:
                    continue
                
                scored_agents.append((agent, agent.priority_score))
            
            # Sort by priority score (highest first)
            scored_agents.sort(key=lambda x: x[1], reverse=True)
            
            # Return top results
            results = [agent for agent, score in scored_agents[:max_results]]
            
            # Update metrics
            routing_time = time.time() - start_time
            self.registry_metrics["avg_routing_time"] = (
                (self.registry_metrics["avg_routing_time"] * (self.registry_metrics["routing_requests"] - 1) + routing_time) /
                self.registry_metrics["routing_requests"]
            )
            
            if results:
                self.registry_metrics["successful_routes"] += 1
            
            logger.debug(
                "Agent routing completed",
                found_agents=len(results),
                routing_time_ms=round(routing_time * 1000, 2)
            )
            
            return results
            
        except Exception as e:
            logger.error("Failed to find agents by capability", error=str(e))
            return []
    
    async def find_agents_by_category(
        self,
        category: str,
        available_only: bool = True,
        max_results: int = 10
    ) -> List[AgentInfo]:
        """Find agents by category."""
        try:
            candidate_names = self._category_index.get(category, set())
            agents = []
            
            for agent_name in candidate_names:
                agent = self._agents.get(agent_name)
                if not agent:
                    continue
                
                if available_only and not agent.is_available:
                    continue
                
                agents.append(agent)
            
            # Sort by priority score
            agents.sort(key=lambda a: a.priority_score, reverse=True)
            
            return agents[:max_results]
            
        except Exception as e:
            logger.error("Failed to find agents by category", category=category, error=str(e))
            return []
    
    async def get_best_agent_for_task(
        self,
        required_capabilities: List[str],
        preferred_category: Optional[str] = None,
        exclude_agents: Optional[List[str]] = None
    ) -> Optional[AgentInfo]:
        """Get the best agent for a specific task."""
        try:
            exclude_agents = exclude_agents or []
            
            # Find candidates by capability
            candidates = await self.find_agents_by_capability(
                capabilities=required_capabilities,
                require_all=True,
                max_results=20,
                include_busy=True
            )
            
            if not candidates:
                logger.warning(
                    "No agents found with required capabilities",
                    required_capabilities=required_capabilities
                )
                return None
            
            # Filter out excluded agents
            candidates = [agent for agent in candidates if agent.name not in exclude_agents]
            
            if not candidates:
                logger.warning("All capable agents are excluded")
                return None
            
            # Apply category preference
            if preferred_category:
                category_candidates = [agent for agent in candidates if agent.category == preferred_category]
                if category_candidates:
                    candidates = category_candidates
            
            # Select best agent
            best_agent = candidates[0]  # Already sorted by priority score
            
            logger.info(
                "Selected best agent for task",
                agent_name=best_agent.name,
                category=best_agent.category,
                priority_score=best_agent.priority_score,
                utilization=best_agent.utilization_rate
            )
            
            return best_agent
            
        except Exception as e:
            logger.error("Failed to get best agent for task", error=str(e))
            return None
    
    async def get_agent_info(self, agent_name: str) -> Optional[AgentInfo]:
        """Get detailed information about a specific agent."""
        return self._agents.get(agent_name)
    
    async def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get information about all registered agents."""
        return [agent.to_dict() for agent in self._agents.values()]
    
    async def get_agent_count(self) -> int:
        """Get total number of registered agents."""
        return len(self._agents)
    
    async def validate_agents(self, agent_names: List[str]) -> bool:
        """Validate that all specified agents exist and are available."""
        for agent_name in agent_names:
            agent = self._agents.get(agent_name)
            if not agent or not agent.is_available:
                return False
        return True
    
    async def agent_exists(self, agent_name: str) -> bool:
        """Check if agent exists in registry."""
        return agent_name in self._agents
    
    async def is_agent_available(self, agent_name: str) -> bool:
        """Check if agent is available for new tasks."""
        agent = self._agents.get(agent_name)
        return agent.is_available if agent else False
    
    async def get_active_assignments(self) -> List[Dict[str, Any]]:
        """Get active agent assignments."""
        assignments = []
        
        for agent in self._agents.values():
            if agent.current_workload > 0:
                assignments.append({
                    "agent_name": agent.name,
                    "category": agent.category,
                    "current_workload": agent.current_workload,
                    "max_concurrent": agent.max_concurrent,
                    "utilization_rate": agent.utilization_rate,
                    "status": agent.status,
                    "last_seen": agent.last_seen
                })
        
        return assignments
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed registry status information."""
        # Calculate status distribution
        status_counts = {}
        for agent in self._agents.values():
            status_counts[agent.status] = status_counts.get(agent.status, 0) + 1
        
        # Calculate category distribution
        category_counts = {}
        for agent in self._agents.values():
            category_counts[agent.category] = category_counts.get(agent.category, 0) + 1
        
        # Calculate utilization statistics
        total_utilization = sum(agent.utilization_rate for agent in self._agents.values())
        avg_utilization = total_utilization / len(self._agents) if self._agents else 0
        
        # Update available count
        self.registry_metrics["available_agents"] = sum(
            1 for agent in self._agents.values() if agent.is_available
        )
        
        routing_success_rate = (
            self.registry_metrics["successful_routes"] / self.registry_metrics["routing_requests"]
            if self.registry_metrics["routing_requests"] > 0 else 0
        )
        
        return {
            "total_agents": len(self._agents),
            "status_distribution": status_counts,
            "category_distribution": category_counts,
            "utilization_statistics": {
                "average_utilization": avg_utilization,
                "total_workload": sum(agent.current_workload for agent in self._agents.values()),
                "max_capacity": sum(agent.max_concurrent for agent in self._agents.values())
            },
            "routing_metrics": {
                **self.registry_metrics,
                "routing_success_rate": routing_success_rate
            },
            "discovery_status": {
                "enabled": self.discovery_enabled,
                "running": self._discovery_running,
                "heartbeat_interval": self.heartbeat_interval,
                "offline_threshold": self.offline_threshold
            }
        }
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the agent registry."""
        logger.info("Shutting down Agent Registry...")
        
        try:
            # Stop discovery
            self._discovery_running = False
            
            # Persist final state
            for agent in self._agents.values():
                await self._persist_agent_info(agent)
            
            # Close database pool
            if self._db_pool:
                await self._db_pool.close()
            
            logger.info("Agent Registry shutdown complete")
            
        except Exception as e:
            logger.error("Error during Agent Registry shutdown", error=str(e))
    
    # Private helper methods
    
    async def _load_configured_agents(self) -> None:
        """Load agents from configuration."""
        logger.info("Loading configured agents")
        
        for agent_name, config in AGENT_CAPABILITIES.items():
            agent_info = AgentInfo(
                name=agent_name,
                category=config.get("category", "general"),
                capabilities=config.get("capabilities", []),
                status=AgentStatus.AVAILABLE,
                resource_requirements=config.get("resource_requirements", {}),
                max_concurrent=config.get("max_concurrent", 1),
                metadata={"source": "configuration"}
            )
            
            self._agents[agent_name] = agent_info
            self._update_capability_index(agent_info)
            self._update_category_index(agent_info)
        
        logger.info("Configured agents loaded", count=len(AGENT_CAPABILITIES))
    
    async def _load_persisted_agents(self) -> None:
        """Load agents from database."""
        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT name, category, capabilities, status, resource_requirements,
                           performance_metrics, current_workload, max_concurrent,
                           last_seen, endpoint_url, version, metadata
                    FROM agent_registry
                    WHERE deleted_at IS NULL
                """)
            
            loaded_count = 0
            
            for row in rows:
                try:
                    agent_info = AgentInfo(
                        name=row["name"],
                        category=row["category"],
                        capabilities=json.loads(row["capabilities"]) if row["capabilities"] else [],
                        status=AgentStatus(row["status"]),
                        resource_requirements=json.loads(row["resource_requirements"]) if row["resource_requirements"] else {},
                        performance_metrics=json.loads(row["performance_metrics"]) if row["performance_metrics"] else {},
                        current_workload=row["current_workload"] or 0,
                        max_concurrent=row["max_concurrent"] or 1,
                        last_seen=row["last_seen"].timestamp() if row["last_seen"] else time.time(),
                        endpoint_url=row["endpoint_url"],
                        version=row["version"] or "1.0.0",
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                    )
                    
                    # Only load if not already present from configuration
                    if agent_info.name not in self._agents:
                        self._agents[agent_info.name] = agent_info
                        self._update_capability_index(agent_info)
                        self._update_category_index(agent_info)
                        loaded_count += 1
                    
                except Exception as e:
                    logger.error("Failed to load agent from database", agent_name=row["name"], error=str(e))
            
            logger.info("Persisted agents loaded", count=loaded_count)
            
        except Exception as e:
            logger.error("Failed to load persisted agents", error=str(e))
    
    def _update_capability_index(self, agent: AgentInfo) -> None:
        """Update capability index for agent."""
        for capability in agent.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = set()
            self._capability_index[capability].add(agent.name)
    
    def _remove_from_capability_index(self, agent: AgentInfo) -> None:
        """Remove agent from capability index."""
        for capability in agent.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability].discard(agent.name)
                if not self._capability_index[capability]:
                    del self._capability_index[capability]
    
    def _update_category_index(self, agent: AgentInfo) -> None:
        """Update category index for agent."""
        if agent.category not in self._category_index:
            self._category_index[agent.category] = set()
        self._category_index[agent.category].add(agent.name)
    
    def _remove_from_category_index(self, agent: AgentInfo) -> None:
        """Remove agent from category index."""
        if agent.category in self._category_index:
            self._category_index[agent.category].discard(agent.name)
            if not self._category_index[agent.category]:
                del self._category_index[agent.category]
    
    async def _cache_agent_info(self, agent: AgentInfo) -> None:
        """Cache agent info in Redis."""
        if self.redis_service:
            await self.redis_service.set_json(
                key=f"agent_info:{agent.name}",
                value=agent.to_dict(),
                expiry_seconds=self.offline_threshold * 2
            )
    
    async def _remove_agent_cache(self, agent_name: str) -> None:
        """Remove agent from Redis cache."""
        if self.redis_service:
            await self.redis_service.delete(f"agent_info:{agent_name}")
    
    async def _persist_agent_info(self, agent: AgentInfo) -> None:
        """Persist agent info to database."""
        from datetime import datetime
        
        async with self._db_pool.acquire() as conn:
            # Convert Unix timestamp to datetime
            last_seen_dt = datetime.fromtimestamp(agent.last_seen) if agent.last_seen else datetime.now()
            
            await conn.execute("""
                INSERT INTO agent_registry 
                (name, category, capabilities, status, resource_requirements, performance_metrics,
                 current_workload, max_concurrent, last_seen, endpoint_url, version, metadata, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                ON CONFLICT (name) DO UPDATE SET
                    category = EXCLUDED.category,
                    capabilities = EXCLUDED.capabilities,
                    status = EXCLUDED.status,
                    resource_requirements = EXCLUDED.resource_requirements,
                    performance_metrics = EXCLUDED.performance_metrics,
                    current_workload = EXCLUDED.current_workload,
                    max_concurrent = EXCLUDED.max_concurrent,
                    last_seen = EXCLUDED.last_seen,
                    endpoint_url = EXCLUDED.endpoint_url,
                    version = EXCLUDED.version,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """,
                agent.name,
                agent.category,
                json.dumps(agent.capabilities),
                agent.status,
                json.dumps(agent.resource_requirements),
                json.dumps(agent.performance_metrics),
                agent.current_workload,
                agent.max_concurrent,
                last_seen_dt,
                agent.endpoint_url,
                agent.version,
                json.dumps(agent.metadata)
            )
    
    async def _soft_delete_agent(self, agent_name: str) -> None:
        """Soft delete agent in database."""
        async with self._db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE agent_registry SET deleted_at = NOW() WHERE name = $1",
                agent_name
            )
    
    async def _ensure_database_schema(self) -> None:
        """Ensure database schema exists."""
        async with self._db_pool.acquire() as conn:
            # Create table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_registry (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    capabilities JSONB,
                    status VARCHAR(50) NOT NULL DEFAULT 'unknown',
                    resource_requirements JSONB,
                    performance_metrics JSONB,
                    current_workload INTEGER DEFAULT 0,
                    max_concurrent INTEGER DEFAULT 1,
                    last_seen TIMESTAMP WITH TIME ZONE,
                    endpoint_url VARCHAR(255),
                    version VARCHAR(50) DEFAULT '1.0.0',
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    deleted_at TIMESTAMP WITH TIME ZONE
                )
            """)
            
            # Create indexes separately
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_registry_name ON agent_registry (name)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_registry_category ON agent_registry (category)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_registry_status ON agent_registry (status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_registry_capabilities ON agent_registry USING GIN (capabilities)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_registry_deleted_at ON agent_registry (deleted_at)")
    
    async def _run_discovery_loop(self) -> None:
        """Background agent discovery loop."""
        self._discovery_running = True
        
        logger.info("Starting agent discovery loop")
        
        try:
            while self._discovery_running:
                try:
                    # Discovery logic would go here
                    # This could include service discovery, health checks, etc.
                    await asyncio.sleep(60)  # Discovery every minute
                    
                except Exception as e:
                    logger.error("Error in discovery loop", error=str(e))
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("Discovery loop cancelled")
        finally:
            self._discovery_running = False
    
    async def _run_heartbeat_loop(self) -> None:
        """Background heartbeat and cleanup loop."""
        logger.info("Starting heartbeat loop")
        
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                try:
                    current_time = time.time()
                    
                    # Check for offline agents
                    offline_agents = []
                    
                    for agent_name, agent in list(self._agents.items()):
                        if current_time - agent.last_seen > self.offline_threshold:
                            if agent.status not in [AgentStatus.OFFLINE, AgentStatus.MAINTENANCE]:
                                agent.status = AgentStatus.OFFLINE
                                offline_agents.append(agent_name)
                                
                                # Update cache
                                await self._cache_agent_info(agent)
                    
                    if offline_agents:
                        logger.warning("Agents marked offline due to heartbeat timeout", agents=offline_agents)
                    
                except Exception as e:
                    logger.error("Error in heartbeat loop", error=str(e))
                    
        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")