"""
GPU Monitor Service - Real-time GPU resource monitoring and optimization
Provides detailed GPU metrics, memory tracking, and automatic optimization recommendations.
"""

import asyncio
import logging
import subprocess
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class GPUAlertLevel(str, Enum):
    """GPU monitoring alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class GPUMetrics:
    """GPU performance metrics."""
    gpu_id: int
    memory_used_mb: float
    memory_total_mb: float
    memory_free_mb: float
    memory_utilization_percent: float
    gpu_utilization_percent: float
    temperature_celsius: float
    power_draw_watts: float
    timestamp: datetime
    
    @property
    def memory_usage_percent(self) -> float:
        """Calculate memory usage percentage."""
        return (self.memory_used_mb / self.memory_total_mb) * 100 if self.memory_total_mb > 0 else 0


@dataclass
class GPUAlert:
    """GPU monitoring alert."""
    level: GPUAlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    gpu_id: Optional[int] = None


@dataclass
class ModelMemoryUsage:
    """Model memory usage tracking."""
    model_name: str
    estimated_memory_mb: float
    actual_memory_mb: Optional[float] = None
    reference_count: int = 0
    first_loaded: Optional[datetime] = None
    last_used: Optional[datetime] = None


class GPUMonitorService:
    """
    Comprehensive GPU monitoring and optimization service.
    Tracks performance metrics, memory usage, and provides optimization recommendations.
    """
    
    def __init__(self):
        self.monitoring_enabled = True
        self.monitoring_interval = 5.0  # Monitor every 5 seconds
        self.metrics_history: List[GPUMetrics] = []
        self.alerts: List[GPUAlert] = []
        self.model_memory_tracking: Dict[str, ModelMemoryUsage] = {}
        
        # Alert thresholds
        self.memory_warning_threshold = 80.0  # Warn at 80% memory usage
        self.memory_critical_threshold = 95.0  # Critical at 95% memory usage
        self.temperature_warning_threshold = 80.0  # Warn at 80°C
        self.temperature_critical_threshold = 90.0  # Critical at 90°C
        
        # History management
        self.max_history_entries = 1000
        self.max_alerts = 100
        
        self._monitoring_task: Optional[asyncio.Task] = None
        self._metrics_lock = asyncio.Lock()
        
    async def start_monitoring(self):
        """Start GPU monitoring background task."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started GPU monitoring service")
    
    async def stop_monitoring(self):
        """Stop GPU monitoring background task."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped GPU monitoring service")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                if self.monitoring_enabled:
                    await self._collect_metrics()
                    await self._check_alerts()
                    await self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in GPU monitoring loop: {e}", exc_info=True)
    
    async def _collect_metrics(self):
        """Collect current GPU metrics."""
        try:
            gpu_data = await self._get_nvidia_smi_data()
            if not gpu_data:
                return
            
            async with self._metrics_lock:
                for gpu_info in gpu_data:
                    metrics = GPUMetrics(
                        gpu_id=gpu_info['gpu_id'],
                        memory_used_mb=gpu_info['memory_used'],
                        memory_total_mb=gpu_info['memory_total'],
                        memory_free_mb=gpu_info['memory_free'],
                        memory_utilization_percent=gpu_info.get('memory_utilization', 0),
                        gpu_utilization_percent=gpu_info.get('gpu_utilization', 0),
                        temperature_celsius=gpu_info.get('temperature', 0),
                        power_draw_watts=gpu_info.get('power_draw', 0),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    self.metrics_history.append(metrics)
                    
                    # Update model memory tracking if needed
                    await self._update_model_memory_estimates(metrics)
                
                # Limit history size
                if len(self.metrics_history) > self.max_history_entries:
                    self.metrics_history = self.metrics_history[-self.max_history_entries//2:]
                    
        except Exception as e:
            logger.error(f"Error collecting GPU metrics: {e}")
    
    async def _get_nvidia_smi_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get GPU data from nvidia-smi."""
        try:
            cmd = [
                'nvidia-smi',
                '--query-gpu=index,memory.used,memory.total,memory.free,utilization.gpu,utilization.memory,temperature.gpu,power.draw',
                '--format=csv,noheader,nounits'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.debug(f"nvidia-smi failed: {result.stderr}")
                return None
            
            gpu_data = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 8:
                        try:
                            gpu_data.append({
                                'gpu_id': int(parts[0]),
                                'memory_used': float(parts[1]),
                                'memory_total': float(parts[2]),
                                'memory_free': float(parts[3]),
                                'gpu_utilization': float(parts[4]),
                                'memory_utilization': float(parts[5]),
                                'temperature': float(parts[6]),
                                'power_draw': float(parts[7]) if parts[7] != '[Not Supported]' else 0
                            })
                        except ValueError as e:
                            logger.debug(f"Error parsing GPU data line: {line}, error: {e}")
            
            return gpu_data if gpu_data else None
            
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi command timed out")
            return None
        except FileNotFoundError:
            logger.debug("nvidia-smi not found - GPU monitoring disabled")
            return None
        except Exception as e:
            logger.debug(f"Error running nvidia-smi: {e}")
            return None
    
    async def _update_model_memory_estimates(self, metrics: GPUMetrics):
        """Update model memory usage estimates based on current metrics."""
        # This is a simplified estimation - in reality, you'd need more sophisticated tracking
        # to accurately attribute memory usage to specific models
        
        from worker.services.model_lifecycle_manager import model_lifecycle_manager
        
        try:
            lifecycle_status = await model_lifecycle_manager.get_lifecycle_status()
            loaded_models = lifecycle_status.get('loaded_models', {})
            
            if loaded_models:
                # Estimate memory per model (simplified)
                estimated_memory_per_model = metrics.memory_used_mb / len(loaded_models)
                
                for model_name in loaded_models.keys():
                    if model_name not in self.model_memory_tracking:
                        self.model_memory_tracking[model_name] = ModelMemoryUsage(
                            model_name=model_name,
                            estimated_memory_mb=estimated_memory_per_model,
                            first_loaded=datetime.now(timezone.utc)
                        )
                    
                    self.model_memory_tracking[model_name].actual_memory_mb = estimated_memory_per_model
                    self.model_memory_tracking[model_name].last_used = datetime.now(timezone.utc)
                    
        except Exception as e:
            logger.debug(f"Error updating model memory estimates: {e}")
    
    async def _check_alerts(self):
        """Check for alert conditions and generate alerts."""
        if not self.metrics_history:
            return
        
        latest_metrics = self.metrics_history[-1]
        current_time = datetime.now(timezone.utc)
        
        # Memory usage alerts
        memory_percent = latest_metrics.memory_usage_percent
        if memory_percent >= self.memory_critical_threshold:
            await self._add_alert(
                GPUAlertLevel.CRITICAL,
                f"GPU {latest_metrics.gpu_id} memory usage critical: {memory_percent:.1f}%",
                "memory_usage",
                memory_percent,
                self.memory_critical_threshold,
                latest_metrics.gpu_id
            )
        elif memory_percent >= self.memory_warning_threshold:
            await self._add_alert(
                GPUAlertLevel.WARNING,
                f"GPU {latest_metrics.gpu_id} memory usage high: {memory_percent:.1f}%",
                "memory_usage",
                memory_percent,
                self.memory_warning_threshold,
                latest_metrics.gpu_id
            )
        
        # Temperature alerts
        if latest_metrics.temperature_celsius >= self.temperature_critical_threshold:
            await self._add_alert(
                GPUAlertLevel.CRITICAL,
                f"GPU {latest_metrics.gpu_id} temperature critical: {latest_metrics.temperature_celsius:.1f}°C",
                "temperature",
                latest_metrics.temperature_celsius,
                self.temperature_critical_threshold,
                latest_metrics.gpu_id
            )
        elif latest_metrics.temperature_celsius >= self.temperature_warning_threshold:
            await self._add_alert(
                GPUAlertLevel.WARNING,
                f"GPU {latest_metrics.gpu_id} temperature high: {latest_metrics.temperature_celsius:.1f}°C",
                "temperature",
                latest_metrics.temperature_celsius,
                self.temperature_warning_threshold,
                latest_metrics.gpu_id
            )
    
    async def _add_alert(
        self,
        level: GPUAlertLevel,
        message: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        gpu_id: Optional[int] = None
    ):
        """Add a new alert if it hasn't been raised recently."""
        # Check if we already have a recent similar alert
        recent_threshold = timedelta(minutes=5)
        current_time = datetime.now(timezone.utc)
        
        for alert in reversed(self.alerts[-10:]):  # Check last 10 alerts
            if (alert.level == level and 
                alert.metric_name == metric_name and 
                alert.gpu_id == gpu_id and
                current_time - alert.timestamp < recent_threshold):
                return  # Don't add duplicate recent alert
        
        alert = GPUAlert(
            level=level,
            message=message,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            timestamp=current_time,
            gpu_id=gpu_id
        )
        
        async with self._metrics_lock:
            self.alerts.append(alert)
            
            # Limit alerts history
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts//2:]
        
        # Log the alert
        log_level = logging.CRITICAL if level == GPUAlertLevel.CRITICAL else logging.WARNING
        logger.log(log_level, f"GPU Alert: {message}")
    
    async def _cleanup_old_data(self):
        """Clean up old metrics and alerts."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        async with self._metrics_lock:
            # Remove old metrics
            self.metrics_history = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff_time
            ]
            
            # Remove old alerts
            self.alerts = [
                a for a in self.alerts 
                if a.timestamp > cutoff_time
            ]
    
    async def get_current_metrics(self) -> Optional[GPUMetrics]:
        """Get the most recent GPU metrics."""
        async with self._metrics_lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    async def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get a summary of GPU metrics over the specified time period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with self._metrics_lock:
            recent_metrics = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff_time
            ]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Calculate statistics
        memory_usages = [m.memory_usage_percent for m in recent_metrics]
        gpu_utilizations = [m.gpu_utilization_percent for m in recent_metrics]
        temperatures = [m.temperature_celsius for m in recent_metrics]
        
        return {
            "period_hours": hours,
            "samples_count": len(recent_metrics),
            "memory_usage": {
                "current": recent_metrics[-1].memory_usage_percent,
                "average": sum(memory_usages) / len(memory_usages),
                "max": max(memory_usages),
                "min": min(memory_usages)
            },
            "gpu_utilization": {
                "current": recent_metrics[-1].gpu_utilization_percent,
                "average": sum(gpu_utilizations) / len(gpu_utilizations),
                "max": max(gpu_utilizations),
                "min": min(gpu_utilizations)
            },
            "temperature": {
                "current": recent_metrics[-1].temperature_celsius,
                "average": sum(temperatures) / len(temperatures),
                "max": max(temperatures),
                "min": min(temperatures)
            },
            "latest_metrics": recent_metrics[-1].__dict__ if recent_metrics else None
        }
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on current metrics and usage patterns."""
        recommendations = []
        
        current_metrics = await self.get_current_metrics()
        if not current_metrics:
            return recommendations
        
        # High memory usage recommendations
        if current_metrics.memory_usage_percent > 85:
            recommendations.append({
                "priority": "high",
                "type": "memory_optimization",
                "title": "High GPU Memory Usage",
                "description": f"GPU memory usage is at {current_metrics.memory_usage_percent:.1f}%",
                "suggestions": [
                    "Consider unloading unused models",
                    "Use smaller models for less critical tasks",
                    "Enable model sharing between experts",
                    "Implement more aggressive model lifecycle management"
                ]
            })
        
        # Low GPU utilization recommendations
        if current_metrics.gpu_utilization_percent < 20 and current_metrics.memory_usage_percent > 50:
            recommendations.append({
                "priority": "medium",
                "type": "utilization_optimization",
                "title": "Low GPU Utilization with High Memory Usage",
                "description": f"GPU utilization is only {current_metrics.gpu_utilization_percent:.1f}% but memory usage is {current_metrics.memory_usage_percent:.1f}%",
                "suggestions": [
                    "Models may be loaded but not actively used",
                    "Consider reducing model preloading",
                    "Implement more aggressive model unloading",
                    "Review model lifecycle timeout settings"
                ]
            })
        
        # Temperature recommendations
        if current_metrics.temperature_celsius > 75:
            recommendations.append({
                "priority": "high" if current_metrics.temperature_celsius > 85 else "medium",
                "type": "thermal_management",
                "title": "High GPU Temperature",
                "description": f"GPU temperature is {current_metrics.temperature_celsius:.1f}°C",
                "suggestions": [
                    "Check GPU cooling and ventilation",
                    "Consider reducing parallel execution limits",
                    "Monitor for dust buildup in GPU fans",
                    "Reduce maximum GPU power limit if needed"
                ]
            })
        
        # Model sharing opportunities
        if len(self.model_memory_tracking) > 3:
            recommendations.append({
                "priority": "low",
                "type": "model_sharing",
                "title": "Model Sharing Opportunities",
                "description": f"Currently tracking {len(self.model_memory_tracking)} models",
                "suggestions": [
                    "Consider consolidating to fewer model variants",
                    "Implement model sharing between experts with similar requirements",
                    "Use model pooling for frequently accessed models",
                    "Review expert model assignments for optimization opportunities"
                ]
            })
        
        return recommendations
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get comprehensive monitoring status."""
        current_metrics = await self.get_current_metrics()
        recent_alerts = [a for a in self.alerts if a.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)]
        
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "monitoring_interval_seconds": self.monitoring_interval,
            "metrics_history_count": len(self.metrics_history),
            "current_metrics": current_metrics.__dict__ if current_metrics else None,
            "recent_alerts_count": len(recent_alerts),
            "latest_alerts": [a.__dict__ for a in recent_alerts[-5:]],
            "model_memory_tracking": {
                name: {
                    "estimated_memory_mb": usage.estimated_memory_mb,
                    "actual_memory_mb": usage.actual_memory_mb,
                    "reference_count": usage.reference_count,
                    "last_used": usage.last_used.isoformat() if usage.last_used else None
                }
                for name, usage in self.model_memory_tracking.items()
            },
            "thresholds": {
                "memory_warning": self.memory_warning_threshold,
                "memory_critical": self.memory_critical_threshold,
                "temperature_warning": self.temperature_warning_threshold,
                "temperature_critical": self.temperature_critical_threshold
            }
        }


# Global instance
gpu_monitor_service = GPUMonitorService()