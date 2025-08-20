"""Tests for the main FastAPI application."""

import base64
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch

# Create a simple test image (1x1 PNG)
TEST_IMAGE_PNG = base64.b64encode(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00'
    b'\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
).decode()


@pytest.fixture
def mock_ollama_service():
    """Mock OllamaService for testing."""
    mock_service = AsyncMock()
    mock_service.health_check.return_value = True
    mock_service.is_model_ready.return_value = True
    mock_service.ensure_model_ready.return_value = None
    mock_service.generate_concept_vector.return_value = [0.1] * 1536
    mock_service.close.return_value = None
    return mock_service


@pytest.fixture
def client(mock_ollama_service):
    """Create test client with mocked dependencies."""
    # Mock the lifespan to avoid actual Ollama initialization
    with patch('main.OllamaService', return_value=mock_ollama_service):
        from main import create_app
        app = create_app()
        app.state.ollama_service = mock_ollama_service
        
        with TestClient(app) as test_client:
            yield test_client


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_healthy(self, client, mock_ollama_service):
        """Test health check when service is healthy."""
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "checks" in data
        assert data["checks"]["ollama_service"]["healthy"] is True
        assert data["checks"]["llava_model"]["ready"] is True
    
    def test_health_check_unhealthy_ollama(self, client, mock_ollama_service):
        """Test health check when Ollama is unhealthy."""
        mock_ollama_service.health_check.return_value = False
        mock_ollama_service.is_model_ready.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["ollama_service"]["healthy"] is False
    
    def test_health_check_model_not_ready(self, client, mock_ollama_service):
        """Test health check when model is not ready."""
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["llava_model"]["ready"] is False


class TestConceptualizeEndpoint:
    """Test the conceptualize endpoint."""
    
    def test_conceptualize_success(self, client, mock_ollama_service):
        """Test successful image conceptualization."""
        mock_vector = [0.1] * 1536
        mock_ollama_service.generate_concept_vector.return_value = mock_vector
        
        request_data = {
            "image_data": TEST_IMAGE_PNG,
            "format": "png",
            "prompt": "Test image description"
        }
        
        response = client.post("/conceptualize", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "vector" in data
        assert "dimensions" in data
        assert "processing_time_ms" in data
        assert "request_id" in data
        assert len(data["vector"]) == 1536
        assert data["dimensions"] == 1536
        assert data["processing_time_ms"] >= 0
    
    def test_conceptualize_invalid_base64(self, client):
        """Test conceptualization with invalid base64 data."""
        request_data = {
            "image_data": "invalid_base64_data",
            "format": "png"
        }
        
        response = client.post("/conceptualize", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_conceptualize_empty_image_data(self, client):
        """Test conceptualization with empty image data."""
        request_data = {
            "image_data": "",
            "format": "png"
        }
        
        response = client.post("/conceptualize", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_conceptualize_invalid_format(self, client):
        """Test conceptualization with invalid image format."""
        request_data = {
            "image_data": TEST_IMAGE_PNG,
            "format": "invalid_format"
        }
        
        response = client.post("/conceptualize", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_conceptualize_service_error(self, client, mock_ollama_service):
        """Test conceptualization when service throws an error."""
        mock_ollama_service.generate_concept_vector.side_effect = Exception("Service error")
        
        request_data = {
            "image_data": TEST_IMAGE_PNG,
            "format": "png"
        }
        
        response = client.post("/conceptualize", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error"
    
    def test_conceptualize_with_custom_params(self, client, mock_ollama_service):
        """Test conceptualization with custom parameters."""
        mock_vector = [0.2] * 1536
        mock_ollama_service.generate_concept_vector.return_value = mock_vector
        
        request_data = {
            "image_data": TEST_IMAGE_PNG,
            "format": "png",
            "prompt": "Custom analysis prompt",
            "max_tokens": 256,
            "temperature": 0.5
        }
        
        response = client.post("/conceptualize", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["vector"]) == 1536
        
        # Verify service was called with image data
        mock_ollama_service.generate_concept_vector.assert_called_once()
        call_args = mock_ollama_service.generate_concept_vector.call_args
        assert call_args[1]["image_data"] == TEST_IMAGE_PNG
        assert call_args[1]["image_format"] == "png"


class TestMiddleware:
    """Test middleware functionality."""
    
    def test_request_id_header(self, client):
        """Test that request ID is added to response headers."""
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    def test_security_headers(self, client):
        """Test that security headers are added."""
        response = client.get("/health")
        
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    
    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options("/health")
        # Note: TestClient doesn't automatically handle CORS preflight
        # This is more of a smoke test
        assert response.status_code in [200, 405]


class TestMetrics:
    """Test metrics endpoint."""
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint is accessible."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        
        # Should contain some basic metrics
        content = response.text
        assert "perception_" in content  # Should have our custom metrics


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_content_type(self, client):
        """Test invalid content type handling."""
        response = client.post(
            "/conceptualize",
            data="not json",
            headers={"Content-Type": "text/plain"}
        )
        
        assert response.status_code == 415  # Unsupported Media Type
    
    def test_request_too_large(self, client):
        """Test handling of requests that are too large."""
        # Create a very large base64 string (this is a simplified test)
        large_data = "A" * (50 * 1024 * 1024)  # 50MB of 'A's
        
        request_data = {
            "image_data": large_data,
            "format": "png"
        }
        
        # This should fail validation before reaching the middleware
        response = client.post("/conceptualize", json=request_data)
        
        # Could be 413 (middleware) or 422 (validation)
        assert response.status_code in [413, 422]


@pytest.mark.asyncio
class TestAsyncFunctionality:
    """Test async functionality."""
    
    async def test_concurrent_requests(self, client, mock_ollama_service):
        """Test handling of concurrent requests."""
        import asyncio
        from httpx import AsyncClient
        
        # Mock different vectors for different requests
        mock_ollama_service.generate_concept_vector.side_effect = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.3] * 1536
        ]
        
        request_data = {
            "image_data": TEST_IMAGE_PNG,
            "format": "png"
        }
        
        async def make_request():
            async with AsyncClient(app=client.app, base_url="http://test") as ac:
                return await ac.post("/conceptualize", json=request_data)
        
        # Make 3 concurrent requests
        tasks = [make_request() for _ in range(3)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert len(data["vector"]) == 1536