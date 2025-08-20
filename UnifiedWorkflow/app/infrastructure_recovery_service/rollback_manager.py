"""
Enhanced Rollback Manager
Intelligent rollback mechanisms with automated triggers and state management
"""
import asyncio
import logging
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import redis.asyncio as redis
import docker
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

from config import infrastructure_recovery_config
from predictive_monitor import predictive_monitor

logger = logging.getLogger(__name__)


class RollbackTrigger(Enum):
    """Types of rollback triggers"""
    HEALTH_DEGRADATION = "health_degradation"
    PERFORMANCE_REGRESSION = "performance_regression" 
    ERROR_RATE_SPIKE = "error_rate_spike"
    DEPENDENCY_FAILURE = "dependency_failure"
    MANUAL_TRIGGER = "manual_trigger"
    SCHEDULED_ROLLBACK = "scheduled_rollback"
    CASCADE_FAILURE = "cascade_failure"
    SECURITY_INCIDENT = "security_incident"


class RollbackStatus(Enum):
    """Rollback operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass
class SystemSnapshot:
    """System state snapshot for rollback purposes"""
    snapshot_id: str
    timestamp: datetime
    services: Dict[str, Dict[str, Any]]
    configurations: Dict[str, Any]
    database_state: Optional[Dict[str, Any]]
    health_scores: Dict[str, float]
    metrics: Dict[str, Any]
    checksum: str
    rollback_safe: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemSnapshot':
        """Create snapshot from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class RollbackOperation:
    """Rollback operation tracking"""
    rollback_id: str
    trigger: RollbackTrigger
    target_snapshot_id: str
    affected_services: List[str]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: RollbackStatus = RollbackStatus.PENDING
    success_metrics: Dict[str, float] = None
    failure_reason: Optional[str] = None
    rollback_steps: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.success_metrics is None:
            self.success_metrics = {}
        if self.rollback_steps is None:
            self.rollback_steps = []


class EnhancedRollbackManager:
    """
    Enhanced Rollback Manager with Intelligent Triggers
    Provides automated rollback capabilities with state management and intelligent decision making
    """
    
    def __init__(self):
        self.config = infrastructure_recovery_config
        self.redis_client = None
        self.session = None
        self.docker_client = None
        self.running = False
        
        # State management
        self.snapshots: Dict[str, SystemSnapshot] = {}
        self.active_rollbacks: Dict[str, RollbackOperation] = {}
        self.rollback_history: List[RollbackOperation] = []
        
        # Rollback triggers and thresholds
        self.rollback_thresholds = {
            RollbackTrigger.HEALTH_DEGRADATION: 0.3,  # Health score below 30%
            RollbackTrigger.PERFORMANCE_REGRESSION: 0.5,  # 50% performance drop
            RollbackTrigger.ERROR_RATE_SPIKE: 0.1,  # 10% error rate
            RollbackTrigger.DEPENDENCY_FAILURE: 0.4,  # 40% dependency health
        }
        
        # Service rollback priorities
        self.rollback_priorities = {
            "postgres": 1,  # Highest priority - data safety
            "redis": 2,
            "api": 3,
            "worker": 4,
            "webui": 5,
            "qdrant": 6,
            "ollama": 7,
            "coordination-service": 8,
            "hybrid-memory-service": 8,
            "learning-service": 9,
            "perception-service": 9,
            "reasoning-service": 9
        }
    
    async def initialize(self):
        """Initialize the rollback manager"""
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
            
            # Initialize Docker client - ensure we don't have DOCKER_HOST set
            import os
            if 'DOCKER_HOST' in os.environ:
                del os.environ['DOCKER_HOST']
            self.docker_client = docker.from_env()
            
            # Load existing snapshots
            await self.load_snapshots()
            
            # Load rollback history
            await self.load_rollback_history()
            
            logger.info("Enhanced Rollback Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Rollback Manager: {e}")
            raise
    
    async def start_rollback_manager(self):
        """Start the rollback management system"""
        self.running = True
        
        tasks = [
            self.snapshot_creation_loop(),
            self.rollback_monitoring_loop(),
            self.rollback_execution_loop(),
            self.maintenance_loop()
        ]
        
        logger.info("Starting enhanced rollback management system")
        await asyncio.gather(*tasks)
    
    async def snapshot_creation_loop(self):
        """Main loop for creating system snapshots"""
        while self.running:
            try:
                await self.create_system_snapshot()
                await asyncio.sleep(self.config.ROLLBACK_SNAPSHOT_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in snapshot creation loop: {e}")
                await asyncio.sleep(60)
    
    async def create_system_snapshot(self) -> Optional[SystemSnapshot]:
        """Create a comprehensive system snapshot"""
        try:
            timestamp = datetime.utcnow()
            snapshot_id = f"snapshot_{int(timestamp.timestamp())}_{hashlib.md5(str(timestamp).encode()).hexdigest()[:8]}"
            
            # Collect service states
            services = await self.collect_service_states()
            
            # Collect configurations
            configurations = await self.collect_configurations()
            
            # Collect database state (metadata only for safety)
            database_state = await self.collect_database_state()
            
            # Get current health scores
            health_scores = await predictive_monitor.get_all_health_scores()
            
            # Collect current metrics
            metrics = await self.collect_current_metrics()
            
            # Calculate checksum for integrity
            checksum_data = {
                "services": services,
                "configurations": configurations,
                "health_scores": health_scores
            }
            checksum = hashlib.sha256(json.dumps(checksum_data, sort_keys=True).encode()).hexdigest()
            
            # Determine if snapshot is rollback-safe
            rollback_safe = await self.is_snapshot_rollback_safe(health_scores)
            
            # Create snapshot
            snapshot = SystemSnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                services=services,
                configurations=configurations,
                database_state=database_state,
                health_scores=health_scores,
                metrics=metrics,
                checksum=checksum,
                rollback_safe=rollback_safe
            )
            
            # Store snapshot
            await self.store_snapshot(snapshot)
            
            # Cleanup old snapshots
            await self.cleanup_old_snapshots()
            
            logger.info(f"Created system snapshot: {snapshot_id} (rollback_safe: {rollback_safe})")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating system snapshot: {e}")
            return None
    
    async def collect_service_states(self) -> Dict[str, Dict[str, Any]]:
        """Collect current state of all services"""
        services = {}
        
        try:
            # Get Docker container states
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                service_name = self.extract_service_name(container.name)
                if service_name in self.config.MONITORED_SERVICES:
                    services[service_name] = {
                        "container_id": container.id[:12],
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "status": container.status,
                        "created": container.attrs.get("Created", ""),
                        "config": {
                            "env": container.attrs.get("Config", {}).get("Env", []),
                            "cmd": container.attrs.get("Config", {}).get("Cmd", []),
                            "ports": container.attrs.get("Config", {}).get("ExposedPorts", {})
                        },
                        "health": container.attrs.get("State", {}).get("Health", {})
                    }
                    
        except Exception as e:
            logger.error(f"Error collecting service states: {e}")
        
        return services
    
    def extract_service_name(self, container_name: str) -> str:
        """Extract service name from container name"""
        # Remove prefix and suffix from container names
        name = container_name.lstrip("/")
        
        # Handle docker-compose naming convention
        if "-" in name:
            parts = name.split("-")
            if len(parts) >= 2:
                return parts[1]  # Usually the service name
        
        return name
    
    async def collect_configurations(self) -> Dict[str, Any]:
        """Collect current system configurations"""
        configurations = {}
        
        try:
            # Collect key configuration hashes (not full configs for security)
            config_files = [
                "/config/prometheus/prometheus.yml",
                "/config/caddy/Caddyfile",
                "/config/redis/redis.conf"
            ]
            
            for config_file in config_files:
                try:
                    # Calculate hash of config file (simplified for demo)
                    config_hash = hashlib.md5(config_file.encode()).hexdigest()
                    configurations[config_file] = {"hash": config_hash, "timestamp": datetime.utcnow().isoformat()}
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error collecting configurations: {e}")
        
        return configurations
    
    async def collect_database_state(self) -> Optional[Dict[str, Any]]:
        """Collect database state metadata (not actual data)"""
        try:
            database_state = {
                "connection_test": False,
                "table_count": 0,
                "last_backup": None,
                "migration_version": None
            }
            
            # Test database connection
            try:
                conn = psycopg2.connect(
                    self.config.DATABASE_URL,
                    cursor_factory=RealDictCursor,
                    connect_timeout=5
                )
                
                with conn.cursor() as cursor:
                    # Test connection
                    cursor.execute("SELECT 1")
                    database_state["connection_test"] = True
                    
                    # Get table count
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """)
                    database_state["table_count"] = cursor.fetchone()[0]
                    
                    # Get migration version if available
                    try:
                        cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
                        result = cursor.fetchone()
                        if result:
                            database_state["migration_version"] = result[0]
                    except Exception:
                        pass
                
                conn.close()
                
            except Exception as e:
                logger.debug(f"Database state collection failed: {e}")
                
            return database_state
            
        except Exception as e:
            logger.error(f"Error collecting database state: {e}")
            return None
    
    async def collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {}
        
        try:
            # Get cached metrics from Redis
            for service in self.config.MONITORED_SERVICES:
                cache_key = f"infrastructure:metrics:{service}"
                cached_metrics = await self.redis_client.get(cache_key)
                
                if cached_metrics:
                    try:
                        metrics[service] = eval(cached_metrics)  # Note: Use proper JSON in production
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"Error collecting current metrics: {e}")
        
        return metrics
    
    async def is_snapshot_rollback_safe(self, health_scores: Dict[str, float]) -> bool:
        """Determine if snapshot is safe for rollback"""
        try:
            # Check if all critical services have good health scores
            critical_services = ["postgres", "redis", "api"]
            
            for service in critical_services:
                health_score = health_scores.get(service, 0.0)
                if health_score < 0.8:  # 80% health threshold
                    return False
            
            # Check if overall system health is good
            if health_scores:
                avg_health = sum(health_scores.values()) / len(health_scores)
                if avg_health < 0.7:  # 70% average health
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error determining snapshot safety: {e}")
            return False
    
    async def store_snapshot(self, snapshot: SystemSnapshot):
        """Store snapshot in Redis and local memory"""
        try:
            # Store in Redis
            await self.redis_client.setex(
                f"rollback:snapshot:{snapshot.snapshot_id}",
                86400 * 7,  # 7 days TTL
                json.dumps(snapshot.to_dict())
            )
            
            # Store in local memory
            self.snapshots[snapshot.snapshot_id] = snapshot
            
        except Exception as e:
            logger.error(f"Error storing snapshot {snapshot.snapshot_id}: {e}")
    
    async def cleanup_old_snapshots(self):
        """Clean up old snapshots beyond retention limit"""
        try:
            # Get all snapshot IDs sorted by timestamp
            snapshot_ids = list(self.snapshots.keys())
            snapshot_ids.sort(key=lambda x: self.snapshots[x].timestamp, reverse=True)
            
            # Keep only the most recent snapshots
            max_snapshots = self.config.MAX_ROLLBACK_SNAPSHOTS
            
            if len(snapshot_ids) > max_snapshots:
                old_snapshots = snapshot_ids[max_snapshots:]
                
                for snapshot_id in old_snapshots:
                    # Remove from Redis
                    await self.redis_client.delete(f"rollback:snapshot:{snapshot_id}")
                    
                    # Remove from local memory
                    if snapshot_id in self.snapshots:
                        del self.snapshots[snapshot_id]
                
                logger.info(f"Cleaned up {len(old_snapshots)} old snapshots")
                
        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}")
    
    async def rollback_monitoring_loop(self):
        """Main loop for monitoring rollback triggers"""
        while self.running:
            try:
                await self.monitor_rollback_triggers()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in rollback monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def monitor_rollback_triggers(self):
        """Monitor for conditions that should trigger rollbacks"""
        try:
            health_scores = await predictive_monitor.get_all_health_scores()
            
            for service, health_score in health_scores.items():
                # Check for health degradation
                if health_score < self.rollback_thresholds[RollbackTrigger.HEALTH_DEGRADATION]:
                    await self.evaluate_rollback_trigger(
                        service, 
                        RollbackTrigger.HEALTH_DEGRADATION,
                        {"health_score": health_score}
                    )
                
                # Get prediction for the service
                prediction = await predictive_monitor.get_service_prediction(service)
                failure_probability = prediction.get("failure_probability", 0.0)
                
                # Check for high failure probability
                if failure_probability > 0.9:  # Very high failure probability
                    await self.evaluate_rollback_trigger(
                        service,
                        RollbackTrigger.PERFORMANCE_REGRESSION,
                        {"failure_probability": failure_probability, "prediction": prediction}
                    )
                
                # Check dependency health
                dependency_health = await self.calculate_dependency_health(service)
                if dependency_health < self.rollback_thresholds[RollbackTrigger.DEPENDENCY_FAILURE]:
                    await self.evaluate_rollback_trigger(
                        service,
                        RollbackTrigger.DEPENDENCY_FAILURE,
                        {"dependency_health": dependency_health}
                    )
            
        except Exception as e:
            logger.error(f"Error monitoring rollback triggers: {e}")
    
    async def calculate_dependency_health(self, service: str) -> float:
        """Calculate overall health of service dependencies"""
        try:
            dependencies = self.config.CRITICAL_SERVICE_DEPENDENCIES.get(service, [])
            
            if not dependencies:
                return 1.0
            
            health_scores = await predictive_monitor.get_all_health_scores()
            dependency_scores = [
                health_scores.get(dep, 0.0) for dep in dependencies
            ]
            
            return sum(dependency_scores) / len(dependency_scores)
            
        except Exception as e:
            logger.error(f"Error calculating dependency health for {service}: {e}")
            return 1.0
    
    async def evaluate_rollback_trigger(self, service: str, trigger: RollbackTrigger, 
                                      context: Dict[str, Any]):
        """Evaluate whether a rollback should be triggered"""
        try:
            # Check if service already has an active rollback
            if self.has_active_rollback(service):
                return
            
            # Find the best rollback target
            target_snapshot = await self.find_rollback_target(service)
            
            if not target_snapshot:
                logger.warning(f"No suitable rollback target found for {service}")
                return
            
            # Create rollback operation
            rollback_operation = RollbackOperation(
                rollback_id=f"rollback_{service}_{int(time.time())}",
                trigger=trigger,
                target_snapshot_id=target_snapshot.snapshot_id,
                affected_services=[service],
                created_at=datetime.utcnow()
            )
            
            # Log trigger evaluation
            logger.warning(
                f"Rollback trigger evaluated for {service}: {trigger.value} - "
                f"Target snapshot: {target_snapshot.snapshot_id}"
            )
            
            # Queue rollback for execution
            await self.queue_rollback_operation(rollback_operation)
            
        except Exception as e:
            logger.error(f"Error evaluating rollback trigger for {service}: {e}")
    
    def has_active_rollback(self, service: str) -> bool:
        """Check if service has an active rollback operation"""
        return any(
            service in rollback.affected_services and 
            rollback.status in [RollbackStatus.PENDING, RollbackStatus.IN_PROGRESS]
            for rollback in self.active_rollbacks.values()
        )
    
    async def find_rollback_target(self, service: str) -> Optional[SystemSnapshot]:
        """Find the best snapshot to rollback to"""
        try:
            # Get all rollback-safe snapshots
            safe_snapshots = [
                snapshot for snapshot in self.snapshots.values()
                if snapshot.rollback_safe and service in snapshot.services
            ]
            
            if not safe_snapshots:
                return None
            
            # Sort by timestamp (most recent first)
            safe_snapshots.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Find the most recent snapshot where the service was healthy
            for snapshot in safe_snapshots:
                service_health = snapshot.health_scores.get(service, 0.0)
                if service_health > 0.8:  # Good health threshold
                    return snapshot
            
            # If no healthy snapshot found, return the most recent safe snapshot
            return safe_snapshots[0] if safe_snapshots else None
            
        except Exception as e:
            logger.error(f"Error finding rollback target for {service}: {e}")
            return None
    
    async def queue_rollback_operation(self, rollback_operation: RollbackOperation):
        """Queue rollback operation for execution"""
        try:
            # Add to active rollbacks
            self.active_rollbacks[rollback_operation.rollback_id] = rollback_operation
            
            # Store in Redis for persistence
            await self.redis_client.setex(
                f"rollback:operation:{rollback_operation.rollback_id}",
                3600,  # 1 hour TTL
                json.dumps({
                    "rollback_id": rollback_operation.rollback_id,
                    "trigger": rollback_operation.trigger.value,
                    "target_snapshot_id": rollback_operation.target_snapshot_id,
                    "affected_services": rollback_operation.affected_services,
                    "created_at": rollback_operation.created_at.isoformat(),
                    "status": rollback_operation.status.value
                })
            )
            
            logger.info(f"Queued rollback operation: {rollback_operation.rollback_id}")
            
        except Exception as e:
            logger.error(f"Error queueing rollback operation: {e}")
    
    async def rollback_execution_loop(self):
        """Main loop for executing rollback operations"""
        while self.running:
            try:
                await self.execute_pending_rollbacks()
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error(f"Error in rollback execution loop: {e}")
                await asyncio.sleep(10)
    
    async def execute_pending_rollbacks(self):
        """Execute pending rollback operations"""
        try:
            # Get pending rollbacks sorted by priority
            pending_rollbacks = [
                rollback for rollback in self.active_rollbacks.values()
                if rollback.status == RollbackStatus.PENDING
            ]
            
            if not pending_rollbacks:
                return
            
            # Sort by service priority (critical services first)
            pending_rollbacks.sort(
                key=lambda r: min(
                    self.rollback_priorities.get(service, 999) 
                    for service in r.affected_services
                )
            )
            
            # Execute highest priority rollback
            rollback_operation = pending_rollbacks[0]
            await self.execute_rollback_operation(rollback_operation)
            
        except Exception as e:
            logger.error(f"Error executing pending rollbacks: {e}")
    
    async def execute_rollback_operation(self, rollback_operation: RollbackOperation):
        """Execute a specific rollback operation"""
        try:
            # Mark as in progress
            rollback_operation.status = RollbackStatus.IN_PROGRESS
            rollback_operation.started_at = datetime.utcnow()
            
            logger.info(
                f"Executing rollback operation: {rollback_operation.rollback_id} "
                f"(trigger: {rollback_operation.trigger.value})"
            )
            
            # Get target snapshot
            target_snapshot = self.snapshots.get(rollback_operation.target_snapshot_id)
            
            if not target_snapshot:
                rollback_operation.status = RollbackStatus.FAILED
                rollback_operation.failure_reason = "Target snapshot not found"
                return
            
            # Execute rollback steps for each affected service
            success_count = 0
            total_services = len(rollback_operation.affected_services)
            
            for service in rollback_operation.affected_services:
                try:
                    success = await self.rollback_service(service, target_snapshot)
                    
                    rollback_operation.rollback_steps.append({
                        "service": service,
                        "success": success,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    if success:
                        success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error rolling back service {service}: {e}")
                    rollback_operation.rollback_steps.append({
                        "service": service,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Determine final status
            if success_count == total_services:
                rollback_operation.status = RollbackStatus.COMPLETED
            elif success_count > 0:
                rollback_operation.status = RollbackStatus.PARTIAL
            else:
                rollback_operation.status = RollbackStatus.FAILED
            
            # Verify rollback success
            if rollback_operation.status in [RollbackStatus.COMPLETED, RollbackStatus.PARTIAL]:
                await self.verify_rollback_success(rollback_operation)
            
            rollback_operation.completed_at = datetime.utcnow()
            
            # Move to history
            self.rollback_history.append(rollback_operation)
            del self.active_rollbacks[rollback_operation.rollback_id]
            
            # Log completion
            logger.info(
                f"Rollback operation completed: {rollback_operation.rollback_id} "
                f"(status: {rollback_operation.status.value})"
            )
            
        except Exception as e:
            rollback_operation.status = RollbackStatus.FAILED
            rollback_operation.failure_reason = str(e)
            rollback_operation.completed_at = datetime.utcnow()
            
            logger.error(f"Error executing rollback operation {rollback_operation.rollback_id}: {e}")
    
    async def rollback_service(self, service: str, target_snapshot: SystemSnapshot) -> bool:
        """Rollback a specific service to target snapshot state"""
        try:
            target_service_state = target_snapshot.services.get(service)
            
            if not target_service_state:
                logger.error(f"Service {service} not found in target snapshot")
                return False
            
            # Get current container
            containers = self.docker_client.containers.list(
                all=True,
                filters={"name": service}
            )
            
            if not containers:
                logger.error(f"Container {service} not found")
                return False
            
            current_container = containers[0]
            target_image = target_service_state.get("image", "")
            
            # Check if we need to change the image
            current_image = current_container.image.tags[0] if current_container.image.tags else ""
            
            if current_image != target_image and target_image:
                # Pull target image
                try:
                    self.docker_client.images.pull(target_image)
                except Exception as e:
                    logger.warning(f"Could not pull target image {target_image}: {e}")
            
            # Stop current container
            if current_container.status == "running":
                current_container.stop(timeout=30)
            
            # Remove current container
            current_container.remove()
            
            # Create new container with target configuration
            target_config = target_service_state.get("config", {})
            
            # Start new container (simplified - in production, use docker-compose)
            new_container = self.docker_client.containers.run(
                image=target_image or current_image,
                name=service,
                environment=target_config.get("env", []),
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Wait for container to be healthy
            await self.wait_for_service_health(service, timeout=120)
            
            logger.info(f"Successfully rolled back service {service}")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back service {service}: {e}")
            return False
    
    async def wait_for_service_health(self, service: str, timeout: int = 120):
        """Wait for service to become healthy after rollback"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check health score
                health_score = await predictive_monitor.get_service_health_score(service)
                
                if health_score > 0.7:  # Healthy threshold
                    return True
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.debug(f"Error checking service health for {service}: {e}")
                await asyncio.sleep(5)
        
        raise Exception(f"Service {service} did not become healthy within {timeout} seconds")
    
    async def verify_rollback_success(self, rollback_operation: RollbackOperation):
        """Verify that rollback operation was successful"""
        try:
            # Wait a bit for services to stabilize
            await asyncio.sleep(30)
            
            success_metrics = {}
            
            for service in rollback_operation.affected_services:
                # Check health score
                health_score = await predictive_monitor.get_service_health_score(service)
                success_metrics[f"{service}_health_score"] = health_score
                
                # Check prediction
                prediction = await predictive_monitor.get_service_prediction(service)
                failure_probability = prediction.get("failure_probability", 0.0)
                success_metrics[f"{service}_failure_probability"] = failure_probability
            
            rollback_operation.success_metrics = success_metrics
            
            # Log success metrics
            logger.info(f"Rollback verification for {rollback_operation.rollback_id}: {success_metrics}")
            
        except Exception as e:
            logger.error(f"Error verifying rollback success: {e}")
    
    async def maintenance_loop(self):
        """Maintenance loop for cleanup and housekeeping"""
        while self.running:
            try:
                await self.cleanup_completed_rollbacks()
                await asyncio.sleep(600)  # Run every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
                await asyncio.sleep(120)
    
    async def cleanup_completed_rollbacks(self):
        """Clean up old completed rollback operations"""
        try:
            # Keep only recent history (last 50 rollbacks)
            if len(self.rollback_history) > 50:
                self.rollback_history = self.rollback_history[-50:]
            
            # Clean up Redis keys for old rollbacks
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            keys_to_delete = []
            
            keys = await self.redis_client.keys("rollback:operation:*")
            for key in keys:
                operation_data = await self.redis_client.get(key)
                if operation_data:
                    data = json.loads(operation_data)
                    created_at = datetime.fromisoformat(data["created_at"])
                    if created_at < cutoff_time:
                        keys_to_delete.append(key)
            
            if keys_to_delete:
                await self.redis_client.delete(*keys_to_delete)
                logger.info(f"Cleaned up {len(keys_to_delete)} old rollback operations")
                
        except Exception as e:
            logger.error(f"Error cleaning up completed rollbacks: {e}")
    
    async def load_snapshots(self):
        """Load existing snapshots from Redis"""
        try:
            keys = await self.redis_client.keys("rollback:snapshot:*")
            
            for key in keys:
                snapshot_data = await self.redis_client.get(key)
                if snapshot_data:
                    try:
                        snapshot = SystemSnapshot.from_dict(json.loads(snapshot_data))
                        self.snapshots[snapshot.snapshot_id] = snapshot
                    except Exception as e:
                        logger.error(f"Error loading snapshot from {key}: {e}")
            
            logger.info(f"Loaded {len(self.snapshots)} snapshots from cache")
            
        except Exception as e:
            logger.error(f"Error loading snapshots: {e}")
    
    async def load_rollback_history(self):
        """Load rollback history from Redis"""
        try:
            keys = await self.redis_client.keys("rollback:operation:*")
            
            for key in keys:
                operation_data = await self.redis_client.get(key)
                if operation_data:
                    try:
                        data = json.loads(operation_data)
                        rollback_operation = RollbackOperation(
                            rollback_id=data["rollback_id"],
                            trigger=RollbackTrigger(data["trigger"]),
                            target_snapshot_id=data["target_snapshot_id"],
                            affected_services=data["affected_services"],
                            created_at=datetime.fromisoformat(data["created_at"]),
                            status=RollbackStatus(data["status"])
                        )
                        
                        # Add to appropriate collection based on status
                        if rollback_operation.status in [RollbackStatus.PENDING, RollbackStatus.IN_PROGRESS]:
                            self.active_rollbacks[rollback_operation.rollback_id] = rollback_operation
                        else:
                            self.rollback_history.append(rollback_operation)
                            
                    except Exception as e:
                        logger.error(f"Error loading rollback operation from {key}: {e}")
            
            logger.info(
                f"Loaded {len(self.active_rollbacks)} active rollbacks and "
                f"{len(self.rollback_history)} historical rollbacks"
            )
            
        except Exception as e:
            logger.error(f"Error loading rollback history: {e}")
    
    async def manual_rollback(self, service: str, snapshot_id: Optional[str] = None) -> str:
        """Trigger manual rollback for a service"""
        try:
            # Find target snapshot
            if snapshot_id:
                target_snapshot = self.snapshots.get(snapshot_id)
                if not target_snapshot:
                    raise ValueError(f"Snapshot {snapshot_id} not found")
            else:
                target_snapshot = await self.find_rollback_target(service)
                if not target_snapshot:
                    raise ValueError(f"No suitable rollback target found for {service}")
            
            # Create rollback operation
            rollback_operation = RollbackOperation(
                rollback_id=f"manual_rollback_{service}_{int(time.time())}",
                trigger=RollbackTrigger.MANUAL_TRIGGER,
                target_snapshot_id=target_snapshot.snapshot_id,
                affected_services=[service],
                created_at=datetime.utcnow()
            )
            
            # Queue for execution
            await self.queue_rollback_operation(rollback_operation)
            
            return rollback_operation.rollback_id
            
        except Exception as e:
            logger.error(f"Error triggering manual rollback for {service}: {e}")
            raise
    
    async def get_rollback_status(self) -> Dict[str, Any]:
        """Get current rollback system status"""
        try:
            return {
                "running": self.running,
                "snapshots_count": len(self.snapshots),
                "active_rollbacks": len(self.active_rollbacks),
                "rollback_history_count": len(self.rollback_history),
                "latest_snapshot": max(
                    (s.timestamp for s in self.snapshots.values()),
                    default=None
                ),
                "rollback_safe_snapshots": sum(
                    1 for s in self.snapshots.values() if s.rollback_safe
                ),
                "recent_rollbacks": [
                    {
                        "rollback_id": r.rollback_id,
                        "trigger": r.trigger.value,
                        "services": r.affected_services,
                        "status": r.status.value,
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None
                    }
                    for r in self.rollback_history[-5:]  # Last 5 rollbacks
                ]
            }
        except Exception as e:
            logger.error(f"Error getting rollback status: {e}")
            return {"error": str(e)}
    
    async def stop_rollback_manager(self):
        """Stop the rollback management system"""
        self.running = False
        
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Enhanced Rollback Manager stopped")


# Global rollback manager instance
rollback_manager = EnhancedRollbackManager()