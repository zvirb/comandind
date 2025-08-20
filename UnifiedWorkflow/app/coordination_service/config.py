"""Configuration for the Coordination Service."""

import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import field_validator, validator


class CoordinationConfig(BaseSettings):
    """Configuration settings for the coordination service."""
    
    # Service Configuration
    port: int = int(os.getenv("COORDINATION_PORT", "8001"))
    host: str = os.getenv("COORDINATION_HOST", "0.0.0.0")
    debug: bool = False
    log_level: str = "INFO"
    
    # Database Configuration with Connection Pooling Optimization - Uses shared AI Workflow DB
    database_url: str = os.getenv("DATABASE_URL", "postgresql://app_user:${POSTGRES_PASSWORD}@postgres:5432/ai_workflow_db")
    database_pool_size: int = int(os.getenv("COORDINATION_DB_POOL_SIZE", "20"))
    database_max_overflow: int = int(os.getenv("COORDINATION_DB_MAX_OVERFLOW", "30"))
    database_pool_timeout: int = int(os.getenv("COORDINATION_DB_POOL_TIMEOUT", "30"))
    database_pool_recycle: int = int(os.getenv("COORDINATION_DB_POOL_RECYCLE", "3600"))
    database_echo: bool = os.getenv("COORDINATION_DB_ECHO", "false").lower() == "true"
    
    # Redis Configuration - Uses shared Redis with authentication
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "1"))
    redis_user: str = os.getenv("REDIS_USER", "lwe-app")
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        if self.redis_password:
            # URL encode the password to handle special characters
            from urllib.parse import quote_plus
            password = quote_plus(self.redis_password)
            return f"redis://{self.redis_user}:{password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Service URLs for Integration
    reasoning_service_url: str = os.getenv(
        "COORDINATION_REASONING_SERVICE_URL",
        "http://reasoning-service:8005"
    )
    learning_service_url: str = os.getenv(
        "COORDINATION_LEARNING_SERVICE_URL", 
        "http://learning-service:8005"
    )
    hybrid_memory_service_url: str = os.getenv(
        "COORDINATION_HYBRID_MEMORY_URL",
        "http://hybrid-memory-service:8002"
    )
    
    # Orchestration Configuration
    max_concurrent_workflows: int = int(os.getenv("COORDINATION_MAX_CONCURRENT_WORKFLOWS", "50"))
    max_context_tokens: int = int(os.getenv("COORDINATION_MAX_CONTEXT_TOKENS", "4000"))
    recovery_timeout: int = int(os.getenv("COORDINATION_RECOVERY_TIMEOUT", "30"))
    
    # Agent Configuration
    max_agents_per_workflow: int = int(os.getenv("COORDINATION_MAX_AGENTS_PER_WORKFLOW", "10"))
    agent_timeout: int = int(os.getenv("COORDINATION_AGENT_TIMEOUT", "300"))
    agent_retry_attempts: int = int(os.getenv("COORDINATION_AGENT_RETRY_ATTEMPTS", "3"))
    
    # Enhanced Performance Configuration
    target_completion_rate: float = float(os.getenv("COORDINATION_TARGET_COMPLETION_RATE", "0.95"))
    workflow_timeout: int = int(os.getenv("COORDINATION_WORKFLOW_TIMEOUT", "3600"))
    context_cache_ttl: int = int(os.getenv("COORDINATION_CONTEXT_CACHE_TTL", "1800"))
    
    # Async Performance Optimization
    async_task_limit: int = int(os.getenv("COORDINATION_ASYNC_TASK_LIMIT", "100"))
    connection_pool_optimization: bool = os.getenv("COORDINATION_POOL_OPTIMIZATION", "true").lower() == "true"
    batch_processing_enabled: bool = os.getenv("COORDINATION_BATCH_PROCESSING", "true").lower() == "true"
    batch_size: int = int(os.getenv("COORDINATION_BATCH_SIZE", "25"))
    
    # Event Configuration
    cognitive_event_processing_enabled: bool = os.getenv("COORDINATION_COGNITIVE_EVENT_PROCESSING", "true").lower() == "true"
    event_batch_size: int = int(os.getenv("COORDINATION_EVENT_BATCH_SIZE", "10"))
    event_processing_interval: int = int(os.getenv("COORDINATION_EVENT_PROCESSING_INTERVAL", "5"))
    
    # Monitoring Configuration
    enable_performance_monitoring: bool = os.getenv("COORDINATION_ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    monitoring_interval: int = int(os.getenv("COORDINATION_MONITORING_INTERVAL", "60"))
    metrics_retention_hours: int = int(os.getenv("COORDINATION_METRICS_RETENTION_HOURS", "24"))
    
    # Security Configuration
    enable_auth: bool = os.getenv("COORDINATION_ENABLE_AUTH", "false").lower() == "true"
    auth_secret: Optional[str] = os.getenv("COORDINATION_AUTH_SECRET")
    
    # Feature Flags
    enable_agent_caching: bool = os.getenv("COORDINATION_ENABLE_AGENT_CACHING", "true").lower() == "true"
    enable_workflow_optimization: bool = os.getenv("COORDINATION_ENABLE_WORKFLOW_OPTIMIZATION", "true").lower() == "true"
    enable_auto_scaling: bool = os.getenv("COORDINATION_ENABLE_AUTO_SCALING", "false").lower() == "true"
    enable_context_compression: bool = os.getenv("COORDINATION_ENABLE_CONTEXT_COMPRESSION", "true").lower() == "true"
    
    # Advanced Configuration
    workflow_dependency_timeout: int = int(os.getenv("COORDINATION_WORKFLOW_DEPENDENCY_TIMEOUT", "120"))
    context_package_compression_ratio: float = float(os.getenv("COORDINATION_CONTEXT_COMPRESSION_RATIO", "0.8"))
    parallel_execution_threshold: int = int(os.getenv("COORDINATION_PARALLEL_EXECUTION_THRESHOLD", "3"))
    
    @field_validator('target_completion_rate')
    @classmethod
    def validate_completion_rate(cls, v):
        if not 0.5 <= v <= 1.0:
            raise ValueError('Target completion rate must be between 0.5 and 1.0')
        return v
    
    @field_validator('max_context_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v < 1000 or v > 8000:
            raise ValueError('Max context tokens must be between 1000 and 8000')
        return v
    
    @field_validator('max_concurrent_workflows')
    @classmethod
    def validate_max_workflows(cls, v):
        if v < 1 or v > 200:
            raise ValueError('Max concurrent workflows must be between 1 and 200')
        return v
    
    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "allow"}


# Agent Capability Definitions
AGENT_CAPABILITIES = {
    # Meta-Orchestration Agents
    "agent-integration-orchestrator": {
        "category": "meta-orchestration",
        "capabilities": ["agent_discovery", "registry_management", "protocol_establishment"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "high"},
        "max_concurrent": 1,
        "typical_duration": 60
    },
    "project-orchestrator": {
        "category": "meta-orchestration", 
        "capabilities": ["project_coordination", "multi_domain_analysis", "strategic_planning"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "high"},
        "max_concurrent": 3,
        "typical_duration": 300
    },
    "meta-orchestrator": {
        "category": "meta-orchestration",
        "capabilities": ["large_scale_coordination", "strategic_oversight", "system_integration"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "high"},
        "max_concurrent": 2,
        "typical_duration": 600
    },
    
    # Context Optimization Agents
    "context-compression-agent": {
        "category": "context-optimization",
        "capabilities": ["token_reduction", "content_summarization", "intelligent_truncation"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "medium"},
        "max_concurrent": 10,
        "typical_duration": 30
    },
    "content-compressor": {
        "category": "context-optimization",
        "capabilities": ["content_reduction", "semantic_preservation", "lossy_compression"],
        "resource_requirements": {"cpu": 1, "memory": 256, "priority": "medium"},
        "max_concurrent": 15,
        "typical_duration": 20
    },
    "parallel-file-manager": {
        "category": "context-optimization",
        "capabilities": ["batch_operations", "file_coordination", "concurrent_processing"],
        "resource_requirements": {"cpu": 2, "memory": 512, "priority": "medium"},
        "max_concurrent": 5,
        "typical_duration": 120
    },
    
    # Research & Analysis Agents
    "codebase-research-analyst": {
        "category": "research-analysis",
        "capabilities": ["code_investigation", "pattern_analysis", "deep_inspection"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "medium"},
        "max_concurrent": 8,
        "typical_duration": 180
    },
    "enhanced-research-coordinator": {
        "category": "research-analysis",
        "capabilities": ["historical_analysis", "pattern_discovery", "research_synthesis"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "medium"},
        "max_concurrent": 6,
        "typical_duration": 240
    },
    "smart-search-agent": {
        "category": "research-analysis",
        "capabilities": ["information_discovery", "efficient_search", "result_filtering"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "low"},
        "max_concurrent": 20,
        "typical_duration": 60
    },
    
    # Development Specialists
    "fullstack-communication-auditor": {
        "category": "development",
        "capabilities": ["system_integration", "communication_analysis", "interface_validation"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "medium"},
        "max_concurrent": 4,
        "typical_duration": 300
    },
    "python-refactoring-architect": {
        "category": "development",
        "capabilities": ["code_restructuring", "architecture_improvement", "python_optimization"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "medium"},
        "max_concurrent": 6,
        "typical_duration": 420
    },
    "webui-architect": {
        "category": "development",
        "capabilities": ["frontend_analysis", "ui_design", "user_experience"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "medium"},
        "max_concurrent": 4,
        "typical_duration": 300
    },
    
    # Security & Quality Agents
    "security-validator": {
        "category": "security-quality",
        "capabilities": ["security_testing", "vulnerability_assessment", "real_time_validation"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "high"},
        "max_concurrent": 3,
        "typical_duration": 240
    },
    "code-quality-guardian": {
        "category": "security-quality",
        "capabilities": ["standards_enforcement", "quality_analysis", "best_practices"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "medium"},
        "max_concurrent": 10,
        "typical_duration": 120
    },
    "security-vulnerability-scanner": {
        "category": "security-quality",
        "capabilities": ["comprehensive_security_audit", "vulnerability_detection", "threat_analysis"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "high"},
        "max_concurrent": 2,
        "typical_duration": 600
    },
    
    # Project Management Agents
    "documentation-specialist": {
        "category": "project-management",
        "capabilities": ["live_documentation", "doc_generation", "knowledge_management"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "low"},
        "max_concurrent": 8,
        "typical_duration": 180
    },
    "project-structure-mapper": {
        "category": "project-management",
        "capabilities": ["organization_analysis", "structure_mapping", "project_visualization"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "low"},
        "max_concurrent": 5,
        "typical_duration": 120
    },
    "project-janitor": {
        "category": "project-management",
        "capabilities": ["cleanup", "maintenance", "housekeeping"],
        "resource_requirements": {"cpu": 1, "memory": 256, "priority": "low"},
        "max_concurrent": 3,
        "typical_duration": 90
    },
    "dependency-analyzer": {
        "category": "project-management",
        "capabilities": ["package_management", "dependency_security", "version_analysis"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "medium"},
        "max_concurrent": 6,
        "typical_duration": 150
    },
    
    # Specialized Agents (Additional 27 agents to reach 47+)
    "nexus-synthesis-agent": {
        "category": "synthesis",
        "capabilities": ["cross_domain_integration", "unified_design", "interface_synthesis"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "high"},
        "max_concurrent": 4,
        "typical_duration": 360
    },
    "test-automation-engineer": {
        "category": "testing",
        "capabilities": ["test_suite_execution", "automated_testing", "regression_testing"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "high"},
        "max_concurrent": 5,
        "typical_duration": 300
    },
    "performance-profiler": {
        "category": "performance",
        "capabilities": ["performance_analysis", "bottleneck_detection", "optimization"],
        "resource_requirements": {"cpu": 2, "memory": 1024, "priority": "medium"},
        "max_concurrent": 3,
        "typical_duration": 480
    },
    "orchestration-auditor": {
        "category": "audit",
        "capabilities": ["execution_analysis", "evidence_collection", "validation"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "high"},
        "max_concurrent": 6,
        "typical_duration": 180
    },
    "orchestration-todo-manager": {
        "category": "management",
        "capabilities": ["task_tracking", "progress_management", "completion_validation"],
        "resource_requirements": {"cpu": 1, "memory": 256, "priority": "medium"},
        "max_concurrent": 10,
        "typical_duration": 60
    },
    "user-experience-auditor": {
        "category": "audit",
        "capabilities": ["end_to_end_validation", "workflow_testing", "user_journey"],
        "resource_requirements": {"cpu": 1, "memory": 512, "priority": "medium"},
        "max_concurrent": 4,
        "typical_duration": 360
    }
    # Note: This represents 26 agents. Additional specialized agents would be added
    # to reach 47+ total agents as the system grows
}


# Workflow Templates
WORKFLOW_TEMPLATES = {
    "new_feature": {
        "description": "Implementation of new features in single project phase",
        "required_agents": ["project-orchestrator", "codebase-research-analyst", "nexus-synthesis-agent"],
        "optional_agents": ["security-validator", "test-automation-engineer", "documentation-specialist"],
        "estimated_duration": 1800,  # 30 minutes
        "parallel_stages": ["research", "design"],
        "sequential_stages": ["implementation", "validation", "documentation"]
    },
    "bug_fix": {
        "description": "Bug fixes within single project phase scope",
        "required_agents": ["codebase-research-analyst", "python-refactoring-architect"],
        "optional_agents": ["test-automation-engineer", "security-validator"],
        "estimated_duration": 900,  # 15 minutes
        "parallel_stages": ["research", "analysis"],
        "sequential_stages": ["fix", "validation"]
    },
    "system_integration": {
        "description": "System integration within single project phase",
        "required_agents": ["fullstack-communication-auditor", "nexus-synthesis-agent"],
        "optional_agents": ["user-experience-auditor", "performance-profiler"],
        "estimated_duration": 2400,  # 40 minutes
        "parallel_stages": ["integration_analysis", "design"],
        "sequential_stages": ["implementation", "validation", "optimization"]
    },
    "security_audit": {
        "description": "Comprehensive security audit and validation",
        "required_agents": ["security-validator", "security-vulnerability-scanner"],
        "optional_agents": ["code-quality-guardian", "dependency-analyzer"],
        "estimated_duration": 1800,  # 30 minutes
        "parallel_stages": ["vulnerability_scan", "code_analysis"],
        "sequential_stages": ["threat_assessment", "remediation", "validation"]
    },
    "performance_optimization": {
        "description": "Performance analysis and optimization",
        "required_agents": ["performance-profiler", "python-refactoring-architect"],
        "optional_agents": ["codebase-research-analyst", "test-automation-engineer"],
        "estimated_duration": 2100,  # 35 minutes
        "parallel_stages": ["profiling", "analysis"],
        "sequential_stages": ["optimization", "validation", "monitoring"]
    }
}