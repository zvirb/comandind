"""
Agent Configuration Models - Database models for per-agent LLM and GPU configuration
Supports the Helios Multi-Agent framework's Agent Abstraction Layer with heterogeneous LLM assignments.
"""

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Enum as SQLAlchemyEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from shared.utils.database_setup import Base


class LLMProvider(str, enum.Enum):
    """Supported LLM providers for agent configuration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    GOOGLE = "google"
    OLLAMA = "ollama"


class AgentType(str, enum.Enum):
    """Predefined agent types in the Helios framework."""
    PROJECT_MANAGER = "project_manager"
    RESEARCH_SPECIALIST = "research_specialist"
    BUSINESS_ANALYST = "business_analyst"
    TECHNICAL_EXPERT = "technical_expert"
    FINANCIAL_ADVISOR = "financial_advisor"
    CREATIVE_DIRECTOR = "creative_director"
    QUALITY_ASSURANCE = "quality_assurance"
    DATA_SCIENTIST = "data_scientist"
    PERSONAL_ASSISTANT = "personal_assistant"
    LEGAL_ADVISOR = "legal_advisor"
    MARKETING_SPECIALIST = "marketing_specialist"
    OPERATIONS_MANAGER = "operations_manager"


class GPUAssignmentStrategy(str, enum.Enum):
    """GPU assignment strategies for agent resource allocation."""
    EXCLUSIVE = "exclusive"  # Agent gets dedicated GPU
    SHARED = "shared"       # Agent shares GPU with others
    AUTO = "auto"          # System automatically assigns based on load
    NONE = "none"          # Agent uses CPU-only inference


class ModelLoadStrategy(str, enum.Enum):
    """Model loading strategies for performance optimization."""
    PRELOAD = "preload"     # Keep model loaded at all times
    ON_DEMAND = "on_demand" # Load model when needed
    SHARED = "shared"       # Share loaded model instance with other agents


class LegacyAgentConfiguration(Base):
    """
    LEGACY: Agent configuration for heterogeneous LLM assignments and GPU resource allocation.
    
    This model is being phased out in favor of the Helios Multi-Agent AgentConfiguration.
    Enables per-agent customization of model selection, performance tuning, and resource usage.
    """
    __tablename__ = "legacy_agent_configurations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Agent Identification
    agent_type: Mapped[AgentType] = mapped_column(SQLAlchemyEnum(AgentType), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # LLM Configuration
    llm_provider: Mapped[LLMProvider] = mapped_column(SQLAlchemyEnum(LLMProvider), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # GPU Resource Configuration
    gpu_assignment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0, 1, 2 for RTX Titan X GPUs
    gpu_assignment_strategy: Mapped[GPUAssignmentStrategy] = mapped_column(
        SQLAlchemyEnum(GPUAssignmentStrategy), 
        default=GPUAssignmentStrategy.AUTO, 
        nullable=False
    )
    model_load_strategy: Mapped[ModelLoadStrategy] = mapped_column(
        SQLAlchemyEnum(ModelLoadStrategy), 
        default=ModelLoadStrategy.ON_DEMAND, 
        nullable=False
    )
    
    # Performance Configuration
    max_context_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.7)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=300)
    
    # Agent Behavior Configuration
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    capabilities: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    constraints: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Resource Limits
    memory_limit_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_budget_per_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_concurrent_requests: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    
    # Status and Control
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 1-10 scale
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Foreign Keys
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    
    # Relationships
    created_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="legacy_agent_configurations")
    agent_metrics: Mapped[List["LegacyAgentMetrics"]] = relationship("LegacyAgentMetrics", back_populates="agent_config")
    
    def __repr__(self):
        return f"<LegacyAgentConfiguration(agent_type={self.agent_type}, model={self.model_name}, gpu={self.gpu_assignment})>"


class LegacyAgentMetrics(Base):
    """
    LEGACY: Performance metrics and usage tracking for agent configurations.
    Enables monitoring, optimization, and cost analysis of agent resource usage.
    """
    __tablename__ = "legacy_agent_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Agent Configuration Reference
    agent_config_id: Mapped[int] = mapped_column(
        ForeignKey("legacy_agent_configurations.id"), nullable=False, index=True
    )
    
    # Usage Metrics
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Performance Metrics
    average_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success_rate_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Resource Metrics
    gpu_memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Cost Metrics (if applicable)
    estimated_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Time Period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    # Relationships
    agent_config: Mapped["LegacyAgentConfiguration"] = relationship("LegacyAgentConfiguration", back_populates="agent_metrics")
    
    def __repr__(self):
        return f"<LegacyAgentMetrics(agent_config_id={self.agent_config_id}, requests={self.total_requests}, tokens={self.total_tokens_consumed})>"


class LegacyGPUResourceAllocation(Base):
    """
    LEGACY: GPU resource allocation tracking for the 3x RTX Titan X GPU setup.
    Manages GPU assignment, memory allocation, and load balancing across agents.
    """
    __tablename__ = "legacy_gpu_resource_allocations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # GPU Identification
    gpu_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0, 1, 2
    gpu_name: Mapped[str] = mapped_column(String(255), nullable=False)  # "RTX Titan X"
    gpu_memory_total_mb: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Current Allocation
    allocated_memory_mb: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    available_memory_mb: Mapped[float] = mapped_column(Float, nullable=False)
    active_agent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Performance Tracking
    utilization_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature_celsius: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    power_draw_watts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Status
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    def __repr__(self):
        return f"<LegacyGPUResourceAllocation(gpu_id={self.gpu_id}, allocated={self.allocated_memory_mb}MB, agents={self.active_agent_count})>"


class LegacyModelInstance(Base):
    """
    LEGACY: Loaded model instance tracking for memory optimization and sharing.
    Tracks which models are loaded on which GPUs and their usage patterns.
    """
    __tablename__ = "legacy_model_instances"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Model Information
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_provider: Mapped[LLMProvider] = mapped_column(SQLAlchemyEnum(LLMProvider), nullable=False)
    model_size_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # GPU Assignment
    gpu_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    memory_allocated_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Usage Tracking
    reference_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    load_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    is_loaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    load_strategy: Mapped[ModelLoadStrategy] = mapped_column(
        SQLAlchemyEnum(ModelLoadStrategy), 
        default=ModelLoadStrategy.ON_DEMAND, 
        nullable=False
    )
    
    # Timestamps
    loaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    
    def __repr__(self):
        return f"<LegacyModelInstance(model={self.model_name}, gpu_id={self.gpu_id}, loaded={self.is_loaded})>"