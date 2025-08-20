"""
User Expert Settings Service - Manages user-specific expert model configurations
Provides interface to retrieve per-expert model assignments from admin settings.
"""

import logging
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session

from shared.utils.database_setup import get_db_session
from shared.database.models import User

logger = logging.getLogger(__name__)


class UserExpertSettingsService:
    """
    Service for managing user-specific expert model configurations.
    Provides centralized access to admin model settings for parallel execution.
    """
    
    def __init__(self):
        # Default model assignments if user hasn't configured specific models
        self.default_expert_models = {
            "project_manager": "llama3.2:3b",
            "technical_expert": "llama3.1:8b", 
            "business_analyst": "llama3.2:3b",
            "creative_director": "llama3.2:3b",
            "research_specialist": "llama3.1:8b",
            "planning_expert": "llama3.2:3b",
            "socratic_expert": "llama3.2:3b", 
            "wellbeing_coach": "llama3.2:3b",
            "personal_assistant": "mistral:7b",
            "data_analyst": "qwen2.5:7b",
            "output_formatter": "llama3.2:3b",
            "quality_assurance": "llama3.2:3b"
        }
        
        # Field mapping from expert ID to user model field
        self.expert_model_fields = {
            "project_manager": "project_manager_model",
            "technical_expert": "technical_expert_model",
            "business_analyst": "business_analyst_model", 
            "creative_director": "creative_director_model",
            "research_specialist": "research_specialist_model",
            "planning_expert": "planning_expert_model",
            "socratic_expert": "socratic_expert_model",
            "wellbeing_coach": "wellbeing_coach_model",
            "personal_assistant": "personal_assistant_model",
            "data_analyst": "data_analyst_model",
            "output_formatter": "output_formatter_model",
            "quality_assurance": "quality_assurance_model"
        }
    
    async def get_user_expert_models(self, user_id: int) -> Dict[str, str]:
        """
        Get user's configured expert models from admin settings.
        
        Args:
            user_id: The user ID to get settings for
            
        Returns:
            Dictionary mapping expert_id -> model_name
        """
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.warning(f"User {user_id} not found, using default models")
                    return self.default_expert_models.copy()
                
                expert_models = {}
                
                # Get configured models for each expert
                for expert_id, field_name in self.expert_model_fields.items():
                    configured_model = getattr(user, field_name, None)
                    if configured_model:
                        expert_models[expert_id] = configured_model
                        logger.debug(f"User {user_id} configured {expert_id} -> {configured_model}")
                    else:
                        # Fall back to default
                        expert_models[expert_id] = self.default_expert_models[expert_id]
                        logger.debug(f"User {user_id} using default for {expert_id} -> {expert_models[expert_id]}")
                
                logger.info(f"Retrieved expert models for user {user_id}: {len(expert_models)} experts configured")
                return expert_models
                
        except Exception as e:
            logger.error(f"Error retrieving expert models for user {user_id}: {e}", exc_info=True)
            # Return defaults on error
            return self.default_expert_models.copy()
    
    async def get_expert_model(self, user_id: int, expert_id: str) -> str:
        """
        Get the configured model for a specific expert.
        
        Args:
            user_id: The user ID
            expert_id: The expert identifier
            
        Returns:
            Model name for the expert
        """
        expert_models = await self.get_user_expert_models(user_id)
        return expert_models.get(expert_id, self.default_expert_models.get(expert_id, "llama3.2:3b"))
    
    async def update_expert_model(self, user_id: int, expert_id: str, model_name: str) -> bool:
        """
        Update the model assignment for a specific expert.
        
        Args:
            user_id: The user ID
            expert_id: The expert identifier
            model_name: The new model name
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            field_name = self.expert_model_fields.get(expert_id)
            if not field_name:
                logger.error(f"Unknown expert ID: {expert_id}")
                return False
                
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                # Update the model field
                setattr(user, field_name, model_name)
                db.commit()
                
                logger.info(f"Updated {expert_id} model for user {user_id} to {model_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating expert model for user {user_id}: {e}", exc_info=True)
            return False
    
    async def get_user_model_distribution(self, user_id: int) -> Dict[str, Any]:
        """
        Get a summary of user's model distribution across experts.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with model distribution analysis
        """
        expert_models = await self.get_user_expert_models(user_id)
        
        # Count models by category
        model_counts = {}
        category_counts = {
            "small_1b": 0,
            "medium_4b": 0, 
            "large_8b": 0,
            "xlarge_10b": 0
        }
        
        from worker.services.model_resource_manager import model_resource_manager
        
        for expert_id, model_name in expert_models.items():
            # Count model usage
            if model_name not in model_counts:
                model_counts[model_name] = []
            model_counts[model_name].append(expert_id)
            
            # Count by category
            model_info = model_resource_manager.get_model_info(model_name)
            if model_info:
                category = model_info.category.value
                if category in category_counts:
                    category_counts[category] += 1
        
        return {
            "user_id": user_id,
            "total_experts": len(expert_models),
            "unique_models": len(model_counts),
            "model_usage": model_counts,
            "category_distribution": category_counts,
            "parallel_execution_estimate": self._estimate_parallel_execution(category_counts)
        }
    
    def _estimate_parallel_execution(self, category_counts: Dict[str, int]) -> Dict[str, Any]:
        """Estimate parallel execution possibilities based on model distribution."""
        # Based on our resource limits
        limits = {
            "small_1b": 5,
            "medium_4b": 4,
            "large_8b": 3,
            "xlarge_10b": 1
        }
        
        potential_parallel_experts = 0
        bottleneck_category = None
        bottleneck_ratio = 0
        
        for category, count in category_counts.items():
            limit = limits.get(category, 1)
            parallel_count = min(count, limit)
            potential_parallel_experts += parallel_count
            
            # Find bottleneck category
            if count > 0:
                ratio = count / limit
                if ratio > bottleneck_ratio:
                    bottleneck_ratio = ratio
                    bottleneck_category = category
        
        return {
            "max_parallel_experts": potential_parallel_experts,
            "bottleneck_category": bottleneck_category,
            "bottleneck_ratio": bottleneck_ratio,
            "execution_groups_estimate": max(1, sum(
                (count + limits.get(cat, 1) - 1) // limits.get(cat, 1)
                for cat, count in category_counts.items() if count > 0
            ))
        }
    
    async def validate_expert_models(self, user_id: int) -> Dict[str, Any]:
        """
        Validate user's expert model configurations.
        
        Args:
            user_id: The user ID
            
        Returns:
            Validation report with any issues found
        """
        expert_models = await self.get_user_expert_models(user_id)
        
        validation_report = {
            "user_id": user_id,
            "valid_models": [],
            "invalid_models": [],
            "warnings": [],
            "recommendations": []
        }
        
        from worker.services.model_resource_manager import model_resource_manager
        
        for expert_id, model_name in expert_models.items():
            model_info = model_resource_manager.get_model_info(model_name)
            
            if model_info:
                validation_report["valid_models"].append({
                    "expert_id": expert_id,
                    "model_name": model_name,
                    "category": model_info.category.value,
                    "estimated_memory_gb": model_info.estimated_memory_gb
                })
                
                # Add warnings for very large models
                if model_info.category.value == "xlarge_10b":
                    validation_report["warnings"].append(
                        f"{expert_id} uses very large model {model_name} - will block parallel execution"
                    )
            else:
                validation_report["invalid_models"].append({
                    "expert_id": expert_id,
                    "model_name": model_name,
                    "issue": "Model not found in registry"
                })
        
        # Generate recommendations
        distribution = await self.get_user_model_distribution(user_id)
        parallel_estimate = distribution["parallel_execution_estimate"]
        
        if parallel_estimate["bottleneck_category"]:
            validation_report["recommendations"].append(
                f"Consider using smaller models for some experts in {parallel_estimate['bottleneck_category']} category to improve parallelization"
            )
        
        if len(validation_report["invalid_models"]) > 0:
            validation_report["recommendations"].append(
                "Update invalid model assignments to use supported models"
            )
        
        return validation_report


# Global instance
user_expert_settings_service = UserExpertSettingsService()