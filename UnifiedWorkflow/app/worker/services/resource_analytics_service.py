"""
Resource Analytics Service - Performance Monitoring and Analytics
Provides comprehensive monitoring, analytics, and optimization insights for resource usage.
"""

import asyncio
import logging
import json
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque

from worker.services.model_resource_manager import model_resource_manager, ModelCategory
from worker.services.centralized_resource_service import centralized_resource_service, ComplexityLevel
from worker.services.gpu_load_balancer import gpu_load_balancer
from worker.services.model_lifecycle_manager import model_lifecycle_manager
from worker.services.resource_policy_service import resource_policy_service

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics tracked by the analytics service."""
    ALLOCATION_TIME = "allocation_time"
    PROCESSING_TIME = "processing_time"
    QUEUE_WAIT_TIME = "queue_wait_time"
    GPU_UTILIZATION = "gpu_utilization"
    MEMORY_USAGE = "memory_usage"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MODEL_EFFICIENCY = "model_efficiency"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    metric_type: MetricType
    value: float
    timestamp: datetime
    service_name: str
    model_name: str
    complexity: str
    gpu_id: Optional[int] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for analysis."""
    metric_type: MetricType
    count: int
    mean: float
    median: float
    min_value: float
    max_value: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    time_period: str
    last_updated: datetime


@dataclass
class ServiceAnalytics:
    """Analytics data for a specific service."""
    service_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_processing_time: float
    average_queue_time: float
    throughput_per_hour: float
    most_used_models: Dict[str, int]
    complexity_distribution: Dict[str, int]
    peak_usage_hours: List[int]
    error_patterns: Dict[str, int]
    last_updated: datetime


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation based on analytics."""
    category: str
    priority: str  # high, medium, low
    title: str
    description: str
    current_state: Dict[str, Any]
    recommended_action: str
    expected_improvement: str
    implementation_complexity: str  # low, medium, high
    estimated_impact: float  # 0.0 to 1.0


class ResourceAnalyticsService:
    """
    Comprehensive resource analytics and monitoring service.
    Tracks performance metrics, generates insights, and provides optimization recommendations.
    """
    
    def __init__(self):
        # Metric storage with time-based retention
        self.metrics: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self.aggregated_metrics: Dict[str, AggregatedMetrics] = {}
        self.service_analytics: Dict[str, ServiceAnalytics] = {}
        
        # Real-time monitoring
        self.monitoring_active = False
        self.monitoring_interval = 30.0  # Update analytics every 30 seconds
        self._monitoring_task: Optional[asyncio.Task] = None
        self._analytics_lock = asyncio.Lock()
        
        # Performance thresholds for alerts
        self.performance_thresholds = {
            MetricType.ALLOCATION_TIME: 5.0,  # seconds
            MetricType.PROCESSING_TIME: 30.0,  # seconds
            MetricType.QUEUE_WAIT_TIME: 60.0,  # seconds
            MetricType.GPU_UTILIZATION: 0.95,  # 95%
            MetricType.MEMORY_USAGE: 0.90,  # 90%
            MetricType.ERROR_RATE: 0.05,  # 5%
        }
        
        # Analytics cache for expensive calculations
        self.analytics_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.last_cache_update = datetime.now(timezone.utc)
    
    async def start_monitoring(self):
        """Start real-time performance monitoring."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started resource analytics monitoring")
    
    async def stop_monitoring(self):
        """Stop real-time performance monitoring."""
        self.monitoring_active = False
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped resource analytics monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for collecting and processing metrics."""
        while self.monitoring_active:
            try:
                await self._collect_system_metrics()
                await self._update_service_analytics()
                await self._generate_optimization_recommendations()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.monitoring_interval)
    
    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        service_name: str,
        model_name: str,
        complexity: ComplexityLevel,
        gpu_id: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a performance metric."""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(timezone.utc),
            service_name=service_name,
            model_name=model_name,
            complexity=complexity.value if isinstance(complexity, ComplexityLevel) else complexity,
            gpu_id=gpu_id,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self.metrics.append(metric)
        
        # Trigger real-time analysis for critical metrics
        if metric_type in [MetricType.ERROR_RATE, MetricType.PROCESSING_TIME]:
            await self._check_performance_alerts(metric)
        
        logger.debug(f"Recorded {metric_type.value} metric: {value} for {service_name}")
    
    async def _collect_system_metrics(self):
        """Collect system-wide performance metrics."""
        try:
            # GPU utilization metrics
            gpu_status = await gpu_load_balancer.get_load_balancer_status()
            for gpu_id, gpu_info in gpu_status.get("gpu_details", {}).items():
                await self.record_metric(
                    MetricType.GPU_UTILIZATION,
                    gpu_info["utilization_percent"] / 100.0,
                    "system",
                    "gpu_monitoring",
                    ComplexityLevel.SIMPLE,
                    gpu_id=int(gpu_id)
                )
                
                await self.record_metric(
                    MetricType.MEMORY_USAGE,
                    gpu_info["memory_used_mb"] / gpu_info["memory_total_mb"],
                    "system",
                    "gpu_monitoring",
                    ComplexityLevel.SIMPLE,
                    gpu_id=int(gpu_id)
                )
            
            # Resource manager metrics
            resource_status = await model_resource_manager.get_resource_status()
            total_executions = sum(resource_status.get("active_executions", {}).values())
            
            await self.record_metric(
                MetricType.THROUGHPUT,
                total_executions,
                "system",
                "resource_manager",
                ComplexityLevel.SIMPLE
            )
            
        except Exception as e:
            logger.warning(f"Error collecting system metrics: {e}")
    
    async def _update_service_analytics(self):
        """Update aggregated analytics for all services."""
        async with self._analytics_lock:
            # Group metrics by service
            service_metrics = defaultdict(list)
            for metric in self.metrics:
                service_metrics[metric.service_name].append(metric)
            
            # Calculate analytics for each service
            for service_name, metrics in service_metrics.items():
                if service_name == "system":
                    continue  # Skip system metrics for service analytics
                
                analytics = await self._calculate_service_analytics(service_name, metrics)
                self.service_analytics[service_name] = analytics
    
    async def _calculate_service_analytics(self, service_name: str, metrics: List[PerformanceMetric]) -> ServiceAnalytics:
        """Calculate analytics for a specific service."""
        if not metrics:
            return ServiceAnalytics(
                service_name=service_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_processing_time=0.0,
                average_queue_time=0.0,
                throughput_per_hour=0.0,
                most_used_models={},
                complexity_distribution={},
                peak_usage_hours=[],
                error_patterns={},
                last_updated=datetime.now(timezone.utc)
            )
        
        # Filter recent metrics (last 24 hours)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_metrics = [m for m in metrics if m.timestamp >= recent_cutoff]
        
        # Calculate processing times
        processing_times = [
            m.value for m in recent_metrics 
            if m.metric_type == MetricType.PROCESSING_TIME
        ]
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0.0
        
        # Calculate queue times
        queue_times = [
            m.value for m in recent_metrics 
            if m.metric_type == MetricType.QUEUE_WAIT_TIME
        ]
        avg_queue_time = statistics.mean(queue_times) if queue_times else 0.0
        
        # Model usage distribution
        model_usage = defaultdict(int)
        for metric in recent_metrics:
            model_usage[metric.model_name] += 1
        
        # Complexity distribution
        complexity_dist = defaultdict(int)
        for metric in recent_metrics:
            complexity_dist[metric.complexity] += 1
        
        # Peak usage hours
        hourly_usage = defaultdict(int)
        for metric in recent_metrics:
            hour = metric.timestamp.hour
            hourly_usage[hour] += 1
        
        peak_hours = sorted(hourly_usage.keys(), key=lambda h: hourly_usage[h], reverse=True)[:3]
        
        # Error patterns
        error_metrics = [m for m in recent_metrics if m.metric_type == MetricType.ERROR_RATE]
        error_patterns = defaultdict(int)
        for metric in error_metrics:
            error_type = metric.metadata.get("error_type", "unknown")
            error_patterns[error_type] += 1
        
        # Throughput calculation
        if recent_metrics:
            time_span_hours = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds() / 3600
            throughput = len(recent_metrics) / max(time_span_hours, 1.0)
        else:
            throughput = 0.0
        
        return ServiceAnalytics(
            service_name=service_name,
            total_requests=len(recent_metrics),
            successful_requests=len([m for m in recent_metrics if m.metric_type != MetricType.ERROR_RATE]),
            failed_requests=len(error_metrics),
            average_processing_time=avg_processing_time,
            average_queue_time=avg_queue_time,
            throughput_per_hour=throughput,
            most_used_models=dict(model_usage),
            complexity_distribution=dict(complexity_dist),
            peak_usage_hours=peak_hours,
            error_patterns=dict(error_patterns),
            last_updated=datetime.now(timezone.utc)
        )
    
    async def _generate_optimization_recommendations(self):
        """Generate optimization recommendations based on analytics."""
        recommendations = []
        
        # GPU utilization recommendations
        gpu_status = await gpu_load_balancer.get_load_balancer_status()
        avg_utilization = statistics.mean([
            details["utilization_percent"] / 100.0 
            for details in gpu_status.get("gpu_details", {}).values()
        ]) if gpu_status.get("gpu_details") else 0.0
        
        if avg_utilization < 0.3:
            recommendations.append(OptimizationRecommendation(
                category="resource_utilization",
                priority="medium",
                title="Low GPU Utilization",
                description=f"Average GPU utilization is {avg_utilization:.1%}, indicating underutilization",
                current_state={"avg_utilization": avg_utilization},
                recommended_action="Consider consolidating workloads or reducing allocated GPU resources",
                expected_improvement="Cost reduction without performance impact",
                implementation_complexity="low",
                estimated_impact=0.3
            ))
        elif avg_utilization > 0.9:
            recommendations.append(OptimizationRecommendation(
                category="resource_scaling",
                priority="high",
                title="High GPU Utilization",
                description=f"Average GPU utilization is {avg_utilization:.1%}, indicating potential bottleneck",
                current_state={"avg_utilization": avg_utilization},
                recommended_action="Consider adding more GPU resources or implementing request throttling",
                expected_improvement="Improved response times and system reliability",
                implementation_complexity="medium",
                estimated_impact=0.7
            ))
        
        # Service-specific recommendations
        for service_name, analytics in self.service_analytics.items():
            # High processing time recommendation
            if analytics.average_processing_time > 45.0:
                recommendations.append(OptimizationRecommendation(
                    category="performance",
                    priority="high",
                    title=f"High Processing Time - {service_name}",
                    description=f"Average processing time is {analytics.average_processing_time:.1f}s",
                    current_state={"service": service_name, "avg_time": analytics.average_processing_time},
                    recommended_action="Optimize model selection or implement request caching",
                    expected_improvement="Faster response times and better user experience",
                    implementation_complexity="medium",
                    estimated_impact=0.6
                ))
            
            # High queue time recommendation
            if analytics.average_queue_time > 30.0:
                recommendations.append(OptimizationRecommendation(
                    category="capacity",
                    priority="medium",
                    title=f"High Queue Time - {service_name}",
                    description=f"Average queue wait time is {analytics.average_queue_time:.1f}s",
                    current_state={"service": service_name, "avg_queue_time": analytics.average_queue_time},
                    recommended_action="Increase concurrent processing limits or add more resources",
                    expected_improvement="Reduced wait times and improved responsiveness",
                    implementation_complexity="low",
                    estimated_impact=0.4
                ))
        
        # Cache recommendations for retrieval
        self.analytics_cache["optimization_recommendations"] = recommendations
        self.last_cache_update = datetime.now(timezone.utc)
    
    async def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check if a metric exceeds performance thresholds."""
        threshold = self.performance_thresholds.get(metric.metric_type)
        if threshold and metric.value > threshold:
            logger.warning(
                f"Performance alert: {metric.metric_type.value} = {metric.value} "
                f"exceeds threshold {threshold} for {metric.service_name}"
            )
    
    async def get_real_time_metrics(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        # Filter metrics by service if specified
        relevant_metrics = [
            m for m in self.metrics 
            if service_name is None or m.service_name == service_name
        ]
        
        # Get recent metrics (last 5 minutes)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_metrics = [m for m in relevant_metrics if m.timestamp >= recent_cutoff]
        
        # Calculate real-time statistics
        current_stats = {}
        for metric_type in MetricType:
            type_metrics = [m.value for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                current_stats[metric_type.value] = {
                    "current": type_metrics[-1] if type_metrics else 0,
                    "average": statistics.mean(type_metrics),
                    "count": len(type_metrics),
                    "trend": "increasing" if len(type_metrics) > 1 and type_metrics[-1] > type_metrics[0] else "stable"
                }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_filter": service_name,
            "metrics_count": len(recent_metrics),
            "current_stats": current_stats,
            "monitoring_active": self.monitoring_active
        }
    
    async def get_service_analytics_report(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive analytics report for services."""
        if service_name:
            if service_name in self.service_analytics:
                return {
                    "service": service_name,
                    "analytics": asdict(self.service_analytics[service_name]),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {"error": f"No analytics data for service {service_name}"}
        else:
            return {
                "all_services": {
                    name: asdict(analytics)
                    for name, analytics in self.service_analytics.items()
                },
                "summary": {
                    "total_services": len(self.service_analytics),
                    "total_requests": sum(a.total_requests for a in self.service_analytics.values()),
                    "average_processing_time": statistics.mean([
                        a.average_processing_time for a in self.service_analytics.values()
                    ]) if self.service_analytics else 0.0
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get current optimization recommendations."""
        # Check cache validity
        if (datetime.now(timezone.utc) - self.last_cache_update).total_seconds() > self.cache_ttl:
            await self._generate_optimization_recommendations()
        
        recommendations = self.analytics_cache.get("optimization_recommendations", [])
        return [asdict(rec) for rec in recommendations]
    
    async def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive analytics and monitoring report."""
        service_report = await self.get_service_analytics_report()
        real_time_metrics = await self.get_real_time_metrics()
        recommendations = await self.get_optimization_recommendations()
        
        # System-wide statistics
        system_stats = await centralized_resource_service.get_service_status()
        
        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "monitoring_status": {
                "active": self.monitoring_active,
                "metrics_collected": len(self.metrics),
                "monitoring_interval": self.monitoring_interval
            },
            "real_time_metrics": real_time_metrics,
            "service_analytics": service_report,
            "system_status": system_stats,
            "optimization_recommendations": recommendations,
            "performance_thresholds": {
                metric_type.value: threshold 
                for metric_type, threshold in self.performance_thresholds.items()
            }
        }


# Global instance
resource_analytics_service = ResourceAnalyticsService()