"""
Agent LLM Manager - Core service for the Agent Abstraction Layer
Manages per-agent LLM configurations, GPU resource allocation, and API normalization.
Enables heterogeneous LLM assignments across the 12 Helios Multi-Agent framework experts.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# TEMPORARILY DISABLED: Models don't exist yet due to incomplete migration
# from shared.database.models import (
#     AgentConfiguration, 
#     AgentMetrics, 
#     GPUResourceAllocation, 
#     ModelInstance,
#     LLMProvider, 
#     AgentType, 
#     GPUAssignmentStrategy, 
#     ModelLoadStrategy
# )

# Temporary local imports from agent_config_models which have the legacy versions
from shared.database.models import (
    LegacyAgentConfiguration as AgentConfiguration,
    LegacyAgentMetrics as AgentMetrics,
    LegacyGPUResourceAllocation as GPUResourceAllocation,
    LegacyModelInstance as ModelInstance,
    LLMProvider,
    AgentType,
    GPUAssignmentStrategy,
    ModelLoadStrategy
)
from shared.utils.database_setup import get_db
from worker.services.ollama_service import invoke_llm_with_tokens, invoke_llm_stream_with_tokens
from worker.services.gpu_monitor_service import gpu_monitor_service
from worker.services.model_lifecycle_manager import model_lifecycle_manager
from worker.smart_ai_models import TokenMetrics

logger = logging.getLogger(__name__)


@dataclass
class AgentInvocationRequest:
    """Request structure for agent LLM invocation."""
    agent_type: AgentType
    messages: List[Dict[str, str]]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None


@dataclass
class AgentResponse:
    """Response structure from agent LLM invocation."""
    content: str
    token_metrics: TokenMetrics
    agent_config_id: int
    model_used: str
    gpu_used: Optional[int]
    processing_time_ms: int
    success: bool
    error_message: Optional[str] = None


class ModelProviderType(str, Enum):
    """Model provider types for the Agent Abstraction Layer."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class AgentLLMManager:
    """
    Core Agent Abstraction Layer service for managing heterogeneous LLM assignments.
    
    Features:
    - Per-agent LLM configuration (Claude, GPT-4, Gemini, Llama)
    - GPU resource allocation across 3x RTX Titan X GPUs
    - API normalization layer for different providers
    - Model lifecycle management and optimization
    - Performance tracking and cost analysis
    """
    
    def __init__(self):
        # Database access will use get_db() context manager instead
        self._agent_configs_cache: Dict[AgentType, AgentConfiguration] = {}
        self._gpu_allocations: Dict[int, GPUResourceAllocation] = {}
        self._model_instances: Dict[str, ModelInstance] = {}
        self._cache_lock = asyncio.Lock()
        
        # Default configurations for each agent type
        self.default_configs = {
            AgentType.PROJECT_MANAGER: {"model": "llama3.2:3b", "provider": LLMProvider.OLLAMA, "gpu": 0},
            AgentType.RESEARCH_SPECIALIST: {"model": "claude-3-opus", "provider": LLMProvider.ANTHROPIC, "gpu": 1},
            AgentType.BUSINESS_ANALYST: {"model": "gpt-4", "provider": LLMProvider.OPENAI, "gpu": 1},
            AgentType.TECHNICAL_EXPERT: {"model": "llama3.1:8b", "provider": LLMProvider.OLLAMA, "gpu": 2},
            AgentType.FINANCIAL_ADVISOR: {"model": "claude-3-sonnet", "provider": LLMProvider.ANTHROPIC, "gpu": 0},
            AgentType.CREATIVE_DIRECTOR: {"model": "gpt-4", "provider": LLMProvider.OPENAI, "gpu": 1},
            AgentType.QUALITY_ASSURANCE: {"model": "llama3.2:3b", "provider": LLMProvider.OLLAMA, "gpu": 2},
            AgentType.DATA_SCIENTIST: {"model": "gemini-1.5-pro", "provider": LLMProvider.GOOGLE, "gpu": 2},
            AgentType.PERSONAL_ASSISTANT: {"model": "llama3.2:1b", "provider": LLMProvider.OLLAMA, "gpu": 0},
            AgentType.LEGAL_ADVISOR: {"model": "claude-3-opus", "provider": LLMProvider.ANTHROPIC, "gpu": 1},
            AgentType.MARKETING_SPECIALIST: {"model": "gpt-4", "provider": LLMProvider.OPENAI, "gpu": 0},
            AgentType.OPERATIONS_MANAGER: {"model": "llama3.2:3b", "provider": LLMProvider.OLLAMA, "gpu": 2},
        }
        
        # Provider client instances (lazy-loaded)
        self._provider_clients: Dict[ModelProviderType, Any] = {}
        
    async def initialize(self):
        """Initialize the Agent LLM Manager with GPU allocation and model preloading."""
        logger.info("Initializing Agent LLM Manager...")
        
        try:
            # Initialize GPU resource allocations
            await self._initialize_gpu_allocations()
            
            # Load agent configurations from database
            await self._load_agent_configurations()
            
            # Start GPU monitoring if not already started
            await gpu_monitor_service.start_monitoring()
            
            # Start model lifecycle management
            await model_lifecycle_manager.start_background_management()
            
            # Preload critical models
            await self._preload_critical_models()
            
            logger.info("Agent LLM Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent LLM Manager: {e}", exc_info=True)
            raise
    
    async def _initialize_gpu_allocations(self):
        """Initialize GPU resource allocation tracking for 3x RTX Titan X GPUs."""
        for db in get_db():
            # Check if GPU allocations exist, create if not
            for gpu_id in [0, 1, 2]:
                existing = db.query(GPUResourceAllocation).filter(
                    GPUResourceAllocation.gpu_id == gpu_id
                ).first()
                
                if not existing:
                    gpu_allocation = GPUResourceAllocation(
                        gpu_id=gpu_id,
                        gpu_name="RTX Titan X",
                        gpu_memory_total_mb=12288.0,  # 12GB for RTX Titan X
                        allocated_memory_mb=0.0,
                        available_memory_mb=12288.0,
                        active_agent_count=0,
                        is_available=True,
                        maintenance_mode=False
                    )
                    db.add(gpu_allocation)
                    logger.info(f"Created GPU {gpu_id} resource allocation")
                
            db.commit()
            
            # Load GPU allocations into cache
            gpu_allocations = db.query(GPUResourceAllocation).all()
            for gpu_alloc in gpu_allocations:
                self._gpu_allocations[gpu_alloc.gpu_id] = gpu_alloc
    
    async def _load_agent_configurations(self):
        """Load agent configurations from database into cache."""
        async with self._cache_lock:
            for db in get_db():
                configs = db.query(AgentConfiguration).filter(
                    AgentConfiguration.is_active == True
                ).all()
                
                for config in configs:
                    self._agent_configs_cache[config.agent_type] = config
                    logger.debug(f"Loaded config for {config.agent_type}: {config.model_name}")
                
                # Create default configurations for agents without explicit config
                for agent_type in AgentType:
                    if agent_type not in self._agent_configs_cache:
                        default = self.default_configs.get(agent_type, {
                            "model": "llama3.2:3b", 
                            "provider": LLMProvider.OLLAMA, 
                            "gpu": 0
                        })
                        
                        config = AgentConfiguration(
                            agent_type=agent_type,
                            agent_name=agent_type.value.replace("_", " ").title(),
                            llm_provider=default["provider"],
                            model_name=default["model"],
                            gpu_assignment=default["gpu"],
                            gpu_assignment_strategy=GPUAssignmentStrategy.AUTO,
                            model_load_strategy=ModelLoadStrategy.ON_DEMAND,
                            temperature=0.7,
                            max_tokens=4096,
                            timeout_seconds=300,
                            is_active=True,
                            is_default=True,
                            priority=5
                        )
                        
                        db.add(config)
                        self._agent_configs_cache[agent_type] = config
                        logger.info(f"Created default config for {agent_type}")
                
                db.commit()
    
    async def _preload_critical_models(self):
        """Preload critical models for high-priority agents."""
        critical_agents = [
            AgentType.PROJECT_MANAGER,
            AgentType.PERSONAL_ASSISTANT,
            AgentType.RESEARCH_SPECIALIST
        ]
        
        for agent_type in critical_agents:
            config = await self.get_agent_configuration(agent_type)
            if config and config.llm_provider == LLMProvider.OLLAMA:
                try:
                    await model_lifecycle_manager.ensure_model_loaded(config.model_name)
                    logger.info(f"Preloaded model {config.model_name} for {agent_type}")
                except Exception as e:
                    logger.warning(f"Failed to preload model for {agent_type}: {e}")
    
    async def get_agent_configuration(self, agent_type: AgentType) -> Optional[AgentConfiguration]:
        """Get configuration for a specific agent type."""
        async with self._cache_lock:
            config = self._agent_configs_cache.get(agent_type)
            if config:
                # Update last used timestamp
                config.last_used_at = datetime.now(timezone.utc)
                for db in get_db():
                    db.merge(config)
                    db.commit()
            return config
    
    async def invoke_agent_llm(self, request: AgentInvocationRequest) -> Union[AgentResponse, AsyncGenerator[str, None]]:
        """
        Invoke LLM for a specific agent with normalized API interface.
        
        Args:
            request: Agent invocation request with messages and configuration
            
        Returns:
            AgentResponse for non-streaming requests or AsyncGenerator for streaming
        """
        start_time = datetime.now()
        
        try:
            # Get agent configuration
            config = await self.get_agent_configuration(request.agent_type)
            if not config:
                raise ValueError(f"No configuration found for agent type: {request.agent_type}")
            
            # Ensure model is loaded for Ollama models
            if config.llm_provider == LLMProvider.OLLAMA:
                await model_lifecycle_manager.ensure_model_loaded(config.model_name)
            
            # Override parameters from request if provided
            temperature = request.temperature or config.temperature
            max_tokens = request.max_tokens or config.max_tokens
            
            # Route to appropriate provider
            if config.llm_provider == LLMProvider.OLLAMA:
                return await self._invoke_ollama(config, request, temperature, max_tokens, start_time)
            elif config.llm_provider == LLMProvider.OPENAI:
                return await self._invoke_openai(config, request, temperature, max_tokens, start_time)
            elif config.llm_provider == LLMProvider.ANTHROPIC:
                return await self._invoke_anthropic(config, request, temperature, max_tokens, start_time)
            elif config.llm_provider == LLMProvider.GOOGLE:
                return await self._invoke_google(config, request, temperature, max_tokens, start_time)
            else:
                raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
                
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Agent LLM invocation failed for {request.agent_type}: {e}")
            
            return AgentResponse(
                content="",
                token_metrics=TokenMetrics(),
                agent_config_id=config.id if config else -1,
                model_used=config.model_name if config else "unknown",
                gpu_used=config.gpu_assignment if config else None,
                processing_time_ms=processing_time,
                success=False,
                error_message=str(e)
            )
    
    async def _invoke_ollama(
        self, 
        config: AgentConfiguration, 
        request: AgentInvocationRequest,
        temperature: float,
        max_tokens: int,
        start_time: datetime
    ) -> Union[AgentResponse, AsyncGenerator[str, None]]:
        """Invoke Ollama model with GPU assignment."""
        try:
            if request.stream:
                return self._stream_ollama_response(config, request, temperature, start_time)
            else:
                content, token_metrics = await invoke_llm_with_tokens(
                    messages=request.messages,
                    model_name=config.model_name,
                    category=f"agent_{request.agent_type.value}"
                )
                
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                # Update metrics
                await self._update_agent_metrics(config, token_metrics, processing_time, True)
                
                return AgentResponse(
                    content=content,
                    token_metrics=token_metrics,
                    agent_config_id=config.id,
                    model_used=config.model_name,
                    gpu_used=config.gpu_assignment,
                    processing_time_ms=processing_time,
                    success=True
                )
                
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self._update_agent_metrics(config, TokenMetrics(), processing_time, False)
            raise
    
    async def _stream_ollama_response(
        self, 
        config: AgentConfiguration, 
        request: AgentInvocationRequest,
        temperature: float,
        start_time: datetime
    ) -> AsyncGenerator[str, None]:
        """Stream Ollama model response."""
        try:
            total_content = ""
            final_token_metrics = None
            
            async for chunk, token_metrics in invoke_llm_stream_with_tokens(
                messages=request.messages,
                model_name=config.model_name,
                tools=request.tools,
                category=f"agent_{request.agent_type.value}"
            ):
                if chunk:  # Content chunk
                    total_content += chunk
                    yield chunk
                elif token_metrics:  # Final metrics
                    final_token_metrics = token_metrics
            
            # Update metrics after streaming completes
            if final_token_metrics:
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                await self._update_agent_metrics(config, final_token_metrics, processing_time, True)
                
        except Exception as e:
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            await self._update_agent_metrics(config, TokenMetrics(), processing_time, False)
            raise
    
    async def _invoke_openai(
        self, 
        config: AgentConfiguration, 
        request: AgentInvocationRequest,
        temperature: float,
        max_tokens: int,
        start_time: datetime
    ) -> AgentResponse:
        """Invoke OpenAI model (placeholder - requires OpenAI client implementation)."""
        # TODO: Implement OpenAI client integration
        logger.warning(f"OpenAI provider not yet implemented for {config.model_name}")
        
        # For now, fallback to a simple response
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return AgentResponse(
            content="OpenAI integration not yet implemented",
            token_metrics=TokenMetrics(),
            agent_config_id=config.id,
            model_used=config.model_name,
            gpu_used=None,  # OpenAI is cloud-based
            processing_time_ms=processing_time,
            success=False,
            error_message="OpenAI provider not implemented"
        )
    
    async def _invoke_anthropic(
        self, 
        config: AgentConfiguration, 
        request: AgentInvocationRequest,
        temperature: float,
        max_tokens: int,
        start_time: datetime
    ) -> AgentResponse:
        """Invoke Anthropic Claude model (placeholder - requires Anthropic client implementation)."""
        # TODO: Implement Anthropic client integration
        logger.warning(f"Anthropic provider not yet implemented for {config.model_name}")
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return AgentResponse(
            content="Anthropic integration not yet implemented",
            token_metrics=TokenMetrics(),
            agent_config_id=config.id,
            model_used=config.model_name,
            gpu_used=None,  # Anthropic is cloud-based
            processing_time_ms=processing_time,
            success=False,
            error_message="Anthropic provider not implemented"
        )
    
    async def _invoke_google(
        self, 
        config: AgentConfiguration, 
        request: AgentInvocationRequest,
        temperature: float,
        max_tokens: int,
        start_time: datetime
    ) -> AgentResponse:
        """Invoke Google Gemini model (placeholder - requires Google client implementation)."""
        # TODO: Implement Google Gemini client integration
        logger.warning(f"Google provider not yet implemented for {config.model_name}")
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return AgentResponse(
            content="Google integration not yet implemented",
            token_metrics=TokenMetrics(),
            agent_config_id=config.id,
            model_used=config.model_name,
            gpu_used=None,  # Google is cloud-based
            processing_time_ms=processing_time,
            success=False,
            error_message="Google provider not implemented"
        )
    
    async def _update_agent_metrics(
        self, 
        config: AgentConfiguration, 
        token_metrics: TokenMetrics, 
        processing_time_ms: int, 
        success: bool
    ):
        """Update agent performance metrics in database."""
        try:
            for db in get_db():
                # Get or create metrics record for current period (hourly)
                current_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                next_hour = current_hour.replace(hour=current_hour.hour + 1)
                
                metrics = db.query(AgentMetrics).filter(
                    and_(
                        AgentMetrics.agent_config_id == config.id,
                        AgentMetrics.period_start == current_hour
                    )
                ).first()
                
                if not metrics:
                    metrics = AgentMetrics(
                        agent_config_id=config.id,
                        period_start=current_hour,
                        period_end=next_hour,
                        total_requests=0,
                        total_tokens_consumed=0,
                        total_processing_time_ms=0,
                        success_rate_percent=100.0,
                        error_count=0
                    )
                    db.add(metrics)
                
                # Update metrics
                metrics.total_requests += 1
                metrics.total_tokens_consumed += token_metrics.total_tokens
                metrics.total_processing_time_ms += processing_time_ms
                
                if processing_time_ms > 0:
                    metrics.average_response_time_ms = metrics.total_processing_time_ms / metrics.total_requests
                
                if not success:
                    metrics.error_count += 1
                
                metrics.success_rate_percent = ((metrics.total_requests - metrics.error_count) / metrics.total_requests) * 100
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update agent metrics: {e}")
    
    async def get_agent_status(self, agent_type: AgentType) -> Dict[str, Any]:
        """Get comprehensive status for a specific agent."""
        config = await self.get_agent_configuration(agent_type)
        if not config:
            return {"error": f"No configuration found for {agent_type}"}
        
        for db in get_db():
            # Get recent metrics
            recent_metrics = db.query(AgentMetrics).filter(
                AgentMetrics.agent_config_id == config.id
            ).order_by(AgentMetrics.period_start.desc()).limit(24).all()  # Last 24 hours
            
            # Get GPU allocation if assigned
            gpu_info = None
            if config.gpu_assignment is not None:
                gpu_alloc = self._gpu_allocations.get(config.gpu_assignment)
                if gpu_alloc:
                    gpu_info = {
                        "gpu_id": gpu_alloc.gpu_id,
                        "memory_allocated_mb": gpu_alloc.allocated_memory_mb,
                        "memory_available_mb": gpu_alloc.available_memory_mb,
                        "utilization_percent": gpu_alloc.utilization_percent
                    }
            
            return {
                "agent_type": config.agent_type,
                "agent_name": config.agent_name,
                "llm_provider": config.llm_provider,
                "model_name": config.model_name,
                "gpu_assignment": config.gpu_assignment,
                "gpu_info": gpu_info,
                "is_active": config.is_active,
                "last_used": config.last_used_at.isoformat() if config.last_used_at else None,
                "recent_metrics": [
                    {
                        "period_start": m.period_start.isoformat(),
                        "total_requests": m.total_requests,
                        "total_tokens": m.total_tokens_consumed,
                        "avg_response_time_ms": m.average_response_time_ms,
                        "success_rate_percent": m.success_rate_percent
                    } for m in recent_metrics
                ]
            }
    
    async def update_agent_configuration(
        self, 
        agent_type: AgentType, 
        updates: Dict[str, Any]
    ) -> bool:
        """Update agent configuration with new LLM or GPU assignments."""
        try:
            async with self._cache_lock:
                for db in get_db():
                    config = db.query(AgentConfiguration).filter(
                        AgentConfiguration.agent_type == agent_type
                    ).first()
                    
                    if not config:
                        return False
                    
                    # Update configuration fields
                    for key, value in updates.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                    
                    config.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    # Update cache
                    self._agent_configs_cache[agent_type] = config
                    
                    logger.info(f"Updated configuration for {agent_type}: {updates}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update agent configuration: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for all agents and GPU resources."""
        return {
            "gpu_allocations": {
                gpu_id: {
                    "gpu_name": alloc.gpu_name,
                    "memory_total_mb": alloc.gpu_memory_total_mb,
                    "memory_allocated_mb": alloc.allocated_memory_mb,
                    "memory_available_mb": alloc.available_memory_mb,
                    "active_agents": alloc.active_agent_count,
                    "is_available": alloc.is_available,
                    "utilization_percent": alloc.utilization_percent
                } for gpu_id, alloc in self._gpu_allocations.items()
            },
            "agent_configurations": {
                agent_type.value: {
                    "model_name": config.model_name,
                    "llm_provider": config.llm_provider.value,
                    "gpu_assignment": config.gpu_assignment,
                    "is_active": config.is_active,
                    "last_used": config.last_used_at.isoformat() if config.last_used_at else None
                } for agent_type, config in self._agent_configs_cache.items()
            },
            "monitoring_status": await gpu_monitor_service.get_monitoring_status(),
            "model_lifecycle_status": await model_lifecycle_manager.get_lifecycle_status()
        }


# Global instance
agent_llm_manager = AgentLLMManager()