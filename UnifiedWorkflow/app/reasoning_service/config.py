"""Configuration management for the Reasoning Service.

Follows Phase 1 patterns with structured settings, environment variable support,
and production-ready defaults for cognitive architecture integration.
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ReasoningSettings(BaseSettings):
    """Reasoning Service configuration with cognitive architecture integration."""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="REASONING_HOST")
    port: int = Field(default=8005, alias="REASONING_PORT")
    debug: bool = Field(default=False, alias="REASONING_DEBUG")
    log_level: str = Field(default="INFO", alias="REASONING_LOG_LEVEL")
    
    # Database Configuration - Uses shared AI Workflow DB
    database_url: str = Field(
        default=os.getenv("DATABASE_URL", "postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db"),
        alias="REASONING_DATABASE_URL",
        description="PostgreSQL database URL - uses shared AI Workflow database"
    )
    database_pool_size: int = Field(default=10, alias="REASONING_DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="REASONING_DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, alias="REASONING_DATABASE_POOL_TIMEOUT")
    
    # Redis Configuration for Cognitive State Management - Uses shared Redis with authentication
    redis_host: str = Field(default=os.getenv("REDIS_HOST", "redis"), alias="REDIS_HOST")
    redis_port: int = Field(default=int(os.getenv("REDIS_PORT", "6379")), alias="REDIS_PORT")
    redis_db: int = Field(default=int(os.getenv("REDIS_DB", "3")), alias="REDIS_DB")
    redis_user: str = Field(default=os.getenv("REDIS_USER", "lwe-app"), alias="REDIS_USER")
    redis_password: Optional[str] = Field(default=os.getenv("REDIS_PASSWORD", None), alias="REDIS_PASSWORD")
    
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components with proper URL encoding."""
        if self.redis_password:
            from urllib.parse import quote_plus
            password = quote_plus(self.redis_password)
            return f"redis://{self.redis_user}:{password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    redis_timeout: int = Field(default=5, alias="REASONING_REDIS_TIMEOUT")
    redis_max_connections: int = Field(default=20, alias="REASONING_REDIS_MAX_CONNECTIONS")
    
    # Ollama Configuration
    ollama_url: str = Field(default="http://ollama:11434", alias="REASONING_OLLAMA_URL")
    ollama_model: str = Field(default="llama3.2:3b", alias="REASONING_OLLAMA_MODEL")
    ollama_timeout: int = Field(default=120, alias="REASONING_OLLAMA_TIMEOUT")
    ollama_max_retries: int = Field(default=3, alias="REASONING_OLLAMA_MAX_RETRIES")
    
    # Service Integration URLs
    hybrid_memory_url: str = Field(
        default="http://hybrid-memory-service:8002",
        alias="REASONING_HYBRID_MEMORY_URL"
    )
    perception_service_url: str = Field(
        default="http://perception-service:8001",
        alias="REASONING_PERCEPTION_SERVICE_URL"
    )
    coordination_service_url: str = Field(
        default="http://coordination-service:8004",
        alias="REASONING_COORDINATION_SERVICE_URL"
    )
    learning_service_url: str = Field(
        default="http://learning-service:8005",
        alias="REASONING_LEARNING_SERVICE_URL"
    )
    
    # Reasoning Configuration
    evidence_validation_threshold: float = Field(
        default=0.85,
        alias="REASONING_EVIDENCE_THRESHOLD",
        description="Minimum accuracy threshold for evidence validation (>85%)"
    )
    confidence_threshold: float = Field(
        default=0.7,
        alias="REASONING_CONFIDENCE_THRESHOLD",
        description="Minimum confidence score for reasoning outputs"
    )
    max_reasoning_steps: int = Field(
        default=10,
        alias="REASONING_MAX_STEPS",
        description="Maximum steps in reasoning chain"
    )
    max_chain_depth: int = Field(
        default=5,
        alias="REASONING_MAX_CHAIN_DEPTH",
        description="Maximum depth for recursive reasoning"
    )
    reality_testing_enabled: bool = Field(
        default=True,
        alias="REASONING_REALITY_TESTING_ENABLED"
    )
    
    # Performance Configuration
    max_concurrent_requests: int = Field(
        default=20,
        alias="REASONING_MAX_CONCURRENT_REQUESTS"
    )
    request_timeout: int = Field(
        default=30,
        alias="REASONING_REQUEST_TIMEOUT",
        description="Request timeout in seconds"
    )
    reasoning_timeout: int = Field(
        default=120,
        alias="REASONING_TIMEOUT",
        description="Max time for complex reasoning chains (2 minutes)"
    )
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="REASONING_CORS_ORIGINS"
    )
    
    # Security Configuration
    enable_mtls: bool = Field(default=False, alias="REASONING_ENABLE_MTLS")
    tls_cert_file: Optional[str] = Field(default=None, alias="REASONING_TLS_CERT_FILE")
    tls_key_file: Optional[str] = Field(default=None, alias="REASONING_TLS_KEY_FILE")
    api_key_header: str = Field(default="X-API-Key", alias="REASONING_API_KEY_HEADER")
    
    # Monitoring Configuration
    metrics_enabled: bool = Field(default=True, alias="REASONING_METRICS_ENABLED")
    health_check_interval: int = Field(default=30, alias="REASONING_HEALTH_CHECK_INTERVAL")
    
    # Cognitive Architecture Integration
    cognitive_event_routing: bool = Field(
        default=True,
        alias="REASONING_COGNITIVE_EVENT_ROUTING",
        description="Enable event-driven cognitive communication"
    )
    learning_feedback_enabled: bool = Field(
        default=True,
        alias="REASONING_LEARNING_FEEDBACK_ENABLED",
        description="Enable learning feedback loops"
    )
    
    # Reasoning Prompts
    evidence_validation_prompt: str = Field(
        default="""Analyze the following evidence and determine its validity and reliability.
        
Consider:
1. Source credibility and verification methods
2. Consistency with known facts and logical principles
3. Supporting documentation and cross-references
4. Potential biases, conflicts of interest, or limitations
5. Statistical significance and sample size (if applicable)

Evidence to evaluate:
{evidence}

Provide your assessment as a structured analysis with:
- Validity score (0.0-1.0)
- Reliability assessment
- Key strengths and weaknesses
- Confidence level in your assessment
- Recommendations for additional validation if needed

Be thorough but concise. Focus on factual analysis over speculation.""",
        alias="REASONING_EVIDENCE_VALIDATION_PROMPT"
    )
    
    hypothesis_testing_prompt: str = Field(
        default="""Test the following hypothesis against available evidence and logical reasoning.

Hypothesis: {hypothesis}

Evidence provided: {evidence}

Context: {context}

Perform systematic hypothesis testing:
1. Define testable predictions from the hypothesis
2. Evaluate evidence that supports or contradicts the hypothesis
3. Consider alternative explanations for the observed evidence
4. Assess the strength of the evidence and potential confounding factors
5. Determine if the hypothesis should be accepted, rejected, or requires modification

Provide your analysis with:
- Test result (supported/not supported/inconclusive)
- Confidence score (0.0-1.0)
- Key supporting and contradicting evidence
- Alternative hypotheses to consider
- Recommendations for further testing""",
        alias="REASONING_HYPOTHESIS_TESTING_PROMPT"
    )
    
    multi_criteria_decision_prompt: str = Field(
        default="""Analyze the following decision scenario using multi-criteria decision analysis.

Decision context: {context}
Options: {options}
Criteria: {criteria}
Weights: {weights}

For each option, evaluate:
1. Performance against each criterion
2. Trade-offs and opportunity costs
3. Risk factors and uncertainty levels
4. Implementation feasibility
5. Long-term implications

Provide:
- Scored evaluation matrix
- Overall recommendation with rationale
- Confidence level in recommendation
- Sensitivity analysis for key assumptions
- Risk mitigation strategies for recommended option""",
        alias="REASONING_MULTI_CRITERIA_DECISION_PROMPT"
    )
    
    reasoning_chain_prompt: str = Field(
        default="""Process this multi-step reasoning chain with logical rigor.

Initial premise: {premise}
Goal: {goal}
Context: {context}

For each reasoning step:
1. State the logical connection clearly
2. Identify assumptions being made
3. Evaluate the strength of the inference
4. Consider alternative paths or contradictory evidence
5. Maintain logical consistency throughout

Build the reasoning chain step by step, ensuring:
- Each step follows logically from the previous
- Assumptions are explicitly stated and justified
- Evidence is properly weighted and evaluated
- Alternative conclusions are considered
- Final conclusion is well-supported

Provide:
- Step-by-step reasoning chain
- Confidence assessment for each step
- Overall conclusion with confidence score
- Key assumptions and their impact
- Areas requiring additional evidence or validation""",
        alias="REASONING_REASONING_CHAIN_PROMPT"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8", 
        "case_sensitive": False
    }
        
    @field_validator("evidence_validation_threshold")
    @classmethod
    def validate_evidence_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Evidence validation threshold must be between 0.0 and 1.0")
        if v < 0.85:
            raise ValueError("Evidence validation threshold must be >= 0.85 for Phase 2 requirements")
        return v
        
    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        return v
        
    @field_validator("max_reasoning_steps")
    @classmethod
    def validate_max_reasoning_steps(cls, v):
        if v < 1 or v > 50:
            raise ValueError("Max reasoning steps must be between 1 and 50")
        return v
        
    @field_validator("cors_origins", mode="before")
    @classmethod  
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache()
def get_settings() -> ReasoningSettings:
    """Get cached reasoning service settings."""
    return ReasoningSettings()