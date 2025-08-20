"""
Comprehensive Prometheus Metrics Configuration for Performance Tracking

This module provides centralized metrics tracking for various system components.
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Dict, Any
import time
import threading

class SystemMetrics:
    def __init__(self, namespace: str = "app"):
        self.namespace = namespace
        
        # Database Metrics
        self.db_connection_pool_size = Gauge(
            f'{namespace}_database_connection_pool_size', 
            'Total database connection pool size',
            ['pool_type']
        )
        self.db_connection_utilization = Gauge(
            f'{namespace}_database_connection_utilization', 
            'Database connection pool utilization percentage',
            ['pool_type']
        )
        self.db_connection_requests = Counter(
            f'{namespace}_database_connection_requests', 
            'Total database connection requests',
            ['pool_type', 'status']
        )
        
        # Cache Metrics
        self.cache_hits = Counter(
            f'{namespace}_cache_hits', 
            'Total cache hits'
        )
        self.cache_misses = Counter(
            f'{namespace}_cache_misses', 
            'Total cache misses'
        )
        self.cache_size = Gauge(
            f'{namespace}_cache_size', 
            'Current cache size'
        )
        
        # Request Latency Histogram
        self.request_latency = Histogram(
            f'{namespace}_request_latency_seconds', 
            'Request latency in seconds',
            ['endpoint']
        )
        
        # Background metrics collection thread
        self._metrics_thread = None
        self._stop_metrics_collection = threading.Event()
    
    def update_database_metrics(self, database_stats: Dict[str, Any]):
        """Update database connection pool metrics."""
        for pool_type, stats in database_stats.items():
            if stats:
                self.db_connection_pool_size.labels(pool_type=pool_type).set(
                    stats.get('total_connections', 0)
                )
                self.db_connection_utilization.labels(pool_type=pool_type).set(
                    stats.get('utilization_percent', 0)
                )
    
    def record_cache_metrics(self, cache_metrics: Dict[str, Any]):
        """Record cache performance metrics."""
        self.cache_hits.inc(cache_metrics.get('hits', 0))
        self.cache_misses.inc(cache_metrics.get('misses', 0))
        self.cache_size.set(cache_metrics.get('cache_size', 0))
    
    def start_metrics_server(self, port: int = 8000):
        """Start a Prometheus metrics HTTP server."""
        start_http_server(port)
    
    def start_background_metrics_collection(
        self, 
        database_stats_func=None, 
        cache_metrics_func=None, 
        interval: int = 60
    ):
        """
        Start background thread for periodically collecting metrics.
        
        :param database_stats_func: Function to retrieve database stats
        :param cache_metrics_func: Function to retrieve cache metrics
        :param interval: Metrics collection interval in seconds
        """
        def _metrics_collector():
            while not self._stop_metrics_collection.is_set():
                if database_stats_func:
                    try:
                        self.update_database_metrics(database_stats_func())
                    except Exception as e:
                        print(f"Error collecting database metrics: {e}")
                
                if cache_metrics_func:
                    try:
                        self.record_cache_metrics(cache_metrics_func())
                    except Exception as e:
                        print(f"Error collecting cache metrics: {e}")
                
                time.sleep(interval)
        
        self._metrics_thread = threading.Thread(target=_metrics_collector, daemon=True)
        self._metrics_thread.start()
    
    def stop_background_metrics_collection(self):
        """Stop background metrics collection thread."""
        if self._metrics_thread:
            self._stop_metrics_collection.set()
            self._metrics_thread.join()

# Example usage in main application:
# from shared.prometheus_metrics import SystemMetrics
# from shared.database_setup import get_database_stats
# from shared.cache_utils import cache_manager
#
# metrics = SystemMetrics()
# metrics.start_metrics_server()  # Start Prometheus metrics endpoint
# metrics.start_background_metrics_collection(
#     database_stats_func=get_database_stats,
#     cache_metrics_func=cache_manager.get_metrics
# )