"""Workflow State Manager with Redis-backed state and PostgreSQL persistence.

This module manages workflow execution state with Redis for fast access and PostgreSQL
for durable persistence, supporting <30s recovery time requirements.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class WorkflowState(str, Enum):
    """Workflow execution states."""
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERING = "recovering"


@dataclass
class WorkflowStateSnapshot:
    """Represents a workflow state snapshot."""
    workflow_id: str
    state: WorkflowState
    state_data: Dict[str, Any]
    checkpoint_id: str
    created_at: float = field(default_factory=time.time)
    sequence_number: int = 0
    recovery_metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "workflow_id": self.workflow_id,
            "state": self.state,
            "state_data": self.state_data,
            "checkpoint_id": self.checkpoint_id,
            "created_at": self.created_at,
            "sequence_number": self.sequence_number,
            "recovery_metadata": self.recovery_metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStateSnapshot':
        """Create from dictionary."""
        return cls(
            workflow_id=data["workflow_id"],
            state=WorkflowState(data["state"]),
            state_data=data["state_data"],
            checkpoint_id=data["checkpoint_id"],
            created_at=data["created_at"],
            sequence_number=data["sequence_number"],
            recovery_metadata=data.get("recovery_metadata")
        )


class WorkflowStateManager:
    """Manages workflow state with Redis caching and PostgreSQL persistence."""
    
    def __init__(
        self,
        database_url: str,
        redis_service,
        recovery_timeout: int = 30,
        checkpoint_interval: int = 10,
        state_retention_hours: int = 168  # 1 week
    ):
        self.database_url = database_url
        self.redis_service = redis_service
        self.recovery_timeout = recovery_timeout
        self.checkpoint_interval = checkpoint_interval
        self.state_retention_hours = state_retention_hours
        
        # Database connection pool
        self._db_pool: Optional[asyncpg.Pool] = None
        
        # In-memory state tracking
        self._active_workflows: Dict[str, WorkflowStateSnapshot] = {}
        self._state_locks: Dict[str, asyncio.Lock] = {}
        
        # Recovery tracking
        self._recovery_in_progress = False
        self._last_checkpoint_time = 0.0
        
        # Performance metrics
        self.state_metrics = {
            "total_workflows": 0,
            "active_workflows": 0,
            "checkpoints_created": 0,
            "recovery_operations": 0,
            "avg_recovery_time": 0.0,
            "cache_hit_rate": 0.0
        }
    
    async def initialize(self) -> None:
        """Initialize the workflow state manager."""
        logger.info("Initializing Workflow State Manager...")
        
        # Initialize database connection pool
        self._db_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        
        # Create database schema if needed
        await self._ensure_database_schema()
        
        # Start recovery process
        await self._perform_startup_recovery()
        
        # Start background checkpoint task
        asyncio.create_task(self._run_checkpoint_loop())
        
        logger.info(
            "Workflow State Manager initialized",
            recovery_timeout=self.recovery_timeout,
            checkpoint_interval=self.checkpoint_interval
        )
    
    async def create_workflow_state(
        self,
        workflow_id: str,
        initial_state: WorkflowState = WorkflowState.CREATED,
        state_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowStateSnapshot:
        """Create new workflow state tracking."""
        async with self._get_workflow_lock(workflow_id):
            logger.info("Creating workflow state", workflow_id=workflow_id)
            
            checkpoint_id = f"checkpoint_{workflow_id}_{int(time.time())}"
            
            snapshot = WorkflowStateSnapshot(
                workflow_id=workflow_id,
                state=initial_state,
                state_data=state_data or {},
                checkpoint_id=checkpoint_id,
                sequence_number=1
            )
            
            # Store in memory
            self._active_workflows[workflow_id] = snapshot
            
            # Cache in Redis
            await self._cache_workflow_state(snapshot)
            
            # Persist to database
            await self._persist_workflow_state(snapshot)
            
            # Update metrics
            self.state_metrics["total_workflows"] += 1
            self.state_metrics["active_workflows"] = len(self._active_workflows)
            
            logger.info("Workflow state created", workflow_id=workflow_id, checkpoint_id=checkpoint_id)
            return snapshot
    
    async def update_workflow_state(
        self,
        workflow_id: str,
        new_state: WorkflowState,
        state_data: Optional[Dict[str, Any]] = None,
        create_checkpoint: bool = True
    ) -> WorkflowStateSnapshot:
        """Update workflow state with optional checkpointing."""
        async with self._get_workflow_lock(workflow_id):
            current_snapshot = self._active_workflows.get(workflow_id)
            if not current_snapshot:
                # Try to load from cache/database
                current_snapshot = await self._load_workflow_state(workflow_id)
                if not current_snapshot:
                    raise ValueError(f"Workflow {workflow_id} not found")
            
            logger.debug(
                "Updating workflow state",
                workflow_id=workflow_id,
                old_state=current_snapshot.state,
                new_state=new_state
            )
            
            # Create new snapshot
            new_snapshot = WorkflowStateSnapshot(
                workflow_id=workflow_id,
                state=new_state,
                state_data=state_data or current_snapshot.state_data,
                checkpoint_id=f"checkpoint_{workflow_id}_{int(time.time())}",
                sequence_number=current_snapshot.sequence_number + 1
            )
            
            # Update in memory
            self._active_workflows[workflow_id] = new_snapshot
            
            # Update Redis cache
            await self._cache_workflow_state(new_snapshot)
            
            # Persist to database if checkpointing
            if create_checkpoint:
                await self._persist_workflow_state(new_snapshot)
                self.state_metrics["checkpoints_created"] += 1
            
            logger.debug("Workflow state updated", workflow_id=workflow_id, checkpoint_id=new_snapshot.checkpoint_id)
            return new_snapshot
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive workflow status information."""
        try:
            # First check memory
            snapshot = self._active_workflows.get(workflow_id)
            
            if not snapshot:
                # Check Redis cache
                snapshot = await self._load_from_cache(workflow_id)
                
                if not snapshot:
                    # Load from database
                    snapshot = await self._load_from_database(workflow_id)
            
            if not snapshot:
                return None
            
            # Calculate additional status information
            execution_time = time.time() - snapshot.created_at
            
            status = {
                "workflow_id": workflow_id,
                "current_state": snapshot.state,
                "sequence_number": snapshot.sequence_number,
                "checkpoint_id": snapshot.checkpoint_id,
                "created_at": snapshot.created_at,
                "execution_time_seconds": execution_time,
                "state_data": snapshot.state_data,
                "is_active": snapshot.state in [WorkflowState.RUNNING, WorkflowState.QUEUED],
                "is_complete": snapshot.state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED],
                "recovery_metadata": snapshot.recovery_metadata
            }
            
            # Add progress information if available
            if "progress" in snapshot.state_data:
                status["progress_percentage"] = snapshot.state_data["progress"]
            
            # Add estimated completion time if available
            if "estimated_completion" in snapshot.state_data:
                status["estimated_completion"] = snapshot.state_data["estimated_completion"]
            
            return status
            
        except Exception as e:
            logger.error("Failed to get workflow status", workflow_id=workflow_id, error=str(e))
            raise
    
    async def get_active_workflow_count(self) -> int:
        """Get count of active workflows."""
        active_states = [WorkflowState.RUNNING, WorkflowState.QUEUED, WorkflowState.PAUSED]
        return sum(1 for snapshot in self._active_workflows.values() if snapshot.state in active_states)
    
    async def persist_workflow_state(self, workflow_id: str, state_dict: Dict[str, Any]) -> None:
        """Persist workflow state from external sources."""
        current_state = state_dict.get("status", WorkflowState.RUNNING)
        
        await self.update_workflow_state(
            workflow_id=workflow_id,
            new_state=WorkflowState(current_state),
            state_data=state_dict,
            create_checkpoint=True
        )
    
    async def recover_workflows(self, max_age_hours: int = 24) -> List[str]:
        """Recover workflows from persistent storage."""
        from datetime import datetime, timedelta
        
        start_time = time.time()
        
        logger.info("Starting workflow recovery", max_age_hours=max_age_hours)
        
        try:
            self._recovery_in_progress = True
            
            # Load recent workflows from database
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            async with self._db_pool.acquire() as conn:
                query = """
                    SELECT DISTINCT workflow_id, state, state_data, checkpoint_id, 
                           created_at, sequence_number, recovery_metadata
                    FROM workflow_states 
                    WHERE created_at > $1 
                    AND state IN ('running', 'queued', 'paused')
                    ORDER BY workflow_id, sequence_number DESC
                """
                
                rows = await conn.fetch(query, cutoff_time)
            
            recovered_workflows = []
            workflow_states = {}
            
            # Group by workflow_id and get latest state
            for row in rows:
                workflow_id = row["workflow_id"]
                if workflow_id not in workflow_states:
                    workflow_states[workflow_id] = row
            
            # Restore workflow states
            for workflow_id, row_data in workflow_states.items():
                try:
                    snapshot = WorkflowStateSnapshot(
                        workflow_id=workflow_id,
                        state=WorkflowState(row_data["state"]),
                        state_data=json.loads(row_data["state_data"]) if row_data["state_data"] else {},
                        checkpoint_id=row_data["checkpoint_id"],
                        created_at=row_data["created_at"],
                        sequence_number=row_data["sequence_number"],
                        recovery_metadata=json.loads(row_data["recovery_metadata"]) if row_data["recovery_metadata"] else None
                    )
                    
                    # Mark as recovering
                    snapshot.state = WorkflowState.RECOVERING
                    snapshot.recovery_metadata = {
                        "original_state": row_data["state"],
                        "recovery_started_at": time.time(),
                        "recovery_reason": "startup_recovery"
                    }
                    
                    # Store in memory and cache
                    self._active_workflows[workflow_id] = snapshot
                    await self._cache_workflow_state(snapshot)
                    
                    recovered_workflows.append(workflow_id)
                    
                except Exception as e:
                    logger.error("Failed to recover workflow", workflow_id=workflow_id, error=str(e))
            
            # Update metrics
            recovery_time = time.time() - start_time
            self.state_metrics["recovery_operations"] += 1
            self.state_metrics["avg_recovery_time"] = (
                (self.state_metrics["avg_recovery_time"] * (self.state_metrics["recovery_operations"] - 1) + recovery_time) /
                self.state_metrics["recovery_operations"]
            )
            self.state_metrics["active_workflows"] = len(self._active_workflows)
            
            logger.info(
                "Workflow recovery completed",
                recovered_count=len(recovered_workflows),
                recovery_time_seconds=recovery_time
            )
            
            return recovered_workflows
            
        finally:
            self._recovery_in_progress = False
    
    async def cleanup_old_states(self, retention_hours: int = None) -> int:
        """Clean up old workflow states from storage."""
        retention_hours = retention_hours or self.state_retention_hours
        cutoff_time = time.time() - (retention_hours * 3600)
        
        logger.info("Cleaning up old workflow states", retention_hours=retention_hours)
        
        try:
            # Clean up database
            async with self._db_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM workflow_states WHERE created_at < $1",
                    cutoff_time
                )
            
            # Parse deletion count from result
            deleted_count = int(result.split()[-1]) if result else 0
            
            # Clean up Redis cache for completed workflows
            if self.redis_service:
                cache_keys = await self.redis_service.scan_keys("workflow_state:*")
                cleaned_cache_keys = 0
                
                for key in cache_keys:
                    cached_data = await self.redis_service.get_json(key)
                    if cached_data and cached_data.get("created_at", 0) < cutoff_time:
                        if cached_data.get("state") in ["completed", "failed", "cancelled"]:
                            await self.redis_service.delete(key)
                            cleaned_cache_keys += 1
            
            logger.info(
                "Cleanup completed",
                deleted_db_records=deleted_count,
                cleaned_cache_keys=cleaned_cache_keys
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error("Cleanup failed", error=str(e))
            raise
    
    async def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status information for the state manager."""
        active_count = await self.get_active_workflow_count()
        
        return {
            "active_workflows": active_count,
            "total_tracked_workflows": len(self._active_workflows),
            "recovery_in_progress": self._recovery_in_progress,
            "last_checkpoint_time": self._last_checkpoint_time,
            "metrics": self.state_metrics,
            "configuration": {
                "recovery_timeout": self.recovery_timeout,
                "checkpoint_interval": self.checkpoint_interval,
                "state_retention_hours": self.state_retention_hours
            }
        }
    
    async def shutdown(self) -> None:
        """Graceful shutdown with state preservation."""
        logger.info("Shutting down Workflow State Manager...")
        
        try:
            # Perform final checkpoint for all active workflows
            logger.info("Performing final checkpoint...")
            
            checkpoint_tasks = []
            for workflow_id, snapshot in self._active_workflows.items():
                task = asyncio.create_task(self._persist_workflow_state(snapshot))
                checkpoint_tasks.append(task)
            
            if checkpoint_tasks:
                await asyncio.gather(*checkpoint_tasks, return_exceptions=True)
            
            # Close database pool
            if self._db_pool:
                await self._db_pool.close()
            
            logger.info("Workflow State Manager shutdown complete")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
    
    # Private helper methods
    
    def _get_workflow_lock(self, workflow_id: str) -> asyncio.Lock:
        """Get or create lock for workflow."""
        if workflow_id not in self._state_locks:
            self._state_locks[workflow_id] = asyncio.Lock()
        return self._state_locks[workflow_id]
    
    async def _cache_workflow_state(self, snapshot: WorkflowStateSnapshot) -> None:
        """Cache workflow state in Redis."""
        if self.redis_service:
            await self.redis_service.set_json(
                key=f"workflow_state:{snapshot.workflow_id}",
                value=snapshot.to_dict(),
                expiry_seconds=3600  # 1 hour cache
            )
    
    async def _load_from_cache(self, workflow_id: str) -> Optional[WorkflowStateSnapshot]:
        """Load workflow state from Redis cache."""
        if not self.redis_service:
            return None
        
        cached_data = await self.redis_service.get_json(f"workflow_state:{workflow_id}")
        if cached_data:
            return WorkflowStateSnapshot.from_dict(cached_data)
        
        return None
    
    async def _persist_workflow_state(self, snapshot: WorkflowStateSnapshot) -> None:
        """Persist workflow state to PostgreSQL."""
        async with self._db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO workflow_states 
                (workflow_id, state, state_data, checkpoint_id, created_at, sequence_number, recovery_metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                snapshot.workflow_id,
                snapshot.state,
                json.dumps(snapshot.state_data),
                snapshot.checkpoint_id,
                snapshot.created_at,
                snapshot.sequence_number,
                json.dumps(snapshot.recovery_metadata) if snapshot.recovery_metadata else None
            )
    
    async def _load_from_database(self, workflow_id: str) -> Optional[WorkflowStateSnapshot]:
        """Load latest workflow state from database."""
        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT state, state_data, checkpoint_id, created_at, sequence_number, recovery_metadata
                FROM workflow_states 
                WHERE workflow_id = $1 
                ORDER BY sequence_number DESC 
                LIMIT 1
            """, workflow_id)
            
            if row:
                return WorkflowStateSnapshot(
                    workflow_id=workflow_id,
                    state=WorkflowState(row["state"]),
                    state_data=json.loads(row["state_data"]) if row["state_data"] else {},
                    checkpoint_id=row["checkpoint_id"],
                    created_at=row["created_at"],
                    sequence_number=row["sequence_number"],
                    recovery_metadata=json.loads(row["recovery_metadata"]) if row["recovery_metadata"] else None
                )
        
        return None
    
    async def _load_workflow_state(self, workflow_id: str) -> Optional[WorkflowStateSnapshot]:
        """Load workflow state from cache or database."""
        # Try cache first
        snapshot = await self._load_from_cache(workflow_id)
        if snapshot:
            return snapshot
        
        # Try database
        return await self._load_from_database(workflow_id)
    
    async def _ensure_database_schema(self) -> None:
        """Ensure database schema exists."""
        async with self._db_pool.acquire() as conn:
            # Create workflow_states table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_states (
                    id SERIAL PRIMARY KEY,
                    workflow_id VARCHAR(255) NOT NULL,
                    state VARCHAR(50) NOT NULL,
                    state_data JSONB,
                    checkpoint_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    sequence_number INTEGER NOT NULL DEFAULT 1,
                    recovery_metadata JSONB
                )
            """)
            
            # Create indexes separately
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_states_workflow_id ON workflow_states (workflow_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_states_created_at ON workflow_states (created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_states_state ON workflow_states (state)")
    
    async def _perform_startup_recovery(self) -> None:
        """Perform recovery process at startup."""
        try:
            recovered_workflows = await self.recover_workflows()
            
            if recovered_workflows:
                logger.info("Startup recovery completed", recovered_count=len(recovered_workflows))
            else:
                logger.info("No workflows required recovery")
                
        except Exception as e:
            logger.error("Startup recovery failed", error=str(e))
            # Continue startup even if recovery fails
    
    async def _run_checkpoint_loop(self) -> None:
        """Background task for periodic checkpointing."""
        logger.info("Starting checkpoint loop")
        
        try:
            while True:
                await asyncio.sleep(self.checkpoint_interval)
                
                try:
                    current_time = time.time()
                    
                    # Checkpoint workflows that need it
                    checkpoint_tasks = []
                    
                    for workflow_id, snapshot in self._active_workflows.items():
                        # Checkpoint if workflow is active and hasn't been checkpointed recently
                        if (snapshot.state in [WorkflowState.RUNNING, WorkflowState.PAUSED] and
                            current_time - snapshot.created_at > self.checkpoint_interval):
                            
                            task = asyncio.create_task(self._persist_workflow_state(snapshot))
                            checkpoint_tasks.append(task)
                    
                    if checkpoint_tasks:
                        await asyncio.gather(*checkpoint_tasks, return_exceptions=True)
                        self.state_metrics["checkpoints_created"] += len(checkpoint_tasks)
                        
                        logger.debug("Periodic checkpoint completed", checkpoints=len(checkpoint_tasks))
                    
                    self._last_checkpoint_time = current_time
                    
                except Exception as e:
                    logger.error("Error in checkpoint loop", error=str(e))
                    
        except asyncio.CancelledError:
            logger.info("Checkpoint loop cancelled")
        except Exception as e:
            logger.error("Checkpoint loop failed", error=str(e))