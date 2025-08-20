#!/usr/bin/env python3
"""
Hybrid Intelligence Orchestrator
Enhanced Master Orchestrator that leverages hybrid memory and reasoning services

This service transforms the orchestration by:
1. Performing hybrid retrieval (semantic + structured) before task delegation
2. Integrating with sequential thinking service for complex reasoning
3. Providing real-time transparency through WebSocket connections
4. Creating a "glass box" view of agent operation
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, TypedDict
from dataclasses import dataclass, field
from enum import Enum

import httpx
from fastapi import WebSocket
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from worker.services.ollama_service import invoke_llm_with_tokens
from worker.services.progress_manager import progress_manager
from worker.graph_types import GraphState

logger = logging.getLogger(__name__)

class HybridRetrievalPhase(Enum):
    INITIALIZING = "initializing"
    SEMANTIC_SEARCH = "semantic_search"
    KNOWLEDGE_GRAPH_QUERY = "knowledge_graph_query"
    CONTEXT_SYNTHESIS = "context_synthesis"
    REASONING_PREPARATION = "reasoning_preparation"
    TASK_DELEGATION = "task_delegation"
    COMPLETE = "complete"

class ProcessingStatus(Enum):
    STARTED = "started"
    HYBRID_RETRIEVAL = "hybrid_retrieval"
    SEQUENTIAL_REASONING = "sequential_reasoning"
    TASK_EXECUTION = "task_execution"
    RESULT_SYNTHESIS = "result_synthesis"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class HybridContext:
    """Rich context from hybrid retrieval"""
    semantic_memories: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_entities: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_relationships: List[Dict[str, Any]] = field(default_factory=list)
    cross_references: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReasoningStep:
    """Sequential thinking step with transparency data"""
    step_id: str
    step_number: int
    thought: str
    reasoning_type: str  # "analysis", "synthesis", "validation", "correction"
    context_used: List[str]
    confidence_score: float
    timestamp: datetime
    self_correction: Optional[str] = None

@dataclass 
class TaskExecution:
    """Enhanced task execution with full transparency"""
    task_id: str
    task_type: str
    hybrid_context: HybridContext
    reasoning_steps: List[ReasoningStep]
    final_result: Optional[Dict[str, Any]] = None
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

class HybridOrchestratorState(TypedDict):
    user_request: str
    user_id: int
    session_id: str
    current_phase: str
    hybrid_context: HybridContext
    reasoning_steps: List[ReasoningStep]
    task_executions: List[TaskExecution]
    final_response: Optional[str]
    error: Optional[str]
    websocket_updates: List[Dict[str, Any]]

class HybridIntelligenceOrchestrator:
    """
    Enhanced Master Orchestrator with Hybrid Intelligence
    
    Integrates:
    - Memory Service (semantic + structured hybrid retrieval)
    - Sequential Thinking Service (LangGraph reasoning with self-correction)  
    - Real-time WebSocket transparency
    - Glass box agent operation visibility
    """
    
    def __init__(self, 
                 memory_service_url: str = "http://localhost:8001",
                 reasoning_service_url: str = "http://localhost:8002"):
        self.memory_service_url = memory_service_url
        self.reasoning_service_url = reasoning_service_url
        
        # WebSocket connections for real-time updates
        self.active_websockets: Dict[str, WebSocket] = {}
        
        # Build the orchestration graph
        self.graph = self._build_orchestration_graph()
        
        # HTTP clients for service communication
        self.http_client = httpx.AsyncClient(timeout=30.0)

    def _build_orchestration_graph(self):
        """Build LangGraph orchestration workflow"""
        workflow = StateGraph(HybridOrchestratorState)
        
        # Define orchestration nodes
        workflow.add_node("initialize_session", self._initialize_session_node)
        workflow.add_node("hybrid_retrieval", self._hybrid_retrieval_node)
        workflow.add_node("sequential_reasoning", self._sequential_reasoning_node)
        workflow.add_node("task_execution", self._task_execution_node)
        workflow.add_node("result_synthesis", self._result_synthesis_node)
        workflow.add_node("finalize_response", self._finalize_response_node)
        
        # Define workflow edges
        workflow.set_entry_point("initialize_session")
        workflow.add_edge("initialize_session", "hybrid_retrieval")
        workflow.add_edge("hybrid_retrieval", "sequential_reasoning")
        workflow.add_edge("sequential_reasoning", "task_execution")
        workflow.add_edge("task_execution", "result_synthesis")
        workflow.add_edge("result_synthesis", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        # Add error handling
        workflow.add_conditional_edges(
            "hybrid_retrieval",
            lambda state: "sequential_reasoning" if not state.get("error") else "finalize_response",
            {"sequential_reasoning": "sequential_reasoning", "finalize_response": "finalize_response"}
        )
        
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def process_request(self, 
                            user_request: str, 
                            user_id: int,
                            websocket: Optional[WebSocket] = None) -> Dict[str, Any]:
        """
        Main orchestration entry point with hybrid intelligence
        
        Args:
            user_request: The user's request to process
            user_id: ID of the requesting user
            websocket: Optional WebSocket for real-time updates
            
        Returns:
            Complete orchestration result with transparency data
        """
        session_id = str(uuid.uuid4())
        
        # Register WebSocket if provided
        if websocket:
            self.active_websockets[session_id] = websocket
        
        try:
            # Initialize orchestration state
            initial_state = {
                "user_request": user_request,
                "user_id": user_id,
                "session_id": session_id,
                "current_phase": "initializing",
                "hybrid_context": HybridContext(),
                "reasoning_steps": [],
                "task_executions": [],
                "final_response": None,
                "error": None,
                "websocket_updates": []
            }
            
            # Execute orchestration graph
            config = {"configurable": {"thread_id": session_id}}
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Clean up WebSocket
            if session_id in self.active_websockets:
                del self.active_websockets[session_id]
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestration failed for session {session_id}: {e}")
            
            # Send error update via WebSocket
            await self._send_websocket_update(session_id, {
                "type": "orchestration_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            # Clean up WebSocket
            if session_id in self.active_websockets:
                del self.active_websockets[session_id]
            
            raise

    # Orchestration Graph Nodes
    
    async def _initialize_session_node(self, state: HybridOrchestratorState) -> Dict[str, Any]:
        """Initialize orchestration session with transparency logging"""
        session_id = state["session_id"]
        
        await self._send_websocket_update(session_id, {
            "type": "orchestration_started",
            "phase": "initialization",
            "message": "🤖 Initializing hybrid intelligence orchestration...",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"🚀 Starting hybrid orchestration for session {session_id}")
        
        return {
            "current_phase": "hybrid_retrieval",
            "websocket_updates": state["websocket_updates"] + [{
                "phase": "initialization",
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    async def _hybrid_retrieval_node(self, state: HybridOrchestratorState) -> Dict[str, Any]:
        """Perform hybrid retrieval (semantic + structured)"""
        session_id = state["session_id"]
        user_request = state["user_request"]
        user_id = state["user_id"]
        
        await self._send_websocket_update(session_id, {
            "type": "hybrid_retrieval_started",
            "phase": "hybrid_retrieval", 
            "message": "🧠 Searching semantic memory...",
            "sub_phase": "semantic_search",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Perform hybrid search via Memory Service
            hybrid_search_payload = {
                "query": user_request,
                "search_type": "hybrid",  # Combines semantic + structured
                "limit": 10,
                "filters": {}
            }
            
            logger.info(f"🔍 Performing hybrid retrieval for: {user_request[:100]}...")
            
            response = await self.http_client.post(
                f"{self.memory_service_url}/hybrid_search",
                json=hybrid_search_payload,
                headers={"Authorization": f"Bearer {self._get_service_token()}"}
            )
            
            if response.status_code == 200:
                search_results = response.json()
                
                # Parse hybrid results
                hybrid_context = self._parse_hybrid_results(search_results["results"])
                
                # Send semantic search update
                await self._send_websocket_update(session_id, {
                    "type": "semantic_search_complete",
                    "phase": "hybrid_retrieval",
                    "message": f"🧠 Found {len(hybrid_context.semantic_memories)} semantic memories",
                    "sub_phase": "knowledge_graph_query",
                    "data": {
                        "semantic_count": len(hybrid_context.semantic_memories),
                        "entity_count": len(hybrid_context.knowledge_entities),
                        "relationship_count": len(hybrid_context.knowledge_relationships)
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send knowledge graph update  
                await self._send_websocket_update(session_id, {
                    "type": "knowledge_graph_complete", 
                    "phase": "hybrid_retrieval",
                    "message": f"🌐 Retrieved {len(hybrid_context.knowledge_entities)} entities and {len(hybrid_context.knowledge_relationships)} relationships",
                    "sub_phase": "context_synthesis",
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "current_phase": "sequential_reasoning",
                    "hybrid_context": hybrid_context,
                    "websocket_updates": state["websocket_updates"] + [{
                        "phase": "hybrid_retrieval",
                        "status": "completed",
                        "context_summary": {
                            "semantic_memories": len(hybrid_context.semantic_memories),
                            "knowledge_entities": len(hybrid_context.knowledge_entities),
                            "relationships": len(hybrid_context.knowledge_relationships)
                        },
                        "timestamp": datetime.now().isoformat()
                    }]
                }
            else:
                raise Exception(f"Memory service error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}")
            
            await self._send_websocket_update(session_id, {
                "type": "hybrid_retrieval_error",
                "phase": "hybrid_retrieval",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "current_phase": "sequential_reasoning", 
                "error": f"Hybrid retrieval failed: {str(e)}",
                "hybrid_context": HybridContext()  # Empty context as fallback
            }
    
    async def _sequential_reasoning_node(self, state: HybridOrchestratorState) -> Dict[str, Any]:
        """Delegate to Sequential Thinking Service with enhanced context"""
        session_id = state["session_id"]
        user_request = state["user_request"]
        user_id = state["user_id"]
        hybrid_context = state["hybrid_context"]
        
        await self._send_websocket_update(session_id, {
            "type": "sequential_reasoning_started",
            "phase": "sequential_reasoning",
            "message": "🤔 Beginning sequential reasoning with hybrid context...",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Prepare enhanced context for reasoning
            enhanced_context = self._prepare_reasoning_context(user_request, hybrid_context)
            
            # Create reasoning request
            reasoning_payload = {
                "query": user_request,
                "context": enhanced_context,
                "user_id": user_id,
                "session_id": session_id,
                "max_steps": 10,
                "enable_memory_integration": True,
                "enable_self_correction": True,
                "transparency_level": "full"  # Request full reasoning transparency
            }
            
            logger.info(f"🧠 Starting sequential reasoning with {len(enhanced_context)} context items")
            
            response = await self.http_client.post(
                f"{self.reasoning_service_url}/reason",
                json=reasoning_payload,
                headers={"Authorization": f"Bearer {self._get_service_token()}"}
            )
            
            if response.status_code == 200:
                reasoning_result = response.json()
                
                # Parse reasoning steps for transparency
                reasoning_steps = self._parse_reasoning_steps(reasoning_result.get("reasoning_steps", []))
                
                # Send reasoning updates
                for i, step in enumerate(reasoning_steps):
                    await self._send_websocket_update(session_id, {
                        "type": "reasoning_step",
                        "phase": "sequential_reasoning",
                        "step_number": i + 1,
                        "thought": step.thought,
                        "reasoning_type": step.reasoning_type,
                        "confidence": step.confidence_score,
                        "timestamp": step.timestamp.isoformat()
                    })
                
                await self._send_websocket_update(session_id, {
                    "type": "sequential_reasoning_complete",
                    "phase": "sequential_reasoning", 
                    "message": f"✅ Completed reasoning in {len(reasoning_steps)} steps",
                    "final_answer": reasoning_result.get("final_answer", ""),
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "current_phase": "task_execution",
                    "reasoning_steps": reasoning_steps,
                    "websocket_updates": state["websocket_updates"] + [{
                        "phase": "sequential_reasoning",
                        "status": "completed",
                        "steps_count": len(reasoning_steps),
                        "final_answer": reasoning_result.get("final_answer", ""),
                        "timestamp": datetime.now().isoformat()
                    }]
                }
            else:
                raise Exception(f"Reasoning service error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Sequential reasoning failed: {e}")
            
            await self._send_websocket_update(session_id, {
                "type": "reasoning_error",
                "phase": "sequential_reasoning", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "current_phase": "task_execution",
                "error": f"Sequential reasoning failed: {str(e)}",
                "reasoning_steps": []
            }
    
    async def _task_execution_node(self, state: HybridOrchestratorState) -> Dict[str, Any]:
        """Execute tasks with full transparency"""
        session_id = state["session_id"]
        reasoning_steps = state.get("reasoning_steps", [])
        
        await self._send_websocket_update(session_id, {
            "type": "task_execution_started",
            "phase": "task_execution",
            "message": "⚡ Executing tasks based on reasoning analysis...", 
            "timestamp": datetime.now().isoformat()
        })
        
        # For now, create a simple task execution based on reasoning
        # In a full implementation, this would delegate to specific specialist agents
        
        task_execution = TaskExecution(
            task_id=str(uuid.uuid4()),
            task_type="reasoning_based_response",
            hybrid_context=state["hybrid_context"],
            reasoning_steps=reasoning_steps,
            final_result={
                "response_type": "analytical",
                "confidence": 0.85,
                "sources_used": len(state["hybrid_context"].semantic_memories) + len(state["hybrid_context"].knowledge_entities)
            },
            execution_metadata={
                "start_time": datetime.now().isoformat(),
                "execution_method": "hybrid_intelligence_orchestration"
            }
        )
        
        await self._send_websocket_update(session_id, {
            "type": "task_execution_complete",
            "phase": "task_execution",
            "message": "✅ Task execution completed successfully",
            "task_summary": {
                "task_type": task_execution.task_type,
                "confidence": task_execution.final_result.get("confidence", 0.0),
                "sources_used": task_execution.final_result.get("sources_used", 0)
            },
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "current_phase": "result_synthesis",
            "task_executions": [task_execution],
            "websocket_updates": state["websocket_updates"] + [{
                "phase": "task_execution", 
                "status": "completed",
                "tasks_completed": 1,
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    async def _result_synthesis_node(self, state: HybridOrchestratorState) -> Dict[str, Any]:
        """Synthesize final results from all processing"""
        session_id = state["session_id"]
        reasoning_steps = state.get("reasoning_steps", [])
        task_executions = state.get("task_executions", [])
        
        await self._send_websocket_update(session_id, {
            "type": "result_synthesis_started",
            "phase": "result_synthesis",
            "message": "🔗 Synthesizing final response from all intelligence sources...",
            "timestamp": datetime.now().isoformat()
        })
        
        # Create comprehensive response
        final_answer = ""
        if reasoning_steps:
            final_answer = reasoning_steps[-1].thought if reasoning_steps else "Analysis completed."
        
        # Enhance with hybrid intelligence insights
        synthesis_data = {
            "reasoning_summary": f"Completed {len(reasoning_steps)} reasoning steps",
            "context_sources": {
                "semantic_memories": len(state["hybrid_context"].semantic_memories),
                "knowledge_entities": len(state["hybrid_context"].knowledge_entities),
                "relationships": len(state["hybrid_context"].knowledge_relationships)
            },
            "task_executions": len(task_executions),
            "confidence_score": 0.85
        }
        
        await self._send_websocket_update(session_id, {
            "type": "result_synthesis_complete",
            "phase": "result_synthesis",
            "message": "✨ Response synthesis completed",
            "synthesis_data": synthesis_data,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "current_phase": "finalization",
            "final_response": final_answer,
            "websocket_updates": state["websocket_updates"] + [{
                "phase": "result_synthesis",
                "status": "completed",
                "synthesis_data": synthesis_data,
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    async def _finalize_response_node(self, state: HybridOrchestratorState) -> Dict[str, Any]:
        """Finalize orchestration with complete transparency data"""
        session_id = state["session_id"]
        
        await self._send_websocket_update(session_id, {
            "type": "orchestration_complete",
            "phase": "complete",
            "message": "🎉 Hybrid intelligence orchestration completed successfully!",
            "final_response": state["final_response"],
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_phases": 6,
                "reasoning_steps": len(state.get("reasoning_steps", [])),
                "context_sources": len(state["hybrid_context"].semantic_memories) + len(state["hybrid_context"].knowledge_entities),
                "tasks_executed": len(state.get("task_executions", []))
            }
        })
        
        logger.info(f"✅ Hybrid orchestration completed for session {session_id}")
        
        return {
            "current_phase": "complete",
            "websocket_updates": state["websocket_updates"] + [{
                "phase": "finalization",
                "status": "completed", 
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    # Helper Methods
    
    def _parse_hybrid_results(self, search_results: List[Dict[str, Any]]) -> HybridContext:
        """Parse hybrid search results into structured context"""
        semantic_memories = []
        knowledge_entities = []
        knowledge_relationships = []
        cross_references = []
        
        for result in search_results:
            if result["source"] == "semantic":
                semantic_memories.append({
                    "content": result["content"],
                    "score": result["score"],
                    "metadata": result.get("semantic_metadata", {})
                })
            elif result["source"] == "structured":
                if result["result_type"] == "entity":
                    knowledge_entities.extend(result.get("entities", []))
                elif result["result_type"] == "relationship":
                    knowledge_relationships.extend(result.get("relationships", []))
            
            # Track cross-references
            if result.get("entities") and result.get("semantic_metadata"):
                cross_references.append({
                    "semantic_content": result["content"][:100],
                    "connected_entities": [e.get("entity_id") for e in result.get("entities", [])],
                    "score": result["score"]
                })
        
        return HybridContext(
            semantic_memories=semantic_memories,
            knowledge_entities=knowledge_entities,
            knowledge_relationships=knowledge_relationships,
            cross_references=cross_references,
            retrieval_metadata={
                "total_results": len(search_results),
                "semantic_count": len(semantic_memories),
                "entity_count": len(knowledge_entities),
                "relationship_count": len(knowledge_relationships),
                "retrieval_timestamp": datetime.now().isoformat()
            }
        )
    
    def _prepare_reasoning_context(self, user_request: str, hybrid_context: HybridContext) -> List[str]:
        """Prepare enhanced context for sequential reasoning"""
        context_items = []
        
        # Add semantic memory context
        for memory in hybrid_context.semantic_memories[:5]:  # Top 5 most relevant
            context_items.append(f"Previous conversation: {memory['content'][:200]}... (Relevance: {memory['score']:.2f})")
        
        # Add knowledge graph entity context
        for entity in hybrid_context.knowledge_entities[:3]:  # Top 3 entities
            props = entity.get("properties", {})
            name = props.get("name", entity.get("entity_id", "Unknown"))
            entity_type = entity.get("entity_type", "Unknown")
            context_items.append(f"Known entity: {name} (Type: {entity_type})")
        
        # Add relationship context
        for rel in hybrid_context.knowledge_relationships[:3]:  # Top 3 relationships
            source = rel.get("source_entity_id", "")
            target = rel.get("target_entity_id", "")
            rel_type = rel.get("relationship_type", "")
            context_items.append(f"Relationship: {source} {rel_type} {target}")
        
        return context_items
    
    def _parse_reasoning_steps(self, reasoning_data: List[Dict[str, Any]]) -> List[ReasoningStep]:
        """Parse reasoning steps from sequential thinking service"""
        steps = []
        
        for i, step_data in enumerate(reasoning_data):
            step = ReasoningStep(
                step_id=str(uuid.uuid4()),
                step_number=i + 1,
                thought=step_data.get("thought", ""),
                reasoning_type=step_data.get("type", "analysis"),
                context_used=step_data.get("context_used", []),
                confidence_score=step_data.get("confidence", 0.7),
                timestamp=datetime.fromisoformat(step_data.get("timestamp", datetime.now().isoformat())),
                self_correction=step_data.get("self_correction")
            )
            steps.append(step)
        
        return steps
    
    async def _send_websocket_update(self, session_id: str, update_data: Dict[str, Any]):
        """Send real-time update via WebSocket"""
        if session_id in self.active_websockets:
            try:
                websocket = self.active_websockets[session_id]
                await websocket.send_json(update_data)
            except Exception as e:
                logger.debug(f"WebSocket update failed for session {session_id}: {e}")
                # Remove broken WebSocket connection
                if session_id in self.active_websockets:
                    del self.active_websockets[session_id]
    
    def _get_service_token(self) -> str:
        """Get service authentication token - placeholder for now"""
        # In a real implementation, this would generate or retrieve a proper service token
        return "service_token_placeholder"
    
    async def cleanup(self):
        """Clean up resources"""
        await self.http_client.aclose()

# Global instance
hybrid_orchestrator = HybridIntelligenceOrchestrator()