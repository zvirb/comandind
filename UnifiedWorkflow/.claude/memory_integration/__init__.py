"""
Memory Service Integration for AI Workflow Engine

Provides comprehensive memory MCP service integration to replace markdown file
creation with structured knowledge storage and retrieval.

Key Components:
- MemoryServiceIntegration: Core memory service wrapper
- MemoryUtilities: Convenient agent functions
- OrchestrationWrapper: Automatic markdown prevention
- Entity Types: Standardized knowledge schemas

Usage:
    from .memory_integration import initialize_orchestration_wrapper
    from .memory_utilities import store_analysis, search_knowledge
    from .orchestration_wrapper import agent_memory
    
    # Initialize with MCP functions
    await initialize_orchestration_wrapper(mcp_functions)
    
    # Store knowledge instead of creating markdown
    await store_analysis("redis_connectivity", analysis_data, "security-validator")
    
    # Search knowledge instead of reading files
    results = await search_knowledge("authentication patterns")
"""

from .memory_service_integration import (
    MemoryServiceIntegration,
    MemoryEntityType,
    MemoryAntiPattern,
    create_memory_integration_instance
)

from .memory_utilities import (
    initialize_memory_utilities,
    store_analysis,
    store_validation_evidence,
    store_configuration_analysis,
    store_performance_metrics,
    store_security_analysis,
    store_infrastructure_findings,
    store_error_pattern,
    store_orchestration_context,
    search_knowledge,
    get_specific_knowledge,
    search_patterns,
    search_error_solutions,
    search_validation_history,
    prevent_markdown_creation,
    quick_store,
    get_recent_knowledge
)

from .orchestration_wrapper import (
    initialize_orchestration_wrapper,
    set_agent_context,
    get_current_agent,
    enable_markdown_prevention,
    MemoryServiceWrite,
    AgentMemoryInterface,
    agent_memory,
    create_memory_aware_agent_wrapper,
    wrap_orchestration_tools,
    get_memory_usage_statistics
)

# Version information
__version__ = "1.0.0"
__author__ = "AI Workflow Engine"
__description__ = "Memory MCP service integration for orchestration knowledge management"

# Public API
__all__ = [
    # Core integration classes
    "MemoryServiceIntegration",
    "MemoryEntityType", 
    "MemoryAntiPattern",
    "AgentMemoryInterface",
    "MemoryServiceWrite",
    
    # Initialization functions
    "initialize_orchestration_wrapper",
    "initialize_memory_utilities",
    "create_memory_integration_instance",
    
    # Storage functions
    "store_analysis",
    "store_validation_evidence",
    "store_configuration_analysis", 
    "store_performance_metrics",
    "store_security_analysis",
    "store_infrastructure_findings",
    "store_error_pattern",
    "store_orchestration_context",
    "quick_store",
    
    # Search functions
    "search_knowledge",
    "get_specific_knowledge",
    "search_patterns",
    "search_error_solutions",
    "search_validation_history",
    "get_recent_knowledge",
    
    # Orchestration integration
    "set_agent_context",
    "get_current_agent",
    "enable_markdown_prevention",
    "prevent_markdown_creation",
    "create_memory_aware_agent_wrapper",
    "wrap_orchestration_tools",
    "get_memory_usage_statistics",
    
    # Global interfaces
    "agent_memory"
]