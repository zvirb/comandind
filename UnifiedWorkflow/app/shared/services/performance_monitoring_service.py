"""
Database Performance Monitoring Service

This service provides comprehensive monitoring and metrics collection for database
performance, query execution times, connection pool health, and cache performance.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import psutil
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_session
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Query performance metrics."""
    query_hash: str
    query_type: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf') 
    max_time_ms: float = 0.0
    last_executed: Optional[datetime] = None
    
    def update(self, execution_time_ms: float):
        """Update metrics with new execution time."""
        self.execution_count += 1
        self.total_time_ms += execution_time_ms
        self.avg_time_ms = self.total_time_ms / self.execution_count
        self.min_time_ms = min(self.min_time_ms, execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, execution_time_ms)
        self.last_executed = datetime.now()

@dataclass
class DatabaseHealthMetrics:
    """Database health and performance metrics."""
    # Connection metrics
    active_connections: int = 0
    idle_connections: int = 0
    max_connections: int = 0
    connection_utilization_percent: float = 0.0
    
    # Query performance
    slow_queries_count: int = 0
    avg_query_time_ms: float = 0.0
    queries_per_second: float = 0.0
    
    # Resource usage
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_percent: float = 0.0
    
    # Cache performance
    cache_hit_rate_percent: float = 0.0
    cache_memory_usage_mb: float = 0.0
    
    # Database size metrics
    database_size_mb: float = 0.0
    largest_tables: List[Dict[str, Any]] = None
    
    # Index usage
    unused_indexes: List[str] = None
    missing_indexes: List[str] = None
    
    def __post_init__(self):
        if self.largest_tables is None:
            self.largest_tables = []
        if self.unused_indexes is None:
            self.unused_indexes = []
        if self.missing_indexes is None:
            self.missing_indexes = []

class PerformanceMonitor:
    """Comprehensive database and system performance monitoring."""
    
    def __init__(self):
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.slow_query_threshold_ms = 1000  # 1 second
        self.monitoring_enabled = True
        self.redis_cache = None
        
    async def initialize(self):
        """Initialize performance monitoring."""
        try:
            self.redis_cache = await get_redis_cache()
            logger.info("Performance monitoring service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize performance monitoring: {e}")
    
    @asynccontextmanager
    async def monitor_query(self, query: str, query_type: str = "unknown"):
        """Context manager to monitor query execution time."""
        if not self.monitoring_enabled:
            yield
            return
            
        start_time = time.time()
        query_hash = str(hash(query.strip()[:200]))  # Use first 200 chars for hash
        
        try:
            yield
        finally:
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Update query metrics
            if query_hash not in self.query_metrics:
                self.query_metrics[query_hash] = QueryMetrics(
                    query_hash=query_hash,
                    query_type=query_type
                )
            
            self.query_metrics[query_hash].update(execution_time_ms)
            
            # Log slow queries
            if execution_time_ms > self.slow_query_threshold_ms:
                logger.warning(
                    f"Slow query detected: {execution_time_ms:.2f}ms - "
                    f"Type: {query_type} - Hash: {query_hash}"
                )
    
    async def get_database_health_metrics(self) -> DatabaseHealthMetrics:
        """Collect comprehensive database health metrics."""
        metrics = DatabaseHealthMetrics()
        
        try:
            async with get_session() as session:
                # Connection metrics
                await self._collect_connection_metrics(session, metrics)
                
                # Query performance metrics
                await self._collect_query_performance_metrics(session, metrics)
                
                # Database size metrics
                await self._collect_database_size_metrics(session, metrics)
                
                # Index usage metrics
                await self._collect_index_usage_metrics(session, metrics)
                
            # System resource metrics
            await self._collect_system_metrics(metrics)
            
            # Cache performance metrics
            await self._collect_cache_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting database health metrics: {e}")
            
        return metrics
    
    async def _collect_connection_metrics(self, session: AsyncSession, metrics: DatabaseHealthMetrics):
        """Collect database connection metrics."""
        try:
            # Get connection statistics
            result = await session.execute(text("""
                SELECT 
                    state,
                    COUNT(*) as count
                FROM pg_stat_activity 
                WHERE datname = current_database()
                GROUP BY state
            """))
            
            connection_stats = {row.state: row.count for row in result}
            
            metrics.active_connections = connection_stats.get('active', 0)
            metrics.idle_connections = connection_stats.get('idle', 0)
            
            # Get max connections
            result = await session.execute(text("SHOW max_connections"))
            metrics.max_connections = int(result.scalar())
            
            total_connections = metrics.active_connections + metrics.idle_connections
            metrics.connection_utilization_percent = (
                (total_connections / metrics.max_connections) * 100 
                if metrics.max_connections > 0 else 0
            )
            
        except Exception as e:
            logger.error(f"Error collecting connection metrics: {e}")
    
    async def _collect_query_performance_metrics(self, session: AsyncSession, metrics: DatabaseHealthMetrics):
        """Collect query performance metrics."""
        try:
            # Get slow queries count (from pg_stat_statements if available)
            result = await session.execute(text("""
                SELECT COUNT(*) as slow_queries
                FROM pg_stat_statements 
                WHERE mean_exec_time > %s
            """), (self.slow_query_threshold_ms,))
            
            metrics.slow_queries_count = result.scalar() or 0
            
            # Get average query time
            result = await session.execute(text("""
                SELECT AVG(mean_exec_time) as avg_time
                FROM pg_stat_statements
            """))
            
            metrics.avg_query_time_ms = result.scalar() or 0.0
            
            # Calculate queries per second (approximate)
            result = await session.execute(text("""
                SELECT SUM(calls) as total_calls
                FROM pg_stat_statements
            """))
            
            total_calls = result.scalar() or 0
            # Rough estimate: divide by uptime in seconds
            result = await session.execute(text("""
                SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time())) as uptime_seconds
            """))
            
            uptime_seconds = result.scalar() or 1
            metrics.queries_per_second = total_calls / uptime_seconds if uptime_seconds > 0 else 0
            
        except Exception as e:
            # pg_stat_statements might not be available
            logger.debug(f"Query performance metrics not available: {e}")
            metrics.slow_queries_count = len([
                m for m in self.query_metrics.values() 
                if m.avg_time_ms > self.slow_query_threshold_ms
            ])
            
            if self.query_metrics:
                metrics.avg_query_time_ms = sum(
                    m.avg_time_ms for m in self.query_metrics.values()
                ) / len(self.query_metrics)
    
    async def _collect_database_size_metrics(self, session: AsyncSession, metrics: DatabaseHealthMetrics):
        """Collect database size and table metrics."""
        try:
            # Get database size
            result = await session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                       pg_database_size(current_database()) as size_bytes
            """))
            
            row = result.fetchone()
            metrics.database_size_mb = row.size_bytes / (1024 * 1024) if row else 0.0
            
            # Get largest tables
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """))
            
            metrics.largest_tables = [
                {
                    "table_name": f"{row.schemaname}.{row.tablename}",
                    "size": row.size,
                    "size_mb": row.size_bytes / (1024 * 1024)
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error collecting database size metrics: {e}")
    
    async def _collect_index_usage_metrics(self, session: AsyncSession, metrics: DatabaseHealthMetrics):
        """Collect index usage and recommendations."""
        try:
            # Find unused indexes
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_tup_read = 0 AND idx_tup_fetch = 0
                AND schemaname = 'public'
                ORDER BY pg_relation_size(indexrelid) DESC
                LIMIT 20
            """))
            
            metrics.unused_indexes = [f"{row.schemaname}.{row.tablename}.{row.indexname}" for row in result]
            
            # Find tables with sequential scans (potential missing indexes)
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch,
                    seq_tup_read::float / GREATEST(seq_scan, 1) as avg_seq_tup_read
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                AND seq_scan > 100  -- Tables with more than 100 sequential scans
                AND (idx_scan = 0 OR seq_scan > idx_scan * 10)  -- Much more seq scans than index scans
                ORDER BY seq_tup_read DESC
                LIMIT 10
            """))
            
            metrics.missing_indexes = [
                f"{row.schemaname}.{row.tablename} (seq_scans: {row.seq_scan}, avg_rows: {row.avg_seq_tup_read:.0f})"
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Error collecting index usage metrics: {e}")
    
    async def _collect_system_metrics(self, metrics: DatabaseHealthMetrics):
        """Collect system resource metrics."""
        try:
            # CPU usage
            metrics.cpu_usage_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.memory_usage_mb = memory.used / (1024 * 1024)
            
            # Disk usage (for data directory)
            disk = psutil.disk_usage('/')
            metrics.disk_usage_percent = (disk.used / disk.total) * 100
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_cache_metrics(self, metrics: DatabaseHealthMetrics):
        """Collect cache performance metrics."""
        try:
            if self.redis_cache:
                cache_metrics = await self.redis_cache.get_cache_metrics()
                metrics.cache_hit_rate_percent = cache_metrics.get('hit_rate_percent', 0.0)
                
                # Estimate cache memory usage from Redis info
                redis_info = cache_metrics.get('redis_info', {})
                used_memory = redis_info.get('used_memory_human', '0B')
                
                # Parse memory string (e.g., "1.5M" -> 1.5)
                if used_memory.endswith('M'):
                    metrics.cache_memory_usage_mb = float(used_memory[:-1])
                elif used_memory.endswith('K'):
                    metrics.cache_memory_usage_mb = float(used_memory[:-1]) / 1024
                elif used_memory.endswith('G'):
                    metrics.cache_memory_usage_mb = float(used_memory[:-1]) * 1024
                    
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
    
    async def get_query_performance_report(self) -> Dict[str, Any]:
        """Get detailed query performance report."""
        if not self.query_metrics:
            return {"message": "No query metrics available"}
        
        # Sort queries by average execution time
        sorted_queries = sorted(
            self.query_metrics.values(),
            key=lambda x: x.avg_time_ms,
            reverse=True
        )
        
        slow_queries = [q for q in sorted_queries if q.avg_time_ms > self.slow_query_threshold_ms]
        
        return {
            "total_unique_queries": len(self.query_metrics),
            "slow_queries_count": len(slow_queries),
            "slowest_queries": [asdict(q) for q in sorted_queries[:10]],
            "most_executed_queries": sorted(
                [asdict(q) for q in self.query_metrics.values()],
                key=lambda x: x['execution_count'],
                reverse=True
            )[:10],
            "performance_summary": {
                "avg_execution_time_ms": sum(q.avg_time_ms for q in self.query_metrics.values()) / len(self.query_metrics),
                "total_executions": sum(q.execution_count for q in self.query_metrics.values()),
                "total_time_ms": sum(q.total_time_ms for q in self.query_metrics.values())
            }
        }
    
    async def get_performance_recommendations(self) -> List[Dict[str, str]]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        try:
            metrics = await self.get_database_health_metrics()
            
            # Connection pool recommendations
            if metrics.connection_utilization_percent > 80:
                recommendations.append({
                    "type": "connection_pool",
                    "severity": "high",
                    "message": f"Connection utilization is high ({metrics.connection_utilization_percent:.1f}%). Consider increasing max_connections or optimizing connection usage.",
                    "action": "Review PgBouncer configuration and connection pooling strategy."
                })
            
            # Slow query recommendations
            if metrics.slow_queries_count > 10:
                recommendations.append({
                    "type": "query_performance",
                    "severity": "medium",
                    "message": f"Found {metrics.slow_queries_count} slow queries. Consider query optimization.",
                    "action": "Review slow query log and add appropriate indexes."
                })
            
            # Index recommendations
            if len(metrics.unused_indexes) > 5:
                recommendations.append({
                    "type": "index_optimization",
                    "severity": "low",
                    "message": f"Found {len(metrics.unused_indexes)} unused indexes consuming storage.",
                    "action": "Consider dropping unused indexes to free up space and improve write performance."
                })
            
            if len(metrics.missing_indexes) > 0:
                recommendations.append({
                    "type": "index_optimization",
                    "severity": "medium",
                    "message": f"Found {len(metrics.missing_indexes)} tables with high sequential scan ratios.",
                    "action": "Consider adding indexes to frequently queried columns."
                })
            
            # Cache recommendations
            if metrics.cache_hit_rate_percent < 80:
                recommendations.append({
                    "type": "cache_performance",
                    "severity": "medium",
                    "message": f"Cache hit rate is low ({metrics.cache_hit_rate_percent:.1f}%). Consider cache optimization.",
                    "action": "Review caching strategy and increase cache TTL for frequently accessed data."
                })
            
            # System resource recommendations
            if metrics.cpu_usage_percent > 80:
                recommendations.append({
                    "type": "system_resources",
                    "severity": "high",
                    "message": f"CPU usage is high ({metrics.cpu_usage_percent:.1f}%).",
                    "action": "Consider scaling up the database server or optimizing resource-intensive queries."
                })
            
            if metrics.disk_usage_percent > 85:
                recommendations.append({
                    "type": "system_resources",
                    "severity": "high",
                    "message": f"Disk usage is high ({metrics.disk_usage_percent:.1f}%).",
                    "action": "Consider disk cleanup, archiving old data, or expanding storage capacity."
                })
                
        except Exception as e:
            logger.error(f"Error generating performance recommendations: {e}")
            recommendations.append({
                "type": "monitoring_error",
                "severity": "low",
                "message": "Unable to generate complete performance recommendations.",
                "action": "Check monitoring service configuration and database connectivity."
            })
        
        return recommendations
    
    def reset_metrics(self):
        """Reset all collected metrics."""
        self.query_metrics.clear()
        logger.info("Performance metrics reset")
    
    def enable_monitoring(self):
        """Enable performance monitoring."""
        self.monitoring_enabled = True
        logger.info("Performance monitoring enabled")
    
    def disable_monitoring(self):
        """Disable performance monitoring."""
        self.monitoring_enabled = False
        logger.info("Performance monitoring disabled")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

async def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    if performance_monitor.redis_cache is None:
        await performance_monitor.initialize()
    return performance_monitor