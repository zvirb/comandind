#!/usr/bin/env python3
"""
Orchestration Wrapper for Memory Service Integration

Provides wrapper functions that intercept markdown file creation attempts
and redirect them to the memory MCP service. This prevents the anti-pattern
of creating documentation files in the project root.

Key Features:
- Intercepts Write() calls for .md files
- Redirects to memory service automatically
- Provides agent-friendly interfaces
- Maintains compatibility with existing orchestration patterns
- Enforces memory-first knowledge storage
"""

import asyncio
import functools
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

from .memory_utilities import (
    initialize_memory_utilities,
    prevent_markdown_creation,
    store_analysis,
    store_validation_evidence,
    store_configuration_analysis,
    store_performance_metrics,
    store_security_analysis,
    store_infrastructure_findings,
    store_error_pattern,
    store_orchestration_context,
    search_knowledge,
    quick_store
)

logger = logging.getLogger(__name__)

# Global state for wrapper functionality
_wrapper_initialized = False
_agent_context = {}
_markdown_prevention_enabled = True


async def initialize_orchestration_wrapper(mcp_functions: Dict[str, Any]) -> None:
    """
    Initialize the orchestration wrapper with memory service integration.
    
    Args:
        mcp_functions: Dictionary containing MCP function references
    """
    global _wrapper_initialized
    
    try:
        await initialize_memory_utilities(mcp_functions)
        _wrapper_initialized = True
        logger.info("Orchestration wrapper initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestration wrapper: {e}")
        raise


def set_agent_context(agent_name: str, agent_type: str = "unknown") -> None:
    """
    Set current agent context for proper attribution.
    
    Args:
        agent_name: Name of the current agent
        agent_type: Type/category of the agent
    """
    global _agent_context
    _agent_context = {
        "name": agent_name,
        "type": agent_type,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    logger.debug(f"Set agent context: {agent_name} ({agent_type})")


def get_current_agent() -> str:
    """Get current agent name from context."""
    return _agent_context.get("name", "unknown_agent")


def enable_markdown_prevention(enabled: bool = True) -> None:
    """
    Enable or disable markdown file creation prevention.
    
    Args:
        enabled: Whether to prevent markdown file creation
    """
    global _markdown_prevention_enabled
    _markdown_prevention_enabled = enabled
    logger.info(f"Markdown prevention {'enabled' if enabled else 'disabled'}")


class MemoryServiceWrite:
    """
    Wrapper for Write function that intercepts markdown file creation.
    
    Provides compatibility with existing orchestration patterns while
    redirecting markdown files to memory service.
    """
    
    def __init__(self, original_write_func: Callable):
        """
        Initialize with original Write function.
        
        Args:
            original_write_func: Original Write function to wrap
        """
        self.original_write = original_write_func
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def __call__(
        self,
        file_path: str,
        content: str,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        Wrapped Write function with markdown interception.
        
        Args:
            file_path: Path to write to
            content: Content to write
            **kwargs: Additional arguments for original Write function
            
        Returns:
            Result from original Write or memory service entity name
        """
        if not _wrapper_initialized:
            self.logger.warning("Orchestration wrapper not initialized, using original Write")
            return await self.original_write(file_path, content, **kwargs)
        
        # Check if this is a markdown file creation attempt
        if _markdown_prevention_enabled and file_path.lower().endswith('.md'):
            self.logger.info(f"Intercepting markdown file creation: {file_path}")
            
            # Prevent markdown creation and redirect to memory service
            try:
                entity_name = await prevent_markdown_creation(
                    intended_file_path=file_path,
                    content=content,
                    agent_name=get_current_agent()
                )
                
                self.logger.info(f"Redirected markdown creation to memory: {file_path} -> {entity_name}")
                
                # Return information about the redirection
                return {
                    "status": "redirected_to_memory",
                    "original_path": file_path,
                    "entity_name": entity_name,
                    "message": f"Markdown file creation prevented. Content stored in memory as: {entity_name}"
                }
                
            except Exception as e:
                self.logger.error(f"Failed to redirect markdown creation: {e}")
                # Fall back to original Write in case of memory service failure
                self.logger.warning("Falling back to original Write due to memory service error")
                return await self.original_write(file_path, content, **kwargs)
        
        # For non-markdown files, use original Write function
        return await self.original_write(file_path, content, **kwargs)


class AgentMemoryInterface:
    """
    High-level interface for agents to store knowledge without creating files.
    
    Provides specialized methods for common agent operations with automatic
    classification and storage in the memory service.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def store_research_findings(
        self,
        topic: str,
        findings: Union[str, Dict[str, Any]],
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store research findings from analysis agents.
        
        Args:
            topic: Research topic or area
            findings: Research findings and analysis
            agent_name: Name of researching agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        return await store_analysis(
            analysis_name=f"research_{topic}",
            content=findings,
            agent_name=agent,
            analysis_type="research"
        )
    
    async def store_validation_results(
        self,
        validation_type: str,
        results: Dict[str, Any],
        success: bool,
        evidence: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store validation results from QA agents.
        
        Args:
            validation_type: Type of validation performed
            results: Validation results and data
            success: Whether validation succeeded
            evidence: Optional evidence data
            agent_name: Name of validating agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        # Combine results and evidence
        combined_evidence = {
            "results": results,
            "success": success,
            "evidence": evidence or {},
            "validation_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return await store_validation_evidence(
            validation_name=validation_type,
            evidence=combined_evidence,
            success=success,
            agent_name=agent
        )
    
    async def store_implementation_report(
        self,
        component: str,
        implementation_details: Union[str, Dict[str, Any]],
        status: str = "completed",
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store implementation reports from development agents.
        
        Args:
            component: Component or feature implemented
            implementation_details: Implementation details and notes
            status: Implementation status (completed, in_progress, failed)
            agent_name: Name of implementing agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        # Structure implementation data
        impl_data = {
            "component": component,
            "status": status,
            "details": implementation_details,
            "implemented_by": agent,
            "implementation_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return await store_analysis(
            analysis_name=f"implementation_{component}",
            content=impl_data,
            agent_name=agent,
            analysis_type="implementation"
        )
    
    async def store_system_status(
        self,
        system_component: str,
        status_data: Dict[str, Any],
        health_status: str = "unknown",
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store system status reports from monitoring agents.
        
        Args:
            system_component: System component being monitored
            status_data: Status and health data
            health_status: Overall health (healthy, degraded, failed, unknown)
            agent_name: Name of monitoring agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        return await store_infrastructure_findings(
            component_name=system_component,
            findings=status_data,
            status=health_status,
            agent_name=agent
        )
    
    async def store_security_findings(
        self,
        security_area: str,
        findings: Dict[str, Any],
        severity: str = "medium",
        remediation: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store security findings from security agents.
        
        Args:
            security_area: Area of security analyzed
            findings: Security findings and vulnerabilities
            severity: Severity level (low, medium, high, critical)
            remediation: Optional remediation steps
            agent_name: Name of security agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        # Structure security data
        security_data = {
            "area": security_area,
            "findings": findings,
            "severity": severity,
            "remediation": remediation,
            "analyzed_by": agent,
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return await store_security_analysis(
            security_area=security_area,
            analysis=security_data,
            severity=severity,
            agent_name=agent
        )
    
    async def store_performance_analysis(
        self,
        component: str,
        metrics: Dict[str, Any],
        recommendations: Optional[List[str]] = None,
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store performance analysis from performance agents.
        
        Args:
            component: Component analyzed for performance
            metrics: Performance metrics and data
            recommendations: Optional performance recommendations
            agent_name: Name of performance agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        # Structure performance data
        perf_data = {
            "component": component,
            "metrics": metrics,
            "recommendations": recommendations or [],
            "analyzed_by": agent,
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return await store_performance_metrics(
            metric_name=component,
            metrics=perf_data,
            agent_name=agent
        )
    
    async def store_error_analysis(
        self,
        error_type: str,
        error_details: Dict[str, Any],
        root_cause: Optional[str] = None,
        solution: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> str:
        """
        Store error analysis from debugging agents.
        
        Args:
            error_type: Type or category of error
            error_details: Detailed error information
            root_cause: Optional root cause analysis
            solution: Optional solution or workaround
            agent_name: Name of debugging agent
            
        Returns:
            Entity name for future reference
        """
        agent = agent_name or get_current_agent()
        
        # Structure error data
        error_data = {
            "type": error_type,
            "details": error_details,
            "root_cause": root_cause,
            "analyzed_by": agent,
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return await store_error_pattern(
            error_name=error_type,
            error_data=error_data,
            solution=solution,
            agent_name=agent
        )
    
    async def search_previous_work(
        self,
        topic: str,
        agent_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for previous work by topic or agent type.
        
        Args:
            topic: Topic to search for
            agent_type: Optional agent type filter
            limit: Maximum results to return
            
        Returns:
            List of matching knowledge entities
        """
        # Build search query
        query = topic
        if agent_type:
            query = f"{query} {agent_type}"
        
        return await search_knowledge(
            query=query,
            limit=limit
        )
    
    async def get_context_for_task(
        self,
        task_type: str,
        specific_area: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get context information for a specific task type.
        
        Args:
            task_type: Type of task being performed
            specific_area: Optional specific area within task type
            limit: Maximum context items to return
            
        Returns:
            List of relevant context entities
        """
        # Build context search query
        query = task_type
        if specific_area:
            query = f"{query} {specific_area}"
        
        # Search for relevant context
        results = await search_knowledge(
            query=query,
            limit=limit
        )
        
        # Log context retrieval for debugging
        self.logger.info(f"Retrieved {len(results)} context items for task: {task_type}")
        
        return results


# Global agent memory interface instance
agent_memory = AgentMemoryInterface()


def create_memory_aware_agent_wrapper(agent_func: Callable) -> Callable:
    """
    Decorator to create memory-aware agent wrapper.
    
    Automatically sets agent context and provides memory interface.
    
    Args:
        agent_func: Original agent function to wrap
        
    Returns:
        Wrapped agent function with memory integration
    """
    @functools.wraps(agent_func)
    async def wrapped_agent(*args, **kwargs):
        # Extract agent name from function name or arguments
        agent_name = agent_func.__name__.replace('_', '-')
        
        # Set agent context
        set_agent_context(agent_name)
        
        # Add memory interface to kwargs
        kwargs['memory'] = agent_memory
        
        try:
            # Execute original agent function
            result = await agent_func(*args, **kwargs)
            
            # Log successful execution
            logger.info(f"Agent {agent_name} completed successfully with memory integration")
            
            return result
            
        except Exception as e:
            # Log error and store in memory
            logger.error(f"Agent {agent_name} failed: {e}")
            
            try:
                await agent_memory.store_error_analysis(
                    error_type="agent_execution_error",
                    error_details={
                        "agent": agent_name,
                        "error": str(e),
                        "args": str(args)[:500],  # Limit for storage
                        "kwargs": str({k: str(v)[:100] for k, v in kwargs.items()})[:500]
                    },
                    agent_name=agent_name
                )
            except Exception as storage_error:
                logger.error(f"Failed to store agent error in memory: {storage_error}")
            
            raise
    
    return wrapped_agent


# Utility functions for orchestration integration

async def wrap_orchestration_tools(tool_dict: Dict[str, Callable]) -> Dict[str, Callable]:
    """
    Wrap orchestration tools with memory service integration.
    
    Args:
        tool_dict: Dictionary of tool functions to wrap
        
    Returns:
        Dictionary of wrapped tool functions
    """
    wrapped_tools = {}
    
    for tool_name, tool_func in tool_dict.items():
        if tool_name == "Write":
            # Wrap Write function with markdown interception
            wrapped_tools[tool_name] = MemoryServiceWrite(tool_func)
        else:
            # Keep other tools as-is
            wrapped_tools[tool_name] = tool_func
    
    logger.info(f"Wrapped {len(wrapped_tools)} orchestration tools with memory integration")
    return wrapped_tools


def get_memory_usage_statistics() -> Dict[str, Any]:
    """
    Get statistics about memory service usage.
    
    Returns:
        Dictionary containing usage statistics
    """
    global _agent_context
    
    return {
        "wrapper_initialized": _wrapper_initialized,
        "markdown_prevention_enabled": _markdown_prevention_enabled,
        "current_agent": _agent_context.get("name", "none"),
        "agent_context": _agent_context
    }


# Export public interface
__all__ = [
    "initialize_orchestration_wrapper",
    "set_agent_context",
    "get_current_agent",
    "enable_markdown_prevention",
    "MemoryServiceWrite",
    "AgentMemoryInterface",
    "agent_memory",
    "create_memory_aware_agent_wrapper",
    "wrap_orchestration_tools",
    "get_memory_usage_statistics"
]