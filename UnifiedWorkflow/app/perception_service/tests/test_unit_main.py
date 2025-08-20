"""Unit tests for Perception Service main application.

Tests the FastAPI application, endpoints, middleware, and error handling
with comprehensive mocking of dependencies.
"""

import asyncio
import base64
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import numpy as np
from fastapi import status
from fastapi.testclient import TestClient

from perception_service.main import create_app
from perception_service.models import ConceptualizeRequest, ConceptualizeResponse


class TestApplicationCreation:
    """Test FastAPI application creation and configuration."""
    
    def test_create_app_structure(self):
        """Test that the application is created with correct structure."""
        app = create_app()
        
        assert app.title == "Perception Service"
        assert "AI-powered image analysis" in app.description
        assert app.version == "1.0.0"
        
        # Check that routes exist
        routes = [route.path for route in app.routes]
        expected_routes = ["/health", "/metrics", "/conceptualize"]
        
        for expected_route in expected_routes:
            assert any(expected_route in route for route in routes), f"Route {expected_route} not found"
    
    def test_middleware_configuration(self):
        """Test that middleware is properly configured."""
        app = create_app()
        
        middleware_classes = [middleware.cls.__name__ for middleware in app.user_middleware]
        
        # Should include CORS and custom middleware
        assert "CORSMiddleware" in middleware_classes
        assert "LoggingMiddleware" in middleware_classes
        assert "MetricsMiddleware" in middleware_classes


class TestHealthEndpoint:
    """Test health check endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client, mock_ollama_service):
        """Test successful health check response."""
        # Configure mock service
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "checks" in health_data
        
        # Verify service checks
        checks = health_data["checks"]
        assert "ollama_service" in checks
        assert "llava_model" in checks
        assert checks["ollama_service"]["healthy"] is True
        assert checks["llava_model"]["ready"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_ollama_unhealthy(self, async_client, mock_ollama_service):
        """Test health check when Ollama service is unhealthy."""
        mock_ollama_service.health_check.return_value = False
        mock_ollama_service.is_model_ready.return_value = True
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        assert health_data["status"] == "unhealthy"
        assert health_data["checks"]["ollama_service"]["healthy"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_model_not_ready(self, async_client, mock_ollama_service):
        """Test health check when LLaVA model is not ready."""
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = False
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        assert health_data["status"] == "unhealthy"
        assert health_data["checks"]["llava_model"]["ready"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_service_error(self, async_client):
        """Test health check when service throws exception."""
        with patch('perception_service.main.app.state') as mock_state:
            mock_state.ollama_service.health_check.side_effect = Exception("Service error")
            
            response = await async_client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "unhealthy"
            assert "error" in health_data["checks"]
    
    @pytest.mark.asyncio
    async def test_health_check_latency_measurement(self, async_client, mock_ollama_service):
        """Test that health check measures Ollama service latency."""
        # Mock a slow health check
        async def slow_health_check():
            await asyncio.sleep(0.1)  # 100ms delay
            return True
        
        mock_ollama_service.health_check.side_effect = slow_health_check
        mock_ollama_service.is_model_ready.return_value = True
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        latency_ms = health_data["checks"]["ollama_service"]["latency_ms"]
        
        # Should be at least 100ms due to our sleep
        assert latency_ms >= 100


class TestConceptualizeEndpoint:
    """Test image conceptualization endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_conceptualize_success(self, async_client, mock_ollama_service, create_test_image):
        """Test successful image conceptualization."""
        # Create test image
        test_image = create_test_image(256, 256, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Mock service response
        test_vector = np.random.rand(1536).tolist()
        mock_ollama_service.generate_concept_vector.return_value = test_vector
        
        request_data = {
            "image_data": image_b64,
            "format": "jpeg",
            "prompt": "Describe this image"
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert "vector" in result
        assert "dimensions" in result
        assert "processing_time_ms" in result
        assert "request_id" in result
        
        assert len(result["vector"]) == 1536
        assert result["dimensions"] == 1536
        assert isinstance(result["processing_time_ms"], (int, float))
    
    @pytest.mark.asyncio
    async def test_conceptualize_with_custom_prompt(self, async_client, mock_ollama_service, create_test_image):
        """Test conceptualization with custom prompt."""
        test_image = create_test_image(128, 128, "PNG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        custom_prompt = "What objects are visible in this scene?"
        
        test_vector = np.random.rand(1536).tolist()
        mock_ollama_service.generate_concept_vector.return_value = test_vector
        
        request_data = {
            "image_data": image_b64,
            "format": "png",
            "prompt": custom_prompt
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify custom prompt was passed to service
        mock_ollama_service.generate_concept_vector.assert_called_once()
        call_args = mock_ollama_service.generate_concept_vector.call_args
        assert call_args.kwargs["prompt"] == custom_prompt
    
    @pytest.mark.asyncio
    async def test_conceptualize_invalid_image_data(self, async_client):
        """Test conceptualization with invalid image data."""
        request_data = {
            "image_data": "not-valid-base64",
            "format": "jpeg"
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.json()
    
    @pytest.mark.asyncio
    async def test_conceptualize_unsupported_format(self, async_client, create_test_image):
        """Test conceptualization with unsupported image format."""
        test_image = create_test_image(200, 200, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        request_data = {
            "image_data": image_b64,
            "format": "bmp"  # Unsupported format
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported image format" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_conceptualize_missing_fields(self, async_client):
        """Test conceptualization with missing required fields."""
        # Missing image_data
        request_data = {
            "format": "jpeg"
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_conceptualize_service_error(self, async_client, mock_ollama_service, create_test_image):
        """Test conceptualization when service throws exception."""
        test_image = create_test_image(150, 150, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Mock service error
        mock_ollama_service.generate_concept_vector.side_effect = RuntimeError("Service error")
        
        request_data = {
            "image_data": image_b64,
            "format": "jpeg"
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Internal server error"
    
    @pytest.mark.asyncio
    async def test_conceptualize_large_image(self, async_client, mock_ollama_service, create_test_image):
        """Test conceptualization with large image."""
        # Create large test image
        test_image = create_test_image(1024, 1024, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        test_vector = np.random.rand(1536).tolist()
        mock_ollama_service.generate_concept_vector.return_value = test_vector
        
        request_data = {
            "image_data": image_b64,
            "format": "jpeg",
            "prompt": "Analyze this high-resolution image"
        }
        
        response = await async_client.post("/conceptualize", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert len(result["vector"]) == 1536


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_accessibility(self, async_client):
        """Test that metrics endpoint is accessible."""
        response = await async_client.get("/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/plain" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_metrics_content_format(self, async_client):
        """Test metrics content format."""
        response = await async_client.get("/metrics")
        
        content = response.text
        
        # Should contain Prometheus-formatted metrics
        assert "# HELP" in content
        assert "# TYPE" in content


class TestErrorHandling:
    """Test global error handling and exception management."""
    
    @pytest.mark.asyncio
    async def test_global_exception_handler(self, async_client):
        """Test global exception handler for unhandled errors."""
        with patch('perception_service.main.app.state') as mock_state:
            # Make the mock service raise an unhandled exception
            mock_state.ollama_service.health_check.side_effect = RuntimeError("Unhandled error")
            
            response = await async_client.get("/health")
            
            # Should still return a proper error response
            assert response.status_code in [200, 500]  # Health endpoint handles its own errors
    
    @pytest.mark.asyncio
    async def test_request_validation_errors(self, async_client):
        """Test request validation error handling."""
        # Send request with wrong data types
        invalid_request = {
            "image_data": 12345,  # Should be string
            "format": ["jpeg"],    # Should be string
        }
        
        response = await async_client.post("/conceptualize", json=invalid_request)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        error_detail = response.json()
        assert "detail" in error_detail
        assert isinstance(error_detail["detail"], list)


class TestPerformanceMetrics:
    """Test performance metrics collection and reporting."""
    
    @pytest.mark.asyncio
    async def test_request_duration_tracking(self, async_client, mock_ollama_service, create_test_image):
        """Test that request duration is properly tracked."""
        test_image = create_test_image(200, 200, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Mock slow processing to test timing
        async def slow_processing(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = slow_processing
        
        request_data = {
            "image_data": image_b64,
            "format": "jpeg"
        }
        
        start_time = time.time()
        response = await async_client.post("/conceptualize", json=request_data)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        processing_time = result["processing_time_ms"]
        
        # Processing time should be at least 100ms due to our mock delay
        assert processing_time >= 100
        
        # Total request time should be reasonable
        total_time_ms = (end_time - start_time) * 1000
        assert total_time_ms >= processing_time


class TestConcurrentRequests:
    """Test handling of concurrent requests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_conceptualization_requests(
        self, async_client, mock_ollama_service, create_test_image
    ):
        """Test handling multiple concurrent conceptualization requests."""
        test_image = create_test_image(150, 150, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Mock service to return different vectors for each request
        test_vectors = [np.random.rand(1536).tolist() for _ in range(5)]
        mock_ollama_service.generate_concept_vector.side_effect = test_vectors
        
        request_data = {
            "image_data": image_b64,
            "format": "jpeg",
            "prompt": "Concurrent test"
        }
        
        # Send multiple requests concurrently
        tasks = [
            async_client.post("/conceptualize", json=request_data)
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert len(result["vector"]) == 1536
        
        # Service should have been called for each request
        assert mock_ollama_service.generate_concept_vector.call_count == 5


@pytest.mark.unit
@pytest.mark.api
class TestAPISpecification:
    """Test API specification compliance."""
    
    def test_openapi_schema_generation(self):
        """Test that OpenAPI schema is properly generated."""
        app = create_app()
        
        # Should be able to generate OpenAPI schema without errors
        openapi_schema = app.openapi()
        
        assert openapi_schema is not None
        assert "info" in openapi_schema
        assert "paths" in openapi_schema
        
        # Check required endpoints are documented
        paths = openapi_schema["paths"]
        assert "/health" in paths
        assert "/conceptualize" in paths
    
    def test_request_response_models(self):
        """Test request and response model definitions."""
        # Test ConceptualizeRequest model
        test_image_data = base64.b64encode(b"test").decode("utf-8")
        request = ConceptualizeRequest(
            image_data=test_image_data,
            format="jpeg",
            prompt="Test prompt"
        )
        
        assert request.image_data == test_image_data
        assert request.format == "jpeg"
        assert request.prompt == "Test prompt"
        
        # Test ConceptualizeResponse model
        test_vector = list(range(1536))
        response = ConceptualizeResponse(
            vector=test_vector,
            dimensions=1536,
            processing_time_ms=1500,
            request_id="test-123"
        )
        
        assert response.vector == test_vector
        assert response.dimensions == 1536
        assert response.processing_time_ms == 1500
        assert response.request_id == "test-123"