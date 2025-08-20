#!/usr/bin/env python3
"""
Enhanced Knowledge Graph System v2.0
Evidence-based pattern storage and retrieval for orchestration workflows
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class PatternType(Enum):
    AUTHENTICATION_FAILURE = "authentication_failure"
    API_ENDPOINT_FAILURE = "api_endpoint_failure"  
    UI_FUNCTIONALITY_FAILURE = "ui_functionality_failure"
    CROSS_ENVIRONMENT_DRIFT = "cross_environment_drift"
    FALSE_POSITIVE_SUCCESS = "false_positive_success"
    VALIDATION_GAP = "validation_gap"
    SUCCESS_IMPLEMENTATION = "success_implementation"

class FailureCategory(Enum):
    TECHNICAL_SUCCESS_USER_FAILURE = "technical_success_user_failure"
    ENVIRONMENT_SPECIFIC = "environment_specific"
    TIMING_DEPENDENT = "timing_dependent"
    VALIDATION_INSUFFICIENT = "validation_insufficient"
    INTEGRATION_BREAKDOWN = "integration_breakdown"

@dataclass
class FailurePattern:
    """Comprehensive failure pattern documentation"""
    id: str
    pattern_type: PatternType
    category: FailureCategory
    description: str
    symptoms: List[str]
    root_causes: List[str]
    false_positive_indicators: List[str]
    actual_user_impact: List[str]
    environments_affected: List[str]
    fix_attempts: List[Dict[str, Any]]
    successful_resolution: Optional[Dict[str, Any]]
    occurrence_count: int
    first_occurrence: str
    last_occurrence: str
    agent_claims_vs_reality: Dict[str, Any]
    evidence_quality_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass 
class SuccessPattern:
    """Documented successful implementations"""
    id: str
    pattern_type: str
    description: str
    implementation_steps: List[str]
    validation_evidence: List[str]
    replication_requirements: List[str]
    environments_tested: List[str]
    user_functionality_verified: List[str]
    cross_validation_agents: List[str]
    evidence_quality_score: float
    reproduction_success_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ValidationGap:
    """Documented validation methodology gaps"""
    id: str
    gap_type: str
    description: str
    missed_scenarios: List[str]
    improvement_recommendations: List[str]
    affected_workflows: List[str]
    detection_method: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class EnhancedKnowledgeGraph:
    """Enhanced knowledge graph with pattern recognition and validation"""
    
    def __init__(self, storage_path: str = "/home/marku/ai_workflow_engine/.claude/knowledge"):
        self.storage_path = storage_path
        self.failure_patterns: Dict[str, FailurePattern] = {}
        self.success_patterns: Dict[str, SuccessPattern] = {}
        self.validation_gaps: Dict[str, ValidationGap] = {}
        self.load_patterns()
    
    def generate_pattern_id(self, description: str, timestamp: str) -> str:
        """Generate unique pattern ID"""
        content = f"{description}-{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def store_failure_pattern(self, 
                            pattern_type: PatternType,
                            category: FailureCategory,
                            description: str,
                            symptoms: List[str],
                            root_causes: List[str],
                            false_positive_indicators: List[str],
                            actual_user_impact: List[str],
                            environments_affected: List[str],
                            agent_claims: Dict[str, Any],
                            evidence_quality_score: float) -> str:
        """Store a new failure pattern"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        pattern_id = self.generate_pattern_id(description, timestamp)
        
        # Check if similar pattern exists
        existing_pattern = self.find_similar_failure_pattern(symptoms, root_causes)
        if existing_pattern:
            # Update existing pattern
            existing_pattern.occurrence_count += 1
            existing_pattern.last_occurrence = timestamp
            existing_pattern.fix_attempts.append({
                "timestamp": timestamp,
                "agent_claims": agent_claims,
                "evidence_score": evidence_quality_score
            })
            pattern_id = existing_pattern.id
        else:
            # Create new pattern
            pattern = FailurePattern(
                id=pattern_id,
                pattern_type=pattern_type,
                category=category,
                description=description,
                symptoms=symptoms,
                root_causes=root_causes,
                false_positive_indicators=false_positive_indicators,
                actual_user_impact=actual_user_impact,
                environments_affected=environments_affected,
                fix_attempts=[{
                    "timestamp": timestamp,
                    "agent_claims": agent_claims,
                    "evidence_score": evidence_quality_score
                }],
                successful_resolution=None,
                occurrence_count=1,
                first_occurrence=timestamp,
                last_occurrence=timestamp,
                agent_claims_vs_reality=agent_claims,
                evidence_quality_score=evidence_quality_score
            )
            self.failure_patterns[pattern_id] = pattern
        
        self.save_patterns()
        return pattern_id
    
    def store_success_pattern(self,
                            pattern_type: str,
                            description: str,
                            implementation_steps: List[str],
                            validation_evidence: List[str],
                            user_functionality_verified: List[str],
                            cross_validation_agents: List[str],
                            evidence_quality_score: float) -> str:
        """Store a successful implementation pattern"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        pattern_id = self.generate_pattern_id(description, timestamp)
        
        pattern = SuccessPattern(
            id=pattern_id,
            pattern_type=pattern_type,
            description=description,
            implementation_steps=implementation_steps,
            validation_evidence=validation_evidence,
            replication_requirements=[],
            environments_tested=["production", "development"],
            user_functionality_verified=user_functionality_verified,
            cross_validation_agents=cross_validation_agents,
            evidence_quality_score=evidence_quality_score,
            reproduction_success_rate=1.0
        )
        
        self.success_patterns[pattern_id] = pattern
        self.save_patterns()
        return pattern_id
    
    def query_failure_patterns(self, 
                              symptoms: List[str] = None,
                              pattern_type: PatternType = None,
                              environment: str = None) -> List[FailurePattern]:
        """Query failure patterns by various criteria"""
        
        results = []
        for pattern in self.failure_patterns.values():
            match = True
            
            if pattern_type and pattern.pattern_type != pattern_type:
                match = False
            
            if environment and environment not in pattern.environments_affected:
                match = False
                
            if symptoms:
                symptom_match = any(
                    any(symptom.lower() in existing_symptom.lower() 
                        for existing_symptom in pattern.symptoms)
                    for symptom in symptoms
                )
                if not symptom_match:
                    match = False
            
            if match:
                results.append(pattern)
        
        # Sort by occurrence count and recency
        results.sort(key=lambda p: (p.occurrence_count, p.last_occurrence), reverse=True)
        return results
    
    def query_success_patterns(self, pattern_type: str = None) -> List[SuccessPattern]:
        """Query successful implementation patterns"""
        
        results = []
        for pattern in self.success_patterns.values():
            if pattern_type is None or pattern.pattern_type == pattern_type:
                results.append(pattern)
        
        # Sort by evidence quality and success rate
        results.sort(key=lambda p: (p.evidence_quality_score, p.reproduction_success_rate), reverse=True)
        return results
    
    def find_similar_failure_pattern(self, symptoms: List[str], root_causes: List[str]) -> Optional[FailurePattern]:
        """Find existing similar failure patterns"""
        
        for pattern in self.failure_patterns.values():
            symptom_overlap = len(set(symptoms) & set(pattern.symptoms))
            cause_overlap = len(set(root_causes) & set(pattern.root_causes))
            
            if symptom_overlap >= 2 or cause_overlap >= 1:
                return pattern
        
        return None
    
    def identify_validation_gaps(self, 
                               agent_claims: Dict[str, Any],
                               actual_outcomes: Dict[str, Any]) -> List[str]:
        """Identify gaps in validation methodology"""
        
        gaps = []
        
        for claim, claimed_result in agent_claims.items():
            actual_result = actual_outcomes.get(claim)
            
            if claimed_result and not actual_result:
                gaps.append(f"Agent claimed success for {claim} but actual validation failed")
            
            if claimed_result == "working" and actual_result == "failed":
                gaps.append(f"Technical success reported for {claim} but user functionality failed")
        
        return gaps
    
    def store_validation_gap(self, 
                           gap_type: str,
                           description: str,
                           missed_scenarios: List[str],
                           improvement_recommendations: List[str],
                           affected_workflows: List[str]) -> str:
        """Store identified validation gap"""
        
        timestamp = datetime.now(timezone.utc).isoformat()
        gap_id = self.generate_pattern_id(description, timestamp)
        
        gap = ValidationGap(
            id=gap_id,
            gap_type=gap_type,
            description=description,
            missed_scenarios=missed_scenarios,
            improvement_recommendations=improvement_recommendations,
            affected_workflows=affected_workflows,
            detection_method="orchestration_audit_v2"
        )
        
        self.validation_gaps[gap_id] = gap
        self.save_patterns()
        return gap_id
    
    def get_orchestration_recommendations(self, 
                                        current_symptoms: List[str],
                                        environment: str = "production") -> Dict[str, Any]:
        """Get recommendations based on historical patterns"""
        
        # Find similar past failures
        similar_failures = self.query_failure_patterns(symptoms=current_symptoms, environment=environment)
        
        # Find successful patterns in similar domains
        success_patterns = self.query_success_patterns()
        
        recommendations = {
            "similar_past_failures": len(similar_failures),
            "high_risk_patterns": [
                p.description for p in similar_failures 
                if p.occurrence_count >= 3 and p.successful_resolution is None
            ],
            "validation_requirements": [],
            "evidence_collection_priority": [],
            "cross_validation_agents": []
        }
        
        # Generate specific recommendations
        if similar_failures:
            most_common = similar_failures[0]
            recommendations["validation_requirements"] = [
                f"Test specifically for: {symptom}" for symptom in most_common.symptoms
            ]
            recommendations["evidence_collection_priority"] = most_common.actual_user_impact
            
            # Identify validation gaps from past failures
            for failure in similar_failures[:3]:  # Top 3 similar failures
                for indicator in failure.false_positive_indicators:
                    recommendations["validation_requirements"].append(
                        f"Avoid false positive: {indicator}"
                    )
        
        # Add successful pattern insights
        if success_patterns:
            best_success = success_patterns[0]
            recommendations["cross_validation_agents"] = best_success.cross_validation_agents
            recommendations["evidence_collection_priority"].extend(
                best_success.user_functionality_verified
            )
        
        return recommendations
    
    def save_patterns(self):
        """Save patterns to persistent storage"""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save failure patterns with enum serialization
        failure_data = {}
        for pattern_id, pattern in self.failure_patterns.items():
            pattern_dict = pattern.to_dict()
            # Convert enums to string values for JSON serialization
            pattern_dict["pattern_type"] = pattern_dict["pattern_type"].value
            pattern_dict["category"] = pattern_dict["category"].value
            failure_data[pattern_id] = pattern_dict
        
        with open(f"{self.storage_path}/failure_patterns.json", "w") as f:
            json.dump(failure_data, f, indent=2)
        
        # Save success patterns  
        success_data = {
            pattern_id: pattern.to_dict()
            for pattern_id, pattern in self.success_patterns.items()
        }
        with open(f"{self.storage_path}/success_patterns.json", "w") as f:
            json.dump(success_data, f, indent=2)
        
        # Save validation gaps
        gap_data = {
            gap_id: gap.to_dict()
            for gap_id, gap in self.validation_gaps.items()
        }
        with open(f"{self.storage_path}/validation_gaps.json", "w") as f:
            json.dump(gap_data, f, indent=2)
    
    def load_patterns(self):
        """Load patterns from persistent storage"""
        import os
        
        # Load failure patterns
        failure_path = f"{self.storage_path}/failure_patterns.json"
        if os.path.exists(failure_path):
            with open(failure_path, "r") as f:
                data = json.load(f)
                for pattern_id, pattern_data in data.items():
                    pattern_data["pattern_type"] = PatternType(pattern_data["pattern_type"])
                    pattern_data["category"] = FailureCategory(pattern_data["category"])
                    self.failure_patterns[pattern_id] = FailurePattern(**pattern_data)
        
        # Load success patterns
        success_path = f"{self.storage_path}/success_patterns.json"
        if os.path.exists(success_path):
            with open(success_path, "r") as f:
                data = json.load(f)
                for pattern_id, pattern_data in data.items():
                    self.success_patterns[pattern_id] = SuccessPattern(**pattern_data)
        
        # Load validation gaps
        gap_path = f"{self.storage_path}/validation_gaps.json"
        if os.path.exists(gap_path):
            with open(gap_path, "r") as f:
                data = json.load(f)
                for gap_id, gap_data in data.items():
                    self.validation_gaps[gap_id] = ValidationGap(**gap_data)

# Example usage and testing
if __name__ == "__main__":
    kg = EnhancedKnowledgeGraph()
    
    # Store current CSRF failure pattern
    pattern_id = kg.store_failure_pattern(
        pattern_type=PatternType.AUTHENTICATION_FAILURE,
        category=FailureCategory.TECHNICAL_SUCCESS_USER_FAILURE,
        description="CSRF token validation fails for existing users but works for new registrations",
        symptoms=[
            "403 CSRF token validation failed",
            "New user registration and immediate login works", 
            "Existing users cannot log in",
            "CSRF endpoint returns 200 OK",
            "Token generation appears functional"
        ],
        root_causes=[
            "CSRF token synchronization between client and server",
            "Token rotation timing issues", 
            "Session state management problems"
        ],
        false_positive_indicators=[
            "CSRF endpoint returns 200 OK",
            "Token generation appears functional", 
            "Technical validation passes",
            "Health check endpoints working"
        ],
        actual_user_impact=[
            "User retention broken",
            "Existing users locked out", 
            "Registration required for access",
            "Business continuity impacted"
        ],
        environments_affected=["production", "development"],
        agent_claims={
            "ui_regression_debugger": "Authentication flows working",
            "backend_gateway_expert": "API endpoints operational", 
            "security_validator": "CSRF protection functional"
        },
        evidence_quality_score=0.3  # Low due to false positive validation
    )
    
    print(f"Stored failure pattern: {pattern_id}")
    
    # Query for similar patterns
    similar = kg.query_failure_patterns(
        symptoms=["CSRF token validation failed", "existing users cannot log in"]
    )
    
    print(f"Found {len(similar)} similar failure patterns")
    
    # Get recommendations
    recommendations = kg.get_orchestration_recommendations(
        current_symptoms=["authentication failure", "CSRF validation error"],
        environment="production"
    )
    
    print("Orchestration recommendations:")
    print(json.dumps(recommendations, indent=2))