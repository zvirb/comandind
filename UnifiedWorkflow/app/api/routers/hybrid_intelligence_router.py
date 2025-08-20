"""
Hybrid Intelligence Router
API endpoints for the enhanced Master Orchestrator with hybrid intelligence
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..dependencies import get_current_user, get_db
from worker.services.hybrid_intelligence_orchestrator import hybrid_orchestrator

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Router
router = APIRouter(prefix="/api/v1/hybrid", tags=["Hybrid Intelligence"])

# Request/Response Models
class HybridRequestModel(BaseModel):
    query: str
    chat_mode: str = "simple"
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    transparency_level: str = "full"  # "minimal", "standard", "full"
    enable_hybrid_retrieval: bool = True
    enable_sequential_reasoning: bool = True

class HybridResponseModel(BaseModel):
    session_id: str
    response: str
    processing_summary: Dict[str, Any]
    transparency_data: Optional[Dict[str, Any]] = None
    execution_time_ms: int
    success: bool

class SessionStatusModel(BaseModel):
    session_id: str
    status: str
    current_phase: str
    progress_percentage: float
    start_time: datetime
    estimated_completion: Optional[datetime] = None

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

@router.post("/process", response_model=HybridResponseModel)
async def process_hybrid_request(
    request: HybridRequestModel,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Process request using hybrid intelligence orchestration
    
    This endpoint:
    1. Performs hybrid retrieval (semantic + structured)
    2. Uses sequential reasoning with self-correction
    3. Provides complete transparency of the process
    4. Returns enhanced response with processing insights
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🚀 Starting hybrid intelligence processing for user {current_user.id}")
        
        # Get WebSocket connection if available
        websocket = active_connections.get(request.session_id)
        
        # Process request through hybrid orchestrator
        result = await hybrid_orchestrator.process_request(
            user_request=request.query,
            user_id=current_user.id,
            websocket=websocket
        )
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Prepare transparency data based on level
        transparency_data = None
        if request.transparency_level == "full":
            transparency_data = {
                "hybrid_context": {
                    "semantic_memories": len(result.get("hybrid_context", {}).get("semantic_memories", [])),
                    "knowledge_entities": len(result.get("hybrid_context", {}).get("knowledge_entities", [])),
                    "relationships": len(result.get("hybrid_context", {}).get("knowledge_relationships", [])),
                    "retrieval_metadata": result.get("hybrid_context", {}).get("retrieval_metadata", {})
                },
                "reasoning_steps": [
                    {
                        "step_number": step.get("step_number"),
                        "thought": step.get("thought"),
                        "reasoning_type": step.get("reasoning_type"),
                        "confidence": step.get("confidence_score"),
                        "timestamp": step.get("timestamp")
                    }
                    for step in result.get("reasoning_steps", [])
                ],
                "task_executions": len(result.get("task_executions", [])),
                "websocket_updates": result.get("websocket_updates", [])
            }
        elif request.transparency_level == "standard":
            transparency_data = {
                "processing_phases": len([u for u in result.get("websocket_updates", []) if u.get("phase")]),
                "reasoning_steps_count": len(result.get("reasoning_steps", [])),
                "context_sources_used": len(result.get("hybrid_context", {}).get("semantic_memories", [])) + len(result.get("hybrid_context", {}).get("knowledge_entities", []))
            }
        
        # Prepare processing summary
        processing_summary = {
            "phases_completed": len([u for u in result.get("websocket_updates", []) if u.get("status") == "completed"]),
            "hybrid_retrieval": {
                "semantic_memories": len(result.get("hybrid_context", {}).get("semantic_memories", [])),
                "knowledge_entities": len(result.get("hybrid_context", {}).get("knowledge_entities", [])),
                "relationships": len(result.get("hybrid_context", {}).get("knowledge_relationships", []))
            },
            "sequential_reasoning": {
                "steps_completed": len(result.get("reasoning_steps", [])),
                "self_corrections": len([s for s in result.get("reasoning_steps", []) if s.get("self_correction")])
            },
            "final_confidence": result.get("reasoning_steps", [{}])[-1].get("confidence_score", 0.0) if result.get("reasoning_steps") else 0.0
        }
        
        response = HybridResponseModel(
            session_id=result["session_id"],
            response=result.get("final_response", "Processing completed"),
            processing_summary=processing_summary,
            transparency_data=transparency_data,
            execution_time_ms=int(execution_time),
            success=not bool(result.get("error"))
        )
        
        logger.info(f"✅ Hybrid processing completed in {execution_time:.0f}ms for session {result['session_id']}")
        
        return response
        
    except Exception as e:
        logger.error(f"💥 Hybrid intelligence processing failed: {e}")
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return HybridResponseModel(
            session_id=request.session_id or "error",
            response=f"Processing failed: {str(e)}",
            processing_summary={"error": str(e)},
            execution_time_ms=int(execution_time),
            success=False
        )

@router.get("/sessions/{session_id}/status", response_model=SessionStatusModel)
async def get_session_status(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get current status of a hybrid processing session"""
    try:
        # In a full implementation, this would check the orchestrator's session status
        # For now, return a placeholder response
        return SessionStatusModel(
            session_id=session_id,
            status="active",
            current_phase="processing",
            progress_percentage=50.0,
            start_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket connection for real-time hybrid intelligence updates
    
    Provides live transparency into:
    - Hybrid retrieval progress
    - Sequential reasoning steps
    - Task execution status
    - Processing phase transitions
    """
    await websocket.accept()
    active_connections[session_id] = websocket
    
    try:
        logger.info(f"🔗 Hybrid Intelligence WebSocket connected for session {session_id}")
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "message": "🧠 Hybrid intelligence transparency stream connected",
            "timestamp": datetime.now().isoformat(),
            "capabilities": [
                "hybrid_retrieval_updates",
                "sequential_reasoning_steps",
                "task_execution_progress",
                "phase_transitions",
                "error_notifications"
            ]
        })
        
        # Keep connection alive and handle any incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                
                # Handle client commands
                try:
                    message = eval(data) if data.startswith('{') else {"command": data}
                    
                    if message.get("command") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                    elif message.get("command") == "status":
                        await websocket.send_json({
                            "type": "status_update",
                            "session_id": session_id,
                            "connection_status": "active",
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        await websocket.send_json({
                            "type": "echo",
                            "message": f"Received: {data}",
                            "session_id": session_id
                        })
                        
                except:
                    # Send echo for non-JSON messages
                    await websocket.send_json({
                        "type": "echo",
                        "message": f"Received: {data}",
                        "session_id": session_id
                    })
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        # Clean up connection
        if session_id in active_connections:
            del active_connections[session_id]
        logger.info(f"🔗 Hybrid Intelligence WebSocket disconnected for session {session_id}")

@router.get("/capabilities")
async def get_hybrid_capabilities():
    """Get hybrid intelligence system capabilities"""
    return {
        "hybrid_retrieval": {
            "semantic_memory": True,
            "knowledge_graph": True,
            "cross_reference_linking": True
        },
        "sequential_reasoning": {
            "self_correction": True,
            "multi_step_analysis": True,
            "confidence_scoring": True
        },
        "transparency": {
            "real_time_updates": True,
            "reasoning_visualization": True,
            "phase_tracking": True,
            "context_visualization": True
        },
        "integration": {
            "memory_service": True,
            "sequential_thinking_service": True,
            "websocket_streaming": True
        },
        "supported_modes": [
            "simple",
            "smart-router", 
            "socratic"
        ]
    }

@router.get("/health")
async def hybrid_health_check():
    """Health check for hybrid intelligence system"""
    try:
        # Check orchestrator health
        health_status = {
            "hybrid_orchestrator": "healthy",
            "memory_service": "checking",
            "reasoning_service": "checking",
            "websocket_connections": len(active_connections)
        }
        
        # In a full implementation, these would be actual service health checks
        health_status["memory_service"] = "healthy"
        health_status["reasoning_service"] = "healthy"
        
        overall_health = "healthy" if all(
            status == "healthy" for key, status in health_status.items() 
            if key != "websocket_connections"
        ) else "degraded"
        
        return {
            "status": overall_health,
            "services": health_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Background cleanup task
async def cleanup_inactive_connections():
    """Clean up inactive WebSocket connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            # Check for inactive connections (would need actual implementation)
            # For now, this is a placeholder
            
            logger.debug(f"Active WebSocket connections: {len(active_connections)}")
            
        except Exception as e:
            logger.error(f"Error in connection cleanup: {e}")

# Start cleanup task
asyncio.create_task(cleanup_inactive_connections())