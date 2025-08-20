"""
Worker monitoring and metrics collection for Celery tasks.

This module provides comprehensive monitoring for:
- Task queue depths and processing times
- Worker health and resource usage
- Task success/failure rates
- Custom business logic metrics
- Integration with Prometheus metrics
"""

from typing import Dict, List, Optional, Any, Callable
from celery import Celery
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_success,
    worker_ready, worker_shutdown, task_sent, task_received
)
from celery.states import ALL_STATES
import time
import logging
import psutil
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from shared.monitoring.prometheus_metrics import metrics
from shared.monitoring.structured_logging import get_logger, performance_logger, business_logger
import json

logger = get_logger(__name__)


@dataclass
class TaskMetrics:
    """Container for task execution metrics."""
    task_id: str
    task_name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = 'pending'
    duration: Optional[float] = None
    worker_name: Optional[str] = None
    queue_name: Optional[str] = None
    retries: int = 0
    exception: Optional[str] = None
    result_size: Optional[int] = None


@dataclass
class WorkerMetrics:
    """Container for worker health metrics."""
    worker_name: str
    active_tasks: int = 0
    processed_tasks: int = 0
    failed_tasks: int = 0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    load_average: float = 0.0
    last_heartbeat: Optional[datetime] = None


class WorkerMonitor:
    """
    Comprehensive monitoring system for Celery workers.
    
    Features:
    - Real-time task metrics collection
    - Worker health monitoring
    - Queue depth tracking
    - Performance analysis
    - Integration with Prometheus
    - Structured logging
    """
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.task_metrics: Dict[str, TaskMetrics] = {}
        self.worker_metrics: Dict[str, WorkerMetrics] = {}
        self.queue_depths: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Monitoring configuration
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds
        
        # Performance thresholds
        self.slow_task_threshold = 60.0  # seconds
        self.high_failure_rate_threshold = 0.1  # 10%
        self.high_memory_threshold_mb = 500
        self.high_cpu_threshold = 80.0
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("WorkerMonitor initialized")
    
    def _setup_signal_handlers(self):
        """Setup Celery signal handlers for monitoring."""
        
        @task_sent.connect
        def task_sent_handler(sender=None, task_id=None, task=None, **kwargs):
            """Handle task sent signal."""
            try:
                queue_name = kwargs.get('routing_key', 'default')
                
                # Update queue depth
                current_time = time.time()
                self.queue_depths[queue_name].append(current_time)
                
                # Update Prometheus metrics
                metrics.update_queue_depth(queue_name, len(self.queue_depths[queue_name]))
                
                logger.debug(f"Task {task_id} sent to queue {queue_name}")
            
            except Exception as e:
                logger.error(f"Error in task_sent_handler: {str(e)}")
        
        @task_prerun.connect
        def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
            """Handle task prerun signal."""
            try:
                task_name = sender.name if sender else 'unknown'
                worker_name = kwargs.get('worker_name', 'unknown')
                
                # Create task metrics entry
                self.task_metrics[task_id] = TaskMetrics(
                    task_id=task_id,
                    task_name=task_name,
                    start_time=time.time(),
                    worker_name=worker_name,
                    status='running'
                )
                
                # Update worker metrics
                if worker_name not in self.worker_metrics:
                    self.worker_metrics[worker_name] = WorkerMetrics(worker_name=worker_name)
                
                self.worker_metrics[worker_name].active_tasks += 1
                self.worker_metrics[worker_name].last_heartbeat = datetime.now()
                
                logger.info(f"Task {task_id} ({task_name}) started on worker {worker_name}")
            
            except Exception as e:
                logger.error(f"Error in task_prerun_handler: {str(e)}")
        
        @task_postrun.connect
        def task_postrun_handler(sender=None, task_id=None, task=None, 
                               retries=None, state=None, **kwargs):
            """Handle task postrun signal."""
            try:
                if task_id not in self.task_metrics:
                    return
                
                task_metric = self.task_metrics[task_id]
                task_metric.end_time = time.time()
                task_metric.duration = task_metric.end_time - task_metric.start_time
                task_metric.status = state or 'completed'
                task_metric.retries = retries or 0
                
                # Update worker metrics
                worker_name = task_metric.worker_name
                if worker_name and worker_name in self.worker_metrics:
                    self.worker_metrics[worker_name].active_tasks -= 1
                    self.worker_metrics[worker_name].processed_tasks += 1
                
                # Record performance history
                self.performance_history[task_metric.task_name].append({
                    'timestamp': task_metric.end_time,
                    'duration': task_metric.duration,
                    'status': task_metric.status
                })
                
                # Log slow tasks
                if task_metric.duration > self.slow_task_threshold:
                    performance_logger.log_slow_query(
                        query=f"Task: {task_metric.task_name}",
                        duration=task_metric.duration,
                        task_id=task_id,
                        worker_name=worker_name
                    )
                
                # Update Prometheus metrics
                task_type = self._extract_task_type(task_metric.task_name)
                model = self._extract_model_from_task(task_metric.task_name)
                
                metrics.record_ai_task(
                    task_type=task_type,
                    model=model,
                    duration=task_metric.duration,
                    status=task_metric.status
                )
                
                # Business logging
                business_logger.log_ai_task_completion(
                    task_id=task_id,
                    task_type=task_type,
                    duration=task_metric.duration,
                    success=(task_metric.status == 'SUCCESS'),
                    model_used=model
                )
                
                logger.info(
                    f"Task {task_id} completed",
                    extra={
                        'task_name': task_metric.task_name,
                        'duration': task_metric.duration,
                        'status': task_metric.status,
                        'worker_name': worker_name
                    }
                )
            
            except Exception as e:
                logger.error(f"Error in task_postrun_handler: {str(e)}")
        
        @task_failure.connect
        def task_failure_handler(sender=None, task_id=None, exception=None, 
                                traceback=None, einfo=None, **kwargs):
            """Handle task failure signal."""
            try:
                if task_id in self.task_metrics:
                    task_metric = self.task_metrics[task_id]
                    task_metric.status = 'FAILURE'
                    task_metric.exception = str(exception) if exception else 'Unknown error'
                    
                    # Update worker metrics
                    worker_name = task_metric.worker_name
                    if worker_name and worker_name in self.worker_metrics:
                        self.worker_metrics[worker_name].failed_tasks += 1
                
                logger.error(
                    f"Task {task_id} failed",
                    extra={
                        'task_name': sender.name if sender else 'unknown',
                        'exception': str(exception) if exception else 'Unknown',
                        'traceback': traceback
                    }
                )
            
            except Exception as e:
                logger.error(f"Error in task_failure_handler: {str(e)}")
        
        @worker_ready.connect
        def worker_ready_handler(sender=None, **kwargs):
            """Handle worker ready signal."""
            try:
                worker_name = str(sender)
                
                if worker_name not in self.worker_metrics:
                    self.worker_metrics[worker_name] = WorkerMetrics(worker_name=worker_name)
                
                self.worker_metrics[worker_name].last_heartbeat = datetime.now()
                
                logger.info(f"Worker {worker_name} ready")
            
            except Exception as e:
                logger.error(f"Error in worker_ready_handler: {str(e)}")
        
        @worker_shutdown.connect
        def worker_shutdown_handler(sender=None, **kwargs):
            """Handle worker shutdown signal."""
            try:
                worker_name = str(sender)
                
                if worker_name in self.worker_metrics:
                    del self.worker_metrics[worker_name]
                
                logger.info(f"Worker {worker_name} shutdown")
            
            except Exception as e:
                logger.error(f"Error in worker_shutdown_handler: {str(e)}")
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Worker monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring thread."""
        self.monitoring_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("Worker monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._analyze_performance()
                self._update_prometheus_metrics()
                self._cleanup_old_metrics()
                
                time.sleep(self.monitoring_interval)
            
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
    
    def _collect_system_metrics(self):
        """Collect system resource metrics for workers."""
        try:
            # Get current process metrics
            process = psutil.Process()
            
            # Update system metrics for current worker
            for worker_name, worker_metric in self.worker_metrics.items():
                try:
                    # Get CPU and memory usage
                    worker_metric.cpu_percent = process.cpu_percent()
                    worker_metric.memory_mb = process.memory_info().rss / 1024 / 1024
                    worker_metric.load_average = psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
                    
                    # Check for high resource usage
                    if worker_metric.memory_mb > self.high_memory_threshold_mb:
                        performance_logger.log_high_memory_usage(
                            service=f"worker_{worker_name}",
                            memory_mb=worker_metric.memory_mb,
                            threshold_mb=self.high_memory_threshold_mb
                        )
                    
                    if worker_metric.cpu_percent > self.high_cpu_threshold:
                        logger.warning(
                            f"High CPU usage detected",
                            extra={
                                'worker_name': worker_name,
                                'cpu_percent': worker_metric.cpu_percent,
                                'threshold': self.high_cpu_threshold
                            }
                        )
                
                except Exception as e:
                    logger.warning(f"Failed to collect metrics for worker {worker_name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
    
    def _analyze_performance(self):
        """Analyze task performance and detect issues."""
        try:
            for task_name, history in self.performance_history.items():
                if len(history) < 10:  # Need some data for analysis
                    continue
                
                recent_tasks = list(history)[-50:]  # Last 50 tasks
                
                # Calculate failure rate
                failed_tasks = sum(1 for task in recent_tasks if task['status'] != 'SUCCESS')
                failure_rate = failed_tasks / len(recent_tasks)
                
                if failure_rate > self.high_failure_rate_threshold:
                    logger.warning(
                        f"High failure rate detected for task {task_name}",
                        extra={
                            'task_name': task_name,
                            'failure_rate': failure_rate,
                            'threshold': self.high_failure_rate_threshold,
                            'sample_size': len(recent_tasks)
                        }
                    )
                
                # Calculate average processing time
                successful_tasks = [task for task in recent_tasks if task['status'] == 'SUCCESS']
                if successful_tasks:
                    avg_duration = sum(task['duration'] for task in successful_tasks) / len(successful_tasks)
                    
                    # Check for performance degradation
                    if len(successful_tasks) >= 20:
                        recent_avg = sum(task['duration'] for task in successful_tasks[-10:]) / 10
                        older_avg = sum(task['duration'] for task in successful_tasks[-20:-10]) / 10
                        
                        if recent_avg > older_avg * 1.5:  # 50% increase
                            logger.warning(
                                f"Performance degradation detected for task {task_name}",
                                extra={
                                    'task_name': task_name,
                                    'recent_avg_duration': recent_avg,
                                    'older_avg_duration': older_avg,
                                    'degradation_factor': recent_avg / older_avg
                                }
                            )
        
        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")
    
    def _update_prometheus_metrics(self):
        """Update Prometheus metrics with current data."""
        try:
            # Update queue depth metrics
            for queue_name, depths in self.queue_depths.items():
                current_depth = len(depths)
                metrics.update_queue_depth(queue_name, current_depth)
            
            # Update worker resource metrics
            for worker_name, worker_metric in self.worker_metrics.items():
                metrics.ai_model_resource_utilization.labels(
                    model=worker_name,
                    resource_type='cpu'
                ).set(worker_metric.cpu_percent)
                
                metrics.ai_model_resource_utilization.labels(
                    model=worker_name,
                    resource_type='memory'
                ).set(worker_metric.memory_mb)
        
        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {str(e)}")
    
    def _cleanup_old_metrics(self):
        """Clean up old task metrics to prevent memory leaks."""
        try:
            current_time = time.time()
            cleanup_threshold = current_time - (24 * 3600)  # 24 hours
            
            # Clean up old task metrics
            old_tasks = [
                task_id for task_id, task_metric in self.task_metrics.items()
                if task_metric.end_time and task_metric.end_time < cleanup_threshold
            ]
            
            for task_id in old_tasks:
                del self.task_metrics[task_id]
            
            if old_tasks:
                logger.debug(f"Cleaned up {len(old_tasks)} old task metrics")
            
            # Clean up old queue depth entries
            for queue_name, depths in self.queue_depths.items():
                while depths and depths[0] < cleanup_threshold:
                    depths.popleft()
        
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {str(e)}")
    
    def _extract_task_type(self, task_name: str) -> str:
        """Extract task type from task name for metrics."""
        if 'generate' in task_name.lower():
            return 'generation'
        elif 'analyze' in task_name.lower():
            return 'analysis'
        elif 'process' in task_name.lower():
            return 'processing'
        elif 'embed' in task_name.lower():
            return 'embedding'
        else:
            return 'other'
    
    def _extract_model_from_task(self, task_name: str) -> str:
        """Extract model name from task name for metrics."""
        # This would depend on your task naming conventions
        if 'llama' in task_name.lower():
            return 'llama'
        elif 'gpt' in task_name.lower():
            return 'gpt'
        elif 'claude' in task_name.lower():
            return 'claude'
        else:
            return 'unknown'
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get current worker status summary."""
        try:
            current_time = datetime.now()
            
            status = {
                'workers': {},
                'queues': {},
                'summary': {
                    'total_workers': len(self.worker_metrics),
                    'active_workers': 0,
                    'total_active_tasks': 0,
                    'total_processed_tasks': 0,
                    'total_failed_tasks': 0
                }
            }
            
            # Worker details
            for worker_name, worker_metric in self.worker_metrics.items():
                is_active = (
                    worker_metric.last_heartbeat and
                    current_time - worker_metric.last_heartbeat < timedelta(minutes=5)
                )
                
                status['workers'][worker_name] = {
                    'active': is_active,
                    'active_tasks': worker_metric.active_tasks,
                    'processed_tasks': worker_metric.processed_tasks,
                    'failed_tasks': worker_metric.failed_tasks,
                    'cpu_percent': worker_metric.cpu_percent,
                    'memory_mb': worker_metric.memory_mb,
                    'last_heartbeat': worker_metric.last_heartbeat.isoformat() if worker_metric.last_heartbeat else None
                }
                
                if is_active:
                    status['summary']['active_workers'] += 1
                
                status['summary']['total_active_tasks'] += worker_metric.active_tasks
                status['summary']['total_processed_tasks'] += worker_metric.processed_tasks
                status['summary']['total_failed_tasks'] += worker_metric.failed_tasks
            
            # Queue details
            for queue_name, depths in self.queue_depths.items():
                status['queues'][queue_name] = {
                    'current_depth': len(depths),
                    'avg_depth_1h': len(depths) if depths else 0  # Simplified
                }
            
            return status
        
        except Exception as e:
            logger.error(f"Error getting worker status: {str(e)}")
            return {'error': str(e)}
    
    def get_task_performance_summary(self, task_name: str = None) -> Dict[str, Any]:
        """Get performance summary for tasks."""
        try:
            if task_name:
                histories = {task_name: self.performance_history[task_name]}
            else:
                histories = dict(self.performance_history)
            
            summary = {}
            
            for name, history in histories.items():
                if not history:
                    continue
                
                recent_tasks = list(history)[-100:]  # Last 100 tasks
                successful_tasks = [t for t in recent_tasks if t['status'] == 'SUCCESS']
                
                if successful_tasks:
                    durations = [t['duration'] for t in successful_tasks]
                    
                    summary[name] = {
                        'total_tasks': len(recent_tasks),
                        'successful_tasks': len(successful_tasks),
                        'failed_tasks': len(recent_tasks) - len(successful_tasks),
                        'success_rate': len(successful_tasks) / len(recent_tasks),
                        'avg_duration': sum(durations) / len(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations),
                        'p95_duration': sorted(durations)[int(len(durations) * 0.95)] if durations else 0
                    }
            
            return summary
        
        except Exception as e:
            logger.error(f"Error getting task performance summary: {str(e)}")
            return {'error': str(e)}


# Global worker monitor instance (to be initialized with Celery app)
worker_monitor: Optional[WorkerMonitor] = None


def initialize_worker_monitoring(celery_app: Celery) -> WorkerMonitor:
    """Initialize worker monitoring with Celery app."""
    global worker_monitor
    worker_monitor = WorkerMonitor(celery_app)
    return worker_monitor


def get_worker_monitor() -> Optional[WorkerMonitor]:
    """Get the global worker monitor instance."""
    return worker_monitor