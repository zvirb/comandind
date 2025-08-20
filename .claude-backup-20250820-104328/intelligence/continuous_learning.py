#!/usr/bin/env python3
"""
Continuous Learning Integration Framework
Enhanced Nexus Synthesis Agent - Intelligence Integration Phase 5 Stream 3

Implements systematic learning from orchestration outcomes with pattern recognition,
strategy refinement, and adaptive optimization based on historical performance.
"""

import json
import pickle
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, Counter
import logging
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OrchestrationOutcome:
    """Complete orchestration outcome record"""
    orchestration_id: str
    timestamp: datetime
    task_profile: Dict[str, Any]
    selected_agents: List[str]
    success: bool
    completion_time: int
    efficiency_score: float
    bottlenecks_encountered: List[str]
    resource_utilization: Dict[str, float]
    coordination_challenges: List[str]
    quality_metrics: Dict[str, float]
    user_satisfaction: Optional[float]
    lessons_learned: List[str]

@dataclass
class LearningPattern:
    """Identified learning pattern"""
    pattern_id: str
    pattern_type: str  # "success", "failure", "optimization", "bottleneck"
    pattern_description: str
    confidence_score: float
    frequency: int
    contexts: List[str]  # Where this pattern applies
    evidence: List[str]
    recommendations: List[str]
    created_at: datetime
    last_validated: datetime

@dataclass
class AdaptiveStrategy:
    """Adaptive orchestration strategy"""
    strategy_id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    success_rate: float
    usage_count: int
    effectiveness_score: float
    last_updated: datetime

class ContinuousLearningEngine:
    """
    Continuous Learning Integration Framework
    
    Features:
    - Outcome analysis and pattern extraction
    - Success/failure pattern recognition
    - Adaptive strategy development
    - Predictive failure prevention
    - Performance optimization learning
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("/home/marku/ai_workflow_engine/.claude/intelligence")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Learning data storage
        self.orchestration_outcomes: List[OrchestrationOutcome] = []
        self.identified_patterns: Dict[str, LearningPattern] = {}
        self.adaptive_strategies: Dict[str, AdaptiveStrategy] = {}
        self.prediction_models: Dict[str, Any] = {}
        
        # Learning configuration
        self.min_pattern_frequency = 3
        self.pattern_confidence_threshold = 0.7
        self.learning_window_days = 30
        self.max_outcomes_stored = 1000
        
        # Performance tracking
        self.learning_metrics = {
            "patterns_identified": 0,
            "strategies_created": 0,
            "predictions_made": 0,
            "prediction_accuracy": 0.0,
            "learning_efficiency": 0.0
        }
        
        # Load existing learning data
        self._load_learning_data()
        
    def _load_learning_data(self):
        """Load existing learning data from persistent storage"""
        outcomes_file = self.data_dir / "orchestration_outcomes.json"
        patterns_file = self.data_dir / "learning_patterns.json"
        strategies_file = self.data_dir / "adaptive_strategies.json"
        
        # Load orchestration outcomes
        if outcomes_file.exists():
            try:
                with open(outcomes_file) as f:
                    data = json.load(f)
                    self.orchestration_outcomes = [
                        OrchestrationOutcome(
                            orchestration_id=item["orchestration_id"],
                            timestamp=datetime.fromisoformat(item["timestamp"]),
                            task_profile=item["task_profile"],
                            selected_agents=item["selected_agents"],
                            success=item["success"],
                            completion_time=item["completion_time"],
                            efficiency_score=item["efficiency_score"],
                            bottlenecks_encountered=item["bottlenecks_encountered"],
                            resource_utilization=item["resource_utilization"],
                            coordination_challenges=item["coordination_challenges"],
                            quality_metrics=item["quality_metrics"],
                            user_satisfaction=item.get("user_satisfaction"),
                            lessons_learned=item.get("lessons_learned", [])
                        )
                        for item in data
                    ]
                logger.info(f"Loaded {len(self.orchestration_outcomes)} orchestration outcomes")
            except Exception as e:
                logger.error(f"Error loading orchestration outcomes: {e}")
        
        # Load learning patterns
        if patterns_file.exists():
            try:
                with open(patterns_file) as f:
                    data = json.load(f)
                    for pattern_id, pattern_data in data.items():
                        self.identified_patterns[pattern_id] = LearningPattern(
                            pattern_id=pattern_data["pattern_id"],
                            pattern_type=pattern_data["pattern_type"],
                            pattern_description=pattern_data["pattern_description"],
                            confidence_score=pattern_data["confidence_score"],
                            frequency=pattern_data["frequency"],
                            contexts=pattern_data["contexts"],
                            evidence=pattern_data["evidence"],
                            recommendations=pattern_data["recommendations"],
                            created_at=datetime.fromisoformat(pattern_data["created_at"]),
                            last_validated=datetime.fromisoformat(pattern_data["last_validated"])
                        )
                logger.info(f"Loaded {len(self.identified_patterns)} learning patterns")
            except Exception as e:
                logger.error(f"Error loading learning patterns: {e}")
        
        # Load adaptive strategies
        if strategies_file.exists():
            try:
                with open(strategies_file) as f:
                    data = json.load(f)
                    for strategy_id, strategy_data in data.items():
                        self.adaptive_strategies[strategy_id] = AdaptiveStrategy(
                            strategy_id=strategy_data["strategy_id"],
                            name=strategy_data["name"],
                            description=strategy_data["description"],
                            conditions=strategy_data["conditions"],
                            actions=strategy_data["actions"],
                            success_rate=strategy_data["success_rate"],
                            usage_count=strategy_data["usage_count"],
                            effectiveness_score=strategy_data["effectiveness_score"],
                            last_updated=datetime.fromisoformat(strategy_data["last_updated"])
                        )
                logger.info(f"Loaded {len(self.adaptive_strategies)} adaptive strategies")
            except Exception as e:
                logger.error(f"Error loading adaptive strategies: {e}")
    
    def record_orchestration_outcome(self, outcome: OrchestrationOutcome):
        """Record orchestration outcome for learning"""
        self.orchestration_outcomes.append(outcome)
        
        # Maintain size limit
        if len(self.orchestration_outcomes) > self.max_outcomes_stored:
            self.orchestration_outcomes = self.orchestration_outcomes[-self.max_outcomes_stored:]
        
        # Trigger immediate pattern analysis for recent outcome
        self._analyze_recent_outcome(outcome)
        
        # Save updated outcomes
        self._save_learning_data()
        
        logger.info(f"Recorded orchestration outcome {outcome.orchestration_id}")
    
    def _analyze_recent_outcome(self, outcome: OrchestrationOutcome):
        """Analyze recent outcome for immediate learning opportunities"""
        # Success pattern analysis
        if outcome.success and outcome.efficiency_score > 0.8:
            self._identify_success_patterns(outcome)
        
        # Failure pattern analysis
        elif not outcome.success or outcome.efficiency_score < 0.5:
            self._identify_failure_patterns(outcome)
        
        # Bottleneck pattern analysis
        if outcome.bottlenecks_encountered:
            self._identify_bottleneck_patterns(outcome)
        
        # Optimization opportunity analysis
        self._identify_optimization_patterns(outcome)
    
    def _identify_success_patterns(self, outcome: OrchestrationOutcome):
        """Identify patterns that lead to successful orchestration"""
        # Agent combination success patterns
        agent_combo_hash = hashlib.md5(
            "|".join(sorted(outcome.selected_agents)).encode()
        ).hexdigest()[:8]
        
        pattern_id = f"success_agent_combo_{agent_combo_hash}"
        
        if pattern_id in self.identified_patterns:
            pattern = self.identified_patterns[pattern_id]
            pattern.frequency += 1
            pattern.confidence_score = min(1.0, pattern.confidence_score + 0.05)
            pattern.last_validated = datetime.now()
        else:
            self.identified_patterns[pattern_id] = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="success",
                pattern_description=f"Successful agent combination: {', '.join(outcome.selected_agents)}",
                confidence_score=0.7,
                frequency=1,
                contexts=[outcome.task_profile.get("domain", "unknown")],
                evidence=[f"Orchestration {outcome.orchestration_id} completed successfully"],
                recommendations=[f"Prioritize agent combination {', '.join(outcome.selected_agents)} for similar tasks"],
                created_at=datetime.now(),
                last_validated=datetime.now()
            )
        
        # Task-agent affinity patterns
        task_domain = outcome.task_profile.get("domain", "unknown")
        for agent in outcome.selected_agents:
            affinity_pattern_id = f"success_affinity_{task_domain}_{agent}"
            
            if affinity_pattern_id in self.identified_patterns:
                pattern = self.identified_patterns[affinity_pattern_id]
                pattern.frequency += 1
                pattern.confidence_score = min(1.0, pattern.confidence_score + 0.03)
            else:
                self.identified_patterns[affinity_pattern_id] = LearningPattern(
                    pattern_id=affinity_pattern_id,
                    pattern_type="success",
                    pattern_description=f"Agent {agent} shows high success in {task_domain} domain",
                    confidence_score=0.6,
                    frequency=1,
                    contexts=[task_domain],
                    evidence=[f"Successful completion in orchestration {outcome.orchestration_id}"],
                    recommendations=[f"Prioritize {agent} for {task_domain} tasks"],
                    created_at=datetime.now(),
                    last_validated=datetime.now()
                )
    
    def _identify_failure_patterns(self, outcome: OrchestrationOutcome):
        """Identify patterns that lead to orchestration failures"""
        # Agent combination failure patterns
        agent_combo_hash = hashlib.md5(
            "|".join(sorted(outcome.selected_agents)).encode()
        ).hexdigest()[:8]
        
        pattern_id = f"failure_agent_combo_{agent_combo_hash}"
        
        if pattern_id in self.identified_patterns:
            pattern = self.identified_patterns[pattern_id]
            pattern.frequency += 1
            pattern.confidence_score = min(1.0, pattern.confidence_score + 0.1)
        else:
            self.identified_patterns[pattern_id] = LearningPattern(
                pattern_id=pattern_id,
                pattern_type="failure",
                pattern_description=f"Problematic agent combination: {', '.join(outcome.selected_agents)}",
                confidence_score=0.8,
                frequency=1,
                contexts=[outcome.task_profile.get("domain", "unknown")],
                evidence=[f"Orchestration {outcome.orchestration_id} failed or performed poorly"],
                recommendations=[f"Avoid agent combination {', '.join(outcome.selected_agents)} for similar tasks"],
                created_at=datetime.now(),
                last_validated=datetime.now()
            )
        
        # Resource constraint failure patterns
        for resource_type, utilization in outcome.resource_utilization.items():
            if utilization > 0.9:  # High resource usage
                pattern_id = f"failure_resource_{resource_type}_overuse"
                
                if pattern_id in self.identified_patterns:
                    pattern = self.identified_patterns[pattern_id]
                    pattern.frequency += 1
                else:
                    self.identified_patterns[pattern_id] = LearningPattern(
                        pattern_id=pattern_id,
                        pattern_type="failure",
                        pattern_description=f"High {resource_type} utilization leads to poor performance",
                        confidence_score=0.8,
                        frequency=1,
                        contexts=[outcome.task_profile.get("domain", "unknown")],
                        evidence=[f"Resource utilization {utilization:.1%} in {outcome.orchestration_id}"],
                        recommendations=[f"Implement {resource_type} throttling or staggered execution"],
                        created_at=datetime.now(),
                        last_validated=datetime.now()
                    )
    
    def _identify_bottleneck_patterns(self, outcome: OrchestrationOutcome):
        """Identify bottleneck patterns for prevention"""
        for bottleneck in outcome.bottlenecks_encountered:
            pattern_id = f"bottleneck_{bottleneck.replace(' ', '_')}"
            
            if pattern_id in self.identified_patterns:
                pattern = self.identified_patterns[pattern_id]
                pattern.frequency += 1
                pattern.confidence_score = min(1.0, pattern.confidence_score + 0.05)
            else:
                self.identified_patterns[pattern_id] = LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type="bottleneck",
                    pattern_description=f"Recurring bottleneck: {bottleneck}",
                    confidence_score=0.7,
                    frequency=1,
                    contexts=[outcome.task_profile.get("domain", "unknown")],
                    evidence=[f"Bottleneck occurred in {outcome.orchestration_id}"],
                    recommendations=[f"Implement proactive measures to prevent {bottleneck}"],
                    created_at=datetime.now(),
                    last_validated=datetime.now()
                )
    
    def _identify_optimization_patterns(self, outcome: OrchestrationOutcome):
        """Identify optimization opportunities"""
        # Completion time optimization patterns
        if outcome.completion_time > outcome.task_profile.get("estimated_duration", 300) * 1.5:
            pattern_id = f"optimization_slow_completion_{outcome.task_profile.get('domain', 'unknown')}"
            
            if pattern_id in self.identified_patterns:
                pattern = self.identified_patterns[pattern_id]
                pattern.frequency += 1
            else:
                self.identified_patterns[pattern_id] = LearningPattern(
                    pattern_id=pattern_id,
                    pattern_type="optimization",
                    pattern_description=f"Slow completion times in {outcome.task_profile.get('domain', 'unknown')} domain",
                    confidence_score=0.6,
                    frequency=1,
                    contexts=[outcome.task_profile.get("domain", "unknown")],
                    evidence=[f"Completion time {outcome.completion_time}s vs estimated {outcome.task_profile.get('estimated_duration', 300)}s"],
                    recommendations=["Consider parallel execution or agent optimization"],
                    created_at=datetime.now(),
                    last_validated=datetime.now()
                )
    
    def generate_adaptive_strategies(self) -> List[AdaptiveStrategy]:
        """Generate adaptive strategies based on learned patterns"""
        new_strategies = []
        
        # Generate strategies from success patterns
        success_patterns = [p for p in self.identified_patterns.values() 
                          if p.pattern_type == "success" and p.confidence_score > self.pattern_confidence_threshold]
        
        for pattern in success_patterns:
            strategy_id = f"adaptive_{pattern.pattern_id}"
            
            if strategy_id not in self.adaptive_strategies:
                strategy = AdaptiveStrategy(
                    strategy_id=strategy_id,
                    name=f"Success Strategy: {pattern.pattern_description[:50]}...",
                    description=f"Apply successful pattern: {pattern.pattern_description}",
                    conditions={"pattern_match": pattern.contexts},
                    actions=[{"type": "prioritize_pattern", "pattern_id": pattern.pattern_id}],
                    success_rate=pattern.confidence_score,
                    usage_count=0,
                    effectiveness_score=pattern.confidence_score,
                    last_updated=datetime.now()
                )
                
                self.adaptive_strategies[strategy_id] = strategy
                new_strategies.append(strategy)
        
        # Generate strategies from failure patterns
        failure_patterns = [p for p in self.identified_patterns.values() 
                          if p.pattern_type == "failure" and p.confidence_score > self.pattern_confidence_threshold]
        
        for pattern in failure_patterns:
            strategy_id = f"avoidance_{pattern.pattern_id}"
            
            if strategy_id not in self.adaptive_strategies:
                strategy = AdaptiveStrategy(
                    strategy_id=strategy_id,
                    name=f"Failure Avoidance: {pattern.pattern_description[:50]}...",
                    description=f"Avoid failure pattern: {pattern.pattern_description}",
                    conditions={"pattern_risk": pattern.contexts},
                    actions=[{"type": "avoid_pattern", "pattern_id": pattern.pattern_id}],
                    success_rate=1.0 - pattern.confidence_score,
                    usage_count=0,
                    effectiveness_score=pattern.confidence_score,
                    last_updated=datetime.now()
                )
                
                self.adaptive_strategies[strategy_id] = strategy
                new_strategies.append(strategy)
        
        # Save new strategies
        if new_strategies:
            self._save_learning_data()
            self.learning_metrics["strategies_created"] += len(new_strategies)
        
        logger.info(f"Generated {len(new_strategies)} new adaptive strategies")
        return new_strategies
    
    def predict_orchestration_outcome(self, task_profile: Dict[str, Any], 
                                    selected_agents: List[str]) -> Dict[str, Any]:
        """Predict orchestration outcome based on learned patterns"""
        prediction = {
            "success_probability": 0.5,
            "estimated_completion_time": task_profile.get("estimated_duration", 300),
            "efficiency_score": 0.7,
            "risk_factors": [],
            "optimization_opportunities": [],
            "confidence": 0.5
        }
        
        # Analyze against success patterns
        success_indicators = 0
        failure_indicators = 0
        
        for pattern in self.identified_patterns.values():
            if pattern.pattern_type == "success" and self._pattern_matches(pattern, task_profile, selected_agents):
                success_indicators += pattern.confidence_score
                prediction["optimization_opportunities"].append(pattern.pattern_description)
            
            elif pattern.pattern_type == "failure" and self._pattern_matches(pattern, task_profile, selected_agents):
                failure_indicators += pattern.confidence_score
                prediction["risk_factors"].append(pattern.pattern_description)
        
        # Calculate success probability
        if success_indicators + failure_indicators > 0:
            prediction["success_probability"] = success_indicators / (success_indicators + failure_indicators)
            prediction["confidence"] = min(1.0, (success_indicators + failure_indicators) / 5.0)
        
        # Adjust estimates based on patterns
        if failure_indicators > success_indicators:
            prediction["estimated_completion_time"] = int(prediction["estimated_completion_time"] * 1.3)
            prediction["efficiency_score"] = max(0.3, prediction["efficiency_score"] - 0.2)
        elif success_indicators > failure_indicators:
            prediction["estimated_completion_time"] = int(prediction["estimated_completion_time"] * 0.9)
            prediction["efficiency_score"] = min(1.0, prediction["efficiency_score"] + 0.2)
        
        self.learning_metrics["predictions_made"] += 1
        
        return prediction
    
    def _pattern_matches(self, pattern: LearningPattern, task_profile: Dict[str, Any], 
                        selected_agents: List[str]) -> bool:
        """Check if pattern matches current task and agents"""
        # Check domain context match
        task_domain = task_profile.get("domain", "unknown")
        if task_domain in pattern.contexts:
            return True
        
        # Check agent combination match
        pattern_agents = self._extract_agents_from_pattern(pattern)
        if pattern_agents and set(pattern_agents).intersection(set(selected_agents)):
            return True
        
        return False
    
    def _extract_agents_from_pattern(self, pattern: LearningPattern) -> List[str]:
        """Extract agent names from pattern description"""
        # Simple extraction - in practice would be more sophisticated
        known_agents = [
            "codebase-research-analyst", "backend-gateway-expert", "security-validator",
            "webui-architect", "performance-profiler", "nexus-synthesis-agent",
            "production-endpoint-validator", "user-experience-auditor"
        ]
        
        found_agents = []
        for agent in known_agents:
            if agent in pattern.pattern_description:
                found_agents.append(agent)
        
        return found_agents
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get comprehensive learning insights"""
        current_time = datetime.now()
        
        # Calculate learning metrics
        recent_outcomes = [
            o for o in self.orchestration_outcomes
            if (current_time - o.timestamp).days <= self.learning_window_days
        ]
        
        success_rate = sum(1 for o in recent_outcomes if o.success) / len(recent_outcomes) if recent_outcomes else 0.0
        avg_efficiency = sum(o.efficiency_score for o in recent_outcomes) / len(recent_outcomes) if recent_outcomes else 0.0
        
        # Pattern analysis
        pattern_distribution = Counter(p.pattern_type for p in self.identified_patterns.values())
        high_confidence_patterns = [
            p for p in self.identified_patterns.values() 
            if p.confidence_score > self.pattern_confidence_threshold
        ]
        
        return {
            "timestamp": current_time.isoformat(),
            "learning_window_days": self.learning_window_days,
            "outcomes_analyzed": len(recent_outcomes),
            "overall_success_rate": success_rate,
            "average_efficiency": avg_efficiency,
            "patterns_identified": len(self.identified_patterns),
            "pattern_distribution": dict(pattern_distribution),
            "high_confidence_patterns": len(high_confidence_patterns),
            "adaptive_strategies": len(self.adaptive_strategies),
            "learning_metrics": self.learning_metrics,
            "top_success_patterns": [
                {
                    "description": p.pattern_description,
                    "confidence": p.confidence_score,
                    "frequency": p.frequency
                }
                for p in sorted(
                    [p for p in self.identified_patterns.values() if p.pattern_type == "success"],
                    key=lambda x: x.confidence_score * x.frequency,
                    reverse=True
                )[:5]
            ],
            "critical_failure_patterns": [
                {
                    "description": p.pattern_description,
                    "confidence": p.confidence_score,
                    "frequency": p.frequency
                }
                for p in sorted(
                    [p for p in self.identified_patterns.values() if p.pattern_type == "failure"],
                    key=lambda x: x.confidence_score * x.frequency,
                    reverse=True
                )[:5]
            ]
        }
    
    def _save_learning_data(self):
        """Save learning data to persistent storage"""
        # Save orchestration outcomes
        outcomes_file = self.data_dir / "orchestration_outcomes.json"
        outcomes_data = []
        for outcome in self.orchestration_outcomes:
            outcome_dict = asdict(outcome)
            outcome_dict["timestamp"] = outcome.timestamp.isoformat()
            outcomes_data.append(outcome_dict)
        
        with open(outcomes_file, 'w') as f:
            json.dump(outcomes_data, f, indent=2)
        
        # Save learning patterns
        patterns_file = self.data_dir / "learning_patterns.json"
        patterns_data = {}
        for pattern_id, pattern in self.identified_patterns.items():
            pattern_dict = asdict(pattern)
            pattern_dict["created_at"] = pattern.created_at.isoformat()
            pattern_dict["last_validated"] = pattern.last_validated.isoformat()
            patterns_data[pattern_id] = pattern_dict
        
        with open(patterns_file, 'w') as f:
            json.dump(patterns_data, f, indent=2)
        
        # Save adaptive strategies
        strategies_file = self.data_dir / "adaptive_strategies.json"
        strategies_data = {}
        for strategy_id, strategy in self.adaptive_strategies.items():
            strategy_dict = asdict(strategy)
            strategy_dict["last_updated"] = strategy.last_updated.isoformat()
            strategies_data[strategy_id] = strategy_dict
        
        with open(strategies_file, 'w') as f:
            json.dump(strategies_data, f, indent=2)


def create_sample_outcome(orchestration_id: str, success: bool, agents: List[str], 
                         domain: str = "backend", efficiency: float = 0.8) -> OrchestrationOutcome:
    """Helper function to create sample orchestration outcomes"""
    return OrchestrationOutcome(
        orchestration_id=orchestration_id,
        timestamp=datetime.now(),
        task_profile={"domain": domain, "complexity": 0.7, "estimated_duration": 300},
        selected_agents=agents,
        success=success,
        completion_time=300 if success else 450,
        efficiency_score=efficiency,
        bottlenecks_encountered=[] if success else ["resource_contention"],
        resource_utilization={"cpu": 0.6, "memory": 0.4, "network": 0.3},
        coordination_challenges=[] if success else ["communication_overhead"],
        quality_metrics={"code_quality": 0.9, "test_coverage": 0.85},
        user_satisfaction=0.9 if success else 0.6,
        lessons_learned=["Effective agent coordination"] if success else ["Need better resource management"]
    )


if __name__ == "__main__":
    # Initialize learning engine
    learning_engine = ContinuousLearningEngine()
    
    # Simulate some orchestration outcomes
    sample_outcomes = [
        create_sample_outcome("orch_1", True, ["codebase-research-analyst", "backend-gateway-expert"], "backend", 0.9),
        create_sample_outcome("orch_2", True, ["security-validator", "performance-profiler"], "security", 0.85),
        create_sample_outcome("orch_3", False, ["webui-architect", "backend-gateway-expert"], "frontend", 0.4),
        create_sample_outcome("orch_4", True, ["codebase-research-analyst", "security-validator"], "research", 0.8),
        create_sample_outcome("orch_5", False, ["performance-profiler", "backend-gateway-expert"], "performance", 0.3)
    ]
    
    for outcome in sample_outcomes:
        learning_engine.record_orchestration_outcome(outcome)
    
    # Generate adaptive strategies
    strategies = learning_engine.generate_adaptive_strategies()
    print(f"Generated {len(strategies)} adaptive strategies")
    
    # Make a prediction
    test_profile = {"domain": "backend", "complexity": 0.8, "estimated_duration": 400}
    test_agents = ["codebase-research-analyst", "backend-gateway-expert"]
    prediction = learning_engine.predict_orchestration_outcome(test_profile, test_agents)
    
    print(f"Prediction for backend task with research and backend agents:")
    print(f"Success probability: {prediction['success_probability']:.2f}")
    print(f"Risk factors: {prediction['risk_factors']}")
    
    # Get learning insights
    insights = learning_engine.get_learning_insights()
    print(f"\nLearning Insights:")
    print(f"Success rate: {insights['overall_success_rate']:.2f}")
    print(f"Patterns identified: {insights['patterns_identified']}")
    print(f"Top success patterns: {len(insights['top_success_patterns'])}")
    
    logger.info("Continuous learning framework demonstration completed")