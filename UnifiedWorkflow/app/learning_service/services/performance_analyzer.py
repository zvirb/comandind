"""
Performance Analyzer
===================

Analyzes agent and workflow performance patterns to identify
optimization opportunities and performance bottlenecks.
"""

import asyncio
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from models.patterns import LearningPattern, PatternMetrics
from models.learning_requests import PerformanceMetricType
from models.learning_responses import PerformanceInsight
from pattern_recognition_engine import PatternRecognitionEngine
from knowledge_graph_service import KnowledgeGraphService
from redis_service import RedisService


logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Analyzes performance patterns across agents, workflows, and services.
    
    Provides:
    - Performance trend analysis
    - Bottleneck identification
    - Optimization opportunity detection
    - Comparative performance analysis
    - Predictive performance modeling
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
        
        # Analysis cache
        self.performance_cache: Dict[str, Dict[str, Any]] = {}
        self.trend_analysis_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("Performance Analyzer initialized")
    
    async def initialize(self) -> None:
        """Initialize the performance analyzer."""
        try:
            # Load historical performance data
            await self._load_historical_data()
            
            # Initialize analysis models
            await self._initialize_analysis_models()
            
            logger.info("Performance Analyzer initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize Performance Analyzer: {e}")
            raise
    
    async def analyze_performance(
        self,
        analysis_type: str,
        subject_id: str,
        time_range: Optional[Dict[str, datetime]] = None,
        metrics: List[PerformanceMetricType] = None,
        comparison_subjects: Optional[List[str]] = None,
        include_patterns: bool = True,
        include_recommendations: bool = True,
        granularity: str = "daily"
    ) -> Dict[str, Any]:
        """
        Analyze performance for a specific subject.
        
        Args:
            analysis_type: Type of analysis (agent, workflow, service, system)
            subject_id: ID of the subject to analyze
            time_range: Time range for analysis
            metrics: Performance metrics to analyze
            comparison_subjects: Other subjects to compare against
            include_patterns: Include identified patterns
            include_recommendations: Include optimization recommendations
            granularity: Analysis granularity
            
        Returns:
            Comprehensive performance analysis results
        """
        try:
            analysis_start = datetime.utcnow()
            
            # Set default time range if not provided
            if not time_range:
                time_range = {
                    "start": datetime.utcnow() - timedelta(days=7),
                    "end": datetime.utcnow()
                }
            
            # Set default metrics if not provided
            if not metrics:
                metrics = [PerformanceMetricType.SUCCESS_RATE, PerformanceMetricType.ACCURACY]
            
            # Gather performance data
            performance_data = await self._gather_performance_data(
                analysis_type, subject_id, time_range, metrics, granularity
            )
            
            # Analyze trends
            trends = await self._analyze_performance_trends(
                performance_data, metrics, granularity
            )
            
            # Identify patterns
            patterns = []
            if include_patterns:
                patterns = await self._identify_performance_patterns(
                    performance_data, analysis_type, subject_id
                )
            
            # Generate insights
            insights = await self._generate_performance_insights(
                performance_data, trends, patterns, analysis_type
            )
            
            # Perform comparisons if requested
            comparisons = {}
            if comparison_subjects:
                comparisons = await self._perform_comparative_analysis(
                    subject_id, comparison_subjects, time_range, metrics
                )
            
            # Calculate metrics
            calculated_metrics = await self._calculate_performance_metrics(
                performance_data, metrics
            )
            
            analysis_time = (datetime.utcnow() - analysis_start).total_seconds()
            
            return {
                "metrics": calculated_metrics,
                "patterns_identified": patterns,
                "insights": insights,
                "comparisons": comparisons,
                "trends": trends
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            raise
    
    async def identify_bottlenecks(
        self,
        analysis_type: str,
        subject_id: str,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Identify performance bottlenecks for a subject.
        
        Args:
            analysis_type: Type of subject
            subject_id: Subject identifier
            threshold: Performance threshold for bottleneck identification
            
        Returns:
            List of identified bottlenecks
        """
        try:
            bottlenecks = []
            
            # Get performance data
            performance_data = await self._gather_performance_data(
                analysis_type, subject_id,
                {"start": datetime.utcnow() - timedelta(days=3), "end": datetime.utcnow()},
                [PerformanceMetricType.SPEED, PerformanceMetricType.SUCCESS_RATE],
                "hourly"
            )
            
            # Analyze for bottlenecks
            for metric_type, data_points in performance_data.items():
                if not data_points:
                    continue
                
                # Calculate average performance
                values = [point.get("value", 0) for point in data_points]
                if not values:
                    continue
                
                avg_performance = statistics.mean(values)
                
                # Check if below threshold
                if avg_performance < threshold:
                    bottleneck = {
                        "type": "performance_degradation",
                        "metric": metric_type,
                        "subject_id": subject_id,
                        "average_performance": avg_performance,
                        "threshold": threshold,
                        "severity": "high" if avg_performance < threshold * 0.7 else "medium",
                        "data_points": len(values),
                        "time_period": "3 days"
                    }
                    bottlenecks.append(bottleneck)
            
            # Sort by severity
            bottlenecks.sort(key=lambda x: x["average_performance"])
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")
            return []
    
    async def predict_performance(
        self,
        subject_id: str,
        prediction_horizon: timedelta = timedelta(hours=24),
        metrics: List[PerformanceMetricType] = None
    ) -> Dict[str, Any]:
        """
        Predict future performance based on historical patterns.
        
        Args:
            subject_id: Subject to predict performance for
            prediction_horizon: How far into the future to predict
            metrics: Metrics to predict
            
        Returns:
            Performance predictions
        """
        try:
            if not metrics:
                metrics = [PerformanceMetricType.SUCCESS_RATE, PerformanceMetricType.ACCURACY]
            
            predictions = {}
            
            # Get historical data for trend analysis
            historical_data = await self._gather_performance_data(
                "agent", subject_id,
                {"start": datetime.utcnow() - timedelta(days=14), "end": datetime.utcnow()},
                metrics,
                "hourly"
            )
            
            for metric in metrics:
                metric_data = historical_data.get(metric.value, [])
                if len(metric_data) < 10:  # Need minimum data points
                    continue
                
                # Simple linear trend prediction
                values = [point.get("value", 0) for point in metric_data[-24:]]  # Last 24 hours
                if values:
                    # Calculate trend
                    trend = self._calculate_trend(values)
                    current_value = values[-1]
                    
                    # Predict future value
                    hours_ahead = prediction_horizon.total_seconds() / 3600
                    predicted_value = current_value + (trend * hours_ahead)
                    
                    # Ensure realistic bounds
                    predicted_value = max(0, min(1.0, predicted_value))
                    
                    predictions[metric.value] = {
                        "current_value": current_value,
                        "predicted_value": predicted_value,
                        "trend": trend,
                        "confidence": self._calculate_prediction_confidence(values, trend),
                        "prediction_horizon": str(prediction_horizon),
                        "data_points_used": len(values)
                    }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return {}
    
    async def generate_optimization_recommendations(
        self,
        subject_id: str,
        analysis_type: str,
        performance_goals: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations based on performance analysis.
        
        Args:
            subject_id: Subject to optimize
            analysis_type: Type of subject
            performance_goals: Target performance metrics
            
        Returns:
            List of optimization recommendations
        """
        try:
            recommendations = []
            
            # Analyze current performance
            current_performance = await self._gather_performance_data(
                analysis_type, subject_id,
                {"start": datetime.utcnow() - timedelta(days=7), "end": datetime.utcnow()},
                list(PerformanceMetricType),
                "daily"
            )
            
            # Compare with goals
            for goal_metric, target_value in performance_goals.items():
                metric_data = current_performance.get(goal_metric, [])
                if not metric_data:
                    continue
                
                current_avg = statistics.mean([p.get("value", 0) for p in metric_data])
                gap = target_value - current_avg
                
                if gap > 0.05:  # 5% improvement needed
                    # Generate specific recommendations
                    recs = await self._generate_metric_recommendations(
                        goal_metric, current_avg, target_value, subject_id
                    )
                    recommendations.extend(recs)
            
            # Add pattern-based recommendations
            pattern_recs = await self._generate_pattern_based_recommendations(
                subject_id, analysis_type, current_performance
            )
            recommendations.extend(pattern_recs)
            
            # Sort by impact and priority
            recommendations.sort(key=lambda x: x.get("priority", 5), reverse=True)
            
            return recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return []
    
    # Private methods
    
    async def _gather_performance_data(
        self,
        analysis_type: str,
        subject_id: str,
        time_range: Dict[str, datetime],
        metrics: List[PerformanceMetricType],
        granularity: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Gather performance data from various sources."""
        try:
            performance_data = defaultdict(list)
            
            # Try to get data from Redis cache first
            for metric in metrics:
                cache_key = f"performance_{analysis_type}_{subject_id}_{metric.value}"
                cached_data = await self.redis_service.get_performance_metrics(cache_key, 1000)
                
                if cached_data:
                    # Filter by time range
                    filtered_data = []
                    for data_point in cached_data:
                        timestamp = datetime.fromisoformat(data_point["timestamp"])
                        if time_range["start"] <= timestamp <= time_range["end"]:
                            filtered_data.append(data_point)
                    
                    performance_data[metric.value] = filtered_data
                else:
                    # Generate synthetic data for demo purposes
                    synthetic_data = self._generate_synthetic_performance_data(
                        metric, time_range, granularity
                    )
                    performance_data[metric.value] = synthetic_data
            
            return dict(performance_data)
            
        except Exception as e:
            logger.error(f"Error gathering performance data: {e}")
            return {}
    
    def _generate_synthetic_performance_data(
        self,
        metric: PerformanceMetricType,
        time_range: Dict[str, datetime],
        granularity: str
    ) -> List[Dict[str, Any]]:
        """Generate synthetic performance data for demonstration."""
        import random
        
        data_points = []
        current_time = time_range["start"]
        
        # Determine time delta based on granularity
        if granularity == "hourly":
            delta = timedelta(hours=1)
        elif granularity == "daily":
            delta = timedelta(days=1)
        else:
            delta = timedelta(hours=6)
        
        while current_time < time_range["end"]:
            # Generate realistic values based on metric type
            if metric == PerformanceMetricType.SUCCESS_RATE:
                value = random.uniform(0.7, 0.95)
            elif metric == PerformanceMetricType.ACCURACY:
                value = random.uniform(0.8, 0.98)
            elif metric == PerformanceMetricType.SPEED:
                value = random.uniform(0.6, 0.9)
            else:
                value = random.uniform(0.5, 1.0)
            
            data_points.append({
                "value": value,
                "timestamp": current_time.isoformat(),
                "context": {"synthetic": True}
            })
            
            current_time += delta
        
        return data_points
    
    async def _analyze_performance_trends(
        self,
        performance_data: Dict[str, List[Dict[str, Any]]],
        metrics: List[PerformanceMetricType],
        granularity: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze performance trends."""
        try:
            trends = {}
            
            for metric in metrics:
                metric_data = performance_data.get(metric.value, [])
                if len(metric_data) < 2:
                    continue
                
                # Sort by timestamp
                sorted_data = sorted(metric_data, key=lambda x: x["timestamp"])
                
                # Calculate trend points
                trend_points = []
                window_size = max(3, len(sorted_data) // 10)  # Adaptive window size
                
                for i in range(window_size, len(sorted_data)):
                    window_data = sorted_data[i-window_size:i]
                    values = [point["value"] for point in window_data]
                    avg_value = statistics.mean(values)
                    
                    trend_points.append({
                        "timestamp": sorted_data[i]["timestamp"],
                        "value": avg_value,
                        "trend": self._calculate_trend(values),
                        "volatility": statistics.stdev(values) if len(values) > 1 else 0
                    })
                
                trends[metric.value] = trend_points
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing performance trends: {e}")
            return {}
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend from a series of values."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi * xi for xi in x)
        
        # Calculate slope (trend)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    def _calculate_prediction_confidence(
        self, 
        values: List[float], 
        trend: float
    ) -> float:
        """Calculate confidence in prediction based on data consistency."""
        if len(values) < 3:
            return 0.5
        
        # Calculate R-squared as confidence measure
        mean_value = statistics.mean(values)
        predicted_values = [mean_value + trend * i for i in range(len(values))]
        
        ss_res = sum((values[i] - predicted_values[i]) ** 2 for i in range(len(values)))
        ss_tot = sum((values[i] - mean_value) ** 2 for i in range(len(values)))
        
        if ss_tot == 0:
            return 0.9  # Perfect fit
        
        r_squared = 1 - (ss_res / ss_tot)
        return max(0.1, min(0.9, r_squared))
    
    async def _identify_performance_patterns(
        self,
        performance_data: Dict[str, List[Dict[str, Any]]],
        analysis_type: str,
        subject_id: str
    ) -> List[LearningPattern]:
        """Identify performance patterns using the pattern engine."""
        try:
            patterns = []
            
            # Convert performance data to pattern search contexts
            for metric, data_points in performance_data.items():
                if len(data_points) < 5:
                    continue
                
                # Create context for pattern search
                context = {
                    "subject_id": subject_id,
                    "analysis_type": analysis_type,
                    "metric_type": metric,
                    "data_points": len(data_points),
                    "average_performance": statistics.mean([p["value"] for p in data_points])
                }
                
                # Search for matching patterns
                matches = await self.pattern_engine.search_patterns(
                    context=context,
                    similarity_threshold=0.7,
                    max_results=5
                )
                
                for match in matches:
                    patterns.append(match.pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying performance patterns: {e}")
            return []
    
    async def _generate_performance_insights(
        self,
        performance_data: Dict[str, List[Dict[str, Any]]],
        trends: Dict[str, List[Dict[str, Any]]],
        patterns: List[LearningPattern],
        analysis_type: str
    ) -> List[PerformanceInsight]:
        """Generate insights from performance analysis."""
        try:
            insights = []
            
            # Trend-based insights
            for metric, trend_data in trends.items():
                if not trend_data:
                    continue
                
                recent_trend = trend_data[-1]["trend"] if trend_data else 0
                
                if recent_trend > 0.01:
                    insights.append(PerformanceInsight(
                        type="trend",
                        description=f"{metric} is showing positive trend",
                        impact="medium",
                        confidence=0.8,
                        recommended_actions=[f"Monitor {metric} to maintain improvement"]
                    ))
                elif recent_trend < -0.01:
                    insights.append(PerformanceInsight(
                        type="trend",
                        description=f"{metric} is declining",
                        impact="high",
                        confidence=0.8,
                        recommended_actions=[f"Investigate causes of {metric} decline"]
                    ))
            
            # Pattern-based insights
            if patterns:
                insights.append(PerformanceInsight(
                    type="opportunity",
                    description=f"Found {len(patterns)} performance patterns for optimization",
                    impact="medium",
                    confidence=0.7,
                    recommended_actions=["Apply pattern-based optimizations"]
                ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
            return []
    
    async def _perform_comparative_analysis(
        self,
        subject_id: str,
        comparison_subjects: List[str],
        time_range: Dict[str, datetime],
        metrics: List[PerformanceMetricType]
    ) -> Dict[str, Dict[str, float]]:
        """Perform comparative analysis between subjects."""
        try:
            comparisons = {}
            
            # Get data for main subject
            main_data = await self._gather_performance_data(
                "agent", subject_id, time_range, metrics, "daily"
            )
            
            for comparison_subject in comparison_subjects:
                comparison_data = await self._gather_performance_data(
                    "agent", comparison_subject, time_range, metrics, "daily"
                )
                
                comparison_results = {}
                for metric in metrics:
                    main_values = [p["value"] for p in main_data.get(metric.value, [])]
                    comp_values = [p["value"] for p in comparison_data.get(metric.value, [])]
                    
                    if main_values and comp_values:
                        main_avg = statistics.mean(main_values)
                        comp_avg = statistics.mean(comp_values)
                        comparison_results[metric.value] = (main_avg - comp_avg) / comp_avg if comp_avg > 0 else 0
                
                comparisons[comparison_subject] = comparison_results
            
            return comparisons
            
        except Exception as e:
            logger.error(f"Error performing comparative analysis: {e}")
            return {}
    
    async def _calculate_performance_metrics(
        self,
        performance_data: Dict[str, List[Dict[str, Any]]],
        metrics: List[PerformanceMetricType]
    ) -> Dict[str, PatternMetrics]:
        """Calculate performance metrics from raw data."""
        try:
            calculated_metrics = {}
            
            for metric in metrics:
                data_points = performance_data.get(metric.value, [])
                if not data_points:
                    continue
                
                values = [p["value"] for p in data_points]
                
                # Create PatternMetrics object
                pattern_metrics = PatternMetrics(
                    applications=len(values),
                    successes=len([v for v in values if v > 0.7]),  # Success threshold
                    failures=len([v for v in values if v <= 0.7]),
                    average_confidence=statistics.mean(values),
                    average_execution_time=1.0  # Default value
                )
                
                calculated_metrics[metric.value] = pattern_metrics
            
            return calculated_metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    async def _load_historical_data(self) -> None:
        """Load historical performance data."""
        try:
            # Load cached performance data
            cache_stats = await self.redis_service.get_cache_statistics()
            logger.info(f"Loaded performance cache with {cache_stats.get('performance_count', 0)} entries")
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    async def _initialize_analysis_models(self) -> None:
        """Initialize analysis models and algorithms."""
        try:
            # Initialize trend analysis parameters
            self.trend_window_size = 10
            self.anomaly_threshold = 2.0  # Standard deviations
            
            logger.info("Analysis models initialized")
            
        except Exception as e:
            logger.error(f"Error initializing analysis models: {e}")
    
    async def _generate_metric_recommendations(
        self,
        metric: str,
        current_value: float,
        target_value: float,
        subject_id: str
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for improving a specific metric."""
        recommendations = []
        
        gap = target_value - current_value
        priority = min(10, max(1, int(gap * 10)))
        
        if metric == "success_rate":
            recommendations.append({
                "type": "performance",
                "title": "Improve Success Rate",
                "description": f"Increase success rate from {current_value:.2f} to {target_value:.2f}",
                "expected_impact": {"success_rate": gap},
                "priority": priority,
                "confidence": 0.8,
                "implementation_effort": "medium"
            })
        
        return recommendations
    
    async def _generate_pattern_based_recommendations(
        self,
        subject_id: str,
        analysis_type: str,
        performance_data: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on identified patterns."""
        recommendations = []
        
        # Simple pattern-based recommendation
        if performance_data:
            recommendations.append({
                "type": "strategy",
                "title": "Apply Performance Patterns",
                "description": "Apply learned performance patterns to improve efficiency",
                "expected_impact": {"overall_performance": 0.1},
                "priority": 7,
                "confidence": 0.7,
                "implementation_effort": "low"
            })
        
        return recommendations