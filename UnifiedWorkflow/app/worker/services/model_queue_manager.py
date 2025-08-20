"""
Model Queue Manager - Advanced queue management for model availability and request optimization
Provides intelligent queuing, priority management, and batch processing for model requests.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import heapq

from worker.services.model_resource_manager import model_resource_manager, ModelCategory

logger = logging.getLogger(__name__)


class RequestPriority(int, Enum):
    """Priority levels for model requests."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ModelRequest:
    """Represents a queued model request."""
    request_id: str
    expert_id: str
    model_name: str
    user_id: str
    session_id: str
    priority: RequestPriority
    created_at: datetime
    estimated_duration_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Priority queue comparison (higher priority first)."""
        return self.priority.value > other.priority.value


@dataclass
class QueueStats:
    """Statistics for model queue performance."""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    average_wait_time_seconds: float = 0.0
    average_processing_time_seconds: float = 0.0
    queue_length: int = 0
    active_executions: int = 0


class ModelQueueManager:
    """
    Advanced queue management system for model requests.
    Provides intelligent batching, priority handling, and resource optimization.
    """
    
    def __init__(self):
        self.request_queues: Dict[ModelCategory, List[ModelRequest]] = {
            category: [] for category in ModelCategory
        }
        self.active_requests: Dict[str, ModelRequest] = {}
        self.completed_requests: List[ModelRequest] = []
        self.request_futures: Dict[str, asyncio.Future] = {}
        
        self.stats = QueueStats()
        self._queue_lock = asyncio.Lock()
        self._processing_task: Optional[asyncio.Task] = None
        self._queue_check_interval = 1.0  # Check queue every second
        
        # Queue optimization settings
        self.max_queue_size_per_category = 50
        self.max_wait_time_minutes = 15
        self.batch_processing_enabled = True
        self.adaptive_priority_adjustment = True
    
    async def start_queue_processing(self):
        """Start the background queue processing task."""
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._queue_processing_loop())
            logger.info("Started model queue processing")
    
    async def stop_queue_processing(self):
        """Stop the background queue processing task."""
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped model queue processing")
    
    async def enqueue_request(
        self,
        expert_id: str,
        model_name: str,
        user_id: str,
        session_id: str,
        priority: RequestPriority = RequestPriority.NORMAL,
        estimated_duration: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enqueue a model request for processing.
        
        Args:
            expert_id: Expert identifier
            model_name: Model to use
            user_id: User making the request
            session_id: Session identifier
            priority: Request priority
            estimated_duration: Estimated processing time in seconds
            metadata: Additional request metadata
            
        Returns:
            Request ID for tracking
        """
        request_id = f"{session_id}_{expert_id}_{datetime.now().timestamp()}"
        
        # Get model category for queue assignment
        model_info = model_resource_manager.get_model_info(model_name)
        if not model_info:
            raise ValueError(f"Unknown model: {model_name}")
        
        category = model_info.category
        
        # Create request
        request = ModelRequest(
            request_id=request_id,
            expert_id=expert_id,
            model_name=model_name,
            user_id=user_id,
            session_id=session_id,
            priority=priority,
            created_at=datetime.now(timezone.utc),
            estimated_duration_seconds=estimated_duration,
            metadata=metadata or {}
        )
        
        async with self._queue_lock:
            # Check queue capacity
            if len(self.request_queues[category]) >= self.max_queue_size_per_category:
                # Remove oldest low-priority request if queue is full
                if not self._remove_low_priority_request(category):
                    raise Exception(f"Queue full for {category.value} models")
            
            # Add to priority queue
            heapq.heappush(self.request_queues[category], request)
            self.stats.total_requests += 1
            self.stats.queue_length += 1
            
            # Create future for result tracking
            future = asyncio.Future()
            self.request_futures[request_id] = future
            
            logger.info(f"Enqueued request {request_id} for {expert_id} with {model_name} (priority: {priority.name})")
            
            return request_id
    
    def _remove_low_priority_request(self, category: ModelCategory) -> bool:
        """Remove the lowest priority request from a queue."""
        queue = self.request_queues[category]
        if not queue:
            return False
        
        # Find lowest priority request
        min_priority_idx = 0
        min_priority = queue[0].priority
        
        for i, request in enumerate(queue):
            if request.priority < min_priority:
                min_priority = request.priority
                min_priority_idx = i
        
        # Remove the request
        removed_request = queue.pop(min_priority_idx)
        heapq.heapify(queue)  # Re-heapify after removal
        
        # Cancel the future
        if removed_request.request_id in self.request_futures:
            future = self.request_futures.pop(removed_request.request_id)
            if not future.done():
                future.set_exception(Exception("Request removed due to queue capacity"))
        
        logger.info(f"Removed low-priority request {removed_request.request_id} due to queue capacity")
        return True
    
    async def get_request_result(self, request_id: str, timeout: float = 300.0) -> Any:
        """
        Wait for a request to complete and return the result.
        
        Args:
            request_id: Request identifier
            timeout: Maximum wait time in seconds
            
        Returns:
            Request result
        """
        if request_id not in self.request_futures:
            raise ValueError(f"Unknown request ID: {request_id}")
        
        future = self.request_futures[request_id]
        
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            # Cancel the request if it times out
            await self.cancel_request(request_id)
            raise Exception(f"Request {request_id} timed out after {timeout} seconds")
    
    async def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a queued or active request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            True if request was cancelled, False if not found or already completed
        """
        async with self._queue_lock:
            # Check if request is active
            if request_id in self.active_requests:
                request = self.active_requests.pop(request_id)
                logger.info(f"Cancelled active request {request_id}")
                
                # Release resource slot
                await model_resource_manager.release_execution_slot(request.model_name, request.expert_id)
                
                # Mark future as cancelled
                if request_id in self.request_futures:
                    future = self.request_futures.pop(request_id)
                    if not future.done():
                        future.set_exception(asyncio.CancelledError("Request cancelled"))
                
                return True
            
            # Check queues for the request
            for category, queue in self.request_queues.items():
                for i, request in enumerate(queue):
                    if request.request_id == request_id:
                        # Remove from queue
                        queue.pop(i)
                        heapq.heapify(queue)
                        self.stats.queue_length -= 1
                        
                        # Mark future as cancelled
                        if request_id in self.request_futures:
                            future = self.request_futures.pop(request_id)
                            if not future.done():
                                future.set_exception(asyncio.CancelledError("Request cancelled"))
                        
                        logger.info(f"Cancelled queued request {request_id}")
                        return True
            
            return False
    
    async def _queue_processing_loop(self):
        """Main queue processing loop."""
        while True:
            try:
                await asyncio.sleep(self._queue_check_interval)
                await self._process_queues()
                await self._cleanup_expired_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}", exc_info=True)
    
    async def _process_queues(self):
        """Process all category queues for available requests."""
        async with self._queue_lock:
            for category in ModelCategory:
                queue = self.request_queues[category]
                if not queue:
                    continue
                
                # Process requests that can be executed
                while queue:
                    request = queue[0]  # Peek at highest priority
                    
                    # Check if we can execute this request
                    can_execute, reason = await model_resource_manager.check_execution_availability(request.model_name)
                    
                    if can_execute:
                        # Reserve slot and start execution
                        if await model_resource_manager.reserve_execution_slot(request.model_name, request.expert_id):
                            # Remove from queue and start processing
                            heapq.heappop(queue)
                            self.stats.queue_length -= 1
                            
                            # Move to active requests
                            self.active_requests[request.request_id] = request
                            self.stats.active_executions += 1
                            
                            # Start processing
                            asyncio.create_task(self._process_request(request))
                            
                            logger.info(f"Started processing request {request.request_id}")
                        else:
                            # Could not reserve slot, stop processing this category
                            break
                    else:
                        # Cannot execute, stop processing this category
                        logger.debug(f"Cannot execute {request.request_id}: {reason}")
                        break
    
    async def _process_request(self, request: ModelRequest):
        """Process a single request."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Simulate request processing (replace with actual execution logic)
            logger.info(f"Processing request {request.request_id} for {request.expert_id}")
            
            # This would be replaced with actual expert execution
            await asyncio.sleep(0.1)  # Minimal delay for simulation
            
            # Mock result
            result = {
                "request_id": request.request_id,
                "expert_id": request.expert_id,
                "model_name": request.model_name,
                "response": f"Processed by {request.expert_id} using {request.model_name}",
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
            
            # Complete the request
            if request.request_id in self.request_futures:
                future = self.request_futures.pop(request.request_id)
                if not future.done():
                    future.set_result(result)
            
            # Update stats
            self.stats.completed_requests += 1
            wait_time = (start_time - request.created_at).total_seconds()
            self._update_average_wait_time(wait_time)
            
            logger.info(f"Completed request {request.request_id}")
            
        except Exception as e:
            logger.error(f"Error processing request {request.request_id}: {e}")
            
            # Mark as failed
            if request.request_id in self.request_futures:
                future = self.request_futures.pop(request.request_id)
                if not future.done():
                    future.set_exception(e)
            
            self.stats.failed_requests += 1
            
        finally:
            # Clean up
            async with self._queue_lock:
                self.active_requests.pop(request.request_id, None)
                self.stats.active_executions -= 1
            
            # Release resource slot
            await model_resource_manager.release_execution_slot(request.model_name, request.expert_id)
            
            # Move to completed requests (keep history)
            self.completed_requests.append(request)
            
            # Limit completed requests history
            if len(self.completed_requests) > 1000:
                self.completed_requests = self.completed_requests[-500:]
    
    async def _cleanup_expired_requests(self):
        """Remove requests that have been waiting too long."""
        current_time = datetime.now(timezone.utc)
        max_wait = timedelta(minutes=self.max_wait_time_minutes)
        
        expired_requests = []
        
        async with self._queue_lock:
            for category, queue in self.request_queues.items():
                # Find expired requests
                for i, request in enumerate(queue):
                    if current_time - request.created_at > max_wait:
                        expired_requests.append((category, i, request))
            
            # Remove expired requests (in reverse order to maintain indices)
            for category, index, request in reversed(expired_requests):
                queue = self.request_queues[category]
                queue.pop(index)
                heapq.heapify(queue)
                self.stats.queue_length -= 1
                
                # Cancel future
                if request.request_id in self.request_futures:
                    future = self.request_futures.pop(request.request_id)
                    if not future.done():
                        future.set_exception(Exception(f"Request expired after {self.max_wait_time_minutes} minutes"))
                
                logger.warning(f"Expired request {request.request_id} after {self.max_wait_time_minutes} minutes")
    
    def _update_average_wait_time(self, wait_time: float):
        """Update the running average wait time."""
        if self.stats.completed_requests == 1:
            self.stats.average_wait_time_seconds = wait_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.stats.average_wait_time_seconds = (
                alpha * wait_time + (1 - alpha) * self.stats.average_wait_time_seconds
            )
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        async with self._queue_lock:
            queue_lengths = {
                category.value: len(queue) 
                for category, queue in self.request_queues.items()
            }
            
            return {
                "queue_lengths": queue_lengths,
                "total_queue_length": sum(queue_lengths.values()),
                "active_executions": len(self.active_requests),
                "stats": {
                    "total_requests": self.stats.total_requests,
                    "completed_requests": self.stats.completed_requests,
                    "failed_requests": self.stats.failed_requests,
                    "success_rate": (
                        self.stats.completed_requests / max(1, self.stats.total_requests) * 100
                    ),
                    "average_wait_time_seconds": self.stats.average_wait_time_seconds,
                    "queue_length": self.stats.queue_length,
                    "active_executions": self.stats.active_executions
                },
                "settings": {
                    "max_queue_size_per_category": self.max_queue_size_per_category,
                    "max_wait_time_minutes": self.max_wait_time_minutes,
                    "batch_processing_enabled": self.batch_processing_enabled,
                    "queue_check_interval": self._queue_check_interval
                }
            }
    
    async def optimize_queue_settings(self):
        """Automatically optimize queue settings based on performance."""
        if self.adaptive_priority_adjustment and self.stats.completed_requests > 10:
            # Adjust queue check interval based on load
            if self.stats.average_wait_time_seconds > 60:
                # High wait times, check more frequently
                self._queue_check_interval = max(0.5, self._queue_check_interval * 0.9)
            elif self.stats.average_wait_time_seconds < 10:
                # Low wait times, can check less frequently
                self._queue_check_interval = min(2.0, self._queue_check_interval * 1.1)
            
            logger.debug(f"Adjusted queue check interval to {self._queue_check_interval:.1f}s")


# Global instance
model_queue_manager = ModelQueueManager()