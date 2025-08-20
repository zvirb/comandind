"""Response models for the Reasoning Service API."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EvidenceAssessment(BaseModel):
    """Assessment result for individual evidence item."""
    
    evidence_id: str = Field(..., description="Unique identifier for evidence item")
    validity_score: float = Field(..., ge=0.0, le=1.0, description="Validity assessment (0.0-1.0)")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Reliability assessment (0.0-1.0)")
    strengths: List[str] = Field(default_factory=list, description="Key strengths identified")
    weaknesses: List[str] = Field(default_factory=list, description="Key weaknesses identified") 
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in assessment")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    
    class Config:
        schema_extra = {
            "example": {
                "evidence_id": "evidence_001",
                "validity_score": 0.89,
                "reliability_score": 0.92,
                "strengths": ["Peer-reviewed source", "Large sample size", "Replicated results"],
                "weaknesses": ["Limited geographic diversity", "Short observation period"],
                "confidence": 0.87,
                "recommendations": ["Extend observation period", "Include more diverse populations"]
            }
        }


class EvidenceValidationResponse(BaseModel):
    """Response for evidence validation with >85% accuracy requirement."""
    
    overall_validity: float = Field(..., ge=0.0, le=1.0, description="Overall validity score")
    meets_threshold: bool = Field(..., description="Whether evidence meets >85% threshold")
    assessments: List[EvidenceAssessment] = Field(..., description="Individual evidence assessments")
    summary: str = Field(..., description="Summary of validation results")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    validation_method: str = Field(..., description="Method used for validation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    
    class Config:
        schema_extra = {
            "example": {
                "overall_validity": 0.88,
                "meets_threshold": True,
                "assessments": [
                    {
                        "evidence_id": "evidence_001",
                        "validity_score": 0.88,
                        "reliability_score": 0.91,
                        "confidence": 0.86,
                        "strengths": ["Strong source credibility"],
                        "weaknesses": ["Limited timeframe"],
                        "recommendations": ["Extend data collection period"]
                    }
                ],
                "summary": "Evidence meets high-confidence validation threshold with strong source credibility",
                "processing_time_ms": 1250.5,
                "validation_method": "multi_criteria_analysis",
                "confidence_score": 0.87
            }
        }


class DecisionEvaluation(BaseModel):
    """Evaluation result for decision option."""
    
    option_name: str = Field(..., description="Name of evaluated option")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall weighted score")
    criteria_scores: Dict[str, float] = Field(..., description="Scores for each criterion")
    strengths: List[str] = Field(default_factory=list, description="Option strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Option weaknesses")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    implementation_considerations: List[str] = Field(
        default_factory=list,
        description="Implementation considerations"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "option_name": "Microservices Architecture",
                "overall_score": 0.78,
                "criteria_scores": {
                    "Scalability": 0.9,
                    "Complexity": 0.6,
                    "Cost": 0.7
                },
                "strengths": ["Excellent scalability", "Independent deployments"],
                "weaknesses": ["Higher initial complexity", "Operational overhead"],
                "risk_factors": ["Service communication complexity", "Distributed system challenges"],
                "implementation_considerations": ["Team expertise required", "Monitoring infrastructure needed"]
            }
        }


class MultiCriteriaDecisionResponse(BaseModel):
    """Response for multi-criteria decision making."""
    
    recommended_option: str = Field(..., description="Recommended option name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in recommendation")
    evaluations: List[DecisionEvaluation] = Field(..., description="All option evaluations")
    decision_rationale: str = Field(..., description="Rationale for recommendation")
    sensitivity_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sensitivity analysis results"
    )
    risk_mitigation: List[str] = Field(
        default_factory=list,
        description="Risk mitigation strategies"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    class Config:
        schema_extra = {
            "example": {
                "recommended_option": "Microservices Architecture",
                "confidence_score": 0.82,
                "evaluations": [
                    {
                        "option_name": "Microservices",
                        "overall_score": 0.78,
                        "criteria_scores": {"Scalability": 0.9, "Cost": 0.7},
                        "strengths": ["Scalable", "Flexible"],
                        "weaknesses": ["Complex"],
                        "risk_factors": ["Operational complexity"],
                        "implementation_considerations": ["Team training needed"]
                    }
                ],
                "decision_rationale": "Best balance of scalability and long-term benefits",
                "sensitivity_analysis": {"weight_changes": "Recommendation stable across ±15% weight variations"},
                "risk_mitigation": ["Gradual migration", "Invest in monitoring tools"],
                "processing_time_ms": 2150.3
            }
        }


class HypothesisResult(BaseModel):
    """Result of hypothesis testing."""
    
    test_result: str = Field(
        ...,
        description="Test result (supported, not_supported, inconclusive)"
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in result")
    p_value: Optional[float] = Field(None, description="Statistical p-value if applicable")
    effect_size: Optional[float] = Field(None, description="Effect size if applicable")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting the hypothesis"
    )
    contradicting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence contradicting the hypothesis"
    )
    alternative_hypotheses: List[str] = Field(
        default_factory=list,
        description="Alternative hypotheses to consider"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "test_result": "supported",
                "confidence_score": 0.87,
                "p_value": 0.023,
                "effect_size": 0.12,
                "supporting_evidence": ["A/B test shows positive results", "User feedback is positive"],
                "contradicting_evidence": ["Small sample size limitation"],
                "alternative_hypotheses": ["Effect may be temporary", "Results may not generalize"]
            }
        }


class HypothesisTestingResponse(BaseModel):
    """Response for hypothesis testing with reality validation."""
    
    hypothesis: str = Field(..., description="Original hypothesis tested")
    result: HypothesisResult = Field(..., description="Testing results")
    methodology: str = Field(..., description="Testing methodology used")
    evidence_analysis: str = Field(..., description="Analysis of provided evidence")
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for further testing"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    class Config:
        schema_extra = {
            "example": {
                "hypothesis": "New feature increases user engagement by 15%",
                "result": {
                    "test_result": "supported",
                    "confidence_score": 0.83,
                    "supporting_evidence": ["Positive A/B test results"],
                    "contradicting_evidence": ["Limited test duration"],
                    "alternative_hypotheses": ["Novelty effect may decline"]
                },
                "methodology": "Statistical analysis with Bayesian inference",
                "evidence_analysis": "Evidence shows consistent positive trend with statistical significance",
                "recommendations": ["Extend test duration", "Monitor long-term effects"],
                "processing_time_ms": 1875.2
            }
        }


class ReasoningChainResult(BaseModel):
    """Result of multi-step reasoning chain."""
    
    steps: List[Dict[str, Any]] = Field(..., description="Individual reasoning steps")
    final_conclusion: str = Field(..., description="Final conclusion reached")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    logical_consistency: float = Field(..., ge=0.0, le=1.0, description="Logical consistency score")
    key_assumptions: List[str] = Field(
        default_factory=list,
        description="Key assumptions made in reasoning"
    )
    potential_flaws: List[str] = Field(
        default_factory=list,
        description="Potential flaws or weaknesses identified"
    )
    alternative_paths: List[str] = Field(
        default_factory=list,
        description="Alternative reasoning paths considered"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "steps": [
                    {
                        "step": 1,
                        "premise": "System shows memory leaks",
                        "inference": "Memory not properly released",
                        "conclusion": "Code has resource management issues",
                        "confidence": 0.9
                    }
                ],
                "final_conclusion": "Root cause is improper resource disposal in async operations",
                "overall_confidence": 0.85,
                "logical_consistency": 0.92,
                "key_assumptions": ["Memory monitoring is accurate", "Code review findings are representative"],
                "potential_flaws": ["Limited sample of code reviewed"],
                "alternative_paths": ["Hardware issues", "Third-party library bugs"]
            }
        }


class ReasoningChainResponse(BaseModel):
    """Response for multi-step reasoning chain processing."""
    
    initial_premise: str = Field(..., description="Original premise")
    goal: str = Field(..., description="Reasoning goal")
    result: ReasoningChainResult = Field(..., description="Reasoning chain results")
    reasoning_type: str = Field(..., description="Type of reasoning used")
    validation_checks: List[str] = Field(
        default_factory=list,
        description="Validation checks performed"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    
    class Config:
        schema_extra = {
            "example": {
                "initial_premise": "System exhibits performance issues",
                "goal": "Identify root cause and solution",
                "result": {
                    "steps": [],
                    "final_conclusion": "Memory leak in async handler causing performance degradation",
                    "overall_confidence": 0.87,
                    "logical_consistency": 0.93,
                    "key_assumptions": ["Monitoring data is accurate"],
                    "potential_flaws": ["Limited test scenarios"],
                    "alternative_paths": ["Network bottlenecks", "Database issues"]
                },
                "reasoning_type": "abductive",
                "validation_checks": ["Logical consistency", "Evidence support", "Alternative consideration"],
                "processing_time_ms": 3200.7
            }
        }


class HealthResponse(BaseModel):
    """Health check response with cognitive capability status."""
    
    status: str = Field(..., description="Overall health status")
    timestamp: float = Field(..., description="Unix timestamp")
    checks: Dict[str, Any] = Field(..., description="Individual service checks")
    version: str = Field(..., description="Service version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime")
    cognitive_capabilities: Dict[str, bool] = Field(
        default_factory=dict,
        description="Status of cognitive capabilities"
    )
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Current performance metrics"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": 1672531200.0,
                "checks": {
                    "database": {"healthy": True, "latency_ms": 15.2},
                    "redis": {"healthy": True, "latency_ms": 2.1},
                    "ollama": {"healthy": True, "model_ready": True}
                },
                "version": "1.0.0",
                "uptime_seconds": 86400.0,
                "cognitive_capabilities": {
                    "evidence_validation": True,
                    "multi_criteria_decision": True,
                    "hypothesis_testing": True,
                    "reasoning_chains": True
                },
                "performance_metrics": {
                    "avg_response_time_ms": 1800.5,
                    "success_rate": 0.98,
                    "validation_accuracy": 0.89
                }
            }
        }