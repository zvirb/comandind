"""Secure token storage service with encryption and session management."""

import json
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from shared.database.models.secure_token_models import SecureTokenStorage
from shared.services.security_audit_service import security_audit_service

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of tokens that can be stored securely."""
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    SESSION_TOKEN = "session_token"
    CSRF_TOKEN = "csrf_token"
    API_KEY = "api_key"
    DEVICE_TOKEN = "device_token"


class StorageType(Enum):
    """Types of storage backends."""
    MEMORY = "memory"
    BROWSER_CRYPTO = "browser_crypto"
    ENCRYPTED_COOKIE = "encrypted_cookie"
    SECURE_STORAGE = "secure_storage"


@dataclass
class SecureToken:
    """Represents a securely stored token."""
    token_id: str
    token_type: TokenType
    encrypted_value: str
    user_id: int
    session_id: Optional[str] = None
    device_fingerprint: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: Optional[datetime] = None
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    storage_type: StorageType = StorageType.MEMORY


class SecureTokenStorageService:
    """Service for secure token storage with encryption and session management."""
    
    def __init__(self):
        self.logger = logger
        self._memory_storage: Dict[str, SecureToken] = {}
        self._encryption_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        self._session_keys: Dict[str, bytes] = {}  # Per-session encryption keys
        self._initialized = False
    
    async def initialize(self, master_key: Optional[str] = None):
        """Initialize the secure token storage service."""
        if self._initialized:
            return
        
        try:
            # Generate or derive master encryption key
            if master_key:
                # Derive key from provided master key
                salt = b"secure_token_storage_salt_v1"
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                self._encryption_key = kdf.derive(master_key.encode())
            else:
                # Generate random key
                self._encryption_key = secrets.token_bytes(32)
            
            # Initialize Fernet encryption
            fernet_key = base64.urlsafe_b64encode(self._encryption_key)
            self._fernet = Fernet(fernet_key)
            
            self._initialized = True
            self.logger.info("SecureTokenStorageService initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SecureTokenStorageService: {str(e)}")
            raise
    
    async def store_token(
        self,
        session: AsyncSession,
        user_id: int,
        token_type: TokenType,
        token_value: str,
        session_id: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        storage_type: StorageType = StorageType.SECURE_STORAGE,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a token securely with encryption."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Generate unique token ID
            token_id = secrets.token_urlsafe(32)
            
            # Encrypt token value
            encrypted_value = await self._encrypt_token(
                token_value, user_id, session_id
            )
            
            # Create secure token object
            secure_token = SecureToken(
                token_id=token_id,
                token_type=token_type,
                encrypted_value=encrypted_value,
                user_id=user_id,
                session_id=session_id,
                device_fingerprint=device_fingerprint,
                expires_at=expires_at,
                storage_type=storage_type,
                metadata=metadata or {}
            )
            
            # Store based on storage type
            if storage_type == StorageType.MEMORY:
                self._memory_storage[token_id] = secure_token
                
            elif storage_type == StorageType.SECURE_STORAGE:
                # Store in database
                db_token = SecureTokenStorage(
                    token_id=token_id,
                    user_id=user_id,
                    token_type=token_type.value,
                    encrypted_value=encrypted_value,
                    session_id=session_id,
                    device_fingerprint=device_fingerprint,
                    expires_at=expires_at,
                    metadata=metadata or {}
                )
                
                session.add(db_token)
                await session.commit()
                
                # Also keep in memory for quick access
                self._memory_storage[token_id] = secure_token
            
            # Log token storage
            await security_audit_service.log_data_access(
                session=session,
                user_id=user_id,
                service_name="secure_token_storage",
                access_type="TOKEN_STORE",
                table_name="secure_token_storage",
                row_count=1,
                sensitive_data_accessed=True,
                access_pattern={
                    "token_type": token_type.value,
                    "storage_type": storage_type.value,
                    "has_expiry": expires_at is not None,
                    "token_id": token_id
                },
                session_id=session_id
            )
            
            self.logger.debug(f"Stored token {token_id} ({token_type.value}) for user {user_id}")
            return token_id
            
        except Exception as e:
            self.logger.error(f"Failed to store token: {str(e)}")
            
            await security_audit_service.log_security_violation(
                session=session,
                violation_type="TOKEN_STORAGE_FAILED",
                severity="MEDIUM",
                violation_details={
                    "user_id": user_id,
                    "token_type": token_type.value,
                    "error": str(e)
                },
                user_id=user_id,
                blocked=True
            )
            
            raise
    
    async def retrieve_token(
        self,
        session: AsyncSession,
        token_id: str,
        user_id: int,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """Retrieve and decrypt a stored token."""
        if not self._initialized:
            await self.initialize()
        
        try:
            secure_token = None
            
            # Try memory storage first
            if token_id in self._memory_storage:
                secure_token = self._memory_storage[token_id]
            else:
                # Try database storage
                result = await session.execute(
                    select(SecureTokenStorage).where(
                        and_(
                            SecureTokenStorage.token_id == token_id,
                            SecureTokenStorage.user_id == user_id,
                            SecureTokenStorage.is_active == True,
                            or_(
                                SecureTokenStorage.expires_at.is_(None),
                                SecureTokenStorage.expires_at > datetime.now(timezone.utc)
                            )
                        )
                    )
                )
                
                db_token = result.scalar_one_or_none()
                if db_token:
                    secure_token = SecureToken(
                        token_id=db_token.token_id,
                        token_type=TokenType(db_token.token_type),
                        encrypted_value=db_token.encrypted_value,
                        user_id=db_token.user_id,
                        session_id=db_token.session_id,
                        device_fingerprint=db_token.device_fingerprint,
                        expires_at=db_token.expires_at,
                        created_at=db_token.created_at,
                        last_accessed_at=db_token.last_accessed_at,
                        access_count=db_token.access_count,
                        metadata=db_token.metadata or {},
                        storage_type=StorageType.SECURE_STORAGE
                    )
                    
                    # Cache in memory for faster access
                    self._memory_storage[token_id] = secure_token
            
            if not secure_token:
                return None
            
            # Check expiry
            if (secure_token.expires_at and 
                secure_token.expires_at <= datetime.now(timezone.utc)):
                # Token expired, remove it
                await self.revoke_token(session, token_id, user_id)
                return None
            
            # Validate user and session
            if secure_token.user_id != user_id:
                await security_audit_service.log_security_violation(
                    session=session,
                    violation_type="UNAUTHORIZED_TOKEN_ACCESS",
                    severity="HIGH",
                    violation_details={
                        "token_id": token_id,
                        "requested_user_id": user_id,
                        "token_user_id": secure_token.user_id
                    },
                    user_id=user_id,
                    blocked=True
                )
                return None
            
            if (session_id and secure_token.session_id and 
                secure_token.session_id != session_id):
                self.logger.warning(f"Session mismatch for token {token_id}")
                return None
            
            # Decrypt token value
            decrypted_value = await self._decrypt_token(
                secure_token.encrypted_value, user_id, secure_token.session_id
            )
            
            # Update access tracking
            secure_token.last_accessed_at = datetime.now(timezone.utc)
            secure_token.access_count += 1
            
            # Update database if stored there
            if secure_token.storage_type == StorageType.SECURE_STORAGE:
                db_result = await session.execute(
                    select(SecureTokenStorage).where(
                        SecureTokenStorage.token_id == token_id
                    )
                )
                db_token = db_result.scalar_one_or_none()
                if db_token:
                    db_token.last_accessed_at = secure_token.last_accessed_at
                    db_token.access_count = secure_token.access_count
                    await session.commit()
            
            # Log token access
            await security_audit_service.log_data_access(
                session=session,
                user_id=user_id,
                service_name="secure_token_storage",
                access_type="TOKEN_RETRIEVE",
                table_name="secure_token_storage",
                row_count=1,
                sensitive_data_accessed=True,
                access_pattern={
                    "token_type": secure_token.token_type.value,
                    "access_count": secure_token.access_count,
                    "token_age_hours": (
                        datetime.now(timezone.utc) - secure_token.created_at
                    ).total_seconds() / 3600,
                    "token_id": token_id
                },
                session_id=session_id
            )
            
            return decrypted_value
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve token {token_id}: {str(e)}")
            
            await security_audit_service.log_security_violation(
                session=session,
                violation_type="TOKEN_RETRIEVAL_FAILED",
                severity="MEDIUM",
                violation_details={
                    "token_id": token_id,
                    "user_id": user_id,
                    "error": str(e)
                },
                user_id=user_id,
                blocked=False
            )
            
            return None
    
    async def revoke_token(
        self,
        session: AsyncSession,
        token_id: str,
        user_id: int,
        reason: str = "manual_revocation"
    ) -> bool:
        """Revoke a stored token."""
        try:
            revoked = False
            
            # Remove from memory storage
            if token_id in self._memory_storage:
                del self._memory_storage[token_id]
                revoked = True
            
            # Update database storage
            result = await session.execute(
                select(SecureTokenStorage).where(
                    and_(
                        SecureTokenStorage.token_id == token_id,
                        SecureTokenStorage.user_id == user_id
                    )
                )
            )
            
            db_token = result.scalar_one_or_none()
            if db_token:
                db_token.is_active = False
                db_token.revoked_at = datetime.now(timezone.utc)
                db_token.revocation_reason = reason
                await session.commit()
                revoked = True
            
            if revoked:
                # Log token revocation
                await security_audit_service.log_data_access(
                    session=session,
                    user_id=user_id,
                    service_name="secure_token_storage",
                    access_type="TOKEN_REVOKE",
                    table_name="secure_token_storage",
                    row_count=1,
                    sensitive_data_accessed=True,
                    access_pattern={
                        "token_id": token_id,
                        "reason": reason,
                        "revoked_at": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                self.logger.info(f"Revoked token {token_id} for user {user_id}: {reason}")
            
            return revoked
            
        except Exception as e:
            self.logger.error(f"Failed to revoke token {token_id}: {str(e)}")
            return False
    
    async def revoke_user_tokens(
        self,
        session: AsyncSession,
        user_id: int,
        token_types: Optional[List[TokenType]] = None,
        except_session_id: Optional[str] = None,
        reason: str = "bulk_revocation"
    ) -> int:
        """Revoke all tokens for a user."""
        try:
            revoked_count = 0
            
            # Revoke memory storage tokens
            tokens_to_remove = []
            for token_id, secure_token in self._memory_storage.items():
                if secure_token.user_id == user_id:
                    if token_types and secure_token.token_type not in token_types:
                        continue
                    if (except_session_id and 
                        secure_token.session_id == except_session_id):
                        continue
                    
                    tokens_to_remove.append(token_id)
            
            for token_id in tokens_to_remove:
                del self._memory_storage[token_id]
                revoked_count += 1
            
            # Revoke database storage tokens
            query = select(SecureTokenStorage).where(
                and_(
                    SecureTokenStorage.user_id == user_id,
                    SecureTokenStorage.is_active == True
                )
            )
            
            if token_types:
                token_type_values = [tt.value for tt in token_types]
                query = query.where(SecureTokenStorage.token_type.in_(token_type_values))
            
            if except_session_id:
                query = query.where(
                    or_(
                        SecureTokenStorage.session_id.is_(None),
                        SecureTokenStorage.session_id != except_session_id
                    )
                )
            
            result = await session.execute(query)
            db_tokens = result.scalars().all()
            
            for db_token in db_tokens:
                db_token.is_active = False
                db_token.revoked_at = datetime.now(timezone.utc)
                db_token.revocation_reason = reason
                revoked_count += 1
            
            if db_tokens:
                await session.commit()
            
            # Log bulk revocation
            if revoked_count > 0:
                await security_audit_service.log_data_access(
                    session=session,
                    user_id=user_id,
                    service_name="secure_token_storage",
                    access_type="TOKEN_BULK_REVOKE",
                    table_name="secure_token_storage",
                    row_count=revoked_count,
                    sensitive_data_accessed=True,
                    access_pattern={
                        "revoked_count": revoked_count,
                        "token_types": [tt.value for tt in token_types] if token_types else "all",
                        "except_session_id": except_session_id,
                        "reason": reason
                    }
                )
                
                self.logger.info(f"Revoked {revoked_count} tokens for user {user_id}: {reason}")
            
            return revoked_count
            
        except Exception as e:
            self.logger.error(f"Failed to revoke user tokens: {str(e)}")
            return 0
    
    async def cleanup_expired_tokens(self, session: AsyncSession) -> int:
        """Clean up expired tokens."""
        try:
            current_time = datetime.now(timezone.utc)
            cleaned_count = 0
            
            # Clean up memory storage
            expired_tokens = []
            for token_id, secure_token in self._memory_storage.items():
                if (secure_token.expires_at and 
                    secure_token.expires_at <= current_time):
                    expired_tokens.append(token_id)
            
            for token_id in expired_tokens:
                del self._memory_storage[token_id]
                cleaned_count += 1
            
            # Clean up database storage
            result = await session.execute(
                select(SecureTokenStorage).where(
                    and_(
                        SecureTokenStorage.expires_at <= current_time,
                        SecureTokenStorage.is_active == True
                    )
                )
            )
            
            expired_db_tokens = result.scalars().all()
            
            for db_token in expired_db_tokens:
                db_token.is_active = False
                db_token.revoked_at = current_time
                db_token.revocation_reason = "expired"
                cleaned_count += 1
            
            if expired_db_tokens:
                await session.commit()
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} expired tokens")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired tokens: {str(e)}")
            return 0
    
    async def get_user_tokens(
        self,
        session: AsyncSession,
        user_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get list of user's stored tokens (metadata only, not values)."""
        try:
            tokens = []
            
            # Add memory storage tokens
            for token_id, secure_token in self._memory_storage.items():
                if secure_token.user_id == user_id:
                    tokens.append({
                        "token_id": token_id,
                        "token_type": secure_token.token_type.value,
                        "storage_type": secure_token.storage_type.value,
                        "session_id": secure_token.session_id,
                        "device_fingerprint": secure_token.device_fingerprint,
                        "created_at": secure_token.created_at.isoformat(),
                        "expires_at": secure_token.expires_at.isoformat() if secure_token.expires_at else None,
                        "last_accessed_at": secure_token.last_accessed_at.isoformat() if secure_token.last_accessed_at else None,
                        "access_count": secure_token.access_count,
                        "is_expired": (
                            secure_token.expires_at and 
                            secure_token.expires_at <= datetime.now(timezone.utc)
                        ),
                        "metadata": secure_token.metadata
                    })
            
            # Add database storage tokens
            query = select(SecureTokenStorage).where(
                SecureTokenStorage.user_id == user_id
            )
            
            if active_only:
                query = query.where(
                    and_(
                        SecureTokenStorage.is_active == True,
                        or_(
                            SecureTokenStorage.expires_at.is_(None),
                            SecureTokenStorage.expires_at > datetime.now(timezone.utc)
                        )
                    )
                )
            
            result = await session.execute(query)
            db_tokens = result.scalars().all()
            
            for db_token in db_tokens:
                # Skip if already in memory storage list
                if any(t["token_id"] == db_token.token_id for t in tokens):
                    continue
                
                tokens.append({
                    "token_id": db_token.token_id,
                    "token_type": db_token.token_type,
                    "storage_type": "secure_storage",
                    "session_id": db_token.session_id,
                    "device_fingerprint": db_token.device_fingerprint,
                    "created_at": db_token.created_at.isoformat(),
                    "expires_at": db_token.expires_at.isoformat() if db_token.expires_at else None,
                    "last_accessed_at": db_token.last_accessed_at.isoformat() if db_token.last_accessed_at else None,
                    "access_count": db_token.access_count,
                    "is_active": db_token.is_active,
                    "is_expired": (
                        db_token.expires_at and 
                        db_token.expires_at <= datetime.now(timezone.utc)
                    ),
                    "revoked_at": db_token.revoked_at.isoformat() if db_token.revoked_at else None,
                    "revocation_reason": db_token.revocation_reason,
                    "metadata": db_token.metadata or {}
                })
            
            return tokens
            
        except Exception as e:
            self.logger.error(f"Failed to get user tokens: {str(e)}")
            return []
    
    async def _encrypt_token(
        self,
        token_value: str,
        user_id: int,
        session_id: Optional[str] = None
    ) -> str:
        """Encrypt a token value."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        try:
            # Add additional entropy with user/session context
            context = f"{user_id}:{session_id or 'no_session'}"
            context_hash = hashlib.sha256(context.encode()).hexdigest()[:16]
            
            # Prepare data for encryption
            data_to_encrypt = {
                "token": token_value,
                "context": context_hash,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            json_data = json.dumps(data_to_encrypt).encode()
            
            # Encrypt with Fernet
            encrypted_data = self._fernet.encrypt(json_data)
            
            # Return base64 encoded encrypted data
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt token: {str(e)}")
            raise
    
    async def _decrypt_token(
        self,
        encrypted_value: str,
        user_id: int,
        session_id: Optional[str] = None
    ) -> str:
        """Decrypt a token value."""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")
        
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_value.encode())
            
            # Decrypt with Fernet
            decrypted_data = self._fernet.decrypt(encrypted_data)
            
            # Parse JSON
            data = json.loads(decrypted_data.decode())
            
            # Verify context
            expected_context = f"{user_id}:{session_id or 'no_session'}"
            expected_hash = hashlib.sha256(expected_context.encode()).hexdigest()[:16]
            
            if data.get("context") != expected_hash:
                raise ValueError("Token context mismatch")
            
            return data["token"]
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt token: {str(e)}")
            raise
    
    def generate_session_key(self, session_id: str, user_id: int) -> bytes:
        """Generate a unique encryption key for a session."""
        key_material = f"{session_id}:{user_id}:{secrets.token_hex(16)}"
        key_hash = hashlib.sha256(key_material.encode()).digest()
        
        self._session_keys[session_id] = key_hash
        return key_hash
    
    def get_session_key(self, session_id: str) -> Optional[bytes]:
        """Get the encryption key for a session."""
        return self._session_keys.get(session_id)
    
    def clear_session_key(self, session_id: str):
        """Clear the encryption key for a session."""
        if session_id in self._session_keys:
            del self._session_keys[session_id]


# Global secure token storage service instance
secure_token_storage = SecureTokenStorageService()