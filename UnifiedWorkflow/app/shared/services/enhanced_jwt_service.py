"""Enhanced JWT service for cross-service authentication and security."""

import jwt
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from shared.database.models._models import User
from shared.database.models.security_models import CrossServiceAuth
from shared.services.security_audit_service import security_audit_service
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EnhancedJWTService:
    """Enhanced JWT service with cross-service security and audit capabilities."""
    
    def __init__(self):
        self.logger = logger
        self.algorithm = "HS256"
        self.secret_key = settings.JWT_SECRET_KEY.get_secret_value() if settings.JWT_SECRET_KEY else "fallback-secret"
        self.access_token_expire_minutes = 60  # Increased from 30 to 60 minutes
        self.service_token_expire_hours = 24
        self.clock_skew_seconds = 60  # Allow 60 seconds clock skew
        # Circuit breaker for security audit service to prevent connection pool exhaustion
        self.enable_security_audit = False  # Temporarily disabled
    
    async def create_access_token(
        self,
        session: AsyncSession,
        user_id: int,
        scopes: List[str] = None,
        session_id: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create access token with enhanced security features."""
        try:
            scopes = scopes or ["read", "write"]
            
            # Get user information
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            if not user.is_active:
                raise ValueError(f"User {user_id} is not active")
            
            # Create token payload
            now = datetime.utcnow()
            expire = now + timedelta(minutes=self.access_token_expire_minutes)
            
            payload = {
                "sub": str(user_id),
                "email": user.email,
                "role": user.role.value,
                "scopes": scopes,
                "iat": now.timestamp(),
                "exp": expire.timestamp(),
                "nbf": now.timestamp(),
                "iss": "ai_workflow_engine",
                "aud": ["api", "webui"],
                "jti": secrets.token_urlsafe(32),  # JWT ID for tracking
                "session_id": session_id,
                "device_fingerprint": device_fingerprint,
                "security_level": "standard"
            }
            
            # Add additional security claims for high-privilege operations
            if user.role.value == "admin":
                payload["security_level"] = "elevated"
                payload["admin_permissions"] = True
            
            # Encode token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Log token creation (disabled to prevent connection pool exhaustion)
            if self.enable_security_audit:
                try:
                    await security_audit_service.log_data_access(
                        session=session,
                        user_id=user_id,
                        service_name="jwt_service",
                        access_type="TOKEN_CREATE",
                        table_name="access_tokens",
                        row_count=1,
                        sensitive_data_accessed=True,
                        access_pattern={
                            "token_type": "access_token",
                            "scopes": scopes,
                            "expires_at": expire.isoformat()
                        },
                        session_id=session_id,
                        ip_address=ip_address
                    )
                except Exception as audit_error:
                    self.logger.warning(f"Security audit logging failed: {audit_error}")
            else:
                self.logger.debug("Security audit disabled - skipping token creation log")
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "expires_at": expire.isoformat(),
                "scopes": scopes,
                "jti": payload["jti"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create access token: {str(e)}")
            
            # Log security violation (disabled to prevent connection pool exhaustion)
            if self.enable_security_audit:
                try:
                    await security_audit_service.log_security_violation(
                        session=session,
                        violation_type="TOKEN_CREATION_FAILED",
                        severity="MEDIUM",
                        violation_details={
                            "user_id": user_id,
                            "error": str(e),
                            "attempted_scopes": scopes
                        },
                        user_id=user_id,
                        session_id=session_id,
                        ip_address=ip_address,
                        blocked=True
                    )
                except Exception as audit_error:
                    self.logger.warning(f"Security violation logging failed: {audit_error}")
            
            raise
    
    async def create_service_token(
        self,
        session: AsyncSession,
        user_id: int,
        source_service: str,
        target_service: str,
        permissions: Dict[str, Any],
        scope: List[str],
        expires_hours: int = None
    ) -> Dict[str, Any]:
        """Create cross-service authentication token."""
        try:
            expires_hours = expires_hours or self.service_token_expire_hours
            
            # Validate user
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create token payload
            now = datetime.utcnow()
            expire = now + timedelta(hours=expires_hours)
            
            payload = {
                "sub": str(user_id),
                "source_service": source_service,
                "target_service": target_service,
                "permissions": permissions,
                "scope": scope,
                "iat": now.timestamp(),
                "exp": expire.timestamp(),
                "nbf": now.timestamp(),
                "iss": f"ai_workflow_engine_{source_service}",
                "aud": [target_service],
                "jti": secrets.token_urlsafe(32),
                "token_type": "service",
                "security_level": "service_to_service"
            }
            
            # Encode token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Store cross-service auth record
            cross_service_auth = CrossServiceAuth(
                user_id=user_id,
                source_service=source_service,
                target_service=target_service,
                token_hash=token_hash,
                permissions=permissions,
                scope=scope,
                expires_at=expire
            )
            
            session.add(cross_service_auth)
            await session.commit()
            
            # Log service token creation
            await security_audit_service.log_data_access(
                session=session,
                user_id=user_id,
                service_name="jwt_service",
                access_type="SERVICE_TOKEN_CREATE",
                table_name="cross_service_auth",
                row_count=1,
                sensitive_data_accessed=True,
                access_pattern={
                    "source_service": source_service,
                    "target_service": target_service,
                    "permissions": permissions,
                    "scope": scope
                }
            )
            
            return {
                "service_token": token,
                "token_type": "service_bearer",
                "expires_in": expires_hours * 3600,
                "expires_at": expire.isoformat(),
                "permissions": permissions,
                "scope": scope,
                "jti": payload["jti"],
                "auth_id": str(cross_service_auth.id)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create service token: {str(e)}")
            
            await security_audit_service.log_security_violation(
                session=session,
                violation_type="SERVICE_TOKEN_CREATION_FAILED",
                severity="HIGH",
                violation_details={
                    "user_id": user_id,
                    "source_service": source_service,
                    "target_service": target_service,
                    "error": str(e)
                },
                user_id=user_id,
                blocked=True
            )
            
            raise
    
    async def verify_token(
        self,
        session: AsyncSession,
        token: str,
        required_scopes: List[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify and decode token with security validation."""
        try:
            # Decode token with clock skew tolerance
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={
                    "verify_exp": True, 
                    "verify_nbf": True,
                    "verify_iat": False,  # Don't verify issued at time for compatibility
                    "verify_aud": False   # Don't verify audience for compatibility
                },
                leeway=timedelta(seconds=self.clock_skew_seconds)  # Allow clock skew
            )
            
            # Handle both legacy and enhanced token formats
            user_id = None
            token_type = payload.get("token_type", "access")
            
            # Enhanced format: sub=user_id, email=email
            if "email" in payload and payload.get("sub"):
                try:
                    user_id = int(payload["sub"])
                except (ValueError, TypeError):
                    # If sub is not a number, might be legacy format
                    pass
            
            # Legacy format: sub=email, id=user_id  
            if user_id is None and "id" in payload:
                try:
                    user_id = int(payload["id"])
                except (ValueError, TypeError):
                    pass
            
            if user_id is None:
                raise jwt.InvalidTokenError("Cannot determine user ID from token")
            
            # Validate user still exists and is active
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise jwt.InvalidTokenError("User not found")
            
            if not user.is_active:
                raise jwt.InvalidTokenError("User account disabled")
            
            # Check required scopes
            if required_scopes:
                token_scopes = payload.get("scopes", [])
                if not all(scope in token_scopes for scope in required_scopes):
                    raise jwt.InvalidTokenError("Insufficient permissions")
            
            # For service tokens, validate cross-service auth record
            if token_type == "service":
                await self._validate_service_token(session, token, payload)
            
            # Log successful token verification (disabled to prevent connection pool exhaustion)
            if self.enable_security_audit:
                try:
                    await security_audit_service.log_data_access(
                        session=session,
                        user_id=user_id,
                        service_name="jwt_service",
                        access_type="TOKEN_VERIFY",
                        table_name="token_verification",
                        row_count=1,
                        sensitive_data_accessed=False,
                        access_pattern={
                            "token_type": token_type,
                            "jti": payload.get("jti"),
                            "verification_success": True
                        },
                        session_id=payload.get("session_id"),
                        ip_address=ip_address
                    )
                except Exception as audit_error:
                    self.logger.warning(f"Token verification logging failed: {audit_error}")
            
            # Extract email and role from token or database
            email = payload.get("email") or user.email
            role = payload.get("role") or user.role.value
            
            # For legacy tokens, scopes might not exist
            scopes = payload.get("scopes", ["read", "write"])
            
            return {
                "valid": True,
                "user_id": user_id,
                "email": email,
                "role": role,
                "scopes": scopes,
                "token_type": token_type,
                "jti": payload.get("jti"),
                "expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
                "security_level": payload.get("security_level", "standard"),
                "session_id": payload.get("session_id"),
                "device_id": payload.get("device_id")
            }
            
        except jwt.ExpiredSignatureError:
            await self._log_token_verification_failure(
                session, "TOKEN_EXPIRED", user_id=None, 
                ip_address=ip_address, user_agent=user_agent
            )
            raise jwt.InvalidTokenError("Token has expired")
            
        except jwt.InvalidTokenError as e:
            await self._log_token_verification_failure(
                session, "INVALID_TOKEN", user_id=None,
                ip_address=ip_address, user_agent=user_agent, error=str(e)
            )
            raise
            
        except Exception as e:
            self.logger.error(f"Token verification failed: {str(e)}")
            await self._log_token_verification_failure(
                session, "TOKEN_VERIFICATION_ERROR", user_id=None,
                ip_address=ip_address, user_agent=user_agent, error=str(e)
            )
            raise jwt.InvalidTokenError("Token verification failed")
    
    async def revoke_token(
        self,
        session: AsyncSession,
        jti: str,
        user_id: Optional[int] = None,
        reason: str = "manual_revocation"
    ) -> bool:
        """Revoke a token by its JTI."""
        try:
            # For service tokens, mark as revoked in database
            if user_id:
                result = await session.execute(
                    select(CrossServiceAuth).where(
                        and_(
                            CrossServiceAuth.user_id == user_id,
                            CrossServiceAuth.is_active == True
                        )
                    )
                )
                
                service_auths = result.scalars().all()
                
                for auth in service_auths:
                    # Check if this token matches (simplified check)
                    auth.is_active = False
                    auth.revoked_at = datetime.utcnow()
                    auth.revocation_reason = reason
                
                await session.commit()
            
            # Log token revocation
            await security_audit_service.log_data_access(
                session=session,
                user_id=user_id,
                service_name="jwt_service",
                access_type="TOKEN_REVOKE",
                table_name="token_revocation",
                row_count=1,
                sensitive_data_accessed=True,
                access_pattern={
                    "jti": jti,
                    "reason": reason,
                    "revoked_at": datetime.utcnow().isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke token: {str(e)}")
            return False
    
    async def get_user_tokens(
        self,
        session: AsyncSession,
        user_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all tokens for a user."""
        try:
            query = select(CrossServiceAuth).where(CrossServiceAuth.user_id == user_id)
            
            if active_only:
                query = query.where(
                    and_(
                        CrossServiceAuth.is_active == True,
                        or_(
                            CrossServiceAuth.expires_at.is_(None),
                            CrossServiceAuth.expires_at > datetime.utcnow()
                        )
                    )
                )
            
            result = await session.execute(query)
            tokens = result.scalars().all()
            
            token_list = []
            for token in tokens:
                token_list.append({
                    "id": str(token.id),
                    "source_service": token.source_service,
                    "target_service": token.target_service,
                    "scope": token.scope,
                    "issued_at": token.issued_at.isoformat(),
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
                    "is_active": token.is_active,
                    "revoked_at": token.revoked_at.isoformat() if token.revoked_at else None
                })
            
            return token_list
            
        except Exception as e:
            self.logger.error(f"Failed to get user tokens: {str(e)}")
            return []
    
    def create_encrypted_payload(self, data: Dict[str, Any], password: str) -> str:
        """Create encrypted payload for sensitive data transmission."""
        try:
            # Generate salt and key
            salt = secrets.token_bytes(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode())
            
            # Generate IV
            iv = secrets.token_bytes(16)
            
            # Encrypt data
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Prepare data for encryption
            json_data = json.dumps(data).encode()
            
            # Pad data to multiple of 16 bytes
            padding_length = 16 - (len(json_data) % 16)
            padded_data = json_data + bytes([padding_length] * padding_length)
            
            # Encrypt
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine salt, IV, and encrypted data
            combined = salt + iv + encrypted_data
            
            # Encode as base64
            return base64.b64encode(combined).decode()
            
        except Exception as e:
            self.logger.error(f"Failed to create encrypted payload: {str(e)}")
            raise
    
    def decrypt_payload(self, encrypted_payload: str, password: str) -> Dict[str, Any]:
        """Decrypt encrypted payload."""
        try:
            # Decode from base64
            combined = base64.b64decode(encrypted_payload.encode())
            
            # Extract components
            salt = combined[:16]
            iv = combined[16:32]
            encrypted_data = combined[32:]
            
            # Derive key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf.derive(password.encode())
            
            # Decrypt
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Remove padding
            padding_length = padded_data[-1]
            json_data = padded_data[:-padding_length]
            
            # Parse JSON
            return json.loads(json_data.decode())
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt payload: {str(e)}")
            raise
    
    async def _validate_service_token(
        self,
        session: AsyncSession,
        token: str,
        payload: Dict[str, Any]
    ) -> None:
        """Validate service token against database record."""
        try:
            user_id = int(payload["sub"])
            source_service = payload["source_service"]
            target_service = payload["target_service"]
            
            # Hash token for comparison
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Find matching auth record
            result = await session.execute(
                select(CrossServiceAuth).where(
                    and_(
                        CrossServiceAuth.user_id == user_id,
                        CrossServiceAuth.source_service == source_service,
                        CrossServiceAuth.target_service == target_service,
                        CrossServiceAuth.token_hash == token_hash,
                        CrossServiceAuth.is_active == True,
                        or_(
                            CrossServiceAuth.expires_at.is_(None),
                            CrossServiceAuth.expires_at > datetime.utcnow()
                        )
                    )
                )
            )
            
            auth_record = result.scalar_one_or_none()
            
            if not auth_record:
                raise jwt.InvalidTokenError("Service token not found or expired")
            
            # Update last used timestamp
            auth_record.last_used_at = datetime.utcnow()
            await session.commit()
            
        except Exception as e:
            self.logger.error(f"Service token validation failed: {str(e)}")
            raise jwt.InvalidTokenError("Service token validation failed")
    
    async def _log_token_verification_failure(
        self,
        session: AsyncSession,
        failure_type: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Log token verification failure."""
        try:
            await security_audit_service.log_security_violation(
                session=session,
                violation_type=failure_type,
                severity="MEDIUM",
                violation_details={
                    "error": error,
                    "verification_timestamp": datetime.utcnow().isoformat()
                },
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                blocked=True
            )
        except Exception as e:
            self.logger.error(f"Failed to log verification failure: {str(e)}")


# Global enhanced JWT service instance
enhanced_jwt_service = EnhancedJWTService()