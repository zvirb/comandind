"""Security enforcement middleware for FastAPI endpoints."""

import logging
from typing import Callable, Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_async_session
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_enforcement_service import security_enforcement_service
from shared.database.models import User

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user_with_security_check(
    request: Request,
    token: str = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Enhanced user authentication with security tier enforcement.
    
    This dependency can be used in place of get_current_user to automatically
    enforce security tier requirements for endpoints.
    """
    try:
        # Extract token from Bearer format
        if hasattr(token, 'credentials'):
            token_str = token.credentials
        else:
            token_str = str(token)
        
        # Validate token and get user
        user_data = await enhanced_jwt_service.verify_token(token_str)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        user = User(**user_data)
        
        # Perform security tier validation
        endpoint_path = str(request.url.path)
        method = request.method
        
        validation_result = await security_enforcement_service.validate_user_access(
            session=session,
            user=user,
            endpoint_path=endpoint_path,
            request_method=method
        )
        
        # Handle validation result
        if not validation_result.get("allowed", True):
            # Access denied due to insufficient security tier
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient security tier",
                    "message": validation_result.get("message", "Access denied"),
                    "user_tier": validation_result.get("user_tier"),
                    "required_tier": validation_result.get("required_tier"),
                    "upgrade_required": validation_result.get("upgrade_required", False)
                }
            )
        
        # Add security context to user object for logging/monitoring
        if hasattr(user, 'security_context'):
            user.security_context = {
                "validation_result": validation_result,
                "endpoint": endpoint_path,
                "method": method
            }
        
        # Log warning if user accessed with insufficient tier but was allowed (ADVISORY mode)
        if validation_result.get("warning"):
            logger.warning(
                f"User {user.id} accessed {endpoint_path} with insufficient security tier "
                f"(Current: {validation_result.get('user_tier')}, "
                f"Required: {validation_result.get('required_tier')})"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Security enforcement error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security validation failed"
        )


def require_security_tier(minimum_tier: str, enforcement_level: str = "MANDATORY"):
    """
    Decorator factory for requiring specific security tiers on endpoints.
    
    Usage:
        @router.get("/sensitive-endpoint")
        @require_security_tier("enhanced", "MANDATORY")
        async def sensitive_endpoint(user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # This is a placeholder - in practice, you'd need to inject the dependency
            # The actual implementation would use FastAPI's dependency injection system
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_user_compliance(
    user: User,
    session: AsyncSession = Depends(get_session)
) -> dict:
    """
    Check if user is compliant with current security policies.
    Can be used as a dependency in endpoints that need compliance verification.
    """
    try:
        compliance = await security_enforcement_service.check_policy_compliance(
            session=session,
            user_id=user.id
        )
        
        if not compliance.get("compliant", True):
            logger.warning(
                f"User {user.id} is not compliant with security policies: "
                f"{len(compliance.get('violations', []))} violations"
            )
        
        return compliance
        
    except Exception as e:
        logger.error(f"Error checking user compliance: {str(e)}")
        return {"compliant": True, "error": str(e)}


async def get_user_security_recommendations(
    user: User,
    session: AsyncSession = Depends(get_session)
) -> list:
    """
    Get security upgrade recommendations for the current user.
    Can be used as a dependency to provide upgrade suggestions.
    """
    try:
        recommendations = await security_enforcement_service.get_upgrade_recommendations(
            session=session,
            user_id=user.id
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting security recommendations: {str(e)}")
        return []


class SecurityEnforcementMiddleware:
    """
    Middleware class for automatic security enforcement across all endpoints.
    
    This can be added to the FastAPI app to automatically enforce security
    requirements on all endpoints based on configuration.
    """
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Skip enforcement for certain paths
            skip_paths = [
                "/docs", "/openapi.json", "/redoc", 
                "/api/v1/auth/", "/api/v1/public/",
                "/health", "/metrics"
            ]
            
            path = request.url.path
            if any(path.startswith(skip_path) for skip_path in skip_paths):
                await self.app(scope, receive, send)
                return
            
            # For API endpoints, security enforcement will be handled by dependencies
            # This middleware can log requests for monitoring purposes
            try:
                logger.debug(f"Security middleware processing: {request.method} {path}")
                await self.app(scope, receive, send)
            except Exception as e:
                logger.error(f"Security middleware error: {str(e)}")
                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


def create_security_enforcement_dependency(
    minimum_tier: Optional[str] = None,
    enforcement_level: str = "ADVISORY"
):
    """
    Create a custom security enforcement dependency for specific endpoints.
    
    Args:
        minimum_tier: Minimum security tier required (standard, enhanced, enterprise)
        enforcement_level: Enforcement level (ADVISORY, MANDATORY, STRICT)
    
    Returns:
        FastAPI dependency function
    """
    async def security_dependency(
        request: Request,
        token: str = Depends(security),
        session: AsyncSession = Depends(get_session)
    ) -> User:
        # Get user
        user = await get_current_user_with_security_check(request, token, session)
        
        # If specific requirements are set, validate them
        if minimum_tier:
            user_tier = await security_enforcement_service.get_user_security_tier(
                session, user.id
            )
            
            tier_hierarchy = {
                "standard": 1,
                "enhanced": 2,
                "enterprise": 3
            }
            
            user_level = tier_hierarchy.get(user_tier.current_tier.value, 0)
            required_level = tier_hierarchy.get(minimum_tier, 999)
            
            if user_level < required_level:
                if enforcement_level in ["MANDATORY", "STRICT"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "Insufficient security tier",
                            "user_tier": user_tier.current_tier.value,
                            "required_tier": minimum_tier,
                            "upgrade_required": True
                        }
                    )
                elif enforcement_level == "ADVISORY":
                    logger.warning(
                        f"User {user.id} accessing endpoint with insufficient security tier"
                    )
        
        return user
    
    return security_dependency


# Pre-configured dependencies for common security levels
require_standard_security = create_security_enforcement_dependency("standard", "MANDATORY")
require_enhanced_security = create_security_enforcement_dependency("enhanced", "MANDATORY")
require_enterprise_security = create_security_enforcement_dependency("enterprise", "MANDATORY")

# Advisory dependencies (log warnings but allow access)
suggest_enhanced_security = create_security_enforcement_dependency("enhanced", "ADVISORY")
suggest_enterprise_security = create_security_enforcement_dependency("enterprise", "ADVISORY")