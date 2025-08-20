"""
OAuth Token Manager Service
Handles automatic token refresh, health checks, and lifecycle management for external service tokens.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

import httpx
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import UserOAuthToken, GoogleService
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class TokenHealth(Enum):
    """Token health status enumeration."""
    HEALTHY = "healthy"
    EXPIRES_SOON = "expires_soon" 
    EXPIRED = "expired"
    REFRESH_FAILED = "refresh_failed"
    NO_REFRESH_TOKEN = "no_refresh_token"


@dataclass
class TokenStatus:
    """Token status information."""
    health: TokenHealth
    expires_at: Optional[datetime]
    needs_refresh: bool
    error_message: Optional[str] = None


class CircuitBreakerState(Enum):
    """Circuit breaker states for external service calls."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class OAuthTokenManager:
    """
    Manages OAuth token lifecycle including automatic refresh, health monitoring,
    and circuit breaker patterns for external service integration.
    
    Features:
    - Proactive token refresh 5 minutes before expiry
    - Circuit breaker pattern for external service failures
    - Token health monitoring and status reporting
    - Atomic token updates to prevent race conditions
    - Exponential backoff for failed refresh attempts
    """
    
    # Class-level circuit breaker state tracking
    _circuit_breakers: Dict[str, Dict[str, Any]] = {}
    _token_refresh_locks: Dict[int, asyncio.Lock] = {}
    
    def __init__(self, db: Union[Session, AsyncSession]):
        self.db = db
        self.settings = get_settings()
        self.settings.load_google_oauth_from_secrets()
    
    async def get_healthy_token(
        self, 
        user_id: int, 
        service: GoogleService,
        auto_refresh: bool = True
    ) -> Optional[UserOAuthToken]:
        """
        Get a healthy, valid token for the specified service.
        Automatically refreshes if needed and auto_refresh is True.
        
        Args:
            user_id: User ID
            service: Google service enum
            auto_refresh: Whether to automatically refresh expiring tokens
            
        Returns:
            Valid UserOAuthToken or None if unavailable/unhealthy
        """
        # Get token from database
        token = await self._get_user_token(user_id, service)
        if not token:
            return None
        
        # Check token health
        status = self._check_token_health(token)
        
        # Return immediately if healthy
        if status.health == TokenHealth.HEALTHY:
            return token
        
        # Auto-refresh if enabled and needed
        if auto_refresh and status.needs_refresh:
            if status.health == TokenHealth.EXPIRES_SOON or status.health == TokenHealth.EXPIRED:
                refresh_success = await self.refresh_token(token)
                if refresh_success:
                    # Re-fetch updated token
                    return await self._get_user_token(user_id, service)
        
        # Return None if token is unhealthy and can't be refreshed
        if status.health in [TokenHealth.EXPIRED, TokenHealth.REFRESH_FAILED, TokenHealth.NO_REFRESH_TOKEN]:
            return None
            
        return token
    
    async def refresh_token(self, token: UserOAuthToken) -> bool:
        """
        Refresh an OAuth token with atomic updates and circuit breaker protection.
        
        Args:
            token: The token to refresh
            
        Returns:
            True if refresh succeeded, False otherwise
        """
        # Use per-user lock to prevent concurrent refresh attempts
        lock = await self._get_token_lock(token.user_id)
        
        async with lock:
            # Re-fetch token to avoid stale data
            fresh_token = await self._get_user_token(token.user_id, token.service)
            if not fresh_token:
                return False
            
            # Check if another process already refreshed this token
            if (fresh_token.updated_at and token.updated_at and 
                fresh_token.updated_at > token.updated_at):
                logger.info(f"Token already refreshed by another process for user {token.user_id}")
                return True
            
            # Check circuit breaker
            circuit_key = f"refresh_{token.service.value}"
            if not self._can_attempt_refresh(circuit_key):
                logger.warning(f"Circuit breaker open for {circuit_key}, skipping refresh")
                return False
            
            try:
                # Perform token refresh
                success = await self._perform_token_refresh(fresh_token)
                
                if success:
                    self._record_refresh_success(circuit_key)
                    logger.info(f"Successfully refreshed token for user {token.user_id}, service {token.service.value}")
                else:
                    self._record_refresh_failure(circuit_key)
                
                return success
                
            except Exception as e:
                self._record_refresh_failure(circuit_key)
                logger.error(f"Token refresh failed for user {token.user_id}: {e}", exc_info=True)
                return False
    
    async def check_all_user_tokens(self, user_id: int) -> Dict[str, TokenStatus]:
        """
        Check health status of all tokens for a user.
        
        Args:
            user_id: User ID to check tokens for
            
        Returns:
            Dictionary mapping service names to TokenStatus
        """
        user_tokens = await self._get_all_user_tokens(user_id)
        
        status_map = {}
        for token in user_tokens:
            service_name = token.service.value
            status = self._check_token_health(token)
            status_map[service_name] = status
        
        return status_map
    
    async def refresh_expiring_tokens(self, user_id: int) -> Dict[str, Any]:
        """
        Proactively refresh all tokens expiring within 5 minutes for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with refresh results
        """
        cutoff_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        if isinstance(self.db, AsyncSession):  # Async session
            result = await self.db.execute(
                select(UserOAuthToken).filter(
                    UserOAuthToken.user_id == user_id,
                    UserOAuthToken.refresh_token.isnot(None),
                    UserOAuthToken.token_expiry <= cutoff_time
                )
            )
            expiring_tokens = result.scalars().all()
        else:  # Sync session
            expiring_tokens = self.db.query(UserOAuthToken).filter(
                UserOAuthToken.user_id == user_id,
                UserOAuthToken.refresh_token.isnot(None),
                UserOAuthToken.token_expiry <= cutoff_time
            ).all()
        
        if not expiring_tokens:
            return {
                "status": "no_refresh_needed",
                "tokens_refreshed": 0,
                "errors": []
            }
        
        tokens_refreshed = 0
        errors = []
        
        for token in expiring_tokens:
            try:
                if await self.refresh_token(token):
                    tokens_refreshed += 1
                else:
                    errors.append(f"Failed to refresh {token.service.value} token")
            except Exception as e:
                errors.append(f"Error refreshing {token.service.value}: {str(e)}")
        
        return {
            "status": "completed",
            "tokens_refreshed": tokens_refreshed,
            "total_tokens": len(expiring_tokens),
            "errors": errors if errors else None
        }
    
    async def _get_user_token(self, user_id: int, service: GoogleService) -> Optional[UserOAuthToken]:
        """Get a specific token for a user and service."""
        if isinstance(self.db, AsyncSession):  # Async session
            result = await self.db.execute(
                select(UserOAuthToken).filter(
                    UserOAuthToken.user_id == user_id,
                    UserOAuthToken.service == service
                )
            )
            return result.scalars().first()
        else:  # Sync session
            return self.db.query(UserOAuthToken).filter(
                UserOAuthToken.user_id == user_id,
                UserOAuthToken.service == service
            ).first()
    
    async def _get_all_user_tokens(self, user_id: int) -> List[UserOAuthToken]:
        """Get all tokens for a user."""
        if isinstance(self.db, AsyncSession):  # Async session
            result = await self.db.execute(
                select(UserOAuthToken).filter(UserOAuthToken.user_id == user_id)
            )
            return result.scalars().all()
        else:  # Sync session
            return self.db.query(UserOAuthToken).filter(
                UserOAuthToken.user_id == user_id
            ).all()
    
    def _check_token_health(self, token: UserOAuthToken) -> TokenStatus:
        """Check the health status of a token."""
        if not token.refresh_token:
            return TokenStatus(
                health=TokenHealth.NO_REFRESH_TOKEN,
                expires_at=token.token_expiry,
                needs_refresh=False,
                error_message="No refresh token available"
            )
        
        now = datetime.now(timezone.utc)
        
        # Check if expired
        if token.token_expiry and token.token_expiry <= now:
            return TokenStatus(
                health=TokenHealth.EXPIRED,
                expires_at=token.token_expiry,
                needs_refresh=True,
                error_message="Token has expired"
            )
        
        # Check if expires soon (within 5 minutes)
        if token.token_expiry and token.token_expiry <= now + timedelta(minutes=5):
            return TokenStatus(
                health=TokenHealth.EXPIRES_SOON,
                expires_at=token.token_expiry,
                needs_refresh=True
            )
        
        # Token is healthy
        return TokenStatus(
            health=TokenHealth.HEALTHY,
            expires_at=token.token_expiry,
            needs_refresh=False
        )
    
    async def _perform_token_refresh(self, token: UserOAuthToken) -> bool:
        """Perform the actual token refresh API call."""
        if not self.settings.GOOGLE_CLIENT_ID or not self.settings.GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth configuration missing")
            return False
        
        if not token.refresh_token:
            logger.error(f"No refresh token available for user {token.user_id}")
            return False
        
        refresh_params = {
            "client_id": self.settings.GOOGLE_CLIENT_ID,
            "client_secret": self.settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            "refresh_token": token.refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data=refresh_params,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Update token atomically
                    expires_in = token_data.get("expires_in", 3600)
                    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    
                    if isinstance(self.db, AsyncSession):  # Async session
                        await self.db.execute(
                            update(UserOAuthToken)
                            .where(UserOAuthToken.id == token.id)
                            .values(
                                access_token=token_data["access_token"],
                                refresh_token=token_data.get("refresh_token", token.refresh_token),
                                token_expiry=new_expiry,
                                updated_at=datetime.now(timezone.utc)
                            )
                        )
                        await self.db.commit()
                    else:  # Sync session
                        token.access_token = token_data["access_token"]
                        if "refresh_token" in token_data:
                            token.refresh_token = token_data["refresh_token"]
                        token.token_expiry = new_expiry
                        token.updated_at = datetime.now(timezone.utc)
                        self.db.commit()
                    
                    return True
                else:
                    logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error("Token refresh timed out")
            return False
        except Exception as e:
            logger.error(f"Token refresh error: {e}", exc_info=True)
            return False
    
    async def _get_token_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a token refresh lock for a user."""
        if user_id not in self._token_refresh_locks:
            self._token_refresh_locks[user_id] = asyncio.Lock()
        return self._token_refresh_locks[user_id]
    
    def _can_attempt_refresh(self, circuit_key: str) -> bool:
        """Check if circuit breaker allows refresh attempt."""
        if circuit_key not in self._circuit_breakers:
            self._circuit_breakers[circuit_key] = {
                "state": CircuitBreakerState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "last_success": None
            }
        
        breaker = self._circuit_breakers[circuit_key]
        now = datetime.now(timezone.utc)
        
        if breaker["state"] == CircuitBreakerState.OPEN:
            # Check if cooldown period has passed (5 minutes)
            if (breaker["last_failure"] and 
                (now - breaker["last_failure"]).total_seconds() > 300):
                breaker["state"] = CircuitBreakerState.HALF_OPEN
                return True
            return False
        
        return True  # CLOSED or HALF_OPEN
    
    def _record_refresh_success(self, circuit_key: str):
        """Record successful token refresh for circuit breaker."""
        if circuit_key in self._circuit_breakers:
            self._circuit_breakers[circuit_key].update({
                "state": CircuitBreakerState.CLOSED,
                "failure_count": 0,
                "last_success": datetime.now(timezone.utc)
            })
    
    def _record_refresh_failure(self, circuit_key: str):
        """Record failed token refresh for circuit breaker."""
        if circuit_key not in self._circuit_breakers:
            self._circuit_breakers[circuit_key] = {
                "state": CircuitBreakerState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "last_success": None
            }
        
        breaker = self._circuit_breakers[circuit_key]
        breaker["failure_count"] += 1
        breaker["last_failure"] = datetime.now(timezone.utc)
        
        # Open circuit breaker after 3 consecutive failures
        if breaker["failure_count"] >= 3:
            breaker["state"] = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened for {circuit_key} after 3 failures")


# Global instance for dependency injection
oauth_token_manager_instance = None


def get_oauth_token_manager(db: Union[Session, AsyncSession]) -> OAuthTokenManager:
    """Get OAuth token manager instance for dependency injection."""
    return OAuthTokenManager(db)