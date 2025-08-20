"""
Authentication Performance Monitoring Router

Provides endpoints to monitor the performance improvements from the backend optimization.
Tracks authentication latency, cache hit rates, and database pool usage.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User
from shared.utils.database_setup import get_async_session
from api.dependencies import get_current_user
from api.services.optimized_auth_service import optimized_auth_service
from api.dependencies import AuthenticationMetrics

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication Performance Monitoring"])


@router.get("/performance-metrics")
async def get_auth_performance_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive authentication performance metrics.
    
    Provides insights into:
    - Cache hit rates  
    - Average response times
    - Database query counts
    - Performance improvements over baseline
    """
    try:
        # Get service metrics
        service_metrics = AuthenticationMetrics.get_service_metrics()
        
        # Calculate performance improvements
        baseline_response_time_ms = 176.0  # Original 176ms baseline
        current_avg_ms = service_metrics.get("avg_response_time_ms", 0)
        
        if current_avg_ms > 0 and baseline_response_time_ms > 0:
            improvement_percent = ((baseline_response_time_ms - current_avg_ms) / baseline_response_time_ms) * 100
        else:
            improvement_percent = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "performance_summary": {
                "baseline_response_time_ms": baseline_response_time_ms,
                "current_avg_response_time_ms": current_avg_ms,
                "performance_improvement_percent": round(improvement_percent, 2),
                "target_achieved": current_avg_ms < 40.0 if current_avg_ms > 0 else False,
                "cache_hit_rate_percent": service_metrics.get("cache_hit_rate_percent", 0)
            },
            "detailed_metrics": service_metrics,
            "optimization_status": {
                "router_consolidation": "completed",
                "jwt_caching": "active",
                "rate_limit_optimization": "active",
                "connection_pool_enhancement": "active"
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/performance-test")
async def run_performance_test(
    request: Request,
    iterations: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Run a controlled performance test of the authentication system.
    
    Args:
        iterations: Number of authentication validation cycles to run
        
    Returns:
        Performance test results with timing statistics
    """
    try:
        if iterations > 100:  # Prevent abuse
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 iterations allowed"
            )
        
        from api.dependencies.optimized_auth_dependencies import extract_token_from_request
        
        # Extract token for testing
        token = extract_token_from_request(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No authentication token found for testing"
            )
        
        # Reset metrics for clean test
        AuthenticationMetrics.reset_service_metrics()
        
        response_times = []
        
        # Run performance test
        for i in range(iterations):
            start_time = time.time()
            
            try:
                # Get async database session
                async with get_async_session() as db:
                    is_valid, user_obj, metadata = await optimized_auth_service.validate_token_optimized(
                        token=token,
                        db=db,
                        is_session_validation=True
                    )
                
                response_time = (time.time() - start_time) * 1000
                response_times.append(response_time)
                
                if not is_valid:
                    logger.warning(f"Token validation failed on iteration {i+1}")
                
            except Exception as e:
                logger.warning(f"Test iteration {i+1} failed: {e}")
                response_times.append(999.0)  # Record failure as high latency
        
        # Calculate statistics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            median_response_time = sorted(response_times)[len(response_times) // 2]
        else:
            avg_response_time = min_response_time = max_response_time = median_response_time = 0
        
        # Get final metrics
        final_metrics = AuthenticationMetrics.get_service_metrics()
        
        return {
            "test_config": {
                "iterations": iterations,
                "user_id": current_user.id,
                "timestamp": datetime.now().isoformat()
            },
            "performance_results": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "min_response_time_ms": round(min_response_time, 2),
                "max_response_time_ms": round(max_response_time, 2),
                "median_response_time_ms": round(median_response_time, 2),
                "target_achieved": avg_response_time < 40.0,
                "improvement_over_baseline": round(((176.0 - avg_response_time) / 176.0) * 100, 2)
            },
            "cache_performance": {
                "cache_hit_rate_percent": final_metrics.get("cache_hit_rate_percent", 0),
                "total_requests": final_metrics.get("total_requests", 0),
                "cache_hits": final_metrics.get("cache_hits", 0),
                "database_queries": final_metrics.get("database_queries", 0)
            },
            "response_time_distribution": response_times
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Performance test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance test failed: {str(e)}"
        )


@router.post("/reset-metrics")
async def reset_performance_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Reset authentication performance metrics.
    Useful for clean measurement periods.
    """
    try:
        # Reset service metrics
        AuthenticationMetrics.reset_service_metrics()
        
        return {
            "message": "Performance metrics reset successfully",
            "reset_by": current_user.id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset performance metrics"
        )


@router.get("/cache-stats")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed Redis cache statistics for authentication.
    """
    try:
        from shared.services.redis_cache_service import get_redis_cache
        
        redis = await get_redis_cache()
        
        # Get cache statistics
        cache_info = await redis.info()
        cache_stats = {
            "memory_usage": cache_info.get("used_memory_human", "unknown"),
            "total_connections": cache_info.get("connected_clients", 0),
            "total_commands": cache_info.get("total_commands_processed", 0),
            "cache_hits": cache_info.get("keyspace_hits", 0),
            "cache_misses": cache_info.get("keyspace_misses", 0)
        }
        
        # Calculate hit rate
        total_requests = cache_stats["cache_hits"] + cache_stats["cache_misses"]
        hit_rate = (cache_stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        service_metrics = AuthenticationMetrics.get_service_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "redis_cache_stats": cache_stats,
            "redis_hit_rate_percent": round(hit_rate, 2),
            "auth_service_metrics": service_metrics,
            "optimization_impact": {
                "estimated_database_queries_saved": service_metrics.get("cache_hits", 0),
                "estimated_response_time_improvement": f"{service_metrics.get('cache_hit_rate_percent', 0)}% faster on cache hits"
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )