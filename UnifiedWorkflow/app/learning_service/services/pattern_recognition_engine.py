"""
Pattern Recognition Engine
=========================

Core engine for recognizing, learning, and applying patterns from
cognitive service outcomes with >80% accuracy target.
"""

import asyncio
import json
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import hashlib

from models.patterns import (
    LearningPattern, PatternType, PatternScope, PatternStatus,
    PatternMatch, PatternApplication, PatternMetrics, PatternRelationship
)
from models.learning_requests import OutcomeType, PatternSearchScope
from .redis_service import RedisService
from .knowledge_graph_service import KnowledgeGraphService
from .qdrant_service import QdrantService


logger = logging.getLogger(__name__)


class PatternRecognitionEngine:
    """
    Advanced pattern recognition engine with machine learning capabilities.
    
    Provides:
    - Pattern extraction from outcomes
    - Semantic pattern matching
    - Pattern relationship discovery
    - Adaptive pattern evolution
    - Performance-driven pattern validation
    """
    
    def __init__(
        self,
        redis_service: RedisService,
        knowledge_graph_service: KnowledgeGraphService,
        qdrant_service: QdrantService,
        pattern_threshold: float = 0.80,
        similarity_threshold: float = 0.85
    ):
        self.redis_service = redis_service
        self.knowledge_graph_service = knowledge_graph_service
        self.qdrant_service = qdrant_service
        self.pattern_threshold = pattern_threshold
        self.similarity_threshold = similarity_threshold
        
        # Pattern storage
        self._patterns: Dict[str, LearningPattern] = {}
        self._pattern_embeddings: Dict[str, np.ndarray] = {}
        self._pattern_relationships: Dict[str, List[PatternRelationship]] = {}
        
        # Learning state
        self._learning_sessions: Dict[str, Dict[str, Any]] = {}
        self._pattern_evolution_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Performance tracking
        self._recognition_accuracy_history: List[float] = []
        self._pattern_success_rates: Dict[str, float] = {}
        
        # Initialize vectorizers for text analysis
        self._text_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self._is_vectorizer_fitted = False
        
        logger.info("Pattern Recognition Engine initialized")
    
    async def initialize(self) -> None:
        """Initialize the pattern recognition engine."""
        try:
            # Load existing patterns from storage
            await self._load_patterns_from_storage()
            
            # Initialize vectorizers with existing patterns
            await self._initialize_vectorizers()
            
            # Load performance metrics
            await self._load_performance_metrics()
            
            logger.info("Pattern Recognition Engine initialization completed")
        except Exception as e:
            logger.error(f"Failed to initialize Pattern Recognition Engine: {e}")
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
        Learn patterns from a cognitive service outcome.
        
        Args:
            outcome_type: Type of outcome (success/failure)
            service_name: Name of the service that generated the outcome
            context: Context in which the outcome occurred
            input_data: Input data that led to the outcome
            output_data: Output data from successful outcome
            error_data: Error data from failed outcome
            performance_metrics: Performance metrics
            session_id: Session identifier for grouping
        
        Returns:
            Tuple of (learned patterns, learning insights)
        """
        try:
            learning_start = datetime.utcnow()
            
            # Extract patterns from the outcome
            extracted_patterns = await self._extract_patterns_from_outcome(
                outcome_type, service_name, context, input_data, 
                output_data, error_data, performance_metrics, session_id
            )
            
            # Analyze pattern relationships
            relationships = await self._analyze_pattern_relationships(extracted_patterns)
            
            # Store patterns in knowledge graph
            stored_patterns = []
            for pattern in extracted_patterns:
                stored_pattern = await self._store_pattern(pattern, relationships.get(pattern.pattern_id, []))
                stored_patterns.append(stored_pattern)
            
            # Update performance tracking
            await self._update_recognition_performance(extracted_patterns)
            
            # Generate learning insights
            insights = await self._generate_learning_insights(
                extracted_patterns, relationships, performance_metrics
            )
            
            learning_time = (datetime.utcnow() - learning_start).total_seconds()
            logger.info(f"Learned {len(stored_patterns)} patterns in {learning_time:.2f}s")
            
            return stored_patterns, insights
            
        except Exception as e:
            logger.error(f"Error learning from outcome: {e}")
            raise
    
    async def search_patterns(
        self,
        context: Dict[str, Any],
        search_scope: PatternSearchScope = PatternSearchScope.GLOBAL,
        similarity_threshold: Optional[float] = None,
        max_results: int = 10,
        filter_by_success: Optional[bool] = None,
        outcome_types: Optional[List[OutcomeType]] = None
    ) -> List[PatternMatch]:
        """
        Search for patterns matching the given context.
        
        Args:
            context: Context to find patterns for
            search_scope: Scope of pattern search
            similarity_threshold: Override default similarity threshold
            max_results: Maximum number of results
            filter_by_success: Filter by success rate
            outcome_types: Filter by outcome types
        
        Returns:
            List of pattern matches with similarity scores
        """
        try:
            search_start = datetime.utcnow()
            
            # Use provided threshold or default
            threshold = similarity_threshold or self.similarity_threshold
            
            # Get candidate patterns based on scope
            candidate_patterns = await self._get_candidate_patterns(
                search_scope, outcome_types, filter_by_success
            )
            
            # Generate context embedding
            context_embedding = await self._generate_context_embedding(context)
            
            # Calculate similarities
            pattern_matches = []
            for pattern in candidate_patterns:
                similarity_score = await self._calculate_pattern_similarity(
                    pattern, context, context_embedding
                )
                
                if similarity_score >= threshold:
                    match = await self._create_pattern_match(
                        pattern, context, similarity_score, context_embedding
                    )
                    pattern_matches.append(match)
            
            # Sort by similarity score and limit results
            pattern_matches.sort(key=lambda m: m.similarity_score, reverse=True)
            pattern_matches = pattern_matches[:max_results]
            
            search_time = (datetime.utcnow() - search_start).total_seconds()
            logger.info(f"Found {len(pattern_matches)} pattern matches in {search_time:.2f}s")
            
            return pattern_matches
            
        except Exception as e:
            logger.error(f"Error searching patterns: {e}")
            raise
    
    async def adapt_pattern_to_context(
        self,
        pattern: LearningPattern,
        context: Dict[str, Any],
        adaptation_confidence: float = 0.7
    ) -> Tuple[LearningPattern, float]:
        """
        Adapt a pattern to a specific context.
        
        Args:
            pattern: Pattern to adapt
            context: Target context
            adaptation_confidence: Minimum confidence for adaptation
        
        Returns:
            Tuple of (adapted pattern, confidence score)
        """
        try:
            if not pattern.adaptable:
                return pattern, 1.0
            
            # Analyze context differences
            context_diff = await self._analyze_context_differences(
                pattern.context_requirements, context
            )
            
            # Generate adaptations
            adaptations = await self._generate_pattern_adaptations(
                pattern, context, context_diff
            )
            
            if not adaptations:
                return pattern, 1.0
            
            # Create adapted pattern
            adapted_pattern = await self._create_adapted_pattern(
                pattern, adaptations, context
            )
            
            # Calculate adaptation confidence
            confidence = await self._calculate_adaptation_confidence(
                pattern, adapted_pattern, context_diff, adaptations
            )
            
            if confidence >= adaptation_confidence:
                logger.info(f"Successfully adapted pattern {pattern.pattern_id} with confidence {confidence:.2f}")
                return adapted_pattern, confidence
            else:
                logger.warning(f"Pattern adaptation confidence {confidence:.2f} below threshold {adaptation_confidence}")
                return pattern, 1.0
                
        except Exception as e:
            logger.error(f"Error adapting pattern: {e}")
            return pattern, 0.0
    
    async def validate_pattern_application(
        self,
        pattern: LearningPattern,
        application: PatternApplication
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Validate the success of a pattern application.
        
        Args:
            pattern: Applied pattern
            application: Application result
        
        Returns:
            Tuple of (success, confidence, validation details)
        """
        try:
            validation_details = {}
            
            # Check outcome alignment
            outcome_alignment = application.outcome_alignment_score
            validation_details['outcome_alignment'] = outcome_alignment
            
            # Check execution time
            expected_time = pattern.metrics.average_execution_time or 10.0
            actual_time = application.execution_time or 0.0
            time_ratio = min(expected_time / max(actual_time, 0.1), 2.0)
            validation_details['time_efficiency'] = time_ratio
            
            # Check error conditions
            has_errors = application.error_information is not None
            validation_details['error_free'] = not has_errors
            
            # Calculate overall success
            success_indicators = [
                outcome_alignment >= 0.7,
                time_ratio >= 0.5,
                not has_errors
            ]
            success = sum(success_indicators) >= 2
            
            # Calculate confidence based on multiple factors
            confidence_factors = [
                outcome_alignment,
                min(time_ratio, 1.0),
                1.0 if not has_errors else 0.5,
                pattern.confidence_score
            ]
            confidence = np.mean(confidence_factors)
            
            # Update pattern metrics
            await self._update_pattern_metrics(pattern, application, success)
            
            validation_details['success_indicators'] = success_indicators
            validation_details['confidence_factors'] = confidence_factors
            
            return success, confidence, validation_details
            
        except Exception as e:
            logger.error(f"Error validating pattern application: {e}")
            return False, 0.0, {"error": str(e)}
    
    async def get_pattern_relationships(
        self, 
        pattern_id: str,
        relationship_types: Optional[List[str]] = None,
        max_depth: int = 2
    ) -> Dict[str, List[PatternRelationship]]:
        """
        Get relationships for a specific pattern.
        
        Args:
            pattern_id: ID of the pattern
            relationship_types: Filter by relationship types
            max_depth: Maximum traversal depth
        
        Returns:
            Dictionary of relationship types to relationships
        """
        try:
            return await self.knowledge_graph_service.get_pattern_relationships(
                pattern_id, relationship_types, max_depth
            )
        except Exception as e:
            logger.error(f"Error getting pattern relationships: {e}")
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for the pattern recognition engine."""
        try:
            metrics = {
                "total_patterns": len(self._patterns),
                "recognition_accuracy": np.mean(self._recognition_accuracy_history[-100:]) if self._recognition_accuracy_history else 0.0,
                "average_success_rate": np.mean(list(self._pattern_success_rates.values())) if self._pattern_success_rates else 0.0,
                "patterns_by_type": {},
                "patterns_by_scope": {},
                "patterns_by_status": {}
            }
            
            # Count patterns by categories
            for pattern in self._patterns.values():
                # By type
                type_key = pattern.pattern_type.value
                metrics["patterns_by_type"][type_key] = metrics["patterns_by_type"].get(type_key, 0) + 1
                
                # By scope
                scope_key = pattern.pattern_scope.value
                metrics["patterns_by_scope"][scope_key] = metrics["patterns_by_scope"].get(scope_key, 0) + 1
                
                # By status
                status_key = pattern.status.value
                metrics["patterns_by_status"][status_key] = metrics["patterns_by_status"].get(status_key, 0) + 1
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    # Private methods
    
    async def _extract_patterns_from_outcome(
        self,
        outcome_type: OutcomeType,
        service_name: str,
        context: Dict[str, Any],
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]],
        error_data: Optional[Dict[str, Any]],
        performance_metrics: Optional[Dict[str, float]],
        session_id: Optional[str]
    ) -> List[LearningPattern]:
        """Extract learning patterns from an outcome."""
        patterns = []
        
        try:
            # Generate pattern based on outcome type
            if "success" in outcome_type.value:
                pattern = await self._create_success_pattern(
                    outcome_type, service_name, context, input_data, output_data, performance_metrics
                )
            else:
                pattern = await self._create_failure_pattern(
                    outcome_type, service_name, context, input_data, error_data, performance_metrics
                )
            
            if pattern:
                patterns.append(pattern)
            
            # Extract contextual patterns
            contextual_patterns = await self._extract_contextual_patterns(
                context, input_data, output_data or error_data, service_name
            )
            patterns.extend(contextual_patterns)
            
            # Extract sequential patterns if session ID provided
            if session_id:
                sequential_patterns = await self._extract_sequential_patterns(
                    session_id, outcome_type, service_name, context
                )
                patterns.extend(sequential_patterns)
            
        except Exception as e:
            logger.error(f"Error extracting patterns from outcome: {e}")
        
        return patterns
    
    async def _create_success_pattern(
        self,
        outcome_type: OutcomeType,
        service_name: str,
        context: Dict[str, Any],
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]],
        performance_metrics: Optional[Dict[str, float]]
    ) -> Optional[LearningPattern]:
        """Create a pattern from a successful outcome."""
        try:
            # Generate pattern name and description
            pattern_name = f"{service_name}_{outcome_type.value}_{self._generate_context_hash(context)[:8]}"
            description = f"Success pattern for {service_name} in {outcome_type.value} scenario"
            
            # Determine pattern scope
            scope = await self._determine_pattern_scope(service_name, context)
            
            # Create trigger conditions
            trigger_conditions = await self._extract_trigger_conditions(context, input_data)
            
            # Create action sequence
            action_sequence = await self._extract_action_sequence(input_data, service_name)
            
            # Create expected outcomes
            expected_outcomes = output_data or {}
            
            pattern = LearningPattern(
                pattern_type=PatternType.SUCCESS,
                pattern_scope=scope,
                name=pattern_name,
                description=description,
                trigger_conditions=trigger_conditions,
                context_requirements=context,
                action_sequence=action_sequence,
                expected_outcomes=expected_outcomes,
                source_service=service_name,
                confidence_score=0.7,  # Initial confidence
                metrics=PatternMetrics()
            )
            
            # Set initial metrics
            if performance_metrics:
                pattern.metrics.average_execution_time = performance_metrics.get('execution_time', 0.0)
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error creating success pattern: {e}")
            return None
    
    async def _create_failure_pattern(
        self,
        outcome_type: OutcomeType,
        service_name: str,
        context: Dict[str, Any],
        input_data: Dict[str, Any],
        error_data: Optional[Dict[str, Any]],
        performance_metrics: Optional[Dict[str, float]]
    ) -> Optional[LearningPattern]:
        """Create a pattern from a failed outcome."""
        try:
            # Generate pattern name and description
            pattern_name = f"{service_name}_{outcome_type.value}_{self._generate_context_hash(context)[:8]}"
            description = f"Failure pattern for {service_name} in {outcome_type.value} scenario"
            
            # Determine pattern scope
            scope = await self._determine_pattern_scope(service_name, context)
            
            # Create trigger conditions
            trigger_conditions = await self._extract_trigger_conditions(context, input_data)
            
            # Create action sequence (what led to failure)
            action_sequence = await self._extract_action_sequence(input_data, service_name)
            
            # Create expected outcomes (error conditions)
            expected_outcomes = error_data or {}
            
            pattern = LearningPattern(
                pattern_type=PatternType.ERROR,
                pattern_scope=scope,
                name=pattern_name,
                description=description,
                trigger_conditions=trigger_conditions,
                context_requirements=context,
                action_sequence=action_sequence,
                expected_outcomes=expected_outcomes,
                source_service=service_name,
                confidence_score=0.8,  # Higher confidence for error patterns
                metrics=PatternMetrics()
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error creating failure pattern: {e}")
            return None
    
    async def _generate_context_hash(self, context: Dict[str, Any]) -> str:
        """Generate a hash for context identification."""
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    async def _determine_pattern_scope(self, service_name: str, context: Dict[str, Any]) -> PatternScope:
        """Determine the scope of a pattern based on service and context."""
        if "workflow" in service_name.lower() or "coordination" in service_name.lower():
            return PatternScope.WORKFLOW
        elif "agent" in str(context).lower():
            return PatternScope.AGENT
        elif service_name in ["reasoning-service", "perception-service", "hybrid-memory-service"]:
            return PatternScope.SERVICE
        else:
            return PatternScope.SYSTEM
    
    async def _extract_trigger_conditions(self, context: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract conditions that trigger this pattern."""
        conditions = {}
        
        # Context-based conditions
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                conditions[f"context_{key}"] = value
        
        # Input-based conditions
        for key, value in input_data.items():
            if isinstance(value, (str, int, float, bool)):
                conditions[f"input_{key}"] = value
        
        return conditions
    
    async def _extract_action_sequence(self, input_data: Dict[str, Any], service_name: str) -> List[Dict[str, Any]]:
        """Extract the sequence of actions from input data."""
        actions = []
        
        # Create a basic action based on service type
        action = {
            "type": "service_call",
            "service": service_name,
            "parameters": input_data
        }
        actions.append(action)
        
        return actions
    
    async def _load_patterns_from_storage(self) -> None:
        """Load existing patterns from persistent storage."""
        try:
            # Load from Redis cache first
            cached_patterns = await self.redis_service.get_cached_patterns()
            if cached_patterns:
                self._patterns.update(cached_patterns)
                logger.info(f"Loaded {len(cached_patterns)} patterns from cache")
            
            # Load from knowledge graph
            graph_patterns = await self.knowledge_graph_service.load_all_patterns()
            self._patterns.update(graph_patterns)
            logger.info(f"Loaded {len(graph_patterns)} patterns from knowledge graph")
            
        except Exception as e:
            logger.error(f"Error loading patterns from storage: {e}")
    
    async def _initialize_vectorizers(self) -> None:
        """Initialize text vectorizers with existing patterns."""
        try:
            if not self._patterns:
                return
            
            # Collect pattern texts for vectorizer fitting
            pattern_texts = []
            for pattern in self._patterns.values():
                text = f"{pattern.name} {pattern.description}"
                pattern_texts.append(text)
            
            if pattern_texts:
                self._text_vectorizer.fit(pattern_texts)
                self._is_vectorizer_fitted = True
                logger.info(f"Initialized text vectorizer with {len(pattern_texts)} patterns")
            
        except Exception as e:
            logger.error(f"Error initializing vectorizers: {e}")
    
    async def _store_pattern(
        self, 
        pattern: LearningPattern, 
        relationships: List[PatternRelationship]
    ) -> LearningPattern:
        """Store a pattern in all storage systems."""
        try:
            # Store in local cache
            self._patterns[pattern.pattern_id] = pattern
            
            # Store in Redis cache
            await self.redis_service.cache_pattern(pattern)
            
            # Store in knowledge graph
            await self.knowledge_graph_service.store_pattern(pattern, relationships)
            
            # Store embedding in Qdrant
            embedding = await self._generate_pattern_embedding(pattern)
            if embedding is not None:
                await self.qdrant_service.store_pattern_embedding(
                    pattern.pattern_id, embedding, pattern.dict()
                )
                self._pattern_embeddings[pattern.pattern_id] = embedding
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
            raise
    
    async def _generate_pattern_embedding(self, pattern: LearningPattern) -> Optional[np.ndarray]:
        """Generate vector embedding for a pattern."""
        try:
            # Combine pattern text components
            text_components = [
                pattern.name,
                pattern.description,
                str(pattern.trigger_conditions),
                str(pattern.context_requirements)
            ]
            pattern_text = " ".join(text_components)
            
            if self._is_vectorizer_fitted:
                # Use TF-IDF vectorization
                tfidf_vector = self._text_vectorizer.transform([pattern_text])
                return tfidf_vector.toarray()[0]
            else:
                # Simple hash-based embedding as fallback
                hash_value = hash(pattern_text)
                # Convert hash to fixed-size embedding
                embedding = np.array([
                    (hash_value >> i) & 1 for i in range(384)
                ], dtype=np.float32)
                return embedding
                
        except Exception as e:
            logger.error(f"Error generating pattern embedding: {e}")
            return None