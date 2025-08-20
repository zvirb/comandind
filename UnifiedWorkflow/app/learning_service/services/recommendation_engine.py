"""
Recommendation Engine
====================

AI-driven optimization recommendation engine that analyzes patterns,
performance data, and system context to generate actionable recommendations.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import statistics

from models.learning_responses import OptimizationRecommendation, RecommendationType
from pattern_recognition_engine import PatternRecognitionEngine
from performance_analyzer import PerformanceAnalyzer
from knowledge_graph_service import KnowledgeGraphService


logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generates intelligent recommendations for system optimization.
    
    Provides:
    - Context-aware optimization recommendations
    - Pattern-based improvement suggestions
    - Performance optimization strategies
    - Resource utilization recommendations
    - Configuration optimization advice
    """
    
    def __init__(
        self,
        pattern_engine: PatternRecognitionEngine,
        performance_analyzer: PerformanceAnalyzer,
        knowledge_graph: KnowledgeGraphService
    ):
        self.pattern_engine = pattern_engine
        self.performance_analyzer = performance_analyzer
        self.knowledge_graph = knowledge_graph
        
        # Recommendation scoring weights
        self.scoring_weights = {
            "impact": 0.3,
            "confidence": 0.25,
            "effort": 0.2,
            "risk": 0.15,
            "novelty": 0.1
        }
        
        logger.info("Recommendation Engine initialized")
    
    async def initialize(self) -> None:
        """Initialize the recommendation engine."""
        try:
            # Load recommendation models and templates
            await self._load_recommendation_templates()
            
            # Initialize scoring algorithms
            await self._initialize_scoring_algorithms()
            
            logger.info("Recommendation Engine initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize Recommendation Engine: {e}")
            raise
    
    async def generate_recommendations(
        self,
        context: Dict[str, Any],
        focus_areas: Optional[List[str]] = None,
        performance_goals: Dict[str, float] = None,
        constraints: Dict[str, Any] = None,
        priority: str = "balanced",
        include_rationale: bool = True,
        max_recommendations: int = 5
    ) -> Dict[str, Any]:
        """
        Generate AI-driven optimization recommendations.
        
        Args:
            context: Current system context
            focus_areas: Specific areas to focus on
            performance_goals: Performance targets
            constraints: System constraints
            priority: Recommendation priority (speed, accuracy, resource, balanced)
            include_rationale: Include explanation for recommendations
            max_recommendations: Maximum number of recommendations
            
        Returns:
            Comprehensive recommendation results
        """
        try:
            generation_start = datetime.utcnow()
            
            # Analyze current context
            context_analysis = await self._analyze_context(context, constraints)
            
            # Generate candidate recommendations
            candidates = await self._generate_candidate_recommendations(
                context, focus_areas, performance_goals, priority
            )
            
            # Score and rank recommendations
            scored_recommendations = await self._score_recommendations(
                candidates, context_analysis, performance_goals, priority
            )
            
            # Select top recommendations
            top_recommendations = scored_recommendations[:max_recommendations]
            
            # Add rationale if requested
            if include_rationale:
                for rec in top_recommendations:
                    rec.rationale = await self._generate_rationale(rec, context_analysis)
            
            # Calculate opportunity score
            opportunity_score = await self._calculate_opportunity_score(
                context_analysis, performance_goals, top_recommendations
            )
            
            # Identify focus areas
            identified_focus_areas = await self._identify_focus_areas(
                context_analysis, top_recommendations
            )
            
            # Calculate projected improvements
            projected_improvements = await self._calculate_projected_improvements(
                top_recommendations, context_analysis
            )
            
            generation_time = (datetime.utcnow() - generation_start).total_seconds()
            
            return {
                "recommendations": top_recommendations,
                "context_analysis": context_analysis,
                "opportunity_score": opportunity_score,
                "focus_areas": identified_focus_areas,
                "baseline_metrics": context_analysis.get("current_metrics", {}),
                "projected_improvements": projected_improvements
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {
                "recommendations": [],
                "context_analysis": {},
                "opportunity_score": 0.0,
                "focus_areas": [],
                "baseline_metrics": {},
                "projected_improvements": {}
            }
    
    async def generate_pattern_based_recommendations(
        self,
        pattern_id: str,
        current_context: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate recommendations based on a specific pattern."""
        try:
            recommendations = []
            
            # Get pattern from engine
            pattern = await self.pattern_engine._patterns.get(pattern_id)
            if not pattern:
                return recommendations
            
            # Analyze pattern applicability
            applicability_score = await self._analyze_pattern_applicability(
                pattern, current_context
            )
            
            if applicability_score > 0.6:
                # Generate pattern-based recommendation
                recommendation = OptimizationRecommendation(
                    type=RecommendationType.STRATEGY,
                    title=f"Apply {pattern.name} Pattern",
                    description=f"Apply the learned pattern '{pattern.name}' which has shown {pattern.metrics.success_rate:.1f}% success rate",
                    expected_impact={
                        "success_rate": 0.15,
                        "efficiency": 0.10
                    },
                    implementation_effort="medium",
                    priority=int(applicability_score * 10),
                    confidence=applicability_score,
                    supporting_patterns=[pattern_id],
                    prerequisites=[f"Context similarity: {applicability_score:.2f}"]
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating pattern-based recommendations: {e}")
            return []
    
    async def generate_performance_recommendations(
        self,
        subject_id: str,
        analysis_type: str,
        performance_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate recommendations based on performance analysis."""
        try:
            recommendations = []
            
            # Identify performance bottlenecks
            bottlenecks = await self.performance_analyzer.identify_bottlenecks(
                analysis_type, subject_id, 0.7
            )
            
            for bottleneck in bottlenecks:
                severity = bottleneck.get("severity", "medium")
                metric = bottleneck.get("metric", "performance")
                
                # Generate recommendation based on bottleneck type
                if metric == "speed":
                    recommendation = OptimizationRecommendation(
                        type=RecommendationType.PERFORMANCE,
                        title="Optimize Processing Speed",
                        description=f"Address speed bottleneck identified in {subject_id}",
                        expected_impact={"speed": 0.25, "efficiency": 0.15},
                        implementation_effort="high" if severity == "high" else "medium",
                        priority=8 if severity == "high" else 6,
                        confidence=0.8,
                        risks=["Temporary performance degradation during optimization"]
                    )
                elif metric == "success_rate":
                    recommendation = OptimizationRecommendation(
                        type=RecommendationType.ACCURACY,
                        title="Improve Success Rate",
                        description=f"Address success rate issues in {subject_id}",
                        expected_impact={"success_rate": 0.20, "reliability": 0.15},
                        implementation_effort="medium",
                        priority=9,
                        confidence=0.85,
                        prerequisites=["Error analysis", "Pattern review"]
                    )
                else:
                    recommendation = OptimizationRecommendation(
                        type=RecommendationType.PERFORMANCE,
                        title=f"Optimize {metric.title()}",
                        description=f"General optimization for {metric} in {subject_id}",
                        expected_impact={metric: 0.15},
                        implementation_effort="medium",
                        priority=7,
                        confidence=0.7
                    )
                
                recommendations.append(recommendation)
            
            return recommendations[:3]  # Return top 3 performance recommendations
            
        except Exception as e:
            logger.error(f"Error generating performance recommendations: {e}")
            return []
    
    async def generate_resource_recommendations(
        self,
        context: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate resource optimization recommendations."""
        try:
            recommendations = []
            
            # Analyze resource utilization
            resource_analysis = await self._analyze_resource_utilization(context, constraints)
            
            # CPU optimization
            cpu_utilization = resource_analysis.get("cpu_utilization", 0.5)
            if cpu_utilization > 0.8:
                recommendations.append(OptimizationRecommendation(
                    type=RecommendationType.RESOURCE,
                    title="Optimize CPU Usage",
                    description="High CPU utilization detected, consider load balancing or scaling",
                    expected_impact={"response_time": 0.2, "throughput": 0.15},
                    implementation_effort="high",
                    priority=8,
                    confidence=0.8
                ))
            elif cpu_utilization < 0.3:
                recommendations.append(OptimizationRecommendation(
                    type=RecommendationType.RESOURCE,
                    title="Right-size CPU Resources",
                    description="CPU under-utilization detected, consider reducing allocated resources",
                    expected_impact={"cost": 0.25},
                    implementation_effort="low",
                    priority=5,
                    confidence=0.7
                ))
            
            # Memory optimization
            memory_utilization = resource_analysis.get("memory_utilization", 0.5)
            if memory_utilization > 0.85:
                recommendations.append(OptimizationRecommendation(
                    type=RecommendationType.RESOURCE,
                    title="Increase Memory Allocation",
                    description="High memory utilization may cause performance issues",
                    expected_impact={"stability": 0.3, "performance": 0.15},
                    implementation_effort="medium",
                    priority=9,
                    confidence=0.9
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating resource recommendations: {e}")
            return []
    
    async def generate_configuration_recommendations(
        self,
        context: Dict[str, Any],
        performance_goals: Dict[str, float]
    ) -> List[OptimizationRecommendation]:
        """Generate configuration optimization recommendations."""
        try:
            recommendations = []
            
            # Analyze current configuration
            config_analysis = await self._analyze_configuration(context)
            
            # Threshold optimization
            current_thresholds = config_analysis.get("thresholds", {})
            for threshold_name, current_value in current_thresholds.items():
                optimal_value = await self._calculate_optimal_threshold(
                    threshold_name, current_value, performance_goals
                )
                
                if abs(optimal_value - current_value) > 0.05:
                    recommendations.append(OptimizationRecommendation(
                        type=RecommendationType.CONFIGURATION,
                        title=f"Optimize {threshold_name.title()} Threshold",
                        description=f"Adjust {threshold_name} from {current_value:.2f} to {optimal_value:.2f}",
                        expected_impact={"accuracy": 0.08, "efficiency": 0.05},
                        implementation_effort="low",
                        priority=6,
                        confidence=0.75
                    ))
            
            # Timeout optimization
            timeouts = config_analysis.get("timeouts", {})
            for timeout_name, current_timeout in timeouts.items():
                if current_timeout < 5.0:  # Very short timeout
                    recommendations.append(OptimizationRecommendation(
                        type=RecommendationType.CONFIGURATION,
                        title=f"Increase {timeout_name.title()} Timeout",
                        description=f"Short timeout ({current_timeout}s) may cause premature failures",
                        expected_impact={"success_rate": 0.12, "reliability": 0.10},
                        implementation_effort="low",
                        priority=7,
                        confidence=0.8
                    ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating configuration recommendations: {e}")
            return []
    
    # Private methods
    
    async def _analyze_context(
        self, 
        context: Dict[str, Any], 
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analyze the current system context."""
        try:
            analysis = {
                "current_metrics": {},
                "bottlenecks": [],
                "opportunities": [],
                "risk_factors": [],
                "resource_status": {}
            }
            
            # Extract current metrics
            analysis["current_metrics"] = context.get("performance_metrics", {})
            
            # Identify potential bottlenecks
            for key, value in context.items():
                if key.endswith("_utilization") and isinstance(value, (int, float)):
                    if value > 0.8:
                        analysis["bottlenecks"].append({
                            "type": key,
                            "value": value,
                            "severity": "high" if value > 0.9 else "medium"
                        })
                    elif value < 0.3:
                        analysis["opportunities"].append({
                            "type": key,
                            "value": value,
                            "opportunity": "resource_optimization"
                        })
            
            # Analyze constraints
            if constraints:
                analysis["constraints"] = constraints
                
                # Check for resource constraints
                if "max_cpu" in constraints or "max_memory" in constraints:
                    analysis["risk_factors"].append("resource_constraints")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            return {}
    
    async def _generate_candidate_recommendations(
        self,
        context: Dict[str, Any],
        focus_areas: Optional[List[str]],
        performance_goals: Dict[str, float] = None,
        priority: str = "balanced"
    ) -> List[OptimizationRecommendation]:
        """Generate candidate recommendations."""
        try:
            candidates = []
            
            # Generate pattern-based recommendations
            pattern_recs = await self._generate_pattern_recommendations(context)
            candidates.extend(pattern_recs)
            
            # Generate performance-based recommendations
            perf_recs = await self._generate_performance_optimization_recommendations(
                context, performance_goals
            )
            candidates.extend(perf_recs)
            
            # Generate resource recommendations
            resource_recs = await self.generate_resource_recommendations(
                context, context.get("constraints", {})
            )
            candidates.extend(resource_recs)
            
            # Generate configuration recommendations
            config_recs = await self.generate_configuration_recommendations(
                context, performance_goals or {}
            )
            candidates.extend(config_recs)
            
            # Filter by focus areas if specified
            if focus_areas:
                candidates = [
                    rec for rec in candidates 
                    if any(area.lower() in rec.description.lower() for area in focus_areas)
                ]
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error generating candidate recommendations: {e}")
            return []
    
    async def _score_recommendations(
        self,
        recommendations: List[OptimizationRecommendation],
        context_analysis: Dict[str, Any],
        performance_goals: Dict[str, float] = None,
        priority: str = "balanced"
    ) -> List[OptimizationRecommendation]:
        """Score and rank recommendations."""
        try:
            scored_recommendations = []
            
            for rec in recommendations:
                score = await self._calculate_recommendation_score(
                    rec, context_analysis, performance_goals, priority
                )
                
                # Update recommendation with score
                rec_dict = rec.dict()
                rec_dict["score"] = score
                
                scored_recommendations.append(OptimizationRecommendation(**rec_dict))
            
            # Sort by score (descending)
            scored_recommendations.sort(key=lambda x: getattr(x, 'score', 0), reverse=True)
            
            return scored_recommendations
            
        except Exception as e:
            logger.error(f"Error scoring recommendations: {e}")
            return recommendations
    
    async def _calculate_recommendation_score(
        self,
        recommendation: OptimizationRecommendation,
        context_analysis: Dict[str, Any],
        performance_goals: Dict[str, float] = None,
        priority: str = "balanced"
    ) -> float:
        """Calculate score for a recommendation."""
        try:
            # Base score from priority and confidence
            score = (recommendation.priority / 10.0) * 0.4 + recommendation.confidence * 0.4
            
            # Adjust based on expected impact
            impact_score = sum(recommendation.expected_impact.values()) * 0.2
            score += impact_score
            
            # Adjust based on implementation effort (lower effort = higher score)
            effort_adjustment = {"low": 0.1, "medium": 0.05, "high": 0.0}
            score += effort_adjustment.get(recommendation.implementation_effort, 0.0)
            
            # Adjust based on priority focus
            if priority == "speed" and "speed" in recommendation.expected_impact:
                score += 0.1
            elif priority == "accuracy" and "accuracy" in recommendation.expected_impact:
                score += 0.1
            elif priority == "resource" and recommendation.type == RecommendationType.RESOURCE:
                score += 0.1
            
            # Adjust based on risks (higher risk = lower score)
            risk_penalty = len(recommendation.risks) * 0.02
            score -= risk_penalty
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating recommendation score: {e}")
            return 0.5
    
    async def _generate_rationale(
        self, 
        recommendation: OptimizationRecommendation,
        context_analysis: Dict[str, Any]
    ) -> str:
        """Generate rationale for a recommendation."""
        try:
            rationale_parts = []
            
            # Base rationale
            rationale_parts.append(f"This recommendation addresses {recommendation.type.value} optimization.")
            
            # Impact rationale
            if recommendation.expected_impact:
                impact_items = [f"{k}: +{v:.1%}" for k, v in recommendation.expected_impact.items()]
                rationale_parts.append(f"Expected improvements: {', '.join(impact_items)}.")
            
            # Confidence rationale
            if recommendation.confidence > 0.8:
                rationale_parts.append("High confidence based on strong supporting evidence.")
            elif recommendation.confidence < 0.6:
                rationale_parts.append("Lower confidence due to limited supporting evidence.")
            
            # Context relevance
            bottlenecks = context_analysis.get("bottlenecks", [])
            if bottlenecks and recommendation.type == RecommendationType.PERFORMANCE:
                rationale_parts.append("Addresses identified performance bottlenecks.")
            
            return " ".join(rationale_parts)
            
        except Exception as e:
            logger.error(f"Error generating rationale: {e}")
            return "Rationale not available."
    
    async def _calculate_opportunity_score(
        self,
        context_analysis: Dict[str, Any],
        performance_goals: Dict[str, float] = None,
        recommendations: List[OptimizationRecommendation] = None
    ) -> float:
        """Calculate overall optimization opportunity score."""
        try:
            factors = []
            
            # Bottleneck factor
            bottleneck_count = len(context_analysis.get("bottlenecks", []))
            if bottleneck_count > 0:
                factors.append(min(1.0, bottleneck_count / 5.0))
            
            # Opportunity factor
            opportunity_count = len(context_analysis.get("opportunities", []))
            if opportunity_count > 0:
                factors.append(min(1.0, opportunity_count / 3.0))
            
            # Recommendation quality factor
            if recommendations:
                avg_confidence = statistics.mean([rec.confidence for rec in recommendations])
                factors.append(avg_confidence)
            
            # Performance gap factor
            if performance_goals:
                current_metrics = context_analysis.get("current_metrics", {})
                gaps = []
                for goal_metric, target in performance_goals.items():
                    current = current_metrics.get(goal_metric, target)
                    if target > current:
                        gaps.append((target - current) / target)
                
                if gaps:
                    factors.append(statistics.mean(gaps))
            
            if not factors:
                return 0.5
            
            return statistics.mean(factors)
            
        except Exception as e:
            logger.error(f"Error calculating opportunity score: {e}")
            return 0.0
    
    async def _identify_focus_areas(
        self,
        context_analysis: Dict[str, Any],
        recommendations: List[OptimizationRecommendation]
    ) -> List[str]:
        """Identify key focus areas for optimization."""
        try:
            focus_areas = []
            
            # From bottlenecks
            for bottleneck in context_analysis.get("bottlenecks", []):
                if bottleneck["type"].endswith("_utilization"):
                    area = bottleneck["type"].replace("_utilization", "")
                    focus_areas.append(area)
            
            # From recommendation types
            rec_types = [rec.type.value for rec in recommendations]
            most_common_type = max(set(rec_types), key=rec_types.count) if rec_types else None
            if most_common_type:
                focus_areas.append(most_common_type)
            
            # Remove duplicates and return top 3
            unique_areas = list(set(focus_areas))
            return unique_areas[:3]
            
        except Exception as e:
            logger.error(f"Error identifying focus areas: {e}")
            return []
    
    async def _calculate_projected_improvements(
        self,
        recommendations: List[OptimizationRecommendation],
        context_analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate projected improvements from implementing recommendations."""
        try:
            projections = {}
            
            # Aggregate expected impacts
            for rec in recommendations:
                for metric, impact in rec.expected_impact.items():
                    # Weight by confidence and priority
                    weighted_impact = impact * rec.confidence * (rec.priority / 10.0)
                    projections[metric] = projections.get(metric, 0) + weighted_impact
            
            # Apply diminishing returns
            for metric in projections:
                # Cap improvements at reasonable levels
                projections[metric] = min(projections[metric], 0.5)
                
                # Apply diminishing returns formula
                projections[metric] = 1 - (1 - projections[metric]) ** 0.8
            
            return projections
            
        except Exception as e:
            logger.error(f"Error calculating projected improvements: {e}")
            return {}
    
    # Additional helper methods (simplified implementations)
    
    async def _load_recommendation_templates(self) -> None:
        """Load recommendation templates."""
        logger.info("Recommendation templates loaded")
    
    async def _initialize_scoring_algorithms(self) -> None:
        """Initialize scoring algorithms."""
        logger.info("Scoring algorithms initialized")
    
    async def _analyze_pattern_applicability(self, pattern, context) -> float:
        """Analyze how applicable a pattern is to current context."""
        return 0.8  # Simplified
    
    async def _analyze_resource_utilization(self, context, constraints) -> Dict[str, float]:
        """Analyze resource utilization."""
        return {
            "cpu_utilization": context.get("cpu_utilization", 0.5),
            "memory_utilization": context.get("memory_utilization", 0.6)
        }
    
    async def _analyze_configuration(self, context) -> Dict[str, Any]:
        """Analyze current configuration."""
        return {
            "thresholds": {"confidence": 0.7, "similarity": 0.8},
            "timeouts": {"request": 30.0, "processing": 60.0}
        }
    
    async def _calculate_optimal_threshold(self, name, current, goals) -> float:
        """Calculate optimal threshold value."""
        return current + 0.05  # Simplified
    
    async def _generate_pattern_recommendations(self, context) -> List[OptimizationRecommendation]:
        """Generate pattern-based recommendations."""
        return []  # Simplified
    
    async def _generate_performance_optimization_recommendations(self, context, goals) -> List[OptimizationRecommendation]:
        """Generate performance optimization recommendations."""
        return []  # Simplified