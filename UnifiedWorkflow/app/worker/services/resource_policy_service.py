"""
Resource Policy Service - Enterprise Resource Allocation Management
Provides configurable policies for GPU resource allocation, model selection, and performance optimization.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path

from worker.services.model_resource_manager import ModelCategory
from worker.services.centralized_resource_service import ComplexityLevel
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)


class PolicyPriority(str, Enum):
    """Priority levels for resource allocation policies."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceActionType(str, Enum):
    """Types of resource actions that can be configured."""
    ALLOW = "allow"
    RESTRICT = "restrict"
    PREFER = "prefer"
    FALLBACK = "fallback"


@dataclass
class ServiceResourcePolicy:
    """Resource allocation policy for a specific service."""
    service_name: str
    max_concurrent_requests: int = 10
    allowed_model_categories: List[ModelCategory] = field(default_factory=lambda: list(ModelCategory))
    preferred_models: List[str] = field(default_factory=list)
    fallback_models: List[str] = field(default_factory=list)
    complexity_overrides: Dict[str, ComplexityLevel] = field(default_factory=dict)
    timeout_seconds: int = 300
    priority: PolicyPriority = PolicyPriority.NORMAL
    queue_priority_boost: float = 1.0  # Multiplier for queue priority
    memory_limit_gb: Optional[float] = None
    enabled: bool = True


@dataclass
class UserResourcePolicy:
    """Resource allocation policy for specific users or user groups."""
    user_id: Optional[str] = None
    user_group: Optional[str] = None
    max_concurrent_requests: int = 5
    allowed_services: List[str] = field(default_factory=list)
    allowed_model_categories: List[ModelCategory] = field(default_factory=lambda: list(ModelCategory))
    daily_request_limit: Optional[int] = None
    hourly_request_limit: Optional[int] = None
    priority: PolicyPriority = PolicyPriority.NORMAL
    quota_reset_hour: int = 0  # Hour of day when daily quotas reset (0-23)
    enabled: bool = True


@dataclass
class SystemResourcePolicy:
    """System-wide resource allocation policies."""
    max_total_concurrent_requests: int = 50
    gpu_memory_threshold_percent: float = 80.0
    model_unload_threshold_minutes: int = 10
    emergency_fallback_enabled: bool = True
    load_balancing_enabled: bool = True
    adaptive_scaling_enabled: bool = True
    performance_monitoring_enabled: bool = True
    security_validation_enabled: bool = True


@dataclass
class PerformanceOptimizationPolicy:
    """Policies for performance optimization and resource efficiency."""
    enable_model_preloading: bool = True
    enable_intelligent_caching: bool = True
    enable_request_batching: bool = True
    batch_size_limit: int = 5
    batch_timeout_seconds: float = 2.0
    enable_complexity_prediction: bool = True
    enable_usage_analytics: bool = True
    optimization_interval_minutes: int = 15


class ResourcePolicyService:
    """
    Enterprise resource allocation policy management service.
    Provides configurable policies for GPU resources, model selection, and performance optimization.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.policy_file_path = Path("config/resource_policies.json")
        
        # Default policies
        self.system_policy = SystemResourcePolicy()
        self.performance_policy = PerformanceOptimizationPolicy()
        self.service_policies: Dict[str, ServiceResourcePolicy] = {}
        self.user_policies: Dict[str, UserResourcePolicy] = {}
        
        # Usage tracking for quota enforcement
        self.usage_tracking: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default service policies
        self._initialize_default_policies()
        
        # Load policies from configuration file if it exists
        asyncio.create_task(self.load_policies())
    
    def _initialize_default_policies(self):
        """Initialize default resource policies for all services."""
        
        # Simple Chat Policy - Fast, lightweight responses
        self.service_policies["simple_chat"] = ServiceResourcePolicy(
            service_name="simple_chat",
            max_concurrent_requests=15,
            allowed_model_categories=[ModelCategory.SMALL_1B, ModelCategory.MEDIUM_4B, ModelCategory.LARGE_8B],
            preferred_models=["llama3.2:1b", "llama3.2:3b", "llama3.1:8b"],
            fallback_models=["llama3.2:1b"],
            timeout_seconds=120,
            priority=PolicyPriority.HIGH,  # High priority for fast responses
            queue_priority_boost=1.2
        )
        
        # Smart Router Policy - Complex reasoning and planning
        self.service_policies["smart_router"] = ServiceResourcePolicy(
            service_name="smart_router",
            max_concurrent_requests=8,
            allowed_model_categories=list(ModelCategory),  # Allow all categories
            preferred_models=["llama3.1:8b", "qwen2.5:7b", "qwen2.5:14b"],
            fallback_models=["llama3.1:8b", "llama3.2:3b"],
            timeout_seconds=600,
            priority=PolicyPriority.NORMAL,
            queue_priority_boost=1.0
        )
        
        # Expert Group Policy - Maximum capability for expert discussions
        self.service_policies["expert_group"] = ServiceResourcePolicy(
            service_name="expert_group",
            max_concurrent_requests=5,
            allowed_model_categories=list(ModelCategory),
            preferred_models=["qwen2.5:14b", "qwen2.5:32b", "llama3.1:70b"],
            fallback_models=["llama3.1:8b", "qwen2.5:7b"],
            timeout_seconds=900,
            priority=PolicyPriority.HIGH,
            queue_priority_boost=1.5
        )
        
        # Helios Policy - Enterprise multi-agent system
        self.service_policies["helios"] = ServiceResourcePolicy(
            service_name="helios",
            max_concurrent_requests=3,
            allowed_model_categories=list(ModelCategory),
            preferred_models=["qwen2.5:32b", "llama3.1:70b", "qwen2.5:14b"],
            fallback_models=["qwen2.5:14b", "llama3.1:8b"],
            timeout_seconds=1200,
            priority=PolicyPriority.CRITICAL,
            queue_priority_boost=2.0
        )
        
        # Socratic Policy - Educational and reflective interactions
        self.service_policies["socratic"] = ServiceResourcePolicy(
            service_name="socratic",
            max_concurrent_requests=10,
            allowed_model_categories=[ModelCategory.MEDIUM_4B, ModelCategory.LARGE_8B],
            preferred_models=["llama3.2:3b", "llama3.1:8b"],
            fallback_models=["llama3.2:3b"],
            timeout_seconds=300,
            priority=PolicyPriority.NORMAL,
            queue_priority_boost=1.0
        )
    
    async def load_policies(self):
        """Load policies from configuration file."""
        try:
            if self.policy_file_path.exists():
                with open(self.policy_file_path, 'r') as f:
                    data = json.load(f)
                
                # Load system policy
                if "system_policy" in data:
                    self.system_policy = SystemResourcePolicy(**data["system_policy"])
                
                # Load performance policy
                if "performance_policy" in data:
                    self.performance_policy = PerformanceOptimizationPolicy(**data["performance_policy"])
                
                # Load service policies
                if "service_policies" in data:
                    for service_name, policy_data in data["service_policies"].items():
                        # Convert string enums back to enum objects
                        if "allowed_model_categories" in policy_data:
                            policy_data["allowed_model_categories"] = [
                                ModelCategory(cat) for cat in policy_data["allowed_model_categories"]
                            ]
                        if "priority" in policy_data:
                            policy_data["priority"] = PolicyPriority(policy_data["priority"])
                        
                        self.service_policies[service_name] = ServiceResourcePolicy(**policy_data)
                
                # Load user policies
                if "user_policies" in data:
                    for user_key, policy_data in data["user_policies"].items():
                        # Convert string enums back to enum objects
                        if "allowed_model_categories" in policy_data:
                            policy_data["allowed_model_categories"] = [
                                ModelCategory(cat) for cat in policy_data["allowed_model_categories"]
                            ]
                        if "priority" in policy_data:
                            policy_data["priority"] = PolicyPriority(policy_data["priority"])
                        
                        self.user_policies[user_key] = UserResourcePolicy(**policy_data)
                
                logger.info("Successfully loaded resource policies from configuration file")
            else:
                logger.info("No policy configuration file found, using defaults")
                
        except Exception as e:
            logger.error(f"Error loading policies from file: {e}")
    
    async def save_policies(self):
        """Save current policies to configuration file."""
        try:
            # Create config directory if it doesn't exist
            self.policy_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert policies to serializable format
            data = {
                "system_policy": asdict(self.system_policy),
                "performance_policy": asdict(self.performance_policy),
                "service_policies": {
                    name: self._serialize_service_policy(policy)
                    for name, policy in self.service_policies.items()
                },
                "user_policies": {
                    key: self._serialize_user_policy(policy)
                    for key, policy in self.user_policies.items()
                },
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.policy_file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info("Successfully saved resource policies to configuration file")
            
        except Exception as e:
            logger.error(f"Error saving policies to file: {e}")
    
    def _serialize_service_policy(self, policy: ServiceResourcePolicy) -> Dict[str, Any]:
        """Convert ServiceResourcePolicy to serializable dictionary."""
        data = asdict(policy)
        data["allowed_model_categories"] = [cat.value for cat in policy.allowed_model_categories]
        data["priority"] = policy.priority.value
        return data
    
    def _serialize_user_policy(self, policy: UserResourcePolicy) -> Dict[str, Any]:
        """Convert UserResourcePolicy to serializable dictionary."""
        data = asdict(policy)
        data["allowed_model_categories"] = [cat.value for cat in policy.allowed_model_categories]
        data["priority"] = policy.priority.value
        return data
    
    def get_service_policy(self, service_name: str) -> ServiceResourcePolicy:
        """Get resource policy for a specific service."""
        return self.service_policies.get(service_name, ServiceResourcePolicy(service_name=service_name))
    
    def get_user_policy(self, user_id: str, user_group: Optional[str] = None) -> UserResourcePolicy:
        """Get resource policy for a specific user."""
        # Check for user-specific policy first
        if user_id in self.user_policies:
            return self.user_policies[user_id]
        
        # Check for group policy
        if user_group and f"group:{user_group}" in self.user_policies:
            return self.user_policies[f"group:{user_group}"]
        
        # Return default policy
        return UserResourcePolicy(user_id=user_id, user_group=user_group)
    
    async def update_service_policy(self, service_name: str, policy_updates: Dict[str, Any]):
        """Update resource policy for a service."""
        if service_name not in self.service_policies:
            self.service_policies[service_name] = ServiceResourcePolicy(service_name=service_name)
        
        policy = self.service_policies[service_name]
        
        # Update fields
        for field_name, value in policy_updates.items():
            if hasattr(policy, field_name):
                # Handle enum conversions
                if field_name == "allowed_model_categories" and isinstance(value, list):
                    value = [ModelCategory(cat) if isinstance(cat, str) else cat for cat in value]
                elif field_name == "priority" and isinstance(value, str):
                    value = PolicyPriority(value)
                
                setattr(policy, field_name, value)
        
        await self.save_policies()
        logger.info(f"Updated policy for service {service_name}: {policy_updates}")
    
    async def update_user_policy(self, user_id: str, policy_updates: Dict[str, Any], user_group: Optional[str] = None):
        """Update resource policy for a user."""
        policy_key = f"group:{user_group}" if user_group else user_id
        
        if policy_key not in self.user_policies:
            self.user_policies[policy_key] = UserResourcePolicy(user_id=user_id, user_group=user_group)
        
        policy = self.user_policies[policy_key]
        
        # Update fields
        for field_name, value in policy_updates.items():
            if hasattr(policy, field_name):
                # Handle enum conversions
                if field_name == "allowed_model_categories" and isinstance(value, list):
                    value = [ModelCategory(cat) if isinstance(cat, str) else cat for cat in value]
                elif field_name == "priority" and isinstance(value, str):
                    value = PolicyPriority(value)
                
                setattr(policy, field_name, value)
        
        await self.save_policies()
        logger.info(f"Updated policy for user {user_id}: {policy_updates}")
    
    async def validate_request(
        self, 
        user_id: str, 
        service_name: str, 
        model_category: ModelCategory,
        user_group: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate if a request meets policy requirements.
        
        Returns:
            Dictionary with validation results and recommendations
        """
        validation_result = {
            "allowed": True,
            "reasons": [],
            "recommendations": [],
            "policy_violations": []
        }
        
        # Get applicable policies
        service_policy = self.get_service_policy(service_name)
        user_policy = self.get_user_policy(user_id, user_group)
        
        # Check if service is enabled
        if not service_policy.enabled:
            validation_result["allowed"] = False
            validation_result["policy_violations"].append(f"Service {service_name} is disabled")
        
        # Check if user policy is enabled
        if not user_policy.enabled:
            validation_result["allowed"] = False
            validation_result["policy_violations"].append(f"User {user_id} access is disabled")
        
        # Check service access for user
        if user_policy.allowed_services and service_name not in user_policy.allowed_services:
            validation_result["allowed"] = False
            validation_result["policy_violations"].append(f"User {user_id} not allowed to use service {service_name}")
        
        # Check model category restrictions
        if model_category not in service_policy.allowed_model_categories:
            validation_result["allowed"] = False
            validation_result["policy_violations"].append(f"Model category {model_category.value} not allowed for service {service_name}")
        
        if model_category not in user_policy.allowed_model_categories:
            validation_result["allowed"] = False
            validation_result["policy_violations"].append(f"User {user_id} not allowed to use model category {model_category.value}")
        
        # Check usage quotas
        quota_status = await self.check_usage_quota(user_id, service_name)
        if not quota_status["within_limits"]:
            validation_result["allowed"] = False
            validation_result["policy_violations"].extend(quota_status["violations"])
        
        # Add recommendations if request is allowed
        if validation_result["allowed"]:
            # Recommend preferred models
            if service_policy.preferred_models:
                validation_result["recommendations"].append({
                    "type": "preferred_models",
                    "models": service_policy.preferred_models
                })
            
            # Recommend fallback models
            if service_policy.fallback_models:
                validation_result["recommendations"].append({
                    "type": "fallback_models",
                    "models": service_policy.fallback_models
                })
        
        return validation_result
    
    async def check_usage_quota(self, user_id: str, service_name: str) -> Dict[str, Any]:
        """Check if user is within usage quotas."""
        quota_status = {
            "within_limits": True,
            "violations": [],
            "current_usage": {},
            "limits": {}
        }
        
        user_policy = self.get_user_policy(user_id)
        current_time = datetime.now(timezone.utc)
        
        # Initialize usage tracking for user if not exists
        if user_id not in self.usage_tracking:
            self.usage_tracking[user_id] = {
                "daily_requests": 0,
                "hourly_requests": 0,
                "last_reset_date": current_time.date(),
                "last_reset_hour": current_time.hour,
                "service_usage": {}
            }
        
        user_usage = self.usage_tracking[user_id]
        
        # Reset daily quota if needed
        if user_usage["last_reset_date"] < current_time.date():
            user_usage["daily_requests"] = 0
            user_usage["last_reset_date"] = current_time.date()
        
        # Reset hourly quota if needed
        if user_usage["last_reset_hour"] != current_time.hour:
            user_usage["hourly_requests"] = 0
            user_usage["last_reset_hour"] = current_time.hour
        
        # Check daily limit
        if user_policy.daily_request_limit is not None:
            quota_status["limits"]["daily"] = user_policy.daily_request_limit
            quota_status["current_usage"]["daily"] = user_usage["daily_requests"]
            
            if user_usage["daily_requests"] >= user_policy.daily_request_limit:
                quota_status["within_limits"] = False
                quota_status["violations"].append(f"Daily request limit exceeded ({user_usage['daily_requests']}/{user_policy.daily_request_limit})")
        
        # Check hourly limit
        if user_policy.hourly_request_limit is not None:
            quota_status["limits"]["hourly"] = user_policy.hourly_request_limit
            quota_status["current_usage"]["hourly"] = user_usage["hourly_requests"]
            
            if user_usage["hourly_requests"] >= user_policy.hourly_request_limit:
                quota_status["within_limits"] = False
                quota_status["violations"].append(f"Hourly request limit exceeded ({user_usage['hourly_requests']}/{user_policy.hourly_request_limit})")
        
        return quota_status
    
    async def record_usage(self, user_id: str, service_name: str, model_name: str, processing_time: float):
        """Record usage for quota tracking and analytics."""
        current_time = datetime.now(timezone.utc)
        
        # Initialize usage tracking for user if not exists
        if user_id not in self.usage_tracking:
            self.usage_tracking[user_id] = {
                "daily_requests": 0,
                "hourly_requests": 0,
                "last_reset_date": current_time.date(),
                "last_reset_hour": current_time.hour,
                "service_usage": {}
            }
        
        user_usage = self.usage_tracking[user_id]
        
        # Update request counts
        user_usage["daily_requests"] += 1
        user_usage["hourly_requests"] += 1
        
        # Update service-specific usage
        if service_name not in user_usage["service_usage"]:
            user_usage["service_usage"][service_name] = {
                "requests": 0,
                "total_processing_time": 0.0,
                "models_used": {}
            }
        
        service_usage = user_usage["service_usage"][service_name]
        service_usage["requests"] += 1
        service_usage["total_processing_time"] += processing_time
        
        # Update model usage
        if model_name not in service_usage["models_used"]:
            service_usage["models_used"][model_name] = 0
        service_usage["models_used"][model_name] += 1
        
        logger.debug(f"Recorded usage for user {user_id}: {service_name} with {model_name}")
    
    async def get_usage_analytics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage analytics for monitoring and optimization."""
        if user_id:
            # Return analytics for specific user
            if user_id not in self.usage_tracking:
                return {"error": f"No usage data found for user {user_id}"}
            
            return {
                "user_id": user_id,
                "usage_data": self.usage_tracking[user_id],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Return aggregated analytics
            total_users = len(self.usage_tracking)
            total_daily_requests = sum(data.get("daily_requests", 0) for data in self.usage_tracking.values())
            total_hourly_requests = sum(data.get("hourly_requests", 0) for data in self.usage_tracking.values())
            
            # Aggregate service usage
            service_analytics = {}
            model_analytics = {}
            
            for user_data in self.usage_tracking.values():
                for service_name, service_data in user_data.get("service_usage", {}).items():
                    if service_name not in service_analytics:
                        service_analytics[service_name] = {"requests": 0, "total_processing_time": 0.0}
                    
                    service_analytics[service_name]["requests"] += service_data.get("requests", 0)
                    service_analytics[service_name]["total_processing_time"] += service_data.get("total_processing_time", 0.0)
                    
                    # Aggregate model usage
                    for model_name, count in service_data.get("models_used", {}).items():
                        if model_name not in model_analytics:
                            model_analytics[model_name] = 0
                        model_analytics[model_name] += count
            
            return {
                "total_users": total_users,
                "total_daily_requests": total_daily_requests,
                "total_hourly_requests": total_hourly_requests,
                "service_analytics": service_analytics,
                "model_analytics": model_analytics,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_policy_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all policies."""
        return {
            "system_policy": asdict(self.system_policy),
            "performance_policy": asdict(self.performance_policy),
            "service_policies": {
                name: self._serialize_service_policy(policy)
                for name, policy in self.service_policies.items()
            },
            "user_policies_count": len(self.user_policies),
            "active_users_tracked": len(self.usage_tracking),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }


# Global instance
resource_policy_service = ResourcePolicyService()