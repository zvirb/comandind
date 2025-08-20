"""Pytest configuration and fixtures for Hybrid Memory Service tests.

Provides comprehensive test fixtures, mocks, and utilities for testing
memory service functionality including database, vector storage, and LLM integration.
"""

import asyncio
import os
import tempfile
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient
import numpy as np
from faker import Faker

# Import application components
from hybrid_memory_service.main import create_app
from hybrid_memory_service.config import get_settings
from hybrid_memory_service.models import MemoryAddRequest, MemorySearchRequest
from hybrid_memory_service.services import (
    DatabaseService, QdrantService, OllamaService, MemoryPipeline
)

# Test configuration
os.environ.update({
    "TESTING": "true",
    "LOG_LEVEL": "WARNING",
    "DATABASE_ECHO": "false",
    "QDRANT_COLLECTION_NAME": "test_memories",
})

fake = Faker()


# ==================== Event Loop and Asyncio Fixtures ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== Configuration and Settings ====================

@pytest.fixture
def test_settings():
    """Override application settings for testing."""
    settings = get_settings()
    
    # Override with test-specific values
    settings.database_url = "postgresql+asyncpg://test:test@localhost:5432/test_memory_db"
    settings.qdrant_url = "http://localhost:6333"
    settings.qdrant_collection_name = "test_memories"
    settings.ollama_url = "http://localhost:11434"
    settings.ollama_model = "llama2"
    settings.debug = True
    settings.testing = True
    
    return settings


# ==================== Database Fixtures ====================

@pytest.fixture
async def test_db_engine():
    """Create test database engine with in-memory SQLite."""
    # Use SQLite in-memory for fast testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Create tables
    from hybrid_memory_service.models.memory import Base
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def mock_database_service():
    """Mock DatabaseService for testing."""
    mock_service = AsyncMock(spec=DatabaseService)
    
    # Mock health check
    mock_service.health_check.return_value = {
        "healthy": True,
        "memory_count": 100,
        "vector_count": 100,
        "connection_pool": {"active": 2, "idle": 8}
    }
    
    # Mock memory operations
    mock_service.add_memory.return_value = {
        "memory_id": str(uuid.uuid4()),
        "created_at": fake.date_time_this_year()
    }
    
    mock_service.search_memories.return_value = {
        "results": [],
        "total_count": 0
    }
    
    return mock_service


# ==================== Vector Database Fixtures ====================

@pytest.fixture
async def mock_qdrant_service():
    """Mock QdrantService for testing."""
    mock_service = AsyncMock(spec=QdrantService)
    
    # Mock health check
    mock_service.health_check.return_value = True
    mock_service.get_collection_info.return_value = {
        "points_count": 100,
        "segments_count": 2,
        "status": "green"
    }
    
    # Mock vector operations
    mock_service.add_vector.return_value = {"operation_id": 1, "status": "acknowledged"}
    mock_service.search_vectors.return_value = {
        "results": [],
        "total_count": 0
    }
    
    return mock_service


# ==================== LLM Service Fixtures ====================

@pytest.fixture
async def mock_ollama_service():
    """Mock OllamaService for testing."""
    mock_service = AsyncMock(spec=OllamaService)
    
    # Mock health check
    mock_service.health_check.return_value = True
    mock_service.ensure_model_ready.return_value = None
    
    # Mock text generation
    mock_service.generate_text.return_value = {
        "response": fake.text(max_nb_chars=500),
        "processing_time_ms": fake.random_int(min=100, max=1500)
    }
    
    # Mock vector generation
    mock_service.generate_embeddings.return_value = {
        "embeddings": np.random.rand(1536).tolist(),
        "processing_time_ms": fake.random_int(min=50, max=800)
    }
    
    return mock_service


# ==================== Memory Pipeline Fixtures ====================

@pytest.fixture
async def mock_memory_pipeline(mock_ollama_service, mock_database_service, mock_qdrant_service):
    """Mock MemoryPipeline for testing."""
    pipeline = MemoryPipeline(
        ollama_service=mock_ollama_service,
        database_service=mock_database_service,
        qdrant_service=mock_qdrant_service
    )
    
    # Mock pipeline methods
    pipeline.process_memory = AsyncMock(return_value={
        "memory_id": str(uuid.uuid4()),
        "processed_content": fake.text(max_nb_chars=200),
        "summary": fake.sentence(nb_words=10),
        "confidence_score": fake.random.uniform(0.8, 1.0),
        "processing_time_ms": fake.random_int(min=500, max=2000),
        "status": "success"
    })
    
    pipeline.search_memories = AsyncMock(return_value={
        "results": [],
        "total_count": 0,
        "processing_time_ms": fake.random_int(min=100, max=800),
        "similarity_threshold_used": 0.7
    })
    
    return pipeline


# ==================== Application Fixtures ====================

@pytest.fixture
async def test_app(test_settings, mock_memory_pipeline):
    """Create test FastAPI application with mocked services."""
    app = create_app()
    
    # Override services with mocks
    app.state.services = {
        "pipeline": mock_memory_pipeline,
        "ollama": mock_memory_pipeline.ollama_service,
        "database": mock_memory_pipeline.database_service,
        "qdrant": mock_memory_pipeline.qdrant_service
    }
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client for synchronous tests."""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app):
    """Create async test client for async tests."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


# ==================== Test Data Fixtures ====================

@pytest.fixture
def sample_memory_data():
    """Generate sample memory data for testing."""
    return {
        "content": fake.text(max_nb_chars=1000),
        "content_type": fake.random_element(["text", "note", "document"]),
        "source": fake.url(),
        "tags": fake.words(nb=3),
        "metadata": {
            "author": fake.name(),
            "created_date": fake.date_this_year().isoformat(),
            "category": fake.word()
        }
    }


@pytest.fixture
def sample_memory_requests():
    """Generate multiple sample memory requests."""
    return [
        MemoryAddRequest(
            content=fake.text(max_nb_chars=800),
            content_type="text",
            source=fake.url(),
            tags=fake.words(nb=2),
            metadata={"test": True}
        )
        for _ in range(5)
    ]


@pytest.fixture
def sample_search_queries():
    """Generate sample search queries."""
    return [
        {
            "query": fake.sentence(nb_words=5),
            "limit": fake.random_int(min=1, max=20),
            "similarity_threshold": fake.random.uniform(0.5, 0.9)
        }
        for _ in range(3)
    ]


# ==================== Performance Testing Fixtures ====================

@pytest.fixture
def performance_test_data():
    """Generate data for performance testing."""
    return {
        "small_content": fake.text(max_nb_chars=100),
        "medium_content": fake.text(max_nb_chars=1000),
        "large_content": fake.text(max_nb_chars=5000),
        "search_queries": [fake.sentence(nb_words=i) for i in range(1, 10)]
    }


# ==================== Mock External Services ====================

@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for external API calls."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        # Mock successful responses
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response
        
        yield mock_instance


# ==================== Utility Functions ====================

@pytest.fixture
def assert_response_time():
    """Utility to assert API response times."""
    def _assert_response_time(duration_ms: float, max_time_ms: float):
        assert duration_ms <= max_time_ms, f"Response time {duration_ms}ms exceeded {max_time_ms}ms"
    return _assert_response_time


@pytest.fixture
def create_test_vector():
    """Create test vectors with specified dimensions."""
    def _create_vector(dimensions: int = 1536) -> List[float]:
        return np.random.rand(dimensions).tolist()
    return _create_vector


# ==================== Database Test Helpers ====================

@pytest.fixture
async def populated_test_db(test_db_session):
    """Create a populated test database with sample data."""
    # Add sample memories to database
    from hybrid_memory_service.models.memory import Memory
    
    memories = [
        Memory(
            content=fake.text(max_nb_chars=500),
            processed_content=fake.text(max_nb_chars=200),
            content_type="text",
            source=fake.url(),
            summary=fake.sentence(nb_words=10),
            tags=fake.words(nb=3),
            metadata_={"test": True},
            confidence_score=fake.random.uniform(0.8, 1.0)
        )
        for _ in range(10)
    ]
    
    for memory in memories:
        test_db_session.add(memory)
    
    await test_db_session.commit()
    yield test_db_session


# ==================== Cleanup Fixtures ====================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Cleanup can be added here if needed


# ==================== Markers and Test Categories ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")


# ==================== Test Selection Functions ====================

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file names
        if "test_unit" in item.fspath.basename:
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        elif "test_e2e" in item.fspath.basename:
            item.add_marker(pytest.mark.e2e)
        elif "test_performance" in item.fspath.basename:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)