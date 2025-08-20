"""
Agent Configuration Service - Persistent management of agent configurations
Handles CRUD operations, validation, and optimization of agent LLM and GPU assignments.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError

# TEMPORARILY USING LEGACY MODELS: New models not available yet
from shared.database.models import (
    LegacyAgentConfiguration as AgentConfiguration, 
    LegacyAgentMetrics as AgentMetrics, 
    LegacyGPUResourceAllocation as GPUResourceAllocation,
    AgentType, 
    LLMProvider, 
    GPUAssignmentStrategy, 
    ModelLoadStrategy,
    User
)
from shared.utils.database_setup import get_db

logger = logging.getLogger(__name__)


@dataclass
class AgentConfigurationCreate:
    """Data transfer object for creating agent configurations."""
    agent_type: AgentType
    agent_name: str
    agent_description: Optional[str] = None
    llm_provider: LLMProvider = LLMProvider.OLLAMA
    model_name: str = "llama3.2:3b"
    model_parameters: Optional[Dict[str, Any]] = None
    gpu_assignment: Optional[int] = None
    gpu_assignment_strategy: GPUAssignmentStrategy = GPUAssignmentStrategy.AUTO
    model_load_strategy: ModelLoadStrategy = ModelLoadStrategy.ON_DEMAND
    max_context_length: Optional[int] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout_seconds: int = 300
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    memory_limit_mb: Optional[int] = None
    token_budget_per_hour: Optional[int] = None
    max_concurrent_requests: int = 1
    is_active: bool = True
    is_default: bool = False
    priority: int = 5
    created_by_user_id: Optional[int] = None


@dataclass
class AgentConfigurationUpdate:
    """Data transfer object for updating agent configurations."""
    agent_name: Optional[str] = None
    agent_description: Optional[str] = None
    llm_provider: Optional[LLMProvider] = None
    model_name: Optional[str] = None
    model_parameters: Optional[Dict[str, Any]] = None
    gpu_assignment: Optional[int] = None
    gpu_assignment_strategy: Optional[GPUAssignmentStrategy] = None
    model_load_strategy: Optional[ModelLoadStrategy] = None
    max_context_length: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    memory_limit_mb: Optional[int] = None
    token_budget_per_hour: Optional[int] = None
    max_concurrent_requests: Optional[int] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


@dataclass
class AgentConfigurationResponse:
    """Response object for agent configuration queries."""
    id: int
    agent_type: AgentType
    agent_name: str
    agent_description: Optional[str]
    llm_provider: LLMProvider
    model_name: str
    model_parameters: Optional[Dict[str, Any]]
    gpu_assignment: Optional[int]
    gpu_assignment_strategy: GPUAssignmentStrategy
    model_load_strategy: ModelLoadStrategy
    max_context_length: Optional[int]
    temperature: Optional[float]
    max_tokens: Optional[int]
    timeout_seconds: Optional[int]
    system_prompt: Optional[str]
    capabilities: Optional[List[str]]
    constraints: Optional[Dict[str, Any]]
    memory_limit_mb: Optional[int]
    token_budget_per_hour: Optional[int]
    max_concurrent_requests: Optional[int]
    is_active: bool
    is_default: bool
    priority: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_by_user_id: Optional[int]
    
    # Performance metrics
    recent_usage_count: Optional[int] = None
    avg_response_time_ms: Optional[float] = None
    success_rate_percent: Optional[float] = None
    total_tokens_consumed: Optional[int] = None


class AgentConfigurationService:
    """
    Service for managing agent configurations with validation and optimization.
    
    Features:
    - CRUD operations for agent configurations
    - Configuration validation and conflict resolution
    - Performance metrics integration
    - GPU resource optimization
    - Configuration templates and presets
    - Bulk operations and migration support
    """
    
    def __init__(self):
        # Database access uses get_db() context manager instead
        
        # Default configurations for each agent type
        self.default_configurations = {
            AgentType.PROJECT_MANAGER: {
                "agent_name": "Project Manager",
                "agent_description": "Coordinates team activities and manages project workflows",
                "llm_provider": LLMProvider.OLLAMA,
                "model_name": "llama3.2:3b",
                "gpu_assignment": 0,
                "system_prompt": "You are a skilled project manager focused on coordinating team activities, managing timelines, and ensuring project success.",
                "capabilities": ["project_planning", "team_coordination", "deadline_management", "resource_allocation"],
                "priority": 8
            },
            AgentType.RESEARCH_SPECIALIST: {
                "agent_name": "Research Specialist",
                "agent_description": "Conducts thorough research and analysis using web search and knowledge bases",
                "llm_provider": LLMProvider.ANTHROPIC,
                "model_name": "claude-3-opus",
                "gpu_assignment": 1,
                "system_prompt": "You are a research specialist with expertise in gathering, analyzing, and synthesizing information from multiple sources.",
                "capabilities": ["web_search", "data_analysis", "report_writing", "fact_checking"],
                "priority": 9
            },
            AgentType.BUSINESS_ANALYST: {
                "agent_name": "Business Analyst",
                "agent_description": "Analyzes business requirements and provides strategic insights",
                "llm_provider": LLMProvider.OPENAI,
                "model_name": "gpt-4",
                "gpu_assignment": 1,
                "system_prompt": "You are a business analyst specializing in requirements analysis, process optimization, and strategic planning.",
                "capabilities": ["requirements_analysis", "process_modeling", "stakeholder_management", "roi_analysis"],
                "priority": 7
            },
            AgentType.TECHNICAL_EXPERT: {
                "agent_name": "Technical Expert",
                "agent_description": "Provides technical expertise and solutions for complex technical challenges",
                "llm_provider": LLMProvider.OLLAMA,
                "model_name": "llama3.1:8b",
                "gpu_assignment": 2,
                "system_prompt": "You are a technical expert with deep knowledge in software development, system architecture, and technology solutions.",
                "capabilities": ["code_review", "architecture_design", "troubleshooting", "technology_assessment"],
                "priority": 8
            },
            AgentType.FINANCIAL_ADVISOR: {
                "agent_name": "Financial Advisor",
                "agent_description": "Provides financial analysis and investment guidance",
                "llm_provider": LLMProvider.ANTHROPIC,
                "model_name": "claude-3-sonnet",
                "gpu_assignment": 0,
                "system_prompt": "You are a financial advisor with expertise in financial planning, investment analysis, and risk management.",
                "capabilities": ["financial_planning", "investment_analysis", "risk_assessment", "budgeting"],
                "priority": 6
            },
            # Add more default configurations as needed
        }
    
    async def create_configuration(
        self, 
        config_data: AgentConfigurationCreate
    ) -> AgentConfigurationResponse:
        """
        Create a new agent configuration.
        
        Args:
            config_data: Configuration data for the new agent
            
        Returns:
            Created agent configuration
            
        Raises:
            ValueError: If configuration is invalid
            IntegrityError: If agent type already has a configuration
        """
        for db in get_db():
            try:
                # Validate configuration
                await self._validate_configuration(db, config_data)
                
                # Check if configuration already exists for this agent type
                existing = db.query(AgentConfiguration).filter(
                    AgentConfiguration.agent_type == config_data.agent_type
                ).first()
                
                if existing and not config_data.is_default:
                    raise ValueError(f"Configuration already exists for agent type: {config_data.agent_type}")
                
                # Create new configuration
                config = AgentConfiguration(
                    agent_type=config_data.agent_type,
                    agent_name=config_data.agent_name,
                    agent_description=config_data.agent_description,
                    llm_provider=config_data.llm_provider,
                    model_name=config_data.model_name,
                    model_parameters=config_data.model_parameters,
                    gpu_assignment=config_data.gpu_assignment,
                    gpu_assignment_strategy=config_data.gpu_assignment_strategy,
                    model_load_strategy=config_data.model_load_strategy,
                    max_context_length=config_data.max_context_length,
                    temperature=config_data.temperature,
                    max_tokens=config_data.max_tokens,
                    timeout_seconds=config_data.timeout_seconds,
                    system_prompt=config_data.system_prompt,
                    capabilities=config_data.capabilities,
                    constraints=config_data.constraints,
                    memory_limit_mb=config_data.memory_limit_mb,
                    token_budget_per_hour=config_data.token_budget_per_hour,
                    max_concurrent_requests=config_data.max_concurrent_requests,
                    is_active=config_data.is_active,
                    is_default=config_data.is_default,
                    priority=config_data.priority,
                    created_by_user_id=config_data.created_by_user_id
                )
                
                db.add(config)
                db.commit()
                db.refresh(config)
                
                logger.info(f"Created configuration for {config_data.agent_type}: {config_data.model_name}")
                
                return await self._config_to_response(db, config)
                
            except IntegrityError as e:
                db.rollback()
                logger.error(f"Integrity error creating configuration: {e}")
                raise ValueError("Configuration violates database constraints")
            except Exception as e:
                db.rollback()
                logger.error(f"Error creating configuration: {e}")
                raise
    
    async def get_configuration(
        self, 
        agent_type: AgentType, 
        include_metrics: bool = True
    ) -> Optional[AgentConfigurationResponse]:
        """
        Get configuration for a specific agent type.
        
        Args:
            agent_type: Type of agent to get configuration for
            include_metrics: Whether to include performance metrics
            
        Returns:
            Agent configuration or None if not found
        """
        for db in get_db():
            config = db.query(AgentConfiguration).filter(
                and_(
                    AgentConfiguration.agent_type == agent_type,
                    AgentConfiguration.is_active == True
                )
            ).order_by(desc(AgentConfiguration.priority)).first()
            
            if not config:
                return None
            
            return await self._config_to_response(db, config, include_metrics)
    
    async def get_all_configurations(
        self, 
        include_inactive: bool = False,
        include_metrics: bool = True
    ) -> List[AgentConfigurationResponse]:
        """
        Get all agent configurations.
        
        Args:
            include_inactive: Whether to include inactive configurations
            include_metrics: Whether to include performance metrics
            
        Returns:
            List of agent configurations
        """
        for db in get_db():
            query = db.query(AgentConfiguration)
            
            if not include_inactive:
                query = query.filter(AgentConfiguration.is_active == True)
            
            configs = query.order_by(
                AgentConfiguration.agent_type,
                desc(AgentConfiguration.priority)
            ).all()
            
            return [await self._config_to_response(db, config, include_metrics) for config in configs]
    
    async def update_configuration(
        self, 
        agent_type: AgentType, 
        update_data: AgentConfigurationUpdate
    ) -> Optional[AgentConfigurationResponse]:
        """
        Update an existing agent configuration.
        
        Args:
            agent_type: Type of agent to update
            update_data: Updated configuration data
            
        Returns:
            Updated configuration or None if not found
        """
        for db in get_db():
            try:
                config = db.query(AgentConfiguration).filter(
                    AgentConfiguration.agent_type == agent_type
                ).first()
                
                if not config:
                    return None
                
                # Update fields
                for field, value in update_data.__dict__.items():
                    if value is not None and hasattr(config, field):
                        setattr(config, field, value)
                
                config.updated_at = datetime.now(timezone.utc)
                
                # Validate updated configuration
                await self._validate_configuration_update(db, config)
                
                db.commit()
                db.refresh(config)
                
                logger.info(f"Updated configuration for {agent_type}")
                
                return await self._config_to_response(db, config)
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error updating configuration for {agent_type}: {e}")
                raise
    
    async def delete_configuration(self, agent_type: AgentType) -> bool:
        """
        Delete an agent configuration.
        
        Args:
            agent_type: Type of agent to delete configuration for
            
        Returns:
            True if deleted, False if not found
        """
        for db in get_db():
            try:
                config = db.query(AgentConfiguration).filter(
                    AgentConfiguration.agent_type == agent_type
                ).first()
                
                if not config:
                    return False
                
                # Soft delete by setting inactive
                config.is_active = False
                config.updated_at = datetime.now(timezone.utc)
                
                db.commit()
                
                logger.info(f"Deleted (deactivated) configuration for {agent_type}")
                return True
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error deleting configuration for {agent_type}: {e}")
                raise
    
    async def create_default_configurations(self, user_id: Optional[int] = None) -> List[AgentConfigurationResponse]:
        """
        Create default configurations for all agent types.
        
        Args:
            user_id: ID of user creating the configurations
            
        Returns:
            List of created configurations
        """
        created_configs = []
        
        for agent_type, defaults in self.default_configurations.items():
            try:
                # Check if configuration already exists
                existing = await self.get_configuration(agent_type, include_metrics=False)
                if existing:
                    logger.info(f"Configuration already exists for {agent_type}, skipping")
                    continue
                
                config_data = AgentConfigurationCreate(
                    agent_type=agent_type,
                    created_by_user_id=user_id,
                    is_default=True,
                    **defaults
                )
                
                created_config = await self.create_configuration(config_data)
                created_configs.append(created_config)
                
                logger.info(f"Created default configuration for {agent_type}")
                
            except Exception as e:
                logger.error(f"Failed to create default configuration for {agent_type}: {e}")
                continue
        
        return created_configs
    
    async def optimize_configurations(self) -> Dict[str, Any]:
        """
        Optimize agent configurations based on performance metrics.
        
        Returns:
            Optimization results and recommendations
        """
        optimization_results = {
            "analyzed_configurations": 0,
            "recommendations": [],
            "actions_taken": [],
            "performance_improvements": {}
        }
        
        for db in get_db():
            try:
                # Get all active configurations
                configs = db.query(AgentConfiguration).filter(
                    AgentConfiguration.is_active == True
                ).all()
                
                optimization_results["analyzed_configurations"] = len(configs)
                
                for config in configs:
                    # Analyze performance metrics
                    recent_metrics = db.query(AgentMetrics).filter(
                        and_(
                            AgentMetrics.agent_config_id == config.id,
                            AgentMetrics.period_start >= datetime.now(timezone.utc) - timedelta(days=7)
                        )
                    ).all()
                    
                    if not recent_metrics:
                        continue
                    
                    # Calculate performance indicators
                    total_requests = sum(m.total_requests for m in recent_metrics)
                    avg_response_time = sum(m.average_response_time_ms or 0 for m in recent_metrics) / len(recent_metrics)
                    avg_success_rate = sum(m.success_rate_percent or 100 for m in recent_metrics) / len(recent_metrics)
                    
                    # Generate recommendations
                    if avg_response_time > 5000:  # > 5 seconds
                        optimization_results["recommendations"].append({
                            "agent_type": config.agent_type.value,
                            "issue": "high_latency",
                            "current_value": f"{avg_response_time:.0f}ms",
                            "recommendation": "Consider using a smaller model or GPU optimization",
                            "priority": "high"
                        })
                    
                    if avg_success_rate < 95:  # < 95% success rate
                        optimization_results["recommendations"].append({
                            "agent_type": config.agent_type.value,
                            "issue": "low_success_rate",
                            "current_value": f"{avg_success_rate:.1f}%",
                            "recommendation": "Review model configuration and timeout settings",
                            "priority": "high"
                        })
                    
                    if total_requests < 10:  # Underutilized
                        optimization_results["recommendations"].append({
                            "agent_type": config.agent_type.value,
                            "issue": "underutilized",
                            "current_value": f"{total_requests} requests/week",
                            "recommendation": "Consider consolidating with similar agents or reducing resources",
                            "priority": "low"
                        })
                
            except Exception as e:
                logger.error(f"Error in configuration optimization: {e}")
                optimization_results["error"] = str(e)
        
        return optimization_results
    
    async def get_configuration_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration templates for different use cases.
        
        Returns:
            Dictionary of template configurations
        """
        templates = {
            "high_performance": {
                "description": "Optimized for maximum performance and quality",
                "llm_provider": LLMProvider.ANTHROPIC,
                "model_name": "claude-3-opus",
                "temperature": 0.3,
                "max_tokens": 8192,
                "timeout_seconds": 600,
                "model_load_strategy": ModelLoadStrategy.PRELOAD,
                "gpu_assignment_strategy": GPUAssignmentStrategy.EXCLUSIVE
            },
            "cost_optimized": {
                "description": "Optimized for cost efficiency",
                "llm_provider": LLMProvider.OLLAMA,
                "model_name": "llama3.2:1b",
                "temperature": 0.7,
                "max_tokens": 2048,
                "timeout_seconds": 180,
                "model_load_strategy": ModelLoadStrategy.ON_DEMAND,
                "gpu_assignment_strategy": GPUAssignmentStrategy.SHARED
            },
            "balanced": {
                "description": "Balanced performance and cost",
                "llm_provider": LLMProvider.OLLAMA,
                "model_name": "llama3.2:3b",
                "temperature": 0.7,
                "max_tokens": 4096,
                "timeout_seconds": 300,
                "model_load_strategy": ModelLoadStrategy.ON_DEMAND,
                "gpu_assignment_strategy": GPUAssignmentStrategy.AUTO
            },
            "development": {
                "description": "Fast response for development and testing",
                "llm_provider": LLMProvider.OLLAMA,
                "model_name": "llama3.2:1b",
                "temperature": 0.5,
                "max_tokens": 1024,
                "timeout_seconds": 60,
                "model_load_strategy": ModelLoadStrategy.PRELOAD,
                "gpu_assignment_strategy": GPUAssignmentStrategy.SHARED
            }
        }
        
        return templates
    
    async def _validate_configuration(self, db: Session, config_data: AgentConfigurationCreate):
        """Validate configuration data."""
        # Validate GPU assignment
        if config_data.gpu_assignment is not None:
            if config_data.gpu_assignment not in [0, 1, 2]:
                raise ValueError("GPU assignment must be 0, 1, or 2")
            
            # Check if GPU exists
            gpu_alloc = db.query(GPUResourceAllocation).filter(
                GPUResourceAllocation.gpu_id == config_data.gpu_assignment
            ).first()
            
            if not gpu_alloc:
                raise ValueError(f"GPU {config_data.gpu_assignment} not found")
        
        # Validate model parameters
        if config_data.temperature is not None:
            if not 0.0 <= config_data.temperature <= 2.0:
                raise ValueError("Temperature must be between 0.0 and 2.0")
        
        if config_data.max_tokens is not None:
            if config_data.max_tokens <= 0:
                raise ValueError("Max tokens must be positive")
        
        if config_data.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        
        if not 1 <= config_data.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")
    
    async def _validate_configuration_update(self, db: Session, config: AgentConfiguration):
        """Validate configuration update."""
        # Similar validation as create, but for existing config
        if config.gpu_assignment is not None:
            if config.gpu_assignment not in [0, 1, 2]:
                raise ValueError("GPU assignment must be 0, 1, or 2")
        
        if config.temperature is not None:
            if not 0.0 <= config.temperature <= 2.0:
                raise ValueError("Temperature must be between 0.0 and 2.0")
    
    async def _config_to_response(
        self, 
        db: Session, 
        config: AgentConfiguration, 
        include_metrics: bool = True
    ) -> AgentConfigurationResponse:
        """Convert configuration model to response object."""
        response = AgentConfigurationResponse(
            id=config.id,
            agent_type=config.agent_type,
            agent_name=config.agent_name,
            agent_description=config.agent_description,
            llm_provider=config.llm_provider,
            model_name=config.model_name,
            model_parameters=config.model_parameters,
            gpu_assignment=config.gpu_assignment,
            gpu_assignment_strategy=config.gpu_assignment_strategy,
            model_load_strategy=config.model_load_strategy,
            max_context_length=config.max_context_length,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout_seconds=config.timeout_seconds,
            system_prompt=config.system_prompt,
            capabilities=config.capabilities,
            constraints=config.constraints,
            memory_limit_mb=config.memory_limit_mb,
            token_budget_per_hour=config.token_budget_per_hour,
            max_concurrent_requests=config.max_concurrent_requests,
            is_active=config.is_active,
            is_default=config.is_default,
            priority=config.priority,
            created_at=config.created_at,
            updated_at=config.updated_at,
            last_used_at=config.last_used_at,
            created_by_user_id=config.created_by_user_id
        )
        
        if include_metrics:
            # Get recent metrics
            recent_metrics = db.query(AgentMetrics).filter(
                and_(
                    AgentMetrics.agent_config_id == config.id,
                    AgentMetrics.period_start >= datetime.now(timezone.utc) - timedelta(hours=24)
                )
            ).all()
            
            if recent_metrics:
                response.recent_usage_count = sum(m.total_requests for m in recent_metrics)
                response.avg_response_time_ms = sum(m.average_response_time_ms or 0 for m in recent_metrics) / len(recent_metrics)
                response.success_rate_percent = sum(m.success_rate_percent or 100 for m in recent_metrics) / len(recent_metrics)
                response.total_tokens_consumed = sum(m.total_tokens_consumed for m in recent_metrics)
        
        return response


# Global instance
agent_configuration_service = AgentConfigurationService()