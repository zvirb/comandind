"""
Agent Configuration Router - Admin API endpoints for Agent Abstraction Layer management
Provides REST endpoints for configuring agent LLM assignments, GPU allocation, and performance monitoring.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_admin_role
from shared.database.models import User, AgentType, LLMProvider, GPUAssignmentStrategy, ModelLoadStrategy
from shared.utils.database_setup import get_db
from shared.services.agent_configuration_service import (
    AgentConfigurationService,
    AgentConfigurationCreate,
    AgentConfigurationUpdate,
    AgentConfigurationResponse,
    agent_configuration_service
)
from worker.services.agent_llm_manager import agent_llm_manager
from worker.services.agent_gpu_resource_manager import agent_gpu_resource_manager
from worker.services.agent_api_abstraction import agent_api_abstraction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/agent-config", tags=["Agent Configuration"])


# Pydantic models for API requests/responses
from pydantic import BaseModel, Field
from datetime import datetime


class AgentConfigCreateRequest(BaseModel):
    """Request model for creating agent configuration."""
    agent_type: AgentType
    agent_name: str = Field(..., min_length=1, max_length=255)
    agent_description: Optional[str] = Field(None, max_length=1000)
    llm_provider: LLMProvider
    model_name: str = Field(..., min_length=1, max_length=255)
    model_parameters: Optional[Dict[str, Any]] = None
    gpu_assignment: Optional[int] = Field(None, ge=0, le=2)
    gpu_assignment_strategy: GPUAssignmentStrategy = GPUAssignmentStrategy.AUTO
    model_load_strategy: ModelLoadStrategy = ModelLoadStrategy.ON_DEMAND
    max_context_length: Optional[int] = Field(None, gt=0)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    timeout_seconds: int = Field(300, gt=0, le=3600)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    capabilities: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    memory_limit_mb: Optional[int] = Field(None, gt=0)
    token_budget_per_hour: Optional[int] = Field(None, gt=0)
    max_concurrent_requests: int = Field(1, ge=1, le=10)
    is_active: bool = True
    priority: int = Field(5, ge=1, le=10)


class AgentConfigUpdateRequest(BaseModel):
    """Request model for updating agent configuration."""
    agent_name: Optional[str] = Field(None, min_length=1, max_length=255)
    agent_description: Optional[str] = Field(None, max_length=1000)
    llm_provider: Optional[LLMProvider] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=255)
    model_parameters: Optional[Dict[str, Any]] = None
    gpu_assignment: Optional[int] = Field(None, ge=0, le=2)
    gpu_assignment_strategy: Optional[GPUAssignmentStrategy] = None
    model_load_strategy: Optional[ModelLoadStrategy] = None
    max_context_length: Optional[int] = Field(None, gt=0)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    timeout_seconds: Optional[int] = Field(None, gt=0, le=3600)
    system_prompt: Optional[str] = Field(None, max_length=10000)
    capabilities: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    memory_limit_mb: Optional[int] = Field(None, gt=0)
    token_budget_per_hour: Optional[int] = Field(None, gt=0)
    max_concurrent_requests: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)


class GPUTestRequest(BaseModel):
    """Request model for testing GPU allocation."""
    agent_type: AgentType
    model_name: str
    estimated_memory_mb: float = Field(..., gt=0)
    priority: int = Field(5, ge=1, le=10)


@router.get("/configurations", response_model=List[AgentConfigurationResponse])
async def get_all_configurations(
    include_inactive: bool = Query(False, description="Include inactive configurations"),
    include_metrics: bool = Query(True, description="Include performance metrics"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get all agent configurations."""
    try:
        configurations = await agent_configuration_service.get_all_configurations(
            include_inactive=include_inactive,
            include_metrics=include_metrics
        )
        return configurations
    except Exception as e:
        logger.error(f"Error retrieving configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configurations"
        )


@router.get("/configurations/{agent_type}", response_model=AgentConfigurationResponse)
async def get_configuration(
    agent_type: AgentType,
    include_metrics: bool = Query(True, description="Include performance metrics"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get configuration for a specific agent type."""
    try:
        configuration = await agent_configuration_service.get_configuration(
            agent_type=agent_type,
            include_metrics=include_metrics
        )
        
        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No configuration found for agent type: {agent_type}"
            )
        
        return configuration
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving configuration for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.post("/configurations", response_model=AgentConfigurationResponse)
async def create_configuration(
    config_request: AgentConfigCreateRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Create a new agent configuration."""
    try:
        config_data = AgentConfigurationCreate(
            agent_type=config_request.agent_type,
            agent_name=config_request.agent_name,
            agent_description=config_request.agent_description,
            llm_provider=config_request.llm_provider,
            model_name=config_request.model_name,
            model_parameters=config_request.model_parameters,
            gpu_assignment=config_request.gpu_assignment,
            gpu_assignment_strategy=config_request.gpu_assignment_strategy,
            model_load_strategy=config_request.model_load_strategy,
            max_context_length=config_request.max_context_length,
            temperature=config_request.temperature,
            max_tokens=config_request.max_tokens,
            timeout_seconds=config_request.timeout_seconds,
            system_prompt=config_request.system_prompt,
            capabilities=config_request.capabilities,
            constraints=config_request.constraints,
            memory_limit_mb=config_request.memory_limit_mb,
            token_budget_per_hour=config_request.token_budget_per_hour,
            max_concurrent_requests=config_request.max_concurrent_requests,
            is_active=config_request.is_active,
            priority=config_request.priority,
            created_by_user_id=current_user.id
        )
        
        configuration = await agent_configuration_service.create_configuration(config_data)
        
        logger.info(f"Admin {current_user.email} created configuration for {config_request.agent_type}")
        
        return configuration
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create configuration"
        )


@router.put("/configurations/{agent_type}", response_model=AgentConfigurationResponse)
async def update_configuration(
    agent_type: AgentType,
    update_request: AgentConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Update an existing agent configuration."""
    try:
        update_data = AgentConfigurationUpdate(
            agent_name=update_request.agent_name,
            agent_description=update_request.agent_description,
            llm_provider=update_request.llm_provider,
            model_name=update_request.model_name,
            model_parameters=update_request.model_parameters,
            gpu_assignment=update_request.gpu_assignment,
            gpu_assignment_strategy=update_request.gpu_assignment_strategy,
            model_load_strategy=update_request.model_load_strategy,
            max_context_length=update_request.max_context_length,
            temperature=update_request.temperature,
            max_tokens=update_request.max_tokens,
            timeout_seconds=update_request.timeout_seconds,
            system_prompt=update_request.system_prompt,
            capabilities=update_request.capabilities,
            constraints=update_request.constraints,
            memory_limit_mb=update_request.memory_limit_mb,
            token_budget_per_hour=update_request.token_budget_per_hour,
            max_concurrent_requests=update_request.max_concurrent_requests,
            is_active=update_request.is_active,
            priority=update_request.priority
        )
        
        configuration = await agent_configuration_service.update_configuration(
            agent_type=agent_type,
            update_data=update_data
        )
        
        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No configuration found for agent type: {agent_type}"
            )
        
        logger.info(f"Admin {current_user.email} updated configuration for {agent_type}")
        
        return configuration
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating configuration for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )


@router.delete("/configurations/{agent_type}")
async def delete_configuration(
    agent_type: AgentType,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Delete (deactivate) an agent configuration."""
    try:
        success = await agent_configuration_service.delete_configuration(agent_type)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No configuration found for agent type: {agent_type}"
            )
        
        logger.info(f"Admin {current_user.email} deleted configuration for {agent_type}")
        
        return {"message": f"Configuration for {agent_type} has been deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting configuration for {agent_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration"
        )


@router.post("/configurations/defaults")
async def create_default_configurations(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Create default configurations for all agent types."""
    try:
        configurations = await agent_configuration_service.create_default_configurations(
            user_id=current_user.id
        )
        
        logger.info(f"Admin {current_user.email} created {len(configurations)} default configurations")
        
        return {
            "message": f"Created {len(configurations)} default configurations",
            "configurations": configurations
        }
    except Exception as e:
        logger.error(f"Error creating default configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create default configurations"
        )


@router.get("/templates")
async def get_configuration_templates(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get configuration templates for different use cases."""
    try:
        templates = await agent_configuration_service.get_configuration_templates()
        return templates
    except Exception as e:
        logger.error(f"Error retrieving templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get comprehensive system status for Agent Abstraction Layer."""
    try:
        # Initialize services if needed
        if not agent_api_abstraction._initialized:
            await agent_api_abstraction.initialize()
        
        status = await agent_api_abstraction.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Error retrieving system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system status"
        )


@router.get("/gpu/status")
async def get_gpu_status(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get GPU resource allocation status."""
    try:
        status = await agent_gpu_resource_manager.get_gpu_status()
        return status
    except Exception as e:
        logger.error(f"Error retrieving GPU status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve GPU status"
        )


@router.post("/gpu/test-allocation")
async def test_gpu_allocation(
    test_request: GPUTestRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Test GPU allocation for an agent without permanent assignment."""
    try:
        from worker.services.agent_gpu_resource_manager import GPUAllocationRequest
        
        allocation_request = GPUAllocationRequest(
            agent_type=test_request.agent_type,
            model_name=test_request.model_name,
            estimated_memory_mb=test_request.estimated_memory_mb,
            priority=test_request.priority,
            max_wait_time_seconds=30
        )
        
        # Initialize GPU manager if needed
        if not hasattr(agent_gpu_resource_manager, '_initialized') or not agent_gpu_resource_manager._initialized:
            await agent_gpu_resource_manager.initialize()
        
        result = await agent_gpu_resource_manager.allocate_gpu_for_agent(allocation_request)
        
        # Release allocation immediately (this is just a test)
        if result.success and result.allocated_gpu_id is not None:
            await agent_gpu_resource_manager.release_gpu_for_agent(
                test_request.agent_type, 
                test_request.estimated_memory_mb
            )
        
        return {
            "test_result": {
                "success": result.success,
                "allocated_gpu_id": result.allocated_gpu_id,
                "allocated_memory_mb": result.allocated_memory_mb,
                "wait_time_seconds": result.wait_time_seconds,
                "error_message": result.error_message,
                "alternative_suggestions": result.alternative_suggestions
            },
            "note": "This was a test allocation - resources have been released"
        }
    except Exception as e:
        logger.error(f"Error testing GPU allocation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test GPU allocation"
        )


@router.post("/optimize")
async def optimize_configurations(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Optimize agent configurations based on performance metrics."""
    try:
        optimization_results = await agent_configuration_service.optimize_configurations()
        
        logger.info(f"Admin {current_user.email} ran configuration optimization")
        
        return optimization_results
    except Exception as e:
        logger.error(f"Error optimizing configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize configurations"
        )


@router.post("/system/optimize")
async def optimize_system_performance(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Optimize overall system performance including GPU allocation."""
    try:
        # Initialize if needed
        if not agent_api_abstraction._initialized:
            await agent_api_abstraction.initialize()
        
        optimization_results = await agent_api_abstraction.optimize_system_performance()
        
        logger.info(f"Admin {current_user.email} ran system performance optimization")
        
        return optimization_results
    except Exception as e:
        logger.error(f"Error optimizing system performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to optimize system performance"
        )


@router.get("/agent-types")
async def get_available_agent_types(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get list of available agent types."""
    return {
        "agent_types": [
            {
                "value": agent_type.value,
                "label": agent_type.value.replace("_", " ").title(),
                "description": f"Agent specialized in {agent_type.value.replace('_', ' ')}"
            }
            for agent_type in AgentType
        ]
    }


@router.get("/llm-providers")
async def get_available_llm_providers(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_admin_role)
):
    """Get list of available LLM providers."""
    try:
        # Check which providers are actually available
        from worker.services.model_provider_factory import model_provider_factory
        
        if not model_provider_factory._initialized:
            await model_provider_factory.initialize()
        
        available_providers = await model_provider_factory.get_available_providers()
        
        provider_info = []
        for provider in LLMProvider:
            provider_info.append({
                "value": provider.value,
                "label": provider.value.title(),
                "available": provider in available_providers,
                "description": f"{provider.value.title()} language model provider"
            })
        
        return {
            "providers": provider_info,
            "available_count": len(available_providers)
        }
    except Exception as e:
        logger.error(f"Error retrieving LLM providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve LLM providers"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for Agent Abstraction Layer."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "agent_configuration_service": "healthy",
                "agent_llm_manager": "unknown",
                "agent_gpu_resource_manager": "unknown",
                "agent_api_abstraction": "unknown"
            }
        }
        
        # Check service initialization status
        if hasattr(agent_api_abstraction, '_initialized'):
            health_status["services"]["agent_api_abstraction"] = "healthy" if agent_api_abstraction._initialized else "not_initialized"
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )