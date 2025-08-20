"""Coordination Service - Central Agent Orchestration Bus

This service serves as the central orchestration hub managing 47+ specialist agents,
workflow execution, and inter-service coordination with <30s recovery time.

Key Features:
- Event-driven agent coordination with no direct agent-to-agent communication  
- Context package generation with intelligent <4000 token limit enforcement
- Redis-backed workflow state with PostgreSQL persistence
- Automatic dependency resolution for sequential and parallel execution
- <30s workflow recovery time after service restart

Architecture:
- AgentOrchestrator: Main coordination engine managing agent lifecycles
- WorkflowStateManager: Persistent workflow state with Redis caching
- ContextPackageGenerator: Intelligent context compression for agent tasks
- CognitiveEventHandler: Cross-service event processing and routing
- AgentRegistry: Dynamic agent discovery and capability management
- PerformanceMonitor: Real-time performance tracking and optimization

This service operates as a stateless coordination layer with stateful workflow
persistence, enabling horizontal scaling while maintaining workflow consistency.
"""

__version__ = "1.0.0"
__author__ = "AIWFE Cognitive Architecture Team"
__description__ = "Central Agent Orchestration Bus for Multi-Agent Coordination"

# Package metadata
__all__ = [
    "__version__",
    "__author__", 
    "__description__"
]

# Service information
SERVICE_NAME = "coordination-service"
SERVICE_PORT = 8004
SERVICE_HEALTH_ENDPOINT = "/health"

# Default configuration values
DEFAULT_MAX_CONTEXT_TOKENS = 4000
DEFAULT_MAX_CONCURRENT_WORKFLOWS = 10
DEFAULT_RECOVERY_TIMEOUT = 30
DEFAULT_REDIS_DB = 2

# Agent orchestration constants
AGENT_COORDINATION_NAMESPACE = "agent:coordination"
WORKFLOW_STATE_NAMESPACE = "workflow:state"
COGNITIVE_EVENT_NAMESPACE = "cognitive:events"
PERFORMANCE_METRICS_NAMESPACE = "performance:metrics"