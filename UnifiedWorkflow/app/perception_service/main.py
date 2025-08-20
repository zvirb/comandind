"""Perception Service Main Application

FastAPI application providing image-to-vector conversion capabilities
using Ollama's LLaVA model integration.

Key Features:
- Async image processing with HTTPX client
- 1536-dimension vector output for compatibility
- Production-ready health checks and monitoring
- Performance optimizations for P95 < 2s latency
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest

from config import get_settings

# Version definition - compatible with module execution in Docker  
__version__ = "1.0.0"
from models import ConceptualizeRequest, ConceptualizeResponse, HealthResponse
from services.ollama_service import OllamaService
from middleware import LoggingMiddleware, MetricsMiddleware

# Configure structured logging
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('perception_requests_total', 'Total perception requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('perception_request_duration_seconds', 'Perception request duration')
PROCESSING_DURATION = Histogram('perception_processing_duration_seconds', 'Image processing duration')

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown tasks."""
    logger.info("Starting Perception Service", version=__version__)
    
    # Initialize Ollama service
    ollama_service = OllamaService(settings.ollama_url)
    app.state.ollama_service = ollama_service
    
    # Test Ollama connection and model availability
    try:
        await ollama_service.health_check()
        logger.info("Ollama service connection established")
        
        # Ensure LLaVA model is available
        await ollama_service.ensure_model_ready()
        logger.info("LLaVA model ready for inference")
        
    except Exception as e:
        logger.error("Failed to initialize Ollama service", error=str(e))
        raise
    
    yield
    
    # Cleanup
    await ollama_service.close()
    logger.info("Perception Service stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Perception Service",
        description="AI-powered image analysis and vector generation service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    
    return app


app = create_app()


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check endpoint with detailed service status."""
    try:
        ollama_service = app.state.ollama_service
        
        # Check Ollama service health
        start_time = time.time()
        ollama_healthy = await ollama_service.health_check()
        ollama_latency = time.time() - start_time
        
        # Check model availability
        model_ready = await ollama_service.is_model_ready()
        
        status = "healthy" if (ollama_healthy and model_ready) else "unhealthy"
        
        return HealthResponse(
            status=status,
            timestamp=time.time(),
            checks={
                "ollama_service": {
                    "healthy": ollama_healthy,
                    "latency_ms": round(ollama_latency * 1000, 2)
                },
                "llava_model": {
                    "ready": model_ready
                }
            }
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=time.time(),
            checks={
                "error": str(e)
            }
        )


@app.get("/metrics", include_in_schema=False)
async def get_metrics():
    """Prometheus metrics endpoint."""
    return generate_latest().decode("utf-8")


@app.post("/conceptualize", response_model=ConceptualizeResponse, tags=["ai"])
async def conceptualize_image(request: ConceptualizeRequest) -> ConceptualizeResponse:
    """
    Convert image to conceptual vector representation.
    
    This endpoint processes images using LLaVA model to generate
    1536-dimension vectors for semantic similarity and search.
    
    Performance Target: P95 latency < 2 seconds for 1MB images
    """
    request_id = id(request)
    start_time = time.time()
    
    logger.info("Processing conceptualization request", 
                request_id=request_id,
                image_size_bytes=len(request.image_data) if request.image_data else 0,
                format=request.format)
    
    try:
        ollama_service = app.state.ollama_service
        
        # Process image with performance tracking
        processing_start = time.time()
        
        vector = await ollama_service.generate_concept_vector(
            image_data=request.image_data,
            image_format=request.format,
            prompt=request.prompt,
            request_id=request_id
        )
        
        processing_time = time.time() - processing_start
        total_time = time.time() - start_time
        
        # Record metrics
        PROCESSING_DURATION.observe(processing_time)
        REQUEST_DURATION.observe(total_time)
        REQUEST_COUNT.labels(method="POST", endpoint="/conceptualize", status="success").inc()
        
        logger.info("Conceptualization completed",
                   request_id=request_id,
                   processing_time_ms=round(processing_time * 1000, 2),
                   total_time_ms=round(total_time * 1000, 2),
                   vector_dimensions=len(vector))
        
        return ConceptualizeResponse(
            vector=vector,
            dimensions=len(vector),
            processing_time_ms=round(processing_time * 1000, 2),
            request_id=str(request_id)
        )
        
    except ValueError as e:
        # Client errors (bad input)
        REQUEST_COUNT.labels(method="POST", endpoint="/conceptualize", status="client_error").inc()
        logger.warning("Client error in conceptualization", 
                      request_id=request_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server errors
        REQUEST_COUNT.labels(method="POST", endpoint="/conceptualize", status="server_error").inc()
        logger.error("Server error in conceptualization", 
                    request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error("Unhandled exception", 
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        access_log=False,  # We handle access logging in middleware
    )