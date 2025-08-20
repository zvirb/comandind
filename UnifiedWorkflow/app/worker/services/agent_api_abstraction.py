"""
Agent API Abstraction Layer - Unified interface for heterogeneous LLM providers
Normalizes different API formats and provides seamless agent-to-model communication.
Integrates ModelProviderFactory with AgentLLMManager for complete abstraction.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from enum import Enum

from shared.database.models import AgentType, LLMProvider
from worker.services.agent_llm_manager import (
    AgentLLMManager, 
    AgentInvocationRequest, 
    AgentResponse,
    agent_llm_manager
)
from worker.services.model_provider_factory import (
    ModelProviderFactory, 
    ModelProviderRequest, 
    ModelProviderMessage, 
    ModelProviderResponse,
    model_provider_factory
)
# TEMPORARILY DISABLED: Missing psutil dependency
# from worker.services.agent_gpu_resource_manager import (
#     AgentGPUResourceManager,
#     GPUAllocationRequest,
#     agent_gpu_resource_manager
# )
from worker.smart_ai_models import TokenMetrics

logger = logging.getLogger(__name__)


class AgentInvocationMode(str, Enum):
    """Modes for agent invocation with different optimization strategies."""
    FAST = "fast"              # Optimized for speed, may use smaller models
    BALANCED = "balanced"      # Balance between speed and quality
    QUALITY = "quality"        # Optimized for highest quality output
    COST_OPTIMIZED = "cost"    # Optimized for minimal cost
    GPU_OPTIMIZED = "gpu"      # Optimized for GPU utilization


@dataclass
class UnifiedAgentRequest:
    """Unified request format for all agent interactions."""
    agent_type: AgentType
    messages: List[Dict[str, str]]  # Standard message format
    mode: AgentInvocationMode = AgentInvocationMode.BALANCED
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    priority: int = 5  # 1-10 scale, 10 being highest
    timeout_seconds: int = 300
    retry_on_failure: bool = True
    fallback_model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UnifiedAgentResponse:
    """Unified response format from agent interactions."""
    content: str
    token_metrics: TokenMetrics
    agent_type: AgentType
    model_used: str
    provider_used: LLMProvider
    gpu_used: Optional[int]
    processing_time_ms: int
    mode_used: AgentInvocationMode
    success: bool
    was_fallback: bool = False
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class AgentAPIAbstraction:
    """
    Unified API abstraction layer for heterogeneous agent-model interactions.
    
    Features:
    - Seamless switching between different LLM providers per agent
    - Automatic GPU resource allocation and optimization
    - Intelligent fallback strategies
    - Performance monitoring and optimization
    - Cost tracking and optimization
    - Dynamic model selection based on invocation mode
    """
    
    def __init__(self):
        self.agent_manager = agent_llm_manager
        self.provider_factory = model_provider_factory
        # TEMPORARILY DISABLED: GPU resource manager not available
        self.gpu_manager = None  # agent_gpu_resource_manager
        self._performance_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._fallback_strategies: Dict[AgentType, List[Dict[str, Any]]] = {}
        self._optimization_rules: Dict[AgentInvocationMode, Dict[str, Any]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Agent API Abstraction Layer."""
        if self._initialized:
            return
        
        logger.info("Initializing Agent API Abstraction Layer...")
        
        try:
            # Initialize core components
            await self.agent_manager.initialize()
            await self.provider_factory.initialize()
            await self.gpu_manager.initialize()
            
            # Setup optimization rules
            self._setup_optimization_rules()
            
            # Setup fallback strategies
            await self._setup_fallback_strategies()
            
            self._initialized = True
            logger.info("Agent API Abstraction Layer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent API Abstraction Layer: {e}", exc_info=True)
            raise
    
    def _setup_optimization_rules(self):
        """Setup optimization rules for different invocation modes."""
        self._optimization_rules = {
            AgentInvocationMode.FAST: {
                "prefer_small_models": True,
                "max_tokens_limit": 1024,
                "temperature_adjustment": 0.3,  # Lower temperature for faster generation
                "gpu_priority": "lowest_latency",
                "timeout_seconds": 60
            },
            AgentInvocationMode.BALANCED: {
                "prefer_small_models": False,
                "max_tokens_limit": 4096,
                "temperature_adjustment": 0.0,  # No adjustment
                "gpu_priority": "balanced",
                "timeout_seconds": 300
            },
            AgentInvocationMode.QUALITY: {
                "prefer_small_models": False,
                "max_tokens_limit": 8192,
                "temperature_adjustment": 0.0,
                "gpu_priority": "highest_performance",
                "timeout_seconds": 600
            },
            AgentInvocationMode.COST_OPTIMIZED: {
                "prefer_small_models": True,
                "max_tokens_limit": 2048,
                "temperature_adjustment": 0.0,
                "gpu_priority": "lowest_cost",
                "timeout_seconds": 180
            },
            AgentInvocationMode.GPU_OPTIMIZED: {
                "prefer_small_models": False,
                "max_tokens_limit": 4096,
                "temperature_adjustment": 0.0,
                "gpu_priority": "maximize_utilization",
                "timeout_seconds": 300
            }
        }
    
    async def _setup_fallback_strategies(self):
        """Setup fallback strategies for each agent type."""
        # Define fallback models for each agent type
        base_fallbacks = [
            {"provider": LLMProvider.OLLAMA, "model": "llama3.2:3b"},
            {"provider": LLMProvider.OLLAMA, "model": "llama3.2:1b"},
        ]
        
        for agent_type in AgentType:
            self._fallback_strategies[agent_type] = base_fallbacks.copy()
    
    async def invoke_agent(self, request: UnifiedAgentRequest) -> UnifiedAgentResponse:
        """
        Invoke an agent with unified API abstraction.
        
        Args:
            request: Unified agent request
            
        Returns:
            Unified agent response with performance metrics
        """
        if not self._initialized:
            await self.initialize()
        
        start_time = datetime.now()
        
        try:
            # Apply optimization based on mode
            optimized_request = await self._optimize_request(request)
            
            # Get agent configuration
            agent_config = await self.agent_manager.get_agent_configuration(request.agent_type)
            if not agent_config:
                raise ValueError(f"No configuration found for agent: {request.agent_type}")
            
            # Allocate GPU resources if needed
            gpu_allocation = None
            if agent_config.llm_provider == LLMProvider.OLLAMA:
                gpu_allocation = await self._allocate_gpu_resources(agent_config, request)
            
            # Create provider request
            provider_request = await self._create_provider_request(agent_config, optimized_request)
            
            # Invoke through provider factory
            if request.stream:
                return await self._stream_agent_response(agent_config, provider_request, request, start_time)
            else:
                return await self._invoke_agent_response(agent_config, provider_request, request, start_time)
                
        except Exception as e:
            # Try fallback strategy
            if request.retry_on_failure:
                logger.warning(f"Primary invocation failed for {request.agent_type}, trying fallback: {e}")
                return await self._try_fallback(request, start_time, str(e))
            else:
                processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                return UnifiedAgentResponse(
                    content="",
                    token_metrics=TokenMetrics(),
                    agent_type=request.agent_type,
                    model_used="unknown",
                    provider_used=LLMProvider.OLLAMA,
                    gpu_used=None,
                    processing_time_ms=processing_time,
                    mode_used=request.mode,
                    success=False,
                    error_message=str(e)
                )
    
    async def _optimize_request(self, request: UnifiedAgentRequest) -> UnifiedAgentRequest:
        """Apply optimizations based on invocation mode."""
        optimization = self._optimization_rules.get(request.mode, {})
        
        # Apply timeout adjustment
        if "timeout_seconds" in optimization:
            request.timeout_seconds = min(request.timeout_seconds, optimization["timeout_seconds"])
        
        # Apply token limit
        if "max_tokens_limit" in optimization and request.max_tokens:
            request.max_tokens = min(request.max_tokens, optimization["max_tokens_limit"])
        elif "max_tokens_limit" in optimization:
            request.max_tokens = optimization["max_tokens_limit"]
        
        # Apply temperature adjustment
        if "temperature_adjustment" in optimization and request.temperature:
            adjustment = optimization["temperature_adjustment"]
            request.temperature = max(0.0, min(2.0, request.temperature + adjustment))
        
        return request
    
    async def _allocate_gpu_resources(self, agent_config, request: UnifiedAgentRequest):
        """Allocate GPU resources for agent if needed."""
        # TEMPORARILY DISABLED: GPU resource manager not available
        logger.debug(f"GPU allocation temporarily disabled for {request.agent_type}")
        return
        try:
            # Estimate memory requirements based on model
            estimated_memory = self._estimate_model_memory(agent_config.model_name)
            
            # gpu_request = GPUAllocationRequest(
            #     agent_type=request.agent_type,
            #     model_name=agent_config.model_name,
            #     estimated_memory_mb=estimated_memory,
            #     priority=request.priority,
            #     max_wait_time_seconds=30,
            #     preferred_gpu_id=agent_config.gpu_assignment
            # )
            # 
            # allocation_result = await self.gpu_manager.allocate_gpu_for_agent(gpu_request)
            # if allocation_result.success:
            #     logger.debug(f"Allocated GPU {allocation_result.allocated_gpu_id} for {request.agent_type}")
            #     return allocation_result
            # else:
            #     logger.warning(f"GPU allocation failed for {request.agent_type}: {allocation_result.error_message}")
            #     return None
                
        except Exception as e:
            logger.error(f"Error allocating GPU resources: {e}")
            return None
    
    def _estimate_model_memory(self, model_name: str) -> float:
        """Estimate memory requirements for a model."""
        # Simple estimation based on model name patterns
        if "1b" in model_name.lower():
            return 2048.0  # 2GB for 1B parameter models
        elif "3b" in model_name.lower():
            return 4096.0  # 4GB for 3B parameter models
        elif "8b" in model_name.lower():
            return 8192.0  # 8GB for 8B parameter models
        elif "13b" in model_name.lower():
            return 12288.0  # 12GB for 13B parameter models
        else:
            return 4096.0  # Default 4GB
    
    async def _create_provider_request(self, agent_config, request: UnifiedAgentRequest) -> ModelProviderRequest:
        """Create provider-specific request."""
        # Convert messages to provider format
        provider_messages = [
            ModelProviderMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                metadata=msg.get("metadata")
            ) for msg in request.messages
        ]
        
        return ModelProviderRequest(
            messages=provider_messages,
            model_name=agent_config.model_name,
            temperature=request.temperature or agent_config.temperature or 0.7,
            max_tokens=request.max_tokens or agent_config.max_tokens,
            stream=request.stream,
            tools=request.tools,
            metadata=request.metadata
        )
    
    async def _invoke_agent_response(
        self, 
        agent_config, 
        provider_request: ModelProviderRequest, 
        request: UnifiedAgentRequest, 
        start_time: datetime
    ) -> UnifiedAgentResponse:
        """Invoke agent and return unified response."""
        provider_response = await self.provider_factory.invoke_model(
            agent_config.llm_provider, 
            provider_request
        )
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Record performance metrics
        await self._record_performance_metrics(
            request.agent_type, 
            agent_config.model_name, 
            processing_time, 
            provider_response.token_metrics,
            provider_response.success
        )
        
        return UnifiedAgentResponse(
            content=provider_response.content,
            token_metrics=provider_response.token_metrics,
            agent_type=request.agent_type,
            model_used=agent_config.model_name,
            provider_used=agent_config.llm_provider,
            gpu_used=agent_config.gpu_assignment,
            processing_time_ms=processing_time,
            mode_used=request.mode,
            success=provider_response.success,
            error_message=provider_response.error_message
        )
    
    async def _stream_agent_response(
        self, 
        agent_config, 
        provider_request: ModelProviderRequest, 
        request: UnifiedAgentRequest, 
        start_time: datetime
    ) -> AsyncGenerator[str, None]:
        """Stream agent response."""
        try:
            total_content = ""
            async for chunk in self.provider_factory.stream_model(
                agent_config.llm_provider, 
                provider_request
            ):
                total_content += chunk
                yield chunk
            
            # Record final metrics
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            token_metrics = TokenMetrics()
            token_metrics.add_tokens(
                sum(len(msg.content.split()) for msg in provider_request.messages) * 1.3,
                len(total_content.split()) * 1.3,
                f"agent_{request.agent_type.value}"
            )
            
            await self._record_performance_metrics(
                request.agent_type, 
                agent_config.model_name, 
                processing_time, 
                token_metrics,
                True
            )
            
        except Exception as e:
            logger.error(f"Streaming failed for {request.agent_type}: {e}")
            yield f"Error: {str(e)}"
    
    async def _try_fallback(
        self, 
        request: UnifiedAgentRequest, 
        start_time: datetime, 
        original_error: str
    ) -> UnifiedAgentResponse:
        """Try fallback strategies when primary invocation fails."""
        fallback_strategies = self._fallback_strategies.get(request.agent_type, [])
        
        for i, fallback in enumerate(fallback_strategies):
            try:
                logger.info(f"Trying fallback {i+1} for {request.agent_type}: {fallback['model']}")
                
                # Create fallback provider request
                provider_messages = [
                    ModelProviderMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        metadata=msg.get("metadata")
                    ) for msg in request.messages
                ]
                
                fallback_request = ModelProviderRequest(
                    messages=provider_messages,
                    model_name=fallback["model"],
                    temperature=request.temperature or 0.7,
                    max_tokens=request.max_tokens or 2048,
                    stream=request.stream,
                    tools=request.tools,
                    metadata=request.metadata
                )
                
                provider_response = await self.provider_factory.invoke_model(
                    fallback["provider"], 
                    fallback_request
                )
                
                if provider_response.success:
                    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    return UnifiedAgentResponse(
                        content=provider_response.content,
                        token_metrics=provider_response.token_metrics,
                        agent_type=request.agent_type,
                        model_used=fallback["model"],
                        provider_used=fallback["provider"],
                        gpu_used=None,  # Fallbacks typically don't use specific GPU
                        processing_time_ms=processing_time,
                        mode_used=request.mode,
                        success=True,
                        was_fallback=True,
                        error_message=f"Primary failed ({original_error}), used fallback {i+1}"
                    )
                    
            except Exception as e:
                logger.warning(f"Fallback {i+1} failed for {request.agent_type}: {e}")
                continue
        
        # All fallbacks failed
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return UnifiedAgentResponse(
            content="",
            token_metrics=TokenMetrics(),
            agent_type=request.agent_type,
            model_used="none",
            provider_used=LLMProvider.OLLAMA,
            gpu_used=None,
            processing_time_ms=processing_time,
            mode_used=request.mode,
            success=False,
            was_fallback=True,
            error_message=f"All strategies failed. Original: {original_error}"
        )
    
    async def _record_performance_metrics(
        self, 
        agent_type: AgentType, 
        model_name: str, 
        processing_time_ms: int, 
        token_metrics: TokenMetrics,
        success: bool
    ):
        """Record performance metrics for optimization."""
        metric_key = f"{agent_type.value}_{model_name}"
        
        if metric_key not in self._performance_cache:
            self._performance_cache[metric_key] = []
        
        metric = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": processing_time_ms,
            "tokens_per_second": (token_metrics.total_tokens / processing_time_ms * 1000) if processing_time_ms > 0 else 0,
            "total_tokens": token_metrics.total_tokens,
            "success": success
        }
        
        self._performance_cache[metric_key].append(metric)
        
        # Keep only recent metrics
        if len(self._performance_cache[metric_key]) > 100:
            self._performance_cache[metric_key] = self._performance_cache[metric_key][-50:]
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        agent_status = await self.agent_manager.get_system_status()
        gpu_status = await self.gpu_manager.get_gpu_status()
        available_providers = await self.provider_factory.get_available_providers()
        
        return {
            "agent_abstraction_layer": {
                "initialized": self._initialized,
                "available_providers": [p.value for p in available_providers],
                "optimization_modes": list(self._optimization_rules.keys()),
                "fallback_strategies_count": len(self._fallback_strategies),
                "performance_cache_entries": len(self._performance_cache)
            },
            "agent_manager_status": agent_status,
            "gpu_manager_status": gpu_status,
            "performance_summary": {
                agent_model: {
                    "recent_invocations": len(metrics),
                    "avg_processing_time_ms": sum(m["processing_time_ms"] for m in metrics) / len(metrics) if metrics else 0,
                    "avg_tokens_per_second": sum(m["tokens_per_second"] for m in metrics) / len(metrics) if metrics else 0,
                    "success_rate": sum(1 for m in metrics if m["success"]) / len(metrics) if metrics else 0
                } for agent_model, metrics in self._performance_cache.items()
            }
        }
    
    async def optimize_system_performance(self) -> Dict[str, Any]:
        """Optimize system performance based on collected metrics."""
        optimization_results = {
            "actions_taken": [],
            "recommendations": [],
            "performance_improvement_estimate": 0.0
        }
        
        try:
            # Analyze performance patterns
            for agent_model, metrics in self._performance_cache.items():
                if len(metrics) < 10:  # Need sufficient data
                    continue
                
                recent_metrics = metrics[-20:]  # Last 20 invocations
                avg_time = sum(m["processing_time_ms"] for m in recent_metrics) / len(recent_metrics)
                success_rate = sum(1 for m in recent_metrics if m["success"]) / len(recent_metrics)
                
                if avg_time > 10000:  # > 10 seconds
                    optimization_results["recommendations"].append(
                        f"{agent_model}: Consider smaller model or GPU optimization (avg: {avg_time:.0f}ms)"
                    )
                
                if success_rate < 0.9:  # < 90% success rate
                    optimization_results["recommendations"].append(
                        f"{agent_model}: Low success rate ({success_rate*100:.1f}%) - review configuration"
                    )
            
            # GPU optimization recommendations
            gpu_status = await self.gpu_manager.get_gpu_status()
            gpu_optimization = await self.gpu_manager.optimize_allocations()
            optimization_results["actions_taken"].extend(gpu_optimization.get("actions_taken", []))
            optimization_results["recommendations"].extend(gpu_optimization.get("recommendations", []))
            
        except Exception as e:
            logger.error(f"Error in system optimization: {e}")
            optimization_results["error"] = str(e)
        
        return optimization_results


# Global instance
agent_api_abstraction = AgentAPIAbstraction()