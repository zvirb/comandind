"""Enhanced Orchestration Package

Next-generation ML-enhanced agentic orchestration system that integrates
machine learning at every decision point in the workflow.

Key Components:
- ML Service Bus: Centralized ML service coordination and communication
- Agent Communication Protocol: Inter-agent communication and coordination
- Dynamic Context Assembly: Intelligent context management using memory service
- Evidence-Based Validation: ML-enhanced validation and quality assurance
- File Organization System: Intelligent file placement and organization
"""

from .ml_service_bus import (
    MLServiceBus,
    MLRequest,
    MLResponse,
    ServiceEndpoint,
    ServiceStatus,
    get_ml_service_bus,
    shutdown_ml_service_bus,
    ml_service_bus_context
)

__version__ = "1.0.0"

__all__ = [
    "MLServiceBus",
    "MLRequest", 
    "MLResponse",
    "ServiceEndpoint",
    "ServiceStatus",
    "get_ml_service_bus",
    "shutdown_ml_service_bus",
    "ml_service_bus_context"
]