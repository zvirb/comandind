"""
Cross-Service Dependency Monitoring
Advanced dependency tracking with cascading failure prevention
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import networkx as nx
import redis.asyncio as redis
import aiohttp
import json

from config import infrastructure_recovery_config
from predictive_monitor import predictive_monitor
from automated_recovery import automated_recovery

logger = logging.getLogger(__name__)


class DependencyStatus(Enum):
    """Dependency health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    CRITICAL = "critical"
    UNAVAILABLE = "unavailable"


class ImpactLevel(Enum):
    """Service failure impact levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ServiceDependency:
    """Dependency relationship between services"""
    service: str
    depends_on: str
    dependency_type: str  # sync, async, optional, critical
    weight: float  # importance of dependency (0.0 - 1.0)
    health_threshold: float  # minimum health for dependency
    circuit_breaker_enabled: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30


@dataclass
class DependencyHealthCheck:
    """Health check result for a dependency"""
    service: str
    dependency: str
    status: DependencyStatus
    health_score: float
    response_time: float
    last_check: datetime
    failure_count: int
    error_message: Optional[str] = None


@dataclass
class CascadeRisk:
    """Cascading failure risk assessment"""
    root_service: str
    affected_services: List[str]
    risk_score: float
    impact_level: ImpactLevel
    failure_path: List[str]
    estimated_downtime: int  # seconds
    mitigation_actions: List[str]


class CrossServiceDependencyMonitor:
    """
    Cross-Service Dependency Monitor
    Advanced monitoring system for service dependencies with cascading failure prevention
    """
    
    def __init__(self):
        self.config = infrastructure_recovery_config
        self.redis_client = None
        self.session = None
        self.running = False
        
        # Dependency graph management
        self.dependency_graph = nx.DiGraph()
        self.service_dependencies: Dict[str, List[ServiceDependency]] = {}
        self.dependency_health: Dict[Tuple[str, str], DependencyHealthCheck] = {}
        
        # Circuit breaker states
        self.circuit_breakers: Dict[Tuple[str, str], Dict[str, Any]] = {}
        
        # Cascade prevention
        self.cascade_risks: List[CascadeRisk] = []
        self.active_preventions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize dependency mappings
        self.init_dependency_mappings()
    
    def init_dependency_mappings(self):
        """Initialize service dependency mappings"""
        
        # Critical service dependencies from config
        base_dependencies = self.config.CRITICAL_SERVICE_DEPENDENCIES
        
        # Extended dependency mappings with detailed configuration
        extended_dependencies = {
            "api": [
                ServiceDependency("api", "postgres", "critical", 1.0, 0.8, True, 3, 10),
                ServiceDependency("api", "redis", "critical", 0.9, 0.7, True, 3, 5),
                ServiceDependency("api", "qdrant", "critical", 0.8, 0.6, True, 2, 15),
                ServiceDependency("api", "ollama", "async", 0.7, 0.5, True, 1, 30)
            ],
            "worker": [
                ServiceDependency("worker", "postgres", "critical", 1.0, 0.8, True, 3, 10),
                ServiceDependency("worker", "redis", "critical", 0.9, 0.7, True, 3, 5),
                ServiceDependency("worker", "ollama", "critical", 0.8, 0.6, True, 2, 45),
                ServiceDependency("worker", "qdrant", "async", 0.6, 0.5, True, 2, 20)
            ],
            "webui": [
                ServiceDependency("webui", "api", "critical", 1.0, 0.8, True, 3, 10)
            ],
            "coordination-service": [
                ServiceDependency("coordination-service", "postgres", "critical", 0.9, 0.8, True, 3, 10),
                ServiceDependency("coordination-service", "redis", "critical", 0.8, 0.7, True, 3, 5),
                ServiceDependency("coordination-service", "qdrant", "async", 0.7, 0.6, True, 2, 15)
            ],
            "hybrid-memory-service": [
                ServiceDependency("hybrid-memory-service", "postgres", "critical", 0.9, 0.8, True, 3, 10),
                ServiceDependency("hybrid-memory-service", "qdrant", "critical", 0.9, 0.7, True, 3, 15),
                ServiceDependency("hybrid-memory-service", "ollama", "async", 0.6, 0.5, True, 2, 30)
            ],
            "learning-service": [
                ServiceDependency("learning-service", "postgres", "critical", 0.8, 0.8, True, 3, 10),
                ServiceDependency("learning-service", "redis", "critical", 0.7, 0.7, True, 3, 5),
                ServiceDependency("learning-service", "qdrant", "async", 0.8, 0.6, True, 2, 15),
                ServiceDependency("learning-service", "ollama", "async", 0.7, 0.5, True, 2, 30)
            ],
            "perception-service": [
                ServiceDependency("perception-service", "ollama", "critical", 1.0, 0.7, True, 3, 30)
            ],
            "reasoning-service": [
                ServiceDependency("reasoning-service", "postgres", "critical", 0.8, 0.8, True, 3, 10),
                ServiceDependency("reasoning-service", "redis", "critical", 0.7, 0.7, True, 3, 5),
                ServiceDependency("reasoning-service", "ollama", "critical", 0.9, 0.6, True, 3, 30)
            ]
        }
        
        self.service_dependencies = extended_dependencies
        
        # Build dependency graph
        self.build_dependency_graph()
    
    def build_dependency_graph(self):
        """Build NetworkX dependency graph for analysis"""
        self.dependency_graph.clear()
        
        # Add all services as nodes
        all_services = set()
        for service, deps in self.service_dependencies.items():
            all_services.add(service)
            for dep in deps:
                all_services.add(dep.depends_on)
        
        self.dependency_graph.add_nodes_from(all_services)
        
        # Add edges with weights
        for service, deps in self.service_dependencies.items():
            for dep in deps:
                self.dependency_graph.add_edge(
                    service, 
                    dep.depends_on,
                    weight=dep.weight,
                    dependency_type=dep.dependency_type,
                    threshold=dep.health_threshold
                )
    
    async def initialize(self):
        """Initialize the dependency monitoring system"""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                self.config.REDIS_URL,
                decode_responses=True,
                health_check_interval=30
            )
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
            
            # Initialize circuit breakers
            await self.init_circuit_breakers()
            
            # Load dependency health history
            await self.load_dependency_health()
            
            logger.info("Cross-Service Dependency Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cross-Service Dependency Monitor: {e}")
            raise
    
    async def start_dependency_monitoring(self):
        """Start the dependency monitoring system"""
        self.running = True
        
        tasks = [
            self.dependency_health_monitoring_loop(),
            self.cascade_risk_analysis_loop(),
            self.circuit_breaker_management_loop(),
            self.prevention_action_loop(),
            self.maintenance_loop()
        ]
        
        logger.info("Starting cross-service dependency monitoring system")
        await asyncio.gather(*tasks)
    
    async def dependency_health_monitoring_loop(self):
        """Main loop for monitoring dependency health"""
        while self.running:
            try:
                await self.check_all_dependencies()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in dependency health monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def check_all_dependencies(self):
        """Check health of all service dependencies"""
        tasks = []
        
        for service, dependencies in self.service_dependencies.items():
            for dependency in dependencies:
                tasks.append(
                    self.check_dependency_health(service, dependency)
                )
        
        # Execute all health checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Dependency health check failed: {result}")
    
    async def check_dependency_health(self, service: str, dependency: ServiceDependency):
        """Check health of a specific dependency"""
        try:
            dep_key = (service, dependency.depends_on)
            
            # Check circuit breaker status
            if await self.is_circuit_breaker_open(dep_key):
                # Circuit breaker is open, don't check
                return
            
            start_time = time.time()
            
            # Get dependency health score
            dep_health_score = await predictive_monitor.get_service_health_score(
                dependency.depends_on
            )
            
            response_time = time.time() - start_time
            
            # Determine dependency status
            status = self.determine_dependency_status(dep_health_score, dependency)
            
            # Get current health check or create new one
            current_check = self.dependency_health.get(dep_key)
            failure_count = 0
            
            if current_check:
                if status in [DependencyStatus.FAILING, DependencyStatus.CRITICAL, DependencyStatus.UNAVAILABLE]:
                    failure_count = current_check.failure_count + 1
                else:
                    failure_count = 0  # Reset on success
            
            # Create/update health check
            health_check = DependencyHealthCheck(
                service=service,
                dependency=dependency.depends_on,
                status=status,
                health_score=dep_health_score,
                response_time=response_time,
                last_check=datetime.utcnow(),
                failure_count=failure_count
            )
            
            # Store health check
            self.dependency_health[dep_key] = health_check
            
            # Cache in Redis
            await self.cache_dependency_health(health_check)
            
            # Update circuit breaker
            await self.update_circuit_breaker(dep_key, health_check, dependency)
            
            # Check for cascade risks
            if status in [DependencyStatus.CRITICAL, DependencyStatus.UNAVAILABLE]:
                await self.evaluate_cascade_risk(service, dependency.depends_on, status)
            
        except Exception as e:
            logger.error(f"Error checking dependency health for {service} -> {dependency.depends_on}: {e}")
            
            # Record failure
            dep_key = (service, dependency.depends_on)
            current_check = self.dependency_health.get(dep_key)
            failure_count = (current_check.failure_count + 1) if current_check else 1
            
            health_check = DependencyHealthCheck(
                service=service,
                dependency=dependency.depends_on,
                status=DependencyStatus.UNAVAILABLE,
                health_score=0.0,
                response_time=dependency.timeout_seconds,
                last_check=datetime.utcnow(),
                failure_count=failure_count,
                error_message=str(e)
            )
            
            self.dependency_health[dep_key] = health_check
            await self.update_circuit_breaker(dep_key, health_check, dependency)
    
    def determine_dependency_status(self, health_score: float, 
                                   dependency: ServiceDependency) -> DependencyStatus:
        """Determine dependency status based on health score and thresholds"""
        if health_score >= dependency.health_threshold:
            return DependencyStatus.HEALTHY
        elif health_score >= dependency.health_threshold * 0.8:
            return DependencyStatus.DEGRADED
        elif health_score >= dependency.health_threshold * 0.5:
            return DependencyStatus.FAILING
        elif health_score > 0.0:
            return DependencyStatus.CRITICAL
        else:
            return DependencyStatus.UNAVAILABLE
    
    async def cache_dependency_health(self, health_check: DependencyHealthCheck):
        """Cache dependency health check in Redis"""
        try:
            cache_key = f"dependency:health:{health_check.service}:{health_check.dependency}"
            cache_data = {
                "status": health_check.status.value,
                "health_score": health_check.health_score,
                "response_time": health_check.response_time,
                "failure_count": health_check.failure_count,
                "last_check": health_check.last_check.isoformat(),
                "error_message": health_check.error_message
            }
            
            await self.redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(cache_data)
            )
            
        except Exception as e:
            logger.debug(f"Error caching dependency health: {e}")
    
    async def init_circuit_breakers(self):
        """Initialize circuit breaker states for all dependencies"""
        for service, dependencies in self.service_dependencies.items():
            for dependency in dependencies:
                if dependency.circuit_breaker_enabled:
                    dep_key = (service, dependency.depends_on)
                    self.circuit_breakers[dep_key] = {
                        "state": "closed",  # closed, open, half_open
                        "failure_count": 0,
                        "last_failure_time": None,
                        "next_attempt_time": None,
                        "success_count": 0
                    }
    
    async def update_circuit_breaker(self, dep_key: Tuple[str, str], 
                                   health_check: DependencyHealthCheck,
                                   dependency: ServiceDependency):
        """Update circuit breaker state based on health check"""
        try:
            if not dependency.circuit_breaker_enabled:
                return
            
            circuit_breaker = self.circuit_breakers.get(dep_key)
            if not circuit_breaker:
                return
            
            current_state = circuit_breaker["state"]
            
            # Determine if this is a failure
            is_failure = health_check.status in [
                DependencyStatus.CRITICAL, 
                DependencyStatus.UNAVAILABLE
            ]
            
            if current_state == "closed":
                if is_failure:
                    circuit_breaker["failure_count"] += 1
                    circuit_breaker["last_failure_time"] = datetime.utcnow()
                    
                    # Open circuit if failure threshold exceeded
                    if circuit_breaker["failure_count"] >= dependency.retry_count:
                        circuit_breaker["state"] = "open"
                        circuit_breaker["next_attempt_time"] = (
                            datetime.utcnow() + timedelta(seconds=60)  # 1 minute cooldown
                        )
                        
                        logger.warning(
                            f"Circuit breaker opened for {dep_key[0]} -> {dep_key[1]} "
                            f"after {circuit_breaker['failure_count']} failures"
                        )
                        
                        # Trigger cascade prevention
                        await self.trigger_cascade_prevention(dep_key[0], dep_key[1])
                else:
                    # Reset failure count on success
                    circuit_breaker["failure_count"] = 0
            
            elif current_state == "open":
                # Check if it's time to try half-open
                if (circuit_breaker["next_attempt_time"] and 
                    datetime.utcnow() >= circuit_breaker["next_attempt_time"]):
                    circuit_breaker["state"] = "half_open"
                    circuit_breaker["success_count"] = 0
                    
                    logger.info(f"Circuit breaker half-open for {dep_key[0]} -> {dep_key[1]}")
            
            elif current_state == "half_open":
                if is_failure:
                    # Back to open state
                    circuit_breaker["state"] = "open"
                    circuit_breaker["failure_count"] += 1
                    circuit_breaker["next_attempt_time"] = (
                        datetime.utcnow() + timedelta(seconds=120)  # 2 minutes cooldown
                    )
                    
                    logger.warning(f"Circuit breaker re-opened for {dep_key[0]} -> {dep_key[1]}")
                else:
                    circuit_breaker["success_count"] += 1
                    
                    # Close circuit if enough successes
                    if circuit_breaker["success_count"] >= 2:
                        circuit_breaker["state"] = "closed"
                        circuit_breaker["failure_count"] = 0
                        
                        logger.info(f"Circuit breaker closed for {dep_key[0]} -> {dep_key[1]}")
            
            # Cache circuit breaker state
            await self.redis_client.setex(
                f"circuit_breaker:{dep_key[0]}:{dep_key[1]}",
                3600,
                json.dumps(circuit_breaker, default=str)
            )
            
        except Exception as e:
            logger.error(f"Error updating circuit breaker for {dep_key}: {e}")
    
    async def is_circuit_breaker_open(self, dep_key: Tuple[str, str]) -> bool:
        """Check if circuit breaker is open"""
        try:
            circuit_breaker = self.circuit_breakers.get(dep_key)
            if not circuit_breaker:
                return False
            
            return circuit_breaker["state"] == "open"
            
        except Exception as e:
            logger.debug(f"Error checking circuit breaker state: {e}")
            return False
    
    async def cascade_risk_analysis_loop(self):
        """Main loop for analyzing cascade risks"""
        while self.running:
            try:
                await self.analyze_cascade_risks()
                await asyncio.sleep(60)  # Analyze every minute
                
            except Exception as e:
                logger.error(f"Error in cascade risk analysis loop: {e}")
                await asyncio.sleep(30)
    
    async def analyze_cascade_risks(self):
        """Analyze potential cascading failure risks"""
        try:
            # Clear previous risks
            self.cascade_risks.clear()
            
            # Get all services with health issues
            at_risk_services = []
            
            for service in self.config.MONITORED_SERVICES:
                health_score = await predictive_monitor.get_service_health_score(service)
                if health_score < 0.6:  # Risk threshold
                    at_risk_services.append((service, health_score))
            
            # Analyze cascade impact for each at-risk service
            for service, health_score in at_risk_services:
                cascade_risk = await self.calculate_cascade_risk(service, health_score)
                if cascade_risk:
                    self.cascade_risks.append(cascade_risk)
            
            # Sort by risk score
            self.cascade_risks.sort(key=lambda r: r.risk_score, reverse=True)
            
            # Log high-risk cascades
            for risk in self.cascade_risks:
                if risk.risk_score > 0.7:
                    logger.warning(
                        f"High cascade risk detected: {risk.root_service} -> "
                        f"{len(risk.affected_services)} services (risk: {risk.risk_score:.2f})"
                    )
            
        except Exception as e:
            logger.error(f"Error analyzing cascade risks: {e}")
    
    async def calculate_cascade_risk(self, root_service: str, 
                                   health_score: float) -> Optional[CascadeRisk]:
        """Calculate cascading failure risk for a service"""
        try:
            # Find all services that depend on this service
            affected_services = []
            failure_paths = []
            
            # Use graph traversal to find dependents
            dependents = self.find_service_dependents(root_service)
            
            for dependent in dependents:
                # Check if dependent is critical and would be affected
                if await self.would_service_be_affected(dependent, root_service):
                    affected_services.append(dependent)
                    
                    # Find failure path
                    path = self.find_failure_path(root_service, dependent)
                    if path:
                        failure_paths.append(path)
            
            if not affected_services:
                return None
            
            # Calculate risk score
            risk_score = self.calculate_risk_score(
                root_service, affected_services, health_score
            )
            
            # Determine impact level
            impact_level = self.determine_impact_level(affected_services)
            
            # Estimate downtime
            estimated_downtime = self.estimate_cascade_downtime(
                root_service, affected_services
            )
            
            # Generate mitigation actions
            mitigation_actions = self.generate_mitigation_actions(
                root_service, affected_services
            )
            
            return CascadeRisk(
                root_service=root_service,
                affected_services=affected_services,
                risk_score=risk_score,
                impact_level=impact_level,
                failure_path=failure_paths[0] if failure_paths else [root_service],
                estimated_downtime=estimated_downtime,
                mitigation_actions=mitigation_actions
            )
            
        except Exception as e:
            logger.error(f"Error calculating cascade risk for {root_service}: {e}")
            return None
    
    def find_service_dependents(self, service: str) -> List[str]:
        """Find all services that depend on the given service"""
        dependents = []
        
        try:
            # Use networkx to find predecessors (services that depend on this one)
            if service in self.dependency_graph:
                dependents = list(self.dependency_graph.predecessors(service))
                
                # Also find indirect dependents (services that depend on dependents)
                indirect_dependents = set()
                for dependent in dependents:
                    indirect = list(self.dependency_graph.predecessors(dependent))
                    indirect_dependents.update(indirect)
                
                # Combine direct and indirect dependents
                dependents.extend(list(indirect_dependents))
                dependents = list(set(dependents))  # Remove duplicates
                
        except Exception as e:
            logger.debug(f"Error finding dependents for {service}: {e}")
        
        return dependents
    
    async def would_service_be_affected(self, dependent: str, failed_service: str) -> bool:
        """Check if a dependent service would be affected by failure"""
        try:
            # Get dependency configuration
            deps = self.service_dependencies.get(dependent, [])
            
            for dep in deps:
                if dep.depends_on == failed_service:
                    # Check if this is a critical dependency
                    if dep.dependency_type in ["critical", "sync"]:
                        return True
                    
                    # Check if dependency weight is high
                    if dep.weight > 0.7:
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking service affection: {e}")
            return False
    
    def find_failure_path(self, root_service: str, target_service: str) -> List[str]:
        """Find failure propagation path between services"""
        try:
            if (root_service in self.dependency_graph and 
                target_service in self.dependency_graph):
                
                # Use shortest path to find dependency chain
                path = nx.shortest_path(
                    self.dependency_graph.reverse(), 
                    target_service, 
                    root_service
                )
                return path
                
        except (nx.NetworkXNoPath, nx.NetworkXError):
            pass
        
        return [root_service, target_service]
    
    def calculate_risk_score(self, root_service: str, affected_services: List[str], 
                           health_score: float) -> float:
        """Calculate overall cascade risk score"""
        try:
            # Base risk from root service health
            base_risk = 1.0 - health_score
            
            # Risk amplification based on number of affected services
            service_count_factor = min(len(affected_services) / 10.0, 1.0)
            
            # Risk amplification based on criticality of affected services
            critical_services = ["postgres", "redis", "api"]
            critical_affected = len([s for s in affected_services if s in critical_services])
            criticality_factor = critical_affected / max(len(critical_services), 1)
            
            # Combine factors
            risk_score = base_risk * (1.0 + service_count_factor + criticality_factor) / 3.0
            
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.debug(f"Error calculating risk score: {e}")
            return 0.5
    
    def determine_impact_level(self, affected_services: List[str]) -> ImpactLevel:
        """Determine impact level based on affected services"""
        try:
            critical_services = {"postgres", "redis", "api"}
            important_services = {"webui", "worker", "coordination-service"}
            
            affected_set = set(affected_services)
            
            if affected_set & critical_services:
                return ImpactLevel.CRITICAL
            elif len(affected_set & important_services) > 1:
                return ImpactLevel.HIGH
            elif affected_set & important_services:
                return ImpactLevel.MEDIUM
            else:
                return ImpactLevel.LOW
                
        except Exception as e:
            logger.debug(f"Error determining impact level: {e}")
            return ImpactLevel.MEDIUM
    
    def estimate_cascade_downtime(self, root_service: str, 
                                affected_services: List[str]) -> int:
        """Estimate potential downtime in seconds"""
        try:
            # Base downtime estimates by service type
            service_downtimes = {
                "postgres": 300,  # 5 minutes - critical database
                "redis": 120,     # 2 minutes - cache service
                "api": 180,       # 3 minutes - core API
                "webui": 60,      # 1 minute - frontend
                "worker": 240,    # 4 minutes - background processing
                "ollama": 180,    # 3 minutes - AI service
                "qdrant": 240     # 4 minutes - vector database
            }
            
            # Get base downtime for root service
            base_downtime = service_downtimes.get(root_service, 120)
            
            # Add cascade delay for affected services
            cascade_delay = len(affected_services) * 30  # 30 seconds per service
            
            # Consider recovery time
            recovery_time = 60  # 1 minute base recovery
            
            total_downtime = base_downtime + cascade_delay + recovery_time
            
            return min(total_downtime, 1800)  # Cap at 30 minutes
            
        except Exception as e:
            logger.debug(f"Error estimating downtime: {e}")
            return 300  # Default 5 minutes
    
    def generate_mitigation_actions(self, root_service: str, 
                                  affected_services: List[str]) -> List[str]:
        """Generate mitigation actions for cascade prevention"""
        actions = []
        
        try:
            # Root service recovery
            actions.append(f"Immediate health recovery for {root_service}")
            
            # Circuit breaker activation
            actions.append("Activate circuit breakers for affected dependencies")
            
            # Service isolation
            if len(affected_services) > 3:
                actions.append("Isolate affected services to prevent further cascade")
            
            # Load balancing
            if root_service in ["api", "webui"]:
                actions.append("Redirect traffic to healthy instances")
            
            # Cache warming
            if "redis" in affected_services:
                actions.append("Pre-warm cache after recovery")
            
            # Database failover
            if root_service == "postgres":
                actions.append("Consider database failover if available")
            
            # Rollback consideration
            actions.append("Evaluate rollback to last known good state")
            
        except Exception as e:
            logger.debug(f"Error generating mitigation actions: {e}")
        
        return actions
    
    async def trigger_cascade_prevention(self, service: str, failed_dependency: str):
        """Trigger cascade prevention measures"""
        try:
            prevention_id = f"prevention_{service}_{failed_dependency}_{int(time.time())}"
            
            prevention_actions = {
                "circuit_breaker_activated": True,
                "graceful_degradation": False,
                "traffic_rerouting": False,
                "service_isolation": False,
                "recovery_initiated": False
            }
            
            # Activate graceful degradation for non-critical dependencies
            deps = self.service_dependencies.get(service, [])
            for dep in deps:
                if dep.depends_on == failed_dependency:
                    if dep.dependency_type in ["async", "optional"]:
                        prevention_actions["graceful_degradation"] = True
                        logger.info(
                            f"Activated graceful degradation for {service} -> {failed_dependency}"
                        )
            
            # Consider service isolation for critical failures
            if failed_dependency in ["postgres", "redis"]:
                prevention_actions["service_isolation"] = True
                logger.warning(
                    f"Considering service isolation due to {failed_dependency} failure"
                )
            
            # Trigger automated recovery
            prevention_actions["recovery_initiated"] = True
            # Note: In a full implementation, this would integrate with automated_recovery
            
            # Store prevention action
            self.active_preventions[prevention_id] = {
                "service": service,
                "failed_dependency": failed_dependency,
                "actions": prevention_actions,
                "triggered_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Cache in Redis
            await self.redis_client.setex(
                f"cascade_prevention:{prevention_id}",
                3600,
                json.dumps(self.active_preventions[prevention_id], default=str)
            )
            
            logger.info(f"Cascade prevention triggered: {prevention_id}")
            
        except Exception as e:
            logger.error(f"Error triggering cascade prevention: {e}")
    
    async def evaluate_cascade_risk(self, service: str, failed_dependency: str, 
                                  status: DependencyStatus):
        """Evaluate and respond to cascade risk"""
        try:
            # Find potential cascade impact
            cascade_risk = await self.calculate_cascade_risk(service, 0.2)  # Assume low health
            
            if cascade_risk and cascade_risk.risk_score > 0.6:
                logger.warning(
                    f"High cascade risk detected from {failed_dependency} failure: "
                    f"risk_score={cascade_risk.risk_score:.2f}, "
                    f"affected_services={cascade_risk.affected_services}"
                )
                
                # Trigger prevention measures
                await self.trigger_cascade_prevention(service, failed_dependency)
            
        except Exception as e:
            logger.error(f"Error evaluating cascade risk: {e}")
    
    async def circuit_breaker_management_loop(self):
        """Loop for managing circuit breaker states"""
        while self.running:
            try:
                await self.manage_circuit_breakers()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in circuit breaker management loop: {e}")
                await asyncio.sleep(30)
    
    async def manage_circuit_breakers(self):
        """Manage circuit breaker state transitions"""
        try:
            current_time = datetime.utcnow()
            
            for dep_key, circuit_breaker in self.circuit_breakers.items():
                if circuit_breaker["state"] == "open":
                    # Check if it's time to attempt half-open
                    next_attempt = circuit_breaker.get("next_attempt_time")
                    if next_attempt and current_time >= next_attempt:
                        circuit_breaker["state"] = "half_open"
                        circuit_breaker["success_count"] = 0
                        
                        logger.info(f"Circuit breaker transitioning to half-open: {dep_key}")
                        
                        # Cache updated state
                        await self.redis_client.setex(
                            f"circuit_breaker:{dep_key[0]}:{dep_key[1]}",
                            3600,
                            json.dumps(circuit_breaker, default=str)
                        )
                        
        except Exception as e:
            logger.error(f"Error managing circuit breakers: {e}")
    
    async def prevention_action_loop(self):
        """Loop for managing prevention actions"""
        while self.running:
            try:
                await self.manage_prevention_actions()
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in prevention action loop: {e}")
                await asyncio.sleep(60)
    
    async def manage_prevention_actions(self):
        """Manage active prevention actions"""
        try:
            completed_preventions = []
            
            for prevention_id, prevention in self.active_preventions.items():
                # Check if prevention is still needed
                service = prevention["service"]
                failed_dependency = prevention["failed_dependency"]
                
                # Get current dependency health
                dep_key = (service, failed_dependency)
                current_health = self.dependency_health.get(dep_key)
                
                if current_health and current_health.status == DependencyStatus.HEALTHY:
                    # Dependency recovered, deactivate prevention
                    prevention["status"] = "completed"
                    prevention["completed_at"] = datetime.utcnow()
                    completed_preventions.append(prevention_id)
                    
                    logger.info(f"Prevention action completed: {prevention_id}")
            
            # Remove completed preventions
            for prevention_id in completed_preventions:
                del self.active_preventions[prevention_id]
                await self.redis_client.delete(f"cascade_prevention:{prevention_id}")
            
        except Exception as e:
            logger.error(f"Error managing prevention actions: {e}")
    
    async def maintenance_loop(self):
        """Maintenance loop for cleanup tasks"""
        while self.running:
            try:
                await self.cleanup_old_data()
                await asyncio.sleep(600)  # Cleanup every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(120)
    
    async def cleanup_old_data(self):
        """Clean up old dependency health data"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # Clean up old health checks
            expired_checks = []
            for dep_key, health_check in self.dependency_health.items():
                if health_check.last_check < cutoff_time:
                    expired_checks.append(dep_key)
            
            for dep_key in expired_checks:
                del self.dependency_health[dep_key]
            
            if expired_checks:
                logger.info(f"Cleaned up {len(expired_checks)} expired health checks")
            
            # Clean up completed cascade risks
            if len(self.cascade_risks) > 20:
                self.cascade_risks = self.cascade_risks[:20]  # Keep most recent
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    async def load_dependency_health(self):
        """Load dependency health from Redis cache"""
        try:
            keys = await self.redis_client.keys("dependency:health:*")
            
            for key in keys:
                health_data = await self.redis_client.get(key)
                if health_data:
                    try:
                        data = json.loads(health_data)
                        parts = key.split(":")
                        if len(parts) >= 4:
                            service = parts[2]
                            dependency = parts[3]
                            
                            health_check = DependencyHealthCheck(
                                service=service,
                                dependency=dependency,
                                status=DependencyStatus(data["status"]),
                                health_score=data["health_score"],
                                response_time=data["response_time"],
                                last_check=datetime.fromisoformat(data["last_check"]),
                                failure_count=data["failure_count"],
                                error_message=data.get("error_message")
                            )
                            
                            self.dependency_health[(service, dependency)] = health_check
                    except Exception as e:
                        logger.debug(f"Error loading health data from {key}: {e}")
            
            logger.info(f"Loaded {len(self.dependency_health)} dependency health records")
            
        except Exception as e:
            logger.error(f"Error loading dependency health: {e}")
    
    async def get_dependency_status(self) -> Dict[str, Any]:
        """Get current dependency monitoring status"""
        try:
            # Count circuit breaker states
            cb_states = {"closed": 0, "open": 0, "half_open": 0}
            for cb in self.circuit_breakers.values():
                cb_states[cb["state"]] += 1
            
            # Count health statuses
            health_statuses = {}
            for health_check in self.dependency_health.values():
                status = health_check.status.value
                health_statuses[status] = health_statuses.get(status, 0) + 1
            
            # Get high-risk cascades
            high_risk_cascades = [
                {
                    "root_service": risk.root_service,
                    "affected_services": risk.affected_services,
                    "risk_score": risk.risk_score,
                    "impact_level": risk.impact_level.value
                }
                for risk in self.cascade_risks if risk.risk_score > 0.6
            ]
            
            return {
                "running": self.running,
                "dependencies_monitored": len(self.dependency_health),
                "circuit_breakers": cb_states,
                "health_statuses": health_statuses,
                "active_preventions": len(self.active_preventions),
                "cascade_risks": len(self.cascade_risks),
                "high_risk_cascades": high_risk_cascades,
                "services_in_graph": self.dependency_graph.number_of_nodes(),
                "dependency_edges": self.dependency_graph.number_of_edges()
            }
            
        except Exception as e:
            logger.error(f"Error getting dependency status: {e}")
            return {"error": str(e)}
    
    async def stop_dependency_monitoring(self):
        """Stop the dependency monitoring system"""
        self.running = False
        
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Cross-Service Dependency Monitor stopped")


# Global dependency monitor instance
dependency_monitor = CrossServiceDependencyMonitor()