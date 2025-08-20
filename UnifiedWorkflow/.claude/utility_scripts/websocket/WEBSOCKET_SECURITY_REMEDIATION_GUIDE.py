#!/usr/bin/env python3
"""
WebSocket Security Remediation Implementation Guide
==================================================

This module provides concrete security implementations to address the vulnerabilities
identified in the WebSocket Authentication Security Validation Report.

Security Validator: Implementation guidance for immediate security improvements
Date: 2025-08-07
Priority: CRITICAL

IMPLEMENTATION INSTRUCTIONS:
1. Review each security control implementation
2. Integrate into existing WebSocket router and connection manager
3. Test thoroughly before production deployment
4. Monitor and tune rate limiting parameters as needed
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
from fastapi import WebSocket, Request, HTTPException, status
import ipaddress

logger = logging.getLogger(__name__)

class WebSocketSecurityEnforcer:
    """
    Enhanced security enforcement for WebSocket connections.
    
    Implements missing security controls identified in security validation:
    - Origin header validation
    - Connection rate limiting
    - Message rate limiting
    - Security monitoring and alerting
    """
    
    def __init__(
        self,
        allowed_origins: Set[str] = None,
        max_connections_per_ip: int = 10,
        connection_window_seconds: int = 60,
        max_messages_per_session: int = 60,
        message_window_seconds: int = 60
    ):
        # Origin validation configuration
        self.allowed_origins = allowed_origins or {
            "https://yourdomain.com",
            "https://localhost",
            "https://127.0.0.1"
        }
        
        # Connection rate limiting configuration
        self.max_connections_per_ip = max_connections_per_ip
        self.connection_window_seconds = connection_window_seconds
        self.connection_attempts: Dict[str, List[float]] = defaultdict(list)
        
        # Message rate limiting configuration
        self.max_messages_per_session = max_messages_per_session
        self.message_window_seconds = message_window_seconds
        self.message_counts: Dict[str, List[float]] = defaultdict(list)
        
        # Security monitoring
        self.blocked_attempts = 0
        self.origin_violations = 0
        self.rate_limit_violations = 0
    
    def validate_origin(self, websocket: WebSocket) -> bool:
        """
        Validate WebSocket Origin header to prevent CSRF attacks.
        
        SECURITY CONTROL: Origin Header Validation
        OWASP Reference: WebSocket Security Cheat Sheet
        Risk Mitigated: Cross-Site WebSocket Hijacking (CSWSH)
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            bool: True if origin is allowed, False otherwise
        """
        try:
            origin = websocket.headers.get("origin")
            
            if not origin:
                # No origin header - this could be a direct connection
                # In production, consider whether to allow or block this
                logger.warning("WebSocket connection attempt without Origin header")
                return False
            
            # Normalize origin for comparison
            origin = origin.lower().rstrip('/')
            
            # Check against allowed origins
            for allowed_origin in self.allowed_origins:
                if origin == allowed_origin.lower().rstrip('/'):
                    logger.debug(f"Origin validation passed: {origin}")
                    return True
            
            # Log security violation
            logger.warning(f"Origin validation failed: {origin}")
            self.origin_violations += 1
            return False
            
        except Exception as e:
            logger.error(f"Error validating origin: {e}")
            return False
    
    def check_connection_rate_limit(self, client_ip: str) -> bool:
        """
        Check if client IP has exceeded connection rate limits.
        
        SECURITY CONTROL: Connection Rate Limiting
        Risk Mitigated: WebSocket Connection Flooding, Resource Exhaustion
        
        Args:
            client_ip: Client IP address
            
        Returns:
            bool: True if within rate limit, False if exceeded
        """
        try:
            now = time.time()
            client_attempts = self.connection_attempts[client_ip]
            
            # Remove attempts outside the time window
            cutoff_time = now - self.connection_window_seconds
            client_attempts[:] = [attempt_time for attempt_time in client_attempts 
                                if attempt_time > cutoff_time]
            
            # Check if rate limit exceeded
            if len(client_attempts) >= self.max_connections_per_ip:
                logger.warning(
                    f"Connection rate limit exceeded for IP {client_ip}: "
                    f"{len(client_attempts)} attempts in {self.connection_window_seconds}s"
                )
                self.rate_limit_violations += 1
                return False
            
            # Record this attempt
            client_attempts.append(now)
            
            logger.debug(
                f"Connection rate check passed for IP {client_ip}: "
                f"{len(client_attempts)}/{self.max_connections_per_ip}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error checking connection rate limit: {e}")
            return False
    
    def check_message_rate_limit(self, session_id: str) -> bool:
        """
        Check if session has exceeded message rate limits.
        
        SECURITY CONTROL: Message Rate Limiting
        Risk Mitigated: Message Flooding, Resource Exhaustion
        
        Args:
            session_id: WebSocket session identifier
            
        Returns:
            bool: True if within rate limit, False if exceeded
        """
        try:
            now = time.time()
            session_messages = self.message_counts[session_id]
            
            # Remove messages outside the time window
            cutoff_time = now - self.message_window_seconds
            session_messages[:] = [msg_time for msg_time in session_messages 
                                 if msg_time > cutoff_time]
            
            # Check if rate limit exceeded
            if len(session_messages) >= self.max_messages_per_session:
                logger.warning(
                    f"Message rate limit exceeded for session {session_id}: "
                    f"{len(session_messages)} messages in {self.message_window_seconds}s"
                )
                self.rate_limit_violations += 1
                return False
            
            # Record this message
            session_messages.append(now)
            
            logger.debug(
                f"Message rate check passed for session {session_id}: "
                f"{len(session_messages)}/{self.max_messages_per_session}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error checking message rate limit: {e}")
            return False
    
    def get_client_ip(self, websocket: WebSocket) -> str:
        """
        Extract client IP address from WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            str: Client IP address
        """
        try:
            # Check for forwarded headers (reverse proxy scenarios)
            forwarded_for = websocket.headers.get("x-forwarded-for")
            if forwarded_for:
                # Take the first IP in the chain
                return forwarded_for.split(',')[0].strip()
            
            # Check for real IP header
            real_ip = websocket.headers.get("x-real-ip")
            if real_ip:
                return real_ip.strip()
            
            # Fall back to direct client IP
            if hasattr(websocket, 'client') and websocket.client:
                return websocket.client.host
            
            # Default fallback
            return "unknown"
            
        except Exception as e:
            logger.error(f"Error extracting client IP: {e}")
            return "unknown"
    
    def is_trusted_network(self, client_ip: str) -> bool:
        """
        Check if client IP is from a trusted network.
        
        This can be used to apply different security policies
        for internal vs external connections.
        
        Args:
            client_ip: Client IP address
            
        Returns:
            bool: True if from trusted network
        """
        try:
            if client_ip == "unknown":
                return False
            
            ip = ipaddress.ip_address(client_ip)
            
            # Define trusted networks
            trusted_networks = [
                ipaddress.ip_network("10.0.0.0/8"),      # Private network
                ipaddress.ip_network("172.16.0.0/12"),   # Private network
                ipaddress.ip_network("192.168.0.0/16"),  # Private network
                ipaddress.ip_network("127.0.0.0/8"),     # Loopback
            ]
            
            for network in trusted_networks:
                if ip in network:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking trusted network status for {client_ip}: {e}")
            return False
    
    def validate_websocket_connection(self, websocket: WebSocket) -> Dict[str, any]:
        """
        Comprehensive WebSocket connection validation.
        
        This is the main entry point for WebSocket security validation.
        Call this method before accepting any WebSocket connection.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            dict: Validation result with status and details
        """
        validation_result = {
            "allowed": True,
            "reason": "Connection allowed",
            "client_ip": None,
            "origin": None,
            "trusted": False,
            "security_score": 100
        }
        
        try:
            # Extract client information
            client_ip = self.get_client_ip(websocket)
            origin = websocket.headers.get("origin", "")
            is_trusted = self.is_trusted_network(client_ip)
            
            validation_result.update({
                "client_ip": client_ip,
                "origin": origin,
                "trusted": is_trusted
            })
            
            # 1. Validate Origin header
            if not self.validate_origin(websocket):
                validation_result.update({
                    "allowed": False,
                    "reason": "Invalid or missing Origin header",
                    "security_score": 0
                })
                self.blocked_attempts += 1
                return validation_result
            
            # 2. Check connection rate limits (more lenient for trusted networks)
            max_connections = (self.max_connections_per_ip * 2) if is_trusted else self.max_connections_per_ip
            
            # Temporarily override rate limit for trusted networks
            if is_trusted:
                original_limit = self.max_connections_per_ip
                self.max_connections_per_ip = max_connections
            
            if not self.check_connection_rate_limit(client_ip):
                validation_result.update({
                    "allowed": False,
                    "reason": f"Connection rate limit exceeded for IP {client_ip}",
                    "security_score": 20
                })
                self.blocked_attempts += 1
                
                if is_trusted:
                    self.max_connections_per_ip = original_limit
                return validation_result
            
            if is_trusted:
                self.max_connections_per_ip = original_limit
            
            # Connection passed all security checks
            validation_result["security_score"] = 90 if is_trusted else 75
            
            logger.info(
                f"WebSocket connection security validation passed - "
                f"IP: {client_ip}, Origin: {origin}, Trusted: {is_trusted}"
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection validation: {e}")
            validation_result.update({
                "allowed": False,
                "reason": f"Security validation error: {str(e)}",
                "security_score": 0
            })
            return validation_result
    
    def validate_websocket_message(self, session_id: str, message_data: dict) -> bool:
        """
        Validate incoming WebSocket message for security compliance.
        
        Args:
            session_id: WebSocket session identifier
            message_data: Parsed message data
            
        Returns:
            bool: True if message is allowed, False if blocked
        """
        try:
            # 1. Check message rate limits
            if not self.check_message_rate_limit(session_id):
                return False
            
            # 2. Validate message structure (basic checks)
            if not isinstance(message_data, dict):
                logger.warning(f"Invalid message format from session {session_id}")
                return False
            
            # 3. Check for suspicious message types
            message_type = message_data.get("type", "")
            suspicious_types = {"admin_override", "system_command", "debug_mode"}
            
            if message_type in suspicious_types:
                logger.warning(
                    f"Suspicious message type '{message_type}' from session {session_id}"
                )
                return False
            
            # 4. Message validation passed
            return True
            
        except Exception as e:
            logger.error(f"Error validating WebSocket message: {e}")
            return False
    
    def get_security_metrics(self) -> Dict[str, any]:
        """
        Get current security metrics for monitoring.
        
        Returns:
            dict: Security metrics and statistics
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "blocked_attempts": self.blocked_attempts,
            "origin_violations": self.origin_violations,
            "rate_limit_violations": self.rate_limit_violations,
            "active_connections": len(self.connection_attempts),
            "active_sessions": len(self.message_counts),
            "configuration": {
                "max_connections_per_ip": self.max_connections_per_ip,
                "connection_window_seconds": self.connection_window_seconds,
                "max_messages_per_session": self.max_messages_per_session,
                "message_window_seconds": self.message_window_seconds,
                "allowed_origins_count": len(self.allowed_origins)
            }
        }

# INTEGRATION EXAMPLE: How to integrate with existing WebSocket router

def integrate_security_into_websocket_router():
    """
    Example integration of security controls into existing WebSocket router.
    
    This demonstrates how to modify the existing websocket_router.py to include
    the new security controls.
    """
    
    # Initialize security enforcer (do this once at module level)
    security_enforcer = WebSocketSecurityEnforcer(
        allowed_origins={
            "https://yourdomain.com",
            "https://localhost",
            "https://127.0.0.1:5173"  # Dev server
        },
        max_connections_per_ip=10,
        max_messages_per_session=60
    )
    
    # Modified WebSocket endpoint with security
    async def secure_websocket_agent_endpoint(websocket, session_id, current_user):
        """
        Enhanced WebSocket endpoint with comprehensive security validation.
        
        This replaces the existing websocket_agent_endpoint with security controls.
        """
        
        # 1. Validate connection security BEFORE accepting WebSocket
        validation = security_enforcer.validate_websocket_connection(websocket)
        
        if not validation["allowed"]:
            logger.warning(
                f"WebSocket connection blocked: {validation['reason']} "
                f"(IP: {validation['client_ip']}, Origin: {validation['origin']})"
            )
            await websocket.close(code=1008, reason=validation["reason"])
            return
        
        # 2. Accept WebSocket connection (security validated)
        await websocket.accept()
        
        # 3. Use enhanced connection tracking
        await progress_manager.connect(websocket, current_user.id, session_id, token)
        
        logger.info(
            f"Secure WebSocket connected - Session: {session_id}, User: {current_user.id}, "
            f"IP: {validation['client_ip']}, Score: {validation['security_score']}"
        )
        
        try:
            while True:
                # 4. Handle incoming messages with security validation
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    
                    # 5. Validate message security
                    if not security_enforcer.validate_websocket_message(session_id, message):
                        logger.warning(f"Message blocked from session {session_id}")
                        await websocket.send_json({
                            "type": "security_error",
                            "message": "Message rate limit exceeded or invalid format"
                        })
                        continue
                    
                    # 6. Process message (existing logic)
                    message_type = message.get("type")
                    
                    if message_type == "token_refresh_response":
                        # Handle token refresh (existing logic)
                        new_token = message.get("token")
                        if new_token:
                            success = await progress_manager.handle_token_refresh_response(
                                session_id, new_token
                            )
                            if success:
                                logger.info(f"Token successfully refreshed for session {session_id}")
                    
                    # ... rest of existing message handling ...
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from session {session_id}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except WebSocketDisconnect:
            logger.info(f"Secure WebSocket disconnected: session {session_id}")
            progress_manager.disconnect(session_id)

# CONFIGURATION EXAMPLE: Production security configuration

PRODUCTION_SECURITY_CONFIG = {
    "allowed_origins": {
        "https://yourdomain.com",
        "https://app.yourdomain.com",
        "https://api.yourdomain.com"
    },
    "max_connections_per_ip": 5,        # Stricter in production
    "connection_window_seconds": 60,
    "max_messages_per_session": 30,     # Stricter message limits
    "message_window_seconds": 60,
}

DEVELOPMENT_SECURITY_CONFIG = {
    "allowed_origins": {
        "https://localhost",
        "https://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    },
    "max_connections_per_ip": 20,       # More lenient for dev
    "connection_window_seconds": 60,
    "max_messages_per_session": 100,    # More lenient for dev/testing
    "message_window_seconds": 60,
}

# MONITORING EXAMPLE: Security metrics endpoint

async def get_websocket_security_metrics(security_enforcer: WebSocketSecurityEnforcer):
    """
    Endpoint to expose WebSocket security metrics for monitoring.
    
    Add this to your monitoring router to track security events.
    """
    return security_enforcer.get_security_metrics()

if __name__ == "__main__":
    # Example usage and testing
    import asyncio
    from unittest.mock import Mock
    
    async def test_security_enforcer():
        """Test the security enforcer functionality."""
        
        enforcer = WebSocketSecurityEnforcer(
            allowed_origins={"https://localhost"},
            max_connections_per_ip=3,
            max_messages_per_session=5
        )
        
        # Mock WebSocket connection
        mock_websocket = Mock()
        mock_websocket.headers = {
            "origin": "https://localhost",
            "x-forwarded-for": "192.168.1.100"
        }
        
        # Test connection validation
        validation = enforcer.validate_websocket_connection(mock_websocket)
        print(f"Connection validation: {validation}")
        
        # Test rate limiting
        for i in range(10):
            result = enforcer.check_connection_rate_limit("192.168.1.100")
            print(f"Connection attempt {i+1}: {'Allowed' if result else 'Blocked'}")
        
        # Get security metrics
        metrics = enforcer.get_security_metrics()
        print(f"Security metrics: {metrics}")
    
    # Run test
    asyncio.run(test_security_enforcer())