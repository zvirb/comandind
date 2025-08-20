"""
Performance Monitoring API Endpoints

Provides real-time database performance metrics, query analytics,
and optimization recommendations for system administrators and monitoring tools.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from shared.utils.database_setup import get_session
from shared.services.performance_monitoring_service import get_performance_monitor
from shared.services.redis_cache_service import get_redis_cache
from shared.services.security_audit_service import security_audit_service

router = APIRouter(prefix="/performance", tags=["Performance Monitoring"])

@router.get("/health")
async def get_system_health(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get comprehensive system health metrics."""
    
    try:
        # Set security context for audit logging
        await security_audit_service.set_security_context(
            session=session, 
            user_id=1,  # System user for monitoring
            service_name="performance_api"
        )
        
        monitor = await get_performance_monitor()
        health_metrics = await monitor.get_database_health_metrics()
        
        # Get Redis cache metrics
        cache_metrics = {}
        try:
            redis_cache = await get_redis_cache()
            cache_metrics = await redis_cache.get_cache_metrics()
        except Exception as e:
            cache_metrics = {"error": str(e), "available": False}
        
        # Calculate overall health score
        health_score = calculate_health_score(health_metrics)
        
        return {
            "status": "healthy" if health_score > 70 else "degraded" if health_score > 40 else "unhealthy",
            "health_score": health_score,
            "timestamp": datetime.now().isoformat(),
            "database": {
                "connections": {
                    "active": health_metrics.active_connections,
                    "idle": health_metrics.idle_connections,
                    "max": health_metrics.max_connections,
                    "utilization_percent": health_metrics.connection_utilization_percent
                },
                "performance": {
                    "slow_queries_count": health_metrics.slow_queries_count,
                    "avg_query_time_ms": health_metrics.avg_query_time_ms,
                    "queries_per_second": health_metrics.queries_per_second
                },
                "storage": {
                    "database_size_mb": health_metrics.database_size_mb,
                    "largest_tables": health_metrics.largest_tables[:5]
                }
            },
            "system": {
                "cpu_usage_percent": health_metrics.cpu_usage_percent,
                "memory_usage_mb": health_metrics.memory_usage_mb,
                "disk_usage_percent": health_metrics.disk_usage_percent
            },
            "cache": cache_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system health: {str(e)}")

def calculate_health_score(metrics) -> int:
    """Calculate overall system health score (0-100)."""
    score = 100
    
    # Connection utilization penalty
    if metrics.connection_utilization_percent > 90:
        score -= 30
    elif metrics.connection_utilization_percent > 80:
        score -= 15
    elif metrics.connection_utilization_percent > 70:
        score -= 5
    
    # Query performance penalty
    if metrics.avg_query_time_ms > 1000:
        score -= 20
    elif metrics.avg_query_time_ms > 500:
        score -= 10
    elif metrics.avg_query_time_ms > 200:
        score -= 5
    
    # System resource penalties
    if metrics.cpu_usage_percent > 90:
        score -= 20
    elif metrics.cpu_usage_percent > 80:
        score -= 10
    
    if metrics.disk_usage_percent > 90:
        score -= 20
    elif metrics.disk_usage_percent > 85:
        score -= 10
    
    # Cache performance bonus/penalty
    if metrics.cache_hit_rate_percent > 90:
        score += 5
    elif metrics.cache_hit_rate_percent < 70:
        score -= 10
    
    return max(0, min(100, score))

@router.get("/metrics/database")
async def get_database_metrics(
    include_tables: bool = Query(False, description="Include table size metrics"),
    include_indexes: bool = Query(False, description="Include index usage metrics"),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get detailed database performance metrics."""
    
    try:
        await security_audit_service.set_security_context(
            session=session, user_id=1, service_name="performance_api"
        )
        
        monitor = await get_performance_monitor()
        metrics = await monitor.get_database_health_metrics()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "connections": {
                "active": metrics.active_connections,
                "idle": metrics.idle_connections,
                "max_connections": metrics.max_connections,
                "utilization_percent": round(metrics.connection_utilization_percent, 2)
            },
            "query_performance": {
                "slow_queries_count": metrics.slow_queries_count,
                "avg_query_time_ms": round(metrics.avg_query_time_ms, 2),
                "queries_per_second": round(metrics.queries_per_second, 2)
            },
            "database_size": {
                "total_size_mb": round(metrics.database_size_mb, 2)
            }
        }
        
        if include_tables:
            response["largest_tables"] = metrics.largest_tables
        
        if include_indexes:
            response["index_analysis"] = {
                "unused_indexes": metrics.unused_indexes,
                "missing_indexes_suggestions": metrics.missing_indexes
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving database metrics: {str(e)}")

@router.get("/metrics/queries")
async def get_query_metrics(
    limit: int = Query(20, ge=1, le=100, description="Number of queries to return"),
    sort_by: str = Query("avg_time", regex="^(avg_time|execution_count|total_time)$")
) -> Dict[str, Any]:
    """Get query performance analytics."""
    
    try:
        monitor = await get_performance_monitor()
        query_report = await monitor.get_query_performance_report()
        
        if "message" in query_report:
            return {"message": query_report["message"], "queries": []}
        
        # Sort and limit results based on parameters
        if sort_by == "avg_time":
            sorted_queries = query_report["slowest_queries"][:limit]
        elif sort_by == "execution_count":
            sorted_queries = query_report["most_executed_queries"][:limit]
        else:  # total_time
            sorted_queries = sorted(
                query_report.get("slowest_queries", []),
                key=lambda x: x.get("total_time_ms", 0),
                reverse=True
            )[:limit]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": query_report.get("performance_summary", {}),
            "query_count": query_report.get("total_unique_queries", 0),
            "slow_queries_count": query_report.get("slow_queries_count", 0),
            "queries": sorted_queries
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving query metrics: {str(e)}")

@router.get("/metrics/cache")
async def get_cache_metrics() -> Dict[str, Any]:
    """Get Redis cache performance metrics."""
    
    try:
        redis_cache = await get_redis_cache()
        metrics = await redis_cache.get_cache_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cache_performance": metrics.get("cache_metrics", {}),
            "hit_rate_percent": metrics.get("hit_rate_percent", 0),
            "health": {
                "is_healthy": metrics.get("is_healthy", False),
                "last_health_check": metrics.get("last_health_check")
            },
            "redis_info": metrics.get("redis_info", {})
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "cache_available": False
        }

@router.get("/metrics/materialized-views")
async def get_materialized_view_metrics(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get materialized view performance and refresh status."""
    
    try:
        await security_audit_service.set_security_context(
            session=session, user_id=1, service_name="performance_api"
        )
        
        # Get materialized view information
        result = await session.execute(text("""
            SELECT 
                schemaname,
                matviewname,
                matviewowner,
                hasindexes,
                ispopulated,
                definition
            FROM pg_matviews 
            WHERE schemaname = 'public'
            ORDER BY matviewname
        """))
        
        views = []
        for row in result:
            views.append({
                "name": row.matviewname,
                "schema": row.schemaname,
                "owner": row.matviewowner,
                "has_indexes": row.hasindexes,
                "is_populated": row.ispopulated
            })
        
        # Get last refresh timestamp from system settings
        refresh_result = await session.execute(text("""
            SELECT value, updated_at 
            FROM system_settings 
            WHERE key = 'last_dashboard_refresh'
        """))
        
        refresh_row = refresh_result.fetchone()
        last_refresh = None
        if refresh_row:
            try:
                last_refresh = datetime.fromtimestamp(float(refresh_row.value)).isoformat()
            except (ValueError, TypeError):
                last_refresh = None
        
        return {
            "timestamp": datetime.now().isoformat(),
            "materialized_views": views,
            "view_count": len(views),
            "last_refresh": last_refresh,
            "refresh_available": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving materialized view metrics: {str(e)}")

@router.post("/materialized-views/refresh")
async def refresh_materialized_views(
    view_name: Optional[str] = Query(None, description="Specific view to refresh, or all if not specified"),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Refresh materialized views manually."""
    
    try:
        await security_audit_service.set_security_context(
            session=session, user_id=1, service_name="performance_api"
        )
        
        if view_name:
            # Refresh specific view
            await session.execute(text(f"SELECT refresh_dashboard_view(:view_name)"), {"view_name": view_name})
            message = f"Materialized view '{view_name}' refreshed successfully"
        else:
            # Refresh all views
            await session.execute(text("SELECT refresh_dashboard_views()"))
            message = "All materialized views refreshed successfully"
        
        await session.commit()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "message": message
        }
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error refreshing materialized views: {str(e)}")

@router.get("/recommendations")
async def get_performance_recommendations() -> Dict[str, Any]:
    """Get AI-generated performance optimization recommendations."""
    
    try:
        monitor = await get_performance_monitor()
        recommendations = await monitor.get_performance_recommendations()
        
        # Group recommendations by severity
        grouped_recommendations = {
            "high": [r for r in recommendations if r.get("severity") == "high"],
            "medium": [r for r in recommendations if r.get("severity") == "medium"],
            "low": [r for r in recommendations if r.get("severity") == "low"]
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_recommendations": len(recommendations),
            "severity_breakdown": {
                "high": len(grouped_recommendations["high"]),
                "medium": len(grouped_recommendations["medium"]),
                "low": len(grouped_recommendations["low"])
            },
            "recommendations": grouped_recommendations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")

@router.get("/dashboard")
async def get_performance_dashboard(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get comprehensive performance dashboard data."""
    
    try:
        await security_audit_service.set_security_context(
            session=session, user_id=1, service_name="performance_api"
        )
        
        # Get data from materialized views for fast dashboard loading
        dashboard_data = {}
        
        # System performance summary
        result = await session.execute(text("SELECT * FROM system_performance_summary"))
        perf_row = result.fetchone()
        if perf_row:
            dashboard_data["system_summary"] = dict(perf_row._mapping)
        
        # Recent activity trends (last 7 days)
        result = await session.execute(text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count,
                'tasks' as type
            FROM tasks 
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            
            UNION ALL
            
            SELECT 
                DATE(started_at) as date,
                COUNT(*) as count,
                'chat_sessions' as type
            FROM chat_session_summaries
            WHERE started_at >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(started_at)
            
            ORDER BY date DESC
        """))
        
        activity_trends = {}
        for row in result:
            date_str = row.date.isoformat()
            if date_str not in activity_trends:
                activity_trends[date_str] = {}
            activity_trends[date_str][row.type] = row.count
        
        dashboard_data["activity_trends"] = activity_trends
        
        # Get current health metrics
        monitor = await get_performance_monitor()
        health_metrics = await monitor.get_database_health_metrics()
        
        dashboard_data["current_health"] = {
            "connection_utilization": health_metrics.connection_utilization_percent,
            "avg_query_time": health_metrics.avg_query_time_ms,
            "cache_hit_rate": health_metrics.cache_hit_rate_percent,
            "cpu_usage": health_metrics.cpu_usage_percent,
            "disk_usage": health_metrics.disk_usage_percent
        }
        
        # Get recent recommendations
        recommendations = await monitor.get_performance_recommendations()
        dashboard_data["urgent_recommendations"] = [
            r for r in recommendations if r.get("severity") == "high"
        ][:3]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "dashboard_data": dashboard_data,
            "data_freshness": "real-time"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading performance dashboard: {str(e)}")

@router.post("/monitoring/reset")
async def reset_monitoring_metrics() -> Dict[str, Any]:
    """Reset performance monitoring metrics."""
    
    try:
        monitor = await get_performance_monitor()
        monitor.reset_metrics()
        
        # Also reset Redis cache metrics if available
        try:
            redis_cache = await get_redis_cache()
            await redis_cache.reset_metrics()
        except Exception:
            pass  # Redis not available
        
        return {
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "message": "Performance monitoring metrics reset successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting monitoring metrics: {str(e)}")

@router.get("/status")
async def get_monitoring_status() -> Dict[str, Any]:
    """Get performance monitoring service status."""
    
    try:
        monitor = await get_performance_monitor()
        
        # Check Redis availability
        redis_available = False
        try:
            redis_cache = await get_redis_cache()
            redis_available = await redis_cache.health_check()
        except Exception:
            pass
        
        return {
            "timestamp": datetime.now().isoformat(),
            "monitoring_enabled": monitor.monitoring_enabled,
            "redis_cache_available": redis_available,
            "slow_query_threshold_ms": monitor.slow_query_threshold_ms,
            "tracked_queries": len(monitor.query_metrics),
            "service_health": "operational"
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "service_health": "degraded",
            "error": str(e)
        }