"""
LangGraph Persistence Service with Checkpoints (LangChain 0.3+ feature).
Provides state persistence and recovery capabilities for graph execution.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, AsyncGenerator
from uuid import uuid4

from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from worker.graph_types import GraphState
from shared.schemas.enhanced_chat_schemas import EnhancedGraphState, IntermediateStep
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class CheckpointMetadata(BaseModel):
    """Metadata for graph execution checkpoints."""
    checkpoint_id: str = Field(..., description="Unique checkpoint identifier")
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    node_name: str = Field(..., description="Graph node name")
    timestamp: datetime = Field(default_factory=datetime.now, description="Checkpoint timestamp")
    execution_time_ms: Optional[float] = Field(None, description="Node execution time")
    confidence_score: Optional[float] = Field(None, description="Execution confidence")
    error_message: Optional[str] = Field(None, description="Error if checkpoint failed")

class GraphExecutionHistory(BaseModel):
    """Complete execution history for a session."""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    checkpoints: List[CheckpointMetadata] = Field(default_factory=list, description="Checkpoint history")
    total_execution_time_ms: float = Field(0, description="Total execution time")
    final_state: Optional[Dict[str, Any]] = Field(None, description="Final graph state")
    created_at: datetime = Field(default_factory=datetime.now, description="History creation time")

class GraphPersistenceService:
    """Service for managing LangGraph persistence and checkpoints."""
    
    def __init__(self):
        self.checkpoint_saver: BaseCheckpointSaver = self._create_checkpoint_saver()
        self.execution_histories: Dict[str, GraphExecutionHistory] = {}
        self.checkpoint_retention_hours = 24  # Keep checkpoints for 24 hours
        
    def _create_checkpoint_saver(self) -> BaseCheckpointSaver:
        """Create appropriate checkpoint saver based on environment."""
        # For development, use memory saver
        # For production, consider SQLite or database saver
        if settings.DEBUG:
            logger.info("Using in-memory checkpoint saver for development")
            return MemorySaver()
        else:
            # For production, use SQLite saver with persistent storage
            db_path = "/app/data/checkpoints.db"
            logger.info(f"Using SQLite checkpoint saver at {db_path}")
            return SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
    
    async def create_checkpointed_graph(
        self, 
        graph: StateGraph, 
        session_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> StateGraph:
        """Create a graph with checkpoint persistence enabled."""
        try:
            # Compile graph with checkpoint saver
            checkpointed_graph = graph.compile(checkpointer=self.checkpoint_saver)
            
            logger.info(f"Created checkpointed graph for session {session_id}")
            return checkpointed_graph
            
        except Exception as e:
            logger.error(f"Error creating checkpointed graph: {e}")
            # Fallback to non-checkpointed graph
            return graph.compile()
    
    async def save_checkpoint(
        self, 
        session_id: str,
        user_id: Optional[str],
        node_name: str,
        state: GraphState,
        execution_time_ms: Optional[float] = None,
        confidence_score: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> str:
        """Save a checkpoint for the current graph execution."""
        checkpoint_id = str(uuid4())
        
        try:
            # Create checkpoint metadata
            metadata = CheckpointMetadata(
                checkpoint_id=checkpoint_id,
                session_id=session_id,
                user_id=user_id,
                node_name=node_name,
                execution_time_ms=execution_time_ms,
                confidence_score=confidence_score,
                error_message=error_message
            )
            
            # Add to execution history
            if session_id not in self.execution_histories:
                self.execution_histories[session_id] = GraphExecutionHistory(
                    session_id=session_id,
                    user_id=user_id
                )
            
            history = self.execution_histories[session_id]
            history.checkpoints.append(metadata)
            
            if execution_time_ms:
                history.total_execution_time_ms += execution_time_ms
            
            logger.debug(f"Saved checkpoint {checkpoint_id} for session {session_id} at node {node_name}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            return checkpoint_id
    
    async def get_execution_history(self, session_id: str) -> Optional[GraphExecutionHistory]:
        """Get complete execution history for a session."""
        return self.execution_histories.get(session_id)
    
    async def get_latest_checkpoint(self, session_id: str) -> Optional[CheckpointMetadata]:
        """Get the latest checkpoint for a session."""
        history = await self.get_execution_history(session_id)
        if history and history.checkpoints:
            return history.checkpoints[-1]
        return None
    
    async def resume_from_checkpoint(
        self, 
        session_id: str, 
        checkpoint_id: Optional[str] = None
    ) -> Optional[GraphState]:
        """Resume graph execution from a specific checkpoint."""
        try:
            history = await self.get_execution_history(session_id)
            if not history:
                logger.warning(f"No execution history found for session {session_id}")
                return None
            
            # Find the checkpoint to resume from
            target_checkpoint = None
            if checkpoint_id:
                target_checkpoint = next(
                    (cp for cp in history.checkpoints if cp.checkpoint_id == checkpoint_id),
                    None
                )
            else:
                # Use latest checkpoint
                target_checkpoint = history.checkpoints[-1] if history.checkpoints else None
            
            if not target_checkpoint:
                logger.warning(f"Checkpoint not found for session {session_id}")
                return None
            
            # For now, return None as actual state recovery would need the full LangGraph integration
            # This would be implemented based on the specific checkpoint saver's capabilities
            logger.info(f"Would resume from checkpoint {target_checkpoint.checkpoint_id} at node {target_checkpoint.node_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error resuming from checkpoint: {e}")
            return None
    
    async def stream_with_checkpoints(
        self,
        graph: StateGraph,
        initial_state: GraphState,
        session_id: str,
        user_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[IntermediateStep, None]:
        """Stream graph execution with automatic checkpoint creation."""
        checkpointed_graph = await self.create_checkpointed_graph(graph, session_id, config)
        
        try:
            # Create thread config for checkpointing
            thread_config = {
                "configurable": {
                    "thread_id": session_id,
                    "checkpoint_ns": f"user_{user_id}" if user_id else "default"
                }
            }
            
            # Stream execution with checkpointing
            start_time = datetime.now()
            
            async for event in checkpointed_graph.astream(
                initial_state.model_dump(),
                config=thread_config,
                stream_mode="values"
            ):
                node_name = event.get("__node__", "unknown")
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # Save checkpoint
                # Need to handle BaseMessage conversion properly
                event_copy = event.copy()
                if 'messages' in event_copy and event_copy['messages']:
                    from langchain_core.messages import HumanMessage, AIMessage
                    converted_messages = []
                    for msg in event_copy['messages']:
                        if isinstance(msg, dict):
                            if msg.get('role') == 'user' or msg.get('type') == 'human':
                                converted_messages.append(HumanMessage(content=msg.get('content', '')))
                            elif msg.get('role') == 'assistant' or msg.get('type') == 'ai':
                                converted_messages.append(AIMessage(content=msg.get('content', '')))
                            else:
                                # Try to preserve the original format if it's already a BaseMessage-like object
                                if hasattr(msg, 'content'):
                                    converted_messages.append(HumanMessage(content=msg.content))
                        else:
                            converted_messages.append(msg)  # Already a BaseMessage
                    event_copy['messages'] = converted_messages
                
                checkpoint_id = await self.save_checkpoint(
                    session_id=session_id,
                    user_id=user_id,
                    node_name=node_name,
                    state=GraphState(**event_copy),  # Convert back to GraphState
                    execution_time_ms=execution_time
                )
                
                # Yield intermediate step
                yield IntermediateStep(
                    step_name=f"checkpoint_{node_name}",
                    description=f"Completed node: {node_name}",
                    status="completed",
                    output={
                        "checkpoint_id": checkpoint_id,
                        "node_name": node_name,
                        "execution_time_ms": execution_time,
                        "state_keys": list(event.keys())
                    }
                )
                
                start_time = datetime.now()
                
        except Exception as e:
            logger.error(f"Error in streaming with checkpoints: {e}")
            # Save error checkpoint
            await self.save_checkpoint(
                session_id=session_id,
                user_id=user_id,
                node_name="error",
                state=initial_state,
                error_message=str(e)
            )
            
            yield IntermediateStep(
                step_name="checkpoint_error",
                description=f"Error in graph execution: {str(e)}",
                status="error",
                output={"error": str(e)}
            )
    
    async def cleanup_old_checkpoints(self) -> None:
        """Clean up old checkpoints to prevent memory/storage bloat."""
        cutoff_time = datetime.now() - timedelta(hours=self.checkpoint_retention_hours)
        
        try:
            sessions_to_remove = []
            for session_id, history in self.execution_histories.items():
                if history.created_at < cutoff_time:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                del self.execution_histories[session_id]
                logger.debug(f"Cleaned up old execution history for session {session_id}")
            
            logger.info(f"Cleaned up {len(sessions_to_remove)} old checkpoint histories")
            
        except Exception as e:
            logger.error(f"Error cleaning up checkpoints: {e}")
    
    async def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """Get statistics about checkpoint usage."""
        try:
            total_sessions = len(self.execution_histories)
            total_checkpoints = sum(len(history.checkpoints) for history in self.execution_histories.values())
            
            avg_checkpoints_per_session = total_checkpoints / total_sessions if total_sessions > 0 else 0
            avg_execution_time = sum(
                history.total_execution_time_ms for history in self.execution_histories.values()
            ) / total_sessions if total_sessions > 0 else 0
            
            return {
                "total_sessions": total_sessions,
                "total_checkpoints": total_checkpoints,
                "avg_checkpoints_per_session": avg_checkpoints_per_session,
                "avg_execution_time_ms": avg_execution_time,
                "checkpoint_retention_hours": self.checkpoint_retention_hours
            }
            
        except Exception as e:
            logger.error(f"Error getting checkpoint statistics: {e}")
            return {}

# Global instance
graph_persistence_service = GraphPersistenceService()