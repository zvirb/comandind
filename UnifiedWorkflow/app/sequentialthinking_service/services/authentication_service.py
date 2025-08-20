"""
Authentication service for Sequential Thinking Service
"""

import logging
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthenticationService:
    """
    Service for JWT token validation and user authentication
    """
    
    def __init__(self):
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.jwt_algorithm = settings.JWT_ALGORITHM
        
        if not self.jwt_secret:
            logger.warning("JWT_SECRET_KEY not configured - authentication will fail")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return user information
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict with user information
            
        Raises:
            ValueError: If token is invalid or expired
        """
        if not self.jwt_secret:
            raise ValueError("JWT secret key not configured")
        
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                raise ValueError("Token has expired")
            
            # Extract user information
            user_info = {
                "user_id": payload.get("sub") or payload.get("user_id"),
                "username": payload.get("username"),
                "email": payload.get("email"), 
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "token_type": payload.get("token_type", "access"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp")
            }
            
            # Validate required fields
            if not user_info["user_id"]:
                raise ValueError("Token missing user identifier")
            
            logger.debug(f"Successfully validated token for user {user_info['user_id']}")
            return user_info
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise ValueError(f"Token validation failed: {str(e)}")
    
    async def check_reasoning_permissions(self, user_info: Dict[str, Any]) -> bool:
        """
        Check if user has permissions for reasoning operations
        
        Args:
            user_info: User information from validated token
            
        Returns:
            Boolean indicating if user can perform reasoning
        """
        try:
            roles = user_info.get("roles", [])
            permissions = user_info.get("permissions", [])
            
            # Check for reasoning-specific permissions
            reasoning_permissions = [
                "reasoning:use",
                "thinking:execute", 
                "ai:access",
                "premium:features"
            ]
            
            # Check for admin roles
            admin_roles = ["admin", "superuser", "premium"]
            
            # Allow if user has any reasoning permission or admin role
            has_permission = (
                any(perm in permissions for perm in reasoning_permissions) or
                any(role in roles for role in admin_roles) or
                "reasoning" in str(permissions).lower() or
                "admin" in str(roles).lower()
            )
            
            if not has_permission:
                logger.warning(f"User {user_info['user_id']} lacks reasoning permissions")
            
            return has_permission
            
        except Exception as e:
            logger.error(f"Error checking reasoning permissions: {e}")
            return False  # Deny access on error
    
    def generate_service_token(self, service_name: str, expires_in_hours: int = 24) -> str:
        """
        Generate a service-to-service authentication token
        
        Args:
            service_name: Name of the service requesting token
            expires_in_hours: Token expiration time
            
        Returns:
            JWT token for service authentication
        """
        if not self.jwt_secret:
            raise ValueError("JWT secret key not configured")
        
        try:
            now = datetime.utcnow()
            payload = {
                "sub": f"service:{service_name}",
                "service_name": service_name,
                "token_type": "service",
                "iat": now,
                "exp": now + timedelta(hours=expires_in_hours),
                "roles": ["service"],
                "permissions": ["service:access", "reasoning:use"]
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            logger.debug(f"Generated service token for {service_name}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating service token: {e}")
            raise ValueError(f"Service token generation failed: {str(e)}")
    
    async def validate_service_token(self, token: str) -> Dict[str, Any]:
        """
        Validate service-to-service token
        
        Args:
            token: Service JWT token
            
        Returns:
            Dict with service information
        """
        try:
            user_info = await self.validate_token(token)
            
            # Verify this is a service token
            if user_info.get("token_type") != "service":
                raise ValueError("Not a valid service token")
            
            service_name = user_info.get("service_name")
            if not service_name:
                raise ValueError("Service token missing service name")
            
            logger.debug(f"Successfully validated service token for {service_name}")
            return user_info
            
        except Exception as e:
            logger.error(f"Service token validation failed: {e}")
            raise
    
    def extract_user_id(self, user_info: Dict[str, Any]) -> str:
        """
        Extract user ID from user information
        
        Args:
            user_info: User information dict
            
        Returns:
            User ID string
        """
        user_id = user_info.get("user_id")
        if not user_id:
            # Fallback to other possible fields
            user_id = user_info.get("sub") or user_info.get("username") or "anonymous"
        
        # Handle service tokens
        if isinstance(user_id, str) and user_id.startswith("service:"):
            return user_id
            
        return str(user_id)
    
    def is_service_token(self, user_info: Dict[str, Any]) -> bool:
        """
        Check if the token represents a service account
        
        Args:
            user_info: User information dict
            
        Returns:
            Boolean indicating if this is a service token
        """
        return (
            user_info.get("token_type") == "service" or
            "service" in user_info.get("roles", []) or
            str(user_info.get("user_id", "")).startswith("service:")
        )