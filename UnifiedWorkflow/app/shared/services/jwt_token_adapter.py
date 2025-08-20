"""
JWT Token Adapter - Unified JWT Format Normalization

Provides consistent interface for handling legacy (sub=email) and enhanced (sub=user_id) JWT formats.
Maintains backward compatibility while enabling service boundary coordination.
"""

import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
import jwt
from dataclasses import dataclass

from shared.utils.config import get_settings
from shared.schemas import TokenData
from shared.database.models import UserRole

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class NormalizedTokenData:
    """Normalized token data structure with guaranteed fields"""
    user_id: int
    email: str
    role: UserRole
    format_type: str  # "legacy" or "enhanced"
    raw_payload: Dict[str, Any]
    expires_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None


class JWTTokenAdapter:
    """
    JWT Token Adapter for normalizing different JWT token formats.
    
    Handles:
    - Legacy format: {"sub": "email", "id": user_id, "role": "role"}
    - Enhanced format: {"sub": user_id, "email": "email", "role": "role"}
    - Mixed formats and edge cases
    
    Provides consistent interface for all downstream services.
    """
    
    def __init__(self):
        self.secret_key = str(settings.JWT_SECRET_KEY.get_secret_value())
        self.algorithm = "HS256"
        self.leeway = 60  # 60 seconds clock skew tolerance
        
    def normalize_token(self, token: str) -> NormalizedTokenData:
        """
        Normalize any JWT token format to standard structure.
        
        Args:
            token: Raw JWT token string
            
        Returns:
            NormalizedTokenData with consistent fields
            
        Raises:
            jwt.InvalidTokenError: Invalid or expired token
            ValueError: Token format cannot be normalized
        """
        try:
            # Decode JWT with error tolerance
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "verify_exp": True,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_aud": False,
                },
                leeway=self.leeway
            )
            
            logger.debug(f"Decoded JWT payload keys: {list(payload.keys())}")
            
            # Try enhanced format first (sub=user_id, email=email, role=role)
            normalized = self._try_enhanced_format(payload)
            if normalized:
                return normalized
                
            # Fallback to legacy format (sub=email, id=user_id, role=role)
            normalized = self._try_legacy_format(payload)
            if normalized:
                return normalized
                
            # Last resort: mixed format handling
            normalized = self._try_mixed_format(payload)
            if normalized:
                return normalized
                
            raise ValueError(f"Cannot normalize token format. Available keys: {list(payload.keys())}")
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {e}")
            raise
        except Exception as e:
            logger.error(f"Token normalization error: {e}")
            raise ValueError(f"Token normalization failed: {e}")
    
    def _try_enhanced_format(self, payload: Dict[str, Any]) -> Optional[NormalizedTokenData]:
        """Try to parse enhanced format: sub=user_id, email=email"""
        try:
            sub_value = payload.get("sub")
            email = payload.get("email")
            role = payload.get("role")
            
            if not all([sub_value, email, role]):
                return None
                
            # Sub should be user_id in enhanced format (string or int)
            if isinstance(sub_value, int) or (isinstance(sub_value, str) and sub_value.isdigit()):
                user_id = int(sub_value)
                
                if "@" in email:  # Valid email format
                    logger.debug(f"Parsed enhanced token format: user_id={user_id}, email={email}")
                    return NormalizedTokenData(
                        user_id=user_id,
                        email=email,
                        role=UserRole(role),
                        format_type="enhanced",
                        raw_payload=payload,
                        expires_at=self._extract_timestamp(payload, "exp"),
                        issued_at=self._extract_timestamp(payload, "iat")
                    )
        except (ValueError, TypeError) as e:
            logger.debug(f"Enhanced format parsing failed: {e}")
            
        return None
    
    def _try_legacy_format(self, payload: Dict[str, Any]) -> Optional[NormalizedTokenData]:
        """Try to parse legacy format: sub=email, id=user_id"""
        try:
            sub_value = payload.get("sub")
            user_id = payload.get("id")
            role = payload.get("role")
            
            if not all([sub_value, user_id, role]):
                return None
                
            # Sub should be email in legacy format
            if isinstance(sub_value, str) and "@" in sub_value:
                email = sub_value
                
                if isinstance(user_id, int) or (isinstance(user_id, str) and user_id.isdigit()):
                    user_id = int(user_id)
                    logger.debug(f"Parsed legacy token format: user_id={user_id}, email={email}")
                    return NormalizedTokenData(
                        user_id=user_id,
                        email=email,
                        role=UserRole(role),
                        format_type="legacy",
                        raw_payload=payload,
                        expires_at=self._extract_timestamp(payload, "exp"),
                        issued_at=self._extract_timestamp(payload, "iat")
                    )
        except (ValueError, TypeError) as e:
            logger.debug(f"Legacy format parsing failed: {e}")
            
        return None
    
    def _try_mixed_format(self, payload: Dict[str, Any]) -> Optional[NormalizedTokenData]:
        """Handle mixed or malformed token formats"""
        try:
            # Extract any available user identification
            user_id = None
            email = None
            role = payload.get("role")
            
            # Try to find user_id from various fields
            for field in ["id", "user_id", "sub"]:
                if field in payload:
                    value = payload[field]
                    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                        user_id = int(value)
                        break
            
            # Try to find email from various fields
            for field in ["email", "sub", "username"]:
                if field in payload:
                    value = payload[field]
                    if isinstance(value, str) and "@" in value:
                        email = value
                        break
                        
            if user_id and email and role:
                logger.debug(f"Parsed mixed token format: user_id={user_id}, email={email}")
                return NormalizedTokenData(
                    user_id=user_id,
                    email=email,
                    role=UserRole(role),
                    format_type="mixed",
                    raw_payload=payload,
                    expires_at=self._extract_timestamp(payload, "exp"),
                    issued_at=self._extract_timestamp(payload, "iat")
                )
                
        except (ValueError, TypeError) as e:
            logger.debug(f"Mixed format parsing failed: {e}")
            
        return None
    
    def _extract_timestamp(self, payload: Dict[str, Any], field: str) -> Optional[datetime]:
        """Extract timestamp from payload and convert to datetime"""
        try:
            timestamp = payload.get(field)
            if timestamp:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError, OSError):
            pass
        return None
    
    def convert_to_legacy_format(self, normalized: NormalizedTokenData) -> TokenData:
        """Convert normalized token data to legacy TokenData format"""
        return TokenData(
            id=normalized.user_id,
            email=normalized.email,
            role=normalized.role
        )
    
    def validate_token_consistency(self, token: str, expected_user_id: int, expected_email: str) -> bool:
        """
        Validate that token contains expected user information.
        Used for security verification across service boundaries.
        """
        try:
            normalized = self.normalize_token(token)
            return (
                normalized.user_id == expected_user_id and
                normalized.email.lower() == expected_email.lower()
            )
        except Exception as e:
            logger.warning(f"Token consistency validation failed: {e}")
            return False
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired without full validation"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Don't raise on expiration
            )
            
            exp = payload.get("exp")
            if exp:
                exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                return datetime.now(timezone.utc) > exp_time
                
            return True  # No expiration = expired
        except Exception:
            return True  # Invalid token = expired


# Global instance for service boundary coordination
jwt_token_adapter = JWTTokenAdapter()


from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi import Depends

# Initialize HTTPBearer security
security = HTTPBearer()

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    FastAPI dependency function for JWT token verification.
    
    This function is used by all new services to extract and verify JWT tokens
    from Authorization headers and return normalized user data.
    
    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI HTTPBearer
        
    Returns:
        Dict containing normalized user data for FastAPI dependency injection
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or missing
    """
    from fastapi import HTTPException, status
    
    token = credentials.credentials
    
    if not token:
        logger.error("Empty token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Normalize token using the adapter
        normalized = jwt_token_adapter.normalize_token(token)
        
        # Return dictionary compatible with FastAPI dependency injection
        return {
            "user_id": normalized.user_id,
            "email": normalized.email,
            "role": normalized.role.value,  # Convert enum to string
            "format_type": normalized.format_type,
            "expires_at": normalized.expires_at.isoformat() if normalized.expires_at else None,
            "issued_at": normalized.issued_at.isoformat() if normalized.issued_at else None,
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        logger.error(f"Token normalization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token format not supported",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def normalize_request_token(request) -> Optional[NormalizedTokenData]:
    """
    Convenience function to extract and normalize token from FastAPI request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        NormalizedTokenData if valid token found, None otherwise
    """
    token = None
    
    # Extract from Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    
    # Fallback to cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if token:
        try:
            return jwt_token_adapter.normalize_token(token)
        except Exception as e:
            logger.debug(f"Token normalization failed: {e}")
    
    return None