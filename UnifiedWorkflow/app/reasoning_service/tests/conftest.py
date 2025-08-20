"""Test configuration and fixtures for Reasoning Service tests."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from ..main import create_app
from ..config import ReasoningSettings
from ..services import OllamaService, RedisService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings configuration."""
    return ReasoningSettings(
        debug=True,
        database_url="sqlite+aiosqlite:///test.db",
        redis_url="redis://localhost:6379/15",  # Test database
        ollama_url="http://localhost:11434",
        evidence_validation_threshold=0.85,
        confidence_threshold=0.7,
        cognitive_event_routing=False,  # Disable for tests
        learning_feedback_enabled=False  # Disable for tests
    )


@pytest.fixture
def mock_ollama_service():
    """Mock Ollama service for testing."""
    mock = AsyncMock(spec=OllamaService)
    mock.health_check.return_value = True
    mock.is_model_ready.return_value = True
    mock.ensure_model_ready.return_value = True
    
    # Default LLM response
    mock.generate_reasoning.return_value = {
        "response": "Test reasoning response",
        "processing_time_ms": 100,
        "model": "test-model",
        "tokens_evaluated": 50,
        "tokens_generated": 25
    }
    
    mock.generate_structured_reasoning.return_value = {
        "response": "Test structured response",
        "processing_time_ms": 120,
        "parsing_success": True,
        "structured_response": {
            "validity_score": 0.9,
            "confidence": 0.85,
            "conclusion": "Test conclusion"
        }
    }
    
    return mock


@pytest.fixture
def mock_redis_service():
    """Mock Redis service for testing."""
    mock = AsyncMock(spec=RedisService)
    mock.health_check.return_value = True
    mock.initialize.return_value = None
    mock.store_reasoning_state.return_value = True
    mock.get_reasoning_state.return_value = {}
    mock.publish_cognitive_event.return_value = True
    mock.record_performance_metric.return_value = True
    
    return mock


@pytest.fixture
def mock_services(mock_ollama_service, mock_redis_service):
    """Collection of mocked services."""
    return {
        "ollama": mock_ollama_service,
        "redis": mock_redis_service,
        "service_integrator": AsyncMock(),
        "evidence_validator": AsyncMock(),
        "decision_analyzer": AsyncMock(),
        "hypothesis_tester": AsyncMock(),
        "reasoning_engine": AsyncMock()
    }


@pytest.fixture
def test_app(mock_services):
    """Test FastAPI application with mocked services."""
    app = create_app()
    app.state.services = mock_services
    return app


@pytest.fixture
def client(test_app):
    """Test client for API endpoints."""
    return TestClient(test_app)


@pytest.fixture
def sample_evidence():
    """Sample evidence data for testing."""
    return [
        {
            "content": "Multiple studies show correlation between variables",
            "source": "Academic research database",
            "confidence": 0.9,
            "metadata": {"study_count": 5, "peer_reviewed": True}
        },
        {
            "content": "Field observations confirm theoretical predictions", 
            "source": "Field research team",
            "confidence": 0.85,
            "metadata": {"observation_period": "6 months", "sample_size": 1000}
        }
    ]


@pytest.fixture
def sample_decision_request():
    """Sample multi-criteria decision request."""
    return {
        "context": "Selecting software architecture for new system",
        "options": [
            {
                "name": "Microservices",
                "description": "Distributed microservices architecture",
                "attributes": {"complexity": 8, "scalability": 9, "cost": 7}
            },
            {
                "name": "Monolith", 
                "description": "Traditional monolithic architecture",
                "attributes": {"complexity": 4, "scalability": 5, "cost": 3}
            }
        ],
        "criteria": [
            {"name": "Complexity", "weight": 0.3, "measurement_type": "numeric"},
            {"name": "Scalability", "weight": 0.4, "measurement_type": "numeric"},
            {"name": "Cost", "weight": 0.3, "measurement_type": "numeric"}
        ]
    }


@pytest.fixture
def sample_hypothesis_request():
    """Sample hypothesis testing request."""
    return {
        "hypothesis": "New feature will increase user engagement by 15%",
        "evidence": [
            {
                "content": "A/B test results show 12% increase in session duration",
                "source": "Analytics platform",
                "confidence": 0.88
            }
        ],
        "context": "Product feature evaluation",
        "significance_level": 0.05
    }


@pytest.fixture
def sample_reasoning_request():
    """Sample reasoning chain request."""
    return {
        "initial_premise": "System shows high CPU usage and memory leaks",
        "goal": "Determine root cause and solution",
        "context": "Production system debugging",
        "max_steps": 5,
        "reasoning_type": "abductive"
    }