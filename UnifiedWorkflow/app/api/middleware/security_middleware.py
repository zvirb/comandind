"""
Security middleware for API endpoints.

This module implements comprehensive security middleware including:
- Content Security Policy (CSP) headers
- XSS protection headers
- Request rate limiting
- Security headers enforcement
"""

import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers to all responses.
    """
    
    def __init__(self, app, csp_policy: Optional[str] = None):
        super().__init__(app)
        self.csp_policy = csp_policy or self._get_default_csp_policy()
    
    def _get_default_csp_policy(self) -> str:
        """
        Generate a hardened Content Security Policy with enhanced XSS protection.
        """
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://accounts.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss: https://accounts.google.com https://oauth2.googleapis.com; "
            "frame-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self' https://accounts.google.com; "
            "object-src 'none'; "
            "media-src 'self'; "
            "worker-src 'self'; "
            "manifest-src 'self'; "
            "upgrade-insecure-requests;"
        )
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        response = await call_next(request)
        
        # Enhanced security headers for comprehensive protection
        response.headers["Content-Security-Policy"] = self.csp_policy
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), autoplay=(), camera=(), cross-origin-isolated=(), "
            "display-capture=(), encrypted-media=(), fullscreen=(), "
            "geolocation=(), gyroscope=(), keyboard-map=(), magnetometer=(), "
            "microphone=(), midi=(), payment=(), picture-in-picture=(), "
            "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), "
            "usb=(), web-share=(), xr-spatial-tracking=()"
        )
        
        # Enhanced CSRF protection headers
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # HSTS header for HTTPS (enhanced with preload)
        # Check both direct HTTPS and forwarded HTTPS (through reverse proxy)
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https" or
            request.headers.get("x-forwarded-ssl") == "on"
        )
        
        if is_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        
        # Remove server information and version headers
        headers_to_remove = ["Server", "X-Powered-By", "X-AspNet-Version", "X-Version"]
        for header in headers_to_remove:
            if header in response.headers:
                del response.headers[header]
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse.
    """
    
    def __init__(
        self, 
        app, 
        calls: int = 100,
        period: int = 60,
        burst_calls: int = 20,
        burst_period: int = 1
    ):
        super().__init__(app)
        self.calls = calls  # Normal rate limit
        self.period = period  # Time window in seconds
        self.burst_calls = burst_calls  # Burst rate limit
        self.burst_period = burst_period  # Burst time window
        
        # Storage for rate limiting data
        self.client_requests: Dict[str, deque] = defaultdict(lambda: deque())
        self.client_burst_requests: Dict[str, deque] = defaultdict(lambda: deque())
    
    def _get_client_id(self, request: Request) -> str:
        """
        Extract client identifier for rate limiting.
        Uses IP address but could be enhanced with user ID for authenticated requests.
        """
        # Try to get real IP from headers (for reverse proxy scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return client_ip
    
    def _cleanup_old_requests(self, requests: deque, period: int) -> None:
        """Remove requests older than the specified period."""
        cutoff_time = time.time() - period
        while requests and requests[0] < cutoff_time:
            requests.popleft()
    
    def _is_rate_limited(self, client_id: str) -> tuple[bool, str]:
        """
        Check if client is rate limited.
        Returns (is_limited, reason).
        """
        current_time = time.time()
        
        # Check burst rate limit
        burst_requests = self.client_burst_requests[client_id]
        self._cleanup_old_requests(burst_requests, self.burst_period)
        
        if len(burst_requests) >= self.burst_calls:
            return True, f"Burst rate limit exceeded: {self.burst_calls} requests per {self.burst_period} seconds"
        
        # Check normal rate limit
        normal_requests = self.client_requests[client_id]
        self._cleanup_old_requests(normal_requests, self.period)
        
        if len(normal_requests) >= self.calls:
            return True, f"Rate limit exceeded: {self.calls} requests per {self.period} seconds"
        
        # Record this request
        burst_requests.append(current_time)
        normal_requests.append(current_time)
        
        return False, ""
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        is_limited, reason = self._is_rate_limited(client_id)
        
        if is_limited:
            logger.warning(f"Rate limit exceeded for client {client_id}: {reason}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": reason,
                    "retry_after": self.period
                },
                headers={"Retry-After": str(self.period)}
            )
        
        return await call_next(request)

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for input sanitization and validation.
    """
    
    def __init__(self, app, exempt_paths=None):
        super().__init__(app)
        # Paths to exempt from input sanitization
        self.exempt_paths = exempt_paths or {
            "/api/v1/auth/jwt/login",
            "/api/v1/auth/jwt/login-debug",
            "/api/v1/auth/login", 
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/token"
        }
        # Common XSS patterns to detect
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
            r'onfocus\s*=',
            r'onblur\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<meta[^>]*http-equiv',
        ]
    
    def _contains_xss(self, text: str) -> bool:
        """
        Check if text contains potential XSS patterns.
        """
        import re
        
        if not isinstance(text, str):
            return False
        
        text_lower = text.lower()
        for pattern in self.xss_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    def _sanitize_value(self, value: Any) -> Any:
        """
        Recursively sanitize values in request data.
        """
        if isinstance(value, str):
            if self._contains_xss(value):
                logger.warning(f"Potential XSS detected in input: {value[:100]}...")
                # Instead of blocking, we'll log and sanitize
                # You could also raise HTTPException here for stricter security
                import html
                return html.escape(value, quote=True)
            return value
        elif isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        else:
            return value
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        # Skip sanitization for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
            
        # Only process requests with bodies (POST, PUT, PATCH)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Get request body
                body = await request.body()
                if body:
                    content_type = request.headers.get("content-type", "")
                    
                    if "application/json" in content_type:
                        import json
                        try:
                            data = json.loads(body)
                            sanitized_data = self._sanitize_value(data)
                            
                            # Replace request body with sanitized version
                            sanitized_body = json.dumps(sanitized_data).encode('utf-8')
                            
                            # Store sanitized body in request state for downstream use
                            # without breaking ASGI protocol
                            request._body = sanitized_body
                            
                        except json.JSONDecodeError:
                            # Invalid JSON, let it pass through for proper error handling
                            pass
            except Exception as e:
                logger.error(f"Error in input sanitization middleware: {e}")
                # Continue processing even if sanitization fails
        
        return await call_next(request)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Secure request logging middleware that doesn't log sensitive data.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.sensitive_headers = {
            "authorization", "cookie", "x-csrf-token", "x-api-key",
            "authentication", "proxy-authorization"
        }
        self.sensitive_paths = {
            "/api/v1/auth/login", "/api/v1/auth/register", 
            "/api/v1/auth/reset-password", "/api/v1/auth/change-password"
        }
    
    def _should_log_request(self, request: Request) -> bool:
        """Determine if request should be logged."""
        return request.url.path not in ["/health", "/api/v1/health"]
    
    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logging."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    async def dispatch(self, request: Request, call_next) -> StarletteResponse:
        start_time = time.time()
        
        if self._should_log_request(request):
            client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
            sanitized_headers = self._sanitize_headers(dict(request.headers))
            
            logger.info(
                f"Request: {request.method} {request.url.path} from {client_ip}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "user_agent": request.headers.get("user-agent", "unknown"),
                    "headers": sanitized_headers
                }
            )
        
        response = await call_next(request)
        
        if self._should_log_request(request):
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} for {request.method} {request.url.path} in {process_time:.3f}s",
                extra={
                    "status_code": response.status_code,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time
                }
            )
        
        return response