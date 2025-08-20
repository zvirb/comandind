#!/usr/bin/env python3
"""
Enhanced Research Coordinator Agent
Bridges traditional codebase research with historical pattern analysis
to prevent critical production failures
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .knowledge_graph_research_integration import KnowledgeGraphResearchIntegration
from .critical_failure_pattern_integration import CriticalFailurePatternIntegration

@dataclass
class EnhancedResearchBrief:
    """Enhanced research brief with historical context and failure prevention"""
    task_analysis: Dict[str, Any]
    current_system_investigation: Dict[str, Any]
    historical_pattern_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    research_informed_recommendations: Dict[str, Any]
    success_probability_assessment: Dict[str, Any]
    
class EnhancedResearchCoordinator:
    """
    Enhanced Research Coordinator that combines current system investigation 
    with lessons learned from past successes and failures, specifically
    including critical production failure patterns
    """
    
    def __init__(self, kg_path: str = "/home/marku/ai_workflow_engine/.claude/knowledge"):
        self.kg_integration = KnowledgeGraphResearchIntegration(kg_path)
        self.critical_patterns = CriticalFailurePatternIntegration(kg_path)
        
        # Ensure critical patterns are integrated
        self._ensure_critical_patterns_loaded()
        
    def _ensure_critical_patterns_loaded(self) -> None:
        """Ensure critical failure patterns from cosmic hero incident are loaded"""
        try:
            # Check if critical patterns exist, if not, integrate them
            cosmic_hero_patterns = self.critical_patterns.kg.query_failure_patterns(
                symptoms=["WebSocket connection failed", "null session ID"],
                environment="production"
            )
            
            if not cosmic_hero_patterns or len(cosmic_hero_patterns) < 3:
                # Integrate critical patterns
                integration_result = self.critical_patterns.integrate_cosmic_hero_incident()
                print(f"Integrated {integration_result['patterns_stored']['failure_patterns']} critical failure patterns")
                
        except Exception as e:
            print(f"Warning: Could not ensure critical patterns loaded: {e}")
    
    def conduct_enhanced_research(self, 
                                 user_request: str,
                                 identified_symptoms: List[str] = None) -> EnhancedResearchBrief:
        """
        Conduct enhanced research combining traditional investigation
        with historical pattern analysis and failure prevention
        """
        
        # Phase 1: Historical Context Analysis
        research_brief = self.kg_integration.generate_research_brief(
            task_description=user_request,
            symptoms=identified_symptoms or []
        )
        
        # Phase 2: Critical Pattern Analysis
        critical_risk_analysis = self._analyze_critical_failure_risks(
            user_request, identified_symptoms or []
        )
        
        # Phase 3: Enhanced Risk Assessment
        enhanced_risk_assessment = self._conduct_enhanced_risk_assessment(
            research_brief, critical_risk_analysis
        )
        
        # Phase 4: Research Strategy Adaptation
        adapted_strategy = self._adapt_research_strategy(
            research_brief, critical_risk_analysis
        )
        
        # Phase 5: Evidence Quality Requirements
        evidence_requirements = self._determine_evidence_requirements(
            research_brief, critical_risk_analysis
        )
        
        # Phase 6: Success Probability with Critical Patterns
        success_assessment = self._assess_success_probability_with_critical_patterns(
            research_brief, critical_risk_analysis
        )
        
        return EnhancedResearchBrief(
            task_analysis={
                "description": user_request,
                "identified_symptoms": identified_symptoms or [],
                "risk_level": enhanced_risk_assessment["overall_risk_level"],
                "historical_precedent": research_brief["historical_context"]["similar_past_failures"],
                "critical_pattern_matches": critical_risk_analysis["matching_critical_patterns"]
            },
            current_system_investigation={
                "priority_areas": research_brief["research_guidance"]["priority_areas"],
                "focus_areas": adapted_strategy["investigation_focus"],
                "tool_usage_strategy": adapted_strategy["tool_usage_strategy"],
                "validation_priorities": adapted_strategy["validation_priorities"]
            },
            historical_pattern_analysis={
                "similar_past_failures": research_brief["historical_context"]["similar_past_failures"],
                "successful_approaches": research_brief["research_guidance"]["validated_approaches"],
                "critical_failure_patterns": critical_risk_analysis["critical_patterns_analysis"],
                "risk_indicators": enhanced_risk_assessment["combined_risk_indicators"],
                "evidence_requirements": evidence_requirements["historical_requirements"]
            },
            risk_assessment={
                "high_risk_areas": enhanced_risk_assessment["high_risk_areas"],
                "mitigation_strategies": enhanced_risk_assessment["mitigation_strategies"],
                "validation_checkpoints": enhanced_risk_assessment["validation_checkpoints"],
                "rollback_triggers": enhanced_risk_assessment["rollback_triggers"]
            },
            research_informed_recommendations={
                "recommended_approach": research_brief["execution_strategy"]["recommended_approach"],
                "priority_sequences": research_brief["planning_recommendations"]["proven_sequences"],
                "parallel_opportunities": research_brief["planning_recommendations"]["parallel_opportunities"],
                "infrastructure_first_validation": critical_risk_analysis["infrastructure_first_required"],
                "enhanced_evidence_collection": evidence_requirements["enhanced_requirements"]
            },
            success_probability_assessment={
                "estimated_success_rate": success_assessment["adjusted_success_rate"],
                "iteration_likelihood": success_assessment["iteration_likelihood"],
                "confidence_level": success_assessment["confidence_level"],
                "critical_risk_factors": success_assessment["critical_risk_factors"]
            }
        )
    
    def _analyze_critical_failure_risks(self, task_description: str, symptoms: List[str]) -> Dict[str, Any]:
        """Analyze task against critical failure patterns from cosmic hero incident"""
        
        critical_patterns = {
            "service_dependency_blindness": self._check_service_dependency_risk(task_description),
            "false_validation_success": self._check_false_validation_risk(task_description),
            "infrastructure_implementation_gap": self._check_infrastructure_gap_risk(task_description)
        }
        
        # Check for symptom matches with critical patterns
        critical_symptom_matches = []
        task_lower = task_description.lower()
        symptoms_lower = [s.lower() for s in symptoms]
        
        # Service dependency indicators
        if any(word in task_lower for word in ["deploy", "docker", "service", "container"]):
            critical_symptom_matches.append("deployment_service_risk")
            
        # Validation gap indicators  
        if any(word in task_lower for word in ["fix", "issue", "problem", "error"]):
            critical_symptom_matches.append("validation_gap_risk")
            
        # Infrastructure vs implementation indicators
        if any(word in task_lower for word in ["api", "endpoint", "frontend", "backend"]):
            critical_symptom_matches.append("infrastructure_implementation_risk")
        
        return {
            "critical_patterns_analysis": critical_patterns,
            "matching_critical_patterns": critical_symptom_matches,
            "infrastructure_first_required": any(critical_patterns.values()),
            "enhanced_validation_required": len(critical_symptom_matches) >= 2,
            "service_dependency_validation_required": critical_patterns["service_dependency_blindness"]
        }
    
    def _check_service_dependency_risk(self, task_description: str) -> bool:
        """Check if task has service dependency blindness risk"""
        risk_keywords = [
            "deploy", "docker", "service", "container", "orchestration",
            "infrastructure", "database", "redis", "postgres", "ollama"
        ]
        return any(keyword in task_description.lower() for keyword in risk_keywords)
    
    def _check_false_validation_risk(self, task_description: str) -> bool:
        """Check if task has false validation success risk"""
        risk_keywords = [
            "validation", "test", "verify", "check", "audit", "success",
            "endpoint", "accessibility", "functionality"
        ]
        return any(keyword in task_description.lower() for keyword in risk_keywords)
    
    def _check_infrastructure_gap_risk(self, task_description: str) -> bool:
        """Check if task has infrastructure vs implementation gap risk"""
        implementation_keywords = ["code", "application", "frontend", "backend", "api"]
        infrastructure_keywords = ["docker", "service", "database", "server", "deployment"]
        
        has_implementation = any(word in task_description.lower() for word in implementation_keywords)
        has_infrastructure = any(word in task_description.lower() for word in infrastructure_keywords)
        
        return has_implementation and has_infrastructure
    
    def _conduct_enhanced_risk_assessment(self, 
                                         research_brief: Dict[str, Any],
                                         critical_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct enhanced risk assessment combining historical and critical patterns"""
        
        base_risk = research_brief["task_analysis"]["risk_level"]
        critical_risks = critical_analysis["critical_patterns_analysis"]
        
        # Escalate risk level if critical patterns match
        if any(critical_risks.values()):
            if base_risk == "LOW":
                overall_risk = "MEDIUM"
            elif base_risk == "MEDIUM":
                overall_risk = "HIGH"
            else:
                overall_risk = "CRITICAL"
        else:
            overall_risk = base_risk
        
        # Combine risk indicators
        combined_risk_indicators = (
            research_brief["research_guidance"]["risk_indicators"] +
            [f"Critical pattern: {pattern}" for pattern, present in critical_risks.items() if present]
        )
        
        # Enhanced high-risk areas
        high_risk_areas = research_brief["research_guidance"]["priority_areas"].copy()
        if critical_risks["service_dependency_blindness"]:
            high_risk_areas.extend([
                "Docker service orchestration",
                "Service dependency validation",
                "Infrastructure health monitoring"
            ])
        
        return {
            "overall_risk_level": overall_risk,
            "combined_risk_indicators": combined_risk_indicators,
            "high_risk_areas": list(set(high_risk_areas)),
            "mitigation_strategies": self._generate_mitigation_strategies(critical_risks),
            "validation_checkpoints": self._generate_validation_checkpoints(critical_risks),
            "rollback_triggers": self._generate_rollback_triggers(critical_risks)
        }
    
    def _generate_mitigation_strategies(self, critical_risks: Dict[str, bool]) -> List[str]:
        """Generate mitigation strategies based on critical risk patterns"""
        strategies = []
        
        if critical_risks["service_dependency_blindness"]:
            strategies.extend([
                "Implement Docker service status validation before deployment claims",
                "Include infrastructure health checks in all validation phases",
                "Verify service dependencies before application testing"
            ])
        
        if critical_risks["false_validation_success"]:
            strategies.extend([
                "Require concrete evidence for all validation claims",
                "Implement end-to-end accessibility testing",
                "Cross-validate agent reports with manual verification"
            ])
        
        if critical_risks["infrastructure_implementation_gap"]:
            strategies.extend([
                "Infrastructure-first validation approach",
                "Service health validation before code deployment claims",
                "Multi-service coordination verification"
            ])
        
        return strategies
    
    def _generate_validation_checkpoints(self, critical_risks: Dict[str, bool]) -> List[str]:
        """Generate validation checkpoints based on critical patterns"""
        checkpoints = []
        
        if critical_risks["service_dependency_blindness"]:
            checkpoints.extend([
                "Checkpoint: All Docker services running (docker ps verification)",
                "Checkpoint: Service health endpoints responding",
                "Checkpoint: Database connectivity confirmed"
            ])
        
        if critical_risks["false_validation_success"]:
            checkpoints.extend([
                "Checkpoint: End-to-end user workflow completion",
                "Checkpoint: Production accessibility verified with curl/ping",
                "Checkpoint: Real user interaction testing completed"
            ])
        
        return checkpoints
    
    def _generate_rollback_triggers(self, critical_risks: Dict[str, bool]) -> List[str]:
        """Generate rollback triggers based on critical patterns"""
        triggers = []
        
        if critical_risks["service_dependency_blindness"]:
            triggers.extend([
                "Any Docker service reports as not running",
                "Service health check failures",
                "Infrastructure dependency validation failures"
            ])
        
        if critical_risks["false_validation_success"]:
            triggers.extend([
                "System inaccessibility detected",
                "End-to-end workflow failures",
                "Validation agent claims contradict manual testing"
            ])
        
        return triggers
    
    def _adapt_research_strategy(self, 
                                research_brief: Dict[str, Any],
                                critical_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt research strategy based on critical pattern analysis"""
        
        # Base investigation focus
        investigation_focus = research_brief["research_guidance"]["priority_areas"].copy()
        
        # Add critical pattern focus areas
        if critical_analysis["infrastructure_first_required"]:
            investigation_focus.insert(0, "Infrastructure and service health first")
            investigation_focus.insert(1, "Docker service orchestration status")
        
        # Tool usage strategy adaptation
        tool_usage_strategy = [
            "Start with Docker and service investigation (docker ps, service status)",
            "Use Read and Bash extensively for infrastructure analysis",
            "Employ Grep for service configuration discovery",
            "Utilize production testing tools early",
            "Cross-validate findings with multiple approaches"
        ]
        
        # Validation priorities based on critical patterns
        validation_priorities = [
            "Infrastructure health before code validation",
            "End-to-end accessibility verification",
            "Service dependency chain validation",
            "Real user workflow testing",
            "Evidence-based success claims only"
        ]
        
        return {
            "investigation_focus": investigation_focus,
            "tool_usage_strategy": tool_usage_strategy,
            "validation_priorities": validation_priorities
        }
    
    def _determine_evidence_requirements(self, 
                                        research_brief: Dict[str, Any],
                                        critical_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine evidence requirements enhanced with critical pattern prevention"""
        
        historical_requirements = research_brief["research_guidance"]["evidence_requirements"]
        
        enhanced_requirements = historical_requirements.copy()
        
        # Add critical pattern evidence requirements
        if critical_analysis["service_dependency_validation_required"]:
            enhanced_requirements.extend([
                "Docker ps output showing all required services running",
                "Individual service health check responses (200 OK)",
                "Database connectivity test results",
                "Service dependency chain validation proof"
            ])
        
        if critical_analysis["enhanced_validation_required"]:
            enhanced_requirements.extend([
                "curl/ping evidence of production system accessibility",
                "End-to-end user workflow completion screenshots/logs",
                "Real-time monitoring confirmation of system stability",
                "Cross-validation between multiple testing approaches"
            ])
        
        return {
            "historical_requirements": historical_requirements,
            "enhanced_requirements": enhanced_requirements,
            "critical_pattern_requirements": [
                req for req in enhanced_requirements 
                if req not in historical_requirements
            ]
        }
    
    def _assess_success_probability_with_critical_patterns(self, 
                                                          research_brief: Dict[str, Any],
                                                          critical_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess success probability including critical failure pattern risks"""
        
        base_success_rate = research_brief["execution_strategy"]["success_probability"]
        base_iteration_likelihood = research_brief["execution_strategy"]["iteration_likelihood"]
        
        # Adjust for critical pattern risks
        critical_risk_count = sum(1 for risk in critical_analysis["critical_patterns_analysis"].values() if risk)
        
        # Reduce success rate for critical risks
        critical_risk_penalty = critical_risk_count * 0.2
        adjusted_success_rate = max(0.3, base_success_rate - critical_risk_penalty)
        
        # Increase iteration likelihood for critical risks
        iteration_increase = critical_risk_count * 0.15
        adjusted_iteration_likelihood = min(0.9, base_iteration_likelihood + iteration_increase)
        
        # Confidence level based on pattern matching quality
        confidence_level = 0.85 if critical_risk_count > 0 else 0.75
        
        return {
            "adjusted_success_rate": adjusted_success_rate,
            "iteration_likelihood": adjusted_iteration_likelihood,
            "confidence_level": confidence_level,
            "critical_risk_factors": [
                pattern for pattern, present in critical_analysis["critical_patterns_analysis"].items() 
                if present
            ]
        }
    
    def generate_research_execution_plan(self, research_brief: EnhancedResearchBrief) -> Dict[str, Any]:
        """Generate detailed execution plan for enhanced research phase"""
        
        return {
            "phase_1_historical_context": {
                "actions": [
                    "Query knowledge graph for similar failure patterns",
                    "Identify high-risk areas from historical data", 
                    "Extract validated approaches from successful patterns"
                ],
                "tools": ["knowledge_graph_query", "pattern_analysis"],
                "expected_duration_minutes": 5
            },
            "phase_2_infrastructure_investigation": {
                "actions": [
                    "Check Docker service status (docker ps)",
                    "Verify critical service health (postgres, redis, ollama)",
                    "Validate service dependencies",
                    "Test production system accessibility"
                ],
                "tools": ["Bash", "Read", "Grep"],
                "expected_duration_minutes": 10,
                "critical_for_safety": True
            },
            "phase_3_targeted_codebase_analysis": {
                "actions": research_brief.current_system_investigation["focus_areas"],
                "tools": ["Read", "Grep", "Glob", "LS"],
                "expected_duration_minutes": 15,
                "priority_validation": research_brief.current_system_investigation["validation_priorities"]
            },
            "phase_4_evidence_synthesis": {
                "actions": [
                    "Cross-validate infrastructure and application findings",
                    "Verify findings against historical pattern requirements",
                    "Collect concrete evidence for all claims",
                    "Generate evidence-based recommendations"
                ],
                "tools": ["synthesis", "evidence_validation"],
                "expected_duration_minutes": 8
            },
            "success_criteria": {
                "infrastructure_health_verified": True,
                "historical_patterns_considered": True,
                "evidence_requirements_met": True,
                "critical_risks_assessed": True
            }
        }

# Usage and testing
if __name__ == "__main__":
    coordinator = EnhancedResearchCoordinator()
    
    # Test with infrastructure deployment scenario
    test_request = "Deploy cosmic hero page updates and validate production accessibility"
    test_symptoms = ["deployment success reported", "validation agents report EXCELLENT"]
    
    research_brief = coordinator.conduct_enhanced_research(test_request, test_symptoms)
    execution_plan = coordinator.generate_research_execution_plan(research_brief)
    
    print("=== ENHANCED RESEARCH BRIEF WITH CRITICAL PATTERN ANALYSIS ===")
    print(json.dumps({
        "research_brief": {
            "task_analysis": research_brief.task_analysis,
            "risk_assessment": research_brief.risk_assessment,
            "recommendations": research_brief.research_informed_recommendations,
            "success_probability": research_brief.success_probability_assessment
        },
        "execution_plan": execution_plan
    }, indent=2))