"""Coordination Service - Central Agent Orchestration Bus.

This service serves as the central orchestration hub for the cognitive architecture,
managing 47+ specialist agents, workflow execution, and inter-service coordination.

Key Features:
- Event-driven agent coordination with no direct agent-to-agent communication
- Context package generation with intelligent <4000 token limit enforcement
- Redis-backed workflow state with PostgreSQL persistence
- Automatic dependency resolution for sequential and parallel execution
- <30s workflow recovery time after service restart
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from coordination_service import __version__
    from config import CoordinationConfig
    from middleware import LoggingMiddleware, MetricsMiddleware
    from services import (
        AgentOrchestrator,
        WorkflowStateManager,
        ContextPackageGenerator,
        CognitiveEventHandler,
        AgentRegistry,
        RedisService,
        PerformanceMonitor,
        DynamicRequestHandler,
        ContextIntegrationService
    )
except ImportError:
    # For testing and development when run directly
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    __version__ = "1.0.0"
    from config import CoordinationConfig
    from middleware import LoggingMiddleware, MetricsMiddleware
    from services import (
        AgentOrchestrator,
        WorkflowStateManager,
        ContextPackageGenerator,
        CognitiveEventHandler,
        AgentRegistry,
        RedisService,
        PerformanceMonitor
    )

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global service instances
orchestrator: AgentOrchestrator = None
workflow_manager: WorkflowStateManager = None
context_generator: ContextPackageGenerator = None
cognitive_handler: CognitiveEventHandler = None
agent_registry: AgentRegistry = None
redis_service: RedisService = None
performance_monitor: PerformanceMonitor = None
dynamic_request_handler: DynamicRequestHandler = None
context_integration_service: ContextIntegrationService = None
performance_coordinator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for service startup and shutdown."""
    global orchestrator, workflow_manager, context_generator
    global cognitive_handler, agent_registry, redis_service, performance_monitor
    global dynamic_request_handler, context_integration_service, performance_coordinator
    
    logger.info("Starting Coordination Service...")
    
    try:
        # Initialize configuration
        config = CoordinationConfig()
        
        # Initialize core services
        redis_service = RedisService(
            redis_url=config.redis_url,
            db=config.redis_db
        )
        await redis_service.initialize()
        
        # Initialize agent registry
        agent_registry = AgentRegistry(
            database_url=config.database_url,
            redis_service=redis_service
        )
        await agent_registry.initialize()
        
        # Initialize context package generator  
        context_generator = ContextPackageGenerator(
            max_tokens=config.max_context_tokens,
            redis_service=redis_service
        )
        
        # Initialize workflow state manager
        workflow_manager = WorkflowStateManager(
            database_url=config.database_url,
            redis_service=redis_service,
            recovery_timeout=config.recovery_timeout
        )
        await workflow_manager.initialize()
        
        # Initialize cognitive event handler
        cognitive_handler = CognitiveEventHandler(
            redis_service=redis_service,
            reasoning_service_url=config.reasoning_service_url,
            learning_service_url=config.learning_service_url
        )
        await cognitive_handler.initialize()
        
        # Initialize performance monitor
        performance_monitor = PerformanceMonitor(
            redis_service=redis_service,
            target_completion_rate=config.target_completion_rate
        )
        await performance_monitor.initialize()
        
        # Initialize context integration service
        context_integration_service = ContextIntegrationService(
            context_generator=context_generator,
            redis_service=redis_service
        )
        await context_integration_service.initialize()
        
        # Initialize dynamic request handler
        dynamic_request_handler = DynamicRequestHandler(
            agent_registry=agent_registry,
            context_generator=context_generator,
            orchestrator=None,  # Will be set after orchestrator is created
            workflow_manager=workflow_manager,
            redis_service=redis_service
        )
        await dynamic_request_handler.initialize()
        
        # Initialize main orchestrator
        orchestrator = AgentOrchestrator(
            agent_registry=agent_registry,
            workflow_manager=workflow_manager,
            context_generator=context_generator,
            cognitive_handler=cognitive_handler,
            performance_monitor=performance_monitor,
            max_concurrent_workflows=config.max_concurrent_workflows
        )
        await orchestrator.initialize()
        
        # Set orchestrator reference in dynamic request handler
        dynamic_request_handler.orchestrator = orchestrator
        
        # Initialize performance coordinator
        from performance_coordinator import ContainerPerformanceCoordinator
        performance_coordinator = ContainerPerformanceCoordinator(redis_url=config.redis_url)
        await performance_coordinator.initialize()
        
        logger.info(
            "Coordination Service initialized successfully",
            agent_count=await agent_registry.get_agent_count(),
            concurrent_workflows=config.max_concurrent_workflows
        )
        
        # Start background tasks
        asyncio.create_task(orchestrator.run_orchestration_loop())
        asyncio.create_task(cognitive_handler.run_event_processing())
        asyncio.create_task(performance_monitor.run_monitoring_loop())
        asyncio.create_task(performance_coordinator.run_coordination_loop())
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize Coordination Service", error=str(e))
        raise
    
    finally:
        logger.info("Shutting down Coordination Service...")
        
        # Cleanup services
        if dynamic_request_handler:
            await dynamic_request_handler.stop_processing()
        if context_integration_service:
            await context_integration_service.shutdown()
        if orchestrator:
            await orchestrator.shutdown()
        if cognitive_handler:
            await cognitive_handler.shutdown()
        if performance_monitor:
            await performance_monitor.shutdown()
        if workflow_manager:
            await workflow_manager.shutdown()
        if agent_registry:
            await agent_registry.shutdown()
        if redis_service:
            await redis_service.shutdown()
        
        logger.info("Coordination Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="AIWFE Coordination Service",
    description="Central Agent Orchestration Bus for Cognitive Architecture",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)


# Health and Status Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint with comprehensive service status."""
    try:
        # Check core service health
        redis_health = await redis_service.health_check() if redis_service else False
        agent_count = await agent_registry.get_agent_count() if agent_registry else 0
        active_workflows = await workflow_manager.get_active_workflow_count() if workflow_manager else 0
        
        # Get performance metrics
        performance_data = await performance_monitor.get_current_metrics() if performance_monitor else {}
        
        health_status = {
            "status": "healthy" if redis_health else "degraded",
            "timestamp": time.time(),
            "version": "1.0.0",
            "service": "coordination-service",
            "redis_connected": redis_health,
            "agent_registry": {
                "total_agents": agent_count,
                "status": "operational" if agent_count > 0 else "initializing"
            },
            "workflow_manager": {
                "active_workflows": active_workflows,
                "status": "operational"
            },
            "performance": performance_data,
            "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        }
        
        # Set start time if not already set
        if not hasattr(app.state, 'start_time'):
            app.state.start_time = time.time()
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )


@app.get("/status/detailed")
async def detailed_status():
    """Detailed status endpoint with comprehensive system information."""
    try:
        # Get detailed status from all components
        status_data = {
            "service": "coordination-service",
            "version": "1.0.0",
            "timestamp": time.time(),
            "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        }
        
        # Redis service status
        if redis_service:
            status_data["redis"] = await redis_service.get_detailed_status()
        
        # Agent registry status
        if agent_registry:
            status_data["agents"] = await agent_registry.get_detailed_status()
        
        # Workflow manager status
        if workflow_manager:
            status_data["workflows"] = await workflow_manager.get_detailed_status()
        
        # Cognitive event handler status
        if cognitive_handler:
            status_data["cognitive_events"] = await cognitive_handler.get_detailed_status()
        
        # Performance monitor status
        if performance_monitor:
            status_data["performance"] = await performance_monitor.get_detailed_metrics()
        
        # Orchestrator status
        if orchestrator:
            status_data["orchestrator"] = await orchestrator.get_detailed_status()
        
        return status_data
        
    except Exception as e:
        logger.error("Detailed status check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


# Workflow Management Endpoints
from models.workflow_requests import (
    WorkflowCreateRequest,
    WorkflowPauseRequest,
    WorkflowResumeRequest
)

@app.post("/workflow/create")
async def create_workflow(request: WorkflowCreateRequest, background_tasks: BackgroundTasks):
    """Create new multi-agent workflow with dependency resolution."""
    try:
        workflow_id = str(uuid.uuid4())
        
        logger.info(
            "Creating new workflow",
            workflow_id=workflow_id,
            workflow_type=request.workflow_type,
            agent_count=len(request.required_agents)
        )
        
        # Validate agents exist and are available
        available_agents = await agent_registry.validate_agents(request.required_agents)
        if not available_agents:
            raise HTTPException(
                status_code=400, 
                detail="Required agents not available"
            )
        
        # Create workflow
        workflow = await orchestrator.create_workflow(
            workflow_id=workflow_id,
            workflow_config=request.dict(),
            background_tasks=background_tasks
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "created",
            "estimated_completion": workflow.get("estimated_completion"),
            "assigned_agents": workflow.get("assigned_agents", []),
            "created_at": time.time()
        }
        
    except Exception as e:
        logger.error("Workflow creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow creation failed: {str(e)}")


@app.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get real-time workflow status and progress."""
    try:
        status = await workflow_manager.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return status
        
    except Exception as e:
        logger.error("Workflow status retrieval failed", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@app.post("/workflow/{workflow_id}/pause")
async def pause_workflow(workflow_id: str, request: WorkflowPauseRequest):
    """Pause workflow execution with state preservation."""
    try:
        result = await orchestrator.pause_workflow(
            workflow_id=workflow_id,
            preserve_state=request.preserve_state,
            reason=request.reason
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "paused",
            "state_preserved": result.get("state_preserved", False),
            "paused_at": time.time()
        }
        
    except Exception as e:
        logger.error("Workflow pause failed", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow pause failed: {str(e)}")


@app.post("/workflow/{workflow_id}/resume")
async def resume_workflow(workflow_id: str, request: WorkflowResumeRequest):
    """Resume workflows with automatic context regeneration."""
    try:
        result = await orchestrator.resume_workflow(
            workflow_id=workflow_id,
            regenerate_context=request.regenerate_context
        )
        
        return {
            "workflow_id": workflow_id,
            "status": "resumed",
            "context_regenerated": result.get("context_regenerated", False),
            "resumed_at": time.time()
        }
        
    except Exception as e:
        logger.error("Workflow resume failed", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow resume failed: {str(e)}")


# Cognitive Event Endpoints
from models.event_requests import CognitiveEventRequest

@app.post("/cognitive-events/receive")
async def receive_cognitive_event(request: CognitiveEventRequest):
    """Receive cognitive events from other services."""
    try:
        event_id = str(uuid.uuid4())
        
        # Process cognitive event
        result = await cognitive_handler.process_cognitive_event(
            event_id=event_id,
            event_data=request.dict()
        )
        
        return {
            "event_id": event_id,
            "processed": result.get("processed", False),
            "workflow_updates": result.get("workflow_updates", []),
            "processed_at": time.time()
        }
        
    except Exception as e:
        logger.error("Cognitive event processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Event processing failed: {str(e)}")


# Agent Management Endpoints
from models.agent_requests import AgentAssignmentRequest

@app.post("/agents/assign")
async def assign_agents(request: AgentAssignmentRequest):
    """Assign agents to workflow tasks with context packages."""
    try:
        assignment_result = await orchestrator.assign_agents(
            workflow_id=request.workflow_id,
            task_assignments=request.assignments,
            context_requirements=request.context_requirements
        )
        
        return {
            "workflow_id": request.workflow_id,
            "assignments": assignment_result.get("assignments", []),
            "context_packages_generated": assignment_result.get("context_packages", 0),
            "assigned_at": time.time()
        }
        
    except Exception as e:
        logger.error("Agent assignment failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent assignment failed: {str(e)}")


@app.get("/agents/active")
async def get_active_agents():
    """List active agent assignments and status."""
    try:
        active_agents = await agent_registry.get_active_assignments()
        
        return {
            "total_active": len(active_agents),
            "agents": active_agents,
            "last_updated": time.time()
        }
        
    except Exception as e:
        logger.error("Active agents retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Active agents retrieval failed: {str(e)}")


# Performance and Monitoring Endpoints

@app.get("/performance/metrics")
async def get_performance_metrics():
    """Get current performance metrics and statistics."""
    try:
        metrics = await performance_monitor.get_comprehensive_metrics()
        return metrics
        
    except Exception as e:
        logger.error("Performance metrics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")


@app.get("/workflow/analytics")
async def get_workflow_analytics():
    """Get workflow analytics and optimization insights."""
    try:
        analytics = await orchestrator.get_workflow_analytics()
        return analytics
        
    except Exception as e:
        logger.error("Workflow analytics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analytics retrieval failed: {str(e)}")


# Dynamic Agent Request Endpoints
from models.dynamic_request_models import (
    DynamicAgentRequestCreate,
    DynamicAgentRequestResponse,
    GapDetectionRequest,
    GapDetectionResponse,
    AgentRequestStatus,
    AgentRequestResultsResponse,
    ContextIntegrationRequest,
    ContextIntegrationResponse,
    DynamicRequestMetrics,
    InformationGapModel
)

@app.post("/dynamic-requests/create", response_model=DynamicAgentRequestResponse)
async def create_dynamic_request(request: DynamicAgentRequestCreate):
    """Create a new dynamic agent request for information gathering."""
    try:
        if not dynamic_request_handler:
            raise HTTPException(status_code=503, detail="Dynamic request handler not available")
        
        request_id = await dynamic_request_handler.create_agent_request(
            requesting_agent=request.requesting_agent,
            workflow_id=request.workflow_id,
            request_type=request.request_type,
            description=request.description,
            urgency=request.urgency,
            specific_expertise=request.specific_expertise_needed,
            context_requirements=request.context_requirements
        )
        
        # Get the created request details
        request_details = dynamic_request_handler.active_requests.get(request_id)
        if not request_details:
            raise HTTPException(status_code=500, detail="Failed to retrieve created request")
        
        return DynamicAgentRequestResponse(
            request_id=request_id,
            status=request_details.status,
            created_at=request_details.created_at,
            requesting_agent=request_details.requesting_agent,
            workflow_id=request_details.workflow_id,
            request_type=request_details.request_type,
            urgency=request_details.urgency,
            description=request_details.description
        )
        
    except Exception as e:
        logger.error("Dynamic request creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Request creation failed: {str(e)}")


@app.post("/dynamic-requests/detect-gaps", response_model=GapDetectionResponse)
async def detect_information_gaps(request: GapDetectionRequest):
    """Detect information gaps in agent execution and auto-create requests."""
    try:
        if not dynamic_request_handler:
            raise HTTPException(status_code=503, detail="Dynamic request handler not available")
        
        # Detect gaps
        gaps = await dynamic_request_handler.detect_information_gaps(
            agent_name=request.agent_name,
            task_context=request.task_context,
            execution_log=request.execution_log,
            current_findings=request.current_findings
        )
        
        # Auto-create requests for high-priority gaps
        high_priority_gaps = [gap for gap in gaps if gap.severity in ["high", "critical"]]
        auto_request_ids = []
        
        if high_priority_gaps:
            # Need to extract workflow_id from task_context
            workflow_id = request.task_context.get("workflow_id", "unknown")
            
            auto_request_ids = await dynamic_request_handler.auto_create_requests_for_gaps(
                requesting_agent=request.agent_name,
                workflow_id=workflow_id,
                information_gaps=high_priority_gaps
            )
        
        return GapDetectionResponse(
            gaps_detected=[InformationGapModel(**gap.__dict__) for gap in gaps],
            gap_count=len(gaps),
            high_priority_gaps=len(high_priority_gaps),
            auto_request_ids=auto_request_ids
        )
        
    except Exception as e:
        logger.error("Gap detection failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {str(e)}")


@app.get("/dynamic-requests/{request_id}/status", response_model=AgentRequestStatus)
async def get_dynamic_request_status(request_id: str):
    """Get status of a dynamic agent request."""
    try:
        if not dynamic_request_handler:
            raise HTTPException(status_code=503, detail="Dynamic request handler not available")
        
        status = await dynamic_request_handler.get_request_status(request_id)
        if not status:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return AgentRequestStatus(**status)
        
    except Exception as e:
        logger.error("Request status retrieval failed", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@app.get("/dynamic-requests/{request_id}/results", response_model=AgentRequestResultsResponse)
async def get_dynamic_request_results(request_id: str):
    """Get results of a completed dynamic agent request."""
    try:
        if not dynamic_request_handler:
            raise HTTPException(status_code=503, detail="Dynamic request handler not available")
        
        results = await dynamic_request_handler.get_request_response(request_id)
        if not results:
            raise HTTPException(status_code=404, detail="Request not found or not completed")
        
        return AgentRequestResultsResponse(**results)
        
    except Exception as e:
        logger.error("Request results retrieval failed", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Results retrieval failed: {str(e)}")


@app.get("/dynamic-requests/metrics", response_model=DynamicRequestMetrics)
async def get_dynamic_request_metrics():
    """Get dynamic request system metrics."""
    try:
        if not dynamic_request_handler:
            raise HTTPException(status_code=503, detail="Dynamic request handler not available")
        
        metrics = await dynamic_request_handler.get_metrics()
        return DynamicRequestMetrics(**metrics)
        
    except Exception as e:
        logger.error("Dynamic request metrics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")


# Context Integration Endpoints

@app.post("/context-integration/create", response_model=ContextIntegrationResponse)
async def create_context_integration(request: ContextIntegrationRequest):
    """Create a context integration operation to merge new findings."""
    try:
        if not context_integration_service:
            raise HTTPException(status_code=503, detail="Context integration service not available")
        
        integration_id = await context_integration_service.create_integration(
            requesting_agent=request.requesting_agent,
            workflow_id=request.workflow_id,
            request_id=request.request_id,
            original_context=request.original_context,
            new_findings=request.new_findings,
            integration_strategy=request.integration_strategy
        )
        
        # Wait a moment for processing and get results
        await asyncio.sleep(1)
        results = await context_integration_service.get_integration_result(integration_id)
        
        if results:
            return ContextIntegrationResponse(
                integration_id=integration_id,
                integrated_context=results["integrated_context"],
                integration_summary=results["integration_summary"],
                updated_context_package_id=results.get("updated_context_package_id"),
                confidence_improvement=results["confidence_improvement"]
            )
        else:
            # Return partial response if not yet complete
            return ContextIntegrationResponse(
                integration_id=integration_id,
                integrated_context={},
                integration_summary={"status": "processing"},
                confidence_improvement=0.0
            )
        
    except Exception as e:
        logger.error("Context integration creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Integration creation failed: {str(e)}")


@app.get("/context-integration/{integration_id}/status")
async def get_context_integration_status(integration_id: str):
    """Get status of a context integration operation."""
    try:
        if not context_integration_service:
            raise HTTPException(status_code=503, detail="Context integration service not available")
        
        status = await context_integration_service.get_integration_status(integration_id)
        if not status:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return status
        
    except Exception as e:
        logger.error("Integration status retrieval failed", integration_id=integration_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@app.get("/context-integration/{integration_id}/results")
async def get_context_integration_results(integration_id: str):
    """Get results of a completed context integration."""
    try:
        if not context_integration_service:
            raise HTTPException(status_code=503, detail="Context integration service not available")
        
        results = await context_integration_service.get_integration_result(integration_id)
        if not results:
            raise HTTPException(status_code=404, detail="Integration not found or not completed")
        
        return results
        
    except Exception as e:
        logger.error("Integration results retrieval failed", integration_id=integration_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Results retrieval failed: {str(e)}")


@app.get("/context-integration/metrics")
async def get_context_integration_metrics():
    """Get context integration system metrics."""
    try:
        if not context_integration_service:
            raise HTTPException(status_code=503, detail="Context integration service not available")
        
        metrics = await context_integration_service.get_metrics()
        return metrics
        
    except Exception as e:
        logger.error("Context integration metrics retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")


# Performance Coordination Endpoints

@app.post("/performance/coordinate")
async def coordinate_service_operation(
    service_name: str, 
    operation_type: str, 
    target_service: str
):
    """Coordinate operation between services to prevent conflicts."""
    try:
        if not performance_coordinator:
            raise HTTPException(status_code=503, detail="Performance coordinator not available")
        
        allowed = await performance_coordinator.coordinate_operation(
            service_name=service_name,
            operation_type=operation_type,
            target_service=target_service
        )
        
        return {
            "operation_allowed": allowed,
            "service_name": service_name,
            "operation_type": operation_type,
            "target_service": target_service,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Service operation coordination failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Coordination failed: {str(e)}")

@app.post("/performance/release")
async def release_service_operation(
    service_name: str, 
    operation_type: str, 
    target_service: str
):
    """Release operation coordination resources."""
    try:
        if not performance_coordinator:
            raise HTTPException(status_code=503, detail="Performance coordinator not available")
        
        await performance_coordinator.release_operation(
            service_name=service_name,
            operation_type=operation_type,
            target_service=target_service
        )
        
        return {
            "operation_released": True,
            "service_name": service_name,
            "operation_type": operation_type,
            "target_service": target_service,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Service operation release failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Release failed: {str(e)}")

@app.get("/performance/coordination-status")
async def get_coordination_status():
    """Get current performance coordination status."""
    try:
        if not performance_coordinator:
            raise HTTPException(status_code=503, detail="Performance coordinator not available")
        
        status = await performance_coordinator.get_coordination_status()
        return status
        
    except Exception as e:
        logger.error("Coordination status retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@app.post("/performance/optimize")
async def run_performance_optimization():
    """Run performance optimization analysis and recommendations."""
    try:
        if not performance_coordinator:
            raise HTTPException(status_code=503, detail="Performance coordinator not available")
        
        optimizations = await performance_coordinator.optimize_performance()
        
        return {
            "optimizations_generated": len(optimizations),
            "optimizations": [opt.__dict__ if hasattr(opt, '__dict__') else opt for opt in optimizations],
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Performance optimization failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


if __name__ == "__main__":
    import uvicorn
    import os
    
    config = CoordinationConfig()
    
    # Determine number of workers based on environment
    workers = int(os.getenv("COORDINATION_WORKERS", "4" if not config.debug else "1"))
    
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        workers=workers if not config.debug else None,
        log_config=None  # Use structlog configuration
    )