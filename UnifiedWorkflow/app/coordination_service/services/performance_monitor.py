"""Performance Monitor for coordination service metrics and optimization.

This module tracks system performance, identifies bottlenecks, and provides
insights for workflow and agent optimization.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

import structlog

logger = structlog.get_logger(__name__)


class MetricType(str, Enum):
    """Types of performance metrics."""
    WORKFLOW_COMPLETION_TIME = "workflow_completion_time"
    AGENT_UTILIZATION = "agent_utilization"
    CONTEXT_GENERATION_TIME = "context_generation_time"
    QUEUE_LENGTH = "queue_length"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    RESPONSE_TIME = "response_time"
    RESOURCE_USAGE = "resource_usage"


@dataclass
class PerformanceMetric:
    """Represents a performance metric data point."""
    metric_type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "metric_type": self.metric_type,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "metadata": self.metadata
        }


@dataclass
class AlertRule:
    """Defines an alert rule for performance monitoring."""
    name: str
    metric_type: MetricType
    threshold: float
    comparison: str  # "greater_than", "less_than", "equals"
    duration_seconds: int = 60
    severity: str = "warning"  # "info", "warning", "critical"
    enabled: bool = True
    last_triggered: Optional[float] = None


class PerformanceMonitor:
    """Monitors system performance and provides optimization insights."""
    
    def __init__(
        self,
        redis_service,
        target_completion_rate: float = 0.95,
        monitoring_interval: int = 60,
        metric_retention_seconds: int = 86400,  # 24 hours
        alert_cooldown_seconds: int = 300  # 5 minutes
    ):
        self.redis_service = redis_service
        self.target_completion_rate = target_completion_rate
        self.monitoring_interval = monitoring_interval
        self.metric_retention_seconds = metric_retention_seconds
        self.alert_cooldown_seconds = alert_cooldown_seconds
        
        # Metrics storage
        self._metrics_buffer: List[PerformanceMetric] = []
        self._metric_history: Dict[MetricType, List[PerformanceMetric]] = {}
        self._aggregated_metrics: Dict[str, Any] = {}
        
        # Alert rules
        self._alert_rules: List[AlertRule] = []
        self._active_alerts: List[Dict[str, Any]] = []
        
        # Monitoring state
        self._monitoring_running = False
        self._last_cleanup_time = 0.0
        
        # Performance baselines
        self._performance_baselines: Dict[str, float] = {}
        self._trend_analysis: Dict[str, Dict[str, float]] = {}
    
    async def initialize(self) -> None:
        """Initialize the performance monitor."""
        logger.info("Initializing Performance Monitor...")
        
        # Initialize metric storage
        for metric_type in MetricType:
            self._metric_history[metric_type] = []
        
        # Set up default alert rules
        await self._setup_default_alert_rules()
        
        # Load historical baselines
        await self._load_performance_baselines()
        
        logger.info(
            "Performance Monitor initialized",
            target_completion_rate=self.target_completion_rate,
            monitoring_interval=self.monitoring_interval
        )
    
    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric."""
        try:
            metric = PerformanceMetric(
                metric_type=metric_type,
                value=value,
                labels=labels or {},
                metadata=metadata or {}
            )
            
            # Add to buffer
            self._metrics_buffer.append(metric)
            
            # Add to history
            self._metric_history[metric_type].append(metric)
            
            # Check alert rules
            await self._check_alert_rules(metric)
            
            logger.debug(
                "Performance metric recorded",
                metric_type=metric_type,
                value=value,
                labels=labels
            )
            
        except Exception as e:
            logger.error("Failed to record metric", metric_type=metric_type, error=str(e))
    
    async def record_orchestration_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record orchestration-specific metrics."""
        try:
            # Workflow metrics
            if "active_workflows" in metrics:
                await self.record_metric(
                    MetricType.QUEUE_LENGTH,
                    float(metrics["active_workflows"]),
                    labels={"queue_type": "workflows"}
                )
            
            # Agent utilization
            if "agent_utilization" in metrics:
                await self.record_metric(
                    MetricType.AGENT_UTILIZATION,
                    float(metrics["agent_utilization"]),
                    labels={"resource_type": "agents"}
                )
            
            # Queue lengths
            if "queued_workflows" in metrics:
                await self.record_metric(
                    MetricType.QUEUE_LENGTH,
                    float(metrics["queued_workflows"]),
                    labels={"queue_type": "workflow_queue"}
                )
            
            if "active_assignments" in metrics:
                await self.record_metric(
                    MetricType.QUEUE_LENGTH,
                    float(metrics["active_assignments"]),
                    labels={"queue_type": "assignments"}
                )
                
        except Exception as e:
            logger.error("Failed to record orchestration metrics", error=str(e))
    
    async def record_workflow_completion(
        self,
        workflow_id: str,
        completion_time: float,
        success: bool,
        agent_count: int
    ) -> None:
        """Record workflow completion metrics."""
        try:
            # Completion time
            await self.record_metric(
                MetricType.WORKFLOW_COMPLETION_TIME,
                completion_time,
                labels={
                    "success": str(success).lower(),
                    "agent_count_range": self._get_agent_count_range(agent_count)
                },
                metadata={
                    "workflow_id": workflow_id,
                    "agent_count": agent_count
                }
            )
            
            # Success/failure rate
            error_rate = 0.0 if success else 1.0
            await self.record_metric(
                MetricType.ERROR_RATE,
                error_rate,
                labels={"component": "workflow"},
                metadata={"workflow_id": workflow_id}
            )
            
        except Exception as e:
            logger.error("Failed to record workflow completion", workflow_id=workflow_id, error=str(e))
    
    async def record_agent_performance(
        self,
        agent_name: str,
        execution_time: float,
        success: bool,
        utilization: float
    ) -> None:
        """Record agent performance metrics."""
        try:
            # Response time
            await self.record_metric(
                MetricType.RESPONSE_TIME,
                execution_time,
                labels={
                    "agent": agent_name,
                    "success": str(success).lower()
                },
                metadata={"execution_time": execution_time}
            )
            
            # Utilization
            await self.record_metric(
                MetricType.AGENT_UTILIZATION,
                utilization,
                labels={"agent": agent_name},
                metadata={"utilization": utilization}
            )
            
            # Error rate
            error_rate = 0.0 if success else 1.0
            await self.record_metric(
                MetricType.ERROR_RATE,
                error_rate,
                labels={"agent": agent_name},
                metadata={"success": success}
            )
            
        except Exception as e:
            logger.error("Failed to record agent performance", agent_name=agent_name, error=str(e))
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics summary."""
        try:
            now = time.time()
            recent_window = now - 300  # Last 5 minutes
            
            # Filter recent metrics
            recent_metrics = {}
            for metric_type, metrics in self._metric_history.items():
                recent = [m for m in metrics if m.timestamp > recent_window]
                if recent:
                    values = [m.value for m in recent]
                    recent_metrics[metric_type] = {
                        "current": values[-1],
                        "avg": statistics.mean(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values)
                    }
            
            return {
                "timestamp": now,
                "window_seconds": 300,
                "metrics": recent_metrics,
                "active_alerts": len(self._active_alerts),
                "system_health": self._calculate_system_health()
            }
            
        except Exception as e:
            logger.error("Failed to get current metrics", error=str(e))
            return {"error": str(e)}
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics and analysis."""
        try:
            current_metrics = await self.get_current_metrics()
            
            # Performance trends
            trends = await self._calculate_performance_trends()
            
            # Bottleneck analysis
            bottlenecks = await self._identify_bottlenecks()
            
            # Optimization recommendations
            recommendations = await self._generate_optimization_recommendations()
            
            # Alert summary
            alert_summary = self._get_alert_summary()
            
            return {
                "current_metrics": current_metrics,
                "performance_trends": trends,
                "bottleneck_analysis": bottlenecks,
                "optimization_recommendations": recommendations,
                "alerts": alert_summary,
                "baselines": self._performance_baselines,
                "monitoring_status": {
                    "running": self._monitoring_running,
                    "interval_seconds": self.monitoring_interval,
                    "retention_seconds": self.metric_retention_seconds
                }
            }
            
        except Exception as e:
            logger.error("Failed to get detailed metrics", error=str(e))
            return {"error": str(e)}
    
    async def run_monitoring_loop(self) -> None:
        """Main monitoring loop for periodic analysis."""
        if self._monitoring_running:
            logger.warning("Monitoring loop already running")
            return
        
        self._monitoring_running = True
        logger.info("Starting performance monitoring loop")
        
        try:
            while self._monitoring_running:
                try:
                    # Aggregate recent metrics
                    await self._aggregate_metrics()
                    
                    # Update performance baselines
                    await self._update_performance_baselines()
                    
                    # Perform trend analysis
                    await self._analyze_performance_trends()
                    
                    # Clean up old metrics
                    if time.time() - self._last_cleanup_time > 3600:  # Hourly cleanup
                        await self._cleanup_old_metrics()
                        self._last_cleanup_time = time.time()
                    
                    # Persist metrics to Redis
                    await self._persist_metrics_to_redis()
                    
                    await asyncio.sleep(self.monitoring_interval)
                    
                except Exception as e:
                    logger.error("Error in monitoring loop", error=str(e))
                    await asyncio.sleep(30)
                    
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error("Monitoring loop failed", error=str(e))
        finally:
            self._monitoring_running = False
            logger.info("Monitoring loop stopped")
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the performance monitor."""
        logger.info("Shutting down Performance Monitor...")
        
        try:
            # Stop monitoring
            self._monitoring_running = False
            
            # Persist final metrics
            await self._persist_metrics_to_redis()
            
            logger.info("Performance Monitor shutdown complete")
            
        except Exception as e:
            logger.error("Error during Performance Monitor shutdown", error=str(e))
    
    # Private helper methods
    
    async def _setup_default_alert_rules(self) -> None:
        """Set up default alert rules."""
        self._alert_rules = [
            AlertRule(
                name="High Workflow Completion Time",
                metric_type=MetricType.WORKFLOW_COMPLETION_TIME,
                threshold=1800.0,  # 30 minutes
                comparison="greater_than",
                duration_seconds=300,  # 5 minutes
                severity="warning"
            ),
            AlertRule(
                name="Low Completion Rate",
                metric_type=MetricType.ERROR_RATE,
                threshold=0.1,  # 10% error rate
                comparison="greater_than",
                duration_seconds=600,  # 10 minutes
                severity="critical"
            ),
            AlertRule(
                name="High Agent Utilization",
                metric_type=MetricType.AGENT_UTILIZATION,
                threshold=0.9,  # 90% utilization
                comparison="greater_than",
                duration_seconds=900,  # 15 minutes
                severity="warning"
            ),
            AlertRule(
                name="Long Queue Length",
                metric_type=MetricType.QUEUE_LENGTH,
                threshold=20.0,
                comparison="greater_than",
                duration_seconds=300,
                severity="warning"
            )
        ]
        
        logger.info("Default alert rules configured", count=len(self._alert_rules))
    
    async def _check_alert_rules(self, metric: PerformanceMetric) -> None:
        """Check metric against alert rules."""
        try:
            for rule in self._alert_rules:
                if not rule.enabled or rule.metric_type != metric.metric_type:
                    continue
                
                # Check if alert condition is met
                triggered = False
                if rule.comparison == "greater_than" and metric.value > rule.threshold:
                    triggered = True
                elif rule.comparison == "less_than" and metric.value < rule.threshold:
                    triggered = True
                elif rule.comparison == "equals" and metric.value == rule.threshold:
                    triggered = True
                
                if triggered:
                    await self._trigger_alert(rule, metric)
                    
        except Exception as e:
            logger.error("Failed to check alert rules", error=str(e))
    
    async def _trigger_alert(self, rule: AlertRule, metric: PerformanceMetric) -> None:
        """Trigger an alert."""
        try:
            current_time = time.time()
            
            # Check cooldown period
            if (rule.last_triggered and 
                current_time - rule.last_triggered < self.alert_cooldown_seconds):
                return
            
            # Create alert
            alert = {
                "rule_name": rule.name,
                "metric_type": rule.metric_type,
                "severity": rule.severity,
                "threshold": rule.threshold,
                "actual_value": metric.value,
                "triggered_at": current_time,
                "labels": metric.labels,
                "metadata": metric.metadata
            }
            
            self._active_alerts.append(alert)
            rule.last_triggered = current_time
            
            logger.warning(
                "Performance alert triggered",
                rule_name=rule.name,
                severity=rule.severity,
                threshold=rule.threshold,
                actual_value=metric.value
            )
            
            # Keep only recent alerts
            cutoff_time = current_time - 3600  # Keep alerts for 1 hour
            self._active_alerts = [
                alert for alert in self._active_alerts 
                if alert["triggered_at"] > cutoff_time
            ]
            
        except Exception as e:
            logger.error("Failed to trigger alert", error=str(e))
    
    def _get_agent_count_range(self, agent_count: int) -> str:
        """Get agent count range for labeling."""
        if agent_count <= 2:
            return "1-2"
        elif agent_count <= 5:
            return "3-5"
        elif agent_count <= 10:
            return "6-10"
        else:
            return "10+"
    
    def _calculate_system_health(self) -> str:
        """Calculate overall system health score."""
        try:
            now = time.time()
            recent_window = now - 600  # Last 10 minutes
            
            # Check recent error rates
            recent_errors = []
            for metric in self._metric_history.get(MetricType.ERROR_RATE, []):
                if metric.timestamp > recent_window:
                    recent_errors.append(metric.value)
            
            if not recent_errors:
                return "unknown"
            
            avg_error_rate = statistics.mean(recent_errors)
            
            if avg_error_rate < 0.05:  # < 5% error rate
                return "excellent"
            elif avg_error_rate < 0.10:  # < 10% error rate
                return "good"
            elif avg_error_rate < 0.20:  # < 20% error rate
                return "fair"
            else:
                return "poor"
                
        except Exception as e:
            logger.error("Failed to calculate system health", error=str(e))
            return "unknown"
    
    async def _calculate_performance_trends(self) -> Dict[str, Dict[str, float]]:
        """Calculate performance trends over time."""
        try:
            trends = {}
            now = time.time()
            
            # Analyze trends for each metric type
            for metric_type, metrics in self._metric_history.items():
                if not metrics:
                    continue
                
                # Get recent data points
                hour_ago = now - 3600
                day_ago = now - 86400
                
                recent_hour = [m for m in metrics if m.timestamp > hour_ago]
                recent_day = [m for m in metrics if m.timestamp > day_ago]
                
                if len(recent_hour) < 2 or len(recent_day) < 2:
                    continue
                
                # Calculate trends
                hour_values = [m.value for m in recent_hour]
                day_values = [m.value for m in recent_day]
                
                hour_trend = (hour_values[-1] - hour_values[0]) / len(hour_values) if len(hour_values) > 1 else 0
                day_trend = (day_values[-1] - day_values[0]) / len(day_values) if len(day_values) > 1 else 0
                
                trends[metric_type] = {
                    "hour_trend": hour_trend,
                    "day_trend": day_trend,
                    "hour_avg": statistics.mean(hour_values),
                    "day_avg": statistics.mean(day_values)
                }
            
            return trends
            
        except Exception as e:
            logger.error("Failed to calculate performance trends", error=str(e))
            return {}
    
    async def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify system bottlenecks."""
        try:
            bottlenecks = []
            now = time.time()
            recent_window = now - 900  # Last 15 minutes
            
            # Check queue lengths
            queue_metrics = [
                m for m in self._metric_history.get(MetricType.QUEUE_LENGTH, [])
                if m.timestamp > recent_window
            ]
            
            if queue_metrics:
                avg_queue_length = statistics.mean([m.value for m in queue_metrics])
                if avg_queue_length > 10:
                    bottlenecks.append({
                        "type": "queue_backlog",
                        "severity": "high" if avg_queue_length > 20 else "medium",
                        "avg_queue_length": avg_queue_length,
                        "description": f"Average queue length is {avg_queue_length:.1f}"
                    })
            
            # Check agent utilization
            util_metrics = [
                m for m in self._metric_history.get(MetricType.AGENT_UTILIZATION, [])
                if m.timestamp > recent_window
            ]
            
            if util_metrics:
                avg_utilization = statistics.mean([m.value for m in util_metrics])
                if avg_utilization > 0.8:
                    bottlenecks.append({
                        "type": "high_agent_utilization",
                        "severity": "high" if avg_utilization > 0.9 else "medium",
                        "avg_utilization": avg_utilization,
                        "description": f"Average agent utilization is {avg_utilization:.1%}"
                    })
            
            # Check response times
            response_metrics = [
                m for m in self._metric_history.get(MetricType.RESPONSE_TIME, [])
                if m.timestamp > recent_window
            ]
            
            if response_metrics:
                avg_response_time = statistics.mean([m.value for m in response_metrics])
                if avg_response_time > 300:  # 5 minutes
                    bottlenecks.append({
                        "type": "slow_response_time",
                        "severity": "high" if avg_response_time > 600 else "medium",
                        "avg_response_time": avg_response_time,
                        "description": f"Average response time is {avg_response_time:.1f} seconds"
                    })
            
            return bottlenecks
            
        except Exception as e:
            logger.error("Failed to identify bottlenecks", error=str(e))
            return []
    
    async def _generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        try:
            recommendations = []
            bottlenecks = await self._identify_bottlenecks()
            
            for bottleneck in bottlenecks:
                if bottleneck["type"] == "queue_backlog":
                    recommendations.append({
                        "category": "capacity",
                        "priority": bottleneck["severity"],
                        "title": "Increase Workflow Concurrency",
                        "description": "Consider increasing max_concurrent_workflows to handle queue backlog",
                        "impact": "Reduce queue wait times and improve throughput"
                    })
                
                elif bottleneck["type"] == "high_agent_utilization":
                    recommendations.append({
                        "category": "scaling",
                        "priority": bottleneck["severity"],
                        "title": "Scale High-Demand Agents",
                        "description": "Consider adding more instances of heavily utilized agents",
                        "impact": "Improve response times and reduce agent overload"
                    })
                
                elif bottleneck["type"] == "slow_response_time":
                    recommendations.append({
                        "category": "optimization",
                        "priority": bottleneck["severity"],
                        "title": "Optimize Agent Performance",
                        "description": "Review and optimize slow-performing agents",
                        "impact": "Reduce overall workflow completion times"
                    })
            
            # Add general recommendations
            if not bottlenecks:
                recommendations.append({
                    "category": "maintenance",
                    "priority": "low",
                    "title": "System Running Well",
                    "description": "No immediate optimizations needed",
                    "impact": "Continue monitoring for performance changes"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to generate optimization recommendations", error=str(e))
            return []
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        active_count = len(self._active_alerts)
        
        severity_counts = {}
        for alert in self._active_alerts:
            severity = alert["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "active_alerts": active_count,
            "by_severity": severity_counts,
            "recent_alerts": self._active_alerts[-10:] if self._active_alerts else []
        }
    
    async def _aggregate_metrics(self) -> None:
        """Aggregate recent metrics for analysis."""
        # Implementation for metric aggregation
        pass
    
    async def _update_performance_baselines(self) -> None:
        """Update performance baselines."""
        # Implementation for baseline updates
        pass
    
    async def _analyze_performance_trends(self) -> None:
        """Analyze performance trends."""
        # Implementation for trend analysis
        pass
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics beyond retention period."""
        cutoff_time = time.time() - self.metric_retention_seconds
        
        for metric_type in self._metric_history:
            self._metric_history[metric_type] = [
                m for m in self._metric_history[metric_type]
                if m.timestamp > cutoff_time
            ]
        
        logger.info("Old metrics cleaned up")
    
    async def _persist_metrics_to_redis(self) -> None:
        """Persist metrics to Redis for external access."""
        if not self.redis_service or not self._metrics_buffer:
            return
        
        try:
            # Store recent metrics
            metrics_data = [metric.to_dict() for metric in self._metrics_buffer[-100:]]  # Last 100 metrics
            
            await self.redis_service.set_json(
                key="coordination_performance_metrics",
                value=metrics_data,
                expiry_seconds=self.metric_retention_seconds
            )
            
            # Clear buffer after persistence
            self._metrics_buffer.clear()
            
        except Exception as e:
            logger.error("Failed to persist metrics to Redis", error=str(e))
    
    async def _load_performance_baselines(self) -> None:
        """Load historical performance baselines."""
        # Implementation for loading baselines
        self._performance_baselines = {
            "avg_workflow_completion_time": 600.0,  # 10 minutes
            "target_agent_utilization": 0.7,  # 70%
            "max_queue_length": 5.0,
            "target_error_rate": 0.05  # 5%
        }