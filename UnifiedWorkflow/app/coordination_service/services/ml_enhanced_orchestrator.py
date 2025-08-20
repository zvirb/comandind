"""ML-Enhanced Agent Orchestrator - Intelligent Agent Coordination with Machine Learning.

This module extends the base agent orchestrator with machine learning capabilities for:
- Intelligent agent selection based on task patterns
- Dynamic workflow optimization using ML models
- Predictive performance analysis
- Adaptive resource allocation
"""

import asyncio
import pickle
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import structlog

from .agent_orchestrator import AgentOrchestrator, WorkflowExecution, AgentAssignment, WorkflowStatus, AgentStatus

logger = structlog.get_logger(__name__)


class MLModelType(str, Enum):
    """Types of ML models used in orchestration."""
    AGENT_SELECTOR = "agent_selector"
    PERFORMANCE_PREDICTOR = "performance_predictor"
    RESOURCE_OPTIMIZER = "resource_optimizer"
    WORKFLOW_CLASSIFIER = "workflow_classifier"


@dataclass
class MLPrediction:
    """ML model prediction result."""
    model_type: MLModelType
    prediction: Any
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class WorkflowPattern:
    """Workflow execution pattern for ML training."""
    workflow_type: str
    request_text: str
    selected_agents: List[str]
    execution_time: float
    success_rate: float
    complexity_score: float
    resource_utilization: Dict[str, float]
    performance_metrics: Dict[str, float]


class MLEnhancedOrchestrator(AgentOrchestrator):
    """ML-Enhanced Agent Orchestrator with intelligent automation."""
    
    def __init__(
        self,
        agent_registry,
        workflow_manager,
        context_generator,
        cognitive_handler,
        performance_monitor,
        max_concurrent_workflows: int = 50,
        enable_ml_optimization: bool = True
    ):
        super().__init__(
            agent_registry,
            workflow_manager,
            context_generator,
            cognitive_handler,
            performance_monitor,
            max_concurrent_workflows
        )
        
        self.enable_ml_optimization = enable_ml_optimization
        
        # ML Models
        self.ml_models: Dict[MLModelType, Any] = {}
        self.text_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
        # Training Data Storage
        self.workflow_patterns: List[WorkflowPattern] = []
        self.training_data_cache = {}
        
        # ML Configuration
        self.ml_config = {
            "min_training_samples": 10,
            "retrain_threshold": 50,
            "confidence_threshold": 0.7,
            "feature_update_interval": 100
        }
        
        # Performance Tracking
        self.ml_performance_metrics = {
            "agent_selection_accuracy": 0.0,
            "performance_prediction_mae": 0.0,
            "optimization_improvement": 0.0,
            "ml_prediction_count": 0
        }
    
    async def initialize(self) -> None:
        """Initialize the ML-enhanced orchestrator."""
        await super().initialize()
        
        if self.enable_ml_optimization:
            logger.info("Initializing ML models for orchestration optimization...")
            await self._initialize_ml_models()
            await self._load_historical_patterns()
            logger.info("ML-enhanced orchestrator initialized")
    
    async def create_workflow_with_ml(
        self,
        workflow_config: Dict[str, Any],
        background_tasks
    ) -> Dict[str, Any]:
        """Create workflow with ML-enhanced agent selection and optimization."""
        workflow_id = str(uuid.uuid4())
        
        try:
            # ML-enhanced agent selection
            if self.enable_ml_optimization and "user_request" in workflow_config:
                ml_recommendations = await self._get_ml_agent_recommendations(
                    workflow_config["user_request"],
                    workflow_config.get("context", {})
                )
                
                if ml_recommendations and ml_recommendations.confidence > self.ml_config["confidence_threshold"]:
                    logger.info(
                        "Using ML-recommended agents",
                        workflow_id=workflow_id,
                        confidence=ml_recommendations.confidence,
                        recommended_agents=ml_recommendations.prediction
                    )
                    workflow_config["required_agents"] = ml_recommendations.prediction
                    workflow_config["ml_enhanced"] = True
                    workflow_config["ml_confidence"] = ml_recommendations.confidence
            
            # Predict workflow performance
            performance_prediction = await self._predict_workflow_performance(workflow_config)
            if performance_prediction:
                workflow_config["predicted_duration"] = performance_prediction.prediction
                workflow_config["performance_confidence"] = performance_prediction.confidence
            
            # Create workflow using enhanced configuration
            result = await self.create_workflow(workflow_id, workflow_config, background_tasks)
            
            # Store pattern for future ML training
            if self.enable_ml_optimization:
                await self._record_workflow_pattern(workflow_id, workflow_config)
            
            return result
            
        except Exception as e:
            logger.error("ML-enhanced workflow creation failed", workflow_id=workflow_id, error=str(e))
            raise
    
    async def optimize_agent_assignments(
        self,
        workflow_id: str,
        current_assignments: List[AgentAssignment]
    ) -> List[AgentAssignment]:
        """Optimize agent assignments using ML insights."""
        if not self.enable_ml_optimization:
            return current_assignments
        
        try:
            # Analyze current assignment patterns
            optimization_suggestions = await self._get_assignment_optimizations(
                workflow_id, current_assignments
            )
            
            if optimization_suggestions and optimization_suggestions.confidence > self.ml_config["confidence_threshold"]:
                logger.info(
                    "Applying ML assignment optimizations",
                    workflow_id=workflow_id,
                    confidence=optimization_suggestions.confidence
                )
                
                # Apply optimizations
                optimized_assignments = self._apply_assignment_optimizations(
                    current_assignments,
                    optimization_suggestions.prediction
                )
                
                return optimized_assignments
            
            return current_assignments
            
        except Exception as e:
            logger.error("Assignment optimization failed", workflow_id=workflow_id, error=str(e))
            return current_assignments
    
    async def predict_workflow_bottlenecks(
        self,
        workflow_id: str
    ) -> Optional[MLPrediction]:
        """Predict potential bottlenecks in workflow execution."""
        if not self.enable_ml_optimization:
            return None
        
        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                return None
            
            # Extract workflow features
            features = await self._extract_workflow_features(workflow)
            
            # Predict bottlenecks using trained model
            if MLModelType.RESOURCE_OPTIMIZER in self.ml_models:
                model = self.ml_models[MLModelType.RESOURCE_OPTIMIZER]
                bottleneck_prediction = model.predict_proba([features])[0]
                
                # Find highest probability bottleneck
                agent_names = list(self.agent_workloads.keys())
                bottleneck_idx = np.argmax(bottleneck_prediction)
                confidence = bottleneck_prediction[bottleneck_idx]
                
                if confidence > self.ml_config["confidence_threshold"]:
                    predicted_bottleneck = agent_names[bottleneck_idx] if bottleneck_idx < len(agent_names) else "unknown"
                    
                    return MLPrediction(
                        model_type=MLModelType.RESOURCE_OPTIMIZER,
                        prediction=predicted_bottleneck,
                        confidence=confidence,
                        metadata={
                            "all_probabilities": dict(zip(agent_names, bottleneck_prediction)),
                            "workflow_features": features
                        }
                    )
            
            return None
            
        except Exception as e:
            logger.error("Bottleneck prediction failed", workflow_id=workflow_id, error=str(e))
            return None
    
    async def get_ml_analytics(self) -> Dict[str, Any]:
        """Get ML-enhanced analytics and insights."""
        base_analytics = await self.get_workflow_analytics()
        
        if not self.enable_ml_optimization:
            return base_analytics
        
        # Add ML-specific metrics
        ml_analytics = {
            "ml_performance": self.ml_performance_metrics,
            "model_status": {
                model_type.value: {
                    "trained": model_type in self.ml_models,
                    "training_samples": len(self.workflow_patterns)
                }
                for model_type in MLModelType
            },
            "optimization_insights": await self._generate_ml_insights(),
            "predictive_recommendations": await self._generate_predictive_recommendations()
        }
        
        # Merge with base analytics
        base_analytics["ml_analytics"] = ml_analytics
        return base_analytics
    
    # Private ML methods
    
    async def _initialize_ml_models(self) -> None:
        """Initialize ML models for orchestration optimization."""
        try:
            # Initialize models with default configurations
            self.ml_models[MLModelType.AGENT_SELECTOR] = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            
            self.ml_models[MLModelType.PERFORMANCE_PREDICTOR] = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            
            self.ml_models[MLModelType.RESOURCE_OPTIMIZER] = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                max_depth=8
            )
            
            self.ml_models[MLModelType.WORKFLOW_CLASSIFIER] = RandomForestClassifier(
                n_estimators=50,
                random_state=42,
                max_depth=8
            )
            
            logger.info("ML models initialized", model_count=len(self.ml_models))
            
        except Exception as e:
            logger.error("ML model initialization failed", error=str(e))
            self.enable_ml_optimization = False
    
    async def _load_historical_patterns(self) -> None:
        """Load historical workflow patterns for training."""
        try:
            # This would typically load from a database or file
            # For now, we'll start with empty patterns and build them over time
            logger.info("Historical patterns loaded", pattern_count=len(self.workflow_patterns))
            
        except Exception as e:
            logger.error("Failed to load historical patterns", error=str(e))
    
    async def _get_ml_agent_recommendations(
        self,
        user_request: str,
        context: Dict[str, Any]
    ) -> Optional[MLPrediction]:
        """Get ML-based agent recommendations for a request."""
        try:
            if MLModelType.AGENT_SELECTOR not in self.ml_models:
                return None
            
            # Check if we have enough training data
            if len(self.workflow_patterns) < self.ml_config["min_training_samples"]:
                return None
            
            # Extract features from request
            features = await self._extract_request_features(user_request, context)
            
            # Get agent recommendations
            model = self.ml_models[MLModelType.AGENT_SELECTOR]
            if hasattr(model, 'predict_proba'):
                # Retrain model if needed
                await self._retrain_models_if_needed()
                
                # Make prediction
                agent_probabilities = model.predict_proba([features])[0]
                
                # Get top agents based on probabilities
                agent_names = await self._get_available_agent_names()
                if len(agent_probabilities) == len(agent_names):
                    agent_scores = list(zip(agent_names, agent_probabilities))
                    agent_scores.sort(key=lambda x: x[1], reverse=True)
                    
                    # Select top agents above confidence threshold
                    recommended_agents = [
                        agent for agent, score in agent_scores
                        if score > self.ml_config["confidence_threshold"]
                    ][:5]  # Limit to top 5
                    
                    if recommended_agents:
                        confidence = np.mean([score for _, score in agent_scores[:len(recommended_agents)]])
                        
                        return MLPrediction(
                            model_type=MLModelType.AGENT_SELECTOR,
                            prediction=recommended_agents,
                            confidence=confidence,
                            metadata={
                                "all_scores": dict(agent_scores),
                                "features": features
                            }
                        )
            
            return None
            
        except Exception as e:
            logger.error("ML agent recommendation failed", error=str(e))
            return None
    
    async def _predict_workflow_performance(
        self,
        workflow_config: Dict[str, Any]
    ) -> Optional[MLPrediction]:
        """Predict workflow performance metrics."""
        try:
            if MLModelType.PERFORMANCE_PREDICTOR not in self.ml_models:
                return None
            
            if len(self.workflow_patterns) < self.ml_config["min_training_samples"]:
                return None
            
            # Extract features from workflow config
            features = await self._extract_workflow_config_features(workflow_config)
            
            # Make prediction
            model = self.ml_models[MLModelType.PERFORMANCE_PREDICTOR]
            await self._retrain_models_if_needed()
            
            predicted_duration = model.predict([features])[0]
            
            # Calculate confidence based on model accuracy
            confidence = min(0.9, max(0.1, 1.0 - self.ml_performance_metrics.get("performance_prediction_mae", 1.0)))
            
            return MLPrediction(
                model_type=MLModelType.PERFORMANCE_PREDICTOR,
                prediction=predicted_duration,
                confidence=confidence,
                metadata={"features": features}
            )
            
        except Exception as e:
            logger.error("Performance prediction failed", error=str(e))
            return None
    
    async def _get_assignment_optimizations(
        self,
        workflow_id: str,
        assignments: List[AgentAssignment]
    ) -> Optional[MLPrediction]:
        """Get ML-based assignment optimizations."""
        try:
            if MLModelType.RESOURCE_OPTIMIZER not in self.ml_models:
                return None
            
            # Extract assignment features
            features = await self._extract_assignment_features(workflow_id, assignments)
            
            # Get optimization suggestions
            model = self.ml_models[MLModelType.RESOURCE_OPTIMIZER]
            optimization_scores = model.predict_proba([features])[0]
            
            # Generate optimization suggestions
            optimizations = {
                "parallelization_score": optimization_scores[0] if len(optimization_scores) > 0 else 0,
                "dependency_optimization": optimization_scores[1] if len(optimization_scores) > 1 else 0,
                "resource_reallocation": optimization_scores[2] if len(optimization_scores) > 2 else 0
            }
            
            confidence = np.mean(list(optimizations.values()))
            
            return MLPrediction(
                model_type=MLModelType.RESOURCE_OPTIMIZER,
                prediction=optimizations,
                confidence=confidence,
                metadata={"features": features}
            )
            
        except Exception as e:
            logger.error("Assignment optimization failed", workflow_id=workflow_id, error=str(e))
            return None
    
    async def _extract_request_features(
        self,
        user_request: str,
        context: Dict[str, Any]
    ) -> List[float]:
        """Extract numerical features from user request for ML models."""
        features = []
        
        # Text-based features
        request_lower = user_request.lower()
        
        # Keyword presence features
        technical_keywords = ["code", "programming", "technical", "software", "system", "api", "database"]
        business_keywords = ["business", "strategy", "market", "revenue", "roi", "growth"]
        creative_keywords = ["design", "creative", "ui", "ux", "brand", "visual"]
        
        features.extend([
            sum(1 for keyword in technical_keywords if keyword in request_lower),
            sum(1 for keyword in business_keywords if keyword in request_lower),
            sum(1 for keyword in creative_keywords if keyword in request_lower),
            len(user_request.split()),  # Word count
            len(user_request),  # Character count
        ])
        
        # Context features
        features.extend([
            len(context.get("parameters", {})),
            1 if context.get("priority") == "high" else 0,
            1 if context.get("urgent", False) else 0
        ])
        
        return features
    
    async def _extract_workflow_features(self, workflow: WorkflowExecution) -> List[float]:
        """Extract features from workflow for ML analysis."""
        features = []
        
        # Basic workflow features
        features.extend([
            len(workflow.agent_assignments),
            workflow.completion_percentage,
            time.time() - workflow.created_at,  # Age
            len(workflow.context),
            len(workflow.parameters)
        ])
        
        # Agent workload features
        if self.agent_workloads:
            features.extend([
                np.mean(list(self.agent_workloads.values())),
                np.max(list(self.agent_workloads.values())),
                np.min(list(self.agent_workloads.values()))
            ])
        else:
            features.extend([0, 0, 0])
        
        return features
    
    async def _extract_workflow_config_features(self, config: Dict[str, Any]) -> List[float]:
        """Extract features from workflow configuration."""
        features = []
        
        # Configuration features
        features.extend([
            len(config.get("required_agents", [])),
            1 if config.get("priority") == "high" else 0,
            config.get("timeout_minutes", 60),
            len(config.get("parameters", {})),
            len(config.get("context", {}))
        ])
        
        # Request text features if available
        if "user_request" in config:
            request_features = await self._extract_request_features(
                config["user_request"],
                config.get("context", {})
            )
            features.extend(request_features[:5])  # Limit to avoid feature explosion
        else:
            features.extend([0] * 5)
        
        return features
    
    async def _extract_assignment_features(
        self,
        workflow_id: str,
        assignments: List[AgentAssignment]
    ) -> List[float]:
        """Extract features from agent assignments."""
        features = []
        
        # Assignment features
        features.extend([
            len(assignments),
            sum(1 for a in assignments if a.status == AgentStatus.RUNNING),
            sum(1 for a in assignments if a.status == AgentStatus.COMPLETED),
            sum(1 for a in assignments if len(a.dependencies) > 0),
            np.mean([len(a.dependencies) for a in assignments]) if assignments else 0
        ])
        
        # Workflow context features
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow_features = await self._extract_workflow_features(workflow)
            features.extend(workflow_features[:5])  # Limit features
        else:
            features.extend([0] * 5)
        
        return features
    
    async def _record_workflow_pattern(
        self,
        workflow_id: str,
        workflow_config: Dict[str, Any]
    ) -> None:
        """Record workflow pattern for ML training."""
        try:
            pattern = WorkflowPattern(
                workflow_type=workflow_config.get("workflow_type", "unknown"),
                request_text=workflow_config.get("user_request", ""),
                selected_agents=workflow_config.get("required_agents", []),
                execution_time=0.0,  # Will be updated when workflow completes
                success_rate=0.0,  # Will be updated when workflow completes
                complexity_score=len(workflow_config.get("required_agents", [])),
                resource_utilization={},
                performance_metrics={}
            )
            
            self.workflow_patterns.append(pattern)
            logger.debug("Workflow pattern recorded", workflow_id=workflow_id)
            
        except Exception as e:
            logger.error("Failed to record workflow pattern", workflow_id=workflow_id, error=str(e))
    
    async def _retrain_models_if_needed(self) -> None:
        """Retrain ML models if enough new data is available."""
        if len(self.workflow_patterns) % self.ml_config["retrain_threshold"] == 0:
            await self._retrain_all_models()
    
    async def _retrain_all_models(self) -> None:
        """Retrain all ML models with current data."""
        try:
            if len(self.workflow_patterns) < self.ml_config["min_training_samples"]:
                return
            
            logger.info("Retraining ML models", pattern_count=len(self.workflow_patterns))
            
            # Prepare training data
            X_requests = []
            y_agents = []
            X_performance = []
            y_performance = []
            
            for pattern in self.workflow_patterns:
                if pattern.request_text and pattern.selected_agents:
                    request_features = await self._extract_request_features(
                        pattern.request_text, {}
                    )
                    X_requests.append(request_features)
                    
                    # Convert agent list to binary features
                    agent_features = await self._agents_to_binary_features(pattern.selected_agents)
                    y_agents.append(agent_features)
                    
                    if pattern.execution_time > 0:
                        X_performance.append(request_features)
                        y_performance.append(pattern.execution_time)
            
            # Retrain agent selector
            if len(X_requests) >= self.ml_config["min_training_samples"]:
                if MLModelType.AGENT_SELECTOR in self.ml_models:
                    self.ml_models[MLModelType.AGENT_SELECTOR].fit(X_requests, y_agents)
                    logger.info("Agent selector model retrained")
            
            # Retrain performance predictor
            if len(X_performance) >= self.ml_config["min_training_samples"]:
                if MLModelType.PERFORMANCE_PREDICTOR in self.ml_models:
                    self.ml_models[MLModelType.PERFORMANCE_PREDICTOR].fit(X_performance, y_performance)
                    logger.info("Performance predictor model retrained")
            
        except Exception as e:
            logger.error("Model retraining failed", error=str(e))
    
    async def _agents_to_binary_features(self, agent_list: List[str]) -> List[int]:
        """Convert agent list to binary feature vector."""
        all_agents = await self._get_available_agent_names()
        return [1 if agent in agent_list else 0 for agent in all_agents]
    
    async def _get_available_agent_names(self) -> List[str]:
        """Get list of all available agent names."""
        all_agents = await self.agent_registry.get_all_agents()
        return [agent["name"] for agent in all_agents]
    
    def _apply_assignment_optimizations(
        self,
        assignments: List[AgentAssignment],
        optimizations: Dict[str, float]
    ) -> List[AgentAssignment]:
        """Apply ML-suggested optimizations to assignments."""
        optimized = assignments.copy()
        
        # Apply optimizations based on scores
        if optimizations.get("parallelization_score", 0) > 0.7:
            # Reduce dependencies where possible
            for assignment in optimized:
                if len(assignment.dependencies) > 1:
                    assignment.dependencies = assignment.dependencies[:1]
        
        if optimizations.get("resource_reallocation", 0) > 0.7:
            # Adjust retry counts based on agent workload
            for assignment in optimized:
                agent_workload = self.agent_workloads.get(assignment.agent_name, 0)
                if agent_workload > 3:
                    assignment.max_retries = min(assignment.max_retries, 2)
        
        return optimized
    
    async def _generate_ml_insights(self) -> List[str]:
        """Generate ML-based optimization insights."""
        insights = []
        
        if len(self.workflow_patterns) > 0:
            # Analyze success patterns
            successful_patterns = [p for p in self.workflow_patterns if p.success_rate > 0.8]
            if len(successful_patterns) > len(self.workflow_patterns) * 0.6:
                insights.append("High success rate observed - current agent selection strategy is effective")
            
            # Analyze performance patterns
            avg_execution_time = np.mean([p.execution_time for p in self.workflow_patterns if p.execution_time > 0])
            if avg_execution_time > 0:
                insights.append(f"Average workflow execution time: {avg_execution_time:.1f} minutes")
        
        return insights
    
    async def _generate_predictive_recommendations(self) -> List[str]:
        """Generate predictive recommendations based on ML analysis."""
        recommendations = []
        
        # Analyze current system state
        if self.enable_ml_optimization and len(self.workflow_patterns) > 10:
            # Resource utilization recommendations
            high_demand_agents = [
                agent for agent, workload in self.agent_workloads.items()
                if workload > np.mean(list(self.agent_workloads.values())) * 1.5
            ]
            
            if high_demand_agents:
                recommendations.append(f"Consider scaling high-demand agents: {', '.join(high_demand_agents[:3])}")
            
            # Performance optimization recommendations
            if self.ml_performance_metrics.get("agent_selection_accuracy", 0) < 0.7:
                recommendations.append("Agent selection accuracy below threshold - consider retraining models")
        
        return recommendations