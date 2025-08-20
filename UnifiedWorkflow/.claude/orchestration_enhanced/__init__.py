"""Enhanced Orchestration Package for Claude Code CLI

Next-generation ML-enhanced agentic orchestration system that integrates
machine learning at every decision point using only MCP services available
in Claude Code CLI.

This package replaces both the current ML and agentic flow systems with
a unified approach that provides:

- ML integration at every decision point
- Real inter-agent communication and coordination  
- Intelligent file organization and context management
- Evidence-based validation with concrete proof requirements
- Memory service integration for context replacement
- Enhanced error detection and validation systems

Key Components:
- MLEnhancedOrchestrator: Main orchestration controller
- MCPIntegrationLayer: MCP service coordination layer
- Intelligent file organization system
- Dynamic context assembly from memory service
- Evidence-based validation framework

Usage:
    from .claude.orchestration_enhanced import start_agentic_flow
    
    # Start the ML-enhanced agentic workflow
    result = await start_agentic_flow("orchestration")
    
    # Execute specific phases
    from .claude.orchestration_enhanced import execute_phase
    result = await execute_phase(0)  # Execute Phase 0: Todo Context Integration
    
    # Deploy critical services
    from .claude.orchestration_enhanced import deploy_services
    result = await deploy_services()
"""

# Import core ML orchestrator components with dependency status
from .ml_enhanced_orchestrator import (
    MLEnhancedOrchestrator,
    MLDecisionEngine,
    MLModelType,
    MLDecisionPoint,
    get_ml_enhanced_orchestrator,
    start_agentic_flow,
    start_streaming_fixes,
    execute_parallel_agents_with_ml,
    execute_ml_enhanced_audit,
    execute_phase,
    deploy_services,
    get_workflow_status,
    get_available_agents,
    get_orchestration_phases,
    get_ml_decision_engine,
    HAS_NUMPY
)

# Graceful import of MCP integration layer with fallback
try:
    from .mcp_integration_layer import (
        MCPIntegrationLayer,
        WorkflowPhase,
        AgentTask,
        AgentResult,
        get_mcp_integration_layer,
        reset_mcp_integration_layer
    )
    HAS_MCP_INTEGRATION = True
except ImportError:
    # Use fallback definitions from main orchestrator
    from .ml_enhanced_orchestrator import MCPIntegrationLayer, WorkflowPhase, AgentTask
    HAS_MCP_INTEGRATION = False
    
    # Provide fallback functions
    def get_mcp_integration_layer():
        return MCPIntegrationLayer()
    
    def reset_mcp_integration_layer():
        pass
    
    # Create fallback AgentResult if not available
    from dataclasses import dataclass
    from typing import Dict, Any
    
    @dataclass
    class AgentResult:
        agent_id: str
        success: bool
        result_data: Dict[str, Any]
        duration: float = 0.0

# Check for additional dependencies
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

__version__ = "1.0.0"
__author__ = "AI Workflow Engine"
__description__ = "ML-enhanced agentic orchestration using MCP services"

# Quick reference for trigger phrases that auto-start orchestration
ORCHESTRATION_TRIGGERS = [
    "orchestration",
    "agentic flow", 
    "agentic orchestration",
    "start agent",
    "start agents",
    "start flow"
]

# Available orchestration phases
ORCHESTRATION_PHASES = {
    0: "Todo Context Integration",
    1: "Agent Ecosystem Validation", 
    2: "Strategic Intelligence Planning",
    3: "Multi-Domain Research Discovery",
    4: "Context Synthesis & Compression",
    5: "Parallel Implementation Execution",
    6: "Comprehensive Evidence-Based Validation",
    7: "Decision & Iteration Control",
    8: "Atomic Version Control Synchronization",
    9: "Meta-Orchestration Audit & Learning",
    10: "Continuous Todo Integration & Loop Control"
}

# Agent categories and their purposes
AGENT_CATEGORIES = {
    "development": "Backend, database, code architecture specialists",
    "frontend": "Frontend architecture, React components, browser automation",
    "ux": "User experience design, friction elimination, creative interactions", 
    "quality": "Testing, validation, security, code quality assurance",
    "security": "Security validation, penetration testing, vulnerability assessment",
    "validation": "Production validation, user interaction testing, evidence collection",
    "testing": "Test automation, test generation, CI/CD integration",
    "performance": "Performance analysis, optimization, bottleneck identification",
    "infrastructure": "DevOps, deployment, monitoring, version control",
    "orchestration": "Workflow coordination, strategic planning, meta-analysis",
    "intelligence": "Pattern analysis, context synthesis, learning extraction"
}

# MCP services utilized by the orchestration system
MCP_SERVICES_USED = {
    "mcp__memory__": "Knowledge graph management for agent coordination",
    "mcp__orchestration-agent__": "Workflow orchestration and checkpointing",
    "mcp__sequential-thinking__": "Complex reasoning and decision analysis",
    "mcp__filesystem__": "Intelligent file organization and management",
    "mcp__firecrawl__": "Web research and content extraction",
    "mcp__playwright__": "UI automation and validation testing",
    "mcp__redis__": "Caching and session management",
    "mcp__mem0__": "Personal memory and context storage",
    "mcp__context7__": "Library documentation and reference"
}

# Dependency status information
DEPENDENCY_STATUS = {
    "numpy": HAS_NUMPY,
    "structlog": HAS_STRUCTLOG,
    "mcp_integration": HAS_MCP_INTEGRATION
}

# Graceful degradation features
FALLBACK_FEATURES = {
    "numpy_math": "Built-in Python math functions (mean, std)",
    "logging": "Standard Python logging module",
    "mcp_integration": "Minimal integration layer with basic functionality"
}

__all__ = [
    # Main orchestrator
    "MLEnhancedOrchestrator",
    "MLDecisionEngine", 
    "get_ml_enhanced_orchestrator",
    "get_ml_decision_engine",
    
    # ML components
    "MLModelType",
    "MLDecisionPoint",
    
    # Orchestration functions
    "start_agentic_flow",
    "start_streaming_fixes",
    "execute_parallel_agents_with_ml",
    "execute_ml_enhanced_audit",
    "execute_phase", 
    "deploy_services",
    "get_workflow_status",
    "get_available_agents",
    "get_orchestration_phases",
    
    # Integration layer
    "MCPIntegrationLayer",
    "WorkflowPhase",
    "AgentTask",
    "AgentResult",
    "get_mcp_integration_layer",
    "reset_mcp_integration_layer",
    
    # Dependency status
    "HAS_NUMPY",
    "HAS_STRUCTLOG",
    "HAS_MCP_INTEGRATION",
    "DEPENDENCY_STATUS",
    "FALLBACK_FEATURES",
    
    # Constants
    "ORCHESTRATION_TRIGGERS",
    "ORCHESTRATION_PHASES", 
    "AGENT_CATEGORIES",
    "MCP_SERVICES_USED"
]