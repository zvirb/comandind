#!/usr/bin/env python3
"""
Knowledge Graph Research Integration System
Integrates historical success/failure patterns into research and planning phases
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from .knowledge-graph-v2 import EnhancedKnowledgeGraph, PatternType, FailureCategory

@dataclass
class ResearchGuidance:
    """Guidance for research phase based on historical patterns"""
    priority_areas: List[str]
    risk_indicators: List[str] 
    validated_approaches: List[str]
    common_pitfalls: List[str]
    evidence_requirements: List[str]
    agent_recommendations: List[str]

@dataclass 
class PlanningRecommendations:
    """Strategic recommendations for planning phase"""
    proven_sequences: List[str]
    parallel_opportunities: List[str]
    validation_checkpoints: List[str]
    rollback_triggers: List[str]
    agent_coordination_patterns: Dict[str, Any]
    risk_mitigation_steps: List[str]

class KnowledgeGraphResearchIntegration:
    """Integrates knowledge graph patterns into research and planning phases"""
    
    def __init__(self, kg_path: str = "/home/marku/ai_workflow_engine/.claude/knowledge"):
        self.kg = EnhancedKnowledgeGraph(kg_path)
        
    def analyze_task_for_patterns(self, 
                                 task_description: str,
                                 symptoms: List[str] = None,
                                 domain: str = None) -> Tuple[ResearchGuidance, PlanningRecommendations]:
        """Analyze incoming task against historical patterns to guide research and planning"""
        
        # Extract key patterns from task description
        task_patterns = self._extract_task_patterns(task_description)
        
        # Query knowledge graph for similar past scenarios
        similar_failures = self.kg.query_failure_patterns(
            symptoms=symptoms or task_patterns.get("potential_symptoms", []),
            environment="production"
        )
        
        similar_successes = self.kg.query_success_patterns(
            pattern_type=task_patterns.get("primary_type")
        )
        
        # Generate research guidance
        research_guidance = self._generate_research_guidance(
            task_patterns, similar_failures, similar_successes
        )
        
        # Generate planning recommendations  
        planning_recommendations = self._generate_planning_recommendations(
            task_patterns, similar_failures, similar_successes
        )
        
        return research_guidance, planning_recommendations
    
    def _extract_task_patterns(self, task_description: str) -> Dict[str, Any]:
        """Extract pattern indicators from task description"""
        patterns = {
            "primary_type": None,
            "potential_symptoms": [],
            "technology_areas": [],
            "complexity_indicators": []
        }
        
        # Pattern detection based on keywords
        task_lower = task_description.lower()
        
        # Identify primary pattern type
        if any(word in task_lower for word in ["auth", "login", "token", "csrf", "jwt"]):
            patterns["primary_type"] = "authentication_csrf_fix"
            patterns["potential_symptoms"] = [
                "403 CSRF token validation failed",
                "authentication failure", 
                "token validation error"
            ]
            
        elif any(word in task_lower for word in ["websocket", "ws", "connection", "real-time"]):
            patterns["primary_type"] = "websocket_connectivity"
            patterns["potential_symptoms"] = [
                "WebSocket connection failed",
                "connection closed before establishment",
                "real-time functionality broken"
            ]
            
        elif any(word in task_lower for word in ["api", "endpoint", "500", "backend"]):
            patterns["primary_type"] = "api_endpoint_failure"
            patterns["potential_symptoms"] = [
                "API endpoint returns 500",
                "backend service unavailable",
                "request timeout"
            ]
            
        elif any(word in task_lower for word in ["frontend", "ui", "css", "image", "404"]):
            patterns["primary_type"] = "ui_functionality_failure"
            patterns["potential_symptoms"] = [
                "404 resource not found",
                "CSS preload warning",
                "missing static assets"
            ]
        
        # Extract technology areas
        tech_keywords = {
            "authentication": ["auth", "login", "token", "csrf", "jwt"],
            "websocket": ["websocket", "ws", "real-time", "connection"],
            "frontend": ["css", "javascript", "svelte", "ui", "browser"],
            "backend": ["api", "server", "python", "fastapi"],
            "database": ["db", "schema", "migration", "postgres"],
            "infrastructure": ["docker", "ssl", "nginx", "deployment"]
        }
        
        for area, keywords in tech_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                patterns["technology_areas"].append(area)
        
        return patterns
    
    def _generate_research_guidance(self, 
                                   task_patterns: Dict[str, Any],
                                   similar_failures: List,
                                   similar_successes: List) -> ResearchGuidance:
        """Generate research guidance based on historical patterns"""
        
        priority_areas = []
        risk_indicators = []
        validated_approaches = []
        common_pitfalls = []
        evidence_requirements = []
        agent_recommendations = []
        
        # Analyze failure patterns for research priorities
        for failure in similar_failures[:3]:  # Top 3 most relevant failures
            # High-priority research areas based on root causes
            priority_areas.extend(failure.root_causes)
            
            # Risk indicators to watch for
            risk_indicators.extend(failure.false_positive_indicators)
            
            # Common pitfalls to investigate
            common_pitfalls.extend([
                f"Avoid: {symptom}" for symptom in failure.symptoms
            ])
            
            # Evidence requirements based on past false positives
            evidence_requirements.extend([
                f"Verify: {impact}" for impact in failure.actual_user_impact
            ])
        
        # Analyze success patterns for validated approaches
        for success in similar_successes[:2]:  # Top 2 most successful patterns
            validated_approaches.extend(success.implementation_steps)
            agent_recommendations.extend(success.cross_validation_agents)
            evidence_requirements.extend(success.validation_evidence)
        
        # Add technology-specific research priorities
        for tech_area in task_patterns.get("technology_areas", []):
            if tech_area == "authentication":
                priority_areas.extend([
                    "Token validation flow analysis",
                    "CSRF middleware configuration",
                    "Session management implementation"
                ])
            elif tech_area == "websocket":
                priority_areas.extend([
                    "WebSocket connection lifecycle",
                    "Session ID management",
                    "Authentication token handling in WebSocket"
                ])
            elif tech_area == "frontend":
                priority_areas.extend([
                    "Static asset serving configuration",
                    "CSS build process analysis",
                    "Browser caching behavior"
                ])
        
        return ResearchGuidance(
            priority_areas=list(set(priority_areas))[:8],  # Limit to top 8 areas
            risk_indicators=list(set(risk_indicators))[:6],
            validated_approaches=list(set(validated_approaches))[:5],
            common_pitfalls=list(set(common_pitfalls))[:5],
            evidence_requirements=list(set(evidence_requirements))[:6],
            agent_recommendations=list(set(agent_recommendations))
        )
    
    def _generate_planning_recommendations(self,
                                         task_patterns: Dict[str, Any],
                                         similar_failures: List,
                                         similar_successes: List) -> PlanningRecommendations:
        """Generate planning recommendations based on historical patterns"""
        
        proven_sequences = []
        parallel_opportunities = []
        validation_checkpoints = []
        rollback_triggers = []
        agent_coordination_patterns = {}
        risk_mitigation_steps = []
        
        # Extract proven sequences from successful patterns
        for success in similar_successes:
            if success.implementation_steps:
                proven_sequences.append(" → ".join(success.implementation_steps[:3]))
            
            # Agent coordination patterns
            if success.cross_validation_agents:
                agent_coordination_patterns[success.pattern_type] = {
                    "primary_agents": success.cross_validation_agents,
                    "validation_evidence": success.validation_evidence,
                    "success_rate": success.reproduction_success_rate
                }
        
        # Extract risk mitigation from failure patterns
        for failure in similar_failures:
            # Validation checkpoints to prevent similar failures
            for cause in failure.root_causes:
                validation_checkpoints.append(f"Checkpoint: Validate {cause}")
            
            # Rollback triggers based on early warning signs
            for symptom in failure.symptoms[:2]:  # Top 2 symptoms
                rollback_triggers.append(f"Rollback if: {symptom} detected")
            
            # Risk mitigation steps
            risk_mitigation_steps.extend([
                f"Monitor for: {indicator}" 
                for indicator in failure.false_positive_indicators
            ])
        
        # Technology-specific planning recommendations
        primary_type = task_patterns.get("primary_type")
        if primary_type == "authentication_csrf_fix":
            proven_sequences.append("CSRF middleware analysis → Token validation testing → End-to-end auth flow")
            parallel_opportunities.extend([
                "Backend token validation + Frontend token handling can run parallel",
                "CSRF middleware config + JWT format validation parallel"
            ])
            validation_checkpoints.extend([
                "Verify actual user login success (not just 200 response)",
                "Cross-validate token format between frontend and backend"
            ])
            
        elif primary_type == "websocket_connectivity":
            proven_sequences.append("Session ID management → WebSocket auth → Connection lifecycle")
            validation_checkpoints.extend([
                "Verify session ID is not null/undefined",
                "Test WebSocket connection with valid auth token",
                "Validate connection persistence across page refreshes"
            ])
            
        elif primary_type == "ui_functionality_failure":
            parallel_opportunities.extend([
                "Static asset creation + Build configuration updates parallel",
                "CSS optimization + Image asset preparation parallel"
            ])
            validation_checkpoints.extend([
                "Verify all static assets are accessible via HTTP",
                "Test build process produces expected output files"
            ])
        
        return PlanningRecommendations(
            proven_sequences=list(set(proven_sequences)),
            parallel_opportunities=list(set(parallel_opportunities)),
            validation_checkpoints=list(set(validation_checkpoints)),
            rollback_triggers=list(set(rollback_triggers)),
            agent_coordination_patterns=agent_coordination_patterns,
            risk_mitigation_steps=list(set(risk_mitigation_steps))
        )
    
    def generate_research_brief(self, 
                               task_description: str,
                               symptoms: List[str] = None) -> Dict[str, Any]:
        """Generate comprehensive research brief with historical pattern insights"""
        
        research_guidance, planning_recommendations = self.analyze_task_for_patterns(
            task_description, symptoms
        )
        
        # Get overall orchestration recommendations
        orchestration_recommendations = self.kg.get_orchestration_recommendations(
            current_symptoms=symptoms or [],
            environment="production"
        )
        
        return {
            "task_analysis": {
                "description": task_description,
                "identified_symptoms": symptoms or [],
                "risk_level": self._assess_risk_level(orchestration_recommendations)
            },
            "research_guidance": {
                "priority_areas": research_guidance.priority_areas,
                "risk_indicators": research_guidance.risk_indicators,
                "validated_approaches": research_guidance.validated_approaches,
                "common_pitfalls": research_guidance.common_pitfalls,
                "evidence_requirements": research_guidance.evidence_requirements,
                "recommended_agents": research_guidance.agent_recommendations
            },
            "planning_recommendations": {
                "proven_sequences": planning_recommendations.proven_sequences,
                "parallel_opportunities": planning_recommendations.parallel_opportunities,
                "validation_checkpoints": planning_recommendations.validation_checkpoints,
                "rollback_triggers": planning_recommendations.rollback_triggers,
                "agent_coordination": planning_recommendations.agent_coordination_patterns,
                "risk_mitigation": planning_recommendations.risk_mitigation_steps
            },
            "historical_context": {
                "similar_past_failures": orchestration_recommendations["similar_past_failures"],
                "high_risk_patterns": orchestration_recommendations["high_risk_patterns"],
                "validation_requirements": orchestration_recommendations["validation_requirements"],
                "evidence_priority": orchestration_recommendations["evidence_collection_priority"]
            },
            "execution_strategy": {
                "recommended_approach": self._recommend_execution_approach(
                    research_guidance, planning_recommendations
                ),
                "success_probability": self._estimate_success_probability(
                    orchestration_recommendations
                ),
                "iteration_likelihood": self._estimate_iteration_likelihood(
                    orchestration_recommendations
                )
            }
        }
    
    def _assess_risk_level(self, orchestration_recommendations: Dict[str, Any]) -> str:
        """Assess risk level based on historical patterns"""
        high_risk_count = len(orchestration_recommendations.get("high_risk_patterns", []))
        similar_failures = orchestration_recommendations.get("similar_past_failures", 0)
        
        if high_risk_count >= 2 or similar_failures >= 3:
            return "HIGH"
        elif high_risk_count >= 1 or similar_failures >= 1:
            return "MEDIUM" 
        else:
            return "LOW"
    
    def _recommend_execution_approach(self, 
                                    research_guidance: ResearchGuidance,
                                    planning_recommendations: PlanningRecommendations) -> str:
        """Recommend execution approach based on patterns"""
        
        if len(planning_recommendations.proven_sequences) >= 2:
            return "SEQUENTIAL_WITH_VALIDATION"
        elif len(planning_recommendations.parallel_opportunities) >= 2:
            return "PARALLEL_WITH_CHECKPOINTS"
        elif len(research_guidance.risk_indicators) >= 3:
            return "INCREMENTAL_WITH_ROLLBACK"
        else:
            return "STANDARD_ORCHESTRATION"
    
    def _estimate_success_probability(self, orchestration_recommendations: Dict[str, Any]) -> float:
        """Estimate success probability based on historical patterns"""
        base_probability = 0.7
        
        # Reduce probability based on risk factors
        high_risk_patterns = len(orchestration_recommendations.get("high_risk_patterns", []))
        similar_failures = orchestration_recommendations.get("similar_past_failures", 0)
        
        risk_penalty = (high_risk_patterns * 0.15) + (similar_failures * 0.1)
        
        return max(0.2, base_probability - risk_penalty)
    
    def _estimate_iteration_likelihood(self, orchestration_recommendations: Dict[str, Any]) -> float:
        """Estimate likelihood of needing iterations"""
        base_likelihood = 0.3
        
        # Increase likelihood based on complexity indicators
        validation_requirements = len(orchestration_recommendations.get("validation_requirements", []))
        evidence_priority = len(orchestration_recommendations.get("evidence_collection_priority", []))
        
        complexity_factor = (validation_requirements * 0.1) + (evidence_priority * 0.05)
        
        return min(0.8, base_likelihood + complexity_factor)

# Usage example and testing
if __name__ == "__main__":
    kg_integration = KnowledgeGraphResearchIntegration()
    
    # Test with current WebSocket issue
    task_description = "Fix Helios WebSocket connection failures using 'null' session ID"
    symptoms = [
        "WebSocket connection failed", 
        "connection closed before establishment",
        "null session ID in connection URL"
    ]
    
    research_brief = kg_integration.generate_research_brief(task_description, symptoms)
    
    print("=== RESEARCH BRIEF WITH HISTORICAL PATTERNS ===")
    print(json.dumps(research_brief, indent=2))