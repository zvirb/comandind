"""
Service Proxy Router - Proxy requests to isolated microservices
Provides unified API access to chat service (8007) and voice service (8006)
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import StreamingResponse, Response
import json

from api.dependencies import get_current_user
from shared.database.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Service configurations
CHAT_SERVICE_URL = "http://chat-service:8007"
VOICE_SERVICE_URL = "http://voice-interaction-service:8006"

class ServiceProxyError(Exception):
    """Custom exception for service proxy errors"""
    pass

async def proxy_request(
    service_url: str,
    endpoint: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Proxy a request to a microservice"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = f"{service_url}{endpoint}"
            
            if method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                if files:
                    response = await client.post(url, files=files)
                else:
                    response = await client.post(url, json=json_data)
            else:
                raise ServiceProxyError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Service request failed: {response.status_code} - {response.text}")
                raise ServiceProxyError(f"Service returned {response.status_code}")
                
    except httpx.TimeoutException:
        logger.error(f"Service request timeout to {service_url}{endpoint}")
        raise ServiceProxyError("Service request timeout")
    except Exception as e:
        logger.error(f"Service proxy error: {e}")
        raise ServiceProxyError(f"Service communication error: {str(e)}")

# Chat Service Proxy Endpoints
@router.get("/chat/health")
async def chat_service_health():
    """Proxy chat service health check"""
    try:
        result = await proxy_request(CHAT_SERVICE_URL, "/health", timeout=5.0)
        return result
    except ServiceProxyError as e:
        return {
            "status": "offline",
            "service": "chat-service",
            "error": str(e),
            "proxy_status": "failed"
        }
    except Exception as e:
        logger.error(f"Chat health check error: {e}")
        return {
            "status": "error",
            "service": "chat-service",
            "error": "Health check failed",
            "proxy_status": "error"
        }

@router.post("/chat")
async def chat_proxy(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Proxy chat requests to dedicated chat service"""
    try:
        # Add user context to request
        enhanced_request = {
            **request,
            "user_id": str(current_user.id),
            "user_email": current_user.email
        }
        
        result = await proxy_request(
            CHAT_SERVICE_URL, 
            "/api/v1/chat", 
            method="POST", 
            json_data=enhanced_request,
            timeout=60.0  # Longer timeout for chat processing
        )
        return result
        
    except ServiceProxyError as e:
        logger.error(f"Chat proxy error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Chat service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected chat proxy error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal chat processing error"
        )

@router.get("/chat/history/{session_id}")
async def chat_history_proxy(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Proxy chat history requests"""
    try:
        result = await proxy_request(
            CHAT_SERVICE_URL, 
            f"/api/v1/chat/history/{session_id}"
        )
        return result
        
    except ServiceProxyError as e:
        logger.error(f"Chat history proxy error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Chat service unavailable: {str(e)}"
        )

@router.get("/chat/stats")
async def chat_stats_proxy(current_user: User = Depends(get_current_user)):
    """Proxy chat service statistics"""
    try:
        result = await proxy_request(CHAT_SERVICE_URL, "/api/v1/chat/stats")
        return result
        
    except ServiceProxyError as e:
        logger.error(f"Chat stats proxy error: {e}")
        return {
            "active_connections": 0,
            "active_users": 0,
            "service_uptime": 0,
            "proxy_status": "offline",
            "error": str(e)
        }

# Voice Service Proxy Endpoints
@router.get("/voice/health")
async def voice_service_health():
    """Proxy voice service health check"""
    try:
        result = await proxy_request(VOICE_SERVICE_URL, "/health", timeout=5.0)
        return result
    except ServiceProxyError as e:
        return {
            "status": "offline",
            "service": "voice-interaction",
            "error": str(e),
            "proxy_status": "failed"
        }
    except Exception as e:
        logger.error(f"Voice health check error: {e}")
        return {
            "status": "error",
            "service": "voice-interaction",
            "error": "Health check failed",
            "proxy_status": "error"
        }

@router.post("/voice/stt/transcribe")
async def voice_transcribe_proxy(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Proxy speech-to-text requests to voice service"""
    try:
        # Read audio file
        audio_content = await audio.read()
        
        # Prepare files for proxy
        files = {
            "audio": (audio.filename or "recording.webm", audio_content, audio.content_type or "audio/webm")
        }
        
        # Add authentication header
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create request with JWT token
            from api.auth import create_access_token
            token = create_access_token(data={"sub": str(current_user.id)})
            
            response = await client.post(
                f"{VOICE_SERVICE_URL}/stt/transcribe",
                files=files,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Voice transcription failed: {response.status_code} - {response.text}")
                raise ServiceProxyError(f"Transcription service returned {response.status_code}")
                
    except ServiceProxyError as e:
        logger.error(f"Voice transcription proxy error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Voice service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected voice transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal transcription processing error"
        )

@router.post("/voice/tts/synthesize")
async def voice_synthesize_proxy(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Proxy text-to-speech requests to voice service"""
    try:
        # Add authentication and make request
        from api.auth import create_access_token
        token = create_access_token(data={"sub": str(current_user.id)})
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{VOICE_SERVICE_URL}/tts/synthesize",
                json=request,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                # Return audio stream
                return StreamingResponse(
                    iter([response.content]),
                    media_type="audio/wav",
                    headers={"Content-Disposition": "inline; filename=synthesized_speech.wav"}
                )
            else:
                logger.error(f"Voice synthesis failed: {response.status_code} - {response.text}")
                raise ServiceProxyError(f"Synthesis service returned {response.status_code}")
                
    except ServiceProxyError as e:
        logger.error(f"Voice synthesis proxy error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Voice service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected voice synthesis error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal synthesis processing error"
        )

@router.get("/voice/models/status")
async def voice_models_status_proxy(current_user: User = Depends(get_current_user)):
    """Proxy voice models status"""
    try:
        from api.auth import create_access_token
        token = create_access_token(data={"sub": str(current_user.id)})
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{VOICE_SERVICE_URL}/models/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise ServiceProxyError(f"Models status service returned {response.status_code}")
                
    except ServiceProxyError as e:
        logger.error(f"Voice models status proxy error: {e}")
        return {
            "vosk": {"loaded": False},
            "whisper": {"loaded": False},
            "device_info": {"cuda_available": False},
            "proxy_status": "offline",
            "error": str(e)
        }

# Database Service Health (for completeness)
@router.get("/database/health")
async def database_health_proxy():
    """Database health check (internal)"""
    try:
        # Import database utilities
        from shared.utils.database_setup import get_async_session
        from sqlalchemy import text
        
        # Test database connectivity
        async with get_async_session() as session:
            result = await session.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "service": "database",
                "connection": "active",
                "proxy_status": "internal"
            }
            
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        return {
            "status": "unhealthy",
            "service": "database",
            "error": str(e),
            "proxy_status": "internal"
        }

# Service status overview
@router.get("/services/status")
async def services_status_overview():
    """Get overall status of all proxied services"""
    status_results = {}
    
    # Check chat service
    try:
        chat_health = await proxy_request(CHAT_SERVICE_URL, "/health", timeout=5.0)
        status_results["chat"] = {
            "status": chat_health.get("status", "unknown"),
            "service": "chat-service",
            "port": 8007,
            "proxy_status": "connected"
        }
    except Exception as e:
        status_results["chat"] = {
            "status": "offline",
            "service": "chat-service", 
            "port": 8007,
            "proxy_status": "failed",
            "error": str(e)
        }
    
    # Check voice service
    try:
        voice_health = await proxy_request(VOICE_SERVICE_URL, "/health", timeout=5.0)
        status_results["voice"] = {
            "status": voice_health.get("status", "unknown"),
            "service": "voice-interaction",
            "port": 8006,
            "proxy_status": "connected"
        }
    except Exception as e:
        status_results["voice"] = {
            "status": "offline",
            "service": "voice-interaction",
            "port": 8006,
            "proxy_status": "failed", 
            "error": str(e)
        }
    
    # Check database
    try:
        db_health = await database_health_proxy()
        status_results["database"] = db_health
    except Exception as e:
        status_results["database"] = {
            "status": "offline",
            "service": "database",
            "proxy_status": "failed",
            "error": str(e)
        }
    
    # Calculate overall status
    all_statuses = [service.get("status") for service in status_results.values()]
    if all(status == "healthy" for status in all_statuses):
        overall_status = "healthy"
    elif any(status in ["healthy", "degraded"] for status in all_statuses):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "overall_status": overall_status,
        "services": status_results,
        "proxy_version": "1.0.0"
    }