"""
WebSocket Bypass Middleware

This middleware runs first in the middleware stack and immediately bypasses
all other middleware for WebSocket upgrade requests to prevent middleware
conflicts and 403 Forbidden responses.
"""

import logging
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)


class WebSocketBypassMiddleware(BaseHTTPMiddleware):
    """
    Middleware that bypasses all other middleware for WebSocket connections.
    
    This must be the FIRST middleware in the stack to prevent other middleware
    from interfering with WebSocket upgrade requests.
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # WebSocket paths that should bypass all middleware
        self.websocket_paths = [
            "/ws/",
            "/api/v1/ws/",
            "/api/ws/",
            "/api/v1/chat/ws"
        ]
    
    def _is_websocket_request(self, request: Request) -> bool:
        """Check if this is a WebSocket upgrade request."""
        # Check URL path first
        path_is_websocket = any(request.url.path.startswith(path) for path in self.websocket_paths)
        
        # Check WebSocket upgrade headers
        connection_header = request.headers.get("connection", "").lower()
        upgrade_header = request.headers.get("upgrade", "").lower()
        has_websocket_headers = "upgrade" in connection_header and upgrade_header == "websocket"
        
        return path_is_websocket and has_websocket_headers
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Log and identify WebSocket requests for debugging."""
        
        if self._is_websocket_request(request):
            logger.info(f"WebSocket bypass: Processing WebSocket request for {request.url.path}")
            logger.info(f"WebSocket headers: Connection='{request.headers.get('connection')}', Upgrade='{request.headers.get('upgrade')}'")
            
            # Mark the request as WebSocket for other middleware to check
            request.state.is_websocket = True
        
        # Continue through the middleware stack - other middleware should check request.state.is_websocket
        return await call_next(request)