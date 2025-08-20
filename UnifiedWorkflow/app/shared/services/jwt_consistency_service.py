"""
JWT Consistency Service
Ensures consistent JWT SECRET_KEY usage across all authentication modules.

This service addresses the Bearer token authentication issue where tokens created
by one module cannot be validated by another due to SECRET_KEY inconsistencies.
"""

import logging
import time
from typing import Dict, Any, Optional
import jwt
from datetime import datetime, timedelta, timezone
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)

class JWTConsistencyService:
    """
    Centralized JWT service ensuring consistent SECRET_KEY usage.
    """
    
    _instance = None
    _secret_key = None
    _algorithm = "HS256"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._refresh_secret_key()
    
    def _refresh_secret_key(self) -> None:
        """Refresh the SECRET_KEY from settings."""
        try:
            settings = get_settings()
            self._secret_key = str(settings.JWT_SECRET_KEY.get_secret_value())
            logger.debug(f"JWT SECRET_KEY refreshed (length: {len(self._secret_key)})")
            
        except Exception as e:
            logger.error(f"Failed to refresh JWT SECRET_KEY: {e}")
            if not self._secret_key:
                raise RuntimeError("Unable to load JWT SECRET_KEY")
    
    def get_secret_key(self) -> str:
        """Get the current SECRET_KEY, refreshing if necessary."""
        if not self._secret_key:
            self._refresh_secret_key()
        return self._secret_key
    
    def get_algorithm(self) -> str:
        """Get the JWT algorithm."""
        return self._algorithm
    
    def create_token(self, payload: Dict[str, Any], expires_minutes: int = 60) -> str:
        """
        Create JWT token with consistent SECRET_KEY.
        
        Args:
            payload: Token payload data
            expires_minutes: Token expiration in minutes
            
        Returns:
            Encoded JWT token string
        """
        start_time = time.perf_counter()
        
        try:
            to_encode = payload.copy()
            now = datetime.now(timezone.utc)
            expire = now + timedelta(minutes=expires_minutes)
            
            # Standard JWT claims
            to_encode.update({
                "exp": expire,
                "iat": now,
                "nbf": now,
            })
            
            # Use consistent SECRET_KEY
            secret_key = self.get_secret_key()
            encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=self._algorithm)
            
            # Record successful token creation
            creation_time_ms = (time.perf_counter() - start_time) * 1000
            self._record_jwt_operation('create', 'success', creation_time_ms)
            
            logger.debug(f"JWT token created with consistent SECRET_KEY in {creation_time_ms:.2f}ms")
            return encoded_jwt
            
        except Exception as e:
            creation_time_ms = (time.perf_counter() - start_time) * 1000
            self._record_jwt_operation('create', 'failure', creation_time_ms)
            logger.error(f"JWT token creation failed: {e}")
            raise
    
    def decode_token(self, token: str, options: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """
        Decode JWT token with consistent SECRET_KEY.
        
        Args:
            token: JWT token string
            options: JWT decode options
            
        Returns:
            Decoded token payload
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
        """
        start_time = time.perf_counter()
        
        try:
            # Default options
            if options is None:
                options = {
                    "verify_exp": True,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_aud": False,
                }
            
            # Use consistent SECRET_KEY
            secret_key = self.get_secret_key()
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[self._algorithm],
                options=options,
                leeway=60  # Allow 60 seconds clock skew
            )
            
            # Record successful validation
            validation_time_ms = (time.perf_counter() - start_time) * 1000
            self._record_jwt_operation('validate', 'success', validation_time_ms)
            
            logger.debug(f"JWT token decoded with consistent SECRET_KEY in {validation_time_ms:.2f}ms")
            return payload
            
        except jwt.ExpiredSignatureError:
            validation_time_ms = (time.perf_counter() - start_time) * 1000
            self._record_jwt_operation('validate', 'expired', validation_time_ms)
            logger.warning("JWT token has expired")
            raise
        except jwt.InvalidSignatureError:
            validation_time_ms = (time.perf_counter() - start_time) * 1000
            self._record_jwt_operation('validate', 'signature_invalid', validation_time_ms)
            self._record_secret_key_event('mismatch', healthy=False)
            logger.error("JWT signature verification failed - possible SECRET_KEY mismatch")
            # Try refreshing SECRET_KEY in case it changed
            self._refresh_secret_key()
            raise
        except jwt.InvalidTokenError as e:
            validation_time_ms = (time.perf_counter() - start_time) * 1000
            self._record_jwt_operation('validate', 'invalid_token', validation_time_ms)
            logger.error(f"JWT token validation failed: {e}")
            raise
    
    def validate_token_format(self, token: str) -> Dict[str, Any]:
        """
        Validate token format without signature verification.
        
        Args:
            token: JWT token string
            
        Returns:
            Validation result with payload and status
        """
        try:
            # Decode without verification to check format
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Check required fields for authentication
            required_fields = ["sub", "email", "role"]
            missing_fields = [field for field in required_fields if field not in payload]
            
            return {
                "valid_format": len(missing_fields) == 0,
                "payload": payload,
                "missing_fields": missing_fields,
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc) if "exp" in payload else None
            }
            
        except Exception as e:
            logger.error(f"Token format validation failed: {e}")
            return {
                "valid_format": False,
                "payload": {},
                "missing_fields": ["invalid_token"],
                "error": str(e),
                "expires_at": None
            }
    
    def refresh_access_token(self, payload: Dict[str, Any]) -> str:
        """
        Refresh access token with updated timestamps.
        
        Args:
            payload: Original token payload
            
        Returns:
            New JWT token string
        """
        try:
            # Preserve original user data
            user_data = {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "id": payload.get("id"),
                "role": payload.get("role"),
                "session_id": payload.get("session_id"),
                "device_id": payload.get("device_id"),
                "tfa_verified": payload.get("tfa_verified", False)
            }
            
            return self.create_token(user_data)
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
    def _record_jwt_operation(self, operation_type: str, result: str, time_ms: float) -> None:
        """Record JWT operation for monitoring."""
        try:
            # Import here to avoid circular imports
            from shared.services.auth_monitoring_service import auth_monitoring_service
            auth_monitoring_service.record_jwt_operation(operation_type, result, time_ms)
        except ImportError:
            # Monitoring service not available yet, skip
            pass
        except Exception as e:
            logger.debug(f"Failed to record JWT operation: {e}")
    
    def _record_secret_key_event(self, event_type: str, healthy: bool) -> None:
        """Record SECRET_KEY event for monitoring."""
        try:
            # Import here to avoid circular imports
            from shared.services.auth_monitoring_service import auth_monitoring_service
            auth_monitoring_service.record_secret_key_event(event_type, healthy)
        except ImportError:
            # Monitoring service not available yet, skip
            pass
        except Exception as e:
            logger.debug(f"Failed to record SECRET_KEY event: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get JWT consistency service health status."""
        return {
            'secret_key_loaded': bool(self._secret_key),
            'secret_key_length': len(self._secret_key) if self._secret_key else 0,
            'algorithm': self._algorithm,
            'service_initialized': hasattr(self, '_initialized')
        }

# Global singleton instance
jwt_consistency_service = JWTConsistencyService()