#!/usr/bin/env python3
"""
Parser Performance Monitor

This service tracks and analyzes the performance of different parsers in the 
hierarchical parsing system. It collects metrics on success rates, parse times,
confidence scores, and provides insights for optimizing parser selection.
"""

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from shared.utils.database_setup import get_db
from shared.database.models import User

logger = logging.getLogger(__name__)

class ParseOutcome(Enum):
    """Possible outcomes of a parsing attempt"""
    SUCCESS = "success"
    FAILED_LOW_CONFIDENCE = "failed_low_confidence"
    FAILED_EXCEPTION = "failed_exception"
    FAILED_NO_RESULT = "failed_no_result"

@dataclass
class ParseMetric:
    """Individual parsing performance metric"""
    parser_name: str
    timestamp: datetime
    input_length: int
    parse_time_ms: float
    outcome: ParseOutcome
    confidence_score: float
    error_message: str = ""
    user_context_length: int = 0
    input_type: str = "unknown"  # calendar, list, subtask, etc.
    
@dataclass 
class ParserStats:
    """Aggregated statistics for a parser"""
    parser_name: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    avg_parse_time_ms: float = 0.0
    avg_confidence_score: float = 0.0
    success_rate: float = 0.0
    avg_input_length: int = 0
    most_common_failure: str = ""
    last_used: Optional[datetime] = None
    
    # Time-based metrics
    attempts_last_hour: int = 0
    attempts_last_day: int = 0
    success_rate_last_hour: float = 0.0
    success_rate_last_day: float = 0.0

@dataclass
class ParsingSession:
    """Represents a complete parsing session with all parser attempts"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    input_text: str = ""
    input_length: int = 0
    user_context: str = ""
    final_parser: str = ""
    total_time_ms: float = 0.0
    parser_attempts: List['ParseAttempt'] = field(default_factory=list)
    session_success: bool = False
    fallback_used: bool = False

@dataclass
class ParseAttempt:
    """Individual parser attempt within a session"""
    parser_name: str
    start_time: datetime
    end_time: datetime
    outcome: ParseOutcome
    confidence_score: float
    error_message: str = ""
    
    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time).total_seconds() * 1000

class ParserPerformanceMonitor:
    """Monitors and analyzes parser performance with real-time metrics"""
    
    def __init__(self, max_metrics_in_memory: int = 10000):
        self.max_metrics_in_memory = max_metrics_in_memory
        self.metrics: deque = deque(maxlen=max_metrics_in_memory)
        self.active_sessions: Dict[str, ParsingSession] = {}
        self.parser_stats: Dict[str, ParserStats] = {}
        
        # Performance thresholds for alerts
        self.performance_thresholds = {
            "min_success_rate": 0.7,  # Alert if success rate drops below 70%
            "max_avg_parse_time_ms": 5000,  # Alert if avg parse time > 5s
            "min_confidence_score": 0.6,  # Alert if avg confidence < 60%
        }
        
        logger.info("🔍 Parser Performance Monitor initialized")
    
    def start_parsing_session(self, session_id: str, input_text: str, user_context: str = "") -> None:
        """Start tracking a new parsing session"""
        session = ParsingSession(
            session_id=session_id,
            start_time=datetime.utcnow(),
            input_text=input_text,
            input_length=len(input_text),
            user_context=user_context
        )
        
        self.active_sessions[session_id] = session
        logger.debug(f"📊 Started tracking parsing session: {session_id}")
    
    def record_parser_attempt(self, session_id: str, parser_name: str, 
                            outcome: ParseOutcome, confidence_score: float = 0.0,
                            parse_time_ms: float = 0.0, error_message: str = "") -> None:
        """Record an individual parser attempt within a session"""
        
        if session_id not in self.active_sessions:
            logger.warning(f"⚠️ Attempt to record parser attempt for unknown session: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        now = datetime.utcnow()
        
        # Create attempt record
        attempt = ParseAttempt(
            parser_name=parser_name,
            start_time=now - timedelta(milliseconds=parse_time_ms),
            end_time=now,
            outcome=outcome,
            confidence_score=confidence_score,
            error_message=error_message
        )
        
        session.parser_attempts.append(attempt)
        
        # Create detailed metric
        metric = ParseMetric(
            parser_name=parser_name,
            timestamp=now,
            input_length=session.input_length,
            parse_time_ms=parse_time_ms,
            outcome=outcome,
            confidence_score=confidence_score,
            error_message=error_message,
            user_context_length=len(session.user_context),
            input_type=self._detect_input_type(session.input_text, session.user_context)
        )
        
        self.metrics.append(metric)
        self._update_parser_stats(metric)
        
        logger.debug(f"📊 Recorded {parser_name} attempt: {outcome.value} (conf: {confidence_score:.2f})")
    
    def end_parsing_session(self, session_id: str, final_parser: str = "", 
                          session_success: bool = False, fallback_used: bool = False) -> Optional[ParsingSession]:
        """End a parsing session and return session summary"""
        
        if session_id not in self.active_sessions:
            logger.warning(f"⚠️ Attempt to end unknown session: {session_id}")
            return None
        
        session = self.active_sessions[session_id]
        session.end_time = datetime.utcnow()
        session.final_parser = final_parser
        session.session_success = session_success
        session.fallback_used = fallback_used
        session.total_time_ms = (session.end_time - session.start_time).total_seconds() * 1000
        
        # Remove from active sessions
        completed_session = self.active_sessions.pop(session_id)
        
        logger.info(f"📊 Completed parsing session {session_id}: "
                   f"{len(session.parser_attempts)} attempts, "
                   f"final: {final_parser}, "
                   f"success: {session_success}, "
                   f"time: {session.total_time_ms:.1f}ms")
        
        return completed_session
    
    def get_parser_performance_summary(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary for all parsers"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        
        summary = {
            "monitoring_period_hours": time_window_hours,
            "total_metrics_collected": len(self.metrics),
            "recent_metrics": len(recent_metrics),
            "parser_performance": {},
            "overall_stats": self._calculate_overall_stats(recent_metrics),
            "performance_alerts": self._check_performance_alerts(),
            "parser_usage_distribution": self._calculate_usage_distribution(recent_metrics),
            "trending_patterns": self._analyze_trending_patterns(recent_metrics),
            "recommendations": self._generate_recommendations()
        }
        
        # Calculate per-parser performance
        for parser_name in self.parser_stats:
            summary["parser_performance"][parser_name] = self._calculate_parser_performance(
                parser_name, recent_metrics
            )
        
        return summary
    
    def get_parser_comparison(self, parsers: List[str], time_window_hours: int = 24) -> Dict[str, Any]:
        """Compare performance between specific parsers"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.metrics 
                         if m.timestamp >= cutoff_time and m.parser_name in parsers]
        
        comparison = {
            "compared_parsers": parsers,
            "time_window_hours": time_window_hours,
            "total_attempts": len(recent_metrics),
            "parser_comparison": {}
        }
        
        # Group metrics by parser
        parser_metrics = defaultdict(list)
        for metric in recent_metrics:
            parser_metrics[metric.parser_name].append(metric)
        
        # Calculate comparison metrics
        for parser_name in parsers:
            metrics = parser_metrics[parser_name]
            if metrics:
                comparison["parser_comparison"][parser_name] = {
                    "attempts": len(metrics),
                    "success_rate": len([m for m in metrics if m.outcome == ParseOutcome.SUCCESS]) / len(metrics),
                    "avg_parse_time_ms": sum(m.parse_time_ms for m in metrics) / len(metrics),
                    "avg_confidence": sum(m.confidence_score for m in metrics) / len(metrics),
                    "avg_input_length": sum(m.input_length for m in metrics) / len(metrics),
                    "most_common_input_type": self._most_common_input_type(metrics)
                }
            else:
                comparison["parser_comparison"][parser_name] = {
                    "attempts": 0,
                    "success_rate": 0.0,
                    "avg_parse_time_ms": 0.0,
                    "avg_confidence": 0.0,
                    "avg_input_length": 0,
                    "most_common_input_type": "none"
                }
        
        return comparison
    
    def export_metrics_for_analysis(self, time_window_hours: int = 168) -> List[Dict[str, Any]]:
        """Export raw metrics for external analysis (default: 1 week)"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        
        exported_metrics = []
        for metric in recent_metrics:
            exported_metrics.append({
                "parser_name": metric.parser_name,
                "timestamp": metric.timestamp.isoformat(),
                "input_length": metric.input_length,
                "parse_time_ms": metric.parse_time_ms,
                "outcome": metric.outcome.value,
                "confidence_score": metric.confidence_score,
                "error_message": metric.error_message,
                "user_context_length": metric.user_context_length,
                "input_type": metric.input_type
            })
        
        logger.info(f"📊 Exported {len(exported_metrics)} metrics for analysis")
        return exported_metrics
    
    def _detect_input_type(self, input_text: str, user_context: str) -> str:
        """Detect the type of input for categorization"""
        text_lower = (input_text + " " + user_context).lower()
        
        if any(word in text_lower for word in ["due:", "assignments", "calendar", "schedule"]):
            return "calendar"
        elif any(word in text_lower for word in ["subtask", "opportunity", "break down"]):
            return "subtask"
        elif any(word in text_lower for word in ["\n-", "\n*", "\n1.", "sections"]):
            return "list"
        elif len(input_text.split('\n')) > 5:
            return "multiline"
        else:
            return "general"
    
    def _update_parser_stats(self, metric: ParseMetric) -> None:
        """Update aggregated statistics for a parser"""
        
        parser_name = metric.parser_name
        if parser_name not in self.parser_stats:
            self.parser_stats[parser_name] = ParserStats(parser_name=parser_name)
        
        stats = self.parser_stats[parser_name]
        stats.total_attempts += 1
        stats.last_used = metric.timestamp
        
        if metric.outcome == ParseOutcome.SUCCESS:
            stats.successful_attempts += 1
        else:
            stats.failed_attempts += 1
        
        # Update averages (using running average)
        n = stats.total_attempts
        stats.avg_parse_time_ms = ((stats.avg_parse_time_ms * (n-1)) + metric.parse_time_ms) / n
        stats.avg_confidence_score = ((stats.avg_confidence_score * (n-1)) + metric.confidence_score) / n
        stats.avg_input_length = ((stats.avg_input_length * (n-1)) + metric.input_length) / n
        stats.success_rate = stats.successful_attempts / stats.total_attempts
        
        # Update time-based metrics
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        recent_metrics = [m for m in self.metrics 
                         if m.parser_name == parser_name and m.timestamp >= one_hour_ago]
        stats.attempts_last_hour = len(recent_metrics)
        if recent_metrics:
            stats.success_rate_last_hour = len([m for m in recent_metrics 
                                              if m.outcome == ParseOutcome.SUCCESS]) / len(recent_metrics)
        
        recent_metrics_day = [m for m in self.metrics 
                             if m.parser_name == parser_name and m.timestamp >= one_day_ago]
        stats.attempts_last_day = len(recent_metrics_day)
        if recent_metrics_day:
            stats.success_rate_last_day = len([m for m in recent_metrics_day 
                                             if m.outcome == ParseOutcome.SUCCESS]) / len(recent_metrics_day)
    
    def _calculate_overall_stats(self, metrics: List[ParseMetric]) -> Dict[str, Any]:
        """Calculate overall performance statistics"""
        if not metrics:
            return {}
        
        successful = [m for m in metrics if m.outcome == ParseOutcome.SUCCESS]
        
        return {
            "total_attempts": len(metrics),
            "successful_attempts": len(successful),
            "overall_success_rate": len(successful) / len(metrics),
            "avg_parse_time_ms": sum(m.parse_time_ms for m in metrics) / len(metrics),
            "avg_confidence_score": sum(m.confidence_score for m in metrics) / len(metrics),
            "avg_input_length": sum(m.input_length for m in metrics) / len(metrics),
            "most_active_parser": max(metrics, key=lambda m: metrics.count(m.parser_name)).parser_name if metrics else None,
            "fastest_parser": min(metrics, key=lambda m: m.parse_time_ms).parser_name if metrics else None,
            "most_confident_parser": max(metrics, key=lambda m: m.confidence_score).parser_name if metrics else None
        }
    
    def _check_performance_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance issues that need attention"""
        alerts = []
        
        for parser_name, stats in self.parser_stats.items():
            if stats.total_attempts < 5:  # Skip parsers with insufficient data
                continue
                
            # Success rate alert
            if stats.success_rate < self.performance_thresholds["min_success_rate"]:
                alerts.append({
                    "type": "low_success_rate",
                    "parser": parser_name,
                    "current_value": stats.success_rate,
                    "threshold": self.performance_thresholds["min_success_rate"],
                    "severity": "high" if stats.success_rate < 0.5 else "medium",
                    "message": f"{parser_name} success rate ({stats.success_rate:.1%}) below threshold ({self.performance_thresholds['min_success_rate']:.1%})"
                })
            
            # Parse time alert
            if stats.avg_parse_time_ms > self.performance_thresholds["max_avg_parse_time_ms"]:
                alerts.append({
                    "type": "slow_performance",
                    "parser": parser_name,
                    "current_value": stats.avg_parse_time_ms,
                    "threshold": self.performance_thresholds["max_avg_parse_time_ms"],
                    "severity": "medium",
                    "message": f"{parser_name} avg parse time ({stats.avg_parse_time_ms:.0f}ms) exceeds threshold ({self.performance_thresholds['max_avg_parse_time_ms']:.0f}ms)"
                })
            
            # Confidence score alert
            if stats.avg_confidence_score < self.performance_thresholds["min_confidence_score"]:
                alerts.append({
                    "type": "low_confidence",
                    "parser": parser_name,
                    "current_value": stats.avg_confidence_score,
                    "threshold": self.performance_thresholds["min_confidence_score"],
                    "severity": "low",
                    "message": f"{parser_name} avg confidence ({stats.avg_confidence_score:.1%}) below threshold ({self.performance_thresholds['min_confidence_score']:.1%})"
                })
        
        return alerts
    
    def _calculate_usage_distribution(self, metrics: List[ParseMetric]) -> Dict[str, Any]:
        """Calculate how usage is distributed across parsers"""
        if not metrics:
            return {}
        
        parser_counts = defaultdict(int)
        for metric in metrics:
            parser_counts[metric.parser_name] += 1
        
        total = len(metrics)
        distribution = {parser: count/total for parser, count in parser_counts.items()}
        
        return {
            "total_attempts": total,
            "parser_distribution": dict(distribution),
            "most_used_parser": max(parser_counts.items(), key=lambda x: x[1])[0],
            "least_used_parser": min(parser_counts.items(), key=lambda x: x[1])[0],
            "usage_concentration": max(distribution.values())  # How concentrated usage is
        }
    
    def _analyze_trending_patterns(self, metrics: List[ParseMetric]) -> Dict[str, Any]:
        """Analyze trending patterns in performance"""
        if len(metrics) < 10:
            return {"insufficient_data": True}
        
        # Sort by timestamp
        sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
        
        # Split into early and late periods
        mid_point = len(sorted_metrics) // 2
        early_metrics = sorted_metrics[:mid_point]
        late_metrics = sorted_metrics[mid_point:]
        
        early_success_rate = len([m for m in early_metrics if m.outcome == ParseOutcome.SUCCESS]) / len(early_metrics)
        late_success_rate = len([m for m in late_metrics if m.outcome == ParseOutcome.SUCCESS]) / len(late_metrics)
        
        early_avg_time = sum(m.parse_time_ms for m in early_metrics) / len(early_metrics)
        late_avg_time = sum(m.parse_time_ms for m in late_metrics) / len(late_metrics)
        
        return {
            "success_rate_trend": "improving" if late_success_rate > early_success_rate else "declining",
            "success_rate_change": late_success_rate - early_success_rate,
            "performance_trend": "improving" if late_avg_time < early_avg_time else "declining",
            "performance_change_ms": late_avg_time - early_avg_time,
            "early_period_success": early_success_rate,
            "late_period_success": late_success_rate,
            "early_period_avg_time": early_avg_time,
            "late_period_avg_time": late_avg_time
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on performance analysis"""
        recommendations = []
        
        # Check for underperforming parsers
        for parser_name, stats in self.parser_stats.items():
            if stats.total_attempts >= 10:  # Only recommend for parsers with sufficient data
                if stats.success_rate < 0.6:
                    recommendations.append(f"Consider improving {parser_name} parser - low success rate ({stats.success_rate:.1%})")
                
                if stats.avg_parse_time_ms > 3000:
                    recommendations.append(f"Optimize {parser_name} parser performance - slow average time ({stats.avg_parse_time_ms:.0f}ms)")
        
        # Check for usage patterns
        if len(self.parser_stats) > 1:
            best_parser = max(self.parser_stats.values(), 
                            key=lambda s: s.success_rate * (1 / max(s.avg_parse_time_ms, 1)))
            recommendations.append(f"Consider prioritizing {best_parser.parser_name} parser - best performance balance")
        
        return recommendations
    
    def _calculate_parser_performance(self, parser_name: str, metrics: List[ParseMetric]) -> Dict[str, Any]:
        """Calculate detailed performance metrics for a specific parser"""
        parser_metrics = [m for m in metrics if m.parser_name == parser_name]
        
        if not parser_metrics:
            return {"no_data": True}
        
        successful = [m for m in parser_metrics if m.outcome == ParseOutcome.SUCCESS]
        
        return {
            "attempts": len(parser_metrics),
            "successful": len(successful),
            "success_rate": len(successful) / len(parser_metrics),
            "avg_parse_time_ms": sum(m.parse_time_ms for m in parser_metrics) / len(parser_metrics),
            "median_parse_time_ms": sorted([m.parse_time_ms for m in parser_metrics])[len(parser_metrics)//2],
            "avg_confidence_score": sum(m.confidence_score for m in parser_metrics) / len(parser_metrics),
            "avg_input_length": sum(m.input_length for m in parser_metrics) / len(parser_metrics),
            "failure_reasons": self._analyze_failure_reasons(parser_metrics),
            "input_type_performance": self._analyze_input_type_performance(parser_metrics)
        }
    
    def _analyze_failure_reasons(self, metrics: List[ParseMetric]) -> Dict[str, int]:
        """Analyze reasons for parser failures"""
        failure_counts = defaultdict(int)
        for metric in metrics:
            if metric.outcome != ParseOutcome.SUCCESS:
                failure_counts[metric.outcome.value] += 1
        
        return dict(failure_counts)
    
    def _analyze_input_type_performance(self, metrics: List[ParseMetric]) -> Dict[str, Dict[str, float]]:
        """Analyze parser performance by input type"""
        type_performance = defaultdict(lambda: {"attempts": 0, "successes": 0})
        
        for metric in metrics:
            type_performance[metric.input_type]["attempts"] += 1
            if metric.outcome == ParseOutcome.SUCCESS:
                type_performance[metric.input_type]["successes"] += 1
        
        # Calculate success rates
        result = {}
        for input_type, stats in type_performance.items():
            result[input_type] = {
                "attempts": stats["attempts"],
                "success_rate": stats["successes"] / stats["attempts"] if stats["attempts"] > 0 else 0.0
            }
        
        return result
    
    def _most_common_input_type(self, metrics: List[ParseMetric]) -> str:
        """Find the most common input type for a set of metrics"""
        if not metrics:
            return "none"
        
        type_counts = defaultdict(int)
        for metric in metrics:
            type_counts[metric.input_type] += 1
        
        return max(type_counts.items(), key=lambda x: x[1])[0]


# Global instance
parser_performance_monitor = ParserPerformanceMonitor()

# Integration helper functions
def start_monitoring_session(session_id: str, input_text: str, user_context: str = "") -> None:
    """Start monitoring a parsing session"""
    parser_performance_monitor.start_parsing_session(session_id, input_text, user_context)

def record_parser_performance(session_id: str, parser_name: str, success: bool, 
                            confidence_score: float = 0.0, parse_time_ms: float = 0.0, 
                            error_message: str = "") -> None:
    """Record the performance of a parser attempt"""
    outcome = ParseOutcome.SUCCESS if success else ParseOutcome.FAILED_EXCEPTION
    parser_performance_monitor.record_parser_attempt(
        session_id, parser_name, outcome, confidence_score, parse_time_ms, error_message
    )

def end_monitoring_session(session_id: str, final_parser: str = "", 
                          session_success: bool = False, fallback_used: bool = False) -> Optional[ParsingSession]:
    """End a monitoring session"""
    return parser_performance_monitor.end_parsing_session(
        session_id, final_parser, session_success, fallback_used
    )

def get_performance_dashboard() -> Dict[str, Any]:
    """Get a performance dashboard for monitoring"""
    return parser_performance_monitor.get_parser_performance_summary()

def get_parser_recommendations() -> List[str]:
    """Get recommendations for improving parser performance"""
    summary = parser_performance_monitor.get_parser_performance_summary()
    return summary.get("recommendations", [])