#!/usr/bin/env python3
"""
Pattern Recognition System for Success Factor Identification
Enhanced Nexus Synthesis Agent - Intelligence Integration Phase 5 Stream 3

Advanced pattern recognition system that identifies key success factors,
agent collaboration patterns, resource optimization patterns, and predictive indicators.
"""

import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations
import logging
import re
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SuccessFactor:
    """Identified success factor"""
    factor_id: str
    factor_type: str  # "agent_combination", "resource_allocation", "timing", "coordination", "domain_expertise"
    name: str
    description: str
    impact_score: float  # 0.0 to 1.0
    frequency: int
    confidence: float
    applicable_contexts: List[str]
    contributing_patterns: List[str]
    quantitative_evidence: Dict[str, float]
    recommendations: List[str]
    identified_at: datetime

@dataclass
class CollaborationPattern:
    """Agent collaboration pattern"""
    pattern_id: str
    agent_combination: List[str]
    collaboration_type: str  # "parallel", "sequential", "hierarchical", "peer"
    success_rate: float
    average_efficiency: float
    optimal_conditions: Dict[str, Any]
    common_bottlenecks: List[str]
    synergy_score: float
    usage_frequency: int
    domains: List[str]

@dataclass
class ResourcePattern:
    """Resource utilization pattern"""
    pattern_id: str
    resource_type: str
    optimal_allocation: Dict[str, float]
    efficiency_profile: List[Tuple[float, float]]  # (utilization, efficiency) pairs
    bottleneck_thresholds: Dict[str, float]
    performance_indicators: Dict[str, float]
    scaling_characteristics: Dict[str, Any]

class PatternRecognitionEngine:
    """
    Advanced Pattern Recognition System
    
    Features:
    - Success factor identification and ranking
    - Agent collaboration pattern analysis
    - Resource optimization pattern discovery
    - Predictive success indicator detection
    - Multi-dimensional pattern correlation
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("/home/marku/ai_workflow_engine/.claude/intelligence")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Pattern storage
        self.success_factors: Dict[str, SuccessFactor] = {}
        self.collaboration_patterns: Dict[str, CollaborationPattern] = {}
        self.resource_patterns: Dict[str, ResourcePattern] = {}
        
        # Analysis configuration
        self.min_sample_size = 5
        self.confidence_threshold = 0.7
        self.impact_threshold = 0.6
        self.correlation_threshold = 0.5
        
        # Pattern recognition models
        self.agent_affinity_matrix: Dict[Tuple[str, str], float] = {}
        self.domain_expertise_scores: Dict[Tuple[str, str], float] = {}
        self.resource_efficiency_curves: Dict[str, List[Tuple[float, float]]] = {}
        
        # Load existing patterns
        self._load_pattern_data()
        
    def _load_pattern_data(self):
        """Load existing pattern recognition data"""
        success_factors_file = self.data_dir / "success_factors.json"
        collaboration_file = self.data_dir / "collaboration_patterns.json"
        resource_patterns_file = self.data_dir / "resource_patterns.json"
        
        try:
            if success_factors_file.exists():
                with open(success_factors_file) as f:
                    data = json.load(f)
                    for factor_id, factor_data in data.items():
                        self.success_factors[factor_id] = SuccessFactor(
                            factor_id=factor_data["factor_id"],
                            factor_type=factor_data["factor_type"],
                            name=factor_data["name"],
                            description=factor_data["description"],
                            impact_score=factor_data["impact_score"],
                            frequency=factor_data["frequency"],
                            confidence=factor_data["confidence"],
                            applicable_contexts=factor_data["applicable_contexts"],
                            contributing_patterns=factor_data["contributing_patterns"],
                            quantitative_evidence=factor_data["quantitative_evidence"],
                            recommendations=factor_data["recommendations"],
                            identified_at=datetime.fromisoformat(factor_data["identified_at"])
                        )
                logger.info(f"Loaded {len(self.success_factors)} success factors")
            
            if collaboration_file.exists():
                with open(collaboration_file) as f:
                    data = json.load(f)
                    for pattern_id, pattern_data in data.items():
                        self.collaboration_patterns[pattern_id] = CollaborationPattern(**pattern_data)
                logger.info(f"Loaded {len(self.collaboration_patterns)} collaboration patterns")
                
            if resource_patterns_file.exists():
                with open(resource_patterns_file) as f:
                    data = json.load(f)
                    for pattern_id, pattern_data in data.items():
                        self.resource_patterns[pattern_id] = ResourcePattern(**pattern_data)
                logger.info(f"Loaded {len(self.resource_patterns)} resource patterns")
        
        except Exception as e:
            logger.error(f"Error loading pattern data: {e}")
    
    def analyze_orchestration_outcomes(self, outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Comprehensive analysis of orchestration outcomes to identify patterns
        
        Returns analysis results with identified patterns and success factors
        """
        if len(outcomes) < self.min_sample_size:
            logger.warning(f"Insufficient data for pattern analysis ({len(outcomes)} < {self.min_sample_size})")
            return {"error": "Insufficient data", "outcomes_analyzed": len(outcomes)}
        
        analysis_results = {
            "outcomes_analyzed": len(outcomes),
            "analysis_timestamp": datetime.now().isoformat(),
            "success_factors_identified": 0,
            "collaboration_patterns_identified": 0,
            "resource_patterns_identified": 0,
            "key_insights": []
        }
        
        # Identify success factors
        success_factors = self._identify_success_factors(outcomes)
        analysis_results["success_factors_identified"] = len(success_factors)
        
        # Analyze collaboration patterns
        collaboration_patterns = self._analyze_collaboration_patterns(outcomes)
        analysis_results["collaboration_patterns_identified"] = len(collaboration_patterns)
        
        # Analyze resource patterns
        resource_patterns = self._analyze_resource_patterns(outcomes)
        analysis_results["resource_patterns_identified"] = len(resource_patterns)
        
        # Generate key insights
        key_insights = self._generate_key_insights(outcomes, success_factors, collaboration_patterns, resource_patterns)
        analysis_results["key_insights"] = key_insights
        
        # Update pattern storage
        self._update_pattern_storage(success_factors, collaboration_patterns, resource_patterns)
        
        # Save updated patterns
        self._save_pattern_data()
        
        logger.info(f"Pattern analysis completed: {len(success_factors)} success factors, "
                   f"{len(collaboration_patterns)} collaboration patterns, "
                   f"{len(resource_patterns)} resource patterns")
        
        return analysis_results
    
    def _identify_success_factors(self, outcomes: List[Dict[str, Any]]) -> List[SuccessFactor]:
        """Identify key success factors from orchestration outcomes"""
        success_factors = []
        
        # Separate successful and failed outcomes
        successful_outcomes = [o for o in outcomes if o.get("success", False) and o.get("efficiency_score", 0) > 0.7]
        failed_outcomes = [o for o in outcomes if not o.get("success", False) or o.get("efficiency_score", 0) < 0.5]
        
        if len(successful_outcomes) < 3:
            return success_factors
        
        # Factor 1: Agent combination success factors
        agent_combo_success_factors = self._analyze_agent_combination_success_factors(successful_outcomes, failed_outcomes)
        success_factors.extend(agent_combo_success_factors)
        
        # Factor 2: Resource allocation success factors
        resource_success_factors = self._analyze_resource_allocation_success_factors(successful_outcomes, failed_outcomes)
        success_factors.extend(resource_success_factors)
        
        # Factor 3: Timing and coordination success factors
        timing_success_factors = self._analyze_timing_coordination_success_factors(successful_outcomes, failed_outcomes)
        success_factors.extend(timing_success_factors)
        
        # Factor 4: Domain expertise success factors
        domain_success_factors = self._analyze_domain_expertise_success_factors(successful_outcomes, failed_outcomes)
        success_factors.extend(domain_success_factors)
        
        # Factor 5: Task complexity handling success factors
        complexity_success_factors = self._analyze_complexity_handling_success_factors(successful_outcomes, failed_outcomes)
        success_factors.extend(complexity_success_factors)
        
        return success_factors
    
    def _analyze_agent_combination_success_factors(self, successful_outcomes: List[Dict], 
                                                  failed_outcomes: List[Dict]) -> List[SuccessFactor]:
        """Analyze agent combination success factors"""
        success_factors = []
        
        # Count agent combinations in successful vs failed outcomes
        successful_combos = defaultdict(int)
        failed_combos = defaultdict(int)
        
        for outcome in successful_outcomes:
            agents = tuple(sorted(outcome.get("selected_agents", [])))
            successful_combos[agents] += 1
            
        for outcome in failed_outcomes:
            agents = tuple(sorted(outcome.get("selected_agents", [])))
            failed_combos[agents] += 1
        
        # Identify highly successful combinations
        for combo, success_count in successful_combos.items():
            if success_count >= 3:  # Minimum frequency
                fail_count = failed_combos.get(combo, 0)
                success_rate = success_count / (success_count + fail_count)
                
                if success_rate > 0.8:  # High success rate
                    factor_id = f"agent_combo_success_{'_'.join(combo)}"[:50]
                    
                    success_factors.append(SuccessFactor(
                        factor_id=factor_id,
                        factor_type="agent_combination",
                        name=f"High-performing agent combination",
                        description=f"Agent combination {', '.join(combo)} shows {success_rate:.1%} success rate",
                        impact_score=min(1.0, success_rate * (success_count / 10)),
                        frequency=success_count,
                        confidence=min(1.0, success_count / 5),
                        applicable_contexts=self._get_contexts_for_combo(combo, successful_outcomes),
                        contributing_patterns=[f"agent_synergy_{combo[0]}_{combo[1]}" for combo in combinations(combo, 2)],
                        quantitative_evidence={"success_rate": success_rate, "sample_size": success_count + fail_count},
                        recommendations=[f"Prioritize agent combination {', '.join(combo)} for similar tasks"],
                        identified_at=datetime.now()
                    ))
        
        return success_factors
    
    def _analyze_resource_allocation_success_factors(self, successful_outcomes: List[Dict], 
                                                    failed_outcomes: List[Dict]) -> List[SuccessFactor]:
        """Analyze resource allocation success factors"""
        success_factors = []
        
        # Analyze resource utilization patterns
        resource_types = ["cpu", "memory", "network", "io"]
        
        for resource_type in resource_types:
            successful_utilization = []
            failed_utilization = []
            
            for outcome in successful_outcomes:
                util = outcome.get("resource_utilization", {}).get(resource_type)
                if util is not None:
                    successful_utilization.append(util)
            
            for outcome in failed_outcomes:
                util = outcome.get("resource_utilization", {}).get(resource_type)
                if util is not None:
                    failed_utilization.append(util)
            
            if len(successful_utilization) >= 3 and len(failed_utilization) >= 2:
                success_avg = statistics.mean(successful_utilization)
                success_std = statistics.stdev(successful_utilization) if len(successful_utilization) > 1 else 0
                fail_avg = statistics.mean(failed_utilization)
                
                # Check if there's a significant difference
                if abs(success_avg - fail_avg) > 0.2:
                    optimal_range = (max(0, success_avg - success_std), min(1, success_avg + success_std))
                    
                    factor_id = f"resource_allocation_{resource_type}_optimal"
                    success_factors.append(SuccessFactor(
                        factor_id=factor_id,
                        factor_type="resource_allocation",
                        name=f"Optimal {resource_type} utilization pattern",
                        description=f"Optimal {resource_type} utilization range: {optimal_range[0]:.2f}-{optimal_range[1]:.2f}",
                        impact_score=min(1.0, abs(success_avg - fail_avg)),
                        frequency=len(successful_utilization),
                        confidence=0.7,
                        applicable_contexts=["resource_intensive_tasks"],
                        contributing_patterns=[f"{resource_type}_efficiency_curve"],
                        quantitative_evidence={
                            "success_avg": success_avg,
                            "failure_avg": fail_avg,
                            "difference": abs(success_avg - fail_avg)
                        },
                        recommendations=[f"Maintain {resource_type} utilization within {optimal_range[0]:.2f}-{optimal_range[1]:.2f} range"],
                        identified_at=datetime.now()
                    ))
        
        return success_factors
    
    def _analyze_timing_coordination_success_factors(self, successful_outcomes: List[Dict], 
                                                    failed_outcomes: List[Dict]) -> List[SuccessFactor]:
        """Analyze timing and coordination success factors"""
        success_factors = []
        
        # Analyze completion time patterns
        successful_times = [o.get("completion_time", 0) for o in successful_outcomes]
        failed_times = [o.get("completion_time", 0) for o in failed_outcomes if o.get("completion_time", 0) > 0]
        
        if len(successful_times) >= 3 and len(failed_times) >= 2:
            success_avg_time = statistics.mean(successful_times)
            fail_avg_time = statistics.mean(failed_times)
            
            # Check for parallel execution advantages
            parallel_outcomes = [o for o in successful_outcomes if len(o.get("selected_agents", [])) > 2]
            sequential_outcomes = [o for o in successful_outcomes if len(o.get("selected_agents", [])) <= 2]
            
            if len(parallel_outcomes) >= 3 and len(sequential_outcomes) >= 3:
                parallel_avg_time = statistics.mean([o.get("completion_time", 0) for o in parallel_outcomes])
                sequential_avg_time = statistics.mean([o.get("completion_time", 0) for o in sequential_outcomes])
                
                if sequential_avg_time > parallel_avg_time * 1.2:  # 20% time savings
                    factor_id = "parallel_execution_advantage"
                    success_factors.append(SuccessFactor(
                        factor_id=factor_id,
                        factor_type="coordination",
                        name="Parallel execution time advantage",
                        description=f"Parallel execution saves {((sequential_avg_time - parallel_avg_time) / sequential_avg_time * 100):.1f}% time",
                        impact_score=0.8,
                        frequency=len(parallel_outcomes),
                        confidence=0.8,
                        applicable_contexts=["multi_agent_tasks"],
                        contributing_patterns=["parallel_coordination_pattern"],
                        quantitative_evidence={
                            "parallel_avg_time": parallel_avg_time,
                            "sequential_avg_time": sequential_avg_time,
                            "time_savings_percent": (sequential_avg_time - parallel_avg_time) / sequential_avg_time * 100
                        },
                        recommendations=["Prefer parallel execution for multi-agent tasks when possible"],
                        identified_at=datetime.now()
                    ))
        
        return success_factors
    
    def _analyze_domain_expertise_success_factors(self, successful_outcomes: List[Dict], 
                                                 failed_outcomes: List[Dict]) -> List[SuccessFactor]:
        """Analyze domain expertise success factors"""
        success_factors = []
        
        # Track agent performance in different domains
        domain_agent_performance = defaultdict(lambda: defaultdict(list))
        
        for outcome in successful_outcomes + failed_outcomes:
            domain = outcome.get("task_profile", {}).get("domain", "unknown")
            success = outcome.get("success", False)
            efficiency = outcome.get("efficiency_score", 0.5)
            
            for agent in outcome.get("selected_agents", []):
                domain_agent_performance[domain][agent].append((success, efficiency))
        
        # Identify agent-domain expertise patterns
        for domain, agent_performance in domain_agent_performance.items():
            for agent, performance_records in agent_performance.items():
                if len(performance_records) >= 3:
                    success_rate = sum(1 for success, _ in performance_records if success) / len(performance_records)
                    avg_efficiency = statistics.mean([eff for _, eff in performance_records])
                    
                    if success_rate > 0.8 and avg_efficiency > 0.7:
                        factor_id = f"domain_expertise_{domain}_{agent}"
                        success_factors.append(SuccessFactor(
                            factor_id=factor_id,
                            factor_type="domain_expertise",
                            name=f"{agent} domain expertise in {domain}",
                            description=f"{agent} shows {success_rate:.1%} success rate and {avg_efficiency:.2f} efficiency in {domain} domain",
                            impact_score=min(1.0, success_rate * avg_efficiency),
                            frequency=len(performance_records),
                            confidence=min(1.0, len(performance_records) / 5),
                            applicable_contexts=[domain],
                            contributing_patterns=[f"agent_specialization_{agent}"],
                            quantitative_evidence={
                                "success_rate": success_rate,
                                "avg_efficiency": avg_efficiency,
                                "sample_size": len(performance_records)
                            },
                            recommendations=[f"Prioritize {agent} for {domain} domain tasks"],
                            identified_at=datetime.now()
                        ))
        
        return success_factors
    
    def _analyze_complexity_handling_success_factors(self, successful_outcomes: List[Dict], 
                                                    failed_outcomes: List[Dict]) -> List[SuccessFactor]:
        """Analyze task complexity handling success factors"""
        success_factors = []
        
        # Analyze performance vs complexity
        complexity_performance = []
        
        for outcome in successful_outcomes:
            complexity = outcome.get("task_profile", {}).get("complexity", 0.5)
            efficiency = outcome.get("efficiency_score", 0.5)
            agent_count = len(outcome.get("selected_agents", []))
            
            complexity_performance.append((complexity, efficiency, agent_count, True))
        
        for outcome in failed_outcomes:
            complexity = outcome.get("task_profile", {}).get("complexity", 0.5)
            efficiency = outcome.get("efficiency_score", 0.5)
            agent_count = len(outcome.get("selected_agents", []))
            
            complexity_performance.append((complexity, efficiency, agent_count, False))
        
        # Find patterns in complexity handling
        high_complexity_outcomes = [(c, e, a, s) for c, e, a, s in complexity_performance if c > 0.7]
        
        if len(high_complexity_outcomes) >= 5:
            successful_high_complexity = [(c, e, a) for c, e, a, s in high_complexity_outcomes if s]
            
            if len(successful_high_complexity) >= 3:
                avg_agents = statistics.mean([a for _, _, a in successful_high_complexity])
                avg_efficiency = statistics.mean([e for _, e, _ in successful_high_complexity])
                
                if avg_efficiency > 0.7:
                    factor_id = "high_complexity_handling"
                    success_factors.append(SuccessFactor(
                        factor_id=factor_id,
                        factor_type="coordination",
                        name="High complexity task handling pattern",
                        description=f"High complexity tasks (>0.7) succeed with {avg_agents:.1f} agents and {avg_efficiency:.2f} efficiency",
                        impact_score=0.8,
                        frequency=len(successful_high_complexity),
                        confidence=0.7,
                        applicable_contexts=["high_complexity_tasks"],
                        contributing_patterns=["complexity_scaling_pattern"],
                        quantitative_evidence={
                            "avg_agents_for_high_complexity": avg_agents,
                            "avg_efficiency_high_complexity": avg_efficiency,
                            "high_complexity_threshold": 0.7
                        },
                        recommendations=[f"Use approximately {avg_agents:.0f} agents for high complexity tasks"],
                        identified_at=datetime.now()
                    ))
        
        return success_factors
    
    def _analyze_collaboration_patterns(self, outcomes: List[Dict[str, Any]]) -> List[CollaborationPattern]:
        """Analyze agent collaboration patterns"""
        collaboration_patterns = []
        
        # Group outcomes by agent combinations
        agent_combo_outcomes = defaultdict(list)
        
        for outcome in outcomes:
            agents = tuple(sorted(outcome.get("selected_agents", [])))
            if len(agents) >= 2:  # Only analyze multi-agent collaborations
                agent_combo_outcomes[agents].append(outcome)
        
        # Analyze each collaboration pattern
        for agents, combo_outcomes in agent_combo_outcomes.items():
            if len(combo_outcomes) >= 3:  # Minimum sample size
                pattern = self._analyze_single_collaboration_pattern(agents, combo_outcomes)
                if pattern:
                    collaboration_patterns.append(pattern)
        
        return collaboration_patterns
    
    def _analyze_single_collaboration_pattern(self, agents: Tuple[str, ...], 
                                            outcomes: List[Dict]) -> Optional[CollaborationPattern]:
        """Analyze a single collaboration pattern"""
        if len(outcomes) < 3:
            return None
        
        # Calculate collaboration metrics
        successes = sum(1 for o in outcomes if o.get("success", False))
        success_rate = successes / len(outcomes)
        
        efficiency_scores = [o.get("efficiency_score", 0.5) for o in outcomes]
        avg_efficiency = statistics.mean(efficiency_scores)
        
        # Identify collaboration type
        collaboration_type = self._identify_collaboration_type(agents, outcomes)
        
        # Calculate synergy score (compare to individual agent performance)
        synergy_score = self._calculate_synergy_score(agents, outcomes)
        
        # Identify common bottlenecks
        all_bottlenecks = []
        for outcome in outcomes:
            all_bottlenecks.extend(outcome.get("bottlenecks_encountered", []))
        
        common_bottlenecks = [bottleneck for bottleneck, count in Counter(all_bottlenecks).items() if count >= 2]
        
        # Get domains where this collaboration is used
        domains = list(set(o.get("task_profile", {}).get("domain", "unknown") for o in outcomes))
        
        pattern_id = f"collaboration_{'_'.join(agents)}"[:50]
        
        return CollaborationPattern(
            pattern_id=pattern_id,
            agent_combination=list(agents),
            collaboration_type=collaboration_type,
            success_rate=success_rate,
            average_efficiency=avg_efficiency,
            optimal_conditions=self._identify_optimal_conditions(outcomes),
            common_bottlenecks=common_bottlenecks,
            synergy_score=synergy_score,
            usage_frequency=len(outcomes),
            domains=domains
        )
    
    def _analyze_resource_patterns(self, outcomes: List[Dict[str, Any]]) -> List[ResourcePattern]:
        """Analyze resource utilization patterns"""
        resource_patterns = []
        
        resource_types = ["cpu_intensive", "memory_intensive", "network_intensive", "io_intensive"]
        
        for resource_type in resource_types:
            pattern = self._analyze_single_resource_pattern(resource_type, outcomes)
            if pattern:
                resource_patterns.append(pattern)
        
        return resource_patterns
    
    def _analyze_single_resource_pattern(self, resource_type: str, 
                                       outcomes: List[Dict]) -> Optional[ResourcePattern]:
        """Analyze a single resource type pattern"""
        # Filter outcomes that used this resource type
        resource_outcomes = []
        for outcome in outcomes:
            resource_usage = outcome.get("resource_utilization", {})
            if resource_type.split("_")[0] in resource_usage:  # e.g., "cpu" in resource_usage
                resource_outcomes.append(outcome)
        
        if len(resource_outcomes) < 5:
            return None
        
        # Analyze utilization vs efficiency relationship
        utilization_efficiency_pairs = []
        for outcome in resource_outcomes:
            utilization = outcome.get("resource_utilization", {}).get(resource_type.split("_")[0], 0)
            efficiency = outcome.get("efficiency_score", 0.5)
            utilization_efficiency_pairs.append((utilization, efficiency))
        
        # Calculate optimal allocation
        high_efficiency_outcomes = [o for o in resource_outcomes if o.get("efficiency_score", 0) > 0.7]
        if high_efficiency_outcomes:
            optimal_allocation = {}
            for outcome in high_efficiency_outcomes:
                for agent in outcome.get("selected_agents", []):
                    if agent not in optimal_allocation:
                        optimal_allocation[agent] = []
                    optimal_allocation[agent].append(outcome.get("resource_utilization", {}).get(resource_type.split("_")[0], 0))
            
            # Average optimal allocation per agent
            for agent in optimal_allocation:
                optimal_allocation[agent] = statistics.mean(optimal_allocation[agent])
        else:
            optimal_allocation = {}
        
        # Identify bottleneck thresholds
        bottleneck_thresholds = self._identify_bottleneck_thresholds(resource_type, resource_outcomes)
        
        pattern_id = f"resource_pattern_{resource_type}"
        
        return ResourcePattern(
            pattern_id=pattern_id,
            resource_type=resource_type,
            optimal_allocation=optimal_allocation,
            efficiency_profile=utilization_efficiency_pairs,
            bottleneck_thresholds=bottleneck_thresholds,
            performance_indicators=self._calculate_resource_performance_indicators(resource_outcomes),
            scaling_characteristics={"linear_scaling": True, "bottleneck_point": 0.9}  # Simplified
        )
    
    def _get_contexts_for_combo(self, combo: Tuple[str, ...], outcomes: List[Dict]) -> List[str]:
        """Get contexts where agent combination was used"""
        contexts = set()
        for outcome in outcomes:
            agents = tuple(sorted(outcome.get("selected_agents", [])))
            if agents == combo:
                domain = outcome.get("task_profile", {}).get("domain", "unknown")
                contexts.add(domain)
        return list(contexts)
    
    def _identify_collaboration_type(self, agents: Tuple[str, ...], outcomes: List[Dict]) -> str:
        """Identify the type of collaboration between agents"""
        if len(agents) == 2:
            return "peer"
        elif len(agents) > 2:
            # Check if there's a lead agent pattern
            agent_roles = self._analyze_agent_roles(agents, outcomes)
            if any(role == "lead" for role in agent_roles.values()):
                return "hierarchical"
            else:
                return "parallel"
        return "unknown"
    
    def _calculate_synergy_score(self, agents: Tuple[str, ...], outcomes: List[Dict]) -> float:
        """Calculate synergy score for agent collaboration"""
        # Simplified synergy calculation
        avg_efficiency = statistics.mean([o.get("efficiency_score", 0.5) for o in outcomes])
        expected_individual_efficiency = 0.6  # Baseline individual efficiency
        
        synergy_score = avg_efficiency / expected_individual_efficiency
        return min(2.0, max(0.0, synergy_score))  # Cap between 0 and 2
    
    def _identify_optimal_conditions(self, outcomes: List[Dict]) -> Dict[str, Any]:
        """Identify optimal conditions for collaboration"""
        successful_outcomes = [o for o in outcomes if o.get("success", False) and o.get("efficiency_score", 0) > 0.7]
        
        if not successful_outcomes:
            return {}
        
        # Analyze optimal conditions
        conditions = {
            "avg_completion_time": statistics.mean([o.get("completion_time", 300) for o in successful_outcomes]),
            "optimal_complexity_range": self._get_complexity_range(successful_outcomes),
            "preferred_domains": self._get_most_common_domains(successful_outcomes)
        }
        
        return conditions
    
    def _identify_bottleneck_thresholds(self, resource_type: str, outcomes: List[Dict]) -> Dict[str, float]:
        """Identify resource bottleneck thresholds"""
        bottlenecked_outcomes = [o for o in outcomes if resource_type.replace("_", " ") in " ".join(o.get("bottlenecks_encountered", []))]
        
        if bottlenecked_outcomes:
            bottleneck_utilizations = [
                o.get("resource_utilization", {}).get(resource_type.split("_")[0], 0)
                for o in bottlenecked_outcomes
            ]
            
            if bottleneck_utilizations:
                return {
                    "warning_threshold": statistics.mean(bottleneck_utilizations) - 0.1,
                    "critical_threshold": statistics.mean(bottleneck_utilizations)
                }
        
        return {"warning_threshold": 0.8, "critical_threshold": 0.9}  # Default thresholds
    
    def _calculate_resource_performance_indicators(self, outcomes: List[Dict]) -> Dict[str, float]:
        """Calculate resource performance indicators"""
        return {
            "average_efficiency": statistics.mean([o.get("efficiency_score", 0.5) for o in outcomes]),
            "success_rate": sum(1 for o in outcomes if o.get("success", False)) / len(outcomes),
            "completion_time_variance": statistics.variance([o.get("completion_time", 300) for o in outcomes]) if len(outcomes) > 1 else 0
        }
    
    def _analyze_agent_roles(self, agents: Tuple[str, ...], outcomes: List[Dict]) -> Dict[str, str]:
        """Analyze roles of agents in collaboration"""
        # Simplified role analysis - would be more sophisticated in practice
        roles = {}
        for agent in agents:
            if "orchestrator" in agent or "coordinator" in agent:
                roles[agent] = "lead"
            elif "analyst" in agent or "research" in agent:
                roles[agent] = "research"
            elif "validator" in agent or "auditor" in agent:
                roles[agent] = "validation"
            else:
                roles[agent] = "implementation"
        return roles
    
    def _get_complexity_range(self, outcomes: List[Dict]) -> Tuple[float, float]:
        """Get complexity range for successful outcomes"""
        complexities = [o.get("task_profile", {}).get("complexity", 0.5) for o in outcomes]
        if complexities:
            return (min(complexities), max(complexities))
        return (0.0, 1.0)
    
    def _get_most_common_domains(self, outcomes: List[Dict]) -> List[str]:
        """Get most common domains in successful outcomes"""
        domains = [o.get("task_profile", {}).get("domain", "unknown") for o in outcomes]
        domain_counts = Counter(domains)
        return [domain for domain, count in domain_counts.most_common(3)]
    
    def _generate_key_insights(self, outcomes: List[Dict], success_factors: List[SuccessFactor],
                              collaboration_patterns: List[CollaborationPattern],
                              resource_patterns: List[ResourcePattern]) -> List[str]:
        """Generate key insights from pattern analysis"""
        insights = []
        
        # Top success factors
        top_success_factors = sorted(success_factors, key=lambda x: x.impact_score * x.confidence, reverse=True)[:3]
        for factor in top_success_factors:
            insights.append(f"Key success factor: {factor.name} (impact: {factor.impact_score:.2f})")
        
        # Best collaboration patterns
        best_collaborations = sorted(collaboration_patterns, key=lambda x: x.success_rate * x.average_efficiency, reverse=True)[:2]
        for pattern in best_collaborations:
            insights.append(f"High-performing collaboration: {', '.join(pattern.agent_combination)} "
                           f"({pattern.success_rate:.1%} success, {pattern.average_efficiency:.2f} efficiency)")
        
        # Resource optimization opportunities
        for pattern in resource_patterns:
            if pattern.performance_indicators.get("average_efficiency", 0) > 0.8:
                insights.append(f"Optimal {pattern.resource_type} utilization identified with {pattern.performance_indicators['average_efficiency']:.2f} efficiency")
        
        # Overall patterns
        total_success_rate = sum(1 for o in outcomes if o.get("success", False)) / len(outcomes)
        insights.append(f"Overall orchestration success rate: {total_success_rate:.1%}")
        
        return insights
    
    def _update_pattern_storage(self, success_factors: List[SuccessFactor],
                               collaboration_patterns: List[CollaborationPattern],
                               resource_patterns: List[ResourcePattern]):
        """Update pattern storage with new findings"""
        # Update success factors
        for factor in success_factors:
            self.success_factors[factor.factor_id] = factor
        
        # Update collaboration patterns
        for pattern in collaboration_patterns:
            self.collaboration_patterns[pattern.pattern_id] = pattern
        
        # Update resource patterns
        for pattern in resource_patterns:
            self.resource_patterns[pattern.pattern_id] = pattern
    
    def _save_pattern_data(self):
        """Save pattern data to persistent storage"""
        # Save success factors
        success_factors_file = self.data_dir / "success_factors.json"
        success_factors_data = {}
        for factor_id, factor in self.success_factors.items():
            factor_dict = asdict(factor)
            factor_dict["identified_at"] = factor.identified_at.isoformat()
            success_factors_data[factor_id] = factor_dict
        
        with open(success_factors_file, 'w') as f:
            json.dump(success_factors_data, f, indent=2)
        
        # Save collaboration patterns
        collaboration_file = self.data_dir / "collaboration_patterns.json"
        with open(collaboration_file, 'w') as f:
            json.dump({pid: asdict(pattern) for pid, pattern in self.collaboration_patterns.items()}, f, indent=2)
        
        # Save resource patterns
        resource_patterns_file = self.data_dir / "resource_patterns.json"
        with open(resource_patterns_file, 'w') as f:
            json.dump({pid: asdict(pattern) for pid, pattern in self.resource_patterns.items()}, f, indent=2)
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get comprehensive pattern recognition summary"""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_success_factors": len(self.success_factors),
            "total_collaboration_patterns": len(self.collaboration_patterns),
            "total_resource_patterns": len(self.resource_patterns),
            "top_success_factors": [
                {
                    "name": factor.name,
                    "impact_score": factor.impact_score,
                    "confidence": factor.confidence,
                    "type": factor.factor_type
                }
                for factor in sorted(self.success_factors.values(), 
                                   key=lambda x: x.impact_score * x.confidence, reverse=True)[:5]
            ],
            "best_collaborations": [
                {
                    "agents": pattern.agent_combination,
                    "success_rate": pattern.success_rate,
                    "efficiency": pattern.average_efficiency,
                    "domains": pattern.domains
                }
                for pattern in sorted(self.collaboration_patterns.values(),
                                    key=lambda x: x.success_rate * x.average_efficiency, reverse=True)[:3]
            ],
            "resource_insights": [
                {
                    "resource_type": pattern.resource_type,
                    "efficiency": pattern.performance_indicators.get("average_efficiency", 0),
                    "bottleneck_threshold": pattern.bottleneck_thresholds.get("critical_threshold", 0.9)
                }
                for pattern in self.resource_patterns.values()
            ]
        }


def create_sample_outcomes_for_testing() -> List[Dict[str, Any]]:
    """Create sample outcomes for testing pattern recognition"""
    return [
        {
            "orchestration_id": "test_1",
            "success": True,
            "efficiency_score": 0.9,
            "selected_agents": ["codebase-research-analyst", "backend-gateway-expert"],
            "completion_time": 280,
            "task_profile": {"domain": "backend", "complexity": 0.7},
            "resource_utilization": {"cpu": 0.6, "memory": 0.4},
            "bottlenecks_encountered": []
        },
        {
            "orchestration_id": "test_2", 
            "success": True,
            "efficiency_score": 0.85,
            "selected_agents": ["security-validator", "performance-profiler"],
            "completion_time": 320,
            "task_profile": {"domain": "security", "complexity": 0.8},
            "resource_utilization": {"cpu": 0.7, "network": 0.6},
            "bottlenecks_encountered": []
        },
        {
            "orchestration_id": "test_3",
            "success": False,
            "efficiency_score": 0.4,
            "selected_agents": ["webui-architect", "backend-gateway-expert", "performance-profiler"],
            "completion_time": 520,
            "task_profile": {"domain": "frontend", "complexity": 0.9},
            "resource_utilization": {"cpu": 0.95, "memory": 0.8, "io": 0.7},
            "bottlenecks_encountered": ["resource contention", "communication overhead"]
        },
        # Add more test data...
    ]


if __name__ == "__main__":
    # Initialize pattern recognition engine
    pattern_engine = PatternRecognitionEngine()
    
    # Create sample data
    sample_outcomes = create_sample_outcomes_for_testing()
    
    # Add more realistic sample data
    additional_outcomes = []
    for i in range(10):
        additional_outcomes.append({
            "orchestration_id": f"test_{i+4}",
            "success": i % 3 != 0,  # 67% success rate
            "efficiency_score": 0.6 + (i % 4) * 0.1,
            "selected_agents": [
                ["codebase-research-analyst", "backend-gateway-expert"],
                ["security-validator", "performance-profiler"],
                ["webui-architect", "frictionless-ux-architect"],
                ["nexus-synthesis-agent"]
            ][i % 4],
            "completion_time": 250 + i * 20,
            "task_profile": {
                "domain": ["backend", "security", "frontend", "research"][i % 4],
                "complexity": 0.5 + (i % 3) * 0.2
            },
            "resource_utilization": {
                "cpu": 0.4 + (i % 5) * 0.1,
                "memory": 0.3 + (i % 4) * 0.1,
                "network": 0.2 + (i % 3) * 0.1
            },
            "bottlenecks_encountered": [] if i % 3 != 0 else ["resource contention"]
        })
    
    all_outcomes = sample_outcomes + additional_outcomes
    
    # Analyze patterns
    results = pattern_engine.analyze_orchestration_outcomes(all_outcomes)
    
    print(f"Pattern Analysis Results:")
    print(f"- Success factors identified: {results['success_factors_identified']}")
    print(f"- Collaboration patterns identified: {results['collaboration_patterns_identified']}")
    print(f"- Resource patterns identified: {results['resource_patterns_identified']}")
    
    print(f"\nKey Insights:")
    for insight in results['key_insights']:
        print(f"- {insight}")
    
    # Get pattern summary
    summary = pattern_engine.get_pattern_summary()
    print(f"\nTop Success Factors:")
    for factor in summary['top_success_factors']:
        print(f"- {factor['name']} (impact: {factor['impact_score']:.2f})")
    
    logger.info("Pattern recognition system demonstration completed")