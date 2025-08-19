#!/usr/bin/env python3
"""
Critical Failure Pattern Integration System
Integrates critical production outage patterns from the cosmic hero deployment incident
into the knowledge graph for future prevention
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .knowledge_graph_v2 import (
    EnhancedKnowledgeGraph, FailurePattern, SuccessPattern, ValidationGap,
    PatternType, FailureCategory
)

@dataclass
class CriticalIncident:
    """Critical production incident analysis"""
    incident_id: str
    title: str
    description: str
    duration_hours: float
    services_affected: List[str]
    user_impact_severity: str
    detection_delay_hours: float
    root_cause_category: str
    failure_patterns: List[Dict[str, Any]]
    resolution_patterns: List[Dict[str, Any]]
    
class CriticalFailurePatternIntegration:
    """Integrates critical production failure patterns into knowledge graph"""
    
    def __init__(self, kg_path: str = "/home/marku/ai_workflow_engine/.claude/knowledge"):
        self.kg = EnhancedKnowledgeGraph(kg_path)
        self.incident_timestamp = datetime.now(timezone.utc).isoformat()
        
    def integrate_cosmic_hero_incident(self) -> Dict[str, Any]:
        """Integrate the cosmic hero deployment production outage patterns"""
        
        incident = CriticalIncident(
            incident_id="cosmic-hero-deployment-outage",
            title="Critical Production Outage During Cosmic Hero Page Deployment",
            description="Complete system failure during cosmic hero page deployment that went undetected for 20+ hours due to orchestration validation gaps",
            duration_hours=20.0,
            services_affected=["ollama", "postgres", "redis", "main application"],
            user_impact_severity="CRITICAL",
            detection_delay_hours=20.0,
            root_cause_category="service_dependency_blindness",
            failure_patterns=[],
            resolution_patterns=[]
        )
        
        # Pattern 1: Service Dependency Blindness
        service_dependency_pattern = self._create_service_dependency_blindness_pattern()
        
        # Pattern 2: False Validation Success
        false_validation_pattern = self._create_false_validation_success_pattern()
        
        # Pattern 3: Infrastructure vs Implementation Gap
        infrastructure_gap_pattern = self._create_infrastructure_implementation_gap_pattern()
        
        # Success Pattern: Immediate Docker Service Restoration
        service_restoration_success = self._create_service_restoration_success_pattern()
        
        # Validation Gap: Infrastructure Health Not Integrated
        infrastructure_validation_gap = self._create_infrastructure_validation_gap()
        
        # Store all patterns in knowledge graph
        pattern_ids = []
        
        # Store failure patterns
        for pattern in [service_dependency_pattern, false_validation_pattern, infrastructure_gap_pattern]:
            pattern_id = self.kg.store_failure_pattern(pattern)
            pattern_ids.append(pattern_id)
            incident.failure_patterns.append({"id": pattern_id, "type": pattern.pattern_type.value})
        
        # Store success pattern
        success_id = self.kg.store_success_pattern(service_restoration_success)
        incident.resolution_patterns.append({"id": success_id, "type": "immediate_service_restoration"})
        
        # Store validation gap
        gap_id = self.kg.store_validation_gap(infrastructure_validation_gap)
        
        # Create incident summary for knowledge graph
        incident_summary = self._create_incident_summary(incident, pattern_ids, success_id, gap_id)
        
        # Update research guidance protocols
        research_guidance_updates = self._create_research_guidance_updates(incident)
        
        return {
            "incident_integration": incident_summary,
            "patterns_stored": {
                "failure_patterns": len(incident.failure_patterns),
                "success_patterns": len(incident.resolution_patterns), 
                "validation_gaps": 1
            },
            "research_guidance_updates": research_guidance_updates,
            "prevention_protocols": self._create_prevention_protocols(incident)
        }
    
    def _create_service_dependency_blindness_pattern(self) -> FailurePattern:
        """Create the Service Dependency Blindness failure pattern"""
        return FailurePattern(
            id=self.kg.generate_pattern_id("service_dependency_blindness", self.incident_timestamp),
            pattern_type=PatternType.VALIDATION_GAP,
            category=FailureCategory.INTEGRATION_BREAKDOWN,
            description="Deployment processes removing critical Docker services while validation focuses only on code artifacts",
            symptoms=[
                "Application deployment appears successful",
                "Code changes validated and working",
                "No immediate error messages during deployment",
                "Services silently fail to start or are removed",
                "Delayed discovery of system unavailability"
            ],
            root_causes=[
                "Docker service orchestration not integrated into validation flow",
                "Validation focuses on application code, ignores infrastructure health",
                "No real-time monitoring of critical service availability",
                "Deployment scripts affecting service composition without validation"
            ],
            false_positive_indicators=[
                "Successful git commits and deployments",
                "Application builds without errors", 
                "Code-level tests passing",
                "Agent claiming 'EXCELLENT' implementation success",
                "No immediate 5xx HTTP errors visible"
            ],
            actual_user_impact=[
                "Complete system inaccessibility for 20+ hours",
                "All user workflows broken",
                "Data services unavailable",
                "Real-time features non-functional"
            ],
            environments_affected=["production"],
            fix_attempts=[
                {
                    "attempt": "Standard orchestration validation",
                    "outcome": "False success - missed infrastructure failure",
                    "timestamp": self.incident_timestamp
                }
            ],
            successful_resolution={
                "method": "Manual Docker service restoration",
                "steps": [
                    "Identified missing Docker services",
                    "Restored ollama, postgres, redis services",
                    "Verified service health individually",
                    "Confirmed system accessibility"
                ],
                "time_to_resolution_hours": 1.0
            },
            occurrence_count=1,
            first_occurrence=self.incident_timestamp,
            last_occurrence=self.incident_timestamp,
            agent_claims_vs_reality={
                "agent_claims": ["EXCELLENT orchestration success", "All validations passed"],
                "reality": ["Complete production outage", "Critical services removed"]
            },
            evidence_quality_score=0.95  # High quality - clear cause-effect relationship
        )
    
    def _create_false_validation_success_pattern(self) -> FailurePattern:
        """Create the False Validation Success failure pattern"""
        return FailurePattern(
            id=self.kg.generate_pattern_id("false_validation_success", self.incident_timestamp),
            pattern_type=PatternType.FALSE_POSITIVE_SUCCESS,
            category=FailureCategory.VALIDATION_INSUFFICIENT,
            description="Validation agents claiming success during critical system failures due to insufficient evidence collection",
            symptoms=[
                "Validation agents report 'EXCELLENT' results",
                "High confidence scores from automated validation",
                "Apparent successful completion of orchestration phases",
                "No validation failures logged",
                "System actually completely non-functional"
            ],
            root_causes=[
                "Evidence collection missing fundamental health checks",
                "Validation focuses on technical artifacts, not user accessibility", 
                "No end-to-end user workflow validation",
                "Lack of production system health verification",
                "Validation agents not testing actual service availability"
            ],
            false_positive_indicators=[
                "High validation success scores",
                "No technical error messages",
                "Successful API response codes (when services aren't actually running)",
                "Agent confidence levels above 90%",
                "Completion of all orchestration phases"
            ],
            actual_user_impact=[
                "Users cannot access system at all",
                "All application functionality broken", 
                "Data completely inaccessible",
                "No working user workflows"
            ],
            environments_affected=["production"],
            fix_attempts=[
                {
                    "attempt": "Trusted validation agent results",
                    "outcome": "Continued false positive - no real validation performed",
                    "timestamp": self.incident_timestamp
                }
            ],
            successful_resolution={
                "method": "Direct manual system testing and service restoration",
                "steps": [
                    "Bypassed validation agents",
                    "Manually tested system accessibility",
                    "Discovered service failures",
                    "Restored services directly"
                ],
                "time_to_resolution_hours": 1.0
            },
            occurrence_count=1,
            first_occurrence=self.incident_timestamp,
            last_occurrence=self.incident_timestamp,
            agent_claims_vs_reality={
                "agent_claims": [
                    "Production endpoint validation successful",
                    "User experience auditing complete",
                    "All evidence requirements met"
                ],
                "reality": [
                    "Production completely inaccessible",
                    "No user workflows functional",
                    "Zero valid evidence of system health"
                ]
            },
            evidence_quality_score=0.92  # High quality - clear validation failure
        )
    
    def _create_infrastructure_implementation_gap_pattern(self) -> FailurePattern:
        """Create the Infrastructure vs Implementation Gap failure pattern"""
        return FailurePattern(
            id=self.kg.generate_pattern_id("infrastructure_implementation_gap", self.incident_timestamp),
            pattern_type=PatternType.CROSS_ENVIRONMENT_DRIFT,
            category=FailureCategory.INTEGRATION_BREAKDOWN,
            description="Focus on application code implementation while ignoring critical service orchestration and infrastructure health",
            symptoms=[
                "Successful application code deployment",
                "Application components functioning individually",
                "Build and deployment processes complete successfully",
                "Docker containers failing to start or being removed",
                "Infrastructure services unavailable"
            ],
            root_causes=[
                "Orchestration treats infrastructure as separate from implementation",
                "Docker container health not integrated into deployment validation",
                "Service dependencies not validated during application deployment",
                "Multi-service architecture coordination gaps",
                "Infrastructure changes made during application development without integration"
            ],
            false_positive_indicators=[
                "Application deployment success messages",
                "Individual component functionality",
                "Code compilation and build success",
                "Git repository synchronization success"
            ],
            actual_user_impact=[
                "System completely non-functional despite 'successful' deployment",
                "Service unavailability affecting all user interactions",
                "Data layer completely inaccessible",
                "Real-time functionality broken"
            ],
            environments_affected=["production"],
            fix_attempts=[
                {
                    "attempt": "Application-focused troubleshooting",
                    "outcome": "Ineffective - root cause was infrastructure",
                    "timestamp": self.incident_timestamp
                }
            ],
            successful_resolution={
                "method": "Infrastructure-first diagnosis and restoration",
                "steps": [
                    "Checked Docker service status",
                    "Identified missing critical services",
                    "Restored service orchestration",
                    "Validated service health before application testing"
                ],
                "time_to_resolution_hours": 1.0
            },
            occurrence_count=1,
            first_occurrence=self.incident_timestamp,
            last_occurrence=self.incident_timestamp,
            agent_claims_vs_reality={
                "agent_claims": [
                    "Implementation successful",
                    "Code deployment complete",
                    "Application functionality verified"
                ],
                "reality": [
                    "Infrastructure broken",
                    "Critical services unavailable",
                    "System completely non-functional"
                ]
            },
            evidence_quality_score=0.90  # High quality - clear infrastructure gap
        )
    
    def _create_service_restoration_success_pattern(self) -> SuccessPattern:
        """Create the successful service restoration pattern"""
        return SuccessPattern(
            id=self.kg.generate_pattern_id("immediate_service_restoration", self.incident_timestamp),
            pattern_type="infrastructure_restoration",
            description="Immediate Docker service restoration resolving production outage within 1 hour",
            implementation_steps=[
                "Check Docker service status immediately",
                "Identify missing or failed services (ollama, postgres, redis)",
                "Restore services using docker-compose or manual startup",
                "Verify individual service health before system testing",
                "Confirm end-to-end system accessibility"
            ],
            validation_evidence=[
                "Docker ps shows all required services running",
                "Individual service health checks return success",
                "curl/ping tests confirm system accessibility",
                "User workflow testing demonstrates functionality",
                "Real-time monitoring shows service stability"
            ],
            replication_requirements=[
                "Docker orchestration environment",
                "Access to service configuration files",
                "Ability to restart individual services",
                "Health check endpoints for each service"
            ],
            environments_tested=["production"],
            user_functionality_verified=[
                "System login and authentication",
                "Database connectivity and queries",
                "Real-time features and WebSocket connections",
                "API endpoint accessibility"
            ],
            cross_validation_agents=[
                "production-endpoint-validator",
                "user-experience-auditor", 
                "monitoring-analyst"
            ],
            evidence_quality_score=0.98,  # Very high - immediate, verifiable resolution
            reproduction_success_rate=1.0   # 100% success when services are the issue
        )
    
    def _create_infrastructure_validation_gap(self) -> ValidationGap:
        """Create validation gap for infrastructure health integration"""
        return ValidationGap(
            id=self.kg.generate_pattern_id("infrastructure_validation_gap", self.incident_timestamp),
            gap_type="infrastructure_health_integration",
            description="Validation flows do not include Docker service health checks and infrastructure availability",
            missed_scenarios=[
                "Docker services removed during deployment",
                "Service containers failing to start",
                "Infrastructure health degradation",
                "Service dependency chain failures",
                "Real-time service availability validation"
            ],
            improvement_recommendations=[
                "Integrate Docker service status checks into all validation phases",
                "Add infrastructure health as mandatory evidence requirement",
                "Include service dependency validation in orchestration workflows",
                "Implement real-time monitoring integration for validation",
                "Create infrastructure-first validation checkpoints"
            ],
            affected_workflows=[
                "step_6_evidence_validation",
                "production-endpoint-validator",
                "user-experience-auditor",
                "orchestration-auditor validation"
            ],
            detection_method="Production outage post-mortem analysis"
        )
    
    def _create_incident_summary(self, incident: CriticalIncident, 
                                failure_ids: List[str], success_id: str, gap_id: str) -> Dict[str, Any]:
        """Create comprehensive incident summary for knowledge graph"""
        return {
            "incident_id": incident.incident_id,
            "timestamp": self.incident_timestamp,
            "severity": incident.user_impact_severity,
            "duration_hours": incident.duration_hours,
            "detection_delay_hours": incident.detection_delay_hours,
            "patterns_documented": {
                "failure_patterns": failure_ids,
                "success_patterns": [success_id],
                "validation_gaps": [gap_id]
            },
            "key_insights": [
                "Infrastructure health must be validated before claiming deployment success",
                "Service dependency validation is critical for multi-service applications",
                "Validation agents need concrete evidence of system accessibility",
                "Infrastructure-first diagnosis resolves service orchestration issues quickly"
            ],
            "prevention_requirements": [
                "Docker service status integration in validation",
                "Mandatory end-to-end accessibility testing",
                "Infrastructure health as evidence requirement",
                "Service dependency chain validation"
            ]
        }
    
    def _create_research_guidance_updates(self, incident: CriticalIncident) -> Dict[str, Any]:
        """Create research guidance updates for future orchestrations"""
        return {
            "new_priority_areas": [
                "Docker service orchestration health",
                "Infrastructure dependency validation",
                "End-to-end system accessibility verification",
                "Service container status monitoring",
                "Multi-service application coordination"
            ],
            "new_risk_indicators": [
                "Deployment processes modifying Docker configurations",
                "Validation reporting success without infrastructure checks",
                "Agent confidence levels exceeding actual evidence quality",
                "Service orchestration changes during application development",
                "Missing real-time monitoring integration"
            ],
            "enhanced_evidence_requirements": [
                "Docker ps output showing all required services",
                "Individual service health check responses",
                "Curl/ping evidence of system accessibility",
                "End-to-end user workflow completion proof",
                "Real-time monitoring confirmation of system stability"
            ],
            "updated_validation_protocols": [
                "Infrastructure-first validation approach",
                "Mandatory service dependency checking",
                "Concrete accessibility evidence collection",
                "Cross-validation between infrastructure and application health"
            ]
        }
    
    def _create_prevention_protocols(self, incident: CriticalIncident) -> Dict[str, Any]:
        """Create prevention protocols for similar incidents"""
        return {
            "pre_deployment_checks": [
                "Verify all Docker services running before deployment",
                "Document service dependencies and health check endpoints",
                "Test service restart procedures",
                "Validate monitoring integration for all services"
            ],
            "validation_enhancements": [
                "Add Docker service status to mandatory evidence",
                "Implement infrastructure health gates in Step 6",
                "Require production accessibility proof (curl/ping)",
                "Cross-validate infrastructure and application health"
            ],
            "monitoring_requirements": [
                "Real-time Docker service status monitoring",
                "Service dependency chain health tracking",
                "Infrastructure availability alerting",
                "End-to-end system accessibility monitoring"
            ],
            "rollback_triggers": [
                "Any Docker service reported as not running",
                "Failed infrastructure health checks",
                "System accessibility failures",
                "Service dependency validation failures"
            ]
        }

# Integration execution
if __name__ == "__main__":
    integration = CriticalFailurePatternIntegration()
    result = integration.integrate_cosmic_hero_incident()
    
    print("=== CRITICAL FAILURE PATTERN INTEGRATION COMPLETE ===")
    print(json.dumps(result, indent=2))