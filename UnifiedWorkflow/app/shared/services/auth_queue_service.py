"""Authentication queue service for handling race conditions and token validation."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time

from sqlalchemy.ext.asyncio import AsyncSession
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service

logger = logging.getLogger(__name__)


class AuthOperationType(Enum):
    """Types of authentication operations."""
    TOKEN_VALIDATION = "token_validation"
    TOKEN_REFRESH = "token_refresh"
    API_REQUEST = "api_request"
    SESSION_EXTENSION = "session_extension"
    LOGOUT = "logout"


class AuthOperationStatus(Enum):
    """Status of authentication operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AuthOperation:
    """Represents an authentication operation in the queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: AuthOperationType = AuthOperationType.TOKEN_VALIDATION
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    status: AuthOperationStatus = AuthOperationStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    priority: int = 1  # Lower number = higher priority
    callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None


class AuthQueueService:
    """Service for managing authentication operation queues to prevent race conditions."""
    
    def __init__(self):
        self.logger = logger
        self._queues: Dict[str, asyncio.Queue] = {}  # Per-user queues
        self._locks: Dict[str, asyncio.Lock] = {}   # Per-user locks
        self._active_operations: Dict[str, AuthOperation] = {}
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats = {
            "operations_processed": 0,
            "operations_failed": 0,
            "operations_cancelled": 0,
            "queue_overflows": 0,
            "average_processing_time": 0.0
        }
    
    async def start(self, num_workers: int = 5):
        """Start the authentication queue service."""
        if self._running:
            return
        
        self._running = True
        self.logger.info(f"Starting AuthQueueService with {num_workers} workers")
        
        # Start worker tasks
        for i in range(num_workers):
            worker_task = asyncio.create_task(self._worker(f"auth-worker-{i}"))
            self._workers.append(worker_task)
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_operations())
    
    async def stop(self):
        """Stop the authentication queue service."""
        if not self._running:
            return
        
        self.logger.info("Stopping AuthQueueService")
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        if self._cleanup_task:
            await asyncio.gather(self._cleanup_task, return_exceptions=True)
        
        self._workers.clear()
        self._cleanup_task = None
        
        # Cancel pending operations
        for operation in self._active_operations.values():
            if operation.status == AuthOperationStatus.PENDING:
                operation.status = AuthOperationStatus.CANCELLED
                operation.error = "Service shutdown"
        
        self.logger.info("AuthQueueService stopped")
    
    async def queue_token_validation(
        self,
        session: AsyncSession,
        token: str,
        user_id: int,
        required_scopes: List[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        priority: int = 1
    ) -> str:
        """Queue a token validation operation."""
        operation = AuthOperation(
            operation_type=AuthOperationType.TOKEN_VALIDATION,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload={
                "token": token,
                "required_scopes": required_scopes or [],
                "session": session
            },
            priority=priority
        )
        
        return await self._queue_operation(operation)
    
    async def queue_token_refresh(
        self,
        session: AsyncSession,
        user_id: int,
        refresh_token: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        priority: int = 0  # High priority for refreshes
    ) -> str:
        """Queue a token refresh operation."""
        operation = AuthOperation(
            operation_type=AuthOperationType.TOKEN_REFRESH,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload={
                "refresh_token": refresh_token,
                "session": session
            },
            priority=priority,
            timeout_seconds=45  # Longer timeout for refresh
        )
        
        return await self._queue_operation(operation)
    
    async def queue_api_request(
        self,
        user_id: int,
        request_callback: Callable[[], Awaitable[Dict[str, Any]]],
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        retry_count: int = 3,
        priority: int = 2
    ) -> str:
        """Queue an API request operation."""
        operation = AuthOperation(
            operation_type=AuthOperationType.API_REQUEST,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            payload={"request_callback": request_callback},
            max_retries=retry_count,
            priority=priority,
            timeout_seconds=60
        )
        
        return await self._queue_operation(operation)
    
    async def queue_session_extension(
        self,
        session: AsyncSession,
        user_id: int,
        current_token: str,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        priority: int = 1
    ) -> str:
        """Queue a session extension operation."""
        operation = AuthOperation(
            operation_type=AuthOperationType.SESSION_EXTENSION,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            payload={
                "current_token": current_token,
                "session": session
            },
            priority=priority
        )
        
        return await self._queue_operation(operation)
    
    async def get_operation_result(self, operation_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        """Wait for operation completion and return result."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            operation = self._active_operations.get(operation_id)
            
            if not operation:
                raise ValueError(f"Operation {operation_id} not found")
            
            if operation.status == AuthOperationStatus.COMPLETED:
                return operation.result or {}
            
            if operation.status == AuthOperationStatus.FAILED:
                raise Exception(f"Operation failed: {operation.error}")
            
            if operation.status == AuthOperationStatus.CANCELLED:
                raise Exception("Operation was cancelled")
            
            await asyncio.sleep(0.1)
        
        # Timeout reached
        operation = self._active_operations.get(operation_id)
        if operation:
            operation.status = AuthOperationStatus.CANCELLED
            operation.error = "Timeout waiting for result"
        
        raise TimeoutError(f"Operation {operation_id} timed out")
    
    async def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a pending operation."""
        operation = self._active_operations.get(operation_id)
        
        if not operation:
            return False
        
        if operation.status == AuthOperationStatus.PENDING:
            operation.status = AuthOperationStatus.CANCELLED
            operation.error = "Cancelled by request"
            return True
        
        return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        queue_lengths = {
            user_key: queue.qsize() 
            for user_key, queue in self._queues.items()
        }
        
        active_operations = {
            status.value: sum(1 for op in self._active_operations.values() if op.status == status)
            for status in AuthOperationStatus
        }
        
        return {
            **self._stats,
            "queue_lengths": queue_lengths,
            "active_operations": active_operations,
            "total_queues": len(self._queues),
            "workers_running": len([w for w in self._workers if not w.done()]),
            "is_running": self._running
        }
    
    async def _queue_operation(self, operation: AuthOperation) -> str:
        """Add operation to the appropriate user queue."""
        if not self._running:
            raise RuntimeError("AuthQueueService is not running")
        
        user_key = f"user_{operation.user_id}" if operation.user_id else "global"
        
        # Get or create queue for user
        if user_key not in self._queues:
            self._queues[user_key] = asyncio.Queue(maxsize=100)
            self._locks[user_key] = asyncio.Lock()
        
        queue = self._queues[user_key]
        
        # Check queue capacity
        if queue.qsize() >= 95:  # Near capacity
            self._stats["queue_overflows"] += 1
            self.logger.warning(f"Queue {user_key} near capacity: {queue.qsize()}")
            
            # Remove oldest pending operation if queue is full
            if queue.full():
                try:
                    old_operation = queue.get_nowait()
                    old_operation.status = AuthOperationStatus.CANCELLED
                    old_operation.error = "Queue overflow"
                    self.logger.warning(f"Cancelled operation {old_operation.id} due to queue overflow")
                except asyncio.QueueEmpty:
                    pass
        
        # Add to active operations tracking
        self._active_operations[operation.id] = operation
        
        # Queue the operation
        await queue.put(operation)
        
        self.logger.debug(f"Queued operation {operation.id} ({operation.operation_type.value}) for {user_key}")
        return operation.id
    
    async def _worker(self, worker_name: str):
        """Worker task that processes authentication operations."""
        self.logger.info(f"Worker {worker_name} started")
        
        while self._running:
            try:
                # Get next operation from any queue (priority-based)
                operation = await self._get_next_operation()
                
                if not operation:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process the operation
                await self._process_operation(operation, worker_name)
                
            except asyncio.CancelledError:
                self.logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {str(e)}")
                await asyncio.sleep(1)  # Brief pause on error
        
        self.logger.info(f"Worker {worker_name} stopped")
    
    async def _get_next_operation(self) -> Optional[AuthOperation]:
        """Get the next highest priority operation from any queue."""
        best_operation = None
        best_queue = None
        best_priority = float('inf')
        
        # Check all queues for the highest priority operation
        for user_key, queue in self._queues.items():
            if queue.empty():
                continue
            
            # Peek at the front of the queue
            try:
                # Get operation without removing it (we'll remove it after selection)
                temp_operations = []
                while not queue.empty():
                    op = await asyncio.wait_for(queue.get(), timeout=0.01)
                    temp_operations.append(op)
                    
                    if op.status == AuthOperationStatus.PENDING and op.priority < best_priority:
                        best_operation = op
                        best_queue = queue
                        best_priority = op.priority
                        break  # Found a better operation
                
                # Put back operations we didn't select
                for op in temp_operations:
                    if op != best_operation:
                        await queue.put(op)
                        
            except asyncio.TimeoutError:
                continue
        
        return best_operation
    
    async def _process_operation(self, operation: AuthOperation, worker_name: str):
        """Process a single authentication operation."""
        operation.status = AuthOperationStatus.IN_PROGRESS
        operation.started_at = datetime.now(timezone.utc)
        
        self.logger.debug(f"Worker {worker_name} processing operation {operation.id}")
        
        start_time = time.time()
        
        try:
            # Set timeout for operation
            result = await asyncio.wait_for(
                self._execute_operation(operation),
                timeout=operation.timeout_seconds
            )
            
            operation.result = result
            operation.status = AuthOperationStatus.COMPLETED
            operation.completed_at = datetime.now(timezone.utc)
            
            # Update stats
            processing_time = time.time() - start_time
            self._stats["operations_processed"] += 1
            
            # Update average processing time
            total_ops = self._stats["operations_processed"]
            current_avg = self._stats["average_processing_time"]
            self._stats["average_processing_time"] = (
                (current_avg * (total_ops - 1) + processing_time) / total_ops
            )
            
            self.logger.debug(f"Operation {operation.id} completed in {processing_time:.2f}s")
            
            # Execute callback if provided
            if operation.callback:
                try:
                    await operation.callback(result)
                except Exception as e:
                    self.logger.warning(f"Operation callback failed: {str(e)}")
            
        except asyncio.TimeoutError:
            await self._handle_operation_timeout(operation)
        except Exception as e:
            await self._handle_operation_error(operation, e)
    
    async def _execute_operation(self, operation: AuthOperation) -> Dict[str, Any]:
        """Execute the specific operation type."""
        if operation.operation_type == AuthOperationType.TOKEN_VALIDATION:
            return await self._execute_token_validation(operation)
        elif operation.operation_type == AuthOperationType.TOKEN_REFRESH:
            return await self._execute_token_refresh(operation)
        elif operation.operation_type == AuthOperationType.API_REQUEST:
            return await self._execute_api_request(operation)
        elif operation.operation_type == AuthOperationType.SESSION_EXTENSION:
            return await self._execute_session_extension(operation)
        else:
            raise ValueError(f"Unknown operation type: {operation.operation_type}")
    
    async def _execute_token_validation(self, operation: AuthOperation) -> Dict[str, Any]:
        """Execute token validation operation."""
        payload = operation.payload
        session = payload["session"]
        token = payload["token"]
        required_scopes = payload["required_scopes"]
        
        # Use enhanced JWT service for validation
        result = await enhanced_jwt_service.verify_token(
            session=session,
            token=token,
            required_scopes=required_scopes,
            ip_address=operation.ip_address,
            user_agent=operation.user_agent
        )
        
        return result
    
    async def _execute_token_refresh(self, operation: AuthOperation) -> Dict[str, Any]:
        """Execute token refresh operation."""
        payload = operation.payload
        session = payload["session"]
        refresh_token = payload["refresh_token"]
        
        # Implement token refresh logic
        # This would integrate with your existing token refresh mechanism
        # For now, create new access token
        new_token = await enhanced_jwt_service.create_access_token(
            session=session,
            user_id=operation.user_id,
            session_id=operation.session_id,
            ip_address=operation.ip_address
        )
        
        return {
            "success": True,
            "new_token": new_token["access_token"],
            "expires_at": new_token["expires_at"]
        }
    
    async def _execute_api_request(self, operation: AuthOperation) -> Dict[str, Any]:
        """Execute API request operation."""
        payload = operation.payload
        request_callback = payload["request_callback"]
        
        # Execute the API request callback
        result = await request_callback()
        
        return result
    
    async def _execute_session_extension(self, operation: AuthOperation) -> Dict[str, Any]:
        """Execute session extension operation."""
        payload = operation.payload
        session = payload["session"]
        current_token = payload["current_token"]
        
        # Decode current token and create extended version
        import jwt
        from shared.utils.config import get_settings
        
        settings = get_settings()
        secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        
        try:
            # Decode current token
            current_payload = jwt.decode(current_token, secret_key, algorithms=["HS256"])
            
            # Create new token with extended expiry
            new_token = await enhanced_jwt_service.create_access_token(
                session=session,
                user_id=operation.user_id,
                scopes=current_payload.get("scopes", ["read", "write"]),
                session_id=operation.session_id,
                ip_address=operation.ip_address
            )
            
            return {
                "success": True,
                "extended_token": new_token["access_token"],
                "expires_at": new_token["expires_at"]
            }
            
        except jwt.InvalidTokenError as e:
            raise Exception(f"Invalid token for extension: {str(e)}")
    
    async def _handle_operation_timeout(self, operation: AuthOperation):
        """Handle operation timeout."""
        operation.status = AuthOperationStatus.FAILED
        operation.error = f"Operation timed out after {operation.timeout_seconds} seconds"
        operation.completed_at = datetime.now(timezone.utc)
        
        self._stats["operations_failed"] += 1
        
        self.logger.warning(f"Operation {operation.id} timed out")
        
        # Log security event for timeouts
        if operation.user_id:
            try:
                # Note: We can't use session here as it might be closed
                # This would need to be logged through a different mechanism
                pass
            except Exception as e:
                self.logger.warning(f"Failed to log timeout event: {str(e)}")
    
    async def _handle_operation_error(self, operation: AuthOperation, error: Exception):
        """Handle operation error with retry logic."""
        operation.retry_count += 1
        
        # Check if we should retry
        if operation.retry_count <= operation.max_retries and not isinstance(error, (ValueError, jwt.InvalidTokenError)):
            # Retry the operation
            operation.status = AuthOperationStatus.PENDING
            operation.error = None
            
            # Add back to queue with exponential backoff delay
            delay = min(2 ** operation.retry_count, 30)  # Max 30 seconds
            
            async def retry_after_delay():
                await asyncio.sleep(delay)
                user_key = f"user_{operation.user_id}" if operation.user_id else "global"
                if user_key in self._queues:
                    await self._queues[user_key].put(operation)
            
            asyncio.create_task(retry_after_delay())
            
            self.logger.info(f"Retrying operation {operation.id} in {delay}s (attempt {operation.retry_count})")
            return
        
        # Max retries reached or non-retryable error
        operation.status = AuthOperationStatus.FAILED
        operation.error = str(error)
        operation.completed_at = datetime.now(timezone.utc)
        
        self._stats["operations_failed"] += 1
        
        self.logger.error(f"Operation {operation.id} failed: {str(error)}")
    
    async def _cleanup_expired_operations(self):
        """Cleanup expired operations periodically."""
        while self._running:
            try:
                current_time = datetime.now(timezone.utc)
                expired_operations = []
                
                # Find expired operations (older than 5 minutes)
                for op_id, operation in self._active_operations.items():
                    if (current_time - operation.created_at).total_seconds() > 300:
                        expired_operations.append(op_id)
                
                # Remove expired operations
                for op_id in expired_operations:
                    operation = self._active_operations.pop(op_id, None)
                    if operation and operation.status == AuthOperationStatus.PENDING:
                        operation.status = AuthOperationStatus.CANCELLED
                        operation.error = "Expired"
                
                if expired_operations:
                    self.logger.info(f"Cleaned up {len(expired_operations)} expired operations")
                
                # Remove empty queues
                empty_queues = [
                    user_key for user_key, queue in self._queues.items() 
                    if queue.empty()
                ]
                
                for user_key in empty_queues:
                    if user_key in self._queues:
                        del self._queues[user_key]
                    if user_key in self._locks:
                        del self._locks[user_key]
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup task error: {str(e)}")
                await asyncio.sleep(60)


# Global authentication queue service instance
auth_queue_service = AuthQueueService()