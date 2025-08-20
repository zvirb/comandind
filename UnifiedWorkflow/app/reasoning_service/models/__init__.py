"""Models for the Reasoning Service."""

from .requests import (
    EvidenceValidationRequest,
    MultiCriteriaDecisionRequest,
    HypothesisTestingRequest,
    ReasoningChainRequest,
    DecisionCriteria,
    DecisionOption,
    ReasoningStep,
    Evidence
)

from .responses import (
    EvidenceValidationResponse,
    MultiCriteriaDecisionResponse,
    HypothesisTestingResponse,
    ReasoningChainResponse,
    HealthResponse,
    EvidenceAssessment,
    DecisionEvaluation,
    HypothesisResult,
    ReasoningChainResult
)

__all__ = [
    # Request models
    "EvidenceValidationRequest",
    "MultiCriteriaDecisionRequest", 
    "HypothesisTestingRequest",
    "ReasoningChainRequest",
    "DecisionCriteria",
    "DecisionOption",
    "ReasoningStep",
    "Evidence",
    
    # Response models
    "EvidenceValidationResponse",
    "MultiCriteriaDecisionResponse",
    "HypothesisTestingResponse", 
    "ReasoningChainResponse",
    "HealthResponse",
    "EvidenceAssessment",
    "DecisionEvaluation",
    "HypothesisResult",
    "ReasoningChainResult"
]