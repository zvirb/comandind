"""
Dedicated Chat Service - WebSocket Chat with JWT Authentication
Implements isolated chat functionality with WebSocket support and JWT query parameter authentication.
Follows container isolation principles as a separate, independent service.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chat Service",
    description="Dedicated chat service with WebSocket support and JWT authentication",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
redis_client = None
connection_manager = None
ollama_client = None

class ConnectionManager:
    """Manages WebSocket connections with authentication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Accept WebSocket connection and register user session"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        logger.info(f"WebSocket connected: session_id={session_id}, user_id={user_id}")
        
    def disconnect(self, session_id: str):
        """Remove connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            # Remove from user sessions
            for user_id, sess_id in list(self.user_sessions.items()):
                if sess_id == session_id:
                    del self.user_sessions[user_id]
                    break
        logger.info(f"WebSocket disconnected: session_id={session_id}")
        
    async def send_personal_message(self, message: str, session_id: str):
        """Send message to specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
                return False
        return False
        
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)

class ChatService:
    """Core chat processing service"""
    
    def __init__(self):
        self.redis_client = None
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        
    async def initialize(self, redis_client):
        """Initialize chat service with dependencies"""
        self.redis_client = redis_client
        
    async def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token by calling main API service"""
        try:
            api_base_url = os.getenv("API_BASE_URL", "http://api:8000")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{api_base_url}/api/v1/auth/verify-token",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Token verification failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
            
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve chat history from Redis"""
        try:
            if not self.redis_client:
                return []
                
            # Get messages from Redis sorted set
            history_key = f"chat_history:{session_id}"
            messages = await self.redis_client.zrevrange(
                history_key, 0, limit-1, withscores=True
            )
            
            chat_history = []
            for message_data, timestamp in messages:
                try:
                    message = json.loads(message_data)
                    message['timestamp'] = timestamp
                    chat_history.append(message)
                except json.JSONDecodeError:
                    continue
                    
            return list(reversed(chat_history))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []
            
    async def save_message(self, session_id: str, message: Dict[str, Any]):
        """Save message to Redis with timestamp"""
        try:
            if not self.redis_client:
                return
                
            history_key = f"chat_history:{session_id}"
            timestamp = time.time()
            message_data = json.dumps(message)
            
            # Add to sorted set with timestamp as score
            await self.redis_client.zadd(history_key, {message_data: timestamp})
            
            # Keep only last 1000 messages
            await self.redis_client.zremrangebyrank(history_key, 0, -1001)
            
            # Set expiration (30 days)
            await self.redis_client.expire(history_key, 30 * 24 * 3600)
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            
    async def process_chat_message(self, user_input: str, session_id: str, user_id: str, 
                                 chat_model: str = "llama3.2:3b") -> Dict[str, Any]:
        """Process chat message using Ollama"""
        try:
            # Save user message
            user_message = {
                "id": str(uuid.uuid4()),
                "role": "user", 
                "content": user_input,
                "user_id": user_id,
                "timestamp": time.time()
            }
            await self.save_message(session_id, user_message)
            
            # Get recent chat history for context
            history = await self.get_chat_history(session_id, limit=10)
            
            # Prepare messages for Ollama
            ollama_messages = []
            for msg in history[-5:]:  # Use last 5 messages for context
                ollama_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
                
            # Add current message
            ollama_messages.append({"role": "user", "content": user_input})
            
            # Call Ollama API
            ollama_response = await self.call_ollama(ollama_messages, chat_model)
            
            # Save assistant response
            assistant_message = {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": ollama_response.get("response", "Sorry, I couldn't process your request."),
                "model": chat_model,
                "timestamp": time.time()
            }
            await self.save_message(session_id, assistant_message)
            
            return {
                "response": assistant_message["content"],
                "message_id": assistant_message["id"],
                "session_id": session_id,
                "model": chat_model,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            error_response = {
                "response": "I apologize, but I encountered an error processing your message. Please try again.",
                "message_id": str(uuid.uuid4()),
                "session_id": session_id,
                "status": "error",
                "error": str(e)
            }
            
            # Save error message
            error_message = {
                "id": error_response["message_id"],
                "role": "assistant",
                "content": error_response["response"],
                "error": True,
                "timestamp": time.time()
            }
            await self.save_message(session_id, error_message)
            
            return error_response
            
    async def call_ollama(self, messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
        """Call Ollama API for chat completion"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return {"response": "Error communicating with AI model"}
                    
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return {"response": "Error communicating with AI model"}

# Global service instances
chat_service = ChatService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global redis_client, connection_manager
    
    # Initialize Redis connection with authentication
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_user = os.getenv("REDIS_USER", "lwe-app")
    redis_password = os.getenv("REDIS_PASSWORD", "")
    redis_db = int(os.getenv("REDIS_DB", "5"))
    
    redis_client = aioredis.Redis(
        host=redis_host,
        port=redis_port,
        username=redis_user,
        password=redis_password,
        db=redis_db,
        decode_responses=True
    )
    
    # Initialize connection manager
    connection_manager = ConnectionManager()
    
    # Initialize chat service
    await chat_service.initialize(redis_client)
    
    logger.info("Chat Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    logger.info("Chat Service stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Test Redis connection
    redis_status = "unknown"
    try:
        if redis_client:
            await redis_client.ping()
            redis_status = "connected"
    except Exception:
        redis_status = "disconnected"
    
    # Test Ollama connection
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{chat_service.ollama_base_url}/api/tags")
            ollama_status = "connected" if response.status_code == 200 else "disconnected"
    except Exception:
        ollama_status = "disconnected"
    
    return {
        "status": "healthy",
        "service": "chat-service",
        "dependencies": {
            "redis": redis_status,
            "ollama": ollama_status
        },
        "active_connections": len(connection_manager.active_connections) if connection_manager else 0,
        "timestamp": time.time()
    }

@app.post("/api/v1/chat")
async def handle_chat_request(request: Dict[str, Any]):
    """HTTP endpoint for chat messages (REST fallback)"""
    try:
        message = request.get("message", "")
        session_id = request.get("session_id", str(uuid.uuid4()))
        user_id = request.get("user_id", "anonymous")
        chat_model = request.get("chat_model", "llama3.2:3b")
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
            
        # Process message
        response = await chat_service.process_chat_message(
            message, session_id, user_id, chat_model
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in HTTP chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/chat/history/{session_id}")
async def get_chat_history_endpoint(session_id: str, limit: int = 50):
    """Get chat history for a session"""
    try:
        history = await chat_service.get_chat_history(session_id, limit)
        return {"history": history, "session_id": session_id}
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication"),
    session_id: Optional[str] = Query(None, description="Chat session ID")
):
    """
    WebSocket endpoint for real-time chat with JWT authentication via query parameters.
    Usage: /ws/chat?token=<jwt_token>&session_id=<optional_session_id>
    """
    if not session_id:
        session_id = str(uuid.uuid4())
        
    # Verify JWT token
    user_data = await chat_service.verify_jwt_token(token)
    if not user_data:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
        
    user_id = str(user_data.get("user_id", "unknown"))
    
    # Connect to WebSocket
    await connection_manager.connect(websocket, session_id, user_id)
    
    # Send welcome message with session info
    welcome_message = {
        "type": "welcome",
        "session_id": session_id,
        "user_id": user_id,
        "message": "Connected to chat service",
        "timestamp": time.time()
    }
    await connection_manager.send_personal_message(json.dumps(welcome_message), session_id)
    
    # Send recent chat history
    try:
        history = await chat_service.get_chat_history(session_id, limit=10)
        if history:
            history_message = {
                "type": "history",
                "session_id": session_id,
                "history": history,
                "timestamp": time.time()
            }
            await connection_manager.send_personal_message(json.dumps(history_message), session_id)
    except Exception as e:
        logger.error(f"Error sending chat history: {e}")
    
    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "chat")
                
                if message_type == "chat":
                    user_input = message_data.get("message", "")
                    chat_model = message_data.get("chat_model", user_data.get("chat_model", "llama3.2:3b"))
                    
                    if user_input.strip():
                        # Process chat message
                        response = await chat_service.process_chat_message(
                            user_input, session_id, user_id, chat_model
                        )
                        
                        # Send response back
                        response_message = {
                            "type": "response",
                            "session_id": session_id,
                            **response,
                            "timestamp": time.time()
                        }
                        await connection_manager.send_personal_message(
                            json.dumps(response_message), session_id
                        )
                
                elif message_type == "ping":
                    # Handle ping/keepalive
                    pong_message = {
                        "type": "pong",
                        "session_id": session_id,
                        "timestamp": time.time()
                    }
                    await connection_manager.send_personal_message(
                        json.dumps(pong_message), session_id
                    )
                    
            except json.JSONDecodeError:
                error_message = {
                    "type": "error",
                    "session_id": session_id,
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                }
                await connection_manager.send_personal_message(
                    json.dumps(error_message), session_id
                )
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(session_id)

@app.get("/api/v1/chat/stats")
async def get_chat_stats():
    """Get chat service statistics"""
    return {
        "active_connections": len(connection_manager.active_connections) if connection_manager else 0,
        "active_users": len(connection_manager.user_sessions) if connection_manager else 0,
        "service_uptime": time.time(),
        "timestamp": time.time()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        reload=False,
        log_level="info"
    )