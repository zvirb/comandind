#!/usr/bin/env python3
"""
Memory Utilities for Orchestration Agents

Provides simplified wrapper functions for agents to use memory MCP services
instead of creating markdown files. Implements the anti-pattern prevention
and automatic knowledge storage.

Usage Examples:
    # Instead of Write("/path/analysis.md", content)
    await store_analysis("redis_connectivity_analysis", content, "security-validator")
    
    # Instead of creating validation reports as markdown
    await store_validation_evidence("endpoint_validation", evidence_data, True)
    
    # Instead of reading multiple markdown files
    results = await search_knowledge("authentication patterns")
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from .memory_service_integration import (
    MemoryServiceIntegration,
    MemoryEntityType,
    MemoryAntiPattern,
    create_memory_integration_instance
)

logger = logging.getLogger(__name__)

# Global memory integration instance
_memory_integration: Optional[MemoryServiceIntegration] = None
_anti_pattern: Optional[MemoryAntiPattern] = None


async def initialize_memory_utilities(mcp_functions: Dict[str, Any]) -> None:
    """
    Initialize memory utilities with MCP function references.
    
    Args:
        mcp_functions: Dictionary containing MCP function references
    """
    global _memory_integration, _anti_pattern
    
    try:
        _memory_integration = await create_memory_integration_instance(mcp_functions)
        _anti_pattern = MemoryAntiPattern(_memory_integration)
        logger.info("Memory utilities initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize memory utilities: {e}")
        raise


def _ensure_initialized() -> MemoryServiceIntegration:
    """Ensure memory integration is initialized."""
    if _memory_integration is None:
        raise RuntimeError("Memory utilities not initialized. Call initialize_memory_utilities() first.")
    return _memory_integration


# Convenience functions for common agent operations

async def store_analysis(
    analysis_name: str,
    content: Union[str, Dict[str, Any]],
    agent_name: Optional[str] = None,
    analysis_type: Optional[str] = None
) -> str:
    """
    Store analysis results instead of creating markdown files.
    
    Args:
        analysis_name: Unique name for the analysis
        content: Analysis content or structured data
        agent_name: Name of the agent performing analysis
        analysis_type: Type of analysis (security, performance, etc.)
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare metadata
    metadata = {
        "type": "analysis",
        "created_by": agent_name or "unknown_agent",
        "analysis_type": analysis_type or "general"
    }
    
    # Prepare tags
    tags = ["analysis"]
    if agent_name:
        tags.append(agent_name)
    if analysis_type:
        tags.append(analysis_type)
    
    return await memory.store_orchestration_knowledge(
        entity_name=f"analysis_{analysis_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        entity_type=MemoryEntityType.AGENT_FINDINGS,
        content=content,
        metadata=metadata,
        tags=tags
    )


async def store_validation_evidence(
    validation_name: str,
    evidence: Dict[str, Any],
    success: bool,
    agent_name: Optional[str] = None
) -> str:
    """
    Store validation evidence instead of creating markdown reports.
    
    Args:
        validation_name: Name of validation performed
        evidence: Evidence data and results
        success: Whether validation succeeded
        agent_name: Name of validating agent
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare structured evidence
    evidence_data = {
        "validation_type": validation_name,
        "success": success,
        "evidence": evidence,
        "validated_by": agent_name or "unknown_agent",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    return await memory.store_validation_evidence(
        validation_name=validation_name,
        evidence_data=evidence_data,
        success=success
    )


async def store_configuration_analysis(
    config_name: str,
    config_data: Dict[str, Any],
    agent_name: Optional[str] = None
) -> str:
    """
    Store configuration analysis instead of markdown files.
    
    Args:
        config_name: Name of configuration analyzed
        config_data: Configuration data and analysis
        agent_name: Name of analyzing agent
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare metadata
    metadata = {
        "type": "configuration_analysis",
        "analyzed_by": agent_name or "unknown_agent",
        "config_type": config_name
    }
    
    return await memory.store_orchestration_knowledge(
        entity_name=f"config_{config_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        entity_type=MemoryEntityType.SYSTEM_CONFIGURATION,
        content=config_data,
        metadata=metadata,
        tags=["configuration", config_name, agent_name or "unknown"]
    )


async def store_performance_metrics(
    metric_name: str,
    metrics: Dict[str, Any],
    agent_name: Optional[str] = None
) -> str:
    """
    Store performance metrics instead of markdown reports.
    
    Args:
        metric_name: Name of performance metric set
        metrics: Performance data and analysis
        agent_name: Name of analyzing agent
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare metadata
    metadata = {
        "type": "performance_metrics",
        "measured_by": agent_name or "unknown_agent",
        "metric_category": metric_name
    }
    
    return await memory.store_orchestration_knowledge(
        entity_name=f"metrics_{metric_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        entity_type=MemoryEntityType.PERFORMANCE_METRICS,
        content=metrics,
        metadata=metadata,
        tags=["performance", "metrics", metric_name, agent_name or "unknown"]
    )


async def store_security_analysis(
    security_area: str,
    analysis: Dict[str, Any],
    severity: str = "medium",
    agent_name: Optional[str] = None
) -> str:
    """
    Store security analysis instead of markdown reports.
    
    Args:
        security_area: Area of security analyzed
        analysis: Security analysis data
        severity: Severity level (low, medium, high, critical)
        agent_name: Name of analyzing agent
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare metadata
    metadata = {
        "type": "security_analysis",
        "analyzed_by": agent_name or "unknown_agent",
        "security_area": security_area,
        "severity": severity
    }
    
    return await memory.store_orchestration_knowledge(
        entity_name=f"security_{security_area}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        entity_type=MemoryEntityType.SECURITY_VALIDATION,
        content=analysis,
        metadata=metadata,
        tags=["security", security_area, severity, agent_name or "unknown"]
    )


async def store_infrastructure_findings(
    component_name: str,
    findings: Dict[str, Any],
    status: str = "unknown",
    agent_name: Optional[str] = None
) -> str:
    """
    Store infrastructure findings instead of markdown reports.
    
    Args:
        component_name: Infrastructure component analyzed
        findings: Analysis findings and recommendations
        status: Component status (healthy, degraded, failed, unknown)
        agent_name: Name of analyzing agent
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare metadata
    metadata = {
        "type": "infrastructure_analysis",
        "analyzed_by": agent_name or "unknown_agent",
        "component": component_name,
        "status": status
    }
    
    return await memory.store_orchestration_knowledge(
        entity_name=f"infra_{component_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        entity_type=MemoryEntityType.INFRASTRUCTURE_ANALYSIS,
        content=findings,
        metadata=metadata,
        tags=["infrastructure", component_name, status, agent_name or "unknown"]
    )


async def store_error_pattern(
    error_name: str,
    error_data: Dict[str, Any],
    solution: Optional[str] = None,
    agent_name: Optional[str] = None
) -> str:
    """
    Store error pattern analysis instead of markdown files.
    
    Args:
        error_name: Name/type of error
        error_data: Error details and analysis
        solution: Solution or workaround if known
        agent_name: Name of analyzing agent
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Prepare structured error data
    pattern_data = {
        "error_type": error_name,
        "details": error_data,
        "solution": solution,
        "identified_by": agent_name or "unknown_agent",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Prepare metadata
    metadata = {
        "type": "error_pattern",
        "identified_by": agent_name or "unknown_agent",
        "error_category": error_name,
        "has_solution": solution is not None
    }
    
    return await memory.store_orchestration_knowledge(
        entity_name=f"error_{error_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        entity_type=MemoryEntityType.ERROR_PATTERNS,
        content=pattern_data,
        metadata=metadata,
        tags=["error", "pattern", error_name, agent_name or "unknown"]
    )


async def store_orchestration_context(
    context_name: str,
    context_data: Dict[str, Any],
    specialist_type: Optional[str] = None,
    token_estimate: Optional[int] = None
) -> str:
    """
    Store orchestration context package instead of markdown files.
    
    Args:
        context_name: Name of context package
        context_data: Context information and instructions
        specialist_type: Type of specialist this context is for
        token_estimate: Estimated token count
        
    Returns:
        Entity name for future reference
    """
    memory = _ensure_initialized()
    
    # Estimate tokens if not provided (rough estimate: 4 chars = 1 token)
    if token_estimate is None:
        content_str = json.dumps(context_data, indent=2)
        token_estimate = len(content_str) // 4
    
    return await memory.store_context_package(
        package_name=context_name,
        specialist_type=specialist_type or "general",
        context_data=context_data,
        token_count=token_estimate
    )


async def search_knowledge(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search orchestration knowledge instead of reading multiple markdown files.
    
    Args:
        query: Search query
        entity_type: Optional entity type filter
        limit: Maximum results to return
        
    Returns:
        List of matching knowledge entities
    """
    memory = _ensure_initialized()
    
    return await memory.search_orchestration_knowledge(
        query=query,
        entity_type=entity_type,
        limit=limit
    )


async def get_specific_knowledge(entity_name: str) -> Optional[Dict[str, Any]]:
    """
    Get specific knowledge entity by name.
    
    Args:
        entity_name: Name of entity to retrieve
        
    Returns:
        Entity data if found, None otherwise
    """
    memory = _ensure_initialized()
    
    return await memory.get_orchestration_knowledge(entity_name)


async def search_patterns(pattern_type: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for specific patterns in knowledge base.
    
    Args:
        pattern_type: Type of pattern to search for
        limit: Maximum results to return
        
    Returns:
        List of matching pattern entities
    """
    memory = _ensure_initialized()
    
    return await memory.search_orchestration_knowledge(
        query=pattern_type,
        entity_type=MemoryEntityType.PATTERN_LIBRARY,
        limit=limit
    )


async def search_error_solutions(error_keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for error patterns and solutions.
    
    Args:
        error_keyword: Error keyword to search for
        limit: Maximum results to return
        
    Returns:
        List of matching error pattern entities
    """
    memory = _ensure_initialized()
    
    return await memory.search_orchestration_knowledge(
        query=error_keyword,
        entity_type=MemoryEntityType.ERROR_PATTERNS,
        limit=limit
    )


async def search_validation_history(validation_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for previous validation results.
    
    Args:
        validation_type: Type of validation to search for
        limit: Maximum results to return
        
    Returns:
        List of matching validation entities
    """
    memory = _ensure_initialized()
    
    return await memory.search_orchestration_knowledge(
        query=validation_type,
        entity_type=MemoryEntityType.DEPLOYMENT_EVIDENCE,
        limit=limit
    )


async def prevent_markdown_creation(
    intended_file_path: str,
    content: str,
    agent_name: Optional[str] = None
) -> str:
    """
    Prevent markdown file creation and redirect to memory service.
    
    This function should be called by orchestration wrapper when agents
    attempt to create markdown files.
    
    Args:
        intended_file_path: Path where markdown would have been created
        content: Content intended for markdown file
        agent_name: Name of agent attempting creation
        
    Returns:
        Entity name created in memory service
    """
    global _anti_pattern
    
    if _anti_pattern is None:
        raise RuntimeError("Memory utilities not initialized")
    
    # Determine entity type based on content and path
    suggested_type = _determine_entity_type_from_content(content, intended_file_path)
    
    # Redirect to memory service
    entity_name = await _anti_pattern.redirect_to_memory_service(
        intended_file_path=intended_file_path,
        content=content,
        suggested_entity_type=suggested_type
    )
    
    logger.info(f"Prevented markdown creation by {agent_name or 'unknown'}: {intended_file_path} -> {entity_name}")
    return entity_name


def _determine_entity_type_from_content(content: str, file_path: str) -> str:
    """Determine appropriate entity type from content and file path."""
    content_lower = content.lower()
    path_lower = file_path.lower()
    
    # Content-based detection
    if "validation" in content_lower and "evidence" in content_lower:
        return MemoryEntityType.DEPLOYMENT_EVIDENCE
    elif "security" in content_lower or "vulnerability" in content_lower:
        return MemoryEntityType.SECURITY_VALIDATION
    elif "performance" in content_lower or "metrics" in content_lower:
        return MemoryEntityType.PERFORMANCE_METRICS
    elif "error" in content_lower or "exception" in content_lower:
        return MemoryEntityType.ERROR_PATTERNS
    elif "configuration" in content_lower or "config" in content_lower:
        return MemoryEntityType.SYSTEM_CONFIGURATION
    elif "infrastructure" in content_lower or "deployment" in content_lower:
        return MemoryEntityType.INFRASTRUCTURE_ANALYSIS
    elif "api" in content_lower and ("endpoint" in content_lower or "documentation" in content_lower):
        return MemoryEntityType.API_DOCUMENTATION
    elif "orchestration" in content_lower or "workflow" in content_lower:
        return MemoryEntityType.ORCHESTRATION_WORKFLOW
    elif "audit" in content_lower or "report" in content_lower:
        return MemoryEntityType.AUDIT_REPORT
    elif "pattern" in content_lower or "solution" in content_lower:
        return MemoryEntityType.PATTERN_LIBRARY
    elif "context" in content_lower or "package" in content_lower:
        return MemoryEntityType.CONTEXT_PACKAGE
    elif "database" in content_lower or "schema" in content_lower:
        return MemoryEntityType.DATABASE_SCHEMA
    
    # Path-based detection as fallback
    if "validation" in path_lower:
        return MemoryEntityType.VALIDATION_PROTOCOL
    elif "security" in path_lower:
        return MemoryEntityType.SECURITY_VALIDATION
    elif "performance" in path_lower:
        return MemoryEntityType.PERFORMANCE_METRICS
    elif "infrastructure" in path_lower:
        return MemoryEntityType.INFRASTRUCTURE_ANALYSIS
    elif "error" in path_lower:
        return MemoryEntityType.ERROR_PATTERNS
    elif "config" in path_lower:
        return MemoryEntityType.SYSTEM_CONFIGURATION
    elif "api" in path_lower:
        return MemoryEntityType.API_DOCUMENTATION
    elif "orchestration" in path_lower:
        return MemoryEntityType.ORCHESTRATION_WORKFLOW
    elif "audit" in path_lower:
        return MemoryEntityType.AUDIT_REPORT
    
    # Default to agent findings
    return MemoryEntityType.AGENT_FINDINGS


# Utility functions for agent convenience

async def quick_store(
    name: str,
    content: Union[str, Dict[str, Any]],
    content_type: str = "analysis",
    agent_name: Optional[str] = None
) -> str:
    """
    Quick storage function for agents - automatically determines best storage method.
    
    Args:
        name: Name for the stored content
        content: Content to store
        content_type: Type of content (analysis, validation, config, etc.)
        agent_name: Name of storing agent
        
    Returns:
        Entity name for future reference
    """
    # Map content types to storage functions
    type_mapping = {
        "analysis": store_analysis,
        "validation": lambda n, c, a=None, **kwargs: store_validation_evidence(n, c if isinstance(c, dict) else {"content": c}, True, a),
        "config": store_configuration_analysis,
        "performance": store_performance_metrics,
        "security": store_security_analysis,
        "infrastructure": store_infrastructure_findings,
        "error": lambda n, c, a=None, **kwargs: store_error_pattern(n, c if isinstance(c, dict) else {"content": c}, None, a),
        "context": store_orchestration_context
    }
    
    # Use appropriate storage function
    storage_func = type_mapping.get(content_type, store_analysis)
    
    if content_type == "validation":
        return await storage_func(name, content, agent_name)
    elif content_type == "error":
        return await storage_func(name, content, agent_name)
    elif content_type == "context":
        return await storage_func(name, content if isinstance(content, dict) else {"content": content})
    else:
        return await storage_func(name, content, agent_name)


async def get_recent_knowledge(
    entity_type: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get recently created knowledge entities.
    
    Args:
        entity_type: Optional entity type filter
        limit: Maximum results to return
        
    Returns:
        List of recent knowledge entities
    """
    memory = _ensure_initialized()
    
    # Search with recent-focused query
    query = "created updated timestamp"
    if entity_type:
        query = f"{query} entityType:{entity_type}"
    
    return await memory.search_orchestration_knowledge(
        query=query,
        entity_type=entity_type,
        limit=limit
    )


# Export all public functions
__all__ = [
    "initialize_memory_utilities",
    "store_analysis",
    "store_validation_evidence", 
    "store_configuration_analysis",
    "store_performance_metrics",
    "store_security_analysis",
    "store_infrastructure_findings",
    "store_error_pattern",
    "store_orchestration_context",
    "search_knowledge",
    "get_specific_knowledge",
    "search_patterns",
    "search_error_solutions",
    "search_validation_history",
    "prevent_markdown_creation",
    "quick_store",
    "get_recent_knowledge"
]