"""
Learning Service - Minimal Standalone Version
=============================================

Minimal FastAPI application for testing deployment with mocked dependencies.
This version validates the service architecture without requiring external services.

Port: 8005
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application startup time
startup_time = datetime.utcnow()

# Mock configuration for standalone testing
class MockConfig:
    port = 8005
    log_level = "INFO"
    debug = True
    pattern_recognition_threshold = 0.80
    similarity_threshold = 0.85
    confidence_threshold = 0.70

config = MockConfig()

# Create FastAPI app
app = FastAPI(
    title="Learning Service - Minimal",
    description="Minimal Learning Service for standalone testing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response Models
class HealthCheckResponse(BaseModel):
    """Health check response for the learning service."""
    
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_version: str = Field(default="1.0.0-minimal")
    
    # Database Connections (mocked)
    neo4j_connected: bool = Field(default=True)
    qdrant_connected: bool = Field(default=True)
    redis_connected: bool = Field(default=True)
    
    # System Metrics (mocked)
    patterns_stored: int = Field(default=42)
    knowledge_graph_nodes: int = Field(default=156)
    knowledge_graph_edges: int = Field(default=289)
    active_learning_sessions: int = Field(default=3)
    
    # Performance Metrics (mocked)
    average_response_time: float = Field(default=0.125)
    pattern_recognition_accuracy: float = Field(default=0.935)
    application_success_rate: float = Field(default=0.875)
    
    uptime_seconds: float = Field(default=0.0)

class LearningResponse(BaseModel):
    """Response from learning outcome processing."""
    
    status: str = Field(default="success")
    patterns_learned: int = Field(default=0)
    patterns_updated: int = Field(default=0)
    learning_insights: List[str] = Field(default_factory=list)
    pattern_ids: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0)
    processing_time: float = Field(default=0.0)

class OutcomeLearningRequest(BaseModel):
    """Request for learning from outcomes."""
    
    outcome_type: str = Field(..., description="Type of outcome")
    service_name: str = Field(..., description="Name of the service")
    context: Dict[str, Any] = Field(..., description="Context data")
    input_data: Optional[Dict[str, Any]] = Field(None)
    output_data: Optional[Dict[str, Any]] = Field(None)
    error_data: Optional[Dict[str, Any]] = Field(None)
    performance_metrics: Optional[Dict[str, float]] = Field(None)
    session_id: Optional[str] = Field(None)

# Mock service instances
class MockPatternEngine:
    def __init__(self):
        self.connected = True
    
    async def initialize(self):
        logger.info("MockPatternEngine initialized")
    
    async def get_performance_metrics(self):
        return {
            "total_patterns": 42,
            "recognition_accuracy": 0.935,
            "average_success_rate": 0.875
        }

class MockKnowledgeGraph:
    def __init__(self):
        self.connected = True
        self.total_nodes = 156
        self.total_edges = 289
    
    async def initialize(self):
        logger.info("MockKnowledgeGraph initialized")
    
    async def close(self):
        logger.info("MockKnowledgeGraph closed")

class MockQdrantService:
    def __init__(self):
        self.connected = True
    
    async def initialize(self):
        logger.info("MockQdrantService initialized")
    
    async def close(self):
        logger.info("MockQdrantService closed")

class MockRedisService:
    def __init__(self):
        self.connected = True
    
    async def initialize(self):
        logger.info("MockRedisService initialized")
    
    async def close(self):
        logger.info("MockRedisService closed")

class MockLearningEngine:
    def __init__(self):
        self.initialized = True
    
    async def initialize(self):
        logger.info("MockLearningEngine initialized")
    
    async def learn_from_outcome(self, outcome_type, service_name, context, 
                                input_data=None, output_data=None, error_data=None,
                                performance_metrics=None, session_id=None):
        # Mock learning process
        await asyncio.sleep(0.1)  # Simulate processing time
        
        learned_patterns = [{"pattern_id": f"pattern_{int(time.time())}"}]
        insights = {
            "insights": [
                f"Learned pattern from {service_name}",
                f"Context complexity: medium",
                f"Confidence: 0.87"
            ],
            "confidence": 0.87
        }
        
        return learned_patterns, insights

# Global service instances
pattern_engine: Optional[MockPatternEngine] = None
knowledge_graph: Optional[MockKnowledgeGraph] = None
qdrant_service: Optional[MockQdrantService] = None
redis_service: Optional[MockRedisService] = None
learning_engine: Optional[MockLearningEngine] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global pattern_engine, knowledge_graph, qdrant_service, redis_service, learning_engine
    
    logger.info("Starting Learning Service (Minimal) initialization...")
    
    try:
        # Initialize mock services
        redis_service = MockRedisService()
        await redis_service.initialize()
        
        knowledge_graph = MockKnowledgeGraph()
        await knowledge_graph.initialize()
        
        qdrant_service = MockQdrantService()
        await qdrant_service.initialize()
        
        pattern_engine = MockPatternEngine()
        await pattern_engine.initialize()
        
        learning_engine = MockLearningEngine()
        await learning_engine.initialize()
        
        logger.info("Learning Service (Minimal) initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Learning Service (Minimal): {e}")
        raise

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Learning Service (Minimal)...")
    
    # Close service connections
    if redis_service:
        await redis_service.close()
    if knowledge_graph:
        await knowledge_graph.close()
    if qdrant_service:
        await qdrant_service.close()
    
    logger.info("Learning Service (Minimal) shutdown completed")

# Dependency injection
def get_learning_engine() -> MockLearningEngine:
    if learning_engine is None:
        raise HTTPException(status_code=503, detail="Learning Engine not initialized")
    return learning_engine

# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint with detailed service status."""
    try:
        uptime = (datetime.utcnow() - startup_time).total_seconds()
        
        # Check service connections
        neo4j_connected = knowledge_graph.connected if knowledge_graph else False
        qdrant_connected = qdrant_service.connected if qdrant_service else False
        redis_connected = redis_service.connected if redis_service else False
        
        # Get system metrics
        pattern_metrics = {}
        if pattern_engine:
            pattern_metrics = await pattern_engine.get_performance_metrics()
        
        response = HealthCheckResponse(
            status="healthy" if all([neo4j_connected, qdrant_connected, redis_connected]) else "degraded",
            neo4j_connected=neo4j_connected,
            qdrant_connected=qdrant_connected, 
            redis_connected=redis_connected,
            patterns_stored=pattern_metrics.get("total_patterns", 42),
            knowledge_graph_nodes=knowledge_graph.total_nodes if knowledge_graph else 156,
            knowledge_graph_edges=knowledge_graph.total_edges if knowledge_graph else 289,
            pattern_recognition_accuracy=pattern_metrics.get("recognition_accuracy", 0.935),
            application_success_rate=pattern_metrics.get("average_success_rate", 0.875),
            uptime_seconds=uptime
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(status="unhealthy")

# Core Learning API Endpoint
@app.post("/learn/outcome", response_model=LearningResponse)
async def learn_from_outcome(
    request: OutcomeLearningRequest,
    background_tasks: BackgroundTasks,
    engine: MockLearningEngine = Depends(get_learning_engine)
):
    """
    Learn from a cognitive service outcome to extract and store patterns.
    """
    try:
        start_time = time.time()
        
        # Learn from the outcome
        learned_patterns, insights = await engine.learn_from_outcome(
            outcome_type=request.outcome_type,
            service_name=request.service_name,
            context=request.context,
            input_data=request.input_data,
            output_data=request.output_data,
            error_data=request.error_data,
            performance_metrics=request.performance_metrics,
            session_id=request.session_id
        )
        
        processing_time = time.time() - start_time
        
        # Background task for additional processing
        background_tasks.add_task(
            _process_learning_insights,
            insights,
            request.service_name,
            request.session_id
        )
        
        return LearningResponse(
            status="success",
            patterns_learned=len(learned_patterns),
            learning_insights=insights.get("insights", []),
            pattern_ids=[p.get("pattern_id", "") for p in learned_patterns],
            confidence_score=insights.get("confidence", 0.0),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error learning from outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Qdrant connection test endpoint
@app.get("/test/qdrant")
async def test_qdrant_connection():
    """Test endpoint to validate Qdrant SSL connection with our fix."""
    try:
        import os
        from qdrant_client import AsyncQdrantClient
        
        # Get Qdrant URL from environment
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        
        # Create Qdrant client with SSL verification disabled
        # This tests our SSL fix directly
        client = AsyncQdrantClient(
            url=qdrant_url,
            timeout=10.0,
            verify=False  # This is our SSL fix
        )
        
        # Test connection by getting collections
        collections = await client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        await client.close()
        
        return {
            "status": "success",
            "message": "Qdrant connection successful with SSL verification disabled",
            "qdrant_url": qdrant_url,
            "connected": True,
            "collections": collection_names,
            "ssl_verification": False
        }
        
    except Exception as e:
        logger.error(f"Qdrant connection test failed: {e}")
        return {
            "status": "error", 
            "message": f"Qdrant connection failed: {str(e)}",
            "qdrant_url": os.getenv("QDRANT_URL", "http://qdrant:6333"),
            "connected": False,
            "ssl_verification": False
        }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Learning Service",
        "version": "1.0.0-minimal",
        "status": "operational",
        "endpoints": ["/health", "/learn/outcome", "/test/qdrant", "/docs"],
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds()
    }

# Background task functions
async def _process_learning_insights(
    insights: Dict[str, Any], 
    service_name: str, 
    session_id: Optional[str]
):
    """Process learning insights in the background."""
    try:
        logger.info(f"Processing insights for {service_name}, session: {session_id}")
        await asyncio.sleep(0.05)  # Simulate background processing
        logger.info("Insights processed successfully")
    except Exception as e:
        logger.error(f"Error processing learning insights: {e}")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status": "error"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status": "error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main_minimal:app",
        host="0.0.0.0", 
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug
    )