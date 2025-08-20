"""
Query Performance Monitoring Service

Provides comprehensive monitoring, analysis, and optimization recommendations
for database query performance across the application.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import statistics
import threading
import json

from shared.services.redis_cache_service import get_redis_cache
from shared.utils.database_setup import get_database_stats, get_engine, get_async_engine

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Query performance metrics."""
    query_hash: str
    query_text: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    median_time_ms: float = 0.0
    p95_time_ms: float = 0.0
    last_execution: Optional[datetime] = None
    slow_query_count: int = 0
    error_count: int = 0
    execution_times: List[float] = None
    
    def __post_init__(self):
        if self.execution_times is None:
            self.execution_times = []


@dataclass
class SlowQuery:
    """Slow query record."""
    query_hash: str
    query_text: str
    execution_time_ms: float
    executed_at: datetime
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


class QueryPerformanceMonitor:
    """Monitors and analyzes database query performance."""
    
    def __init__(self):
        self.logger = logger
        self._cache = None
        self._metrics: Dict[str, QueryMetrics] = {}
        self._slow_queries: List[SlowQuery] = []
        self._lock = threading.Lock()
        
        # Configuration
        self.slow_query_threshold_ms = 1000  # 1 second
        self.max_slow_queries = 1000
        self.max_execution_times = 100  # Keep last 100 execution times per query
        self.cache_ttl = 300  # 5 minutes
        self.monitoring_enabled = True
        
        # Performance counters
        self.total_queries = 0
        self.slow_queries_count = 0
        self.error_queries_count = 0
        
    async def _get_cache(self):
        """Get Redis cache instance with lazy initialization."""
        if not self._cache:
            self._cache = await get_redis_cache()
        return self._cache
    
    def _generate_query_hash(self, query_text: str) -> str:
        """Generate consistent hash for query text."""
        import hashlib
        # Normalize query text for consistent hashing
        normalized = query_text.strip().lower()
        # Remove parameter placeholders to group similar queries
        import re
        normalized = re.sub(r'\$\d+', '?', normalized)  # PostgreSQL parameters
        normalized = re.sub(r'%\([^)]+\)s', '?', normalized)  # Python parameters
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def start_monitoring(self):
        """Start query performance monitoring by registering SQL event listeners."""
        try:
            engine = get_engine()
            async_engine = get_async_engine()
            
            if engine:
                self._register_sync_listeners(engine)
                logger.info("Sync database query monitoring enabled")
            
            if async_engine:
                self._register_async_listeners(async_engine.sync_engine)
                logger.info("Async database query monitoring enabled")
                
            self.monitoring_enabled = True
            logger.info("Query performance monitoring started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start query performance monitoring: {e}")
            self.monitoring_enabled = False
    
    def _register_sync_listeners(self, engine: Engine):
        """Register SQLAlchemy event listeners for sync engine."""
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                execution_time = (time.time() - context._query_start_time) * 1000
                self._record_query_execution(
                    query_text=statement,
                    execution_time_ms=execution_time,
                    parameters=parameters,
                    error=None
                )
        
        @event.listens_for(engine, "handle_error")
        def handle_error(exception_context):
            if hasattr(exception_context.connection, '_query_start_time'):
                execution_time = (time.time() - exception_context.connection._query_start_time) * 1000
                self._record_query_execution(
                    query_text=exception_context.statement,
                    execution_time_ms=execution_time,
                    parameters=exception_context.parameters,
                    error=str(exception_context.original_exception)
                )
    
    def _register_async_listeners(self, engine: Engine):
        """Register event listeners for async engine (using sync engine)."""
        # Async engines use the same event system through the sync_engine
        self._register_sync_listeners(engine)
    
    def _record_query_execution(
        self,
        query_text: str,
        execution_time_ms: float,
        parameters: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None
    ):
        """Record a query execution for performance analysis."""
        if not self.monitoring_enabled:
            return
        
        try:
            with self._lock:
                self.total_queries += 1
                
                query_hash = self._generate_query_hash(query_text)
                
                # Update or create metrics
                if query_hash not in self._metrics:
                    self._metrics[query_hash] = QueryMetrics(
                        query_hash=query_hash,
                        query_text=query_text
                    )
                
                metrics = self._metrics[query_hash]
                metrics.execution_count += 1
                metrics.total_time_ms += execution_time_ms
                metrics.last_execution = datetime.utcnow()
                
                # Update timing statistics
                metrics.min_time_ms = min(metrics.min_time_ms, execution_time_ms)
                metrics.max_time_ms = max(metrics.max_time_ms, execution_time_ms)
                metrics.avg_time_ms = metrics.total_time_ms / metrics.execution_count
                
                # Track execution times for percentile calculations
                metrics.execution_times.append(execution_time_ms)
                if len(metrics.execution_times) > self.max_execution_times:
                    metrics.execution_times.pop(0)
                
                # Calculate percentiles if we have enough data
                if len(metrics.execution_times) >= 10:
                    sorted_times = sorted(metrics.execution_times)
                    metrics.median_time_ms = statistics.median(sorted_times)
                    p95_index = int(0.95 * len(sorted_times))
                    metrics.p95_time_ms = sorted_times[p95_index]
                
                # Handle errors
                if error:
                    metrics.error_count += 1
                    self.error_queries_count += 1
                
                # Record slow queries
                if execution_time_ms > self.slow_query_threshold_ms:
                    metrics.slow_query_count += 1
                    self.slow_queries_count += 1
                    
                    slow_query = SlowQuery(
                        query_hash=query_hash,
                        query_text=query_text,
                        execution_time_ms=execution_time_ms,
                        executed_at=datetime.utcnow(),
                        user_id=user_id,
                        session_id=session_id,
                        parameters=parameters
                    )
                    
                    self._slow_queries.append(slow_query)
                    
                    # Limit slow query storage
                    if len(self._slow_queries) > self.max_slow_queries:
                        self._slow_queries.pop(0)
                    
                    # Log slow query
                    logger.warning(
                        f"Slow query detected: {execution_time_ms:.2f}ms - {query_text[:200]}..."
                    )
        
        except Exception as e:
            logger.error(f"Error recording query execution: {e}")
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        try:
            cache = await self._get_cache()
            cache_key = "query_performance:summary"
            
            # Try to get from cache first
            cached_summary = await cache.get(cache_key)
            if cached_summary:
                return cached_summary
            
            with self._lock:
                # Calculate summary statistics
                total_execution_time = sum(m.total_time_ms for m in self._metrics.values())
                avg_query_time = total_execution_time / max(self.total_queries, 1)
                
                # Find top slow queries
                top_slow_queries = sorted(
                    [m for m in self._metrics.values() if m.avg_time_ms > 0],
                    key=lambda x: x.avg_time_ms,
                    reverse=True
                )[:10]
                
                # Find most frequent queries
                top_frequent_queries = sorted(
                    self._metrics.values(),
                    key=lambda x: x.execution_count,
                    reverse=True
                )[:10]
                
                # Get database connection pool stats
                db_stats = get_database_stats()
                
                summary = {
                    "monitoring_enabled": self.monitoring_enabled,
                    "total_queries": self.total_queries,
                    "unique_queries": len(self._metrics),
                    "slow_queries_count": self.slow_queries_count,
                    "error_queries_count": self.error_queries_count,
                    "average_query_time_ms": round(avg_query_time, 2),
                    "total_execution_time_ms": round(total_execution_time, 2),
                    "slow_query_threshold_ms": self.slow_query_threshold_ms,
                    "top_slow_queries": [
                        {
                            "query_hash": q.query_hash,
                            "query_text": q.query_text[:200] + "..." if len(q.query_text) > 200 else q.query_text,
                            "avg_time_ms": round(q.avg_time_ms, 2),
                            "execution_count": q.execution_count,
                            "slow_query_count": q.slow_query_count
                        }
                        for q in top_slow_queries
                    ],
                    "top_frequent_queries": [
                        {
                            "query_hash": q.query_hash,
                            "query_text": q.query_text[:200] + "..." if len(q.query_text) > 200 else q.query_text,
                            "execution_count": q.execution_count,
                            "avg_time_ms": round(q.avg_time_ms, 2)
                        }
                        for q in top_frequent_queries
                    ],
                    "database_pool_stats": db_stats,
                    "generated_at": datetime.utcnow().isoformat()
                }
            
            # Cache the summary
            await cache.set(cache_key, summary, ttl=self.cache_ttl)
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}
    
    async def get_query_details(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Get detailed metrics for a specific query."""
        try:
            with self._lock:
                if query_hash not in self._metrics:
                    return None
                
                metrics = self._metrics[query_hash]
                
                # Get recent slow executions for this query
                recent_slow = [
                    {
                        "execution_time_ms": sq.execution_time_ms,
                        "executed_at": sq.executed_at.isoformat(),
                        "user_id": sq.user_id,
                        "session_id": sq.session_id
                    }
                    for sq in self._slow_queries[-50:]  # Last 50 slow queries
                    if sq.query_hash == query_hash
                ]
                
                return {
                    **asdict(metrics),
                    "recent_slow_executions": recent_slow,
                    "execution_times": metrics.execution_times[-20:]  # Last 20 execution times
                }
        
        except Exception as e:
            logger.error(f"Error getting query details: {e}")
            return None
    
    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on query performance."""
        try:
            recommendations = []
            
            with self._lock:
                # Find queries that could benefit from indexing
                for metrics in self._metrics.values():
                    if (metrics.avg_time_ms > self.slow_query_threshold_ms and
                        metrics.execution_count > 10):
                        
                        query_text = metrics.query_text.lower()
                        
                        # Detect common patterns that suggest missing indexes
                        if "where" in query_text and "order by" in query_text:
                            recommendations.append({
                                "type": "INDEX_OPTIMIZATION",
                                "priority": "HIGH",
                                "query_hash": metrics.query_hash,
                                "query_text": metrics.query_text[:200],
                                "avg_time_ms": metrics.avg_time_ms,
                                "execution_count": metrics.execution_count,
                                "recommendation": "Consider adding composite index on columns used in WHERE and ORDER BY clauses",
                                "estimated_impact": "HIGH"
                            })
                        
                        elif "join" in query_text:
                            recommendations.append({
                                "type": "JOIN_OPTIMIZATION",
                                "priority": "MEDIUM",
                                "query_hash": metrics.query_hash,
                                "query_text": metrics.query_text[:200],
                                "avg_time_ms": metrics.avg_time_ms,
                                "execution_count": metrics.execution_count,
                                "recommendation": "Review JOIN conditions and ensure proper indexes on join columns",
                                "estimated_impact": "MEDIUM"
                            })
                        
                        elif "select *" in query_text:
                            recommendations.append({
                                "type": "QUERY_STRUCTURE",
                                "priority": "LOW",
                                "query_hash": metrics.query_hash,
                                "query_text": metrics.query_text[:200],
                                "avg_time_ms": metrics.avg_time_ms,
                                "execution_count": metrics.execution_count,
                                "recommendation": "Avoid SELECT * - specify only needed columns",
                                "estimated_impact": "LOW"
                            })
                
                # Check for connection pool issues
                db_stats = get_database_stats()
                if db_stats.get("sync_engine"):
                    sync_stats = db_stats["sync_engine"]
                    if sync_stats["connections_overflow"] > 0:
                        recommendations.append({
                            "type": "CONNECTION_POOL",
                            "priority": "HIGH",
                            "recommendation": f"Connection pool overflow detected ({sync_stats['connections_overflow']} overflow connections). Consider increasing pool size or optimizing connection usage.",
                            "estimated_impact": "HIGH"
                        })
            
            return sorted(recommendations, key=lambda x: x.get("priority", "LOW") == "HIGH", reverse=True)
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return []
    
    async def clear_metrics(self):
        """Clear all collected metrics (useful for testing or resetting)."""
        try:
            with self._lock:
                self._metrics.clear()
                self._slow_queries.clear()
                self.total_queries = 0
                self.slow_queries_count = 0
                self.error_queries_count = 0
            
            # Clear cache
            cache = await self._get_cache()
            await cache.delete_pattern("query_performance:*")
            
            logger.info("Query performance metrics cleared")
            
        except Exception as e:
            logger.error(f"Error clearing metrics: {e}")
    
    def stop_monitoring(self):
        """Stop query performance monitoring."""
        self.monitoring_enabled = False
        logger.info("Query performance monitoring stopped")


# Context manager for tracking individual query performance
@asynccontextmanager
async def track_query_performance(
    query_name: str,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None
):
    """Context manager to track performance of a specific query or operation."""
    start_time = time.time()
    error_occurred = None
    
    try:
        yield
    except Exception as e:
        error_occurred = str(e)
        raise
    finally:
        execution_time = (time.time() - start_time) * 1000
        
        # Record the execution
        query_performance_service._record_query_execution(
            query_text=f"TRACKED_OPERATION: {query_name}",
            execution_time_ms=execution_time,
            error=error_occurred,
            user_id=user_id,
            session_id=session_id
        )


# Global service instance
query_performance_service = QueryPerformanceMonitor()


# Convenience functions
async def get_performance_summary() -> Dict[str, Any]:
    """Get query performance summary."""
    return await query_performance_service.get_performance_summary()


async def get_optimization_recommendations() -> List[Dict[str, Any]]:
    """Get optimization recommendations."""
    return await query_performance_service.get_optimization_recommendations()


def start_query_monitoring():
    """Start query performance monitoring."""
    query_performance_service.start_monitoring()


def stop_query_monitoring():
    """Stop query performance monitoring."""
    query_performance_service.stop_monitoring()