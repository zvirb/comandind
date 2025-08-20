"""
Correction Memory Service

Implements proactive error prevention using semantic memory of past failures.
Based on smart_ai.txt research for preventing repeated mistakes through "correction memory".
Now uses LangGraph for automatic progress monitoring.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field

from worker.services.qdrant_service import QdrantService
from worker.services.ollama_service import invoke_llm_with_tokens
from worker.graph_types import GraphState
from worker.smart_ai_models import ErrorModel, ToolCallRecord
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class CorrectionMemoryState(BaseModel):
    """State object for the correction memory workflow."""
    # Input data
    state: Dict[str, Any] = Field(default_factory=dict)  # Original GraphState data
    planned_action: str = ""
    tool_name: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Workflow state data
    analysis_results: Dict[str, Any] = Field(default_factory=dict)
    correction_warnings: List[str] = Field(default_factory=list)
    failure_pattern: Optional[Dict[str, Any]] = None
    
    # Results
    warnings_found: bool = False
    pattern_stored: bool = False
    error_message: Optional[str] = None


class CorrectionMemoryService:
    """
    Service for managing correction memory - a specialized semantic memory for proactive error prevention.
    Stores failure patterns and retrieves warnings during planning to prevent repeated mistakes.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.qdrant_service = QdrantService()
        self.correction_collection = "correction_memory"
        
        # Categories of corrections for better retrieval
        self.correction_types = {
            "tool_error": "Tool execution failures and parameter issues",
            "validation_error": "Validation failures and constraint violations", 
            "logic_error": "Logical inconsistencies and reasoning failures",
            "user_correction": "Human corrections and feedback",
            "planning_error": "Planning mistakes and step order issues"
        }
    
    async def initialize_correction_memory(self):
        """Initialize the correction memory collection in Qdrant if it doesn't exist."""
        try:
            # Check if collection exists
            existing_collections = await self.qdrant_service.list_collections()
            
            if self.correction_collection not in existing_collections:
                logger.info("Creating correction_memory collection in Qdrant")
                await self.qdrant_service.create_collection(
                    collection_name=self.correction_collection,
                    vector_size=384,  # Standard for sentence transformers
                    distance="Cosine"
                )
                logger.info("Correction memory collection created successfully")
            else:
                logger.debug("Correction memory collection already exists")
                
        except Exception as e:
            logger.error(f"Failed to initialize correction memory: {e}")
    
    async def store_failure_pattern(self, state: GraphState, failure_info: Dict[str, Any]) -> bool:
        """
        Store a failure pattern in correction memory for future avoidance.
        
        Args:
            state: Current graph state with context
            failure_info: Dict containing failure details
        
        Returns:
            bool: Success status
        """
        try:
            # Create comprehensive failure record
            failure_record = {
                "user_query": state.user_input,
                "failed_action": failure_info.get("action", "unknown"),
                "tool_name": failure_info.get("tool_name", state.selected_tool),
                "error_message": failure_info.get("error_message", ""),
                "error_type": failure_info.get("error_type", "general"),
                "context": failure_info.get("context", ""),
                "step_description": failure_info.get("step_description", ""),
                "timestamp": datetime.now().isoformat(),
                "session_id": state.session_id,
                "user_id": state.user_id
            }
            
            # Create descriptive text for embedding
            correction_text = self._build_correction_text(failure_record)
            
            # Add to Qdrant with metadata
            point_id = str(uuid.uuid4())
            metadata = {
                "text": correction_text,
                "error_type": failure_record["error_type"],
                "tool_name": failure_record["tool_name"],
                "timestamp": failure_record["timestamp"],
                "user_id": failure_record["user_id"],
                "session_id": failure_record["session_id"],
                "content_type": "correction"
            }
            
            # Generate embedding and store
            success = await self.qdrant_service.add_point(
                collection_name=self.correction_collection,
                point_id=point_id,
                text=correction_text,
                metadata=metadata
            )
            
            if success:
                logger.info(f"Stored correction pattern: {failure_record['error_type']} for {failure_record['tool_name']}")
                
                # Broadcast storage success
                if state.session_id:
                    from worker.services.progress_manager import progress_manager
                    import asyncio
                    progress_manager.broadcast_to_session_sync_sync(state.session_id, {
                        "type": "correction_stored",
                        "content": f"Learning from failure: {failure_record['error_type']}",
                        "pattern": correction_text[:100] + "..."
                    })
                
                return True
            else:
                logger.warning("Failed to store correction pattern in Qdrant")
                return False
                
        except Exception as e:
            logger.error(f"Error storing failure pattern: {e}", exc_info=True)
            return False
    
    async def retrieve_correction_warnings(self, state: GraphState, planned_action: str, 
                                         tool_name: Optional[str] = None) -> List[str]:
        """
        Retrieve warnings from correction memory for a planned action.
        
        Args:
            state: Current graph state
            planned_action: The action being planned
            tool_name: Optional specific tool name
            
        Returns:
            List of warning strings to include in planning prompts
        """
        try:
            await self.initialize_correction_memory()
            
            # Build search queries for semantic similarity
            search_queries = [
                planned_action,  # Direct action search
                f"{tool_name} {planned_action}" if tool_name else planned_action,  # Tool-specific
                f"error {planned_action}",  # Error-focused search
                f"{state.user_input} {planned_action}"  # Context-aware search
            ]
            
            warnings = []
            seen_warnings = set()
            
            for query in search_queries:
                try:
                    # Search for similar past failures
                    search_results = await self.qdrant_service.search_points(
                        query_text=query,
                        limit=3,
                        user_id=int(state.user_id) if state.user_id else None,
                        content_types=["correction"],
                        collection_name=self.correction_collection
                    )
                    
                    for result in search_results:
                        if hasattr(result, 'payload') and result.payload:
                            warning_text = result.payload.get('text', '')
                            error_type = result.payload.get('error_type', 'unknown')
                            tool = result.payload.get('tool_name', 'unknown')
                            
                            # Create concise warning
                            if warning_text and warning_text not in seen_warnings:
                                warning = f"⚠️ [{error_type}] {tool}: {warning_text[:150]}"
                                warnings.append(warning)
                                seen_warnings.add(warning_text)
                                
                                # Limit to avoid token bloat
                                if len(warnings) >= 5:
                                    break
                                    
                except Exception as e:
                    logger.debug(f"Search failed for query '{query}': {e}")
                    continue
            
            if warnings:
                logger.info(f"Retrieved {len(warnings)} correction warnings for planning")
                
                # Broadcast warnings retrieval
                if state.session_id:
                    from worker.services.progress_manager import progress_manager
                    import asyncio
                    progress_manager.broadcast_to_session_sync_sync(state.session_id, {
                        "type": "correction_warnings",
                        "content": f"Found {len(warnings)} lessons from past failures",
                        "warnings": [w[:100] + "..." for w in warnings]
                    })
            
            return warnings
            
        except Exception as e:
            logger.warning(f"Error retrieving correction warnings: {e}")
            return []
    
    async def analyze_for_correction_patterns(self, state: GraphState) -> Optional[Dict[str, Any]]:
        """
        Analyze the current state to identify potential correction patterns to store.
        
        Args:
            state: Current graph state
            
        Returns:
            Dict with failure information if correction pattern detected, None otherwise
        """
        try:
            # Check for tool failures
            if state.tool_call_history:
                recent_call = state.tool_call_history[-1]
                if not recent_call.success or recent_call.error_message:
                    return {
                        "action": f"Call {recent_call.tool_name}",
                        "tool_name": recent_call.tool_name,
                        "error_message": recent_call.error_message or "Tool call failed",
                        "error_type": "tool_error",
                        "context": json.dumps(recent_call.input_args) if recent_call.input_args else "",
                        "step_description": f"Tool call to {recent_call.tool_name}"
                    }
            
            # Check for validation failures in recent critique
            if state.critique_history:
                recent_critique = state.critique_history[-1]
                if recent_critique.retry_recommended and recent_critique.specific_issues:
                    return {
                        "action": state.user_input,
                        "tool_name": state.selected_tool or "unknown",
                        "error_message": "; ".join(recent_critique.specific_issues),
                        "error_type": "validation_error",
                        "context": recent_critique.critique_text,
                        "step_description": recent_critique.critique_text[:100]
                    }
            
            # Check for low confidence patterns
            if state.confidence_score < 0.4:
                return {
                    "action": state.user_input,
                    "tool_name": state.selected_tool or "unknown", 
                    "error_message": f"Low confidence ({state.confidence_score:.2f}) in execution",
                    "error_type": "confidence_error",
                    "context": f"User input: {state.user_input}",
                    "step_description": f"Low confidence execution"
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error analyzing for correction patterns: {e}")
            return None
    
    def _build_correction_text(self, failure_record: Dict[str, Any]) -> str:
        """Build descriptive text for embedding that captures the failure pattern."""
        parts = []
        
        # Add main failure description
        if failure_record.get("failed_action"):
            parts.append(f"FAILED ACTION: {failure_record['failed_action']}")
        
        # Add tool information
        if failure_record.get("tool_name"):
            parts.append(f"TOOL: {failure_record['tool_name']}")
        
        # Add error details
        if failure_record.get("error_message"):
            parts.append(f"ERROR: {failure_record['error_message']}")
        
        # Add context
        if failure_record.get("context"):
            parts.append(f"CONTEXT: {failure_record['context'][:200]}")
        
        # Add prevention advice
        parts.append(f"AVOID: Do not repeat this {failure_record.get('error_type', 'error')} pattern")
        
        return " | ".join(parts)
    
    async def get_correction_memory_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about the correction memory for monitoring."""
        try:
            # Count total corrections
            search_results = await self.qdrant_service.search_points(
                query_text="correction",
                limit=1000,  # High limit to get count
                user_id=int(user_id) if user_id else None,
                content_types=["correction"],
                collection_name=self.correction_collection
            )
            
            total_corrections = len(search_results)
            
            # Count by error type
            error_type_counts = {}
            for result in search_results:
                if hasattr(result, 'payload') and result.payload:
                    error_type = result.payload.get('error_type', 'unknown')
                    error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
            
            return {
                "total_corrections": total_corrections,
                "error_type_breakdown": error_type_counts,
                "collection_name": self.correction_collection,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error getting correction memory stats: {e}")
            return {"error": str(e)}

    async def retrieve_warnings_with_progress(self, state: GraphState, planned_action: str, 
                                            tool_name: Optional[str] = None) -> List[str]:
        """
        Retrieve correction warnings using LangGraph with automatic progress monitoring.
        
        Args:
            state: Current graph state
            planned_action: The action being planned
            tool_name: Optional specific tool name
            
        Returns:
            List of warning strings to include in planning prompts
        """
        try:
            # Create correction memory state
            correction_state = CorrectionMemoryState(
                state=state.__dict__ if hasattr(state, '__dict__') else {},
                planned_action=planned_action,
                tool_name=tool_name,
                session_id=state.session_id,
                user_id=state.user_id
            )
            
            logger.info(f"Starting LangGraph correction memory retrieval for: {planned_action}")
            
            # Get progress manager for automatic broadcasting
            from worker.services.progress_manager import progress_manager
            
            # Broadcast workflow start
            if state.session_id:
                await progress_manager.broadcast_workflow_start(
                    state.session_id, 
                    f"Checking for correction patterns: {planned_action[:50]}..."
                )
            
            # Run the correction memory workflow with astream for progress monitoring
            config = RunnableConfig(recursion_limit=10)
            workflow_start_time = datetime.now()
            nodes_executed = 0
            
            final_state = None
            async for event in compiled_correction_workflow.astream(correction_state.model_dump(), config=config):
                nodes_executed += 1
                
                for node_name, node_state in event.items():
                    # Broadcast automatic progress update for this node
                    if state.session_id:
                        try:
                            node_execution_time = (datetime.now() - workflow_start_time).total_seconds()
                            await progress_manager.broadcast_node_transition(
                                state.session_id, f"correction_{node_name}", node_state, node_execution_time
                            )
                            logger.debug(f"Broadcasted correction progress for node: {node_name}")
                        except Exception as e:
                            logger.warning(f"Failed to broadcast correction progress for {node_name}: {e}")
                
                # Store the final state
                final_state = event
            
            # Calculate total execution time
            total_execution_time = (datetime.now() - workflow_start_time).total_seconds()
            
            # Extract final results from the last state
            if final_state:
                last_key = list(final_state.keys())[-1]
                final_correction_state = final_state[last_key]
                
                # Broadcast workflow completion
                if state.session_id:
                    warnings_count = len(final_correction_state.get("correction_warnings", []))
                    await progress_manager.broadcast_workflow_complete(
                        state.session_id, 
                        f"Found {warnings_count} correction warnings",
                        total_execution_time, 
                        nodes_executed
                    )
                
                # Return the warnings
                return final_correction_state.get("correction_warnings", [])
            else:
                # Fallback if no final state
                logger.warning("No final state from correction workflow")
                return []
            
        except Exception as e:
            logger.error(f"Error in LangGraph correction workflow: {e}", exc_info=True)
            
            # Broadcast error if possible
            if state.session_id:
                try:
                    from worker.services.progress_manager import progress_manager
                    await progress_manager.broadcast_workflow_complete(
                        state.session_id,
                        f"Correction memory failed: {str(e)}",
                        0.0,
                        0
                    )
                except:
                    pass
            
            # Fallback to original method
            logger.info("Falling back to original correction memory method")
            return await self.retrieve_correction_warnings(state, planned_action, tool_name)


# --- LangGraph Workflow Nodes ---

async def analyze_patterns_node(state: CorrectionMemoryState) -> Dict[str, Any]:
    """Analyze current state for correction patterns."""
    try:
        service = correction_memory_service
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        analysis_results = await service.analyze_for_correction_patterns(mock_state)
        
        return {
            "analysis_results": analysis_results or {},
            "failure_pattern": analysis_results
        }
        
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        return {
            "analysis_results": {},
            "error_message": f"Analysis error: {str(e)}"
        }


async def retrieve_warnings_node(state: CorrectionMemoryState) -> Dict[str, Any]:
    """Retrieve correction warnings from semantic memory."""
    try:
        service = correction_memory_service
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        warnings = await service.retrieve_correction_warnings(
            mock_state, state.planned_action, state.tool_name
        )
        
        return {
            "correction_warnings": warnings,
            "warnings_found": len(warnings) > 0
        }
        
    except Exception as e:
        logger.error(f"Error retrieving warnings: {e}")
        return {
            "correction_warnings": [],
            "warnings_found": False,
            "error_message": f"Warning retrieval error: {str(e)}"
        }


async def store_pattern_node(state: CorrectionMemoryState) -> Dict[str, Any]:
    """Store failure pattern in correction memory."""
    try:
        service = correction_memory_service
        
        if not state.failure_pattern:
            return {"pattern_stored": False}
        
        # Reconstruct GraphState from stored data
        mock_state = type('MockState', (), state.state)()
        
        success = await service.store_failure_pattern(mock_state, state.failure_pattern)
        
        return {"pattern_stored": success}
        
    except Exception as e:
        logger.error(f"Error storing pattern: {e}")
        return {
            "pattern_stored": False,
            "error_message": f"Pattern storage error: {str(e)}"
        }


def should_store_pattern(state: CorrectionMemoryState) -> str:
    """Decide whether to store a failure pattern or end."""
    if state.error_message:
        logger.info(f"Stopping correction workflow due to error: {state.error_message}")
        return "__end__"
    
    if state.failure_pattern:
        return "store_pattern"
    
    return "__end__"


# Create the correction memory workflow graph
correction_workflow = StateGraph(CorrectionMemoryState)

# Add nodes
correction_workflow.add_node("analyze_patterns", RunnableLambda(analyze_patterns_node))  # type: ignore
correction_workflow.add_node("retrieve_warnings", RunnableLambda(retrieve_warnings_node))  # type: ignore
correction_workflow.add_node("store_pattern", RunnableLambda(store_pattern_node))  # type: ignore

# Set entry point
correction_workflow.set_entry_point("analyze_patterns")

# Add edges
correction_workflow.add_edge("analyze_patterns", "retrieve_warnings")
correction_workflow.add_conditional_edges(
    "retrieve_warnings",
    should_store_pattern,
    {
        "store_pattern": "store_pattern",
        "__end__": END
    }
)
correction_workflow.add_edge("store_pattern", END)

# Compile the workflow
compiled_correction_workflow = correction_workflow.compile()


# Global instance
correction_memory_service = CorrectionMemoryService()