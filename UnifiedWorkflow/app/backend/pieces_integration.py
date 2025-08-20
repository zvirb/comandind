"""
Pieces OS Integration Module for AIWFE
Provides connectivity between Pieces OS/Developers and AIWFE ecosystem
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import jwt
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Environment variables
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://aiwfe-unified-gateway:8000")
COGNITIVE_SERVICES_URL = os.getenv("COGNITIVE_SERVICES_URL", "http://aiwfe-cognitive-services:8001")
DATA_PLATFORM_URL = os.getenv("DATA_PLATFORM_URL", "http://aiwfe-data-platform:8100")
REDIS_URL = os.getenv("REDIS_URL", "redis://aiwfe-data-platform:6379/2")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "")
API_KEY = os.getenv("API_KEY", "")
PIECES_API_KEY = os.getenv("PIECES_API_KEY", "")

# Metrics
request_counter = Counter("pieces_requests_total", "Total Pieces API requests", ["method", "endpoint"])
request_duration = Histogram("pieces_request_duration_seconds", "Request duration", ["method", "endpoint"])
active_connections = Gauge("pieces_active_connections", "Active connections to Pieces")
error_counter = Counter("pieces_errors_total", "Total errors", ["error_type"])

# Security
security = HTTPBearer()

# Pydantic models
class CodeSnippet(BaseModel):
    """Code snippet model for Pieces integration"""
    id: Optional[str] = Field(None, description="Snippet ID")
    title: str = Field(..., description="Snippet title")
    code: str = Field(..., description="Code content")
    language: str = Field(..., description="Programming language")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class WorkflowContext(BaseModel):
    """Workflow context model for developer productivity"""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    context_type: str = Field(..., description="Context type (research, coding, debugging, etc.)")
    context_data: Dict[str, Any] = Field(..., description="Context data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AIAssistanceRequest(BaseModel):
    """AI assistance request model"""
    query: str = Field(..., description="User query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    model: str = Field(default="gpt-4", description="AI model to use")
    max_tokens: int = Field(default=1000, description="Maximum tokens")

class AIAssistanceResponse(BaseModel):
    """AI assistance response model"""
    response: str = Field(..., description="AI response")
    suggestions: List[str] = Field(default_factory=list, description="Code suggestions")
    references: List[Dict[str, Any]] = Field(default_factory=list, description="Reference materials")
    confidence: float = Field(..., description="Confidence score")

class PiecesConnector:
    """Main Pieces OS connector class"""
    
    def __init__(self):
        self.redis_client = None
        self.session = None
        self.cache = {}
        
    async def initialize(self):
        """Initialize connections and resources"""
        try:
            # Initialize Redis connection
            self.redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
            
            # Initialize HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            logger.info("Pieces OS Connector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Pieces Connector: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(
                credentials.credentials,
                JWT_SECRET,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def store_snippet(self, snippet: CodeSnippet, user_id: str) -> str:
        """Store code snippet with AI enrichment"""
        try:
            # Generate unique ID
            snippet_id = f"snippet_{user_id}_{datetime.utcnow().timestamp()}"
            snippet.id = snippet_id
            snippet.created_at = datetime.utcnow()
            
            # Enrich with AI analysis
            enrichment = await self._enrich_snippet(snippet)
            snippet.metadata.update(enrichment)
            
            # Store in Redis
            key = f"pieces:snippets:{user_id}:{snippet_id}"
            await self.redis_client.setex(
                key,
                86400,  # 24 hours TTL
                json.dumps(snippet.dict(), default=str)
            )
            
            # Store in data platform
            await self._sync_to_data_platform(snippet, user_id)
            
            logger.info(f"Stored snippet {snippet_id} for user {user_id}")
            return snippet_id
            
        except Exception as e:
            logger.error(f"Failed to store snippet: {e}")
            error_counter.labels(error_type="store_snippet").inc()
            raise HTTPException(status_code=500, detail="Failed to store snippet")
    
    async def _enrich_snippet(self, snippet: CodeSnippet) -> Dict[str, Any]:
        """Enrich snippet with AI analysis"""
        try:
            async with self.session.post(
                f"{COGNITIVE_SERVICES_URL}/analyze",
                json={
                    "code": snippet.code,
                    "language": snippet.language,
                    "analysis_type": "comprehensive"
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.warning(f"Failed to enrich snippet: {e}")
            return {}
    
    async def _sync_to_data_platform(self, snippet: CodeSnippet, user_id: str):
        """Sync snippet to data platform"""
        try:
            async with self.session.post(
                f"{DATA_PLATFORM_URL}/snippets",
                json={
                    "user_id": user_id,
                    "snippet": snippet.dict(exclude_none=True),
                    "timestamp": datetime.utcnow().isoformat()
                }
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to sync to data platform: {response.status}")
        except Exception as e:
            logger.warning(f"Data platform sync failed: {e}")
    
    async def get_ai_assistance(self, request: AIAssistanceRequest, user_id: str) -> AIAssistanceResponse:
        """Get AI assistance for development tasks"""
        try:
            # Get user context
            context = await self._get_user_context(user_id)
            
            # Prepare request for cognitive services
            ai_request = {
                "query": request.query,
                "context": {**context, **(request.context or {})},
                "model": request.model,
                "max_tokens": request.max_tokens,
                "service": "pieces_integration"
            }
            
            # Call cognitive services
            async with self.session.post(
                f"{COGNITIVE_SERVICES_URL}/chat",
                json=ai_request
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Process and format response
                    return AIAssistanceResponse(
                        response=result.get("response", ""),
                        suggestions=result.get("suggestions", []),
                        references=result.get("references", []),
                        confidence=result.get("confidence", 0.0)
                    )
                else:
                    raise HTTPException(
                        status_code=response.status,
                        detail="AI service unavailable"
                    )
                    
        except Exception as e:
            logger.error(f"AI assistance failed: {e}")
            error_counter.labels(error_type="ai_assistance").inc()
            raise HTTPException(status_code=500, detail="AI assistance failed")
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context from cache and history"""
        try:
            # Get recent snippets
            pattern = f"pieces:snippets:{user_id}:*"
            keys = await self.redis_client.keys(pattern)
            recent_snippets = []
            
            for key in keys[-5:]:  # Last 5 snippets
                snippet_data = await self.redis_client.get(key)
                if snippet_data:
                    recent_snippets.append(json.loads(snippet_data))
            
            # Get workflow context
            workflow_key = f"pieces:workflow:{user_id}"
            workflow_data = await self.redis_client.get(workflow_key)
            workflow = json.loads(workflow_data) if workflow_data else {}
            
            return {
                "recent_snippets": recent_snippets,
                "workflow": workflow,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Failed to get user context: {e}")
            return {}
    
    async def sync_workflow_context(self, context: WorkflowContext) -> bool:
        """Sync workflow context across AIWFE ecosystem"""
        try:
            # Store in Redis
            key = f"pieces:workflow:{context.user_id}"
            await self.redis_client.setex(
                key,
                3600,  # 1 hour TTL
                json.dumps(context.dict(), default=str)
            )
            
            # Notify other services
            await self._broadcast_context_update(context)
            
            logger.info(f"Synced workflow context for user {context.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync workflow context: {e}")
            error_counter.labels(error_type="sync_context").inc()
            return False
    
    async def _broadcast_context_update(self, context: WorkflowContext):
        """Broadcast context update to other services"""
        try:
            # Notify gateway service
            async with self.session.post(
                f"{GATEWAY_URL}/internal/context-update",
                json=context.dict(exclude_none=True),
                headers={"X-API-Key": API_KEY}
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to notify gateway: {response.status}")
                    
        except Exception as e:
            logger.warning(f"Context broadcast failed: {e}")

# Create connector instance
connector = PiecesConnector()

# FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    await connector.initialize()
    yield
    await connector.cleanup()

# Create FastAPI application
app = FastAPI(
    title="Pieces OS Connector",
    description="Pieces OS/Developers connectivity for AIWFE",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aiwfe.com", "http://aiwfe.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints
@app.get("/health/live")
async def liveness():
    """Liveness probe"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    """Readiness probe"""
    try:
        # Check Redis connection
        await connector.redis_client.ping()
        return {"status": "ready"}
    except:
        raise HTTPException(status_code=503, detail="Service not ready")

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return generate_latest()

# API endpoints
@app.post("/api/v1/snippets", response_model=Dict[str, str])
async def create_snippet(
    snippet: CodeSnippet,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Store a new code snippet"""
    user_data = await connector.verify_token(credentials)
    snippet_id = await connector.store_snippet(snippet, user_data["user_id"])
    request_counter.labels(method="POST", endpoint="/snippets").inc()
    return {"snippet_id": snippet_id, "status": "stored"}

@app.post("/api/v1/ai-assist", response_model=AIAssistanceResponse)
async def ai_assistance(
    request: AIAssistanceRequest,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get AI assistance for development tasks"""
    user_data = await connector.verify_token(credentials)
    response = await connector.get_ai_assistance(request, user_data["user_id"])
    request_counter.labels(method="POST", endpoint="/ai-assist").inc()
    return response

@app.post("/api/v1/workflow-context")
async def update_workflow_context(
    context: WorkflowContext,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Update workflow context"""
    user_data = await connector.verify_token(credentials)
    context.user_id = user_data["user_id"]
    success = await connector.sync_workflow_context(context)
    request_counter.labels(method="POST", endpoint="/workflow-context").inc()
    return {"status": "synced" if success else "failed"}

@app.get("/api/v1/snippets/{snippet_id}")
async def get_snippet(
    snippet_id: str,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Retrieve a code snippet"""
    user_data = await connector.verify_token(credentials)
    key = f"pieces:snippets:{user_data['user_id']}:{snippet_id}"
    
    snippet_data = await connector.redis_client.get(key)
    if not snippet_data:
        raise HTTPException(status_code=404, detail="Snippet not found")
    
    request_counter.labels(method="GET", endpoint="/snippets").inc()
    return json.loads(snippet_data)

@app.get("/api/v1/snippets")
async def list_snippets(
    credentials: HTTPAuthorizationCredentials = Security(security),
    limit: int = 10,
    offset: int = 0
):
    """List user's code snippets"""
    user_data = await connector.verify_token(credentials)
    pattern = f"pieces:snippets:{user_data['user_id']}:*"
    
    keys = await connector.redis_client.keys(pattern)
    snippets = []
    
    for key in keys[offset:offset+limit]:
        snippet_data = await connector.redis_client.get(key)
        if snippet_data:
            snippets.append(json.loads(snippet_data))
    
    request_counter.labels(method="GET", endpoint="/snippets").inc()
    return {"snippets": snippets, "total": len(keys)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)