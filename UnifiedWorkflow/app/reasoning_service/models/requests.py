"""Request models for the Reasoning Service API."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class Evidence(BaseModel):
    """Evidence item for reasoning and validation."""
    
    content: str = Field(..., description="Evidence content or description")
    source: Optional[str] = Field(None, description="Source of the evidence")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Source confidence")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "content": "Temperature readings show consistent increase over 20 years",
                "source": "Climate monitoring station dataset",
                "confidence": 0.95,
                "metadata": {"station_id": "US-001", "measurement_type": "surface_temperature"}
            }
        }


class EvidenceValidationRequest(BaseModel):
    """Request for evidence-based validation with >85% accuracy requirement."""
    
    evidence: List[Evidence] = Field(..., min_items=1, description="Evidence items to validate")
    context: Optional[str] = Field(None, description="Context for evidence evaluation")
    validation_criteria: Optional[List[str]] = Field(
        default=None,
        description="Specific criteria for validation (source credibility, consistency, etc.)"
    )
    require_high_confidence: bool = Field(
        default=True,
        description="Require >85% confidence for validation"
    )
    
    @validator("evidence")
    def evidence_not_empty(cls, v):
        if not v:
            raise ValueError("At least one evidence item is required")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "evidence": [
                    {
                        "content": "Multiple peer-reviewed studies show correlation",
                        "source": "Academic research database",
                        "confidence": 0.9
                    }
                ],
                "context": "Evaluating research findings for policy decisions",
                "validation_criteria": ["peer_review", "sample_size", "statistical_significance"],
                "require_high_confidence": True
            }
        }


class DecisionCriteria(BaseModel):
    """Criteria for multi-criteria decision analysis."""
    
    name: str = Field(..., description="Criterion name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Relative importance weight")
    description: Optional[str] = Field(None, description="Criterion description")
    measurement_type: str = Field(default="numeric", description="Type of measurement (numeric, categorical, boolean)")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Cost Effectiveness",
                "weight": 0.3,
                "description": "Total cost relative to expected benefits",
                "measurement_type": "numeric"
            }
        }


class DecisionOption(BaseModel):
    """Option for multi-criteria decision analysis."""
    
    name: str = Field(..., description="Option name")
    description: Optional[str] = Field(None, description="Option description") 
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Option attributes for evaluation")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Option A",
                "description": "Conservative approach with proven results",
                "attributes": {
                    "cost": 10000,
                    "risk_level": "low", 
                    "implementation_time": 6
                }
            }
        }


class MultiCriteriaDecisionRequest(BaseModel):
    """Request for multi-criteria decision making with confidence scoring."""
    
    context: str = Field(..., description="Decision context and background")
    options: List[DecisionOption] = Field(..., min_items=2, description="Decision options to evaluate")
    criteria: List[DecisionCriteria] = Field(..., min_items=1, description="Decision criteria")
    additional_constraints: Optional[List[str]] = Field(
        default=None,
        description="Additional constraints or requirements"
    )
    
    @validator("options")
    def options_minimum(cls, v):
        if len(v) < 2:
            raise ValueError("At least two options required for decision analysis")
        return v
    
    @validator("criteria")
    def criteria_weights_sum(cls, v):
        total_weight = sum(criterion.weight for criterion in v)
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating-point errors
            raise ValueError("Criteria weights must sum to 1.0")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "context": "Selecting software architecture for new system",
                "options": [
                    {
                        "name": "Microservices",
                        "description": "Distributed microservices architecture",
                        "attributes": {"complexity": 8, "scalability": 9, "cost": 7}
                    },
                    {
                        "name": "Monolith",
                        "description": "Traditional monolithic architecture", 
                        "attributes": {"complexity": 4, "scalability": 5, "cost": 3}
                    }
                ],
                "criteria": [
                    {"name": "Complexity", "weight": 0.3, "measurement_type": "numeric"},
                    {"name": "Scalability", "weight": 0.4, "measurement_type": "numeric"},
                    {"name": "Cost", "weight": 0.3, "measurement_type": "numeric"}
                ]
            }
        }


class HypothesisTestingRequest(BaseModel):
    """Request for reality testing with evidence validation."""
    
    hypothesis: str = Field(..., description="Hypothesis to test")
    evidence: List[Evidence] = Field(..., min_items=1, description="Evidence for testing")
    context: Optional[str] = Field(None, description="Context for hypothesis testing")
    significance_level: float = Field(
        default=0.05,
        ge=0.001, 
        le=0.1,
        description="Statistical significance level"
    )
    alternative_hypotheses: Optional[List[str]] = Field(
        default=None,
        description="Alternative hypotheses to consider"
    )
    
    @validator("evidence")
    def evidence_not_empty(cls, v):
        if not v:
            raise ValueError("At least one evidence item is required for hypothesis testing")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "hypothesis": "New feature will increase user engagement by 15%",
                "evidence": [
                    {
                        "content": "A/B test results show 12% increase in session duration",
                        "source": "Analytics platform",
                        "confidence": 0.88
                    }
                ],
                "context": "Product feature evaluation",
                "significance_level": 0.05,
                "alternative_hypotheses": [
                    "Feature has no significant impact on engagement",
                    "Feature decreases engagement due to complexity"
                ]
            }
        }


class ReasoningStep(BaseModel):
    """Individual step in a reasoning chain."""
    
    step_number: int = Field(..., ge=1, description="Step number in sequence")
    premise: str = Field(..., description="Starting premise for this step")
    inference: str = Field(..., description="Logical inference made")
    conclusion: str = Field(..., description="Conclusion from this step")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in this step")
    
    class Config:
        schema_extra = {
            "example": {
                "step_number": 1,
                "premise": "All observed ravens are black",
                "inference": "Inductive generalization from sample",
                "conclusion": "Ravens are likely to be black",
                "confidence": 0.8
            }
        }


class ReasoningChainRequest(BaseModel):
    """Request for multi-step reasoning chain processing."""
    
    initial_premise: str = Field(..., description="Starting premise for reasoning")
    goal: str = Field(..., description="Desired conclusion or goal")
    context: Optional[str] = Field(None, description="Context for reasoning")
    max_steps: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of reasoning steps"
    )
    reasoning_type: str = Field(
        default="deductive",
        description="Type of reasoning (deductive, inductive, abductive)"
    )
    evidence: Optional[List[Evidence]] = Field(
        default=None,
        description="Supporting evidence for reasoning"
    )
    
    @validator("reasoning_type")
    def valid_reasoning_type(cls, v):
        valid_types = {"deductive", "inductive", "abductive", "mixed"}
        if v not in valid_types:
            raise ValueError(f"Reasoning type must be one of {valid_types}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "initial_premise": "System shows high CPU usage and memory leaks",
                "goal": "Determine root cause and solution",
                "context": "Production system debugging",
                "max_steps": 8,
                "reasoning_type": "abductive",
                "evidence": [
                    {
                        "content": "Memory usage increases linearly over time",
                        "source": "System monitoring",
                        "confidence": 0.95
                    }
                ]
            }
        }