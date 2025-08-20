"""
Learning Engine
==============

Core learning orchestration engine that coordinates pattern recognition,
knowledge graph updates, and continuous learning from cognitive service outcomes.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from models.patterns import LearningPattern, PatternType, PatternScope
from models.learning_requests import OutcomeType
from pattern_recognition_engine import PatternRecognitionEngine
from knowledge_graph_service import KnowledgeGraphService
from redis_service import RedisService


logger = logging.getLogger(__name__)


class LearningEngine:
    """
    Orchestrates the learning process across all learning components.
    
    Coordinates:
    - Pattern recognition and extraction
    - Knowledge graph updates
    - Continuous learning loops
    - Cross-pattern relationship discovery
    - Learning performance optimization
    """
    
    def __init__(
        self,
        pattern_engine: PatternRecognitionEngine,
        knowledge_graph: KnowledgeGraphService,
        redis_service: RedisService
    ):
        self.pattern_engine = pattern_engine
        self.knowledge_graph = knowledge_graph
        self.redis_service = redis_service
        
        # Learning state
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.learning_statistics: Dict[str, Any] = {}
        
        logger.info("Learning Engine initialized")
    
    async def initialize(self) -> None:
        """Initialize the learning engine."""
        try:
            # Load learning statistics
            await self._load_learning_statistics()
            
            # Initialize cross-pattern analysis
            await self._initialize_pattern_analysis()
            
            logger.info("Learning Engine initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize Learning Engine: {e}")
            raise
    
    async def learn_from_outcome(
        self,
        outcome_type: OutcomeType,
        service_name: str,
        context: Dict[str, Any],
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        error_data: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, float]] = None,
        session_id: Optional[str] = None
    ) -> Tuple[List[LearningPattern], Dict[str, Any]]:
        """
        Orchestrate learning from a cognitive service outcome.
        
        Args:
            outcome_type: Type of outcome (success/failure)
            service_name: Name of the service
            context: Context information
            input_data: Input data
            output_data: Output data (for successes)
            error_data: Error data (for failures)
            performance_metrics: Performance metrics
            session_id: Optional session identifier
            
        Returns:
            Tuple of (learned patterns, insights)
        """
        try:
            learning_start = datetime.utcnow()
            
            # Track learning session
            if session_id:
                await self._track_learning_session(
                    session_id, outcome_type, service_name, context
                )
            
            # Extract patterns using pattern recognition engine
            learned_patterns, pattern_insights = await self.pattern_engine.learn_from_outcome(
                outcome_type=outcome_type,
                service_name=service_name,
                context=context,
                input_data=input_data,
                output_data=output_data,
                error_data=error_data,
                performance_metrics=performance_metrics,
                session_id=session_id
            )
            
            # Perform cross-pattern analysis
            cross_pattern_insights = await self._analyze_cross_patterns(
                learned_patterns, context, service_name
            )
            
            # Update learning statistics
            await self._update_learning_statistics(
                outcome_type, service_name, len(learned_patterns)
            )
            
            # Generate comprehensive insights
            insights = await self._generate_comprehensive_insights(
                learned_patterns, pattern_insights, cross_pattern_insights,
                outcome_type, service_name, performance_metrics
            )
            
            learning_time = (datetime.utcnow() - learning_start).total_seconds()
            logger.info(f"Learned {len(learned_patterns)} patterns in {learning_time:.2f}s")
            
            return learned_patterns, insights
            
        except Exception as e:
            logger.error(f"Error in learning orchestration: {e}")
            raise
    
    async def continuous_learning_loop(
        self,
        feedback_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process continuous learning feedback to improve patterns.
        
        Args:
            feedback_data: Feedback from system outcomes
            
        Returns:
            Learning improvements summary
        """
        try:
            improvements = {
                "patterns_improved": 0,
                "new_relationships_discovered": 0,
                "insights": []
            }
            
            # Process feedback for pattern improvements
            pattern_improvements = await self._process_pattern_feedback(feedback_data)
            improvements["patterns_improved"] = len(pattern_improvements)
            
            # Discover new relationships
            new_relationships = await self._discover_new_relationships(feedback_data)
            improvements["new_relationships_discovered"] = len(new_relationships)
            
            # Generate insights from continuous learning
            learning_insights = await self._generate_learning_insights(
                pattern_improvements, new_relationships, feedback_data
            )
            improvements["insights"] = learning_insights
            
            return improvements
            
        except Exception as e:
            logger.error(f"Error in continuous learning loop: {e}")
            return {"patterns_improved": 0, "new_relationships_discovered": 0, "insights": []}
    
    async def optimize_learning_performance(self) -> Dict[str, Any]:
        """
        Optimize learning performance based on current metrics.
        
        Returns:
            Optimization results
        """
        try:
            optimizations = {
                "actions_taken": [],
                "performance_improvements": {}
            }
            
            # Analyze current learning performance
            performance_analysis = await self._analyze_learning_performance()
            
            # Optimize pattern recognition thresholds
            if performance_analysis.get("recognition_accuracy", 0) < 0.8:
                await self._optimize_recognition_thresholds()
                optimizations["actions_taken"].append("Adjusted recognition thresholds")
            
            # Optimize pattern storage
            if performance_analysis.get("storage_efficiency", 0) < 0.7:
                await self._optimize_pattern_storage()
                optimizations["actions_taken"].append("Optimized pattern storage")
            
            # Clean up old or ineffective patterns
            cleaned_patterns = await self._cleanup_ineffective_patterns()
            if cleaned_patterns > 0:
                optimizations["actions_taken"].append(f"Cleaned up {cleaned_patterns} patterns")
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing learning performance: {e}")
            return {"actions_taken": [], "performance_improvements": {}}
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics."""
        try:
            stats = {
                **self.learning_statistics,
                "active_sessions": len(self.active_sessions),
                "pattern_engine_metrics": await self.pattern_engine.get_performance_metrics()
            }
            
            # Add cache statistics
            if self.redis_service.connected:
                cache_stats = await self.redis_service.get_cache_statistics()
                stats["cache_statistics"] = cache_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting learning statistics: {e}")
            return {}
    
    # Private methods
    
    async def _track_learning_session(
        self,
        session_id: str,
        outcome_type: OutcomeType,
        service_name: str,
        context: Dict[str, Any]
    ) -> None:
        """Track learning session state."""
        try:
            session_data = {
                "session_id": session_id,
                "service_name": service_name,
                "outcome_type": outcome_type.value,
                "context_summary": str(context)[:200],  # Truncated context
                "outcomes_processed": 1,
                "patterns_learned": 0
            }
            
            # Update or create session in Redis
            existing_session = await self.redis_service.get_learning_session(session_id)
            if existing_session:
                session_data["outcomes_processed"] = existing_session.get("outcomes_processed", 0) + 1
                session_data["patterns_learned"] = existing_session.get("patterns_learned", 0)
            
            await self.redis_service.update_learning_session(session_id, session_data)
            self.active_sessions[session_id] = session_data
            
        except Exception as e:
            logger.error(f"Error tracking learning session: {e}")
    
    async def _analyze_cross_patterns(
        self,
        new_patterns: List[LearningPattern],
        context: Dict[str, Any],
        service_name: str
    ) -> Dict[str, Any]:
        """Analyze relationships between new and existing patterns."""
        try:
            insights = {
                "similar_patterns_found": 0,
                "conflicting_patterns_found": 0,
                "complementary_patterns_found": 0,
                "relationships": []
            }
            
            for pattern in new_patterns:
                # Find similar patterns
                similar_matches = await self.pattern_engine.search_patterns(
                    context=pattern.context_requirements,
                    similarity_threshold=0.85,
                    max_results=5
                )
                
                for match in similar_matches:
                    if match.pattern.pattern_id != pattern.pattern_id:
                        relationship_type = await self._determine_pattern_relationship(
                            pattern, match.pattern
                        )
                        
                        if relationship_type == "similar":
                            insights["similar_patterns_found"] += 1
                        elif relationship_type == "conflicting":
                            insights["conflicting_patterns_found"] += 1
                        elif relationship_type == "complementary":
                            insights["complementary_patterns_found"] += 1
                        
                        insights["relationships"].append({
                            "pattern_id": pattern.pattern_id,
                            "related_pattern_id": match.pattern.pattern_id,
                            "relationship_type": relationship_type,
                            "similarity_score": match.similarity_score
                        })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing cross patterns: {e}")
            return {"similar_patterns_found": 0, "conflicting_patterns_found": 0, "relationships": []}
    
    async def _determine_pattern_relationship(
        self, 
        pattern1: LearningPattern, 
        pattern2: LearningPattern
    ) -> str:
        """Determine the relationship type between two patterns."""
        try:
            # Simple heuristics for relationship determination
            
            # Same type and scope = similar
            if (pattern1.pattern_type == pattern2.pattern_type and 
                pattern1.pattern_scope == pattern2.pattern_scope):
                return "similar"
            
            # Success vs Error pattern = conflicting
            if ((pattern1.pattern_type == PatternType.SUCCESS and pattern2.pattern_type == PatternType.ERROR) or
                (pattern1.pattern_type == PatternType.ERROR and pattern2.pattern_type == PatternType.SUCCESS)):
                return "conflicting"
            
            # Different scopes but same service = complementary
            if (pattern1.source_service == pattern2.source_service and
                pattern1.pattern_scope != pattern2.pattern_scope):
                return "complementary"
            
            return "related"
            
        except Exception as e:
            logger.error(f"Error determining pattern relationship: {e}")
            return "unknown"
    
    async def _update_learning_statistics(
        self,
        outcome_type: OutcomeType,
        service_name: str,
        patterns_learned: int
    ) -> None:
        """Update learning statistics."""
        try:
            current_stats = self.learning_statistics
            
            # Update outcome type statistics
            outcome_key = f"outcomes_{outcome_type.value}"
            current_stats[outcome_key] = current_stats.get(outcome_key, 0) + 1
            
            # Update service statistics
            service_key = f"service_{service_name}_patterns"
            current_stats[service_key] = current_stats.get(service_key, 0) + patterns_learned
            
            # Update total patterns
            current_stats["total_patterns_learned"] = current_stats.get("total_patterns_learned", 0) + patterns_learned
            
            # Update timestamp
            current_stats["last_updated"] = datetime.utcnow().isoformat()
            
            # Cache updated statistics
            await self.redis_service.track_performance_metric(
                "learning_statistics_updated",
                1.0,
                {"outcome_type": outcome_type.value, "service": service_name}
            )
            
        except Exception as e:
            logger.error(f"Error updating learning statistics: {e}")
    
    async def _generate_comprehensive_insights(
        self,
        learned_patterns: List[LearningPattern],
        pattern_insights: Dict[str, Any],
        cross_pattern_insights: Dict[str, Any],
        outcome_type: OutcomeType,
        service_name: str,
        performance_metrics: Optional[Dict[str, float]]
    ) -> Dict[str, Any]:
        """Generate comprehensive insights from learning process."""
        try:
            insights = {
                "insights": [],
                "confidence": 0.0,
                "recommendations": [],
                "performance_impact": {}
            }
            
            # Pattern insights
            if learned_patterns:
                insights["insights"].append(
                    f"Learned {len(learned_patterns)} new patterns from {service_name}"
                )
                
                # Pattern type distribution
                pattern_types = {}
                for pattern in learned_patterns:
                    pattern_types[pattern.pattern_type.value] = pattern_types.get(pattern.pattern_type.value, 0) + 1
                
                most_common_type = max(pattern_types.items(), key=lambda x: x[1])
                insights["insights"].append(
                    f"Most common pattern type: {most_common_type[0]} ({most_common_type[1]} patterns)"
                )
            
            # Cross-pattern insights
            if cross_pattern_insights.get("similar_patterns_found", 0) > 0:
                insights["insights"].append(
                    f"Found {cross_pattern_insights['similar_patterns_found']} similar existing patterns"
                )
                insights["recommendations"].append("Consider pattern consolidation for similar patterns")
            
            if cross_pattern_insights.get("conflicting_patterns_found", 0) > 0:
                insights["insights"].append(
                    f"Detected {cross_pattern_insights['conflicting_patterns_found']} conflicting patterns"
                )
                insights["recommendations"].append("Review conflicting patterns for resolution")
            
            # Performance insights
            if performance_metrics:
                avg_confidence = sum(p.confidence_score for p in learned_patterns) / len(learned_patterns) if learned_patterns else 0
                insights["confidence"] = avg_confidence
                
                if avg_confidence > 0.8:
                    insights["insights"].append("High confidence patterns learned - excellent learning quality")
                elif avg_confidence < 0.5:
                    insights["insights"].append("Low confidence patterns - may need more training data")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating comprehensive insights: {e}")
            return {"insights": [], "confidence": 0.0, "recommendations": []}
    
    async def _load_learning_statistics(self) -> None:
        """Load learning statistics from persistent storage."""
        try:
            # Try to load from Redis first
            stats = await self.redis_service.get_performance_metrics("learning_statistics")
            
            if stats:
                # Use the most recent statistics
                latest_stats = stats[0] if stats else {}
                self.learning_statistics = latest_stats.get("context", {})
            else:
                # Initialize default statistics
                self.learning_statistics = {
                    "total_patterns_learned": 0,
                    "outcomes_processed": 0,
                    "last_updated": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Error loading learning statistics: {e}")
            self.learning_statistics = {}
    
    async def _initialize_pattern_analysis(self) -> None:
        """Initialize cross-pattern analysis capabilities."""
        try:
            # This could include loading pattern similarity matrices,
            # relationship models, etc.
            logger.info("Pattern analysis initialized")
            
        except Exception as e:
            logger.error(f"Error initializing pattern analysis: {e}")
    
    async def _process_pattern_feedback(self, feedback_data: Dict[str, Any]) -> List[str]:
        """Process feedback to improve existing patterns."""
        # Implementation for processing continuous learning feedback
        return []
    
    async def _discover_new_relationships(self, feedback_data: Dict[str, Any]) -> List[str]:
        """Discover new pattern relationships from feedback."""
        # Implementation for discovering new pattern relationships
        return []
    
    async def _generate_learning_insights(
        self, 
        improvements: List[str], 
        relationships: List[str], 
        feedback: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from continuous learning."""
        # Implementation for generating learning insights
        return []
    
    async def _analyze_learning_performance(self) -> Dict[str, Any]:
        """Analyze current learning performance."""
        # Implementation for learning performance analysis
        return {"recognition_accuracy": 0.85, "storage_efficiency": 0.75}
    
    async def _optimize_recognition_thresholds(self) -> None:
        """Optimize pattern recognition thresholds."""
        # Implementation for threshold optimization
        pass
    
    async def _optimize_pattern_storage(self) -> None:
        """Optimize pattern storage efficiency."""
        # Implementation for storage optimization
        pass
    
    async def _cleanup_ineffective_patterns(self) -> int:
        """Clean up patterns that are not performing well."""
        # Implementation for pattern cleanup
        return 0