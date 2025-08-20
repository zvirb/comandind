"""Pytest configuration and fixtures for Perception Service tests.

Provides comprehensive test fixtures, mocks, and utilities for testing
image processing and vector generation functionality.
"""

import asyncio
import base64
import io
import os
import tempfile
from typing import AsyncGenerator, Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
import numpy as np
from PIL import Image
from faker import Faker

# Import application components
from perception_service.main import create_app
from perception_service.config import get_settings
from perception_service.models import ConceptualizeRequest, ConceptualizeResponse
from perception_service.services.ollama_service import OllamaService

# Test configuration
os.environ.update({
    "TESTING": "true",
    "LOG_LEVEL": "WARNING",
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
    settings.ollama_url = "http://localhost:11434"
    settings.ollama_model = "llava"
    settings.debug = True
    settings.testing = True
    settings.port = 8001
    
    return settings


# ==================== Ollama Service Fixtures ====================

@pytest.fixture
async def mock_ollama_service():
    """Mock OllamaService for testing."""
    mock_service = AsyncMock(spec=OllamaService)
    
    # Mock health check
    mock_service.health_check.return_value = True
    mock_service.is_model_ready.return_value = True
    mock_service.ensure_model_ready.return_value = None
    
    # Mock vector generation with realistic dimensions
    mock_service.generate_concept_vector.return_value = np.random.rand(1536).tolist()
    
    # Mock text generation for testing
    mock_service.generate_text.return_value = {
        "response": fake.text(max_nb_chars=200),
        "processing_time_ms": fake.random_int(min=100, max=1500)
    }
    
    return mock_service


# ==================== Application Fixtures ====================

@pytest.fixture
async def test_app(test_settings, mock_ollama_service):
    """Create test FastAPI application with mocked services."""
    app = create_app()
    
    # Override Ollama service with mock
    app.state.ollama_service = mock_ollama_service
    
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


# ==================== Image Data Fixtures ====================

@pytest.fixture
def create_test_image():
    """Create test images of various formats and sizes."""
    def _create_image(
        width: int = 256,
        height: int = 256,
        format: str = "JPEG",
        color: str = "RGB"
    ) -> bytes:
        """Create a test image with specified parameters."""
        # Create a simple test image
        image = Image.new(color, (width, height), (128, 128, 128))
        
        # Add some simple patterns for realism
        import random
        pixels = image.load()
        for i in range(0, width, 20):
            for j in range(0, height, 20):
                if color == "RGB":
                    pixels[i, j] = (
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255)
                    )
                else:
                    pixels[i, j] = random.randint(0, 255)
        
        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format=format, quality=95)
        return buffer.getvalue()
    
    return _create_image


@pytest.fixture
def sample_image_data(create_test_image):
    """Generate sample image data in different formats."""
    return {
        "small_jpeg": create_test_image(128, 128, "JPEG"),
        "medium_png": create_test_image(512, 512, "PNG"),
        "large_jpeg": create_test_image(1024, 1024, "JPEG"),
        "grayscale": create_test_image(256, 256, "JPEG", "L"),
    }


@pytest.fixture
def base64_encoded_images(sample_image_data):
    """Generate base64 encoded images for API testing."""
    return {
        name: base64.b64encode(data).decode("utf-8")
        for name, data in sample_image_data.items()
    }


@pytest.fixture
def sample_conceptualize_requests(base64_encoded_images):
    """Generate sample conceptualize requests."""
    return [
        ConceptualizeRequest(
            image_data=image_data,
            format="jpeg",
            prompt=fake.sentence(nb_words=8)
        )
        for name, image_data in base64_encoded_images.items()
    ]


# ==================== Performance Testing Fixtures ====================

@pytest.fixture
def performance_test_images(create_test_image):
    """Generate images of various sizes for performance testing."""
    return {
        "tiny": create_test_image(64, 64, "JPEG"),      # ~5KB
        "small": create_test_image(256, 256, "JPEG"),   # ~30KB
        "medium": create_test_image(512, 512, "JPEG"),  # ~100KB
        "large": create_test_image(1024, 1024, "JPEG"), # ~400KB
        "xlarge": create_test_image(2048, 2048, "JPEG") # ~1.5MB
    }


@pytest.fixture
def benchmark_scenarios():
    """Define benchmark scenarios for performance testing."""
    return [
        {
            "name": "baseline_performance",
            "description": "Standard 512x512 JPEG processing",
            "target_p95_ms": 2000,
            "iterations": 10
        },
        {
            "name": "high_resolution",
            "description": "Large 2048x2048 JPEG processing",
            "target_p95_ms": 5000,
            "iterations": 5
        },
        {
            "name": "batch_processing",
            "description": "Multiple concurrent requests",
            "target_p95_ms": 3000,
            "iterations": 20
        }
    ]


# ==================== Mock External Services ====================

@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for Ollama API calls."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        # Mock successful Ollama responses
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": fake.text(max_nb_chars=100),
            "done": True,
            "context": list(range(100)),  # Mock context tokens
            "created_at": fake.iso8601(),
            "model": "llava",
            "total_duration": fake.random_int(min=1000000, max=5000000),  # nanoseconds
            "load_duration": fake.random_int(min=100000, max=1000000),
            "prompt_eval_duration": fake.random_int(min=500000, max=2000000),
            "eval_duration": fake.random_int(min=1000000, max=3000000)
        }
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response
        
        yield mock_instance


# ==================== Utility Functions ====================

@pytest.fixture
def assert_response_time():
    """Utility to assert API response times meet P95 requirements."""
    def _assert_response_time(duration_ms: float, max_time_ms: float = 2000):
        assert duration_ms <= max_time_ms, (
            f"Response time {duration_ms}ms exceeded P95 target of {max_time_ms}ms"
        )
    return _assert_response_time


@pytest.fixture
def validate_vector_dimensions():
    """Utility to validate vector dimensions and properties."""
    def _validate_vector(
        vector: List[float],
        expected_dim: int = 1536,
        value_range: tuple = (-1.0, 1.0)
    ):
        assert len(vector) == expected_dim, (
            f"Vector has {len(vector)} dimensions, expected {expected_dim}"
        )
        assert all(isinstance(v, (int, float)) for v in vector), "Vector contains non-numeric values"
        assert all(value_range[0] <= v <= value_range[1] for v in vector), (
            f"Vector values outside expected range {value_range}"
        )
    return _validate_vector


@pytest.fixture
def image_similarity_checker():
    """Utility to check image similarity for validation."""
    def _check_similarity(image1_bytes: bytes, image2_bytes: bytes) -> float:
        """Calculate basic image similarity using histogram comparison."""
        try:
            img1 = Image.open(io.BytesIO(image1_bytes))
            img2 = Image.open(io.BytesIO(image2_bytes))
            
            # Convert to same mode for comparison
            img1 = img1.convert("RGB")
            img2 = img2.convert("RGB")
            
            # Simple histogram comparison
            hist1 = img1.histogram()
            hist2 = img2.histogram()
            
            # Calculate correlation
            sum1 = sum(hist1)
            sum2 = sum(hist2)
            if sum1 == 0 or sum2 == 0:
                return 0.0
            
            correlation = sum(h1 * h2 for h1, h2 in zip(hist1, hist2)) / (sum1 * sum2)
            return correlation
            
        except Exception:
            return 0.0
    
    return _check_similarity


# ==================== Load Testing Fixtures ====================

@pytest.fixture
def load_test_scenarios():
    """Define load testing scenarios."""
    return {
        "light_load": {
            "concurrent_users": 5,
            "requests_per_user": 10,
            "spawn_rate": 1
        },
        "medium_load": {
            "concurrent_users": 20,
            "requests_per_user": 25,
            "spawn_rate": 2
        },
        "heavy_load": {
            "concurrent_users": 50,
            "requests_per_user": 50,
            "spawn_rate": 5
        }
    }


# ==================== Cleanup Fixtures ====================

@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Cleanup temporary files, connections, etc.


# ==================== Markers and Test Categories ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")
    config.addinivalue_line("markers", "image: Image processing tests")
    config.addinivalue_line("markers", "vector: Vector generation tests")


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
        
        # Add specific markers for image and vector tests
        if "image" in item.name.lower():
            item.add_marker(pytest.mark.image)
        if "vector" in item.name.lower():
            item.add_marker(pytest.mark.vector)