"""Cognitive Event Handler for integration with reasoning-service and learning feedback.

This module handles cognitive events from other services, processes them for workflow 
coordination, and provides learning feedback to improve agent orchestration.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

import aiohttp
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


class EventType(str, Enum):
    """Types of cognitive events processed by the coordination service."""
    REASONING_COMPLETE = "reasoning_complete"
    VALIDATION_COMPLETE = "validation_complete"
    LEARNING_UPDATE = "learning_update"
    MEMORY_STORED = "memory_stored"
    PERCEPTION_ANALYSIS = "perception_analysis"
    AGENT_STATUS_CHANGE = "agent_status_change"
    WORKFLOW_STATE_CHANGE = "workflow_state_change"
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR_REPORT = "error_report"


class EventPriority(str, Enum):
    """Event processing priorities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CognitiveEvent:
    """Represents a cognitive event for processing."""
    event_id: str
    event_type: EventType
    source_service: str
    workflow_id: Optional[str] = None
    agent_name: Optional[str] = None
    priority: EventPriority = EventPriority.MEDIUM
    event_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    requires_response: bool = False
    processed: bool = False
    processing_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_service": self.source_service,
            "workflow_id": self.workflow_id,
            "agent_name": self.agent_name,
            "priority": self.priority,
            "event_data": self.event_data,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "requires_response": self.requires_response,
            "processed": self.processed,
            "processing_result": self.processing_result
        }


@dataclass
class EventHandler:
    """Handler configuration for specific event types."""
    event_type: EventType
    handler_func: Callable
    priority_override: Optional[EventPriority] = None
    requires_workflow: bool = False
    max_processing_time: int = 30  # seconds
    retry_attempts: int = 2


class CognitiveEventHandler:
    """Handles cognitive events from other services and provides learning feedback."""
    
    def __init__(
        self,
        redis_service,
        reasoning_service_url: str,
        learning_service_url: str,
        event_processing_interval: int = 5,
        max_concurrent_events: int = 20
    ):
        self.redis_service = redis_service
        self.reasoning_service_url = reasoning_service_url.rstrip("/")
        self.learning_service_url = learning_service_url.rstrip("/")
        self.event_processing_interval = event_processing_interval
        self.max_concurrent_events = max_concurrent_events
        
        # Event processing state
        self._event_queue = asyncio.Queue(maxsize=1000)
        self._processing_running = False
        self._event_handlers: Dict[EventType, EventHandler] = {}
        
        # HTTP session for external calls
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # Event processing metrics
        self.event_metrics = {
            "total_events": 0,
            "processed_events": 0,
            "failed_events": 0,
            "avg_processing_time": 0.0,
            "events_by_type": {},
            "events_by_source": {},
            "learning_feedback_sent": 0
        }
        
        # Workflow impact tracking
        self._workflow_impacts: Dict[str, List[Dict[str, Any]]] = {}
    
    async def initialize(self) -> None:
        """Initialize the cognitive event handler."""
        logger.info("Initializing Cognitive Event Handler...")
        
        # Initialize HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self._http_session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        # Register event handlers
        await self._register_event_handlers()
        
        # Subscribe to cognitive events from Redis
        if self.redis_service:
            asyncio.create_task(self._subscribe_to_cognitive_events())
        
        logger.info("Cognitive Event Handler initialized")
    
    async def process_cognitive_event(
        self,
        event_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single cognitive event."""
        try:
            # Create event object
            event = CognitiveEvent(
                event_id=event_id,
                event_type=EventType(event_data["event_type"]),
                source_service=event_data["source_service"],
                workflow_id=event_data.get("workflow_id"),
                agent_name=event_data.get("agent_name"),
                priority=EventPriority(event_data.get("priority", "medium")),
                event_data=event_data.get("event_data", {}),
                timestamp=event_data.get("timestamp", time.time()),
                correlation_id=event_data.get("correlation_id"),
                requires_response=event_data.get("requires_response", False)
            )
            
            # Queue event for processing
            await self._event_queue.put(event)
            
            # Update metrics
            self.event_metrics["total_events"] += 1
            self.event_metrics["events_by_type"][event.event_type] = (
                self.event_metrics["events_by_type"].get(event.event_type, 0) + 1
            )
            self.event_metrics["events_by_source"][event.source_service] = (
                self.event_metrics["events_by_source"].get(event.source_service, 0) + 1
            )
            
            logger.info(
                "Cognitive event queued for processing",
                event_id=event_id,
                event_type=event.event_type,
                source_service=event.source_service
            )
            
            return {
                "processed": True,
                "event_id": event_id,
                "queued_for_processing": True
            }
            
        except Exception as e:
            logger.error("Failed to process cognitive event", event_id=event_id, error=str(e))
            return {
                "processed": False,
                "error": str(e)
            }
    
    async def publish_workflow_event(
        self,
        workflow_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Publish workflow-related event to other services."""
        try:
            event_message = {
                "event_type": f"workflow_{event_type}",
                "source_service": "coordination_service",
                "workflow_id": workflow_id,
                "event_data": event_data,
                "timestamp": time.time()
            }
            
            # Publish to Redis cognitive events channel
            if self.redis_service:
                published = await self.redis_service.publish_cognitive_event(
                    event_type=f"workflow_{event_type}",
                    event_data=event_message,
                    channel="cognitive_events"
                )
                
                if published:
                    logger.info(
                        "Published workflow event",
                        workflow_id=workflow_id,
                        event_type=event_type
                    )
                
                return published
            
            return False
            
        except Exception as e:
            logger.error(
                "Failed to publish workflow event",
                workflow_id=workflow_id,
                event_type=event_type,
                error=str(e)
            )
            return False
    
    async def run_event_processing(self) -> None:
        """Main event processing loop."""
        if self._processing_running:
            logger.warning("Event processing already running")
            return
        
        self._processing_running = True
        logger.info("Starting cognitive event processing loop")
        
        try:
            while self._processing_running:
                try:
                    # Process events with concurrency control
                    processing_tasks = []
                    
                    # Get events up to concurrency limit
                    for _ in range(min(self.max_concurrent_events, self._event_queue.qsize())):
                        if not self._event_queue.empty():
                            try:
                                event = self._event_queue.get_nowait()
                                task = asyncio.create_task(self._process_single_event(event))
                                processing_tasks.append(task)
                            except asyncio.QueueEmpty:
                                break
                    
                    # Process events concurrently
                    if processing_tasks:
                        await asyncio.gather(*processing_tasks, return_exceptions=True)
                    
                    # Brief pause if no events
                    if not processing_tasks:
                        await asyncio.sleep(self.event_processing_interval)
                    
                except Exception as e:
                    logger.error("Error in event processing loop", error=str(e))
                    await asyncio.sleep(5)
                    
        except asyncio.CancelledError:
            logger.info("Event processing loop cancelled")
        except Exception as e:
            logger.error("Event processing loop failed", error=str(e))
        finally:
            self._processing_running = False
            logger.info("Event processing loop stopped")
    
    async def send_learning_feedback(
        self,
        workflow_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any],
        agent_performance: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send learning feedback to learning service."""
        try:
            if not self._http_session:
                logger.warning("HTTP session not available for learning feedback")
                return False
            
            feedback_payload = {
                "workflow_id": workflow_id,
                "feedback_type": feedback_type,
                "feedback_data": feedback_data,
                "source_service": "coordination_service",
                "timestamp": time.time(),
                "agent_performance": agent_performance or {}
            }
            
            url = f"{self.learning_service_url}/feedback/coordination"
            
            async with self._http_session.post(url, json=feedback_payload) as response:
                if response.status in [200, 201, 202]:
                    self.event_metrics["learning_feedback_sent"] += 1
                    
                    logger.info(
                        "Learning feedback sent successfully",
                        workflow_id=workflow_id,
                        feedback_type=feedback_type
                    )
                    return True
                else:
                    logger.warning(
                        "Learning feedback request failed",
                        workflow_id=workflow_id,
                        status=response.status
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Failed to send learning feedback",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status of the cognitive event handler."""
        processing_rate = (
            self.event_metrics["processed_events"] / self.event_metrics["total_events"]
            if self.event_metrics["total_events"] > 0 else 0
        )
        
        return {
            "processing_status": "running" if self._processing_running else "stopped",
            "queue_size": self._event_queue.qsize(),
            "max_concurrent_events": self.max_concurrent_events,
            "registered_handlers": len(self._event_handlers),
            "metrics": {
                **self.event_metrics,
                "processing_rate": processing_rate,
                "error_rate": (
                    self.event_metrics["failed_events"] / self.event_metrics["total_events"]
                    if self.event_metrics["total_events"] > 0 else 0
                )
            },
            "workflow_impacts": len(self._workflow_impacts),
            "service_urls": {
                "reasoning_service": self.reasoning_service_url,
                "learning_service": self.learning_service_url
            }
        }
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the cognitive event handler."""
        logger.info("Shutting down Cognitive Event Handler...")
        
        try:
            # Stop processing
            self._processing_running = False
            
            # Process remaining events (with timeout)
            remaining_events = []
            try:
                while not self._event_queue.empty():
                    event = self._event_queue.get_nowait()
                    remaining_events.append(event)
            except asyncio.QueueEmpty:
                pass
            
            if remaining_events:
                logger.info(f"Processing {len(remaining_events)} remaining events...")
                processing_tasks = [
                    asyncio.create_task(self._process_single_event(event))
                    for event in remaining_events[:10]  # Limit to prevent hanging
                ]
                
                if processing_tasks:
                    await asyncio.wait_for(
                        asyncio.gather(*processing_tasks, return_exceptions=True),
                        timeout=30
                    )
            
            # Close HTTP session
            if self._http_session:
                await self._http_session.close()
            
            logger.info("Cognitive Event Handler shutdown complete")
            
        except Exception as e:
            logger.error("Error during Cognitive Event Handler shutdown", error=str(e))
    
    # Private helper methods
    
    async def _register_event_handlers(self) -> None:
        """Register handlers for different event types."""
        # Reasoning completion handler
        self._event_handlers[EventType.REASONING_COMPLETE] = EventHandler(
            event_type=EventType.REASONING_COMPLETE,
            handler_func=self._handle_reasoning_complete,
            priority_override=EventPriority.HIGH,
            requires_workflow=True,
            max_processing_time=15
        )
        
        # Validation completion handler
        self._event_handlers[EventType.VALIDATION_COMPLETE] = EventHandler(
            event_type=EventType.VALIDATION_COMPLETE,
            handler_func=self._handle_validation_complete,
            priority_override=EventPriority.HIGH,
            requires_workflow=True,
            max_processing_time=10
        )
        
        # Learning update handler
        self._event_handlers[EventType.LEARNING_UPDATE] = EventHandler(
            event_type=EventType.LEARNING_UPDATE,
            handler_func=self._handle_learning_update,
            priority_override=EventPriority.MEDIUM,
            requires_workflow=False,
            max_processing_time=20
        )
        
        # Agent status change handler
        self._event_handlers[EventType.AGENT_STATUS_CHANGE] = EventHandler(
            event_type=EventType.AGENT_STATUS_CHANGE,
            handler_func=self._handle_agent_status_change,
            priority_override=EventPriority.MEDIUM,
            requires_workflow=False,
            max_processing_time=5
        )
        
        # Error report handler
        self._event_handlers[EventType.ERROR_REPORT] = EventHandler(
            event_type=EventType.ERROR_REPORT,
            handler_func=self._handle_error_report,
            priority_override=EventPriority.CRITICAL,
            requires_workflow=False,
            max_processing_time=10
        )
        
        logger.info("Event handlers registered", handler_count=len(self._event_handlers))
    
    async def _subscribe_to_cognitive_events(self) -> None:
        """Subscribe to cognitive events from Redis."""
        try:
            logger.info("Subscribing to cognitive events from Redis")
            
            async def event_callback(event_data: Dict[str, Any]) -> None:
                """Process incoming cognitive event from Redis."""
                try:
                    event_id = str(uuid.uuid4())
                    await self.process_cognitive_event(event_id, event_data)
                    
                except Exception as e:
                    logger.error("Failed to process Redis cognitive event", error=str(e))
            
            # Subscribe to cognitive events channel
            await self.redis_service.subscribe_to_cognitive_events(
                callback=event_callback,
                channels=["cognitive_events"]
            )
            
        except Exception as e:
            logger.error("Failed to subscribe to cognitive events", error=str(e))
    
    async def _process_single_event(self, event: CognitiveEvent) -> None:
        """Process a single cognitive event."""
        start_time = time.time()
        
        try:
            logger.debug(
                "Processing cognitive event",
                event_id=event.event_id,
                event_type=event.event_type,
                source_service=event.source_service
            )
            
            # Get handler for event type
            handler = self._event_handlers.get(event.event_type)
            if not handler:
                logger.warning(
                    "No handler for event type",
                    event_type=event.event_type,
                    event_id=event.event_id
                )
                event.processed = True
                event.processing_result = {"status": "no_handler"}
                return
            
            # Check workflow requirement
            if handler.requires_workflow and not event.workflow_id:
                logger.warning(
                    "Event requires workflow ID but none provided",
                    event_type=event.event_type,
                    event_id=event.event_id
                )
                event.processed = True
                event.processing_result = {"status": "missing_workflow_id"}
                return
            
            # Process event with timeout
            try:
                result = await asyncio.wait_for(
                    handler.handler_func(event),
                    timeout=handler.max_processing_time
                )
                
                event.processed = True
                event.processing_result = result
                
                # Track workflow impact if applicable
                if event.workflow_id:
                    if event.workflow_id not in self._workflow_impacts:
                        self._workflow_impacts[event.workflow_id] = []
                    
                    self._workflow_impacts[event.workflow_id].append({
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "result": result
                    })
                
                self.event_metrics["processed_events"] += 1
                
            except asyncio.TimeoutError:
                logger.warning(
                    "Event processing timeout",
                    event_id=event.event_id,
                    timeout=handler.max_processing_time
                )
                event.processed = True
                event.processing_result = {"status": "timeout"}
                self.event_metrics["failed_events"] += 1
            
        except Exception as e:
            logger.error(
                "Error processing cognitive event",
                event_id=event.event_id,
                error=str(e)
            )
            event.processed = True
            event.processing_result = {"status": "error", "error": str(e)}
            self.event_metrics["failed_events"] += 1
        
        finally:
            # Update processing time metric
            processing_time = time.time() - start_time
            total_processed = self.event_metrics["processed_events"] + self.event_metrics["failed_events"]
            
            if total_processed > 0:
                self.event_metrics["avg_processing_time"] = (
                    (self.event_metrics["avg_processing_time"] * (total_processed - 1) + processing_time) /
                    total_processed
                )
    
    # Event handler implementations
    
    async def _handle_reasoning_complete(self, event: CognitiveEvent) -> Dict[str, Any]:
        """Handle reasoning completion events from reasoning service."""
        try:
            event_data = event.event_data
            confidence_score = event_data.get("confidence_score", 0.0)
            reasoning_type = event_data.get("reasoning_type", "unknown")
            
            logger.info(
                "Processing reasoning completion",
                workflow_id=event.workflow_id,
                reasoning_type=reasoning_type,
                confidence_score=confidence_score
            )
            
            # Send learning feedback based on reasoning quality
            feedback_data = {
                "reasoning_type": reasoning_type,
                "confidence_score": confidence_score,
                "processing_time": event_data.get("processing_time_ms", 0),
                "evidence_count": event_data.get("evidence_count", 0)
            }
            
            await self.send_learning_feedback(
                workflow_id=event.workflow_id,
                feedback_type="reasoning_performance",
                feedback_data=feedback_data
            )
            
            return {
                "status": "processed",
                "action": "learning_feedback_sent",
                "confidence_score": confidence_score
            }
            
        except Exception as e:
            logger.error("Failed to handle reasoning complete event", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def _handle_validation_complete(self, event: CognitiveEvent) -> Dict[str, Any]:
        """Handle validation completion events."""
        try:
            event_data = event.event_data
            validity_score = event_data.get("validity_score", 0.0)
            meets_threshold = event_data.get("meets_threshold", False)
            
            logger.info(
                "Processing validation completion",
                workflow_id=event.workflow_id,
                validity_score=validity_score,
                meets_threshold=meets_threshold
            )
            
            # Send workflow impact feedback
            impact_data = {
                "validation_passed": meets_threshold,
                "validity_score": validity_score,
                "validation_criteria": event_data.get("validation_criteria", [])
            }
            
            await self.send_learning_feedback(
                workflow_id=event.workflow_id,
                feedback_type="validation_impact",
                feedback_data=impact_data
            )
            
            return {
                "status": "processed",
                "validation_passed": meets_threshold,
                "validity_score": validity_score
            }
            
        except Exception as e:
            logger.error("Failed to handle validation complete event", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def _handle_learning_update(self, event: CognitiveEvent) -> Dict[str, Any]:
        """Handle learning updates from learning service."""
        try:
            event_data = event.event_data
            update_type = event_data.get("update_type", "unknown")
            
            logger.info(
                "Processing learning update",
                update_type=update_type,
                source=event.source_service
            )
            
            # Process learning insights for workflow optimization
            if update_type == "workflow_optimization":
                # Apply optimizations (implementation would depend on specific insights)
                logger.info("Received workflow optimization insights")
            
            return {
                "status": "processed",
                "update_type": update_type,
                "action": "insights_applied"
            }
            
        except Exception as e:
            logger.error("Failed to handle learning update", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def _handle_agent_status_change(self, event: CognitiveEvent) -> Dict[str, Any]:
        """Handle agent status change events."""
        try:
            event_data = event.event_data
            agent_name = event.agent_name
            new_status = event_data.get("new_status", "unknown")
            
            logger.info(
                "Processing agent status change",
                agent_name=agent_name,
                new_status=new_status
            )
            
            # Update agent registry would happen here
            # (This would integrate with the AgentRegistry instance)
            
            return {
                "status": "processed",
                "agent_name": agent_name,
                "new_status": new_status
            }
            
        except Exception as e:
            logger.error("Failed to handle agent status change", error=str(e))
            return {"status": "error", "error": str(e)}
    
    async def _handle_error_report(self, event: CognitiveEvent) -> Dict[str, Any]:
        """Handle error reports from services."""
        try:
            event_data = event.event_data
            error_type = event_data.get("error_type", "unknown")
            severity = event_data.get("severity", "medium")
            
            logger.warning(
                "Processing error report",
                source_service=event.source_service,
                error_type=error_type,
                severity=severity
            )
            
            # Send error impact feedback for learning
            error_feedback = {
                "error_type": error_type,
                "severity": severity,
                "source_service": event.source_service,
                "error_details": event_data.get("error_details", {})
            }
            
            if event.workflow_id:
                await self.send_learning_feedback(
                    workflow_id=event.workflow_id,
                    feedback_type="error_impact",
                    feedback_data=error_feedback
                )
            
            return {
                "status": "processed",
                "error_type": error_type,
                "severity": severity,
                "action": "error_logged"
            }
            
        except Exception as e:
            logger.error("Failed to handle error report", error=str(e))
            return {"status": "error", "error": str(e)}