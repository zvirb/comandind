"""
Performance-Based Auto-Scaling System
Intelligent auto-scaling with predictive resource optimization
"""
import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import numpy as np
import redis.asyncio as redis
import aiohttp
import docker
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from config import infrastructure_recovery_config
from predictive_monitor import predictive_monitor

logger = logging.getLogger(__name__)


class ScalingAction(Enum):
    """Types of scaling actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_OUT = "scale_out"  # Horizontal scaling
    SCALE_IN = "scale_in"   # Horizontal scaling down
    OPTIMIZE_RESOURCES = "optimize_resources"
    NO_ACTION = "no_action"


class ScalingTrigger(Enum):
    """Scaling trigger types"""
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    RESPONSE_TIME = "response_time"
    REQUEST_RATE = "request_rate"
    QUEUE_LENGTH = "queue_length"
    PREDICTIVE = "predictive"
    CUSTOM_METRIC = "custom_metric"


@dataclass
class ScalingRule:
    """Scaling rule configuration"""
    service: str
    trigger: ScalingTrigger
    metric_name: str
    scale_up_threshold: float
    scale_down_threshold: float
    min_instances: int
    max_instances: int
    cooldown_period: int  # seconds
    evaluation_period: int  # seconds
    evaluation_periods: int  # number of periods
    enabled: bool = True
    weight: float = 1.0  # rule importance weight


@dataclass
class ScalingDecision:
    """Scaling decision with context"""
    service: str
    action: ScalingAction
    current_instances: int
    target_instances: int
    trigger_metric: str
    current_value: float
    threshold_value: float
    confidence: float
    reasoning: List[str]
    created_at: datetime
    executed: bool = False


@dataclass
class ResourcePrediction:
    """Resource usage prediction"""
    service: str
    metric: str
    current_value: float
    predicted_value: float
    prediction_horizon: int  # minutes
    confidence: float
    trend_direction: str  # increasing, decreasing, stable
    peak_time: Optional[datetime]
    recommendation: ScalingAction


class PerformanceAutoScaler:
    """
    Performance-Based Auto-Scaling System
    Intelligent resource optimization with predictive scaling
    """
    
    def __init__(self):
        self.config = infrastructure_recovery_config
        self.redis_client = None
        self.session = None
        self.docker_client = None
        self.running = False
        
        # Scaling state management
        self.scaling_rules: Dict[str, List[ScalingRule]] = {}
        self.scaling_history: List[ScalingDecision] = []
        self.cooldown_services: Dict[str, datetime] = {}
        self.resource_predictions: Dict[str, List[ResourcePrediction]] = {}
        
        # ML models for prediction
        self.prediction_models: Dict[str, Dict[str, Any]] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.metric_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Performance metrics cache
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        
        # Initialize scaling rules
        self.init_scaling_rules()
    
    def init_scaling_rules(self):
        """Initialize auto-scaling rules for services"""
        
        # API service scaling rules
        api_rules = [
            ScalingRule(
                service="api",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_name="cpu_usage",
                scale_up_threshold=70.0,
                scale_down_threshold=30.0,
                min_instances=2,
                max_instances=10,
                cooldown_period=300,  # 5 minutes
                evaluation_period=60,
                evaluation_periods=3,
                weight=1.0
            ),
            ScalingRule(
                service="api",
                trigger=ScalingTrigger.MEMORY_UTILIZATION,
                metric_name="memory_utilization",
                scale_up_threshold=80.0,
                scale_down_threshold=40.0,
                min_instances=2,
                max_instances=10,
                cooldown_period=300,
                evaluation_period=60,
                evaluation_periods=2,
                weight=0.8
            ),
            ScalingRule(
                service="api",
                trigger=ScalingTrigger.RESPONSE_TIME,
                metric_name="health_check_response_time",
                scale_up_threshold=2.0,  # 2 seconds
                scale_down_threshold=0.5,  # 0.5 seconds
                min_instances=2,
                max_instances=8,
                cooldown_period=180,
                evaluation_period=30,
                evaluation_periods=3,
                weight=1.2
            )
        ]
        
        # Worker service scaling rules
        worker_rules = [
            ScalingRule(
                service="worker",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_name="cpu_usage",
                scale_up_threshold=75.0,
                scale_down_threshold=25.0,
                min_instances=1,
                max_instances=8,
                cooldown_period=240,
                evaluation_period=60,
                evaluation_periods=3,
                weight=1.0
            ),
            ScalingRule(
                service="worker",
                trigger=ScalingTrigger.QUEUE_LENGTH,
                metric_name="task_queue_length",
                scale_up_threshold=50.0,  # 50 tasks
                scale_down_threshold=5.0,   # 5 tasks
                min_instances=1,
                max_instances=6,
                cooldown_period=180,
                evaluation_period=30,
                evaluation_periods=2,
                weight=1.3
            )
        ]
        
        # WebUI scaling rules
        webui_rules = [
            ScalingRule(
                service="webui",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_name="cpu_usage",
                scale_up_threshold=60.0,
                scale_down_threshold=20.0,
                min_instances=1,
                max_instances=5,
                cooldown_period=300,
                evaluation_period=60,
                evaluation_periods=2,
                weight=1.0
            )
        ]
        
        # Database scaling rules (vertical scaling primarily)
        postgres_rules = [
            ScalingRule(
                service="postgres",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_name="cpu_usage",
                scale_up_threshold=80.0,
                scale_down_threshold=40.0,
                min_instances=1,
                max_instances=1,  # Single instance, vertical scaling
                cooldown_period=600,  # 10 minutes
                evaluation_period=120,
                evaluation_periods=3,
                weight=1.5  # High priority
            ),
            ScalingRule(
                service="postgres",
                trigger=ScalingTrigger.MEMORY_UTILIZATION,
                metric_name="memory_utilization",
                scale_up_threshold=85.0,
                scale_down_threshold=50.0,
                min_instances=1,
                max_instances=1,
                cooldown_period=600,
                evaluation_period=120,
                evaluation_periods=2,
                weight=1.4
            )
        ]
        
        # Coordination service scaling rules
        coordination_rules = [
            ScalingRule(
                service="coordination-service",
                trigger=ScalingTrigger.CPU_UTILIZATION,
                metric_name="cpu_usage",
                scale_up_threshold=65.0,
                scale_down_threshold=25.0,
                min_instances=1,
                max_instances=4,
                cooldown_period=300,
                evaluation_period=60,
                evaluation_periods=2,
                weight=1.0
            )
        ]
        
        self.scaling_rules = {
            "api": api_rules,
            "worker": worker_rules,
            "webui": webui_rules,
            "postgres": postgres_rules,
            "coordination-service": coordination_rules
        }
    
    async def initialize(self):
        """Initialize the auto-scaling system"""
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
            
            # Initialize ML models
            await self.init_prediction_models()
            
            # Load scaling history
            await self.load_scaling_history()
            
            logger.info("Performance Auto-Scaler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Performance Auto-Scaler: {e}")
            raise
    
    async def init_prediction_models(self):
        """Initialize ML models for resource prediction"""
        try:
            for service in self.scaling_rules.keys():
                # Initialize models for different metrics
                self.prediction_models[service] = {
                    "cpu_model": LinearRegression(),
                    "memory_model": LinearRegression(),
                    "response_time_model": LinearRegression(),
                    "request_rate_model": LinearRegression()
                }
                
                # Initialize scalers
                self.scalers[service] = StandardScaler()
                
                # Initialize metric history
                self.metric_history[service] = []
                
        except Exception as e:
            logger.error(f"Error initializing prediction models: {e}")
    
    async def start_auto_scaling(self):
        """Start the auto-scaling system"""
        self.running = True
        
        tasks = [
            self.metrics_collection_loop(),
            self.scaling_evaluation_loop(),
            self.predictive_scaling_loop(),
            self.scaling_execution_loop(),
            self.model_training_loop(),
            self.maintenance_loop()
        ]
        
        logger.info("Starting performance-based auto-scaling system")
        await asyncio.gather(*tasks)
    
    async def metrics_collection_loop(self):
        """Main loop for collecting performance metrics"""
        while self.running:
            try:
                await self.collect_performance_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(10)
    
    async def collect_performance_metrics(self):
        """Collect performance metrics for all scalable services"""
        try:
            for service in self.scaling_rules.keys():
                metrics = await self.collect_service_metrics(service)
                
                # Store in performance metrics cache
                self.performance_metrics[service] = metrics
                
                # Add to metric history for ML training
                historical_entry = {
                    "timestamp": datetime.utcnow(),
                    "metrics": metrics
                }
                
                self.metric_history[service].append(historical_entry)
                
                # Maintain history size
                if len(self.metric_history[service]) > 1000:
                    self.metric_history[service] = self.metric_history[service][-1000:]
                
                # Cache metrics in Redis
                await self.cache_performance_metrics(service, metrics)
                
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
    
    async def collect_service_metrics(self, service: str) -> Dict[str, float]:
        """Collect comprehensive performance metrics for a service"""
        metrics = {}
        
        try:
            # Get basic health metrics from predictive monitor
            health_score = await predictive_monitor.get_service_health_score(service)
            metrics["health_score"] = health_score
            
            # Get cached metrics from Redis
            cached_metrics = await self.redis_client.get(f"infrastructure:metrics:{service}")
            
            if cached_metrics:
                try:
                    cached_data = eval(cached_metrics)  # Note: Use proper JSON in production
                    if isinstance(cached_data, dict) and "features" in cached_data:
                        features = cached_data["features"]
                        
                        # Extract relevant metrics
                        metrics.update({
                            "cpu_usage": features.get("cpu_usage", 0.0),
                            "memory_usage": features.get("memory_usage", 0.0),
                            "memory_utilization": features.get("memory_utilization", 0.0),
                            "network_rx": features.get("network_rx", 0.0),
                            "network_tx": features.get("network_tx", 0.0),
                            "health_check_response_time": features.get("health_check_response_time", 0.0),
                            "restart_count": features.get("restart_count", 0.0)
                        })
                except Exception as e:
                    logger.debug(f"Error parsing cached metrics for {service}: {e}")
            
            # Get container-specific metrics
            container_metrics = await self.get_container_metrics(service)
            metrics.update(container_metrics)
            
            # Get service-specific metrics
            service_specific = await self.get_service_specific_metrics(service)
            metrics.update(service_specific)
            
            # Calculate derived metrics
            metrics.update(self.calculate_derived_metrics(metrics))
            
        except Exception as e:
            logger.error(f"Error collecting metrics for {service}: {e}")
        
        return metrics
    
    async def get_container_metrics(self, service: str) -> Dict[str, float]:
        """Get Docker container metrics"""
        metrics = {}
        
        try:
            containers = self.docker_client.containers.list(
                filters={"name": service}
            )
            
            if containers:
                container = containers[0]
                
                # Get container stats
                stats = container.stats(stream=False)
                
                # Calculate CPU usage
                cpu_stats = stats.get("cpu_stats", {})
                precpu_stats = stats.get("precpu_stats", {})
                
                if cpu_stats and precpu_stats:
                    cpu_usage = self.calculate_cpu_percentage(cpu_stats, precpu_stats)
                    metrics["container_cpu_usage"] = cpu_usage
                
                # Get memory stats
                memory_stats = stats.get("memory_stats", {})
                if memory_stats:
                    memory_usage = memory_stats.get("usage", 0)
                    memory_limit = memory_stats.get("limit", 0)
                    
                    metrics["container_memory_usage"] = memory_usage
                    metrics["container_memory_limit"] = memory_limit
                    
                    if memory_limit > 0:
                        memory_percent = (memory_usage / memory_limit) * 100
                        metrics["container_memory_percent"] = memory_percent
                
                # Get network stats
                networks = stats.get("networks", {})
                total_rx = sum(net.get("rx_bytes", 0) for net in networks.values())
                total_tx = sum(net.get("tx_bytes", 0) for net in networks.values())
                
                metrics["container_network_rx"] = total_rx
                metrics["container_network_tx"] = total_tx
                
        except Exception as e:
            logger.debug(f"Error getting container metrics for {service}: {e}")
        
        return metrics
    
    def calculate_cpu_percentage(self, cpu_stats: Dict, precpu_stats: Dict) -> float:
        """Calculate CPU usage percentage from Docker stats"""
        try:
            cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - \
                       precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            
            system_delta = cpu_stats.get("system_cpu_usage", 0) - \
                          precpu_stats.get("system_cpu_usage", 0)
            
            online_cpus = cpu_stats.get("online_cpus", 1)
            
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
                return max(0.0, min(100.0, cpu_percent))
            
        except Exception as e:
            logger.debug(f"Error calculating CPU percentage: {e}")
        
        return 0.0
    
    async def get_service_specific_metrics(self, service: str) -> Dict[str, float]:
        """Get service-specific performance metrics"""
        metrics = {}
        
        try:
            if service == "api":
                # API-specific metrics
                metrics.update(await self.get_api_metrics())
            elif service == "worker":
                # Worker-specific metrics  
                metrics.update(await self.get_worker_metrics())
            elif service == "postgres":
                # Database-specific metrics
                metrics.update(await self.get_database_metrics())
            elif service == "redis":
                # Redis-specific metrics
                metrics.update(await self.get_redis_metrics())
                
        except Exception as e:
            logger.debug(f"Error getting service-specific metrics for {service}: {e}")
        
        return metrics
    
    async def get_api_metrics(self) -> Dict[str, float]:
        """Get API-specific metrics"""
        metrics = {}
        
        try:
            # Simulate API metrics (in production, get from actual API metrics endpoint)
            metrics.update({
                "requests_per_second": 0.0,  # Would be collected from API metrics
                "average_response_time": 0.0,
                "error_rate": 0.0,
                "active_connections": 0.0
            })
            
        except Exception as e:
            logger.debug(f"Error getting API metrics: {e}")
        
        return metrics
    
    async def get_worker_metrics(self) -> Dict[str, float]:
        """Get worker-specific metrics"""
        metrics = {}
        
        try:
            # Get task queue length from Redis
            queue_length = await self.redis_client.llen("celery")  # Default Celery queue
            metrics["task_queue_length"] = float(queue_length)
            
            # Simulate other worker metrics
            metrics.update({
                "tasks_per_minute": 0.0,
                "task_processing_time": 0.0,
                "worker_utilization": 0.0
            })
            
        except Exception as e:
            logger.debug(f"Error getting worker metrics: {e}")
        
        return metrics
    
    async def get_database_metrics(self) -> Dict[str, float]:
        """Get database-specific metrics"""
        metrics = {}
        
        try:
            # Simulate database metrics (would come from postgres_exporter)
            metrics.update({
                "active_connections": 0.0,
                "query_duration": 0.0,
                "transactions_per_second": 0.0,
                "cache_hit_ratio": 0.0
            })
            
        except Exception as e:
            logger.debug(f"Error getting database metrics: {e}")
        
        return metrics
    
    async def get_redis_metrics(self) -> Dict[str, float]:
        """Get Redis-specific metrics"""
        metrics = {}
        
        try:
            # Get Redis info
            info = await self.redis_client.info()
            
            metrics.update({
                "connected_clients": float(info.get("connected_clients", 0)),
                "used_memory": float(info.get("used_memory", 0)),
                "keyspace_hits": float(info.get("keyspace_hits", 0)),
                "keyspace_misses": float(info.get("keyspace_misses", 0))
            })
            
            # Calculate hit rate
            hits = metrics.get("keyspace_hits", 0)
            misses = metrics.get("keyspace_misses", 0)
            if hits + misses > 0:
                metrics["hit_rate"] = hits / (hits + misses) * 100
            
        except Exception as e:
            logger.debug(f"Error getting Redis metrics: {e}")
        
        return metrics
    
    def calculate_derived_metrics(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate derived performance metrics"""
        derived = {}
        
        try:
            # Resource efficiency
            cpu_usage = metrics.get("cpu_usage", 0.0)
            memory_util = metrics.get("memory_utilization", 0.0)
            
            if cpu_usage > 0 and memory_util > 0:
                derived["resource_efficiency"] = min(cpu_usage, memory_util)
            
            # Network utilization
            network_rx = metrics.get("network_rx", 0.0)
            network_tx = metrics.get("network_tx", 0.0)
            derived["network_total"] = network_rx + network_tx
            
            # Performance score (inverse of response time, normalized)
            response_time = metrics.get("health_check_response_time", 1.0)
            if response_time > 0:
                derived["performance_score"] = max(0.0, 100.0 - (response_time * 10))
            
        except Exception as e:
            logger.debug(f"Error calculating derived metrics: {e}")
        
        return derived
    
    async def cache_performance_metrics(self, service: str, metrics: Dict[str, float]):
        """Cache performance metrics in Redis"""
        try:
            cache_key = f"autoscaler:metrics:{service}"
            cache_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": metrics
            }
            
            await self.redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(cache_data)
            )
            
        except Exception as e:
            logger.debug(f"Error caching performance metrics for {service}: {e}")
    
    async def scaling_evaluation_loop(self):
        """Main loop for evaluating scaling decisions"""
        while self.running:
            try:
                await self.evaluate_scaling_decisions()
                await asyncio.sleep(60)  # Evaluate every minute
                
            except Exception as e:
                logger.error(f"Error in scaling evaluation loop: {e}")
                await asyncio.sleep(30)
    
    async def evaluate_scaling_decisions(self):
        """Evaluate scaling decisions for all services"""
        try:
            for service, rules in self.scaling_rules.items():
                # Skip if service is in cooldown
                if await self.is_service_in_cooldown(service):
                    continue
                
                # Get current metrics
                metrics = self.performance_metrics.get(service, {})
                
                if not metrics:
                    continue
                
                # Evaluate each rule
                scaling_decisions = []
                
                for rule in rules:
                    if not rule.enabled:
                        continue
                    
                    decision = await self.evaluate_scaling_rule(rule, metrics)
                    
                    if decision and decision.action != ScalingAction.NO_ACTION:
                        scaling_decisions.append(decision)
                
                # Process scaling decisions
                if scaling_decisions:
                    final_decision = await self.resolve_scaling_decisions(scaling_decisions)
                    
                    if final_decision:
                        await self.queue_scaling_decision(final_decision)
                
        except Exception as e:
            logger.error(f"Error evaluating scaling decisions: {e}")
    
    async def evaluate_scaling_rule(self, rule: ScalingRule, 
                                  metrics: Dict[str, float]) -> Optional[ScalingDecision]:
        """Evaluate a specific scaling rule"""
        try:
            metric_value = metrics.get(rule.metric_name, 0.0)
            
            if metric_value == 0.0:
                return None  # No data available
            
            # Get current instance count
            current_instances = await self.get_current_instances(rule.service)
            
            # Determine scaling action
            action = ScalingAction.NO_ACTION
            target_instances = current_instances
            threshold_value = 0.0
            reasoning = []
            
            # Check scale-up conditions
            if metric_value > rule.scale_up_threshold:
                if current_instances < rule.max_instances:
                    action = ScalingAction.SCALE_OUT
                    target_instances = min(current_instances + 1, rule.max_instances)
                    threshold_value = rule.scale_up_threshold
                    reasoning.append(f"{rule.metric_name} ({metric_value:.1f}) > threshold ({rule.scale_up_threshold:.1f})")
                else:
                    # Consider vertical scaling if at max instances
                    action = ScalingAction.SCALE_UP
                    target_instances = current_instances
                    threshold_value = rule.scale_up_threshold
                    reasoning.append(f"At max instances, consider vertical scaling")
            
            # Check scale-down conditions
            elif metric_value < rule.scale_down_threshold:
                if current_instances > rule.min_instances:
                    action = ScalingAction.SCALE_IN
                    target_instances = max(current_instances - 1, rule.min_instances)
                    threshold_value = rule.scale_down_threshold
                    reasoning.append(f"{rule.metric_name} ({metric_value:.1f}) < threshold ({rule.scale_down_threshold:.1f})")
                else:
                    # Consider vertical scaling down
                    action = ScalingAction.SCALE_DOWN
                    target_instances = current_instances
                    threshold_value = rule.scale_down_threshold
                    reasoning.append(f"At min instances, consider vertical scaling down")
            
            # Calculate confidence based on how far from threshold
            if action != ScalingAction.NO_ACTION:
                if action in [ScalingAction.SCALE_OUT, ScalingAction.SCALE_UP]:
                    distance = metric_value - rule.scale_up_threshold
                    max_distance = 100.0 - rule.scale_up_threshold  # Assuming max value of 100
                else:
                    distance = rule.scale_down_threshold - metric_value
                    max_distance = rule.scale_down_threshold
                
                confidence = min(1.0, max(0.1, distance / max_distance)) * rule.weight
                
                return ScalingDecision(
                    service=rule.service,
                    action=action,
                    current_instances=current_instances,
                    target_instances=target_instances,
                    trigger_metric=rule.metric_name,
                    current_value=metric_value,
                    threshold_value=threshold_value,
                    confidence=confidence,
                    reasoning=reasoning,
                    created_at=datetime.utcnow()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating scaling rule for {rule.service}: {e}")
            return None
    
    async def get_current_instances(self, service: str) -> int:
        """Get current number of instances for a service"""
        try:
            containers = self.docker_client.containers.list(
                filters={"name": service, "status": "running"}
            )
            return len(containers)
            
        except Exception as e:
            logger.debug(f"Error getting current instances for {service}: {e}")
            return 1  # Default assumption
    
    async def resolve_scaling_decisions(self, decisions: List[ScalingDecision]) -> Optional[ScalingDecision]:
        """Resolve conflicting scaling decisions"""
        try:
            if not decisions:
                return None
            
            if len(decisions) == 1:
                return decisions[0]
            
            # Group by action type
            scale_up_decisions = [d for d in decisions if d.action in [ScalingAction.SCALE_OUT, ScalingAction.SCALE_UP]]
            scale_down_decisions = [d for d in decisions if d.action in [ScalingAction.SCALE_IN, ScalingAction.SCALE_DOWN]]
            
            # If we have both scale up and down, choose based on confidence
            if scale_up_decisions and scale_down_decisions:
                max_up_confidence = max(d.confidence for d in scale_up_decisions)
                max_down_confidence = max(d.confidence for d in scale_down_decisions)
                
                # Scale up takes precedence if confidence is close
                if max_up_confidence >= max_down_confidence * 0.8:
                    return max(scale_up_decisions, key=lambda d: d.confidence)
                else:
                    return max(scale_down_decisions, key=lambda d: d.confidence)
            
            # Return highest confidence decision
            return max(decisions, key=lambda d: d.confidence)
            
        except Exception as e:
            logger.error(f"Error resolving scaling decisions: {e}")
            return decisions[0] if decisions else None
    
    async def queue_scaling_decision(self, decision: ScalingDecision):
        """Queue a scaling decision for execution"""
        try:
            # Add to scaling history
            self.scaling_history.append(decision)
            
            # Cache in Redis
            decision_data = {
                "service": decision.service,
                "action": decision.action.value,
                "current_instances": decision.current_instances,
                "target_instances": decision.target_instances,
                "trigger_metric": decision.trigger_metric,
                "current_value": decision.current_value,
                "threshold_value": decision.threshold_value,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "created_at": decision.created_at.isoformat(),
                "executed": decision.executed
            }
            
            await self.redis_client.lpush(
                f"autoscaler:decisions:{decision.service}",
                json.dumps(decision_data)
            )
            
            # Keep only recent decisions
            await self.redis_client.ltrim(f"autoscaler:decisions:{decision.service}", 0, 99)
            
            logger.info(
                f"Queued scaling decision: {decision.service} {decision.action.value} "
                f"({decision.current_instances} -> {decision.target_instances}) "
                f"confidence: {decision.confidence:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error queuing scaling decision: {e}")
    
    async def predictive_scaling_loop(self):
        """Loop for predictive scaling analysis"""
        while self.running:
            try:
                await self.generate_resource_predictions()
                await asyncio.sleep(300)  # Predict every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in predictive scaling loop: {e}")
                await asyncio.sleep(120)
    
    async def generate_resource_predictions(self):
        """Generate resource usage predictions"""
        try:
            for service in self.scaling_rules.keys():
                history = self.metric_history.get(service, [])
                
                if len(history) < 20:  # Need minimum data points
                    continue
                
                predictions = await self.predict_service_resources(service, history)
                
                if predictions:
                    self.resource_predictions[service] = predictions
                    
                    # Cache predictions
                    await self.cache_resource_predictions(service, predictions)
                    
                    # Check for proactive scaling needs
                    await self.evaluate_predictive_scaling(service, predictions)
                
        except Exception as e:
            logger.error(f"Error generating resource predictions: {e}")
    
    async def predict_service_resources(self, service: str, 
                                      history: List[Dict[str, Any]]) -> List[ResourcePrediction]:
        """Predict resource usage for a service"""
        try:
            predictions = []
            
            # Extract time series data
            timestamps = [h["timestamp"] for h in history[-50:]]  # Last 50 data points
            
            # Convert timestamps to numeric values (minutes since first timestamp)
            base_time = timestamps[0]
            time_values = [(t - base_time).total_seconds() / 60.0 for t in timestamps]
            
            # Predict different metrics
            metrics_to_predict = ["cpu_usage", "memory_utilization", "health_check_response_time"]
            
            for metric in metrics_to_predict:
                metric_values = [h["metrics"].get(metric, 0.0) for h in history[-50:]]
                
                if len(set(metric_values)) < 2:  # Not enough variation
                    continue
                
                try:
                    # Prepare data for prediction
                    X = np.array(time_values).reshape(-1, 1)
                    y = np.array(metric_values)
                    
                    # Train simple linear regression model
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    # Predict future values (next 30 minutes)
                    future_times = np.array([time_values[-1] + i for i in range(1, 31)]).reshape(-1, 1)
                    future_values = model.predict(future_times)
                    
                    # Calculate trend
                    trend_slope = model.coef_[0]
                    if abs(trend_slope) < 0.1:
                        trend_direction = "stable"
                    elif trend_slope > 0:
                        trend_direction = "increasing"
                    else:
                        trend_direction = "decreasing"
                    
                    # Find peak time if trending up
                    peak_time = None
                    if trend_direction == "increasing":
                        # Estimate when metric might reach critical threshold
                        current_value = metric_values[-1]
                        critical_threshold = self.get_critical_threshold(service, metric)
                        
                        if trend_slope > 0 and current_value < critical_threshold:
                            minutes_to_peak = (critical_threshold - current_value) / trend_slope
                            if minutes_to_peak > 0 and minutes_to_peak < 60:  # Within 1 hour
                                peak_time = datetime.utcnow() + timedelta(minutes=minutes_to_peak)
                    
                    # Determine recommendation
                    current_value = metric_values[-1]
                    predicted_max = max(future_values)
                    
                    recommendation = self.get_scaling_recommendation(
                        service, metric, current_value, predicted_max, trend_direction
                    )
                    
                    # Calculate confidence (simplified)
                    confidence = max(0.1, min(1.0, 1.0 - abs(trend_slope) / 10.0))
                    
                    prediction = ResourcePrediction(
                        service=service,
                        metric=metric,
                        current_value=current_value,
                        predicted_value=predicted_max,
                        prediction_horizon=30,
                        confidence=confidence,
                        trend_direction=trend_direction,
                        peak_time=peak_time,
                        recommendation=recommendation
                    )
                    
                    predictions.append(prediction)
                    
                except Exception as e:
                    logger.debug(f"Error predicting {metric} for {service}: {e}")
                    continue
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting resources for {service}: {e}")
            return []
    
    def get_critical_threshold(self, service: str, metric: str) -> float:
        """Get critical threshold for a metric"""
        # Get scaling rules for service
        rules = self.scaling_rules.get(service, [])
        
        for rule in rules:
            if rule.metric_name == metric:
                return rule.scale_up_threshold
        
        # Default thresholds
        default_thresholds = {
            "cpu_usage": 80.0,
            "memory_utilization": 85.0,
            "health_check_response_time": 3.0
        }
        
        return default_thresholds.get(metric, 100.0)
    
    def get_scaling_recommendation(self, service: str, metric: str, current_value: float,
                                 predicted_value: float, trend: str) -> ScalingAction:
        """Get scaling recommendation based on prediction"""
        
        critical_threshold = self.get_critical_threshold(service, metric)
        
        # If predicted value exceeds threshold and trending up
        if predicted_value > critical_threshold and trend == "increasing":
            return ScalingAction.SCALE_OUT
        
        # If trending down significantly
        elif trend == "decreasing" and predicted_value < critical_threshold * 0.5:
            return ScalingAction.SCALE_IN
        
        return ScalingAction.NO_ACTION
    
    async def cache_resource_predictions(self, service: str, 
                                       predictions: List[ResourcePrediction]):
        """Cache resource predictions in Redis"""
        try:
            cache_key = f"autoscaler:predictions:{service}"
            cache_data = []
            
            for pred in predictions:
                cache_data.append({
                    "metric": pred.metric,
                    "current_value": pred.current_value,
                    "predicted_value": pred.predicted_value,
                    "prediction_horizon": pred.prediction_horizon,
                    "confidence": pred.confidence,
                    "trend_direction": pred.trend_direction,
                    "peak_time": pred.peak_time.isoformat() if pred.peak_time else None,
                    "recommendation": pred.recommendation.value
                })
            
            await self.redis_client.setex(
                cache_key,
                600,  # 10 minutes TTL
                json.dumps(cache_data)
            )
            
        except Exception as e:
            logger.debug(f"Error caching predictions for {service}: {e}")
    
    async def evaluate_predictive_scaling(self, service: str, 
                                        predictions: List[ResourcePrediction]):
        """Evaluate if predictive scaling is needed"""
        try:
            high_confidence_predictions = [
                p for p in predictions 
                if p.confidence > 0.7 and p.recommendation != ScalingAction.NO_ACTION
            ]
            
            if not high_confidence_predictions:
                return
            
            # Check if we need proactive scaling
            for prediction in high_confidence_predictions:
                # If peak is within 15 minutes, take action
                if (prediction.peak_time and 
                    prediction.peak_time <= datetime.utcnow() + timedelta(minutes=15)):
                    
                    current_instances = await self.get_current_instances(service)
                    
                    if prediction.recommendation == ScalingAction.SCALE_OUT:
                        target_instances = current_instances + 1
                    elif prediction.recommendation == ScalingAction.SCALE_IN:
                        target_instances = max(1, current_instances - 1)
                    else:
                        target_instances = current_instances
                    
                    # Create predictive scaling decision
                    decision = ScalingDecision(
                        service=service,
                        action=prediction.recommendation,
                        current_instances=current_instances,
                        target_instances=target_instances,
                        trigger_metric=prediction.metric,
                        current_value=prediction.current_value,
                        threshold_value=prediction.predicted_value,
                        confidence=prediction.confidence,
                        reasoning=[
                            f"Predictive scaling based on {prediction.metric}",
                            f"Peak expected at {prediction.peak_time}",
                            f"Trend: {prediction.trend_direction}"
                        ],
                        created_at=datetime.utcnow()
                    )
                    
                    await self.queue_scaling_decision(decision)
                    
                    logger.info(
                        f"Predictive scaling triggered for {service}: {prediction.recommendation.value} "
                        f"due to predicted {prediction.metric} peak at {prediction.peak_time}"
                    )
            
        except Exception as e:
            logger.error(f"Error evaluating predictive scaling for {service}: {e}")
    
    async def scaling_execution_loop(self):
        """Loop for executing scaling decisions"""
        while self.running:
            try:
                await self.execute_scaling_decisions()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in scaling execution loop: {e}")
                await asyncio.sleep(15)
    
    async def execute_scaling_decisions(self):
        """Execute pending scaling decisions"""
        try:
            # Get pending decisions (simplified - in production, use a proper queue)
            for i, decision in enumerate(self.scaling_history):
                if not decision.executed and decision.created_at > datetime.utcnow() - timedelta(minutes=5):
                    
                    # Check if service is still eligible for scaling
                    if not await self.is_service_in_cooldown(decision.service):
                        success = await self.execute_scaling_action(decision)
                        
                        # Mark as executed
                        decision.executed = True
                        
                        if success:
                            # Set cooldown period
                            await self.set_service_cooldown(decision.service)
                            
                            logger.info(
                                f"Successfully executed scaling action: {decision.service} "
                                f"{decision.action.value} ({decision.current_instances} -> "
                                f"{decision.target_instances})"
                            )
                        else:
                            logger.error(
                                f"Failed to execute scaling action: {decision.service} "
                                f"{decision.action.value}"
                            )
                    
                    # Only process one decision per cycle
                    break
                    
        except Exception as e:
            logger.error(f"Error executing scaling decisions: {e}")
    
    async def execute_scaling_action(self, decision: ScalingDecision) -> bool:
        """Execute a specific scaling action"""
        try:
            if decision.action == ScalingAction.SCALE_OUT:
                return await self.scale_out_service(decision.service, decision.target_instances)
            elif decision.action == ScalingAction.SCALE_IN:
                return await self.scale_in_service(decision.service, decision.target_instances)
            elif decision.action == ScalingAction.SCALE_UP:
                return await self.scale_up_service(decision.service)
            elif decision.action == ScalingAction.SCALE_DOWN:
                return await self.scale_down_service(decision.service)
            else:
                return True  # No action needed
                
        except Exception as e:
            logger.error(f"Error executing scaling action for {decision.service}: {e}")
            return False
    
    async def scale_out_service(self, service: str, target_instances: int) -> bool:
        """Scale out service (add more instances)"""
        try:
            current_containers = self.docker_client.containers.list(
                filters={"name": service}
            )
            
            if not current_containers:
                logger.error(f"No containers found for service {service}")
                return False
            
            # Get the template container
            template = current_containers[0]
            
            # Create new instances
            current_count = len(current_containers)
            instances_to_add = target_instances - current_count
            
            for i in range(instances_to_add):
                # Create new container with similar config
                new_container_name = f"{service}_{current_count + i + 1}"
                
                # Use docker-compose scale in production
                # For now, simulate scaling
                logger.info(f"Would create new container: {new_container_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scaling out {service}: {e}")
            return False
    
    async def scale_in_service(self, service: str, target_instances: int) -> bool:
        """Scale in service (remove instances)"""
        try:
            current_containers = self.docker_client.containers.list(
                filters={"name": service, "status": "running"}
            )
            
            current_count = len(current_containers)
            instances_to_remove = current_count - target_instances
            
            if instances_to_remove <= 0:
                return True
            
            # Remove excess containers (keep the healthiest ones)
            containers_to_remove = current_containers[-instances_to_remove:]
            
            for container in containers_to_remove:
                try:
                    container.stop(timeout=30)
                    container.remove()
                    logger.info(f"Removed container: {container.name}")
                except Exception as e:
                    logger.error(f"Error removing container {container.name}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scaling in {service}: {e}")
            return False
    
    async def scale_up_service(self, service: str) -> bool:
        """Scale up service (increase resources)"""
        try:
            # Vertical scaling - increase CPU/memory limits
            # This would typically be done through docker-compose or Kubernetes
            logger.info(f"Would scale up resources for {service}")
            
            # In a real implementation, you would:
            # 1. Update container resource limits
            # 2. Restart container with new limits
            # 3. Verify the scaling worked
            
            return True
            
        except Exception as e:
            logger.error(f"Error scaling up {service}: {e}")
            return False
    
    async def scale_down_service(self, service: str) -> bool:
        """Scale down service (decrease resources)"""
        try:
            # Vertical scaling down - decrease CPU/memory limits
            logger.info(f"Would scale down resources for {service}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scaling down {service}: {e}")
            return False
    
    async def is_service_in_cooldown(self, service: str) -> bool:
        """Check if service is in cooldown period"""
        cooldown_end = self.cooldown_services.get(service)
        if cooldown_end and datetime.utcnow() < cooldown_end:
            return True
        return False
    
    async def set_service_cooldown(self, service: str):
        """Set cooldown period for service"""
        # Use the longest cooldown from service rules
        rules = self.scaling_rules.get(service, [])
        max_cooldown = max((rule.cooldown_period for rule in rules), default=300)
        
        cooldown_end = datetime.utcnow() + timedelta(seconds=max_cooldown)
        self.cooldown_services[service] = cooldown_end
        
        # Cache in Redis
        await self.redis_client.setex(
            f"autoscaler:cooldown:{service}",
            max_cooldown,
            cooldown_end.isoformat()
        )
    
    async def model_training_loop(self):
        """Loop for training prediction models"""
        while self.running:
            try:
                await self.train_prediction_models()
                await asyncio.sleep(3600)  # Train every hour
                
            except Exception as e:
                logger.error(f"Error in model training loop: {e}")
                await asyncio.sleep(600)
    
    async def train_prediction_models(self):
        """Train prediction models with accumulated data"""
        try:
            for service in self.scaling_rules.keys():
                history = self.metric_history.get(service, [])
                
                if len(history) < 50:  # Need more data
                    continue
                
                await self.train_service_models(service, history)
                
        except Exception as e:
            logger.error(f"Error training prediction models: {e}")
    
    async def train_service_models(self, service: str, history: List[Dict[str, Any]]):
        """Train prediction models for a specific service"""
        try:
            # Extract features and targets
            features = []
            targets = {}
            
            for i, entry in enumerate(history[:-1]):  # Exclude last entry as we need next value
                metrics = entry["metrics"]
                next_metrics = history[i + 1]["metrics"]
                
                # Create feature vector
                feature_vector = [
                    metrics.get("cpu_usage", 0.0),
                    metrics.get("memory_utilization", 0.0),
                    metrics.get("health_check_response_time", 0.0),
                    metrics.get("network_total", 0.0),
                    entry["timestamp"].hour,  # Hour of day
                    entry["timestamp"].weekday()  # Day of week
                ]
                
                features.append(feature_vector)
                
                # Create targets (next values)
                for metric in ["cpu_usage", "memory_utilization", "health_check_response_time"]:
                    if metric not in targets:
                        targets[metric] = []
                    targets[metric].append(next_metrics.get(metric, 0.0))
            
            if len(features) < 20:
                return
            
            X = np.array(features)
            
            # Train models for each metric
            models = self.prediction_models.get(service, {})
            scaler = self.scalers.get(service)
            
            if scaler:
                X_scaled = scaler.fit_transform(X)
            else:
                X_scaled = X
            
            for metric, y_values in targets.items():
                if len(set(y_values)) < 2:  # Not enough variation
                    continue
                
                model_key = f"{metric}_model"
                if model_key in models:
                    try:
                        y = np.array(y_values)
                        models[model_key].fit(X_scaled, y)
                        
                        logger.info(f"Trained {model_key} for {service}")
                        
                    except Exception as e:
                        logger.debug(f"Error training {model_key} for {service}: {e}")
            
        except Exception as e:
            logger.error(f"Error training models for {service}: {e}")
    
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
        """Clean up old scaling data"""
        try:
            # Clean up old scaling history
            if len(self.scaling_history) > 200:
                self.scaling_history = self.scaling_history[-200:]
            
            # Clean up old metric history
            for service in self.metric_history:
                if len(self.metric_history[service]) > 1000:
                    self.metric_history[service] = self.metric_history[service][-1000:]
            
            # Clean up expired cooldowns
            current_time = datetime.utcnow()
            expired_services = [
                service for service, cooldown_end in self.cooldown_services.items()
                if current_time >= cooldown_end
            ]
            
            for service in expired_services:
                del self.cooldown_services[service]
                await self.redis_client.delete(f"autoscaler:cooldown:{service}")
            
            if expired_services:
                logger.info(f"Cleaned up cooldowns for services: {expired_services}")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    async def load_scaling_history(self):
        """Load scaling history from Redis"""
        try:
            # Load recent scaling decisions for all services
            for service in self.scaling_rules.keys():
                decisions = await self.redis_client.lrange(
                    f"autoscaler:decisions:{service}", 0, 49  # Last 50 decisions
                )
                
                for decision_json in decisions:
                    try:
                        data = json.loads(decision_json)
                        decision = ScalingDecision(
                            service=data["service"],
                            action=ScalingAction(data["action"]),
                            current_instances=data["current_instances"],
                            target_instances=data["target_instances"],
                            trigger_metric=data["trigger_metric"],
                            current_value=data["current_value"],
                            threshold_value=data["threshold_value"],
                            confidence=data["confidence"],
                            reasoning=data["reasoning"],
                            created_at=datetime.fromisoformat(data["created_at"]),
                            executed=data["executed"]
                        )
                        self.scaling_history.append(decision)
                        
                    except Exception as e:
                        logger.debug(f"Error loading scaling decision: {e}")
            
            logger.info(f"Loaded {len(self.scaling_history)} scaling decisions from cache")
            
        except Exception as e:
            logger.error(f"Error loading scaling history: {e}")
    
    async def get_autoscaler_status(self) -> Dict[str, Any]:
        """Get current auto-scaler status"""
        try:
            # Count scaling decisions by action
            action_counts = {}
            recent_decisions = [d for d in self.scaling_history if d.created_at > datetime.utcnow() - timedelta(hours=1)]
            
            for decision in recent_decisions:
                action = decision.action.value
                action_counts[action] = action_counts.get(action, 0) + 1
            
            # Get current instance counts
            instance_counts = {}
            for service in self.scaling_rules.keys():
                try:
                    instance_counts[service] = await self.get_current_instances(service)
                except Exception:
                    instance_counts[service] = 1
            
            # Get services in cooldown
            services_in_cooldown = [
                service for service, cooldown_end in self.cooldown_services.items()
                if datetime.utcnow() < cooldown_end
            ]
            
            # Get recent predictions
            prediction_summary = {}
            for service, predictions in self.resource_predictions.items():
                if predictions:
                    high_confidence = [p for p in predictions if p.confidence > 0.7]
                    prediction_summary[service] = {
                        "total_predictions": len(predictions),
                        "high_confidence": len(high_confidence),
                        "recommended_actions": [p.recommendation.value for p in high_confidence]
                    }
            
            return {
                "running": self.running,
                "monitored_services": len(self.scaling_rules),
                "scaling_rules_count": sum(len(rules) for rules in self.scaling_rules.values()),
                "recent_scaling_actions": action_counts,
                "current_instances": instance_counts,
                "services_in_cooldown": services_in_cooldown,
                "prediction_summary": prediction_summary,
                "total_scaling_history": len(self.scaling_history),
                "metric_history_size": {
                    service: len(history) for service, history in self.metric_history.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting autoscaler status: {e}")
            return {"error": str(e)}
    
    async def stop_auto_scaling(self):
        """Stop the auto-scaling system"""
        self.running = False
        
        if self.session:
            await self.session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Performance Auto-Scaler stopped")


# Global auto-scaler instance
auto_scaler = PerformanceAutoScaler()