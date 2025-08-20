"""Reasoning Service Main Application

FastAPI application providing evidence-based validation, multi-criteria decision making,
hypothesis testing, and multi-step reasoning chains with >85% accuracy requirements.

Key Features:
- Evidence validation with >85% accuracy requirement
- Multi-criteria decision analysis with confidence scoring
- Hypothesis testing with reality validation integration
- Multi-step reasoning chains with logical consistency validation
- Event-driven cognitive architecture communication
- Redis-backed state management and caching
- Comprehensive monitoring and structured logging
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest

try:
    from __init__ import __version__
    from config import get_settings
    from models.requests import (
        EvidenceValidationRequest,
        MultiCriteriaDecisionRequest, 
        HypothesisTestingRequest,
    )
    from models.responses import (
        EvidenceValidationResponse,
        MultiCriteriaDecisionResponse,
        HypothesisTestingResponse,
    )
    from models.requests import ReasoningChainRequest
    from models.responses import ReasoningChainResponse, HealthResponse
    from services import (
        OllamaService, RedisService, ReasoningEngine,
        EvidenceValidator, DecisionAnalyzer, HypothesisTester,
        ServiceIntegrator
    )
    from middleware import (
        LoggingMiddleware, MetricsMiddleware, SecurityMiddleware,
        RateLimitMiddleware, get_request_id
    )
except ImportError:
    # For testing and development when run directly
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    from __init__ import __version__
    from config import get_settings
    from models import (
        EvidenceValidationRequest, EvidenceValidationResponse,
        MultiCriteriaDecisionRequest, MultiCriteriaDecisionResponse,
        HypothesisTestingRequest, HypothesisTestingResponse,
        ReasoningChainRequest, ReasoningChainResponse,
        HealthResponse
    )
    from services import (
        OllamaService, RedisService, ReasoningEngine,
        EvidenceValidator, DecisionAnalyzer, HypothesisTester,
        ServiceIntegrator
    )
    from middleware import (
        LoggingMiddleware, MetricsMiddleware, SecurityMiddleware,
        RateLimitMiddleware, get_request_id
    )

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

# Prometheus metrics - with duplicate protection
try:
    REQUEST_COUNT = Counter(
        'reasoning_requests_total',
        'Total reasoning service requests', 
        ['method', 'endpoint', 'status']
    )
    REQUEST_DURATION = Histogram(
        'reasoning_request_duration_seconds',
        'Reasoning service request duration'
    )
    EVIDENCE_VALIDATION_ACCURACY = Histogram(
        'reasoning_evidence_validation_accuracy',
        'Evidence validation accuracy scores'
    )
    DECISION_CONFIDENCE_SCORE = Histogram(
        'reasoning_decision_confidence_score',
        'Decision analysis confidence scores'
    )
    HYPOTHESIS_TEST_RESULTS = Counter(
        'reasoning_hypothesis_test_results_total',
        'Hypothesis test results',
        ['result_type']
    )
    REASONING_CHAIN_STEPS = Histogram(
        'reasoning_chain_steps_count',
        'Number of steps in reasoning chains'
    )
except ValueError as e:
    # Metrics already registered, use existing ones
    if "Duplicated timeseries" in str(e):
        logger.warning("Prometheus metrics already registered, using existing ones")
        from prometheus_client import REGISTRY
        REQUEST_COUNT = None
        REQUEST_DURATION = None
        EVIDENCE_VALIDATION_ACCURACY = None
        DECISION_CONFIDENCE_SCORE = None
        HYPOTHESIS_TEST_RESULTS = None
        REASONING_CHAIN_STEPS = None
        for collector in REGISTRY._collector_to_names:
            if hasattr(collector, '_name'):
                if collector._name == 'reasoning_requests_total':
                    REQUEST_COUNT = collector
                elif collector._name == 'reasoning_request_duration_seconds':
                    REQUEST_DURATION = collector
                elif collector._name == 'reasoning_evidence_validation_accuracy':
                    EVIDENCE_VALIDATION_ACCURACY = collector
                elif collector._name == 'reasoning_decision_confidence_score':
                    DECISION_CONFIDENCE_SCORE = collector
                elif collector._name == 'reasoning_hypothesis_test_results_total':
                    HYPOTHESIS_TEST_RESULTS = collector
                elif collector._name == 'reasoning_chain_steps_count':
                    REASONING_CHAIN_STEPS = collector
    else:
        raise

settings = get_settings()

# Global service references
_services: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown tasks."""
    logger.info("Starting Reasoning Service", version=__version__)
    
    try:
        # Initialize Ollama service
        ollama_service = OllamaService(
            url=settings.ollama_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
            max_retries=settings.ollama_max_retries
        )
        
        # Initialize Redis service
        # Password is already included in the URL from settings.redis_url
        redis_service = RedisService(
            url=settings.redis_url,
            timeout=settings.redis_timeout,
            max_connections=settings.redis_max_connections
        )
        
        # Initialize services
        await redis_service.initialize()
        
        # Test Ollama connection and ensure model is ready
        await ollama_service.ensure_model_ready()
        
        # Initialize service integrator
        service_integrator = ServiceIntegrator(
            redis_service=redis_service,
            hybrid_memory_url=settings.hybrid_memory_url,
            perception_service_url=settings.perception_service_url,
            coordination_service_url=settings.coordination_service_url,
            learning_service_url=settings.learning_service_url,
            enable_event_routing=settings.cognitive_event_routing
        )
        
        # Initialize cognitive engines
        evidence_validator = EvidenceValidator(
            ollama_service=ollama_service,
            redis_service=redis_service,
            validation_threshold=settings.evidence_validation_threshold
        )
        
        decision_analyzer = DecisionAnalyzer(
            ollama_service=ollama_service,
            redis_service=redis_service,
            confidence_threshold=settings.confidence_threshold
        )
        
        hypothesis_tester = HypothesisTester(
            ollama_service=ollama_service,
            redis_service=redis_service,
            significance_threshold=0.05  # Standard significance level
        )
        
        reasoning_engine = ReasoningEngine(
            ollama_service=ollama_service,
            redis_service=redis_service,
            max_reasoning_steps=settings.max_reasoning_steps,
            confidence_threshold=settings.confidence_threshold
        )
        
        # Store services in global state
        _services.update({
            "ollama": ollama_service,
            "redis": redis_service,
            "service_integrator": service_integrator,
            "evidence_validator": evidence_validator,
            "decision_analyzer": decision_analyzer,
            "hypothesis_tester": hypothesis_tester,
            "reasoning_engine": reasoning_engine
        })
        
        # Store in app state for access in endpoints
        app.state.services = _services
        
        logger.info("All reasoning services initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize reasoning services", error=str(e))
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down reasoning services")
    
    try:
        if "ollama" in _services:
            await _services["ollama"].close()
        if "redis" in _services:
            await _services["redis"].close()
        if "service_integrator" in _services:
            await _services["service_integrator"].close()
            
        logger.info("All reasoning services shut down successfully")
        
    except Exception as e:
        logger.error("Error during service shutdown", error=str(e))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Reasoning Service",
        description="AI-powered reasoning service with evidence validation, decision analysis, and hypothesis testing",
        version=__version__,
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
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120)  # Allow high throughput
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    
    return app


app = create_app()


def get_services():
    """Dependency to get services from app state."""
    return app.state.services


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Comprehensive health check endpoint with cognitive capability status."""
    start_time = time.time()
    
    try:
        services = get_services()
        
        # Check all services concurrently
        health_checks = {}
        
        # Redis health
        try:
            redis_healthy = await services["redis"].health_check()
            health_checks["redis"] = {
                "healthy": redis_healthy,
                "service": "Cognitive state management"
            }
        except Exception as e:
            health_checks["redis"] = {
                "healthy": False,
                "error": str(e)
            }
        
        # Ollama health
        try:
            ollama_healthy = await services["ollama"].health_check()
            model_ready = await services["ollama"].is_model_ready()
            health_checks["ollama"] = {
                "healthy": ollama_healthy and model_ready,
                "model": settings.ollama_model,
                "model_ready": model_ready
            }
        except Exception as e:
            health_checks["ollama"] = {
                "healthy": False,
                "error": str(e)
            }
        
        # Service integration health
        try:
            integration_health = await services["service_integrator"].get_integration_health()
            health_checks["service_integration"] = integration_health
        except Exception as e:
            health_checks["service_integration"] = {
                "overall_status": "error",
                "error": str(e)
            }
        
        # Overall status
        core_services_healthy = all(
            check.get("healthy", False) 
            for service, check in health_checks.items()
            if service in ["redis", "ollama"]
        )
        
        status = "healthy" if core_services_healthy else "unhealthy"
        
        health_duration = time.time() - start_time
        
        # Cognitive capabilities status
        cognitive_capabilities = {
            "evidence_validation": core_services_healthy,
            "multi_criteria_decision": core_services_healthy,
            "hypothesis_testing": core_services_healthy,
            "reasoning_chains": core_services_healthy
        }
        
        # Performance metrics (from Redis if available)
        performance_metrics = {}
        try:
            if health_checks["redis"].get("healthy"):
                redis_service = services["redis"]
                accuracy_stats = await redis_service.get_performance_stats("evidence_validation_accuracy")
                if accuracy_stats:
                    performance_metrics["validation_accuracy"] = accuracy_stats["average"]
                
                confidence_stats = await redis_service.get_performance_stats("decision_confidence_score")
                if confidence_stats:
                    performance_metrics["decision_confidence"] = confidence_stats["average"]
                
                response_time_stats = await redis_service.get_performance_stats("reasoning_chain_time_ms")
                if response_time_stats:
                    performance_metrics["avg_response_time_ms"] = response_time_stats["average"]
        except Exception:
            pass  # Performance metrics are optional
        
        return HealthResponse(
            status=status,
            timestamp=time.time(),
            checks=health_checks,
            version=__version__,
            uptime_seconds=health_duration,
            cognitive_capabilities=cognitive_capabilities,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            timestamp=time.time(),
            checks={"error": str(e)},
            version=__version__
        )


@app.get("/metrics", include_in_schema=False)
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/validate/evidence", response_model=EvidenceValidationResponse, tags=["reasoning"])
async def validate_evidence(
    request: EvidenceValidationRequest,
    services: Dict[str, Any] = Depends(get_services),
    http_request: Request = None
) -> EvidenceValidationResponse:
    """
    Evidence-based validation with >85% accuracy requirement.
    
    Performs systematic validation of evidence using multiple criteria:
    - Source credibility assessment
    - Factual consistency checking  
    - Statistical validity evaluation
    - Bias and limitation analysis
    - Cross-verification opportunities
    
    Performance Target: <2s response time for complex evidence sets
    Accuracy Target: >85% validation accuracy as required by Phase 2
    """
    request_id = get_request_id(http_request) if http_request else str(uuid4())
    start_time = time.time()
    
    logger.info("Processing evidence validation request", 
                request_id=request_id,
                evidence_count=len(request.evidence),
                require_high_confidence=request.require_high_confidence)
    
    try:
        # Validate evidence through evidence validator
        validator = services["evidence_validator"]
        
        result = await validator.validate_evidence_batch(request, request_id)
        
        # Record metrics
        EVIDENCE_VALIDATION_ACCURACY.observe(result.overall_validity)
        REQUEST_COUNT.labels(method="POST", endpoint="/validate/evidence", status="success").inc()
        
        total_time = time.time() - start_time
        REQUEST_DURATION.observe(total_time)
        
        # Publish cognitive event
        if settings.cognitive_event_routing:
            service_integrator = services["service_integrator"]
            await service_integrator.publish_validation_event(
                workflow_id=request_id,
                validation_type="evidence_validation",
                validity_score=result.overall_validity,
                meets_threshold=result.meets_threshold,
                metadata={
                    "evidence_count": len(request.evidence),
                    "processing_time_ms": result.processing_time_ms
                }
            )
        
        # Send learning feedback
        if settings.learning_feedback_enabled:
            service_integrator = services["service_integrator"]
            await service_integrator.send_learning_feedback(
                workflow_id=request_id,
                pattern_type="evidence_validation",
                outcome_data={
                    "overall_validity": result.overall_validity,
                    "meets_threshold": result.meets_threshold,
                    "validation_method": result.validation_method
                },
                success_indicators={
                    "accuracy_threshold_met": result.meets_threshold,
                    "high_confidence": result.confidence_score > 0.8
                }
            )
        
        logger.info("Evidence validation completed",
                   request_id=request_id,
                   overall_validity=result.overall_validity,
                   meets_threshold=result.meets_threshold,
                   total_time_ms=round(total_time * 1000, 2))
        
        return result
        
    except ValueError as e:
        # Client errors (bad input)
        REQUEST_COUNT.labels(method="POST", endpoint="/validate/evidence", status="client_error").inc()
        logger.warning("Client error in evidence validation", 
                      request_id=request_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server errors
        REQUEST_COUNT.labels(method="POST", endpoint="/validate/evidence", status="server_error").inc()
        logger.error("Server error in evidence validation", 
                    request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/decide/multi-criteria", response_model=MultiCriteriaDecisionResponse, tags=["reasoning"])
async def multi_criteria_decision(
    request: MultiCriteriaDecisionRequest,
    services: Dict[str, Any] = Depends(get_services),
    http_request: Request = None
) -> MultiCriteriaDecisionResponse:
    """
    Multi-criteria decision making with confidence scoring.
    
    Performs comprehensive decision analysis using:
    - Weighted criteria evaluation
    - Trade-off analysis and risk assessment
    - Sensitivity analysis for robustness
    - Implementation feasibility assessment
    - Alternative comparison and ranking
    
    Performance Target: <2s response time for complex decisions
    Confidence Target: >70% confidence for recommendations
    """
    request_id = get_request_id(http_request) if http_request else str(uuid4())
    start_time = time.time()
    
    logger.info("Processing multi-criteria decision request", 
                request_id=request_id,
                options_count=len(request.options),
                criteria_count=len(request.criteria))
    
    try:
        # Analyze decision through decision analyzer
        analyzer = services["decision_analyzer"]
        
        result = await analyzer.analyze_decision(request, request_id)
        
        # Record metrics
        DECISION_CONFIDENCE_SCORE.observe(result.confidence_score)
        REQUEST_COUNT.labels(method="POST", endpoint="/decide/multi-criteria", status="success").inc()
        
        total_time = time.time() - start_time
        REQUEST_DURATION.observe(total_time)
        
        # Publish cognitive event
        if settings.cognitive_event_routing:
            service_integrator = services["service_integrator"]
            await service_integrator.publish_reasoning_complete_event(
                workflow_id=request_id,
                reasoning_type="multi_criteria_decision",
                confidence_score=result.confidence_score,
                result_summary=f"Recommended: {result.recommended_option}",
                metadata={
                    "options_count": len(request.options),
                    "criteria_count": len(request.criteria),
                    "processing_time_ms": result.processing_time_ms
                }
            )
        
        # Store decision memory
        service_integrator = services["service_integrator"]
        await service_integrator.store_reasoning_memory(
            workflow_id=request_id,
            reasoning_summary=f"Multi-criteria analysis recommended {result.recommended_option}: {result.decision_rationale}",
            confidence_score=result.confidence_score,
            metadata={
                "decision_type": "multi_criteria",
                "recommended_option": result.recommended_option
            }
        )
        
        logger.info("Multi-criteria decision completed",
                   request_id=request_id,
                   recommended_option=result.recommended_option,
                   confidence_score=result.confidence_score,
                   total_time_ms=round(total_time * 1000, 2))
        
        return result
        
    except ValueError as e:
        # Client errors (bad input)
        REQUEST_COUNT.labels(method="POST", endpoint="/decide/multi-criteria", status="client_error").inc()
        logger.warning("Client error in multi-criteria decision", 
                      request_id=request_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server errors
        REQUEST_COUNT.labels(method="POST", endpoint="/decide/multi-criteria", status="server_error").inc()
        logger.error("Server error in multi-criteria decision", 
                    request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/test/hypothesis", response_model=HypothesisTestingResponse, tags=["reasoning"])
async def test_hypothesis(
    request: HypothesisTestingRequest,
    services: Dict[str, Any] = Depends(get_services),
    http_request: Request = None
) -> HypothesisTestingResponse:
    """
    Reality testing integration with evidence validation.
    
    Performs systematic hypothesis testing with:
    - Statistical significance analysis
    - Bayesian probability updating
    - Alternative hypothesis consideration
    - Effect size and confidence intervals
    - Methodological validation
    
    Performance Target: <2s response time for hypothesis tests
    Validation: Integration with orchestration-auditor-v2 for reality testing
    """
    request_id = get_request_id(http_request) if http_request else str(uuid4())
    start_time = time.time()
    
    logger.info("Processing hypothesis testing request", 
                request_id=request_id,
                hypothesis=request.hypothesis[:100] + "..." if len(request.hypothesis) > 100 else request.hypothesis,
                evidence_count=len(request.evidence))
    
    try:
        # Test hypothesis through hypothesis tester
        tester = services["hypothesis_tester"]
        
        result = await tester.test_hypothesis(request, request_id)
        
        # Record metrics
        HYPOTHESIS_TEST_RESULTS.labels(result_type=result.result.test_result).inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/test/hypothesis", status="success").inc()
        
        total_time = time.time() - start_time
        REQUEST_DURATION.observe(total_time)
        
        # Publish cognitive event
        if settings.cognitive_event_routing:
            service_integrator = services["service_integrator"]
            await service_integrator.publish_reasoning_complete_event(
                workflow_id=request_id,
                reasoning_type="hypothesis_testing",
                confidence_score=result.result.confidence_score,
                result_summary=f"Hypothesis {result.result.test_result}: {request.hypothesis}",
                metadata={
                    "test_result": result.result.test_result,
                    "methodology": result.methodology,
                    "evidence_count": len(request.evidence),
                    "processing_time_ms": result.processing_time_ms
                }
            )
        
        # Store hypothesis testing memory
        service_integrator = services["service_integrator"]
        await service_integrator.store_reasoning_memory(
            workflow_id=request_id,
            reasoning_summary=f"Hypothesis testing concluded: {result.result.test_result}. {result.evidence_analysis}",
            confidence_score=result.result.confidence_score,
            metadata={
                "hypothesis": request.hypothesis,
                "test_result": result.result.test_result,
                "methodology": result.methodology
            }
        )
        
        logger.info("Hypothesis testing completed",
                   request_id=request_id,
                   test_result=result.result.test_result,
                   confidence_score=result.result.confidence_score,
                   methodology=result.methodology,
                   total_time_ms=round(total_time * 1000, 2))
        
        return result
        
    except ValueError as e:
        # Client errors (bad input)
        REQUEST_COUNT.labels(method="POST", endpoint="/test/hypothesis", status="client_error").inc()
        logger.warning("Client error in hypothesis testing", 
                      request_id=request_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server errors
        REQUEST_COUNT.labels(method="POST", endpoint="/test/hypothesis", status="server_error").inc()
        logger.error("Server error in hypothesis testing", 
                    request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/reasoning/chain", response_model=ReasoningChainResponse, tags=["reasoning"])
async def process_reasoning_chain(
    request: ReasoningChainRequest,
    services: Dict[str, Any] = Depends(get_services),
    http_request: Request = None
) -> ReasoningChainResponse:
    """
    Multi-step reasoning chain processing.
    
    Implements structured reasoning with:
    - Step-by-step logical progression
    - Assumption tracking and validation
    - Alternative path exploration
    - Logical consistency verification
    - Confidence assessment per step
    
    Performance Target: <2s response time for complex reasoning chains
    Validation: Logical consistency >80% for acceptable reasoning
    """
    request_id = get_request_id(http_request) if http_request else str(uuid4())
    start_time = time.time()
    
    logger.info("Processing reasoning chain request", 
                request_id=request_id,
                reasoning_type=request.reasoning_type,
                max_steps=request.max_steps,
                premise=request.initial_premise[:100] + "..." if len(request.initial_premise) > 100 else request.initial_premise)
    
    try:
        # Process reasoning chain through reasoning engine
        engine = services["reasoning_engine"]
        
        result = await engine.process_reasoning_chain(request, request_id)
        
        # Record metrics
        REASONING_CHAIN_STEPS.observe(len(result.result.steps))
        REQUEST_COUNT.labels(method="POST", endpoint="/reasoning/chain", status="success").inc()
        
        total_time = time.time() - start_time
        REQUEST_DURATION.observe(total_time)
        
        # Publish cognitive event
        if settings.cognitive_event_routing:
            service_integrator = services["service_integrator"]
            await service_integrator.publish_reasoning_complete_event(
                workflow_id=request_id,
                reasoning_type=f"reasoning_chain_{request.reasoning_type}",
                confidence_score=result.result.overall_confidence,
                result_summary=result.result.final_conclusion,
                metadata={
                    "reasoning_type": request.reasoning_type,
                    "steps_count": len(result.result.steps),
                    "logical_consistency": result.result.logical_consistency,
                    "processing_time_ms": result.processing_time_ms
                }
            )
        
        # Store reasoning chain memory
        service_integrator = services["service_integrator"]
        await service_integrator.store_reasoning_memory(
            workflow_id=request_id,
            reasoning_summary=f"{request.reasoning_type.title()} reasoning: {result.result.final_conclusion}",
            confidence_score=result.result.overall_confidence,
            metadata={
                "reasoning_type": request.reasoning_type,
                "initial_premise": request.initial_premise,
                "goal": request.goal,
                "steps_count": len(result.result.steps),
                "logical_consistency": result.result.logical_consistency
            }
        )
        
        logger.info("Reasoning chain completed",
                   request_id=request_id,
                   reasoning_type=request.reasoning_type,
                   steps_generated=len(result.result.steps),
                   overall_confidence=result.result.overall_confidence,
                   logical_consistency=result.result.logical_consistency,
                   total_time_ms=round(total_time * 1000, 2))
        
        return result
        
    except ValueError as e:
        # Client errors (bad input)
        REQUEST_COUNT.labels(method="POST", endpoint="/reasoning/chain", status="client_error").inc()
        logger.warning("Client error in reasoning chain", 
                      request_id=request_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server errors
        REQUEST_COUNT.labels(method="POST", endpoint="/reasoning/chain", status="server_error").inc()
        logger.error("Server error in reasoning chain", 
                    request_id=request_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    request_id = get_request_id(request)
    
    logger.error("Unhandled exception", 
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
            "path": request.url.path,
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        access_log=False,  # We handle access logging in structured logs
    )