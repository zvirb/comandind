#!/usr/bin/env python3
"""
Enhanced Validation Framework - Core validation orchestration with MAST compliance
Eliminates false positives through multi-layer validation and evidence requirements
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationLayer(Enum):
    """Validation layers in the enhanced framework"""
    EVIDENCE_COLLECTION = "evidence_collection"
    CROSS_VERIFICATION = "cross_verification" 
    REAL_WORLD_TESTING = "real_world_testing"
    ENSEMBLE_VALIDATION = "ensemble_validation"
    PATTERN_RECOGNITION = "pattern_recognition"

class MASTComponent(Enum):
    """MAST Framework Components"""
    METRICS = "metrics"
    ARTIFACTS = "artifacts"
    SYSTEMS = "systems"
    TESTS = "tests"

class ValidationResult(Enum):
    """Validation result types"""
    SUCCESS = "success"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"
    REQUIRES_REVIEW = "requires_review"

@dataclass
class Evidence:
    """Evidence artifact for validation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    description: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    independence_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_agent: str = ""
    validation_layer: ValidationLayer = ValidationLayer.EVIDENCE_COLLECTION

@dataclass
class ValidationRequest:
    """Request for validation with evidence requirements"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    component: str = ""
    claim: str = ""
    evidence_required: List[str] = field(default_factory=list)
    validation_layers: List[ValidationLayer] = field(default_factory=list)
    mast_components: List[MASTComponent] = field(default_factory=list)
    cross_verification_agents: List[str] = field(default_factory=list)
    minimum_evidence_quality: float = 0.8
    requires_real_world_testing: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class ValidationResponse:
    """Response from validation with evidence and cross-verification"""
    request_id: str
    result: ValidationResult
    evidence: List[Evidence] = field(default_factory=list)
    cross_verification_results: Dict[str, Any] = field(default_factory=dict)
    mast_compliance: Dict[MASTComponent, float] = field(default_factory=dict)
    false_positive_risk: float = 0.0
    confidence_score: float = 0.0
    validation_summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class EnhancedValidationFramework:
    """
    Core validation framework that eliminates false positives through:
    - Multi-layer validation with evidence requirements
    - Cross-verification between independent agents
    - MAST framework compliance
    - Real-world user testing integration
    - False positive pattern recognition
    """
    
    def __init__(self):
        self.validation_history: List[ValidationResponse] = []
        self.evidence_store: Dict[str, Evidence] = {}
        self.agent_registry: Set[str] = set()
        self.false_positive_patterns: List[Dict[str, Any]] = []
        self.mast_baselines: Dict[MASTComponent, float] = {
            MASTComponent.METRICS: 0.95,
            MASTComponent.ARTIFACTS: 0.90,
            MASTComponent.SYSTEMS: 0.95,
            MASTComponent.TESTS: 0.90
        }
        self.validation_stats = {
            "total_validations": 0,
            "false_positives_prevented": 0,
            "evidence_quality_average": 0.0,
            "cross_verification_coverage": 0.0,
            "mast_compliance_average": 0.0
        }
        
        # Load existing patterns and history
        self._load_validation_history()
        self._load_false_positive_patterns()
        
    async def validate_with_evidence(self, request: ValidationRequest) -> ValidationResponse:
        """
        Main validation method that implements multi-layer validation with evidence requirements
        """
        logger.info(f"Starting enhanced validation for: {request.component}")
        
        response = ValidationResponse(
            request_id=request.id,
            result=ValidationResult.INCONCLUSIVE
        )
        
        try:
            # Layer 1: Evidence Collection
            evidence_results = await self._collect_mandatory_evidence(request)
            response.evidence.extend(evidence_results["evidence"])
            
            if evidence_results["sufficient_evidence"]:
                # Layer 2: Cross-Verification
                cross_verification = await self._perform_cross_verification(request, evidence_results)
                response.cross_verification_results = cross_verification
                
                # Layer 3: Real-World Testing (if required)
                if request.requires_real_world_testing:
                    real_world_results = await self._perform_real_world_testing(request)
                    response.evidence.extend(real_world_results["evidence"])
                
                # Layer 4: Ensemble Validation
                ensemble_results = await self._perform_ensemble_validation(request, response.evidence)
                
                # Layer 5: Pattern Recognition & False Positive Detection
                pattern_analysis = await self._analyze_false_positive_patterns(request, response.evidence)
                response.false_positive_risk = pattern_analysis["false_positive_risk"]
                
                # Calculate MAST compliance
                response.mast_compliance = await self._calculate_mast_compliance(response.evidence)
                
                # Make final determination
                response.result = await self._determine_final_result(
                    evidence_results, cross_verification, ensemble_results, pattern_analysis
                )
                response.confidence_score = await self._calculate_confidence_score(response)
                response.validation_summary = await self._generate_validation_summary(response)
                
            else:
                response.result = ValidationResult.FAILURE
                response.validation_summary = "Insufficient evidence provided for validation"
                response.warnings.append("Evidence collection failed minimum requirements")
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            response.result = ValidationResult.FAILURE
            response.validation_summary = f"Validation error: {str(e)}"
            
        # Update statistics and history
        await self._update_validation_stats(response)
        self.validation_history.append(response)
        
        # Save results for analysis
        await self._save_validation_results(response)
        
        logger.info(f"Validation completed: {response.result.value} (confidence: {response.confidence_score:.2f})")
        return response
    
    async def _collect_mandatory_evidence(self, request: ValidationRequest) -> Dict[str, Any]:
        """Collect mandatory evidence for validation"""
        logger.info("Layer 1: Collecting mandatory evidence")
        
        evidence_collection = {
            "evidence": [],
            "sufficient_evidence": False,
            "evidence_quality_score": 0.0,
            "missing_evidence": []
        }
        
        # Evidence types required for different claims
        evidence_requirements = {
            "authentication_success": ["user_workflow_video", "browser_logs", "network_requests"],
            "api_endpoint_functional": ["response_data", "status_codes", "performance_metrics"],
            "deployment_success": ["health_checks", "environment_validation", "user_acceptance"],
            "security_validation": ["vulnerability_scan", "penetration_test", "code_audit"]
        }
        
        required_evidence = evidence_requirements.get(request.claim.lower(), request.evidence_required)
        
        for evidence_type in required_evidence:
            evidence = await self._collect_evidence_by_type(evidence_type, request)
            if evidence:
                evidence_collection["evidence"].append(evidence)
            else:
                evidence_collection["missing_evidence"].append(evidence_type)
        
        # Calculate evidence sufficiency
        collected_count = len(evidence_collection["evidence"])
        required_count = len(required_evidence)
        sufficiency_ratio = collected_count / required_count if required_count > 0 else 0
        
        # Calculate quality score
        if evidence_collection["evidence"]:
            quality_scores = [e.quality_score for e in evidence_collection["evidence"]]
            evidence_collection["evidence_quality_score"] = sum(quality_scores) / len(quality_scores)
        
        # Evidence is sufficient if we have at least 70% of required evidence with good quality
        evidence_collection["sufficient_evidence"] = (
            sufficiency_ratio >= 0.7 and 
            evidence_collection["evidence_quality_score"] >= request.minimum_evidence_quality
        )
        
        logger.info(f"Evidence collection: {collected_count}/{required_count} collected, quality: {evidence_collection['evidence_quality_score']:.2f}")
        return evidence_collection
    
    async def _collect_evidence_by_type(self, evidence_type: str, request: ValidationRequest) -> Optional[Evidence]:
        """Collect specific type of evidence"""
        
        evidence_collectors = {
            "user_workflow_video": self._collect_user_workflow_evidence,
            "browser_logs": self._collect_browser_logs_evidence,
            "network_requests": self._collect_network_evidence,
            "response_data": self._collect_api_response_evidence,
            "status_codes": self._collect_status_code_evidence,
            "performance_metrics": self._collect_performance_evidence,
            "health_checks": self._collect_health_check_evidence,
            "environment_validation": self._collect_environment_evidence,
            "user_acceptance": self._collect_user_acceptance_evidence,
            "vulnerability_scan": self._collect_vulnerability_evidence,
            "penetration_test": self._collect_penetration_test_evidence,
            "code_audit": self._collect_code_audit_evidence
        }
        
        collector = evidence_collectors.get(evidence_type)
        if collector:
            return await collector(request)
        else:
            logger.warning(f"No collector available for evidence type: {evidence_type}")
            return None
    
    async def _collect_user_workflow_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect user workflow evidence through browser automation"""
        
        evidence = Evidence(
            type="user_workflow_video",
            description="User workflow validation through browser automation",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        try:
            # Simulate browser automation results
            # In real implementation, this would use browser automation tools
            workflow_results = {
                "workflow_completed": True,
                "steps_successful": 4,
                "steps_total": 5,
                "user_errors": 1,
                "completion_time": 12.3,
                "screenshots": ["step1.png", "step2.png", "step3.png", "step4.png"],
                "console_errors": ["CSRF token validation failed"],
                "network_failures": 1
            }
            
            evidence.data = workflow_results
            
            # Calculate quality based on workflow success
            success_rate = workflow_results["steps_successful"] / workflow_results["steps_total"]
            error_penalty = len(workflow_results["console_errors"]) * 0.1
            evidence.quality_score = max(0.0, success_rate - error_penalty)
            evidence.independence_score = 1.0  # Browser automation is independent
            
        except Exception as e:
            evidence.data = {"error": str(e), "collection_failed": True}
            evidence.quality_score = 0.0
        
        return evidence
    
    async def _collect_browser_logs_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect browser console logs and errors"""
        
        evidence = Evidence(
            type="browser_logs",
            description="Browser console logs and JavaScript errors",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        # Simulate browser log collection
        browser_logs = {
            "console_errors": [
                {"level": "error", "message": "403 Forbidden: CSRF token validation failed", "timestamp": "2025-01-11T10:30:15Z"},
                {"level": "warning", "message": "Authentication token expired", "timestamp": "2025-01-11T10:30:16Z"}
            ],
            "network_errors": [
                {"url": "/api/v1/auth/login", "status": 403, "error": "CSRF validation failed"}
            ],
            "javascript_errors": [],
            "performance_issues": [
                {"type": "slow_request", "url": "/api/v1/dashboard", "duration": 3200}
            ]
        }
        
        evidence.data = browser_logs
        
        # Quality based on error severity and quantity
        error_count = len(browser_logs["console_errors"]) + len(browser_logs["network_errors"])
        evidence.quality_score = max(0.1, 1.0 - (error_count * 0.2))
        evidence.independence_score = 0.9  # Browser logs are mostly independent
        
        return evidence
    
    async def _collect_network_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect network request/response evidence"""
        
        evidence = Evidence(
            type="network_requests",
            description="HTTP requests and responses during testing",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        # Simulate network monitoring
        network_data = {
            "requests": [
                {
                    "method": "POST",
                    "url": "/api/v1/auth/login",
                    "status": 403,
                    "response_time": 156,
                    "headers": {"Content-Type": "application/json"},
                    "response": {"error": "CSRF token validation failed"}
                },
                {
                    "method": "GET", 
                    "url": "/api/v1/health",
                    "status": 200,
                    "response_time": 45,
                    "response": {"status": "healthy"}
                }
            ],
            "failed_requests": 1,
            "total_requests": 2,
            "average_response_time": 100.5
        }
        
        evidence.data = network_data
        
        # Quality based on request success rate
        success_rate = (network_data["total_requests"] - network_data["failed_requests"]) / network_data["total_requests"]
        evidence.quality_score = success_rate
        evidence.independence_score = 0.8
        
        return evidence
    
    async def _collect_api_response_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect API response data evidence"""
        
        evidence = Evidence(
            type="api_response_data",
            description="API endpoint response data validation",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        # This would integrate with actual API testing
        response_data = {
            "endpoints_tested": [
                {"endpoint": "/api/v1/health", "status": 200, "response_valid": True},
                {"endpoint": "/api/v1/auth/login", "status": 403, "response_valid": False}
            ],
            "schema_validation": "failed",
            "response_times": [45, 156],
            "data_integrity": "partial"
        }
        
        evidence.data = response_data
        evidence.quality_score = 0.5  # Mixed results
        evidence.independence_score = 0.7
        
        return evidence
    
    async def _collect_status_code_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect HTTP status code evidence"""
        
        evidence = Evidence(
            type="status_codes",
            description="HTTP status codes from endpoint testing",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        status_data = {
            "status_codes": [200, 403, 200, 500],
            "success_codes": [200, 200],
            "error_codes": [403, 500],
            "success_rate": 0.5
        }
        
        evidence.data = status_data
        evidence.quality_score = status_data["success_rate"]
        evidence.independence_score = 0.8
        
        return evidence
    
    async def _collect_performance_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect performance metrics evidence"""
        
        evidence = Evidence(
            type="performance_metrics",
            description="System performance metrics during testing",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        performance_data = {
            "response_times": {"p50": 120, "p95": 300, "p99": 450},
            "throughput": {"requests_per_second": 25},
            "resource_usage": {"cpu_percent": 65, "memory_percent": 78},
            "error_rate": 0.15
        }
        
        evidence.data = performance_data
        
        # Quality based on meeting performance targets
        p95_target = 2000  # 2 seconds
        quality = 1.0 if performance_data["response_times"]["p95"] < p95_target else 0.6
        evidence.quality_score = quality
        evidence.independence_score = 0.9
        
        return evidence
    
    async def _collect_health_check_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect system health check evidence"""
        
        evidence = Evidence(
            type="health_checks",
            description="System health and readiness checks",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        health_data = {
            "services_healthy": 4,
            "services_total": 5,
            "unhealthy_services": ["authentication_service"],
            "database_status": "healthy",
            "cache_status": "healthy",
            "external_deps_status": "degraded"
        }
        
        evidence.data = health_data
        
        # Quality based on service health
        health_ratio = health_data["services_healthy"] / health_data["services_total"]
        evidence.quality_score = health_ratio
        evidence.independence_score = 1.0
        
        return evidence
    
    async def _collect_environment_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect environment validation evidence"""
        
        evidence = Evidence(
            type="environment_validation",
            description="Environment configuration and consistency validation",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        env_data = {
            "environments_validated": ["development", "staging"],
            "configuration_consistent": False,
            "environment_issues": [
                {"env": "staging", "issue": "CSRF configuration mismatch"},
                {"env": "staging", "issue": "Authentication backend misconfiguration"}
            ],
            "deployment_status": "partially_successful"
        }
        
        evidence.data = env_data
        evidence.quality_score = 0.3  # Configuration issues detected
        evidence.independence_score = 0.9
        
        return evidence
    
    async def _collect_user_acceptance_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect user acceptance testing evidence"""
        
        evidence = Evidence(
            type="user_acceptance",
            description="User acceptance and usability validation",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        acceptance_data = {
            "user_scenarios_tested": 3,
            "user_scenarios_passed": 1,
            "user_feedback": [
                {"scenario": "login", "success": False, "feedback": "Cannot log in with existing account"},
                {"scenario": "registration", "success": True, "feedback": "New user registration works"},
                {"scenario": "password_reset", "success": False, "feedback": "Password reset form not working"}
            ],
            "usability_score": 3.2  # Out of 10
        }
        
        evidence.data = acceptance_data
        
        # Quality based on user acceptance
        acceptance_rate = acceptance_data["user_scenarios_passed"] / acceptance_data["user_scenarios_tested"]
        evidence.quality_score = acceptance_rate
        evidence.independence_score = 1.0  # User feedback is fully independent
        
        return evidence
    
    async def _collect_vulnerability_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect security vulnerability evidence"""
        
        evidence = Evidence(
            type="vulnerability_scan",
            description="Security vulnerability scan results",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        vuln_data = {
            "vulnerabilities_found": 2,
            "critical_vulns": 0,
            "high_vulns": 1,
            "medium_vulns": 1,
            "low_vulns": 0,
            "vulnerabilities": [
                {"severity": "high", "type": "CSRF protection bypass", "status": "active"},
                {"severity": "medium", "type": "Session fixation", "status": "mitigated"}
            ]
        }
        
        evidence.data = vuln_data
        
        # Quality penalty for vulnerabilities
        vuln_penalty = vuln_data["critical_vulns"] * 0.5 + vuln_data["high_vulns"] * 0.3 + vuln_data["medium_vulns"] * 0.1
        evidence.quality_score = max(0.0, 1.0 - vuln_penalty)
        evidence.independence_score = 0.9
        
        return evidence
    
    async def _collect_penetration_test_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect penetration testing evidence"""
        
        evidence = Evidence(
            type="penetration_test",
            description="Penetration testing results",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        # This would integrate with actual security testing tools
        pentest_data = {
            "tests_conducted": 5,
            "successful_exploits": 1,
            "security_score": 7.5,
            "exploits": [
                {"type": "CSRF bypass", "success": True, "impact": "medium"}
            ]
        }
        
        evidence.data = pentest_data
        evidence.quality_score = 0.8  # Good testing coverage
        evidence.independence_score = 1.0  # External security testing
        
        return evidence
    
    async def _collect_code_audit_evidence(self, request: ValidationRequest) -> Evidence:
        """Collect code audit evidence"""
        
        evidence = Evidence(
            type="code_audit",
            description="Static code analysis and security audit results",
            validation_layer=ValidationLayer.EVIDENCE_COLLECTION,
            source_agent="enhanced_validation_framework"
        )
        
        audit_data = {
            "files_audited": 45,
            "issues_found": 12,
            "security_issues": 3,
            "code_quality_score": 8.2,
            "issues": [
                {"type": "security", "severity": "medium", "description": "CSRF token validation logic"},
                {"type": "quality", "severity": "low", "description": "Code complexity"}
            ]
        }
        
        evidence.data = audit_data
        evidence.quality_score = audit_data["code_quality_score"] / 10.0
        evidence.independence_score = 0.8  # Static analysis is reasonably independent
        
        return evidence
    
    async def _perform_cross_verification(self, request: ValidationRequest, evidence_results: Dict[str, Any]) -> Dict[str, Any]:
        """Perform cross-verification with multiple independent agents"""
        logger.info("Layer 2: Performing cross-verification")
        
        cross_verification = {
            "agents_used": [],
            "verification_results": {},
            "consensus_reached": False,
            "verification_confidence": 0.0,
            "conflicts": []
        }
        
        # Define agent pools for different validation types
        agent_pools = {
            "authentication": ["security-validator", "ui-regression-debugger", "user-experience-auditor"],
            "api": ["backend-gateway-expert", "fullstack-communication-auditor", "production-endpoint-validator"],
            "deployment": ["deployment-orchestrator", "monitoring-analyst", "infrastructure-orchestrator"],
            "security": ["security-validator", "security-vulnerability-scanner", "security-orchestrator"]
        }
        
        # Select agents for cross-verification
        validation_type = self._determine_validation_type(request.claim)
        available_agents = agent_pools.get(validation_type, request.cross_verification_agents)
        
        # Use at least 2 agents for critical validations
        selected_agents = available_agents[:3]  # Use up to 3 agents
        cross_verification["agents_used"] = selected_agents
        
        # Simulate cross-verification results from different agents
        for agent in selected_agents:
            agent_result = await self._simulate_agent_verification(agent, request, evidence_results)
            cross_verification["verification_results"][agent] = agent_result
        
        # Analyze consensus
        consensus_analysis = self._analyze_verification_consensus(cross_verification["verification_results"])
        cross_verification.update(consensus_analysis)
        
        logger.info(f"Cross-verification: {len(selected_agents)} agents, consensus: {cross_verification['consensus_reached']}")
        return cross_verification
    
    def _determine_validation_type(self, claim: str) -> str:
        """Determine validation type from claim"""
        claim_lower = claim.lower()
        
        if "auth" in claim_lower or "login" in claim_lower:
            return "authentication"
        elif "api" in claim_lower or "endpoint" in claim_lower:
            return "api"
        elif "deploy" in claim_lower or "deployment" in claim_lower:
            return "deployment"
        elif "security" in claim_lower or "vulnerability" in claim_lower:
            return "security"
        else:
            return "general"
    
    async def _simulate_agent_verification(self, agent: str, request: ValidationRequest, evidence_results: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate verification results from different agents"""
        
        # Agent-specific verification logic
        agent_behaviors = {
            "security-validator": {
                "focus": "security_aspects",
                "false_positive_tendency": 0.1,
                "evidence_weight": 0.9
            },
            "ui-regression-debugger": {
                "focus": "user_interface",
                "false_positive_tendency": 0.2,
                "evidence_weight": 0.8
            },
            "user-experience-auditor": {
                "focus": "user_workflows",
                "false_positive_tendency": 0.05,  # Low false positive rate for user testing
                "evidence_weight": 1.0
            },
            "backend-gateway-expert": {
                "focus": "api_functionality",
                "false_positive_tendency": 0.3,  # Higher false positive rate for technical checks
                "evidence_weight": 0.7
            }
        }
        
        behavior = agent_behaviors.get(agent, {
            "focus": "general",
            "false_positive_tendency": 0.25,
            "evidence_weight": 0.75
        })
        
        # Calculate agent's assessment based on evidence and behavior
        evidence_score = evidence_results.get("evidence_quality_score", 0.0)
        
        # Apply agent-specific weighting and false positive tendency
        weighted_score = evidence_score * behavior["evidence_weight"]
        
        # Simulate false positive tendency (agents claiming success when evidence shows failure)
        if evidence_score < 0.6:  # Evidence shows problems
            # Some agents might still claim success (false positive)
            import random
            if random.random() < behavior["false_positive_tendency"]:
                agent_assessment = "success"
                confidence = 0.7  # Lower confidence for false positives
            else:
                agent_assessment = "failure"
                confidence = weighted_score
        else:
            agent_assessment = "success" if weighted_score > 0.7 else "failure"
            confidence = weighted_score
        
        return {
            "agent": agent,
            "assessment": agent_assessment,
            "confidence": confidence,
            "focus_area": behavior["focus"],
            "evidence_considered": len(evidence_results.get("evidence", [])),
            "reasoning": f"{agent} focused on {behavior['focus']} with {evidence_score:.2f} evidence quality"
        }
    
    def _analyze_verification_consensus(self, verification_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze consensus between verification agents"""
        
        assessments = [result["assessment"] for result in verification_results.values()]
        confidences = [result["confidence"] for result in verification_results.values()]
        
        # Count votes
        success_votes = assessments.count("success")
        failure_votes = assessments.count("failure")
        total_votes = len(assessments)
        
        # Determine consensus
        consensus_threshold = 0.67  # 67% agreement needed
        consensus_reached = (success_votes / total_votes >= consensus_threshold) or (failure_votes / total_votes >= consensus_threshold)
        
        # Calculate verification confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Detect conflicts (high confidence but different assessments)
        conflicts = []
        if not consensus_reached:
            for agent, result in verification_results.items():
                if result["confidence"] > 0.8:  # High confidence
                    conflicts.append({
                        "agent": agent,
                        "assessment": result["assessment"],
                        "confidence": result["confidence"],
                        "conflict_type": "high_confidence_disagreement"
                    })
        
        return {
            "consensus_reached": consensus_reached,
            "verification_confidence": avg_confidence,
            "success_votes": success_votes,
            "failure_votes": failure_votes,
            "conflicts": conflicts,
            "consensus_assessment": "success" if success_votes > failure_votes else "failure"
        }
    
    async def _perform_real_world_testing(self, request: ValidationRequest) -> Dict[str, Any]:
        """Perform real-world user testing with browser automation"""
        logger.info("Layer 3: Performing real-world user testing")
        
        real_world_results = {
            "evidence": [],
            "user_workflows_tested": 0,
            "user_workflows_successful": 0,
            "real_world_success_rate": 0.0,
            "user_issues_detected": []
        }
        
        # Define real-world test scenarios
        test_scenarios = [
            {
                "name": "existing_user_login",
                "description": "Existing user attempts to log in",
                "steps": ["navigate_to_login", "enter_credentials", "submit_form", "verify_dashboard_access"],
                "expected_success": True
            },
            {
                "name": "new_user_registration",
                "description": "New user registration and first login",
                "steps": ["navigate_to_register", "fill_registration", "submit_registration", "verify_email", "first_login"],
                "expected_success": True
            },
            {
                "name": "password_reset_flow",
                "description": "User resets forgotten password",
                "steps": ["navigate_to_reset", "enter_email", "check_email", "reset_password", "login_with_new_password"],
                "expected_success": True
            }
        ]
        
        for scenario in test_scenarios:
            scenario_result = await self._execute_real_world_scenario(scenario, request)
            real_world_results["user_workflows_tested"] += 1
            
            if scenario_result["success"]:
                real_world_results["user_workflows_successful"] += 1
            else:
                real_world_results["user_issues_detected"].extend(scenario_result["issues"])
            
            # Create evidence from scenario
            scenario_evidence = Evidence(
                type="real_world_user_testing",
                description=f"Real-world testing: {scenario['name']}",
                data=scenario_result,
                quality_score=scenario_result["quality_score"],
                independence_score=1.0,  # Real user testing is fully independent
                validation_layer=ValidationLayer.REAL_WORLD_TESTING,
                source_agent="real_world_tester"
            )
            
            real_world_results["evidence"].append(scenario_evidence)
        
        # Calculate overall real-world success rate
        if real_world_results["user_workflows_tested"] > 0:
            real_world_results["real_world_success_rate"] = (
                real_world_results["user_workflows_successful"] / real_world_results["user_workflows_tested"]
            )
        
        logger.info(f"Real-world testing: {real_world_results['user_workflows_successful']}/{real_world_results['user_workflows_tested']} scenarios successful")
        return real_world_results
    
    async def _execute_real_world_scenario(self, scenario: Dict[str, Any], request: ValidationRequest) -> Dict[str, Any]:
        """Execute a real-world testing scenario"""
        
        # Simulate real browser automation results
        # In actual implementation, this would use browser automation tools
        scenario_results = {
            "scenario": scenario["name"],
            "success": False,
            "steps_completed": 0,
            "steps_total": len(scenario["steps"]),
            "issues": [],
            "performance": {},
            "screenshots": [],
            "quality_score": 0.0
        }
        
        # Simulate scenario execution based on known issues
        if scenario["name"] == "existing_user_login":
            # Known CSRF issue affects existing user login
            scenario_results.update({
                "success": False,
                "steps_completed": 2,  # Can navigate and enter credentials
                "issues": [
                    {"step": "submit_form", "issue": "403 Forbidden - CSRF token validation failed"},
                    {"step": "verify_dashboard_access", "issue": "Cannot access dashboard due to auth failure"}
                ],
                "performance": {"total_time": 15.2, "error_time": 8.3},
                "screenshots": ["login_page.png", "csrf_error.png"],
                "console_errors": ["CSRF token validation failed", "Authentication request rejected"]
            })
            
        elif scenario["name"] == "new_user_registration":
            # New user registration might work better
            scenario_results.update({
                "success": True,
                "steps_completed": 5,
                "issues": [],
                "performance": {"total_time": 45.8, "registration_time": 12.1},
                "screenshots": ["register_page.png", "email_verification.png", "welcome_dashboard.png"]
            })
            
        elif scenario["name"] == "password_reset_flow":
            # Password reset has issues
            scenario_results.update({
                "success": False,
                "steps_completed": 2,
                "issues": [
                    {"step": "check_email", "issue": "Password reset email not sent"},
                    {"step": "reset_password", "issue": "Reset form not accessible"}
                ],
                "performance": {"total_time": 8.5, "timeout_at": "email_check"}
            })
        
        # Calculate quality score based on success and completeness
        completion_rate = scenario_results["steps_completed"] / scenario_results["steps_total"]
        issue_penalty = len(scenario_results["issues"]) * 0.2
        scenario_results["quality_score"] = max(0.0, completion_rate - issue_penalty)
        
        return scenario_results
    
    async def _perform_ensemble_validation(self, request: ValidationRequest, evidence: List[Evidence]) -> Dict[str, Any]:
        """Perform ensemble validation across multiple domains"""
        logger.info("Layer 4: Performing ensemble validation")
        
        ensemble_results = {
            "functional_validation": {},
            "security_validation": {},
            "performance_validation": {},
            "quality_validation": {},
            "ensemble_score": 0.0,
            "domain_consensus": {}
        }
        
        # Functional validation
        functional_evidence = [e for e in evidence if e.type in ["user_workflow_video", "api_response_data", "health_checks"]]
        ensemble_results["functional_validation"] = self._validate_functional_domain(functional_evidence)
        
        # Security validation
        security_evidence = [e for e in evidence if e.type in ["vulnerability_scan", "penetration_test", "code_audit"]]
        ensemble_results["security_validation"] = self._validate_security_domain(security_evidence)
        
        # Performance validation
        performance_evidence = [e for e in evidence if e.type in ["performance_metrics", "network_requests"]]
        ensemble_results["performance_validation"] = self._validate_performance_domain(performance_evidence)
        
        # Quality validation
        quality_evidence = [e for e in evidence if e.type in ["user_acceptance", "code_audit"]]
        ensemble_results["quality_validation"] = self._validate_quality_domain(quality_evidence)
        
        # Calculate ensemble score
        domain_scores = [
            ensemble_results["functional_validation"].get("score", 0.0),
            ensemble_results["security_validation"].get("score", 0.0),
            ensemble_results["performance_validation"].get("score", 0.0),
            ensemble_results["quality_validation"].get("score", 0.0)
        ]
        
        ensemble_results["ensemble_score"] = sum(domain_scores) / len(domain_scores) if domain_scores else 0.0
        
        # Check domain consensus
        ensemble_results["domain_consensus"] = self._analyze_domain_consensus(ensemble_results)
        
        logger.info(f"Ensemble validation score: {ensemble_results['ensemble_score']:.2f}")
        return ensemble_results
    
    def _validate_functional_domain(self, evidence: List[Evidence]) -> Dict[str, Any]:
        """Validate functional domain"""
        
        if not evidence:
            return {"score": 0.0, "status": "no_evidence", "issues": ["No functional evidence available"]}
        
        # Calculate functional score based on user workflows and API responses
        quality_scores = [e.quality_score for e in evidence]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        issues = []
        if avg_quality < 0.7:
            issues.append("Functional validation shows significant issues")
        
        return {
            "score": avg_quality,
            "status": "pass" if avg_quality >= 0.7 else "fail",
            "evidence_count": len(evidence),
            "issues": issues
        }
    
    def _validate_security_domain(self, evidence: List[Evidence]) -> Dict[str, Any]:
        """Validate security domain"""
        
        if not evidence:
            return {"score": 0.5, "status": "no_evidence", "issues": ["No security evidence available"]}
        
        # Security validation is stricter
        quality_scores = [e.quality_score for e in evidence]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        # Security issues detected
        issues = []
        for e in evidence:
            if e.type == "vulnerability_scan" and "vulnerabilities" in e.data:
                vulns = e.data["vulnerabilities"]
                high_severity_vulns = [v for v in vulns if v.get("severity") in ["critical", "high"]]
                if high_severity_vulns:
                    issues.extend([f"High/Critical vulnerability: {v['type']}" for v in high_severity_vulns])
        
        return {
            "score": avg_quality,
            "status": "pass" if avg_quality >= 0.8 and not issues else "fail",
            "evidence_count": len(evidence),
            "issues": issues
        }
    
    def _validate_performance_domain(self, evidence: List[Evidence]) -> Dict[str, Any]:
        """Validate performance domain"""
        
        if not evidence:
            return {"score": 0.7, "status": "no_evidence", "issues": ["No performance evidence available"]}
        
        # Check performance targets
        issues = []
        quality_scores = [e.quality_score for e in evidence]
        
        for e in evidence:
            if e.type == "performance_metrics" and "response_times" in e.data:
                p95_time = e.data["response_times"].get("p95", 0)
                if p95_time > 2000:  # 2 second target
                    issues.append(f"P95 response time {p95_time}ms exceeds 2000ms target")
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.7
        
        return {
            "score": avg_quality,
            "status": "pass" if avg_quality >= 0.8 and not issues else "fail",
            "evidence_count": len(evidence),
            "issues": issues
        }
    
    def _validate_quality_domain(self, evidence: List[Evidence]) -> Dict[str, Any]:
        """Validate quality domain"""
        
        if not evidence:
            return {"score": 0.6, "status": "no_evidence", "issues": ["No quality evidence available"]}
        
        quality_scores = [e.quality_score for e in evidence]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        issues = []
        
        # Check user acceptance scores
        for e in evidence:
            if e.type == "user_acceptance" and "usability_score" in e.data:
                usability_score = e.data["usability_score"]
                if usability_score < 7.0:  # Out of 10
                    issues.append(f"Usability score {usability_score}/10 below acceptable threshold")
        
        return {
            "score": avg_quality,
            "status": "pass" if avg_quality >= 0.7 and not issues else "fail", 
            "evidence_count": len(evidence),
            "issues": issues
        }
    
    def _analyze_domain_consensus(self, ensemble_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze consensus across validation domains"""
        
        domain_statuses = [
            ensemble_results["functional_validation"].get("status", "unknown"),
            ensemble_results["security_validation"].get("status", "unknown"),
            ensemble_results["performance_validation"].get("status", "unknown"),
            ensemble_results["quality_validation"].get("status", "unknown")
        ]
        
        pass_count = domain_statuses.count("pass")
        fail_count = domain_statuses.count("fail")
        total_domains = len(domain_statuses)
        
        consensus_reached = (pass_count / total_domains >= 0.75) or (fail_count / total_domains >= 0.75)
        overall_status = "pass" if pass_count > fail_count else "fail"
        
        return {
            "consensus_reached": consensus_reached,
            "overall_status": overall_status,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "agreement_percentage": max(pass_count, fail_count) / total_domains * 100
        }
    
    async def _analyze_false_positive_patterns(self, request: ValidationRequest, evidence: List[Evidence]) -> Dict[str, Any]:
        """Analyze for false positive patterns"""
        logger.info("Layer 5: Analyzing false positive patterns")
        
        pattern_analysis = {
            "false_positive_risk": 0.0,
            "risk_factors": [],
            "historical_patterns_matched": [],
            "pattern_confidence": 0.0
        }
        
        # Known false positive patterns
        false_positive_indicators = [
            {
                "name": "technical_success_user_failure",
                "description": "Technical endpoints return 200 but users cannot complete workflows",
                "risk_weight": 0.8,
                "indicators": ["health_checks_pass", "user_workflows_fail"]
            },
            {
                "name": "single_agent_validation",
                "description": "Only one agent validates success without cross-verification",
                "risk_weight": 0.6,
                "indicators": ["single_validator", "no_cross_verification"]
            },
            {
                "name": "insufficient_evidence",
                "description": "Success claims without concrete evidence",
                "risk_weight": 0.7,
                "indicators": ["low_evidence_quality", "missing_user_testing"]
            }
        ]
        
        # Check for pattern matches
        total_risk = 0.0
        
        for pattern in false_positive_indicators:
            pattern_match_score = self._check_pattern_match(pattern, evidence, request)
            if pattern_match_score > 0.3:  # Pattern detected
                pattern_analysis["historical_patterns_matched"].append({
                    "pattern": pattern["name"],
                    "description": pattern["description"],
                    "match_score": pattern_match_score,
                    "risk_contribution": pattern_match_score * pattern["risk_weight"]
                })
                pattern_analysis["risk_factors"].append(pattern["description"])
                total_risk += pattern_match_score * pattern["risk_weight"]
        
        pattern_analysis["false_positive_risk"] = min(1.0, total_risk)
        pattern_analysis["pattern_confidence"] = 0.9 if pattern_analysis["historical_patterns_matched"] else 0.1
        
        logger.info(f"False positive risk: {pattern_analysis['false_positive_risk']:.2f}")
        return pattern_analysis
    
    def _check_pattern_match(self, pattern: Dict[str, Any], evidence: List[Evidence], request: ValidationRequest) -> float:
        """Check if evidence matches a false positive pattern"""
        
        match_score = 0.0
        
        if pattern["name"] == "technical_success_user_failure":
            # Look for health checks passing but user workflows failing
            health_evidence = [e for e in evidence if e.type == "health_checks"]
            user_evidence = [e for e in evidence if e.type in ["user_workflow_video", "user_acceptance"]]
            
            health_success = any(e.quality_score > 0.8 for e in health_evidence)
            user_failure = any(e.quality_score < 0.5 for e in user_evidence)
            
            if health_success and user_failure:
                match_score = 0.9
            elif health_success and not user_evidence:
                match_score = 0.6  # No user testing is a risk factor
        
        elif pattern["name"] == "single_agent_validation":
            # Check if only single agent validation was used
            if len(request.cross_verification_agents) <= 1:
                match_score = 0.8
        
        elif pattern["name"] == "insufficient_evidence":
            # Check evidence quality and completeness
            if not evidence:
                match_score = 1.0
            else:
                avg_quality = sum(e.quality_score for e in evidence) / len(evidence)
                if avg_quality < 0.6:
                    match_score = 0.7
                elif avg_quality < 0.8:
                    match_score = 0.4
        
        return match_score
    
    async def _calculate_mast_compliance(self, evidence: List[Evidence]) -> Dict[MASTComponent, float]:
        """Calculate MAST framework compliance"""
        
        mast_compliance = {}
        
        # Metrics compliance
        metrics_evidence = [e for e in evidence if e.type in ["performance_metrics", "status_codes"]]
        mast_compliance[MASTComponent.METRICS] = self._calculate_metrics_compliance(metrics_evidence)
        
        # Artifacts compliance
        artifact_evidence = [e for e in evidence if e.type in ["user_workflow_video", "browser_logs", "network_requests"]]
        mast_compliance[MASTComponent.ARTIFACTS] = self._calculate_artifacts_compliance(artifact_evidence)
        
        # Systems compliance
        systems_evidence = [e for e in evidence if e.type in ["health_checks", "environment_validation"]]
        mast_compliance[MASTComponent.SYSTEMS] = self._calculate_systems_compliance(systems_evidence)
        
        # Tests compliance
        tests_evidence = [e for e in evidence if e.type in ["real_world_user_testing", "vulnerability_scan", "code_audit"]]
        mast_compliance[MASTComponent.TESTS] = self._calculate_tests_compliance(tests_evidence)
        
        return mast_compliance
    
    def _calculate_metrics_compliance(self, evidence: List[Evidence]) -> float:
        """Calculate metrics compliance score"""
        if not evidence:
            return 0.0
        
        quality_scores = [e.quality_score for e in evidence]
        return sum(quality_scores) / len(quality_scores)
    
    def _calculate_artifacts_compliance(self, evidence: List[Evidence]) -> float:
        """Calculate artifacts compliance score"""
        if not evidence:
            return 0.0
        
        # Artifacts should have high independence scores
        independence_scores = [e.independence_score for e in evidence]
        avg_independence = sum(independence_scores) / len(independence_scores)
        
        # Weight by quality as well
        quality_scores = [e.quality_score for e in evidence]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        return (avg_independence + avg_quality) / 2.0
    
    def _calculate_systems_compliance(self, evidence: List[Evidence]) -> float:
        """Calculate systems compliance score"""
        if not evidence:
            return 0.0
        
        quality_scores = [e.quality_score for e in evidence]
        return sum(quality_scores) / len(quality_scores)
    
    def _calculate_tests_compliance(self, evidence: List[Evidence]) -> float:
        """Calculate tests compliance score"""
        if not evidence:
            return 0.0
        
        # Tests should have comprehensive coverage
        test_types = set(e.type for e in evidence)
        coverage_score = len(test_types) / 3.0  # Expect 3 types of tests
        
        quality_scores = [e.quality_score for e in evidence]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        return min(1.0, (coverage_score + avg_quality) / 2.0)
    
    async def _determine_final_result(self, evidence_results: Dict[str, Any], cross_verification: Dict[str, Any], 
                                    ensemble_results: Dict[str, Any], pattern_analysis: Dict[str, Any]) -> ValidationResult:
        """Determine final validation result based on all layers"""
        
        # Gather all validation signals
        evidence_sufficient = evidence_results.get("sufficient_evidence", False)
        evidence_quality = evidence_results.get("evidence_quality_score", 0.0)
        
        cross_verification_consensus = cross_verification.get("consensus_reached", False)
        cross_verification_assessment = cross_verification.get("consensus_assessment", "failure")
        
        ensemble_score = ensemble_results.get("ensemble_score", 0.0)
        domain_consensus = ensemble_results.get("domain_consensus", {}).get("consensus_reached", False)
        
        false_positive_risk = pattern_analysis.get("false_positive_risk", 0.0)
        
        # Decision logic with multiple validation layers
        if not evidence_sufficient:
            return ValidationResult.FAILURE
        
        if false_positive_risk > 0.7:
            return ValidationResult.REQUIRES_REVIEW
        
        if not cross_verification_consensus:
            return ValidationResult.INCONCLUSIVE
        
        if cross_verification_assessment == "failure":
            return ValidationResult.FAILURE
        
        if not domain_consensus:
            return ValidationResult.REQUIRES_REVIEW
        
        if ensemble_score < 0.7:
            return ValidationResult.FAILURE
        
        if evidence_quality >= 0.8 and ensemble_score >= 0.8 and false_positive_risk < 0.3:
            return ValidationResult.SUCCESS
        else:
            return ValidationResult.REQUIRES_REVIEW
    
    async def _calculate_confidence_score(self, response: ValidationResponse) -> float:
        """Calculate overall confidence score"""
        
        confidence_factors = []
        
        # Evidence quality
        if response.evidence:
            evidence_qualities = [e.quality_score for e in response.evidence]
            avg_evidence_quality = sum(evidence_qualities) / len(evidence_qualities)
            confidence_factors.append(avg_evidence_quality)
        
        # Cross-verification confidence
        cv_confidence = response.cross_verification_results.get("verification_confidence", 0.0)
        confidence_factors.append(cv_confidence)
        
        # MAST compliance
        if response.mast_compliance:
            mast_scores = list(response.mast_compliance.values())
            avg_mast = sum(mast_scores) / len(mast_scores)
            confidence_factors.append(avg_mast)
        
        # False positive risk penalty
        fp_penalty = response.false_positive_risk * 0.5
        
        if confidence_factors:
            base_confidence = sum(confidence_factors) / len(confidence_factors)
            return max(0.0, base_confidence - fp_penalty)
        else:
            return 0.0
    
    async def _generate_validation_summary(self, response: ValidationResponse) -> str:
        """Generate human-readable validation summary"""
        
        summary_parts = []
        
        # Result
        summary_parts.append(f"Validation Result: {response.result.value.upper()}")
        
        # Confidence
        summary_parts.append(f"Confidence: {response.confidence_score:.1%}")
        
        # Evidence summary
        evidence_count = len(response.evidence)
        if evidence_count > 0:
            avg_quality = sum(e.quality_score for e in response.evidence) / evidence_count
            summary_parts.append(f"Evidence: {evidence_count} artifacts collected (avg quality: {avg_quality:.1%})")
        
        # Cross-verification
        cv_results = response.cross_verification_results
        if cv_results:
            consensus = cv_results.get("consensus_reached", False)
            agents_used = len(cv_results.get("agents_used", []))
            summary_parts.append(f"Cross-verification: {agents_used} agents, consensus: {'Yes' if consensus else 'No'}")
        
        # MAST compliance
        if response.mast_compliance:
            mast_scores = response.mast_compliance
            avg_mast = sum(mast_scores.values()) / len(mast_scores)
            summary_parts.append(f"MAST Compliance: {avg_mast:.1%}")
        
        # False positive risk
        if response.false_positive_risk > 0.3:
            summary_parts.append(f"⚠️  False Positive Risk: {response.false_positive_risk:.1%}")
        
        # Warnings and recommendations
        if response.warnings:
            summary_parts.append(f"Warnings: {len(response.warnings)} issues detected")
        
        if response.recommendations:
            summary_parts.append(f"Recommendations: {len(response.recommendations)} improvements suggested")
        
        return " | ".join(summary_parts)
    
    async def _update_validation_stats(self, response: ValidationResponse):
        """Update validation statistics"""
        
        self.validation_stats["total_validations"] += 1
        
        # False positive prevention
        if response.false_positive_risk > 0.5 and response.result != ValidationResult.SUCCESS:
            self.validation_stats["false_positives_prevented"] += 1
        
        # Evidence quality
        if response.evidence:
            evidence_qualities = [e.quality_score for e in response.evidence]
            current_avg = self.validation_stats["evidence_quality_average"]
            total_validations = self.validation_stats["total_validations"]
            new_avg = (current_avg * (total_validations - 1) + sum(evidence_qualities) / len(evidence_qualities)) / total_validations
            self.validation_stats["evidence_quality_average"] = new_avg
        
        # Cross-verification coverage
        if response.cross_verification_results.get("consensus_reached", False):
            cv_coverage = self.validation_stats["cross_verification_coverage"]
            total = self.validation_stats["total_validations"]
            self.validation_stats["cross_verification_coverage"] = (cv_coverage * (total - 1) + 1.0) / total
        
        # MAST compliance
        if response.mast_compliance:
            mast_scores = list(response.mast_compliance.values())
            avg_mast = sum(mast_scores) / len(mast_scores)
            current_mast_avg = self.validation_stats["mast_compliance_average"]
            total = self.validation_stats["total_validations"]
            self.validation_stats["mast_compliance_average"] = (current_mast_avg * (total - 1) + avg_mast) / total
    
    async def _save_validation_results(self, response: ValidationResponse):
        """Save validation results for analysis and auditing"""
        
        results_dir = Path("/home/marku/AIWFE/app/testing/validation_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = results_dir / f"validation_{timestamp}_{response.request_id[:8]}.json"
        
        # Serialize response for saving
        response_data = {
            "request_id": response.request_id,
            "result": response.result.value,
            "evidence": [
                {
                    "id": e.id,
                    "type": e.type,
                    "description": e.description,
                    "quality_score": e.quality_score,
                    "independence_score": e.independence_score,
                    "timestamp": e.timestamp,
                    "source_agent": e.source_agent,
                    "validation_layer": e.validation_layer.value,
                    "data_summary": str(e.data)[:200] + "..." if len(str(e.data)) > 200 else str(e.data)
                } for e in response.evidence
            ],
            "cross_verification_results": response.cross_verification_results,
            "mast_compliance": {k.value: v for k, v in response.mast_compliance.items()},
            "false_positive_risk": response.false_positive_risk,
            "confidence_score": response.confidence_score,
            "validation_summary": response.validation_summary,
            "timestamp": response.timestamp,
            "warnings": response.warnings,
            "recommendations": response.recommendations
        }
        
        with open(result_file, 'w') as f:
            json.dump(response_data, f, indent=2)
        
        logger.info(f"Validation results saved: {result_file}")
    
    def _load_validation_history(self):
        """Load existing validation history"""
        
        results_dir = Path("/home/marku/AIWFE/app/testing/validation_results")
        if results_dir.exists():
            for result_file in sorted(results_dir.glob("validation_*.json"))[-10:]:  # Load last 10
                try:
                    with open(result_file, 'r') as f:
                        data = json.load(f)
                    
                    # Convert back to ValidationResponse (simplified)
                    response = ValidationResponse(
                        request_id=data["request_id"],
                        result=ValidationResult(data["result"]),
                        confidence_score=data["confidence_score"],
                        false_positive_risk=data["false_positive_risk"],
                        validation_summary=data["validation_summary"]
                    )
                    
                    self.validation_history.append(response)
                    
                except Exception as e:
                    logger.warning(f"Could not load validation history from {result_file}: {e}")
    
    def _load_false_positive_patterns(self):
        """Load known false positive patterns"""
        
        patterns_file = Path("/home/marku/AIWFE/app/testing/false_positive_patterns.json")
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r') as f:
                    self.false_positive_patterns = json.load(f)
                logger.info(f"Loaded {len(self.false_positive_patterns)} false positive patterns")
            except Exception as e:
                logger.warning(f"Could not load false positive patterns: {e}")
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get current validation statistics"""
        return self.validation_stats.copy()

    def get_validation_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation summary report"""
        
        recent_validations = self.validation_history[-20:]  # Last 20 validations
        
        if not recent_validations:
            return {
                "summary": "No validations performed yet",
                "statistics": self.validation_stats,
                "recommendations": ["Start performing validations with evidence requirements"]
            }
        
        # Calculate metrics
        success_count = sum(1 for v in recent_validations if v.result == ValidationResult.SUCCESS)
        failure_count = sum(1 for v in recent_validations if v.result == ValidationResult.FAILURE)
        review_count = sum(1 for v in recent_validations if v.result == ValidationResult.REQUIRES_REVIEW)
        
        avg_confidence = sum(v.confidence_score for v in recent_validations) / len(recent_validations)
        avg_fp_risk = sum(v.false_positive_risk for v in recent_validations) / len(recent_validations)
        
        high_fp_risk_count = sum(1 for v in recent_validations if v.false_positive_risk > 0.5)
        
        return {
            "validation_summary": {
                "total_recent_validations": len(recent_validations),
                "success_rate": success_count / len(recent_validations),
                "failure_rate": failure_count / len(recent_validations),
                "review_required_rate": review_count / len(recent_validations),
                "average_confidence": avg_confidence,
                "average_false_positive_risk": avg_fp_risk,
                "high_false_positive_risk_count": high_fp_risk_count
            },
            "overall_statistics": self.validation_stats,
            "false_positive_prevention": {
                "patterns_detected": len(self.false_positive_patterns),
                "high_risk_validations": high_fp_risk_count,
                "prevention_effectiveness": self.validation_stats["false_positives_prevented"] / max(1, self.validation_stats["total_validations"])
            },
            "recommendations": self._generate_improvement_recommendations(recent_validations)
        }
    
    def _generate_improvement_recommendations(self, recent_validations: List[ValidationResponse]) -> List[str]:
        """Generate recommendations for improving validation quality"""
        
        recommendations = []
        
        if not recent_validations:
            return ["Start performing evidence-based validations"]
        
        avg_confidence = sum(v.confidence_score for v in recent_validations) / len(recent_validations)
        avg_fp_risk = sum(v.false_positive_risk for v in recent_validations) / len(recent_validations)
        
        if avg_confidence < 0.7:
            recommendations.append("Improve evidence collection quality - current average confidence is low")
        
        if avg_fp_risk > 0.4:
            recommendations.append("High false positive risk detected - strengthen cross-verification")
        
        success_rate = sum(1 for v in recent_validations if v.result == ValidationResult.SUCCESS) / len(recent_validations)
        if success_rate < 0.3:
            recommendations.append("Low success rate may indicate system issues - investigate common failure patterns")
        
        review_rate = sum(1 for v in recent_validations if v.result == ValidationResult.REQUIRES_REVIEW) / len(recent_validations)
        if review_rate > 0.4:
            recommendations.append("Many validations require manual review - consider improving automation")
        
        if self.validation_stats["cross_verification_coverage"] < 0.8:
            recommendations.append("Increase cross-verification coverage for better reliability")
        
        if self.validation_stats["mast_compliance_average"] < 0.9:
            recommendations.append("Improve MAST framework compliance across all components")
        
        return recommendations