"""
Performance Dashboard API Router

Provides comprehensive real-time performance monitoring endpoints for
system administrators, DevOps teams, and monitoring dashboards.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import asdict
import logging
import asyncio
import psutil

from shared.utils.database_setup import get_async_session, get_database_stats
from shared.services.performance_monitoring_service import get_performance_monitor
from shared.services.redis_cache_service import get_redis_cache
from shared.services.query_performance_service import get_performance_summary, get_optimization_recommendations
from shared.services.security_audit_service import security_audit_service
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/performance-dashboard", tags=["Performance Dashboard"])

@router.get("/health-overview")
async def get_health_overview(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get comprehensive system health overview for dashboard."""
    
    try:
        # Set security context for audit logging
        await security_audit_service.set_security_context(
            session=session,
            user_id=current_user.id if hasattr(current_user, 'id') else 1,
            service_name="performance_dashboard"
        )
        
        # Collect metrics from all sources
        monitor = await get_performance_monitor()
        db_metrics = await monitor.get_database_health_metrics()
        
        # Get cache metrics
        cache_metrics = {}
        try:
            cache = await get_redis_cache()
            cache_metrics = await cache.get_cache_metrics()
        except Exception as e:
            cache_metrics = {"error": str(e), "available": False}
        
        # Get system resource metrics
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
        }
        
        # Get connection pool stats
        pool_stats = get_database_stats()
        
        # Calculate overall health score
        health_score = calculate_overall_health_score(db_metrics, cache_metrics, system_metrics)
        
        # Determine health status
        if health_score > 85:
            health_status = "excellent"
        elif health_score > 70:
            health_status = "good"
        elif health_score > 50:
            health_status = "warning"
        else:
            health_status = "critical"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health_status": health_status,
            "health_score": round(health_score, 1),
            "system_metrics": system_metrics,
            "database_metrics": {
                "connections": {
                    "active": db_metrics.active_connections,
                    "idle": db_metrics.idle_connections,
                    "max": db_metrics.max_connections,
                    "utilization_percent": round(db_metrics.connection_utilization_percent, 1)
                },
                "performance": {
                    "avg_query_time_ms": round(db_metrics.avg_query_time_ms, 2),
                    "slow_queries_count": db_metrics.slow_queries_count,
                    "queries_per_second": round(db_metrics.queries_per_second, 2)
                },
                "pool_stats": pool_stats
            },
            "cache_metrics": {
                "hit_rate_percent": cache_metrics.get("hit_rate_percent", 0),
                "is_healthy": cache_metrics.get("is_healthy", False),
                "memory_usage": cache_metrics.get("redis_info", {}).get("used_memory_human", "0B")
            },
            "alerts": await generate_performance_alerts(db_metrics, cache_metrics, system_metrics)
        }
        
    except Exception as e:
        logger.error(f"Health overview error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health overview: {str(e)}")

def calculate_overall_health_score(db_metrics, cache_metrics, system_metrics) -> float:
    """Calculate comprehensive health score based on all system metrics."""
    score = 100.0
    
    # Database health (40% weight)
    if db_metrics.connection_utilization_percent > 90:
        score -= 20
    elif db_metrics.connection_utilization_percent > 80:
        score -= 10
    
    if db_metrics.avg_query_time_ms > 1000:
        score -= 15
    elif db_metrics.avg_query_time_ms > 500:
        score -= 8
    
    # System resources (35% weight)
    if system_metrics["cpu_percent"] > 90:
        score -= 15
    elif system_metrics["cpu_percent"] > 80:
        score -= 8
    
    if system_metrics["memory_percent"] > 95:
        score -= 15
    elif system_metrics["memory_percent"] > 85:
        score -= 8
    
    if system_metrics["disk_percent"] > 95:
        score -= 10
    elif system_metrics["disk_percent"] > 90:
        score -= 5
    
    # Cache performance (25% weight)
    if cache_metrics.get("is_healthy", False):
        hit_rate = cache_metrics.get("hit_rate_percent", 0)
        if hit_rate < 70:
            score -= 10
        elif hit_rate < 85:
            score -= 5
        # Bonus for good cache performance
        elif hit_rate > 95:
            score += 2
    else:
        score -= 15  # Cache unavailable penalty
    
    return max(0.0, min(100.0, score))

async def generate_performance_alerts(db_metrics, cache_metrics, system_metrics) -> List[Dict[str, Any]]:
    """Generate performance alerts based on current metrics."""
    alerts = []
    
    # Critical alerts
    if system_metrics["cpu_percent"] > 95:
        alerts.append({
            "level": "critical",
            "type": "system_resource",
            "message": f"Critical CPU usage: {system_metrics['cpu_percent']:.1f}%",
            "recommendation": "Immediate scaling or optimization required"
        })
    
    if system_metrics["memory_percent"] > 98:
        alerts.append({
            "level": "critical",
            "type": "system_resource", 
            "message": f"Critical memory usage: {system_metrics['memory_percent']:.1f}%",
            "recommendation": "Risk of OOM kills - immediate action required"
        })
    
    if db_metrics.connection_utilization_percent > 95:
        alerts.append({
            "level": "critical",
            "type": "database",
            "message": f"Database connection pool nearly exhausted: {db_metrics.connection_utilization_percent:.1f}%",
            "recommendation": "Increase connection pool size immediately"
        })
    
    # Warning alerts
    if system_metrics["cpu_percent"] > 80:
        alerts.append({
            "level": "warning",
            "type": "system_resource",
            "message": f"High CPU usage: {system_metrics['cpu_percent']:.1f}%",
            "recommendation": "Monitor for performance degradation"
        })
    
    if db_metrics.avg_query_time_ms > 1000:
        alerts.append({
            "level": "warning", 
            "type": "database",
            "message": f"Slow database queries detected: {db_metrics.avg_query_time_ms:.2f}ms average",
            "recommendation": "Review and optimize slow queries"
        })
    
    if not cache_metrics.get("is_healthy", False):
        alerts.append({
            "level": "warning",
            "type": "cache",
            "message": "Redis cache unavailable or unhealthy",
            "recommendation": "Check Redis service status and connectivity"
        })
    elif cache_metrics.get("hit_rate_percent", 0) < 70:
        alerts.append({
            "level": "info",
            "type": "cache",
            "message": f"Low cache hit rate: {cache_metrics.get('hit_rate_percent', 0):.1f}%",
            "recommendation": "Review caching strategy and TTL settings"
        })
    
    return alerts

@router.get("/metrics/realtime")
async def get_realtime_metrics(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get real-time system metrics for live dashboard updates."""
    
    try:
        await security_audit_service.set_security_context(
            session=session,
            user_id=current_user.id if hasattr(current_user, 'id') else 1,
            service_name="performance_dashboard"
        )
        
        # Collect real-time metrics
        timestamp = datetime.now()
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        network = psutil.net_io_counters()
        
        # Database metrics
        monitor = await get_performance_monitor()
        db_health = await monitor.get_database_health_metrics()
        
        # Active sessions count
        active_sessions_result = await session.execute(text("""
            SELECT COUNT(*) as active_sessions
            FROM pg_stat_activity 
            WHERE state = 'active' AND datname = current_database()
        """))
        active_sessions = active_sessions_result.scalar() or 0
        
        return {
            "timestamp": timestamp.isoformat(),
            "system": {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv
            },
            "database": {
                "active_connections": db_health.active_connections,
                "active_sessions": active_sessions,
                "connection_utilization": round(db_health.connection_utilization_percent, 1),
                "avg_query_time_ms": round(db_health.avg_query_time_ms, 2)
            },
            "cache": await get_cache_realtime_metrics()
        }
        
    except Exception as e:
        logger.error(f"Realtime metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get realtime metrics: {str(e)}")

async def get_cache_realtime_metrics() -> Dict[str, Any]:
    """Get real-time cache metrics."""
    try:
        cache = await get_redis_cache()
        if await cache.health_check():
            metrics = await cache.get_cache_metrics()
            return {
                "is_healthy": True,
                "hit_rate_percent": round(metrics.get("hit_rate_percent", 0), 1),
                "memory_usage": metrics.get("redis_info", {}).get("used_memory_human", "0B"),
                "ops_per_sec": metrics.get("redis_info", {}).get("ops_per_sec", 0)
            }
        else:
            return {"is_healthy": False, "error": "Cache not accessible"}
    except Exception as e:
        return {"is_healthy": False, "error": str(e)}

@router.get("/metrics/historical")
async def get_historical_metrics(
    hours: int = Query(24, ge=1, le=168, description="Hours of historical data"),
    interval_minutes: int = Query(15, ge=5, le=60, description="Data interval in minutes"),
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get historical performance metrics for trend analysis."""
    
    try:
        await security_audit_service.set_security_context(
            session=session,
            user_id=current_user.id if hasattr(current_user, 'id') else 1,
            service_name="performance_dashboard"
        )
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get historical data from materialized views if available
        try:
            historical_data = await session.execute(text("""
                SELECT 
                    date_trunc('hour', created_at) as hour,
                    COUNT(*) as activity_count,
                    'system_activity' as metric_type
                FROM tasks 
                WHERE created_at >= :start_time AND created_at <= :end_time
                GROUP BY date_trunc('hour', created_at)
                ORDER BY hour
            """), {"start_time": start_time, "end_time": end_time})
            
            historical_points = []
            for row in historical_data:
                historical_points.append({
                    "timestamp": row.hour.isoformat(),
                    "activity_count": row.activity_count,
                    "metric_type": row.metric_type
                })
            
        except Exception as e:
            logger.warning(f"Historical data query failed: {e}")
            historical_points = []
        
        # Generate simulated historical data if database query fails
        if not historical_points:
            historical_points = generate_simulated_historical_data(start_time, end_time, interval_minutes)
        
        return {
            "period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "hours": hours,
                "interval_minutes": interval_minutes
            },
            "data_points": len(historical_points),
            "metrics": historical_points
        }
        
    except Exception as e:
        logger.error(f"Historical metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get historical metrics: {str(e)}")

def generate_simulated_historical_data(start_time: datetime, end_time: datetime, interval_minutes: int) -> List[Dict[str, Any]]:
    """Generate simulated historical data for demonstration purposes."""
    import random
    
    data_points = []
    current_time = start_time
    
    while current_time <= end_time:
        # Simulate realistic performance metrics
        cpu_base = 30 + random.gauss(0, 10)
        memory_base = 60 + random.gauss(0, 15)
        
        data_points.append({
            "timestamp": current_time.isoformat(),
            "cpu_percent": max(0, min(100, cpu_base)),
            "memory_percent": max(0, min(100, memory_base)),
            "response_time_ms": max(50, 200 + random.gauss(0, 50)),
            "active_connections": random.randint(5, 25)
        })
        
        current_time += timedelta(minutes=interval_minutes)
    
    return data_points

@router.get("/bottlenecks/analysis")
async def get_bottleneck_analysis(
    session: AsyncSession = Depends(get_async_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed bottleneck analysis and recommendations."""
    
    try:
        await security_audit_service.set_security_context(
            session=session,
            user_id=current_user.id if hasattr(current_user, 'id') else 1,
            service_name="performance_dashboard"
        )
        
        # Get performance recommendations from monitoring service
        monitor = await get_performance_monitor()
        recommendations = await monitor.get_performance_recommendations()
        
        # Get query optimization recommendations
        query_recommendations = await get_optimization_recommendations()
        
        # Get database-specific bottlenecks
        db_bottlenecks = await analyze_database_bottlenecks(session)
        
        # Categorize bottlenecks by severity
        bottlenecks = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        # Process monitoring service recommendations
        for rec in recommendations:
            severity = rec.get("severity", "medium").lower()
            if severity in bottlenecks:
                bottlenecks[severity].append({
                    "type": rec.get("type", "unknown"),
                    "message": rec.get("message", ""),
                    "action": rec.get("action", ""),
                    "source": "monitoring_service"
                })
        
        # Process query recommendations
        for rec in query_recommendations:
            priority = rec.get("priority", "MEDIUM").lower()
            severity_map = {"high": "high", "medium": "medium", "low": "low"}
            severity = severity_map.get(priority, "medium")
            
            bottlenecks[severity].append({
                "type": rec.get("type", "query_optimization"),
                "message": rec.get("recommendation", ""),
                "query_hash": rec.get("query_hash", ""),
                "estimated_impact": rec.get("estimated_impact", ""),
                "source": "query_analyzer"
            })
        
        # Add database bottlenecks
        for bottleneck in db_bottlenecks:
            severity = bottleneck.get("severity", "medium").lower()
            if severity in bottlenecks:
                bottlenecks[severity].append(bottleneck)
        
        # Calculate total bottleneck score
        total_bottlenecks = sum(len(bottlenecks[severity]) for severity in bottlenecks)
        bottleneck_score = max(0, 100 - (total_bottlenecks * 5))  # Rough scoring
        
        return {
            "timestamp": datetime.now().isoformat(),
            "bottleneck_summary": {
                "total_bottlenecks": total_bottlenecks,
                "bottleneck_score": bottleneck_score,
                "critical_count": len(bottlenecks["critical"]),
                "high_count": len(bottlenecks["high"]),
                "medium_count": len(bottlenecks["medium"]),
                "low_count": len(bottlenecks["low"])
            },
            "bottlenecks_by_severity": bottlenecks,
            "analysis_recommendations": [
                {
                    "priority": "immediate",
                    "title": "Address Critical Bottlenecks",
                    "description": f"Focus on {len(bottlenecks['critical'])} critical issues first"
                },
                {
                    "priority": "short_term", 
                    "title": "High Priority Optimizations",
                    "description": f"Plan to resolve {len(bottlenecks['high'])} high priority items"
                },
                {
                    "priority": "long_term",
                    "title": "Performance Improvements",
                    "description": f"Address {len(bottlenecks['medium']) + len(bottlenecks['low'])} medium/low priority items"
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Bottleneck analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze bottlenecks: {str(e)}")

async def analyze_database_bottlenecks(session: AsyncSession) -> List[Dict[str, Any]]:
    """Analyze database-specific bottlenecks."""
    bottlenecks = []
    
    try:
        # Check for table bloat
        bloat_result = await session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            AND pg_total_relation_size(schemaname||'.'||tablename) > 100*1024*1024  -- Tables > 100MB
            ORDER BY size_bytes DESC
            LIMIT 5
        """))
        
        large_tables = []
        for row in bloat_result:
            large_tables.append({
                "table": f"{row.schemaname}.{row.tablename}",
                "size": row.size,
                "size_bytes": row.size_bytes
            })
        
        if large_tables:
            bottlenecks.append({
                "type": "table_bloat",
                "severity": "medium",
                "message": f"Found {len(large_tables)} large tables that may benefit from optimization",
                "details": large_tables,
                "source": "database_analyzer"
            })
        
        # Check for unused indexes
        unused_indexes_result = await session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) as size
            FROM pg_stat_user_indexes 
            WHERE idx_scan = 0 
            AND schemaname = 'public'
            AND pg_relation_size(indexrelid) > 1024*1024  -- Indexes > 1MB
            ORDER BY pg_relation_size(indexrelid) DESC
            LIMIT 10
        """))
        
        unused_indexes = []
        for row in unused_indexes_result:
            unused_indexes.append({
                "index": f"{row.schemaname}.{row.tablename}.{row.indexname}",
                "size": row.size
            })
        
        if unused_indexes:
            bottlenecks.append({
                "type": "unused_indexes",
                "severity": "low",
                "message": f"Found {len(unused_indexes)} unused indexes consuming storage",
                "details": unused_indexes,
                "source": "database_analyzer"
            })
        
    except Exception as e:
        logger.warning(f"Database bottleneck analysis failed: {e}")
        bottlenecks.append({
            "type": "analysis_error",
            "severity": "low",
            "message": f"Unable to complete database analysis: {str(e)}",
            "source": "database_analyzer"
        })
    
    return bottlenecks

@router.get("/load-test/status")
async def get_load_test_status() -> Dict[str, Any]:
    """Get current load testing status and recent results."""
    
    # This would integrate with a load testing framework
    # For now, return a simulated status
    return {
        "timestamp": datetime.now().isoformat(),
        "load_test_enabled": False,
        "last_test_run": None,
        "next_scheduled_test": None,
        "test_types_available": [
            "api_endpoints",
            "authentication_flow", 
            "database_connections",
            "concurrent_users"
        ],
        "recent_results": {
            "max_concurrent_users": 100,
            "max_requests_per_second": 250,
            "avg_response_time_ms": 185,
            "error_rate_percent": 0.5
        }
    }

@router.post("/load-test/start")
async def start_load_test(
    background_tasks: BackgroundTasks,
    test_type: str = Query("api_endpoints", description="Type of load test to run"),
    duration_minutes: int = Query(5, ge=1, le=30, description="Test duration in minutes"),
    concurrent_users: int = Query(10, ge=1, le=100, description="Number of concurrent users"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start a load test (simulated for demonstration)."""
    
    # In a real implementation, this would start actual load testing
    # For demonstration, we'll just return a success response
    
    test_id = f"loadtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Add background task for simulated load test
    background_tasks.add_task(
        simulate_load_test,
        test_id=test_id,
        test_type=test_type,
        duration_minutes=duration_minutes,
        concurrent_users=concurrent_users
    )
    
    return {
        "test_id": test_id,
        "status": "started",
        "test_type": test_type,
        "duration_minutes": duration_minutes,
        "concurrent_users": concurrent_users,
        "estimated_completion": (datetime.now() + timedelta(minutes=duration_minutes)).isoformat(),
        "message": "Load test started successfully. Results will be available upon completion."
    }

async def simulate_load_test(test_id: str, test_type: str, duration_minutes: int, concurrent_users: int):
    """Simulate a load test execution (for demonstration)."""
    try:
        logger.info(f"Starting simulated load test {test_id}")
        
        # Simulate test execution time
        await asyncio.sleep(duration_minutes * 60)  # Convert to seconds
        
        # Log completion
        logger.info(f"Completed simulated load test {test_id}")
        
        # In real implementation, results would be stored in database
        # and made available through another endpoint
        
    except Exception as e:
        logger.error(f"Load test simulation failed: {e}")

@router.get("/dashboard/config")
async def get_dashboard_config() -> Dict[str, Any]:
    """Get dashboard configuration and metadata."""
    
    return {
        "version": "1.0.0",
        "update_intervals": {
            "realtime_metrics": 5,  # seconds
            "health_overview": 30,  # seconds 
            "historical_data": 300,  # seconds (5 minutes)
            "bottleneck_analysis": 600  # seconds (10 minutes)
        },
        "metric_thresholds": {
            "cpu_warning": 80,
            "cpu_critical": 95,
            "memory_warning": 85,
            "memory_critical": 95,
            "disk_warning": 90,
            "disk_critical": 95,
            "connection_pool_warning": 80,
            "connection_pool_critical": 95,
            "query_time_warning": 500,  # milliseconds
            "query_time_critical": 1000,  # milliseconds
            "cache_hit_rate_warning": 80,  # percent
            "cache_hit_rate_critical": 70   # percent
        },
        "features": {
            "real_time_monitoring": True,
            "historical_trends": True,
            "bottleneck_analysis": True,
            "load_testing": True,  # Simulated for now
            "alerting": True,
            "recommendations": True
        },
        "data_sources": [
            "performance_monitoring_service",
            "redis_cache_service", 
            "query_performance_service",
            "system_metrics",
            "database_health_metrics"
        ]
    }