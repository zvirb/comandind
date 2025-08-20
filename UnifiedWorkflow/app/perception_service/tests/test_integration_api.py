"""Integration tests for Perception Service API endpoints.

Tests the complete API functionality including request/response handling,
error scenarios, and integration with Ollama service.
"""

import asyncio
import base64
import json
import time
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import status
from httpx import AsyncClient
import numpy as np

from perception_service.main import create_app
from perception_service.models import ConceptualizeRequest


@pytest.mark.integration
class TestConceptualizeIntegration:
    """Integration tests for the conceptualize endpoint."""
    
    @pytest.mark.asyncio
    async def test_conceptualize_end_to_end_success(self, create_test_image):
        """Test complete conceptualize workflow from request to response."""
        app = create_app()
        
        # Create test image
        test_image = create_test_image(256, 256, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Mock Ollama service with realistic response
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        mock_ollama_service.generate_concept_vector.return_value = np.random.rand(1536).tolist()
        
        app.state.ollama_service = mock_ollama_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "image_data": image_b64,
                "format": "jpeg",
                "prompt": "Describe the objects and concepts in this image"
            }
            
            response = await client.post("/conceptualize", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert "vector" in result
            assert "dimensions" in result
            assert "processing_time_ms" in result
            assert "request_id" in result
            
            assert len(result["vector"]) == 1536
            assert result["dimensions"] == 1536
            assert isinstance(result["processing_time_ms"], (int, float))
            assert result["processing_time_ms"] > 0
            
            # Verify service was called correctly
            mock_ollama_service.generate_concept_vector.assert_called_once()
            call_args = mock_ollama_service.generate_concept_vector.call_args
            assert call_args.kwargs["image_data"] == image_b64
            assert call_args.kwargs["image_format"] == "jpeg"
    
    @pytest.mark.asyncio
    async def test_conceptualize_different_image_formats(self, create_test_image):
        """Test conceptualize with different supported image formats."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        app.state.ollama_service = mock_ollama_service
        
        # Test different formats
        formats_to_test = [
            ("JPEG", "jpeg"),
            ("PNG", "png"),
            ("WEBP", "webp")
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for pil_format, api_format in formats_to_test:
                # Generate different vectors for each format
                test_vector = np.random.rand(1536).tolist()
                mock_ollama_service.generate_concept_vector.return_value = test_vector
                
                test_image = create_test_image(200, 200, pil_format)
                image_b64 = base64.b64encode(test_image).decode("utf-8")
                
                request_data = {
                    "image_data": image_b64,
                    "format": api_format,
                    "prompt": f"Analyze this {api_format} image"
                }
                
                response = await client.post("/conceptualize", json=request_data)
                
                assert response.status_code == status.HTTP_200_OK, f"Failed for format {api_format}"
                
                result = response.json()
                assert result["vector"] == test_vector
                assert result["dimensions"] == 1536
    
    @pytest.mark.asyncio
    async def test_conceptualize_various_image_sizes(self, create_test_image):
        """Test conceptualize with various image sizes."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        app.state.ollama_service = mock_ollama_service
        
        # Test different image sizes
        test_sizes = [
            (64, 64),     # Small
            (256, 256),   # Medium
            (512, 512),   # Large
            (800, 600),   # Non-square
            (1024, 768)   # High resolution
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for width, height in test_sizes:
                # Generate consistent vector for each size
                test_vector = [i / 1536.0 for i in range(1536)]
                mock_ollama_service.generate_concept_vector.return_value = test_vector
                
                test_image = create_test_image(width, height, "JPEG")
                image_b64 = base64.b64encode(test_image).decode("utf-8")
                
                request_data = {
                    "image_data": image_b64,
                    "format": "jpeg",
                    "prompt": f"Analyze this {width}x{height} image"
                }
                
                response = await client.post("/conceptualize", json=request_data)
                
                assert response.status_code == status.HTTP_200_OK, f"Failed for size {width}x{height}"
                
                result = response.json()
                assert len(result["vector"]) == 1536
                assert result["dimensions"] == 1536
    
    @pytest.mark.asyncio
    async def test_conceptualize_custom_prompts(self, create_test_image):
        """Test conceptualize with various custom prompts."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        mock_ollama_service.generate_concept_vector.return_value = np.random.rand(1536).tolist()
        
        app.state.ollama_service = mock_ollama_service
        
        test_image = create_test_image(300, 300, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Test various prompts
        test_prompts = [
            "What objects are visible in this image?",
            "Describe the colors and composition",
            "Identify any text or symbols present",
            "What is the mood or atmosphere of this scene?",
            "Focus on geometric shapes and patterns"
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for prompt in test_prompts:
                request_data = {
                    "image_data": image_b64,
                    "format": "jpeg",
                    "prompt": prompt
                }
                
                response = await client.post("/conceptualize", json=request_data)
                
                assert response.status_code == status.HTTP_200_OK
                
                # Verify prompt was passed to service
                call_args = mock_ollama_service.generate_concept_vector.call_args
                assert call_args.kwargs["prompt"] == prompt
    
    @pytest.mark.asyncio
    async def test_conceptualize_error_propagation(self, create_test_image):
        """Test that service errors are properly propagated through API."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        app.state.ollama_service = mock_ollama_service
        
        test_image = create_test_image(200, 200, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        # Test different types of service errors
        error_scenarios = [
            (ValueError("Invalid image data"), status.HTTP_400_BAD_REQUEST),
            (RuntimeError("Ollama service unavailable"), status.HTTP_500_INTERNAL_SERVER_ERROR),
            (TimeoutError("Request timeout"), status.HTTP_500_INTERNAL_SERVER_ERROR)
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for error, expected_status in error_scenarios:
                mock_ollama_service.generate_concept_vector.side_effect = error
                
                request_data = {
                    "image_data": image_b64,
                    "format": "jpeg"
                }
                
                response = await client.post("/conceptualize", json=request_data)
                
                assert response.status_code == expected_status
                
                if expected_status == status.HTTP_400_BAD_REQUEST:
                    # Client errors should include error details
                    assert "Invalid image data" in response.json()["detail"]
                else:
                    # Server errors should be generic for security
                    assert response.json()["detail"] == "Internal server error"
    
    @pytest.mark.asyncio
    async def test_conceptualize_request_validation(self):
        """Test request validation for conceptualize endpoint."""
        app = create_app()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test missing required fields
            invalid_requests = [
                {},  # Empty request
                {"format": "jpeg"},  # Missing image_data
                {"image_data": "base64data"},  # Missing format
                {"image_data": "invalid_base64", "format": "jpeg"},  # Invalid base64
                {"image_data": "dGVzdA==", "format": "unsupported"},  # Unsupported format
            ]
            
            for invalid_request in invalid_requests:
                response = await client.post("/conceptualize", json=invalid_request)
                
                assert response.status_code in [
                    status.HTTP_400_BAD_REQUEST, 
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ]
    
    @pytest.mark.asyncio
    async def test_conceptualize_large_payload(self, create_test_image):
        """Test conceptualize with large image payload."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        mock_ollama_service.generate_concept_vector.return_value = np.random.rand(1536).tolist()
        
        app.state.ollama_service = mock_ollama_service
        
        # Create large image (2MB+)
        large_image = create_test_image(2048, 2048, "JPEG")
        image_b64 = base64.b64encode(large_image).decode("utf-8")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "image_data": image_b64,
                "format": "jpeg",
                "prompt": "Analyze this high-resolution image"
            }
            
            response = await client.post("/conceptualize", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert len(result["vector"]) == 1536
            
            # Processing time might be higher for large images
            assert result["processing_time_ms"] > 0


@pytest.mark.integration
class TestHealthEndpointIntegration:
    """Integration tests for the health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_with_real_service_states(self):
        """Test health check with various service state combinations."""
        app = create_app()
        
        # Test scenario 1: All services healthy
        mock_ollama_healthy = AsyncMock()
        mock_ollama_healthy.health_check.return_value = True
        mock_ollama_healthy.is_model_ready.return_value = True
        
        app.state.ollama_service = mock_ollama_healthy
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert health_data["checks"]["ollama_service"]["healthy"] is True
            assert health_data["checks"]["llava_model"]["ready"] is True
            assert "latency_ms" in health_data["checks"]["ollama_service"]
        
        # Test scenario 2: Service healthy but model not ready
        mock_ollama_model_not_ready = AsyncMock()
        mock_ollama_model_not_ready.health_check.return_value = True
        mock_ollama_model_not_ready.is_model_ready.return_value = False
        
        app.state.ollama_service = mock_ollama_model_not_ready
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "unhealthy"
            assert health_data["checks"]["ollama_service"]["healthy"] is True
            assert health_data["checks"]["llava_model"]["ready"] is False
        
        # Test scenario 3: Service unhealthy
        mock_ollama_unhealthy = AsyncMock()
        mock_ollama_unhealthy.health_check.return_value = False
        mock_ollama_unhealthy.is_model_ready.return_value = True
        
        app.state.ollama_service = mock_ollama_unhealthy
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "unhealthy"
            assert health_data["checks"]["ollama_service"]["healthy"] is False
    
    @pytest.mark.asyncio
    async def test_health_check_latency_measurement(self):
        """Test health check latency measurement accuracy."""
        app = create_app()
        
        # Mock service with controlled delay
        async def slow_health_check():
            await asyncio.sleep(0.2)  # 200ms delay
            return True
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.side_effect = slow_health_check
        mock_ollama_service.is_model_ready.return_value = True
        
        app.state.ollama_service = mock_ollama_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/health")
            end_time = time.time()
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            reported_latency = health_data["checks"]["ollama_service"]["latency_ms"]
            actual_latency = (end_time - start_time) * 1000
            
            # Reported latency should be close to actual (within 50ms tolerance)
            assert abs(reported_latency - actual_latency) < 50
            assert reported_latency >= 200  # Should include our 200ms delay
    
    @pytest.mark.asyncio
    async def test_health_check_error_handling(self):
        """Test health check error handling and recovery."""
        app = create_app()
        
        # Mock service that throws exceptions
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.side_effect = Exception("Connection refused")
        mock_ollama_service.is_model_ready.side_effect = Exception("Model check failed")
        
        app.state.ollama_service = mock_ollama_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "unhealthy"
            assert "error" in health_data["checks"]
            assert "Connection refused" in str(health_data["checks"]["error"])


@pytest.mark.integration
class TestConcurrentRequestHandling:
    """Integration tests for concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_conceptualize_requests(self, create_test_image):
        """Test handling multiple simultaneous conceptualize requests."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        # Mock different responses for concurrent requests
        test_vectors = [np.random.rand(1536).tolist() for _ in range(10)]
        mock_ollama_service.generate_concept_vector.side_effect = test_vectors
        
        app.state.ollama_service = mock_ollama_service
        
        # Create test images
        test_images = [create_test_image(200 + i * 20, 200 + i * 20, "JPEG") for i in range(10)]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Prepare concurrent requests
            tasks = []
            for i, test_image in enumerate(test_images):
                image_b64 = base64.b64encode(test_image).decode("utf-8")
                request_data = {
                    "image_data": image_b64,
                    "format": "jpeg",
                    "prompt": f"Concurrent request {i}"
                }
                task = client.post("/conceptualize", json=request_data)
                tasks.append(task)
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*tasks)
            
            # Verify all requests succeeded
            for i, response in enumerate(responses):
                assert response.status_code == status.HTTP_200_OK
                result = response.json()
                assert len(result["vector"]) == 1536
                assert result["vector"] == test_vectors[i]
            
            # Verify service was called for each request
            assert mock_ollama_service.generate_concept_vector.call_count == 10
    
    @pytest.mark.asyncio
    async def test_mixed_concurrent_requests(self, create_test_image):
        """Test handling mixed concurrent requests (health checks and conceptualize)."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        mock_ollama_service.generate_concept_vector.return_value = np.random.rand(1536).tolist()
        
        app.state.ollama_service = mock_ollama_service
        
        test_image = create_test_image(256, 256, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Mix of health checks and conceptualize requests
            tasks = []
            
            # Add health check requests
            for _ in range(5):
                tasks.append(client.get("/health"))
            
            # Add conceptualize requests
            for i in range(5):
                request_data = {
                    "image_data": image_b64,
                    "format": "jpeg",
                    "prompt": f"Mixed request {i}"
                }
                tasks.append(client.post("/conceptualize", json=request_data))
            
            # Execute all concurrently
            responses = await asyncio.gather(*tasks)
            
            # Verify all requests succeeded
            for response in responses:
                assert response.status_code == status.HTTP_200_OK
            
            # First 5 should be health checks
            for i in range(5):
                health_data = responses[i].json()
                assert health_data["status"] == "healthy"
            
            # Next 5 should be conceptualize responses
            for i in range(5, 10):
                concept_data = responses[i].json()
                assert len(concept_data["vector"]) == 1536


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """Integration tests focusing on performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_response_time_under_load(self, create_test_image, assert_response_time):
        """Test response times under moderate load."""
        app = create_app()
        
        # Mock fast service responses
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        async def fast_vector_generation(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate 100ms processing
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = fast_vector_generation
        app.state.ollama_service = mock_ollama_service
        
        test_image = create_test_image(512, 512, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test individual request performance
            request_data = {
                "image_data": image_b64,
                "format": "jpeg",
                "prompt": "Performance test"
            }
            
            start_time = time.time()
            response = await client.post("/conceptualize", json=request_data)
            end_time = time.time()
            
            assert response.status_code == status.HTTP_200_OK
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Should meet P95 target of <2000ms for moderate-sized images
            assert_response_time(response_time_ms, 2000)
            
            result = response.json()
            assert result["processing_time_ms"] >= 100  # Should include our mock delay
    
    @pytest.mark.asyncio
    async def test_throughput_under_concurrent_load(self, create_test_image):
        """Test throughput under concurrent load."""
        app = create_app()
        
        mock_ollama_service = AsyncMock()
        mock_ollama_service.health_check.return_value = True
        mock_ollama_service.is_model_ready.return_value = True
        
        # Mock consistent processing time
        async def consistent_processing(*args, **kwargs):
            await asyncio.sleep(0.5)  # 500ms per request
            return np.random.rand(1536).tolist()
        
        mock_ollama_service.generate_concept_vector.side_effect = consistent_processing
        app.state.ollama_service = mock_ollama_service
        
        test_image = create_test_image(256, 256, "JPEG")
        image_b64 = base64.b64encode(test_image).decode("utf-8")
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test concurrent throughput
            concurrent_requests = 20
            
            request_data = {
                "image_data": image_b64,
                "format": "jpeg",
                "prompt": "Throughput test"
            }
            
            # Execute concurrent requests
            start_time = time.time()
            tasks = [
                client.post("/conceptualize", json=request_data)
                for _ in range(concurrent_requests)
            ]
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Verify all succeeded
            for response in responses:
                assert response.status_code == status.HTTP_200_OK
            
            total_time = end_time - start_time
            throughput = concurrent_requests / total_time
            
            # Should handle reasonable concurrent load
            # With 500ms per request, perfect concurrency would be 40 req/sec
            # Allow for overhead, expect at least 20 req/sec
            assert throughput >= 20, f"Throughput too low: {throughput:.2f} req/sec"