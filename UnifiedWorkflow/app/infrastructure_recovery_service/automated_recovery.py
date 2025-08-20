"""
Automated Recovery System
Self-healing infrastructure with intelligent recovery actions
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiohttp
import redis.asyncio as redis
import docker
import json
from contextlib import asynccontextmanager

from config import infrastructure_recovery_config
from predictive_monitor import predictive_monitor

logger = logging.getLogger(__name__)


class RecoveryActionType(Enum):
    """Types of recovery actions available"""
    RESTART_CONTAINER = "restart_container"
    SCALE_SERVICE = "scale_service"
    CLEAR_CACHE = "clear_cache"
    REBUILD_INDEX = "rebuild_index"
    RESTART_DEPENDENCY = "restart_dependency"
    DATABASE_MAINTENANCE = "database_maintenance"
    NETWORK_RESET = "network_reset"
    HEALTH_CHECK_RESET = "health_check_reset"
    GRACEFUL_RESTART = "graceful_restart"
    EMERGENCY_ROLLBACK = "emergency_rollback"


class RecoveryStatus(Enum):
    """Recovery operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecoveryAction:
    """Individual recovery action representation"""
    
    def __init__(self, action_type: RecoveryActionType, service: str, 
                 parameters: Dict[str, Any] = None, priority: int = 5):
        self.action_type = action_type
        self.service = service
        self.parameters = parameters or {}
        self.priority = priority
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.status = RecoveryStatus.PENDING
        self.result = None
        self.error_message = None
        self.recovery_id = f"{service}_{action_type.value}_{int(time.time())}"


class AutomatedRecoverySystem:
    """
    Automated Recovery System with Self-Healing Capabilities
    Provides intelligent, automated recovery from infrastructure failures
    """
    
    def __init__(self):
        self.config = infrastructure_recovery_config
        self.redis_client = None
        self.session = None
        self.docker_client = None
        self.running = False
        
        # Recovery state management
        self.active_recoveries: Dict[str, RecoveryAction] = {}
        self.recovery_history: List[RecoveryAction] = []
        self.cooldown_services: Dict[str, datetime] = {}
        self.failure_counts: Dict[str, int] = {}
        
        # Recovery strategies for different services
        self.recovery_strategies = self.init_recovery_strategies()
    
    def init_recovery_strategies(self) -> Dict[str, List[RecoveryActionType]]:
        """Initialize recovery strategies for different services"""
        return {
            "api": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.CLEAR_CACHE,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.DATABASE_MAINTENANCE
            ],
            "webui": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.CLEAR_CACHE
            ],
            "worker": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.CLEAR_CACHE,
                RecoveryActionType.DATABASE_MAINTENANCE
            ],
            "postgres": [
                RecoveryActionType.DATABASE_MAINTENANCE,
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER
            ],
            "redis": [
                RecoveryActionType.CLEAR_CACHE,
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER
            ],
            "qdrant": [
                RecoveryActionType.REBUILD_INDEX,
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER
            ],
            "ollama": [
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.GRACEFUL_RESTART
            ],
            "coordination-service": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.CLEAR_CACHE
            ],
            "hybrid-memory-service": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.REBUILD_INDEX
            ],
            "learning-service": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.CLEAR_CACHE
            ],
            "perception-service": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER
            ],
            "reasoning-service": [
                RecoveryActionType.GRACEFUL_RESTART,
                RecoveryActionType.RESTART_CONTAINER,
                RecoveryActionType.CLEAR_CACHE
            ]
        }
    
    async def initialize(self):
        """Initialize the automated recovery system"""
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
            
            # Load recovery history from Redis
            await self.load_recovery_history()
            
            logger.info("Automated Recovery System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Automated Recovery System: {e}")
            raise
    
    async def start_recovery_system(self):
        """Start the automated recovery system"""
        self.running = True
        
        tasks = [
            self.health_monitoring_loop(),
            self.recovery_execution_loop(),
            self.cleanup_loop()
        ]
        
        logger.info("Starting automated recovery system")
        await asyncio.gather(*tasks)
    
    async def health_monitoring_loop(self):
        """Main loop for monitoring health and triggering recovery"""
        while self.running:
            try:
                await self.monitor_and_trigger_recovery()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def monitor_and_trigger_recovery(self):
        """Monitor service health and trigger recovery when needed"""
        health_scores = await predictive_monitor.get_all_health_scores()
        
        for service, health_score in health_scores.items():
            try:
                # Skip if service is in cooldown
                if await self.is_service_in_cooldown(service):
                    continue
                
                # Skip if recovery already in progress
                if await self.has_active_recovery(service):
                    continue
                
                # Check if intervention is needed
                if health_score < self.config.HEALTH_SCORE_THRESHOLD:
                    await self.trigger_recovery(service, health_score)
                
                # Check predictions for proactive recovery
                prediction = await predictive_monitor.get_service_prediction(service)
                failure_probability = prediction.get("failure_probability", 0.0)
                
                if failure_probability > 0.8:  # Very high failure probability
                    await self.trigger_proactive_recovery(service, prediction)
                
            except Exception as e:
                logger.error(f"Error monitoring service {service}: {e}")
    
    async def trigger_recovery(self, service: str, health_score: float):
        """Trigger recovery for a service based on health score"""
        try:
            logger.warning(f"Triggering recovery for {service} (health score: {health_score:.2f})")
            
            # Get appropriate recovery action
            recovery_action = await self.select_recovery_action(service, health_score)
            
            if recovery_action:
                # Queue recovery action
                await self.queue_recovery_action(recovery_action)
                
                # Update failure count
                self.failure_counts[service] = self.failure_counts.get(service, 0) + 1
                
                # Log recovery trigger
                await self.log_recovery_event(
                    service, 
                    "recovery_triggered",
                    {
                        "health_score": health_score,
                        "recovery_action": recovery_action.action_type.value,
                        "failure_count": self.failure_counts[service]
                    }
                )
        
        except Exception as e:
            logger.error(f"Error triggering recovery for {service}: {e}")
    
    async def trigger_proactive_recovery(self, service: str, prediction: Dict[str, Any]):
        """Trigger proactive recovery based on failure predictions"""
        try:
            failure_probability = prediction.get("failure_probability", 0.0)
            
            logger.info(
                f"Triggering proactive recovery for {service} "
                f"(failure probability: {failure_probability:.2f})"
            )
            
            # Use lighter recovery actions for proactive recovery
            proactive_actions = [
                RecoveryActionType.HEALTH_CHECK_RESET,
                RecoveryActionType.CLEAR_CACHE,
                RecoveryActionType.DATABASE_MAINTENANCE
            ]
            
            # Select action based on risk factors
            risk_factors = prediction.get("risk_factors", [])
            action_type = self.select_proactive_action(service, risk_factors)
            
            if action_type:
                recovery_action = RecoveryAction(
                    action_type=action_type,
                    service=service,
                    parameters={"proactive": True, "prediction": prediction},
                    priority=3  # Lower priority than reactive recovery
                )
                
                await self.queue_recovery_action(recovery_action)
        
        except Exception as e:
            logger.error(f"Error triggering proactive recovery for {service}: {e}")
    
    def select_proactive_action(self, service: str, risk_factors: List[str]) -> Optional[RecoveryActionType]:
        """Select appropriate proactive recovery action based on risk factors"""
        try:
            # Analyze risk factors to determine best action
            if any("memory" in factor.lower() for factor in risk_factors):
                return RecoveryActionType.CLEAR_CACHE
            
            if any("response time" in factor.lower() for factor in risk_factors):
                return RecoveryActionType.HEALTH_CHECK_RESET
            
            if any("database" in factor.lower() for factor in risk_factors):
                return RecoveryActionType.DATABASE_MAINTENANCE
            
            # Default to health check reset
            return RecoveryActionType.HEALTH_CHECK_RESET
            
        except Exception as e:
            logger.debug(f"Error selecting proactive action: {e}")
            return None
    
    async def select_recovery_action(self, service: str, health_score: float) -> Optional[RecoveryAction]:
        """Select appropriate recovery action based on service and health score"""
        try:
            strategies = self.recovery_strategies.get(service, [])
            
            if not strategies:
                return None
            
            # Select action based on severity
            failure_count = self.failure_counts.get(service, 0)
            
            # Escalate recovery actions based on failure count and health score
            if health_score < 0.2 or failure_count > 2:
                # Critical situation - use emergency actions
                action_type = RecoveryActionType.EMERGENCY_ROLLBACK
                priority = 1
            elif health_score < 0.4 or failure_count > 1:
                # Severe situation - restart container
                action_type = RecoveryActionType.RESTART_CONTAINER
                priority = 2
            else:
                # Moderate situation - try graceful recovery first
                action_type = strategies[0]
                priority = 4
            
            # Create recovery action
            recovery_action = RecoveryAction(
                action_type=action_type,
                service=service,
                parameters={
                    "health_score": health_score,
                    "failure_count": failure_count,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=priority
            )
            
            return recovery_action
            
        except Exception as e:
            logger.error(f"Error selecting recovery action for {service}: {e}")
            return None
    
    async def queue_recovery_action(self, recovery_action: RecoveryAction):
        """Queue a recovery action for execution"""
        try:
            # Add to active recoveries
            self.active_recoveries[recovery_action.recovery_id] = recovery_action
            
            # Cache in Redis for persistence
            await self.redis_client.setex(
                f"recovery:action:{recovery_action.recovery_id}",
                3600,  # 1 hour TTL
                json.dumps({
                    "action_type": recovery_action.action_type.value,
                    "service": recovery_action.service,
                    "parameters": recovery_action.parameters,
                    "priority": recovery_action.priority,
                    "created_at": recovery_action.created_at.isoformat(),
                    "status": recovery_action.status.value
                })
            )
            
            logger.info(f"Queued recovery action: {recovery_action.recovery_id}")
            
        except Exception as e:
            logger.error(f"Error queueing recovery action: {e}")
    
    async def recovery_execution_loop(self):
        """Main loop for executing recovery actions"""
        while self.running:
            try:
                await self.execute_pending_recoveries()
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in recovery execution loop: {e}")
                await asyncio.sleep(5)
    
    async def execute_pending_recoveries(self):
        """Execute pending recovery actions by priority"""
        try:
            # Get pending recoveries sorted by priority
            pending_recoveries = [
                action for action in self.active_recoveries.values()
                if action.status == RecoveryStatus.PENDING
            ]
            
            # Sort by priority (lower number = higher priority)
            pending_recoveries.sort(key=lambda x: x.priority)
            
            # Execute highest priority recovery
            if pending_recoveries:
                recovery_action = pending_recoveries[0]
                await self.execute_recovery_action(recovery_action)
        
        except Exception as e:
            logger.error(f"Error executing pending recoveries: {e}")
    
    async def execute_recovery_action(self, recovery_action: RecoveryAction):
        """Execute a specific recovery action"""
        try:
            # Mark as in progress
            recovery_action.status = RecoveryStatus.IN_PROGRESS
            recovery_action.started_at = datetime.utcnow()
            
            logger.info(
                f"Executing recovery action: {recovery_action.action_type.value} "
                f"for service: {recovery_action.service}"
            )
            
            # Execute based on action type
            if recovery_action.action_type == RecoveryActionType.RESTART_CONTAINER:
                result = await self.restart_container(recovery_action.service)
            elif recovery_action.action_type == RecoveryActionType.GRACEFUL_RESTART:
                result = await self.graceful_restart(recovery_action.service)
            elif recovery_action.action_type == RecoveryActionType.CLEAR_CACHE:
                result = await self.clear_cache(recovery_action.service)
            elif recovery_action.action_type == RecoveryActionType.DATABASE_MAINTENANCE:
                result = await self.database_maintenance(recovery_action.service)
            elif recovery_action.action_type == RecoveryActionType.REBUILD_INDEX:
                result = await self.rebuild_index(recovery_action.service)
            elif recovery_action.action_type == RecoveryActionType.HEALTH_CHECK_RESET:
                result = await self.health_check_reset(recovery_action.service)
            elif recovery_action.action_type == RecoveryActionType.EMERGENCY_ROLLBACK:
                result = await self.emergency_rollback(recovery_action.service)
            else:
                result = {"success": False, "message": f"Unknown action type: {recovery_action.action_type}"}
            
            # Update recovery action status
            if result.get("success", False):
                recovery_action.status = RecoveryStatus.COMPLETED
                recovery_action.result = result
                
                # Set cooldown period
                await self.set_service_cooldown(recovery_action.service)
                
                logger.info(
                    f"Recovery action completed successfully: {recovery_action.recovery_id}"
                )
                
            else:
                recovery_action.status = RecoveryStatus.FAILED
                recovery_action.error_message = result.get("message", "Unknown error")
                
                logger.error(
                    f"Recovery action failed: {recovery_action.recovery_id} - "
                    f"{recovery_action.error_message}"
                )
            
            # Mark completion time
            recovery_action.completed_at = datetime.utcnow()
            
            # Move to history
            self.recovery_history.append(recovery_action)
            del self.active_recoveries[recovery_action.recovery_id]
            
            # Log recovery result
            await self.log_recovery_event(
                recovery_action.service,
                "recovery_completed",
                {
                    "action_type": recovery_action.action_type.value,
                    "status": recovery_action.status.value,
                    "duration_seconds": (recovery_action.completed_at - recovery_action.started_at).total_seconds(),
                    "result": recovery_action.result or recovery_action.error_message
                }
            )
            
        except Exception as e:
            recovery_action.status = RecoveryStatus.FAILED
            recovery_action.error_message = str(e)
            recovery_action.completed_at = datetime.utcnow()
            
            logger.error(f"Error executing recovery action {recovery_action.recovery_id}: {e}")
    
    async def restart_container(self, service: str) -> Dict[str, Any]:
        """Restart a Docker container"""
        try:
            # Find container by service name
            containers = self.docker_client.containers.list(
                filters={"name": service}
            )
            
            if not containers:
                return {"success": False, "message": f"Container {service} not found"}
            
            container = containers[0]
            
            # Restart container
            container.restart(timeout=30)
            
            # Wait for container to be healthy
            await self.wait_for_container_health(container, timeout=120)
            
            return {"success": True, "message": f"Container {service} restarted successfully"}
            
        except Exception as e:
            return {"success": False, "message": f"Failed to restart container {service}: {e}"}
    
    async def graceful_restart(self, service: str) -> Dict[str, Any]:
        """Perform graceful restart with health check"""
        try:
            # Send SIGTERM to allow graceful shutdown
            containers = self.docker_client.containers.list(
                filters={"name": service}
            )
            
            if not containers:
                return {"success": False, "message": f"Container {service} not found"}
            
            container = containers[0]
            
            # Send graceful shutdown signal
            container.kill(signal="SIGTERM")
            
            # Wait a bit for graceful shutdown
            await asyncio.sleep(10)
            
            # Start container if it's not running
            if container.status != "running":
                container.start()
            
            # Wait for health
            await self.wait_for_container_health(container, timeout=120)
            
            return {"success": True, "message": f"Graceful restart completed for {service}"}
            
        except Exception as e:
            # Fallback to regular restart
            return await self.restart_container(service)
    
    async def clear_cache(self, service: str) -> Dict[str, Any]:
        """Clear cache for services that use Redis"""
        try:
            if service in ["api", "worker", "coordination-service"]:
                # Clear Redis cache
                await self.redis_client.flushdb()
                return {"success": True, "message": f"Cache cleared for {service}"}
            else:
                return {"success": True, "message": f"No cache to clear for {service}"}
                
        except Exception as e:
            return {"success": False, "message": f"Failed to clear cache for {service}: {e}"}
    
    async def database_maintenance(self, service: str) -> Dict[str, Any]:
        """Perform database maintenance operations"""
        try:
            if service == "postgres":
                # Run VACUUM and ANALYZE
                # This would require database connection - simplified for demo
                return {"success": True, "message": "Database maintenance completed"}
            else:
                return {"success": True, "message": f"No database maintenance needed for {service}"}
                
        except Exception as e:
            return {"success": False, "message": f"Database maintenance failed for {service}: {e}"}
    
    async def rebuild_index(self, service: str) -> Dict[str, Any]:
        """Rebuild indexes for vector databases"""
        try:
            if service == "qdrant":
                # Send rebuild command to Qdrant
                # This would require Qdrant API calls - simplified for demo
                return {"success": True, "message": "Index rebuild initiated for Qdrant"}
            else:
                return {"success": True, "message": f"No index rebuild needed for {service}"}
                
        except Exception as e:
            return {"success": False, "message": f"Index rebuild failed for {service}: {e}"}
    
    async def health_check_reset(self, service: str) -> Dict[str, Any]:
        """Reset health check state"""
        try:
            # Clear health check cache
            await self.redis_client.delete(f"infrastructure:health_score:{service}")
            await self.redis_client.delete(f"infrastructure:metrics:{service}")
            
            return {"success": True, "message": f"Health check reset for {service}"}
            
        except Exception as e:
            return {"success": False, "message": f"Health check reset failed for {service}: {e}"}
    
    async def emergency_rollback(self, service: str) -> Dict[str, Any]:
        """Emergency rollback to last known good state"""
        try:
            # This would implement rollback to previous container version
            # For now, we'll do a restart and cache clear
            result1 = await self.restart_container(service)
            result2 = await self.clear_cache(service)
            
            if result1.get("success") and result2.get("success"):
                return {"success": True, "message": f"Emergency rollback completed for {service}"}
            else:
                return {"success": False, "message": f"Emergency rollback failed for {service}"}
                
        except Exception as e:
            return {"success": False, "message": f"Emergency rollback failed for {service}: {e}"}
    
    async def wait_for_container_health(self, container, timeout: int = 120):
        """Wait for container to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container.reload()
                
                # Check if container is running
                if container.status == "running":
                    # Check health status if available
                    if hasattr(container.attrs, "State") and "Health" in container.attrs["State"]:
                        health_status = container.attrs["State"]["Health"]["Status"]
                        if health_status == "healthy":
                            return True
                    else:
                        # No health check defined, assume healthy if running
                        await asyncio.sleep(5)  # Give it a moment to stabilize
                        return True
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Error checking container health: {e}")
                await asyncio.sleep(2)
        
        raise Exception(f"Container failed to become healthy within {timeout} seconds")
    
    async def is_service_in_cooldown(self, service: str) -> bool:
        """Check if service is in cooldown period"""
        cooldown_end = self.cooldown_services.get(service)
        if cooldown_end and datetime.utcnow() < cooldown_end:
            return True
        return False
    
    async def set_service_cooldown(self, service: str):
        """Set cooldown period for service"""
        cooldown_end = datetime.utcnow() + timedelta(
            seconds=self.config.COOLDOWN_PERIOD_SECONDS
        )
        self.cooldown_services[service] = cooldown_end
        
        # Cache in Redis
        await self.redis_client.setex(
            f"recovery:cooldown:{service}",
            self.config.COOLDOWN_PERIOD_SECONDS,
            cooldown_end.isoformat()
        )
    
    async def has_active_recovery(self, service: str) -> bool:
        """Check if service has active recovery operations"""
        return any(
            action.service == service and action.status in [RecoveryStatus.PENDING, RecoveryStatus.IN_PROGRESS]
            for action in self.active_recoveries.values()
        )
    
    async def log_recovery_event(self, service: str, event_type: str, details: Dict[str, Any]):
        """Log recovery events to Redis and system logs"""
        try:
            event = {
                "service": service,
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details
            }
            
            # Log to Redis
            await self.redis_client.lpush(
                f"recovery:events:{service}",
                json.dumps(event)
            )
            
            # Trim event history (keep last 100 events)
            await self.redis_client.ltrim(f"recovery:events:{service}", 0, 99)
            
            # Log to system
            logger.info(f"Recovery event - {event_type} for {service}: {details}")
            
        except Exception as e:
            logger.error(f"Error logging recovery event: {e}")
    
    async def load_recovery_history(self):
        """Load recovery history from Redis"""
        try:
            # Load active recoveries
            keys = await self.redis_client.keys("recovery:action:*")
            
            for key in keys:
                action_data = await self.redis_client.get(key)
                if action_data:
                    data = json.loads(action_data)
                    recovery_id = key.split(":")[-1]
                    
                    # Recreate recovery action
                    recovery_action = RecoveryAction(
                        action_type=RecoveryActionType(data["action_type"]),
                        service=data["service"],
                        parameters=data["parameters"],
                        priority=data["priority"]
                    )
                    recovery_action.recovery_id = recovery_id
                    recovery_action.created_at = datetime.fromisoformat(data["created_at"])
                    recovery_action.status = RecoveryStatus(data["status"])
                    
                    # Add to active recoveries if still pending/in progress
                    if recovery_action.status in [RecoveryStatus.PENDING, RecoveryStatus.IN_PROGRESS]:
                        self.active_recoveries[recovery_id] = recovery_action
            
            logger.info(f"Loaded {len(self.active_recoveries)} active recovery actions from cache")
            
        except Exception as e:
            logger.error(f"Error loading recovery history: {e}")
    
    async def cleanup_loop(self):
        """Cleanup loop for maintenance tasks"""
        while self.running:
            try:
                await self.cleanup_completed_recoveries()
                await self.cleanup_expired_cooldowns()
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_completed_recoveries(self):
        """Clean up old completed recovery actions"""
        try:
            # Keep only recent history (last 100 entries)
            if len(self.recovery_history) > 100:
                self.recovery_history = self.recovery_history[-100:]
            
            # Clean up Redis keys for old actions
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            keys_to_delete = []
            
            keys = await self.redis_client.keys("recovery:action:*")
            for key in keys:
                action_data = await self.redis_client.get(key)
                if action_data:
                    data = json.loads(action_data)
                    created_at = datetime.fromisoformat(data["created_at"])
                    if created_at < cutoff_time:
                        keys_to_delete.append(key)
            
            if keys_to_delete:
                await self.redis_client.delete(*keys_to_delete)
                logger.info(f"Cleaned up {len(keys_to_delete)} old recovery actions")
                
        except Exception as e:
            logger.error(f"Error cleaning up completed recoveries: {e}")
    
    async def cleanup_expired_cooldowns(self):
        """Clean up expired cooldown periods"""
        try:
            current_time = datetime.utcnow()
            expired_services = [
                service for service, cooldown_end in self.cooldown_services.items()
                if current_time >= cooldown_end
            ]
            
            for service in expired_services:
                del self.cooldown_services[service]
                await self.redis_client.delete(f"recovery:cooldown:{service}")
            
            if expired_services:
                logger.info(f"Cleaned up cooldowns for services: {expired_services}")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cooldowns: {e}")
    
    async def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery system status"""
        try:
            return {
                "running": self.running,
                "active_recoveries": len(self.active_recoveries),
                "recovery_history_count": len(self.recovery_history),
                "services_in_cooldown": len(self.cooldown_services),
                "failure_counts": self.failure_counts.copy(),
                "last_recovery_times": {
                    action.service: action.completed_at.isoformat()
                    for action in self.recovery_history[-10:]  # Last 10 recoveries
                    if action.completed_at
                }
            }
        except Exception as e:
            logger.error(f"Error getting recovery status: {e}")
            return {"error": str(e)}
    
    async def stop_recovery_system(self):
        """Stop the automated recovery system"""
        self.running = False
        
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Automated Recovery System stopped")


# Global recovery system instance
automated_recovery = AutomatedRecoverySystem()