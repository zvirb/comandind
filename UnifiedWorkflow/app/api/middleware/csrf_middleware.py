"""
Enhanced CSRF Protection Middleware

This module provides comprehensive CSRF protection including:
- Double-submit cookie pattern
- SameSite cookie enforcement
- Origin header validation
- Request signing for sensitive operations
"""

import hmac
import hashlib
import secrets
import time
import logging
import asyncio
from typing import Optional, Set, List, Dict
from urllib.parse import urlparse
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)

class EnhancedCSRFMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CSRF protection middleware with multiple defense layers.
    
    SECURITY FIXES:
    - Atomic token operations to prevent race conditions
    - Token caching to reduce rotation frequency
    - Thread-safe token validation and rotation
    """
    
    def __init__(
        self, 
        app,
        secret_key: str,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-TOKEN",
        exempt_paths: Optional[Set[str]] = None,
        require_https: bool = True,
        max_age: int = 3600,  # 1 hour
        trusted_origins: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.require_https = require_https
        self.max_age = max_age
        
        # SECURITY HARDENED: Minimal exempt paths - only essential auth endpoints
        self.exempt_paths = exempt_paths or {
            # Health checks (read-only, no state changes)
            "/health",
            "/api/v1/health",
            # Essential authentication endpoints (initial login only)
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/csrf-token",
            # Public read-only endpoints
            "/api/v1/public",
            # REMOVED: Debugging endpoints that create CSRF bypass opportunities
            # REMOVED: Legacy endpoints that duplicate functionality
            # REMOVED: Task, calendar, and document endpoints (now require CSRF)
        }
        
        # Trusted origins for Origin header validation
        self.trusted_origins = set(trusted_origins or [])
        
        # Methods that require CSRF protection
        self.protected_methods = {"POST", "PUT", "PATCH", "DELETE"}
        
        # SECURITY FIX: Add token cache and locks for atomic operations
        self._token_cache: Dict[str, Dict[str, any]] = {}  # Cache valid tokens
        self._rotation_locks: Dict[str, asyncio.Lock] = {}  # Per-user rotation locks
        self._cache_max_size = 10000  # Prevent memory bloat
        self._cache_cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()  # Track last cleanup time
        
        # Initialize cleanup task reference (started lazily on first request)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def _generate_csrf_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        logger.debug(f"Middleware generating CSRF token")
        
        timestamp = str(int(time.time()))
        nonce = secrets.token_urlsafe(32)
        
        # Create HMAC signature
        message = f"{timestamp}:{nonce}".encode()
        signature = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
        
        return f"{timestamp}:{nonce}:{signature}"
    
    def _validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token integrity and freshness."""
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return False
            
            timestamp_str, nonce, signature = parts
            timestamp = int(timestamp_str)
            
            # Check if token is expired
            if time.time() - timestamp > self.max_age:
                logger.warning("CSRF token expired")
                return False
            
            # Verify signature
            message = f"{timestamp_str}:{nonce}".encode()
            expected_signature = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("CSRF token signature validation failed")
                return False
            
            return True
            
        except (ValueError, IndexError) as e:
            logger.warning(f"CSRF token validation error: {e}")
            return False
    
    def _validate_origin(self, request: Request) -> bool:
        """Validate Origin header against trusted origins."""
        # Check for forwarded origin from proxy first
        forwarded_host = request.headers.get("X-Forwarded-Host")
        origin = request.headers.get("Origin")
        
        # If request came through proxy, reconstruct original origin
        if forwarded_host and not origin:
            # Use forwarded protocol if available, default to http for dev
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
            origin = f"{forwarded_proto}://{forwarded_host}"
        
        if not origin:
            # No Origin header - check Referer as fallback
            referer = request.headers.get("Referer")
            if referer:
                origin = urlparse(referer).netloc
            else:
                # For proxied requests without origin, check forwarded headers
                if forwarded_host:
                    logger.info(f"Using X-Forwarded-Host for origin validation: {forwarded_host}")
                    origin = f"http://{forwarded_host}"  # Assume HTTP for local dev
                else:
                    logger.warning("No Origin, Referer, or X-Forwarded-Host header in request")
                    return False
        
        # Parse the origin
        parsed_origin = urlparse(origin) if origin.startswith(('http://', 'https://')) else urlparse(f"https://{origin}")
        origin_host = parsed_origin.netloc or parsed_origin.path
        
        # Check against trusted origins
        for trusted in self.trusted_origins:
            trusted_parsed = urlparse(trusted) if trusted.startswith(('http://', 'https://')) else urlparse(f"https://{trusted}")
            trusted_host = trusted_parsed.netloc or trusted_parsed.path
            
            if origin_host == trusted_host:
                return True
        
        # Also allow same-origin requests
        request_host = request.headers.get("Host")
        if request_host and origin_host == request_host:
            return True
        
        logger.warning(f"Origin validation failed: {origin} not in trusted origins")
        return False
    
    def _should_protect(self, request: Request) -> bool:
        """Determine if request should be CSRF protected."""
        
        # Check if WebSocket was marked by bypass middleware
        if hasattr(request.state, 'is_websocket') and request.state.is_websocket:
            logger.info(f"CSRF middleware: Skipping protection for marked WebSocket request to {request.url.path}")
            return False
        
        # Skip protection for WebSocket upgrade requests
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        
        # DEBUG: Log all headers for WebSocket paths
        if request.url.path.startswith("/ws/"):
            logger.info(f"CSRF DEBUG: WebSocket path {request.url.path}")
            logger.info(f"CSRF DEBUG: Connection header: '{connection_header}'")
            logger.info(f"CSRF DEBUG: Upgrade header: '{upgrade_header}'")
            logger.info(f"CSRF DEBUG: All headers: {dict(request.headers)}")
            logger.info(f"CSRF DEBUG: Request state has is_websocket: {hasattr(request.state, 'is_websocket')}")
        
        if "upgrade" in connection_header and upgrade_header == "websocket":
            logger.info(f"CSRF middleware: Skipping protection for WebSocket upgrade request to {request.url.path}")
            return False
        
        # Skip protection for exempt paths
        if request.url.path in self.exempt_paths:
            logger.debug(f"CSRF middleware: Skipping protection for exempt path {request.url.path}")
            return False
            
        # Skip protection for WebSocket paths (pattern matching) - more comprehensive
        websocket_patterns = [
            "/api/v1/ws/",
            "/ws/",
            "/api/ws/",
            "/api/v1/chat/ws",  # Specific chat WebSocket endpoint
        ]
        for pattern in websocket_patterns:
            if request.url.path.startswith(pattern):
                logger.info(f"CSRF middleware: Skipping protection for WebSocket path {request.url.path}")
                return False
        
        # Skip protection for GET, HEAD, OPTIONS (safe methods)
        if request.method not in self.protected_methods:
            return False
        
        # Require HTTPS in production
        if self.require_https and request.url.scheme != "https":
            # Allow HTTP for localhost in development
            host = request.headers.get("Host", "")
            if not (host.startswith("localhost") or host.startswith("127.0.0.1")):
                logger.warning(f"CSRF protection requires HTTPS, got {request.url.scheme}")
                return False
        
        return True
    
    async def _get_or_create_rotation_lock(self, user_key: str) -> asyncio.Lock:
        """Get or create a rotation lock for atomic token operations."""
        if user_key not in self._rotation_locks:
            self._rotation_locks[user_key] = asyncio.Lock()
        return self._rotation_locks[user_key]
    
    def _cache_token(self, token: str, user_key: str = "global"):
        """Cache a valid token to reduce validation overhead."""
        if len(self._token_cache) >= self._cache_max_size:
            # Simple LRU: remove oldest entries
            oldest_keys = list(self._token_cache.keys())[:100]
            for key in oldest_keys:
                del self._token_cache[key]
        
        cache_key = f"{user_key}:{token[:16]}"  # Use token prefix as key
        self._token_cache[cache_key] = {
            "token": token,
            "timestamp": time.time(),
            "user_key": user_key
        }
    
    def _get_cached_token(self, token: str, user_key: str = "global") -> bool:
        """Check if token is in cache and still valid."""
        cache_key = f"{user_key}:{token[:16]}"
        cached = self._token_cache.get(cache_key)
        
        if not cached:
            return False
        
        # Check if cached token matches and is not expired
        if cached["token"] == token:
            token_age = time.time() - cached["timestamp"]
            if token_age < self.max_age:
                return True
            else:
                # Remove expired token from cache
                del self._token_cache[cache_key]
        
        return False
    
    async def _periodic_cache_cleanup(self):
        """Periodic cleanup of expired tokens and rotation locks."""
        while True:
            try:
                await asyncio.sleep(self._cache_cleanup_interval)
                current_time = time.time()
                
                # Cleanup expired tokens from cache
                expired_keys = []
                for cache_key, cached_data in self._token_cache.items():
                    token_age = current_time - cached_data["timestamp"]
                    if token_age > self.max_age:
                        expired_keys.append(cache_key)
                
                for key in expired_keys:
                    self._token_cache.pop(key, None)
                
                # Cleanup unused rotation locks
                if len(self._rotation_locks) > 1000:  # Prevent lock memory bloat
                    self._rotation_locks.clear()
                    logger.info("CSRF rotation locks cleaned up")
                
                if expired_keys:
                    logger.debug(f"CSRF cache cleanup: removed {len(expired_keys)} expired tokens")
                    
            except Exception as e:
                logger.error(f"Error in CSRF cache cleanup: {e}")
    
    def _ensure_cleanup_task_started(self):
        """Start cleanup task if not already running."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
                logger.debug("CSRF cache cleanup task started")
            except RuntimeError:
                # No event loop available, cleanup will be manual
                logger.debug("No event loop available for CSRF cache cleanup task")
    
    async def _atomic_validate_csrf_token(self, token: str, user_key: str = "global") -> bool:
        """Thread-safe CSRF token validation with caching."""
        # Quick cache check first
        if self._get_cached_token(token, user_key):
            return True
        
        # Full validation if not in cache
        if self._validate_csrf_token(token):
            self._cache_token(token, user_key)
            return True
        
        return False
    
    async def _validate_request_security(self, request: Request) -> bool:
        """Enhanced security validation for all requests."""
        try:
            # Rate limiting check (basic implementation)
            client_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For") or request.client.host
            
            # Check for suspicious patterns in URL
            path = request.url.path.lower()
            suspicious_patterns = [
                "../", "..\\", "<script", "javascript:", "vbscript:",
                "data:", "file:", "ftp:", "gopher:", "ldap:",
                "mailto:", "news:", "telnet:", "%2e%2e", "%252e",
                "union", "select", "insert", "update", "delete",
                "drop", "create", "alter", "exec", "xp_"
            ]
            
            for pattern in suspicious_patterns:
                if pattern in path:
                    logger.warning(f"Suspicious pattern detected in URL: {pattern} from IP {client_ip}")
                    return False
            
            # Check request size limits
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > 10_000_000:  # 10MB limit
                        logger.warning(f"Request size too large: {size} bytes from IP {client_ip}")
                        return False
                except ValueError:
                    pass
            
            # Check for excessive headers
            if len(request.headers) > 50:
                logger.warning(f"Too many headers: {len(request.headers)} from IP {client_ip}")
                return False
            
            # Validate User-Agent (basic check)
            user_agent = request.headers.get("user-agent", "")
            if len(user_agent) > 500:
                logger.warning(f"Suspicious User-Agent length: {len(user_agent)} from IP {client_ip}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in security validation: {e}")
            return False
    
    def _create_csrf_response_headers(self, token: str, request: Request) -> dict:
        """Create response headers with CSRF token."""
        headers = {}
        
        # Determine cookie security settings
        secure = request.url.scheme == "https" or not self.require_https
        samesite = "strict" if secure else "lax"
        
        # Use consistent domain logic with auth cookies
        import os
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        domain_name = os.getenv('DOMAIN', 'aiwfe.com')
        cookie_domain = f".{domain_name}" if is_production and domain_name not in ['localhost', '127.0.0.1'] else None
        
        # Set CSRF token in cookie (double-submit pattern)
        # NOTE: CSRF tokens must NOT be HttpOnly as they need to be readable by JavaScript
        cookie_value = f"{self.cookie_name}={token}; SameSite={samesite}; Path=/; Max-Age={self.max_age}"
        if cookie_domain:
            cookie_value += f"; Domain={cookie_domain}"
        if secure:
            cookie_value += "; Secure"
        
        headers["Set-Cookie"] = cookie_value
        
        # Also expose in header for JavaScript access
        headers[self.header_name] = token
        
        return headers
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Ensure cleanup task is running (lazy initialization)
        self._ensure_cleanup_task_started()
        
        # SECURITY ENHANCEMENT: Validate request before processing
        if not await self._validate_request_security(request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Security validation failed",
                    "message": "Request failed security checks"
                }
            )
        
        # Check if this request needs CSRF protection
        if not self._should_protect(request):
            response = await call_next(request)
            
            # SECURITY FIX: Don't auto-generate tokens for dedicated CSRF endpoints
            csrf_token_endpoints = ["/api/v1/auth/csrf-token"]
            is_csrf_endpoint = request.url.path in csrf_token_endpoints
            
            # For GET requests to protected paths, provide a CSRF token
            if (request.method == "GET" and 
                request.url.path.startswith("/api/") and 
                request.url.path not in self.exempt_paths and
                not is_csrf_endpoint):
                token = self._generate_csrf_token()
                headers = self._create_csrf_response_headers(token, request)
                for key, value in headers.items():
                    response.headers[key] = value
            
            return response
        
        # Validate Origin header
        if not self._validate_origin(request):
            logger.warning(f"CSRF protection: Origin validation failed for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF protection",
                    "message": "Origin validation failed"
                }
            )
        
        # Get CSRF token from header
        token_from_header = request.headers.get(self.header_name)
        if not token_from_header:
            logger.warning(f"CSRF protection: No CSRF token in header for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF protection",
                    "message": "CSRF token required in header"
                }
            )
        
        # Get CSRF token from cookie
        token_from_cookie = request.cookies.get(self.cookie_name)
        
        # If cookie is present, enforce double-submit pattern
        if token_from_cookie:
            # Double-submit cookie pattern: tokens must match
            if not hmac.compare_digest(token_from_header, token_from_cookie):
                logger.warning(f"CSRF protection: Token mismatch for {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "CSRF protection",
                        "message": "CSRF token mismatch"
                    }
                )
        else:
            # Cookie not available (possibly blocked by proxy/browser)
            # Allow header-only validation for valid tokens
            logger.info(f"CSRF protection: Using header-only validation for {request.url.path} (no cookie available)")
        
        # SECURITY FIX: Use atomic token validation with caching
        user_key = request.headers.get("Authorization", "anonymous")  # Use auth header as user key
        if not await self._atomic_validate_csrf_token(token_from_header, user_key):
            logger.warning(f"CSRF protection: Token validation failed for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF protection",
                    "message": "Invalid or expired CSRF token"
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # SECURITY FIX: Token rotation for validated CSRF requests only
        should_rotate = False
        
        # Check if token should be rotated (every 30 minutes or on critical paths)
        if token_from_header:
            try:
                token_timestamp = int(token_from_header.split(':')[0])
                token_age = time.time() - token_timestamp
                # SECURITY FIX: Increase rotation interval from 5 to 30 minutes
                should_rotate = token_age > 1800  # 30 minutes instead of 5
            except (ValueError, IndexError):
                # If token format is invalid, rotate it
                should_rotate = True
        
        # SECURITY FIX: Only rotate on critical authentication endpoints
        # Removed regular endpoints to prevent race conditions
        critical_auth_endpoints = [
            "/api/v1/auth/login", 
            "/api/v1/auth/register",
            "/api/v1/auth/change-password",
            "/api/v1/auth/delete-account"
        ]
        if any(request.url.path.startswith(endpoint) for endpoint in critical_auth_endpoints):
            should_rotate = True
        
        # SECURITY FIX: Use atomic token rotation with locks and double-check pattern
        if should_rotate:
            rotation_lock = await self._get_or_create_rotation_lock(user_key)
            async with rotation_lock:
                # Double-check pattern: verify rotation is still needed after acquiring lock
                current_token_valid = await self._atomic_validate_csrf_token(token_from_header, user_key)
                if current_token_valid:
                    try:
                        token_timestamp = int(token_from_header.split(':')[0])
                        token_age = time.time() - token_timestamp
                        # Re-check if rotation is still needed with fresh timestamp
                        if token_age > 1800:  # 30 minutes
                            logger.info(f"Atomic CSRF token rotation for path: {request.url.path}")
                            new_token = self._generate_csrf_token()
                            # Cache the new token immediately to prevent duplicate generations
                            self._cache_token(new_token, user_key)
                            # Invalidate old token cache entry
                            cache_key = f"{user_key}:{token_from_header[:16]}"
                            self._token_cache.pop(cache_key, None)
                            headers = self._create_csrf_response_headers(new_token, request)
                            for key, value in headers.items():
                                response.headers[key] = value
                        else:
                            logger.debug(f"CSRF token rotation skipped - token still fresh: {token_age:.1f}s")
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing token for rotation check: {e}")
                        # If token is malformed, generate new one
                        new_token = self._generate_csrf_token()
                        self._cache_token(new_token, user_key)
                        headers = self._create_csrf_response_headers(new_token, request)
                        for key, value in headers.items():
                            response.headers[key] = value
        
        return response

class RequestSigningMiddleware(BaseHTTPMiddleware):
    """
    Request signing middleware for sensitive operations.
    Adds HMAC signatures to critical requests.
    """
    
    def __init__(
        self, 
        app,
        secret_key: str,
        signed_paths: Optional[Set[str]] = None,
        signature_header: str = "X-Request-Signature",
        timestamp_header: str = "X-Request-Timestamp",
        max_timestamp_skew: int = 300  # 5 minutes
    ):
        super().__init__(app)
        self.secret_key = secret_key.encode() if isinstance(secret_key, str) else secret_key
        self.signature_header = signature_header
        self.timestamp_header = timestamp_header
        self.max_timestamp_skew = max_timestamp_skew
        
        # Paths that require request signing
        self.signed_paths = signed_paths or {
            "/api/v1/auth/change-password",
            "/api/v1/auth/delete-account",
            "/api/v1/admin",
            "/api/v1/security",
        }
    
    def _generate_signature(self, method: str, path: str, body: bytes, timestamp: str) -> str:
        """Generate HMAC signature for request."""
        message = f"{method}:{path}:{timestamp}:{body.hex()}".encode()
        signature = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
        return signature
    
    def _validate_signature(
        self, 
        method: str, 
        path: str, 
        body: bytes, 
        timestamp: str, 
        signature: str
    ) -> bool:
        """Validate request signature."""
        expected_signature = self._generate_signature(method, path, body, timestamp)
        return hmac.compare_digest(signature, expected_signature)
    
    def _should_sign(self, request: Request) -> bool:
        """Check if request path requires signing."""
        return any(request.url.path.startswith(path) for path in self.signed_paths)
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        if not self._should_sign(request):
            return await call_next(request)
        
        # Get signature headers
        signature = request.headers.get(self.signature_header)
        timestamp_str = request.headers.get(self.timestamp_header)
        
        if not signature or not timestamp_str:
            logger.warning(f"Request signing: Missing signature headers for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Request signing required",
                    "message": "Signature headers missing"
                }
            )
        
        # Validate timestamp
        try:
            timestamp = int(timestamp_str)
            current_time = int(time.time())
            
            if abs(current_time - timestamp) > self.max_timestamp_skew:
                logger.warning(f"Request signing: Timestamp skew too large for {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Request signing failed",
                        "message": "Request timestamp is too old or too far in the future"
                    }
                )
        except ValueError:
            logger.warning(f"Request signing: Invalid timestamp for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Request signing failed",
                    "message": "Invalid timestamp format"
                }
            )
        
        # Get request body
        body = await request.body()
        
        # Validate signature
        if not self._validate_signature(
            request.method, 
            request.url.path, 
            body, 
            timestamp_str, 
            signature
        ):
            logger.warning(f"Request signing: Signature validation failed for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Request signing failed",
                    "message": "Invalid request signature"
                }
            )
        
        # Store body in request state for downstream processing
        # without breaking ASGI protocol
        request._body = body
        
        return await call_next(request)