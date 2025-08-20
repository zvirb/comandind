"""
Sequential Thinking Service Main Application
FastAPI microservice for LangGraph-based reasoning with Redis checkpointing
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

from .config import get_settings
from .models import (
    ReasoningRequest, ReasoningResponse, ReasoningStatus, 
    MemoryIntegrationRequest, CheckpointInfo
)
from .services import (
    LangGraphReasoningService,
    RedisCheckpointService,
    OllamaClientService,
    MemoryIntegrationService,
    AuthenticationService
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize services as global variables (will be set during startup)
reasoning_service: Optional[LangGraphReasoningService] = None
redis_checkpoint: Optional[RedisCheckpointService] = None
ollama_client: Optional[OllamaClientService] = None
memory_service: Optional[MemoryIntegrationService] = None
auth_service: Optional[AuthenticationService] = None

# WebSocket connections for real-time updates
active_websockets: Dict[str, WebSocket] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown"""
    # Startup
    logger.info("Starting Sequential Thinking Service...")
    
    try:
        # Initialize all services
        global reasoning_service, redis_checkpoint, ollama_client, memory_service, auth_service
        
        # Initialize Redis checkpoint service
        redis_checkpoint = RedisCheckpointService()
        await redis_checkpoint.initialize()
        logger.info("✓ Redis checkpoint service initialized")
        
        # Initialize Ollama client
        ollama_client = OllamaClientService()
        await ollama_client.initialize()
        logger.info("✓ Ollama client service initialized")
        
        # Initialize memory integration service
        memory_service = MemoryIntegrationService()
        await memory_service.initialize()
        logger.info("✓ Memory integration service initialized")
        
        # Initialize authentication service
        auth_service = AuthenticationService()
        logger.info("✓ Authentication service initialized")
        
        # Initialize main reasoning service
        reasoning_service = LangGraphReasoningService()
        await reasoning_service.initialize(redis_checkpoint, ollama_client, memory_service)
        logger.info("✓ LangGraph reasoning service initialized")
        
        # Start background cleanup task
        asyncio.create_task(periodic_cleanup())
        
        logger.info(f"🧠 Sequential Thinking Service started successfully on port {settings.PORT}")
        logger.info(f"🔧 Redis checkpointing: {'Enabled' if redis_checkpoint else 'Disabled'}")
        logger.info(f"🤖 Ollama models: Primary={settings.OLLAMA_PRIMARY_MODEL}, Backup={settings.OLLAMA_BACKUP_MODEL}")
        logger.info(f"🧠 Memory integration: {'Enabled' if memory_service else 'Disabled'}")
        
    except Exception as e:
        logger.error(f"💥 Failed to initialize Sequential Thinking Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sequential Thinking Service...")
    
    # Close all services
    if ollama_client:
        await ollama_client.close()
    if memory_service:
        await memory_service.close()
    if redis_checkpoint:
        await redis_checkpoint.close()
    
    logger.info("Sequential Thinking Service shutdown complete")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="AI Workflow Engine - Sequential Thinking Service",
    description="LangGraph-based reasoning service with Redis checkpointing and self-healing capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://aiwfe.com", "http://aiwfe.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()


# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Validate JWT token and return user information"""
    if not auth_service:
        raise HTTPException(status_code=503, detail="Authentication service not initialized")
    
    try:
        user = await auth_service.validate_token(credentials.credentials)
        
        # Check reasoning permissions
        if not await auth_service.check_reasoning_permissions(user):
            raise HTTPException(status_code=403, detail="Insufficient permissions for reasoning operations")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    services_status = {
        "reasoning_service": reasoning_service is not None,
        "redis_checkpoint": redis_checkpoint is not None and redis_checkpoint._initialized,
        "ollama_client": ollama_client is not None,
        "memory_service": memory_service is not None,
        "auth_service": auth_service is not None
    }
    
    all_healthy = all(services_status.values())
    
    # Get additional stats if services are available
    stats = {}
    if redis_checkpoint:
        try:
            stats["checkpoint_stats"] = await redis_checkpoint.get_checkpoint_stats()
        except:
            pass
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": services_status,
        "version": "1.0.0",
        "stats": stats,
        "settings": {
            "max_thinking_steps": settings.MAX_THINKING_STEPS,
            "checkpoint_enabled": settings.ENABLE_SELF_HEALING,
            "concurrent_limit": settings.CONCURRENT_REASONING_LIMIT
        }
    }


# Main reasoning endpoint
@app.post("/reason", response_model=ReasoningResponse)
async def execute_reasoning(
    request: ReasoningRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute sequential reasoning with self-healing capabilities
    
    This endpoint provides advanced reasoning using LangGraph with:
    - Redis-based state checkpointing for fault tolerance
    - Self-healing error recovery mechanisms  
    - Memory service integration for enhanced context
    - Progressive reasoning with validation loops
    """
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    try:
        # Set user context
        request.user_id = auth_service.extract_user_id(current_user)
        
        # Validate request parameters
        if request.max_steps > settings.MAX_THINKING_STEPS:
            raise HTTPException(
                status_code=400, 
                detail=f"max_steps cannot exceed {settings.MAX_THINKING_STEPS}"
            )
        
        logger.info(f"🧠 Starting reasoning for user {request.user_id}: {request.query[:100]}...")
        
        # Execute reasoning
        response = await reasoning_service.execute_reasoning(request)
        
        # Broadcast completion to WebSocket if connected
        if request.session_id in active_websockets:
            try:
                await active_websockets[request.session_id].send_json({
                    "type": "reasoning_complete",
                    "session_id": request.session_id,
                    "success": response.success,
                    "final_answer": response.final_answer
                })
            except:
                pass  # WebSocket might be closed
        
        logger.info(f"✅ Reasoning completed for session {response.session_id}: {response.state}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Reasoning execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Reasoning failed: {str(e)}")


# Session status endpoint
@app.get("/sessions/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get status of a reasoning session"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    try:
        status = await reasoning_service.get_session_status(session_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "status": status,
            "user_id": auth_service.extract_user_id(current_user)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cancel session endpoint
@app.post("/sessions/{session_id}/cancel")
async def cancel_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cancel an active reasoning session"""
    if not reasoning_service:
        raise HTTPException(status_code=503, detail="Reasoning service not initialized")
    
    try:
        success = await reasoning_service.cancel_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or already completed")
        
        return {
            "session_id": session_id,
            "cancelled": True,
            "message": "Session cancellation requested"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Memory integration endpoints
@app.post("/memory/context")
async def get_memory_context(
    request: MemoryIntegrationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get relevant context from memory service"""
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not available")
    
    try:
        user_id = auth_service.extract_user_id(current_user) if request.user_id is None else request.user_id
        
        context = await memory_service.get_relevant_context(
            query=request.query,
            user_id=user_id,
            context_limit=request.context_limit,
            similarity_threshold=request.similarity_threshold
        )
        
        return context
        
    except Exception as e:
        logger.error(f"Error getting memory context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Checkpoint management endpoints
@app.get("/checkpoints/stats")
async def get_checkpoint_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get checkpoint storage statistics"""
    if not redis_checkpoint:
        raise HTTPException(status_code=503, detail="Checkpoint service not available")
    
    try:
        stats = await redis_checkpoint.get_checkpoint_stats()
        return {
            "checkpoint_stats": stats,
            "service_settings": {
                "redis_db": settings.REDIS_DB,
                "key_prefix": settings.REDIS_KEY_PREFIX,
                "save_frequency": settings.CHECKPOINT_SAVE_FREQUENCY
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting checkpoint stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/checkpoints/cleanup")
async def cleanup_expired_checkpoints(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Clean up expired checkpoints (admin only)"""
    if not redis_checkpoint:
        raise HTTPException(status_code=503, detail="Checkpoint service not available")
    
    # Check admin permissions
    user_roles = current_user.get("roles", [])
    if "admin" not in user_roles and "superuser" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin permissions required")
    
    try:
        cleaned_count = await redis_checkpoint.cleanup_expired_checkpoints()
        
        return {
            "cleaned_checkpoints": cleaned_count,
            "message": f"Successfully cleaned up {cleaned_count} expired checkpoints"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up checkpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time reasoning updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket connection for real-time reasoning updates"""
    await websocket.accept()
    active_websockets[session_id] = websocket
    
    try:
        logger.info(f"WebSocket connected for session {session_id}")
        
        while True:
            # Keep connection alive and handle any incoming messages
            try:
                data = await websocket.receive_text()
                # Echo back or handle commands
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
        if session_id in active_websockets:
            del active_websockets[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}")


# Background cleanup task
async def periodic_cleanup():
    """Periodic cleanup of expired checkpoints and sessions"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            
            if redis_checkpoint:
                cleaned = await redis_checkpoint.cleanup_expired_checkpoints()
                if cleaned > 0:
                    logger.info(f"🧹 Cleaned up {cleaned} expired checkpoints")
                    
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


# Development and debugging endpoints (only in debug mode)
if settings.DEBUG:
    
    @app.get("/debug/sessions")
    async def debug_active_sessions(current_user: Dict[str, Any] = Depends(get_current_user)):
        """Debug endpoint to view active sessions"""
        if not reasoning_service:
            return {"active_sessions": []}
        
        return {
            "active_sessions": list(reasoning_service._active_sessions.keys()),
            "websocket_connections": list(active_websockets.keys())
        }
    
    @app.post("/debug/test-reasoning")
    async def debug_test_reasoning(current_user: Dict[str, Any] = Depends(get_current_user)):
        """Debug endpoint to test reasoning with simple query"""
        if not reasoning_service:
            raise HTTPException(status_code=503, detail="Reasoning service not available")
        
        test_request = ReasoningRequest(
            query="What is 2 + 2?",
            max_steps=3,
            enable_memory_integration=False,
            enable_self_correction=False,
            user_id=auth_service.extract_user_id(current_user)
        )
        
        try:
            response = await reasoning_service.execute_reasoning(test_request)
            return {
                "test_result": "success",
                "response": response,
                "message": "Test reasoning completed successfully"
            }
        except Exception as e:
            return {
                "test_result": "failed", 
                "error": str(e),
                "message": "Test reasoning failed"
            }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )