"""
Centralized Resource Service - Enterprise GPU Resource Management
Replaces direct ollama calls with intelligent GPU resource allocation and queue management.
Integrates existing model resource manager, queue manager, and lifecycle manager.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from worker.services.model_resource_manager import model_resource_manager, ModelCategory
from worker.services.model_queue_manager import model_queue_manager, RequestPriority
from worker.services.model_lifecycle_manager import model_lifecycle_manager
from worker.services.gpu_load_balancer import gpu_load_balancer, LoadBalancingStrategy
from worker.services.ollama_service import invoke_llm_with_tokens, invoke_llm_stream_with_tokens
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.services.security_audit_service import security_audit_service

# Import analytics service with lazy loading to avoid circular imports
resource_analytics_service = None

async def get_analytics_service():
    """Lazy load analytics service to avoid circular imports."""
    global resource_analytics_service
    if resource_analytics_service is None:
        from worker.services.resource_analytics_service import resource_analytics_service as ras
        resource_analytics_service = ras
    return resource_analytics_service

logger = logging.getLogger(__name__)


class ComplexityLevel(str, Enum):
    """Request complexity levels for automatic model selection."""
    SIMPLE = "simple"        # Basic questions, fast responses
    MODERATE = "moderate"    # Standard conversations
    COMPLEX = "complex"      # Detailed analysis
    EXPERT = "expert"        # Complex reasoning, research


@dataclass
class ResourceRequest:
    """Represents a request for model resources."""
    request_id: str
    user_id: str
    service_name: str
    session_id: str
    prompt: str
    complexity: ComplexityLevel
    preferred_model: Optional[str] = None
    fallback_allowed: bool = True
    priority: RequestPriority = RequestPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResourceAllocation:
    """Represents an allocated resource for a request."""
    request_id: str
    allocated_model: str
    model_category: ModelCategory
    expert_id: str
    estimated_completion: datetime
    resource_usage: Dict[str, Any] = field(default_factory=dict)


class CentralizedResourceService:
    """
    Central service for intelligent GPU resource allocation and management.
    Replaces direct ollama calls with enterprise-grade resource management.
    """
    
    def __init__(self):
        self.active_allocations: Dict[str, ResourceAllocation] = {}
        self.complexity_model_mapping = self._initialize_complexity_mapping()
        self.service_configurations = self._initialize_service_configs()
        self._allocation_lock = asyncio.Lock()
        
    def _initialize_complexity_mapping(self) -> Dict[ComplexityLevel, List[str]]:
        """Initialize complexity-based model selection mapping."""
        return {
            ComplexityLevel.SIMPLE: [
                "llama3.2:1b",      # Fastest for simple queries
                "qwen2.5:1.5b",     # Alternative fast model
            ],
            ComplexityLevel.MODERATE: [
                "llama3.2:3b",      # Good balance
                "qwen2.5:3b",       # Alternative moderate model
                "phi3:3.8b",        # Reasoning focused
            ],
            ComplexityLevel.COMPLEX: [
                "llama3.1:8b",      # Current standard
                "mistral:7b",       # Alternative large model
                "qwen2.5:7b",       # Strong performance
                "gemma2:9b",        # Google's large model
            ],
            ComplexityLevel.EXPERT: [
                "qwen2.5:14b",      # Specialized reasoning
                "qwen2.5:32b",      # High-end analysis
                "llama3.1:70b",     # Maximum capability (when available)
            ]
        }
    
    def _initialize_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize service-specific configurations."""
        return {
            "simple_chat": {
                "default_complexity": ComplexityLevel.MODERATE,
                "allow_escalation": True,
                "max_model_category": ModelCategory.LARGE_8B,
                "timeout_seconds": 300,
            },
            "smart_router": {
                "default_complexity": ComplexityLevel.COMPLEX,
                "allow_escalation": True,
                "max_model_category": ModelCategory.XLARGE_10B,
                "timeout_seconds": 600,
            },
            "expert_group": {
                "default_complexity": ComplexityLevel.EXPERT,
                "allow_escalation": False,
                "max_model_category": ModelCategory.XLARGE_10B,
                "timeout_seconds": 900,
            },
            "helios": {
                "default_complexity": ComplexityLevel.EXPERT,
                "allow_escalation": False,
                "max_model_category": ModelCategory.XLARGE_10B,
                "timeout_seconds": 1200,
            }
        }
    
    def analyze_complexity(self, prompt: str, service_name: str) -> ComplexityLevel:
        """
        Analyze prompt complexity to determine appropriate model selection.
        
        Args:
            prompt: User input prompt
            service_name: Requesting service name
            
        Returns:
            Determined complexity level
        """
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())
        
        # Get service default
        service_config = self.service_configurations.get(service_name, {})
        default_complexity = service_config.get("default_complexity", ComplexityLevel.MODERATE)
        
        # Simple queries (use fast models)
        simple_indicators = [
            "what is", "who is", "when", "where", "yes", "no", 
            "hello", "hi", "thanks", "thank you"
        ]
        if any(indicator in prompt_lower for indicator in simple_indicators) and word_count < 20:
            return ComplexityLevel.SIMPLE
        
        # Complex analysis indicators
        complex_indicators = [
            "analyze", "compare", "evaluate", "research", "investigate",
            "comprehensive", "detailed", "in-depth", "explain why",
            "pros and cons", "advantages and disadvantages"
        ]
        if any(indicator in prompt_lower for indicator in complex_indicators) or word_count > 100:
            return ComplexityLevel.COMPLEX
        
        # Expert-level indicators
        expert_indicators = [
            "algorithm", "technical implementation", "architecture",
            "mathematical proof", "statistical analysis", "code review",
            "scientific", "academic", "research paper"
        ]
        if any(indicator in prompt_lower for indicator in expert_indicators):
            return ComplexityLevel.EXPERT
        
        return default_complexity
    
    def select_optimal_model(
        self, 
        complexity: ComplexityLevel,
        service_name: str,
        preferred_model: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Select optimal model based on complexity and resource availability.
        
        Args:
            complexity: Request complexity level
            service_name: Requesting service name
            preferred_model: User-preferred model (if any)
            
        Returns:
            Tuple of (selected_model, selection_reason)
        """
        service_config = self.service_configurations.get(service_name, {})
        max_category = service_config.get("max_model_category", ModelCategory.LARGE_8B)
        
        # Check if preferred model is available and within limits
        if preferred_model:
            model_info = model_resource_manager.get_model_info(preferred_model)
            if model_info and self._is_model_within_limits(model_info.category, max_category):
                return preferred_model, f"User preferred model: {preferred_model}"
        
        # Get complexity-appropriate models
        candidate_models = self.complexity_model_mapping.get(complexity, [])
        
        # Filter by service category limits
        filtered_models = []
        for model_name in candidate_models:
            model_info = model_resource_manager.get_model_info(model_name)
            if model_info and self._is_model_within_limits(model_info.category, max_category):
                filtered_models.append(model_name)
        
        if not filtered_models:
            # Fallback to moderate complexity models
            fallback_models = self.complexity_model_mapping[ComplexityLevel.MODERATE]
            for model_name in fallback_models:
                model_info = model_resource_manager.get_model_info(model_name)
                if model_info and self._is_model_within_limits(model_info.category, max_category):
                    filtered_models.append(model_name)
        
        if not filtered_models:
            # Last resort: use simplest available model
            return "llama3.2:1b", "Fallback to simplest available model"
        
        # Select first available model (could be enhanced with load balancing)
        selected_model = filtered_models[0]
        return selected_model, f"Selected based on {complexity.value} complexity"
    
    def _is_model_within_limits(self, model_category: ModelCategory, max_category: ModelCategory) -> bool:
        """Check if model category is within service limits."""
        category_hierarchy = {
            ModelCategory.SMALL_1B: 1,
            ModelCategory.MEDIUM_4B: 2,
            ModelCategory.LARGE_8B: 3,
            ModelCategory.XLARGE_10B: 4
        }
        return category_hierarchy[model_category] <= category_hierarchy[max_category]
    
    async def allocate_and_invoke(
        self,
        prompt: str,
        user_id: str,
        service_name: str,
        session_id: Optional[str] = None,
        complexity: Optional[ComplexityLevel] = None,
        preferred_model: Optional[str] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        fallback_allowed: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Allocate resources and invoke model for a request.
        
        Args:
            prompt: Input prompt
            user_id: User identifier
            service_name: Requesting service name
            session_id: Session identifier
            complexity: Request complexity (auto-detected if None)
            preferred_model: Preferred model name
            priority: Request priority
            fallback_allowed: Allow fallback models
            metadata: Additional request metadata
            
        Returns:
            Response dictionary with result and metadata
        """
        request_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        
        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self.analyze_complexity(prompt, service_name)
        
        # Create resource request
        resource_request = ResourceRequest(
            request_id=request_id,
            user_id=user_id,
            service_name=service_name,
            session_id=session_id,
            prompt=prompt,
            complexity=complexity,
            preferred_model=preferred_model,
            fallback_allowed=fallback_allowed,
            priority=priority,
            metadata=metadata or {}
        )
        
        allocation_start_time = datetime.now(timezone.utc)
        
        try:
            # Allocate resources
            allocation = await self._allocate_resources(resource_request)
            allocation_time = (datetime.now(timezone.utc) - allocation_start_time).total_seconds()
            
            # Record allocation time metric
            analytics = await get_analytics_service()
            from worker.services.resource_analytics_service import MetricType
            await analytics.record_metric(
                MetricType.ALLOCATION_TIME,
                allocation_time,
                service_name,
                allocation.allocated_model,
                complexity,
                gpu_id=allocation.resource_usage.get("gpu_allocation", {}).get("gpu_id"),
                user_id=user_id,
                session_id=session_id
            )
            
            # Invoke model
            result = await self._invoke_allocated_model(resource_request, allocation)
            
            # Record processing time metric
            processing_time = result.get("processing_time", 0)
            await analytics.record_metric(
                MetricType.PROCESSING_TIME,
                processing_time,
                service_name,
                allocation.allocated_model,
                complexity,
                gpu_id=allocation.resource_usage.get("gpu_allocation", {}).get("gpu_id"),
                user_id=user_id,
                session_id=session_id
            )
            
            # Track usage
            await self._track_resource_usage(allocation, result)
            
            return {
                "request_id": request_id,
                "response": result["response"],
                "token_info": result.get("token_info", {}),
                "allocation": {
                    "model": allocation.allocated_model,
                    "category": allocation.model_category.value,
                    "complexity": complexity.value,
                    "expert_id": allocation.expert_id
                },
                "metadata": {
                    "service": service_name,
                    "session_id": session_id,
                    "processing_time": processing_time,
                    "allocation_time": allocation_time,
                    "resource_usage": allocation.resource_usage
                }
            }
            
        except Exception as e:
            logger.error(f"Error in resource allocation for request {request_id}: {e}")
            
            # Record error metric
            try:
                analytics = await get_analytics_service()
                from worker.services.resource_analytics_service import MetricType
                await analytics.record_metric(
                    MetricType.ERROR_RATE,
                    1.0,
                    service_name,
                    resource_request.preferred_model or "unknown",
                    complexity,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={"error_type": type(e).__name__, "error_message": str(e)}
                )
            except Exception as analytics_error:
                logger.warning(f"Failed to record error metric: {analytics_error}")
            
            # Attempt fallback if allowed
            if fallback_allowed:
                return await self._fallback_invocation(resource_request, str(e))
            else:
                raise
        
        finally:
            # Clean up allocation
            await self._cleanup_allocation(request_id)
    
    async def allocate_and_invoke_stream(
        self,
        prompt: str,
        user_id: str,
        service_name: str,
        session_id: Optional[str] = None,
        complexity: Optional[ComplexityLevel] = None,
        preferred_model: Optional[str] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
        """
        Allocate resources and invoke model with streaming response.
        
        Args:
            prompt: Input prompt
            user_id: User identifier
            service_name: Requesting service name
            session_id: Session identifier
            complexity: Request complexity (auto-detected if None)
            preferred_model: Preferred model name
            priority: Request priority
            metadata: Additional request metadata
            
        Yields:
            Tuples of (chunk, token_info)
        """
        request_id = str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        
        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self.analyze_complexity(prompt, service_name)
        
        # Create resource request
        resource_request = ResourceRequest(
            request_id=request_id,
            user_id=user_id,
            service_name=service_name,
            session_id=session_id,
            prompt=prompt,
            complexity=complexity,
            preferred_model=preferred_model,
            priority=priority,
            metadata=metadata or {}
        )
        
        allocation = None
        try:
            # Allocate resources
            allocation = await self._allocate_resources(resource_request)
            
            # Stream from allocated model
            messages = [{"role": "user", "content": prompt}]
            
            async for chunk, token_info in invoke_llm_stream_with_tokens(
                messages=messages,
                model_name=allocation.allocated_model,
                temperature=0.3,
                stream=True
            ):
                yield chunk, token_info
            
        except Exception as e:
            logger.error(f"Error in streaming allocation for request {request_id}: {e}")
            raise
        
        finally:
            # Clean up allocation
            if allocation:
                await self._cleanup_allocation(request_id)
    
    async def _allocate_resources(self, request: ResourceRequest) -> ResourceAllocation:
        """Allocate GPU resources for a request with load balancing."""
        async with self._allocation_lock:
            # Select optimal model
            selected_model, selection_reason = self.select_optimal_model(
                request.complexity,
                request.service_name,
                request.preferred_model
            )
            
            # Generate expert ID for tracking
            expert_id = f"{request.service_name}_{request.request_id[:8]}"
            
            # Select optimal GPU for load balancing
            gpu_decision = await gpu_load_balancer.select_optimal_gpu(
                selected_model, 
                request.complexity
            )
            
            # Allocate request to selected GPU
            await gpu_load_balancer.allocate_request(
                gpu_decision.selected_gpu, 
                selected_model, 
                request.request_id
            )
            
            # Check if model needs to be preloaded
            await model_lifecycle_manager.ensure_model_loaded(selected_model)
            
            # Reserve execution slot
            reserved = await model_resource_manager.reserve_execution_slot(
                selected_model, expert_id
            )
            
            if not reserved:
                # Add to queue if reservation failed
                queue_request_id = await model_queue_manager.enqueue_request(
                    expert_id=expert_id,
                    model_name=selected_model,
                    user_id=request.user_id,
                    session_id=request.session_id,
                    priority=request.priority,
                    estimated_duration=self._estimate_duration(request.complexity),
                    metadata=request.metadata
                )
                
                # Wait for queue processing
                result = await model_queue_manager.get_request_result(
                    queue_request_id, 
                    timeout=self.service_configurations[request.service_name]["timeout_seconds"]
                )
                
                logger.info(f"Request {request.request_id} processed via queue: {result}")
            
            # Create allocation
            model_info = model_resource_manager.get_model_info(selected_model)
            allocation = ResourceAllocation(
                request_id=request.request_id,
                allocated_model=selected_model,
                model_category=model_info.category,
                expert_id=expert_id,
                estimated_completion=datetime.now(timezone.utc),
                resource_usage={
                    "selection_reason": selection_reason,
                    "complexity": request.complexity.value,
                    "reserved_via_queue": not reserved,
                    "gpu_allocation": {
                        "gpu_id": gpu_decision.selected_gpu,
                        "strategy": gpu_decision.strategy_used.value,
                        "decision_reason": gpu_decision.decision_reason,
                        "confidence": gpu_decision.confidence_score
                    }
                }
            )
            
            self.active_allocations[request.request_id] = allocation
            
            logger.info(f"Allocated {selected_model} on GPU {gpu_decision.selected_gpu} for request {request.request_id} ({selection_reason})")
            return allocation
    
    async def _invoke_allocated_model(
        self, 
        request: ResourceRequest, 
        allocation: ResourceAllocation
    ) -> Dict[str, Any]:
        """Invoke the allocated model for the request."""
        start_time = datetime.now(timezone.utc)
        
        try:
            messages = [{"role": "user", "content": request.prompt}]
            
            response_text, token_info = await invoke_llm_with_tokens(
                messages=messages,
                model_name=allocation.allocated_model,
                temperature=0.3
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "response": response_text,
                "token_info": token_info,
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error invoking model {allocation.allocated_model}: {e}")
            raise
    
    async def _fallback_invocation(
        self, 
        request: ResourceRequest, 
        error_message: str
    ) -> Dict[str, Any]:
        """Perform fallback invocation with simpler model."""
        logger.warning(f"Attempting fallback for request {request.request_id}: {error_message}")
        
        # Use simplest available model as fallback
        fallback_model = "llama3.2:1b"
        
        try:
            messages = [{"role": "user", "content": request.prompt}]
            response_text, token_info = await invoke_llm_with_tokens(
                messages=messages,
                model_name=fallback_model,
                temperature=0.3
            )
            
            return {
                "request_id": request.request_id,
                "response": response_text,
                "token_info": token_info,
                "allocation": {
                    "model": fallback_model,
                    "category": "fallback",
                    "complexity": request.complexity.value,
                    "expert_id": f"fallback_{request.request_id[:8]}"
                },
                "metadata": {
                    "service": request.service_name,
                    "session_id": request.session_id,
                    "fallback_reason": error_message,
                    "is_fallback": True
                }
            }
            
        except Exception as e:
            logger.error(f"Fallback invocation also failed: {e}")
            raise Exception(f"Both primary and fallback allocations failed: {error_message}, {e}")
    
    async def _track_resource_usage(
        self, 
        allocation: ResourceAllocation, 
        result: Dict[str, Any]
    ):
        """Track resource usage for analytics and optimization."""
        try:
            usage_data = {
                "request_id": allocation.request_id,
                "model": allocation.allocated_model,
                "category": allocation.model_category.value,
                "processing_time": result.get("processing_time", 0),
                "tokens": result.get("token_info", {}),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Update allocation with usage data
            allocation.resource_usage.update(usage_data)
            
            logger.debug(f"Tracked resource usage for request {allocation.request_id}")
            
        except Exception as e:
            logger.warning(f"Failed to track resource usage: {e}")
    
    async def _cleanup_allocation(self, request_id: str):
        """Clean up allocation and release resources."""
        if request_id in self.active_allocations:
            allocation = self.active_allocations.pop(request_id)
            
            # Release execution slot
            await model_resource_manager.release_execution_slot(
                allocation.allocated_model,
                allocation.expert_id
            )
            
            # Deallocate from GPU load balancer
            gpu_info = allocation.resource_usage.get("gpu_allocation", {})
            if gpu_info.get("gpu_id") is not None:
                processing_time = allocation.resource_usage.get("processing_time", 0.0)
                await gpu_load_balancer.deallocate_request(
                    gpu_info["gpu_id"],
                    allocation.allocated_model,
                    request_id,
                    processing_time
                )
            
            logger.debug(f"Cleaned up allocation for request {request_id}")
    
    def _estimate_duration(self, complexity: ComplexityLevel) -> float:
        """Estimate processing duration based on complexity."""
        duration_estimates = {
            ComplexityLevel.SIMPLE: 10.0,
            ComplexityLevel.MODERATE: 30.0,
            ComplexityLevel.COMPLEX: 60.0,
            ComplexityLevel.EXPERT: 120.0
        }
        return duration_estimates.get(complexity, 30.0)
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and resource utilization."""
        resource_status = await model_resource_manager.get_resource_status()
        queue_status = await model_queue_manager.get_queue_status()
        gpu_status = await gpu_load_balancer.get_load_balancer_status()
        
        # Get analytics data
        try:
            analytics = await get_analytics_service()
            real_time_metrics = await analytics.get_real_time_metrics()
            analytics_report = await analytics.get_service_analytics_report()
        except Exception as e:
            logger.warning(f"Failed to get analytics data: {e}")
            real_time_metrics = {"error": "Analytics unavailable"}
            analytics_report = {"error": "Analytics unavailable"}
        
        return {
            "active_allocations": len(self.active_allocations),
            "resource_manager": resource_status,
            "queue_manager": queue_status,
            "gpu_load_balancer": gpu_status,
            "real_time_metrics": real_time_metrics,
            "service_analytics": analytics_report,
            "service_configurations": self.service_configurations,
            "complexity_mappings": {
                level.value: models for level, models in self.complexity_model_mapping.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def update_service_configuration(
        self, 
        service_name: str, 
        config_updates: Dict[str, Any]
    ):
        """Update service-specific configuration."""
        if service_name in self.service_configurations:
            self.service_configurations[service_name].update(config_updates)
            logger.info(f"Updated configuration for service {service_name}: {config_updates}")
        else:
            logger.warning(f"Unknown service name: {service_name}")


# Global instance
centralized_resource_service = CentralizedResourceService()