"""
Protocol Infrastructure Services

Core infrastructure for the three-layer communication protocol stack:
- Message routing and delivery
- Protocol layer management
- Authentication and authorization
- Message validation and semantic checking
- Connection management and monitoring
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel, ValidationError

from shared.schemas.protocol_schemas import (
    BaseProtocolMessage, ProtocolMessage, MessageIntent, MessagePriority, MessageStatus,
    ProtocolMetadata, MessageValidationResult, ProtocolError, ProtocolHealthCheck
)
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ================================
# Protocol Service Configuration
# ================================

class ProtocolConfig(BaseModel):
    """Configuration for protocol services."""
    # Redis configuration - use the working redis_url property instead of REDIS_URL
    redis_url: str = settings.redis_url
    redis_key_prefix: str = "protocol:"
    
    # Message routing
    routing_table_ttl: int = 3600  # seconds
    message_ttl: int = 86400  # 24 hours
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    
    # Performance settings
    max_concurrent_messages: int = 1000
    message_batch_size: int = 100
    connection_pool_size: int = 20
    
    # Security settings
    require_authentication: bool = True
    enable_message_encryption: bool = False
    max_retry_attempts: int = 3
    
    # Monitoring
    enable_metrics_collection: bool = True
    metrics_retention_days: int = 7
    health_check_interval: int = 30  # seconds


# ================================
# Protocol Message Router
# ================================

class MessageRouter:
    """Routes messages between protocol layers and services."""
    
    def __init__(self, redis_client: redis.Redis, config: ProtocolConfig):
        self.redis = redis_client
        self.config = config
        self.routing_table: Dict[str, Dict[str, Any]] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.active_sessions: Set[str] = set()
        
    async def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler for a specific message type."""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
        
    async def register_service(self, service_id: str, service_info: Dict[str, Any]) -> None:
        """Register a service in the routing table."""
        routing_key = f"{self.config.redis_key_prefix}routing:{service_id}"
        await self.redis.setex(
            routing_key,
            self.config.routing_table_ttl,
            json.dumps(service_info)
        )
        self.routing_table[service_id] = service_info
        logger.info(f"Registered service: {service_id}")
        
    async def route_message(self, message: BaseProtocolMessage) -> bool:
        """Route a message to its intended recipients."""
        try:
            # Validate message
            validation_result = await self._validate_message(message)
            if not validation_result.is_valid:
                logger.error(f"Message validation failed: {validation_result.validation_errors}")
                return False
                
            # Determine routing destinations
            destinations = await self._determine_destinations(message)
            if not destinations:
                logger.warning(f"No routing destinations found for message {message.metadata.message_id}")
                return False
                
            # Send message to destinations
            delivery_results = await asyncio.gather(
                *[self._deliver_message(dest, message) for dest in destinations],
                return_exceptions=True
            )
            
            # Check delivery results
            successful_deliveries = sum(1 for result in delivery_results if result is True)
            total_destinations = len(destinations)
            
            logger.info(f"Message {message.metadata.message_id} delivered to {successful_deliveries}/{total_destinations} destinations")
            return successful_deliveries > 0
            
        except Exception as e:
            logger.error(f"Error routing message {message.metadata.message_id}: {e}", exc_info=True)
            return False
            
    async def _validate_message(self, message: BaseProtocolMessage) -> MessageValidationResult:
        """Validate message structure and content."""
        errors = []
        warnings = []
        
        # Basic structure validation
        if not message.metadata.sender_id:
            errors.append("Missing sender_id in metadata")
            
        if not message.metadata.protocol_layer:
            errors.append("Missing protocol_layer in metadata")
            
        # Size validation
        message_size = len(json.dumps(message.dict()))
        if message_size > self.config.max_message_size:
            errors.append(f"Message size {message_size} exceeds limit {self.config.max_message_size}")
            
        # Authentication validation
        if self.config.require_authentication and not message.metadata.authentication_token:
            errors.append("Authentication token required but not provided")
            
        # Semantic validation
        semantic_score = await self._calculate_semantic_score(message)
        if semantic_score < 0.5:
            warnings.append(f"Low semantic score: {semantic_score}")
            
        return MessageValidationResult(
            is_valid=len(errors) == 0,
            validation_errors=errors,
            validation_warnings=warnings,
            semantic_score=semantic_score
        )
        
    async def _calculate_semantic_score(self, message: BaseProtocolMessage) -> float:
        """Calculate semantic coherence score for the message."""
        # Basic semantic scoring - can be enhanced with ML models
        score = 1.0
        
        # Check for required fields based on message intent
        if message.metadata.intent == MessageIntent.REQUEST:
            if not message.metadata.requires_response:
                score -= 0.1
                
        if message.metadata.intent == MessageIntent.INFORM:
            if not message.payload:
                score -= 0.2
                
        # Check ontology term usage
        if message.ontology_terms:
            score += 0.1
            
        return max(0.0, min(1.0, score))
        
    async def _determine_destinations(self, message: BaseProtocolMessage) -> List[str]:
        """Determine routing destinations for a message."""
        destinations = []
        
        # Direct recipients
        destinations.extend(message.metadata.recipients)
        
        # Protocol layer routing
        protocol_layer = message.metadata.protocol_layer
        layer_services = await self._get_layer_services(protocol_layer)
        destinations.extend(layer_services)
        
        # Intent-based routing
        intent_services = await self._get_intent_services(message.metadata.intent)
        destinations.extend(intent_services)
        
        # Domain-based routing
        if message.metadata.domain:
            domain_services = await self._get_domain_services(message.metadata.domain)
            destinations.extend(domain_services)
            
        return list(set(destinations))  # Remove duplicates
        
    async def _get_layer_services(self, protocol_layer: str) -> List[str]:
        """Get services registered for a specific protocol layer."""
        pattern = f"{self.config.redis_key_prefix}layer:{protocol_layer}:*"
        keys = await self.redis.keys(pattern)
        return [key.decode().split(':')[-1] for key in keys]
        
    async def _get_intent_services(self, intent: MessageIntent) -> List[str]:
        """Get services registered for a specific message intent."""
        pattern = f"{self.config.redis_key_prefix}intent:{intent.value}:*"
        keys = await self.redis.keys(pattern)
        return [key.decode().split(':')[-1] for key in keys]
        
    async def _get_domain_services(self, domain: str) -> List[str]:
        """Get services registered for a specific domain."""
        pattern = f"{self.config.redis_key_prefix}domain:{domain}:*"
        keys = await self.redis.keys(pattern)
        return [key.decode().split(':')[-1] for key in keys]
        
    async def _deliver_message(self, destination: str, message: BaseProtocolMessage) -> bool:
        """Deliver a message to a specific destination."""
        try:
            # Check if destination is a local handler
            if destination in self.message_handlers:
                handler = self.message_handlers[destination]
                await handler(message)
                return True
                
            # Send via Redis queue
            queue_key = f"{self.config.redis_key_prefix}queue:{destination}"
            message_data = json.dumps(message.dict())
            
            await self.redis.lpush(queue_key, message_data)
            await self.redis.expire(queue_key, self.config.message_ttl)
            
            logger.debug(f"Message delivered to queue: {queue_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver message to {destination}: {e}", exc_info=True)
            return False


# ================================
# Protocol Service Manager
# ================================

class ProtocolServiceManager:
    """Manages protocol services and their lifecycle."""
    
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.redis: Optional[redis.Redis] = None
        self.router: Optional[MessageRouter] = None
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self.metrics_collector: Optional['MetricsCollector'] = None
        
    async def initialize(self) -> None:
        """Initialize the protocol service manager."""
        try:
            # Initialize Redis connection using individual parameters for consistency
            redis_password = settings.REDIS_PASSWORD.get_secret_value() if settings.REDIS_PASSWORD else None
            self.redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                username=settings.REDIS_USER,
                password=redis_password,
                db=settings.REDIS_DB,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.config.connection_pool_size
            )
            await self.redis.ping()
            logger.info("Protocol service manager Redis connection established")
            
            # Initialize message router
            self.router = MessageRouter(self.redis, self.config)
            
            # Initialize metrics collector
            if self.config.enable_metrics_collection:
                self.metrics_collector = MetricsCollector(self.redis, self.config)
                await self.metrics_collector.initialize()
                
            # Start health check task
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("Protocol service manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize protocol service manager: {e}", exc_info=True)
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the protocol service manager."""
        try:
            # Cancel health check task
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
                    
            # Shutdown metrics collector
            if self.metrics_collector:
                await self.metrics_collector.shutdown()
                
            # Close Redis connection
            if self.redis:
                await self.redis.close()
                
            logger.info("Protocol service manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during protocol service manager shutdown: {e}", exc_info=True)
            
    async def register_service(self, service_id: str, service_config: Dict[str, Any]) -> None:
        """Register a new service with the protocol manager."""
        if not self.router:
            raise RuntimeError("Protocol service manager not initialized")
            
        await self.router.register_service(service_id, service_config)
        self.services[service_id] = service_config
        
    async def send_message(self, message: BaseProtocolMessage) -> bool:
        """Send a message through the protocol stack."""
        if not self.router:
            raise RuntimeError("Protocol service manager not initialized")
            
        # Add timestamp and message ID if not present
        if not message.metadata.message_id:
            message.metadata.message_id = str(uuid.uuid4())
        if not message.metadata.timestamp:
            message.metadata.timestamp = datetime.now(timezone.utc)
            
        # Record metrics
        if self.metrics_collector:
            await self.metrics_collector.record_message_sent(message)
            
        # Route the message
        result = await self.router.route_message(message)
        
        # Record delivery result
        if self.metrics_collector:
            await self.metrics_collector.record_message_delivered(message, result)
            
        return result
        
    async def _health_check_loop(self) -> None:
        """Periodic health check of protocol services."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered services."""
        if not self.redis:
            return
            
        for service_id, service_config in self.services.items():
            try:
                # Check service responsiveness
                health_check = ProtocolHealthCheck(
                    metadata=ProtocolMetadata(
                        sender_id="protocol_manager",
                        sender_type="service",
                        protocol_layer="protocol",
                        intent=MessageIntent.QUERY
                    ),
                    service_name=service_id,
                    service_version=service_config.get("version", "unknown"),
                    uptime_seconds=time.time() - service_config.get("start_time", time.time())
                )
                
                # Send health check
                await self.send_message(health_check)
                
            except Exception as e:
                logger.error(f"Health check failed for service {service_id}: {e}", exc_info=True)


# ================================
# Metrics Collection
# ================================

class MetricsCollector:
    """Collects and stores protocol metrics."""
    
    def __init__(self, redis_client: redis.Redis, config: ProtocolConfig):
        self.redis = redis_client
        self.config = config
        self.metrics_key_prefix = f"{config.redis_key_prefix}metrics:"
        
    async def initialize(self) -> None:
        """Initialize metrics collection."""
        await self._create_metrics_structure()
        logger.info("Metrics collector initialized")
        
    async def shutdown(self) -> None:
        """Shutdown metrics collection."""
        # Could implement final metrics export here
        logger.info("Metrics collector shutdown")
        
    async def record_message_sent(self, message: BaseProtocolMessage) -> None:
        """Record a message being sent."""
        timestamp = int(time.time())
        
        # Message count by type
        type_key = f"{self.metrics_key_prefix}sent:{message.message_type}:{timestamp // 60}"
        await self.redis.incr(type_key)
        await self.redis.expire(type_key, self.config.metrics_retention_days * 86400)
        
        # Message count by protocol layer
        layer_key = f"{self.metrics_key_prefix}layer:{message.metadata.protocol_layer}:{timestamp // 60}"
        await self.redis.incr(layer_key)
        await self.redis.expire(layer_key, self.config.metrics_retention_days * 86400)
        
        # Message count by intent
        intent_key = f"{self.metrics_key_prefix}intent:{message.metadata.intent.value}:{timestamp // 60}"
        await self.redis.incr(intent_key)
        await self.redis.expire(intent_key, self.config.metrics_retention_days * 86400)
        
    async def record_message_delivered(self, message: BaseProtocolMessage, success: bool) -> None:
        """Record message delivery result."""
        timestamp = int(time.time())
        
        # Delivery success rate
        result = "success" if success else "failure"
        delivery_key = f"{self.metrics_key_prefix}delivery:{result}:{timestamp // 60}"
        await self.redis.incr(delivery_key)
        await self.redis.expire(delivery_key, self.config.metrics_retention_days * 86400)
        
    async def get_metrics_summary(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for the specified time range."""
        now = int(time.time())
        start_minute = (now // 60) - time_range_minutes
        end_minute = now // 60
        
        metrics = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "delivery_failures": 0,
            "by_protocol_layer": {},
            "by_intent": {},
            "by_message_type": {}
        }
        
        # Aggregate metrics across time range
        for minute in range(start_minute, end_minute + 1):
            # Delivery metrics
            success_key = f"{self.metrics_key_prefix}delivery:success:{minute}"
            failure_key = f"{self.metrics_key_prefix}delivery:failure:{minute}"
            
            delivered = await self.redis.get(success_key) or "0"
            failed = await self.redis.get(failure_key) or "0"
            
            metrics["messages_delivered"] += int(delivered)
            metrics["delivery_failures"] += int(failed)
            
        return metrics
        
    async def _create_metrics_structure(self) -> None:
        """Create initial metrics data structure."""
        # Initialize metrics counters if needed
        pass


# ================================
# Protocol Authentication
# ================================

class ProtocolAuthenticator:
    """Handles authentication for protocol messages."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.token_cache: Dict[str, Dict[str, Any]] = {}
        
    async def authenticate_message(self, message: BaseProtocolMessage) -> bool:
        """Authenticate a protocol message."""
        token = message.metadata.authentication_token
        if not token:
            return False
            
        # Check token cache first
        if token in self.token_cache:
            token_info = self.token_cache[token]
            if token_info["expires_at"] > time.time():
                return True
            else:
                del self.token_cache[token]
                
        # Validate token (implement your token validation logic)
        token_info = await self._validate_token(token)
        if token_info:
            self.token_cache[token] = token_info
            return True
            
        return False
        
    async def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate an authentication token."""
        # Implementation depends on your authentication system
        # This is a placeholder that should integrate with your JWT validation
        try:
            # Check token in Redis or validate JWT
            token_key = f"auth:token:{token}"
            token_data = await self.redis.get(token_key)
            
            if token_data:
                token_info = json.loads(token_data)
                return {
                    "user_id": token_info.get("user_id"),
                    "permissions": token_info.get("permissions", []),
                    "expires_at": token_info.get("expires_at", time.time() + 3600)
                }
                
        except Exception as e:
            logger.error(f"Token validation error: {e}", exc_info=True)
            
        return None


# ================================
# Protocol Factory
# ================================

class ProtocolFactory:
    """Factory for creating protocol service instances."""
    
    @staticmethod
    async def create_service_manager(config: Optional[ProtocolConfig] = None) -> ProtocolServiceManager:
        """Create and initialize a protocol service manager."""
        if config is None:
            config = ProtocolConfig()
            
        manager = ProtocolServiceManager(config)
        await manager.initialize()
        return manager
        
    @staticmethod
    def create_message(
        message_type: str,
        protocol_layer: str,
        sender_id: str,
        intent: MessageIntent,
        payload: Dict[str, Any],
        **kwargs
    ) -> BaseProtocolMessage:
        """Create a protocol message with standard metadata."""
        metadata = ProtocolMetadata(
            sender_id=sender_id,
            sender_type=kwargs.get("sender_type", "service"),
            protocol_layer=protocol_layer,
            intent=intent,
            priority=kwargs.get("priority", MessagePriority.NORMAL),
            **{k: v for k, v in kwargs.items() if k in ProtocolMetadata.__fields__}
        )
        
        return BaseProtocolMessage(
            message_type=message_type,
            metadata=metadata,
            payload=payload,
            ontology_terms=kwargs.get("ontology_terms", []),
            semantic_tags=kwargs.get("semantic_tags", {})
        )