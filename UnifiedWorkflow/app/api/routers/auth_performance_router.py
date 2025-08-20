"""
Authentication Performance Monitoring Router

Provides endpoints to monitor the performance impact of authentication
optimizations including caching, rate limiting, and deduplication.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from api.dependencies import get_current_user
from shared.database.models import User
from shared.services.redis_cache_service import get_redis_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth-performance", tags=["Authentication Performance"])


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_auth_performance_metrics(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive authentication performance metrics.
    
    Includes cache hit rates, rate limiting stats, and deduplication metrics.
    """
    try:
        metrics_data = {
            "timestamp": datetime.now().isoformat(),
            "redis_cache": {},
            "auth_rate_limiting": {},
            "auth_deduplication": {},
            "middleware_performance": {}
        }
        
        # Get Redis cache metrics
        try:
            redis_cache = await get_redis_cache()
            cache_metrics = await redis_cache.get_cache_metrics()
            metrics_data["redis_cache"] = cache_metrics
        except Exception as e:
            logger.warning(f"Failed to get Redis cache metrics: {e}")
            metrics_data["redis_cache"] = {"error": str(e)}
        
        # Get auth rate limiting metrics
        try:
            # Access the middleware instance from the app
            if hasattr(request.app, 'user_data'):
                for middleware in request.app.user_data.get('middleware_stack', []):
                    if hasattr(middleware, 'get_metrics'):
                        middleware_name = middleware.__class__.__name__
                        if 'AuthRateLimit' in middleware_name:
                            metrics_data["auth_rate_limiting"] = middleware.get_metrics()
                        elif 'AuthDeduplication' in middleware_name:
                            metrics_data["auth_deduplication"] = middleware.get_metrics()
        except Exception as e:
            logger.debug(f"Failed to get middleware metrics: {e}")
        
        # Calculate overall performance improvement
        redis_cache_metrics = metrics_data["redis_cache"]
        if isinstance(redis_cache_metrics, dict) and "hit_rate_percent" in redis_cache_metrics:
            hit_rate = redis_cache_metrics["hit_rate_percent"]
            
            # Estimate performance improvement
            estimated_db_load_reduction = hit_rate  # Direct correlation with cache hits
            estimated_response_time_improvement = hit_rate * 0.8  # Conservative estimate
            
            metrics_data["performance_summary"] = {
                "cache_hit_rate_percent": hit_rate,
                "estimated_db_load_reduction_percent": estimated_db_load_reduction,
                "estimated_response_time_improvement_percent": estimated_response_time_improvement,
                "status": "optimal" if hit_rate > 70 else "good" if hit_rate > 50 else "needs_improvement"
            }
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Error getting auth performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve performance metrics: {str(e)}"
        )


@router.get("/cache/status", status_code=status.HTTP_200_OK)
async def get_auth_cache_status(current_user: User = Depends(get_current_user)):
    """
    Get detailed authentication cache status.
    """
    try:
        redis_cache = await get_redis_cache()
        
        # Get general cache metrics
        cache_metrics = await redis_cache.get_cache_metrics()
        
        # Check cache health
        is_healthy = await redis_cache.health_check()
        
        return {
            "cache_healthy": is_healthy,
            "metrics": cache_metrics,
            "recommendations": _get_cache_recommendations(cache_metrics)
        }
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cache status: {str(e)}"
        )


@router.post("/cache/clear", status_code=status.HTTP_200_OK)
async def clear_auth_cache(current_user: User = Depends(get_current_user)):
    """
    Clear authentication cache (admin only).
    """
    # Check if user has admin role
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        redis_cache = await get_redis_cache()
        
        # Clear token validation cache
        token_pattern = "token_validation:*"
        token_cleared = await redis_cache.delete_pattern(token_pattern)
        
        # Clear session validation cache
        session_pattern = "session_validation:*"
        session_cleared = await redis_cache.delete_pattern(session_pattern)
        
        return {
            "success": True,
            "cleared_tokens": token_cleared,
            "cleared_sessions": session_cleared,
            "total_cleared": token_cleared + session_cleared,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing auth cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear auth cache: {str(e)}"
        )


@router.get("/rate-limits/status", status_code=status.HTTP_200_OK)
async def get_rate_limit_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's rate limit status for authentication endpoints.
    """
    try:
        # This would typically require access to the middleware instance
        # For now, return the configured limits
        return {
            "user_id": current_user.id,
            "limits": {
                "session_validation": {
                    "limit": 100,
                    "period": "1 minute",
                    "description": "Very permissive to prevent frontend loops"
                },
                "general_auth": {
                    "limit": 30,
                    "period": "1 minute",
                    "description": "Standard auth operations"
                },
                "login_attempts": {
                    "limit": 10,
                    "period": "10 minutes",
                    "description": "Login and registration attempts"
                },
                "token_refresh": {
                    "limit": 20,
                    "period": "5 minutes",
                    "description": "Token refresh operations"
                }
            },
            "recommendations": [
                "Session validation has very high limits to prevent infinite loops",
                "Login attempts are limited to prevent brute force attacks",
                "Token refresh has moderate limits for security balance"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rate limit status: {str(e)}"
        )


@router.get("/deduplication/status", status_code=status.HTTP_200_OK)
async def get_deduplication_status(current_user: User = Depends(get_current_user)):
    """
    Get authentication request deduplication status.
    """
    try:
        return {
            "deduplication_enabled": True,
            "windows": {
                "session_validation": "3 seconds",
                "general_auth": "10 seconds",
                "description": "Shorter window for session validation due to higher frequency"
            },
            "concurrent_request_limit": 2,
            "benefits": [
                "Prevents duplicate authentication requests",
                "Reduces database load from repeated calls",
                "Caches successful responses for faster subsequent requests",
                "Helps prevent infinite loops in frontend applications"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting deduplication status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve deduplication status: {str(e)}"
        )


def _get_cache_recommendations(cache_metrics: Dict[str, Any]) -> list:
    """Generate cache performance recommendations."""
    recommendations = []
    
    if isinstance(cache_metrics, dict):
        hit_rate = cache_metrics.get("hit_rate_percent", 0)
        
        if hit_rate < 50:
            recommendations.append("Cache hit rate is low. Consider increasing cache TTL values.")
        elif hit_rate > 90:
            recommendations.append("Excellent cache hit rate. Current configuration is optimal.")
        else:
            recommendations.append("Good cache hit rate. Monitor for continued performance.")
        
        if cache_metrics.get("cache_metrics", {}).get("errors", 0) > 0:
            recommendations.append("Cache errors detected. Check Redis connection health.")
        
        if not cache_metrics.get("is_healthy", True):
            recommendations.append("Cache health check failed. Verify Redis connectivity.")
    
    return recommendations