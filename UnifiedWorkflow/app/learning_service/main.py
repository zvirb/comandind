"""
Learning Service - Adaptive Intelligence Foundation
==================================================

FastAPI application for pattern recognition, knowledge graph management,
and continuous learning from cognitive service outcomes.

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

try:
    from . import __version__
    from .config import config
    from .middleware import setup_middleware
    from models.learning_requests import (
        OutcomeLearningRequest, PatternSearchRequest, PatternApplicationRequest,
        PerformanceAnalysisRequest, RecommendationRequest
    )
    from models.learning_responses import (
        LearningResponse, PatternSearchResponse, PatternApplicationResponse,
        PerformanceAnalysisResponse, RecommendationResponse, HealthCheckResponse,
        KnowledgeGraphResponse
    )
except ImportError:
    # For testing and development when run directly
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    
    __version__ = "1.0.0"
    from config import config
    from middleware import setup_middleware
    from models.learning_requests import (
        OutcomeLearningRequest, PatternSearchRequest, PatternApplicationRequest,
        PerformanceAnalysisRequest, RecommendationRequest
    )
    from models.learning_responses import (
        LearningResponse, PatternSearchResponse, PatternApplicationResponse,
        PerformanceAnalysisResponse, RecommendationResponse, HealthCheckResponse,
        KnowledgeGraphResponse
    )
from services.pattern_recognition_engine import PatternRecognitionEngine
from services.knowledge_graph_service import KnowledgeGraphService
from services.qdrant_service import QdrantService
from services.redis_service import RedisService
from services.learning_engine import LearningEngine
from services.performance_analyzer import PerformanceAnalyzer
from services.recommendation_engine import RecommendationEngine


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
pattern_engine: Optional[PatternRecognitionEngine] = None
knowledge_graph: Optional[KnowledgeGraphService] = None
qdrant_service: Optional[QdrantService] = None
redis_service: Optional[RedisService] = None
learning_engine: Optional[LearningEngine] = None
performance_analyzer: Optional[PerformanceAnalyzer] = None
recommendation_engine: Optional[RecommendationEngine] = None

# Application startup time
startup_time = datetime.utcnow()

# Create FastAPI app
app = FastAPI(
    title="Learning Service",
    description="Adaptive Intelligence Foundation for AI Workflow Engine",
    version="1.0.0",
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None
)

# Setup middleware
setup_middleware(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global pattern_engine, knowledge_graph, qdrant_service, redis_service
    global learning_engine, performance_analyzer, recommendation_engine
    
    logger.info("Starting Learning Service initialization...")
    
    try:
        # Initialize data services
        redis_service = RedisService()
        await redis_service.initialize()
        
        knowledge_graph = KnowledgeGraphService()
        await knowledge_graph.initialize()
        
        qdrant_service = QdrantService()
        await qdrant_service.initialize()
        
        # Initialize core learning services
        pattern_engine = PatternRecognitionEngine(
            redis_service=redis_service,
            knowledge_graph_service=knowledge_graph,
            qdrant_service=qdrant_service,
            pattern_threshold=config.pattern_recognition_threshold,
            similarity_threshold=config.similarity_threshold
        )
        await pattern_engine.initialize()
        
        learning_engine = LearningEngine(
            pattern_engine=pattern_engine,
            knowledge_graph=knowledge_graph,
            redis_service=redis_service
        )
        await learning_engine.initialize()
        
        performance_analyzer = PerformanceAnalyzer(
            pattern_engine=pattern_engine,
            knowledge_graph=knowledge_graph,
            redis_service=redis_service
        )
        await performance_analyzer.initialize()
        
        recommendation_engine = RecommendationEngine(
            pattern_engine=pattern_engine,
            performance_analyzer=performance_analyzer,
            knowledge_graph=knowledge_graph
        )
        await recommendation_engine.initialize()
        
        logger.info("Learning Service initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Learning Service: {e}")
        raise


@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Learning Service...")
    
    # Close service connections
    if redis_service:
        await redis_service.close()
    if knowledge_graph:
        await knowledge_graph.close()
    if qdrant_service:
        await qdrant_service.close()
    
    logger.info("Learning Service shutdown completed")


# Dependency injection
def get_pattern_engine() -> PatternRecognitionEngine:
    if pattern_engine is None:
        raise HTTPException(status_code=503, detail="Pattern Recognition Engine not initialized")
    return pattern_engine


def get_learning_engine() -> LearningEngine:
    if learning_engine is None:
        raise HTTPException(status_code=503, detail="Learning Engine not initialized") 
    return learning_engine


def get_performance_analyzer() -> PerformanceAnalyzer:
    if performance_analyzer is None:
        raise HTTPException(status_code=503, detail="Performance Analyzer not initialized")
    return performance_analyzer


def get_recommendation_engine() -> RecommendationEngine:
    if recommendation_engine is None:
        raise HTTPException(status_code=503, detail="Recommendation Engine not initialized")
    return recommendation_engine


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
            patterns_stored=pattern_metrics.get("total_patterns", 0),
            knowledge_graph_nodes=knowledge_graph.total_nodes if knowledge_graph else 0,
            knowledge_graph_edges=knowledge_graph.total_edges if knowledge_graph else 0,
            pattern_recognition_accuracy=pattern_metrics.get("recognition_accuracy", 0.0),
            application_success_rate=pattern_metrics.get("average_success_rate", 0.0),
            uptime_seconds=uptime
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(status="unhealthy")


# Core Learning API Endpoints

@app.post("/learn/outcome", response_model=LearningResponse)
async def learn_from_outcome(
    request: OutcomeLearningRequest,
    background_tasks: BackgroundTasks,
    engine: LearningEngine = Depends(get_learning_engine)
):
    """
    Learn from a cognitive service outcome to extract and store patterns.
    
    This endpoint processes outcomes from reasoning, coordination, and other
    cognitive services to continuously improve the system's intelligence.
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
            pattern_ids=[p.pattern_id for p in learned_patterns],
            confidence_score=insights.get("confidence", 0.0),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error learning from outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/patterns/search", response_model=PatternSearchResponse)
async def search_patterns(
    request: PatternSearchRequest,
    engine: PatternRecognitionEngine = Depends(get_pattern_engine)
):
    """
    Search for patterns matching the given context using semantic similarity.
    
    Returns patterns that are most likely to be applicable to the current
    situation based on historical learning and context analysis.
    """
    try:
        start_time = time.time()
        
        # Search for matching patterns
        pattern_matches = await engine.search_patterns(
            context=request.context,
            search_scope=request.search_scope,
            similarity_threshold=request.similarity_threshold,
            max_results=request.max_results,
            filter_by_success=request.filter_by_success,
            outcome_types=request.outcome_types
        )
        
        search_time = time.time() - start_time
        
        # Generate recommendations based on matches
        recommendations = []
        if pattern_matches:
            top_patterns = sorted(pattern_matches, key=lambda m: m.similarity_score, reverse=True)[:3]
            for match in top_patterns:
                recommendations.append(
                    f"Apply {match.pattern.name} (confidence: {match.confidence_score:.2f})"
                )
        
        # Calculate confidence distribution
        confidence_distribution = {}
        for match in pattern_matches:
            confidence_range = f"{int(match.confidence_score * 10) * 10}-{int(match.confidence_score * 10) * 10 + 9}%"
            confidence_distribution[confidence_range] = confidence_distribution.get(confidence_range, 0) + 1
        
        return PatternSearchResponse(
            status="success",
            matches=pattern_matches,
            total_found=len(pattern_matches),
            search_time=search_time,
            filters_applied={
                "search_scope": request.search_scope.value,
                "similarity_threshold": request.similarity_threshold,
                "filter_by_success": request.filter_by_success
            },
            recommendations=recommendations,
            confidence_distribution=confidence_distribution
        )
        
    except Exception as e:
        logger.error(f"Error searching patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/patterns/apply", response_model=PatternApplicationResponse)
async def apply_pattern(
    request: PatternApplicationRequest,
    background_tasks: BackgroundTasks,
    engine: PatternRecognitionEngine = Depends(get_pattern_engine)
):
    """
    Apply a learned pattern to a new situation with context adaptation.
    
    Adapts the pattern to the current context and predicts the likelihood
    of successful application based on historical data.
    """
    try:
        # Get the pattern
        pattern = await engine._patterns.get(request.pattern_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="Pattern not found")
        
        # Adapt pattern to current context if needed
        adapted_pattern, adaptation_confidence = await engine.adapt_pattern_to_context(
            pattern=pattern,
            context=request.current_context,
            adaptation_confidence=request.confidence_threshold or config.confidence_threshold
        )
        
        # Calculate success probability
        success_probability = min(
            adaptation_confidence * pattern.confidence_score * 
            (pattern.metrics.success_rate / 100.0 if pattern.metrics.applications > 0 else 0.5),
            1.0
        )
        
        # Generate recommended parameters
        recommended_parameters = {
            "confidence_threshold": request.confidence_threshold or config.confidence_threshold,
            "adaptation_enabled": request.adaptation_enabled,
            "expected_execution_time": pattern.metrics.average_execution_time
        }
        
        # Validation warnings
        warnings = []
        if success_probability < 0.7:
            warnings.append("Low success probability based on historical data")
        if adaptation_confidence < 0.8:
            warnings.append("Pattern required significant adaptation to context")
        if pattern.metrics.applications < 5:
            warnings.append("Pattern has limited historical validation")
        
        # Background task to track application
        if not request.dry_run:
            background_tasks.add_task(
                _track_pattern_application,
                pattern.pattern_id,
                request.current_context,
                success_probability
            )
        
        return PatternApplicationResponse(
            status="success",
            adapted_pattern=adapted_pattern,
            confidence_score=adaptation_confidence,
            success_probability=success_probability,
            recommended_parameters=recommended_parameters,
            warnings=warnings,
            validation_results={
                "context_compatibility": adaptation_confidence,
                "historical_success_rate": pattern.metrics.success_rate,
                "application_count": pattern.metrics.applications
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    pattern_id: Optional[str] = None,
    max_depth: int = 2,
    include_visualization: bool = False
):
    """
    Get knowledge graph data for pattern relationships and visualization.
    
    Returns nodes and edges for graph visualization and analysis of
    pattern relationships and dependencies.
    """
    try:
        if not knowledge_graph:
            raise HTTPException(status_code=503, detail="Knowledge Graph not available")
        
        if pattern_id:
            # Get specific pattern's neighborhood
            from .models.knowledge_graph import GraphTraversalQuery
            query = GraphTraversalQuery(
                start_nodes=[pattern_id],
                max_depth=max_depth,
                max_results=100
            )
            result = await knowledge_graph.traverse_graph(query)
            nodes = result.nodes
            edges = result.edges
        else:
            # Get graph analytics
            analytics = await knowledge_graph.get_graph_analytics()
            nodes = []
            edges = []
        
        # Generate insights
        insights = []
        if nodes:
            insights.append(f"Graph contains {len(nodes)} nodes and {len(edges)} edges")
            if pattern_id:
                insights.append(f"Pattern {pattern_id} has {len(edges)} direct relationships")
        
        # Visualization data
        visualization_data = None
        if include_visualization and nodes:
            visualization_data = {
                "nodes": [{"id": n.node_id, "label": n.name, "type": n.node_type.value} for n in nodes],
                "edges": [{"from": e.source_node_id, "to": e.target_node_id, "type": e.edge_type.value} for e in edges]
            }
        
        return KnowledgeGraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=knowledge_graph.total_nodes,
            total_edges=knowledge_graph.total_edges,
            visualization_data=visualization_data,
            insights=insights
        )
        
    except Exception as e:
        logger.error(f"Error getting knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/performance", response_model=PerformanceAnalysisResponse)
async def analyze_performance(
    request: PerformanceAnalysisRequest,
    analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """
    Analyze agent or workflow performance patterns to identify optimization opportunities.
    
    Provides insights into performance trends, identifies bottlenecks,
    and suggests improvements based on historical data analysis.
    """
    try:
        start_time = time.time()
        
        # Perform analysis
        analysis_result = await analyzer.analyze_performance(
            analysis_type=request.analysis_type,
            subject_id=request.subject_id,
            time_range=request.time_range,
            metrics=request.metrics,
            comparison_subjects=request.comparison_subjects,
            include_patterns=request.include_patterns,
            include_recommendations=request.include_recommendations,
            granularity=request.granularity
        )
        
        analysis_time = time.time() - start_time
        
        return PerformanceAnalysisResponse(
            status="success",
            subject_id=request.subject_id,
            analysis_period=request.time_range or {
                "start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            **analysis_result,
            analysis_time=analysis_time
        )
        
    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Get AI-driven optimization recommendations based on current context and patterns.
    
    Analyzes the current system state and provides actionable recommendations
    for improving performance, accuracy, and resource utilization.
    """
    try:
        start_time = time.time()
        
        # Generate recommendations
        recommendations = await engine.generate_recommendations(
            context=request.context,
            focus_areas=request.focus_areas,
            performance_goals=request.performance_goals,
            constraints=request.constraints,
            priority=request.priority,
            include_rationale=request.include_rationale,
            max_recommendations=request.max_recommendations
        )
        
        generation_time = time.time() - start_time
        
        return RecommendationResponse(
            status="success",
            recommendations=recommendations.get("recommendations", []),
            context_analysis=recommendations.get("context_analysis", {}),
            opportunity_score=recommendations.get("opportunity_score", 0.0),
            focus_areas=recommendations.get("focus_areas", []),
            baseline_metrics=recommendations.get("baseline_metrics", {}),
            projected_improvements=recommendations.get("projected_improvements", {}),
            generation_time=generation_time
        )
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions

async def _process_learning_insights(
    insights: Dict[str, Any], 
    service_name: str, 
    session_id: Optional[str]
):
    """Process learning insights in the background."""
    try:
        if redis_service and insights:
            await redis_service.track_performance_metric(
                "learning_insights_generated",
                len(insights.get("insights", [])),
                {"service": service_name, "session": session_id}
            )
    except Exception as e:
        logger.error(f"Error processing learning insights: {e}")


async def _track_pattern_application(
    pattern_id: str, 
    context: Dict[str, Any], 
    success_probability: float
):
    """Track pattern application in the background."""
    try:
        if redis_service:
            await redis_service.track_performance_metric(
                "pattern_applications",
                success_probability,
                {"pattern_id": pattern_id}
            )
    except Exception as e:
        logger.error(f"Error tracking pattern application: {e}")


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
        "main:app",
        host="0.0.0.0", 
        port=config.port,
        log_level=config.log_level.lower(),
        reload=config.debug
    )