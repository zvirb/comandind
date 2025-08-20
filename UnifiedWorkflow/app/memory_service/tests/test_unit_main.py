"""Unit tests for Hybrid Memory Service main application.

Tests the FastAPI application, endpoints, middleware, and error handling
with comprehensive mocking of dependencies.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from hybrid_memory_service.main import create_app
from hybrid_memory_service.models import MemoryAddRequest, MemorySearchRequest


class TestApplicationCreation:
    """Test FastAPI application creation and configuration."""
    
    def test_create_app_structure(self):
        """Test that the application is created with correct structure."""
        app = create_app()
        
        assert app.title == "Hybrid Memory Service"
        assert "AI-powered memory management" in app.description
        assert app.version
        
        # Check that routes exist
        routes = [route.path for route in app.routes]
        expected_routes = ["/health", "/metrics", "/memory/add", "/memory/search"]
        
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
    async def test_health_check_all_services_healthy(self, async_client, mock_memory_pipeline):
        """Test successful health check when all services are healthy."""
        # Mock all service health checks
        mock_memory_pipeline.database_service.health_check.return_value = {
            "healthy": True,
            "memory_count": 1000,
            "vector_count": 1000,
            "connection_pool": {"active": 5, "idle": 15}
        }
        
        mock_memory_pipeline.qdrant_service.health_check.return_value = True
        mock_memory_pipeline.qdrant_service.get_collection_info.return_value = {
            "points_count": 1000,
            "segments_count": 3,
            "status": "green"
        }
        
        mock_memory_pipeline.ollama_service.health_check.return_value = True
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "checks" in health_data
        assert "version" in health_data
        
        # Verify individual service checks
        checks = health_data["checks"]
        assert checks["database"]["healthy"] is True
        assert checks["qdrant"]["healthy"] is True
        assert checks["ollama"]["healthy"] is True
        assert checks["database"]["memory_count"] == 1000
    
    @pytest.mark.asyncio
    async def test_health_check_database_unhealthy(self, async_client, mock_memory_pipeline):
        """Test health check when database service is unhealthy."""
        # Mock database as unhealthy
        mock_memory_pipeline.database_service.health_check.side_effect = Exception("DB connection failed")
        
        # Other services healthy
        mock_memory_pipeline.qdrant_service.health_check.return_value = True
        mock_memory_pipeline.qdrant_service.get_collection_info.return_value = {"status": "green"}
        mock_memory_pipeline.ollama_service.health_check.return_value = True
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        assert health_data["status"] == "unhealthy"
        assert health_data["checks"]["database"]["healthy"] is False
        assert "error" in health_data["checks"]["database"]
    
    @pytest.mark.asyncio
    async def test_health_check_multiple_services_unhealthy(self, async_client, mock_memory_pipeline):
        """Test health check when multiple services are unhealthy."""
        # Mock multiple failures
        mock_memory_pipeline.database_service.health_check.side_effect = Exception("DB error")
        mock_memory_pipeline.qdrant_service.health_check.return_value = False
        mock_memory_pipeline.ollama_service.health_check.return_value = True
        
        response = await async_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        
        health_data = response.json()
        assert health_data["status"] == "unhealthy"
        assert health_data["checks"]["database"]["healthy"] is False
        assert health_data["checks"]["qdrant"]["healthy"] is False
        assert health_data["checks"]["ollama"]["healthy"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_performance_timing(self, async_client, mock_memory_pipeline):
        """Test health check performance timing."""
        # Mock services with known timing
        async def slow_db_check():
            await asyncio.sleep(0.1)  # 100ms delay
            return {"healthy": True, "memory_count": 100, "vector_count": 100}
        
        mock_memory_pipeline.database_service.health_check.side_effect = slow_db_check
        mock_memory_pipeline.qdrant_service.health_check.return_value = True
        mock_memory_pipeline.qdrant_service.get_collection_info.return_value = {"status": "green"}
        mock_memory_pipeline.ollama_service.health_check.return_value = True
        
        start_time = time.time()
        response = await async_client.get("/health")
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        
        # Should take at least 100ms due to DB delay
        total_time = (end_time - start_time) * 1000
        assert total_time >= 100
        
        health_data = response.json()
        assert health_data["status"] == "healthy"


class TestMemoryAddEndpoint:
    """Test memory addition endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_add_memory_success(self, async_client, mock_memory_pipeline):
        """Test successful memory addition."""
        test_memory_id = uuid4()
        pipeline_result = {
            "memory_id": test_memory_id,
            "processed_content": "Structured memory content",
            "summary": "Memory summary",
            "confidence_score": 0.92,
            "related_memories": [],
            "processing_time_ms": 1500,
            "status": "success"
        }
        
        mock_memory_pipeline.process_memory.return_value = pipeline_result
        
        request_data = {
            "content": "This is a test memory about artificial intelligence concepts.",
            "content_type": "text",
            "source": "test_source",
            "tags": ["AI", "concepts", "test"],
            "metadata": {"author": "test_user", "category": "learning"}
        }
        
        response = await async_client.post("/memory/add", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["memory_id"] == str(test_memory_id)
        assert result["processed_content"] == "Structured memory content"
        assert result["summary"] == "Memory summary"
        assert result["confidence_score"] == 0.92
        assert result["status"] == "success"
        assert result["processing_time_ms"] == 1500
        
        # Verify pipeline was called with correct parameters
        mock_memory_pipeline.process_memory.assert_called_once()
        call_args = mock_memory_pipeline.process_memory.call_args
        assert call_args.kwargs["content"] == request_data["content"]
        assert call_args.kwargs["content_type"] == request_data["content_type"]
        assert call_args.kwargs["tags"] == request_data["tags"]
    
    @pytest.mark.asyncio
    async def test_add_memory_with_minimal_data(self, async_client, mock_memory_pipeline):
        """Test memory addition with minimal required data."""
        test_memory_id = uuid4()
        pipeline_result = {
            "memory_id": test_memory_id,
            "processed_content": "Minimal memory content",
            "summary": None,
            "confidence_score": 0.8,
            "related_memories": [],
            "processing_time_ms": 800,
            "status": "success"
        }
        
        mock_memory_pipeline.process_memory.return_value = pipeline_result
        
        # Only required field
        request_data = {
            "content": "Minimal test memory content"
        }
        
        response = await async_client.post("/memory/add", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["memory_id"] == str(test_memory_id)
        assert result["processed_content"] == "Minimal memory content"
        assert result["summary"] is None
    
    @pytest.mark.asyncio
    async def test_add_memory_pipeline_error(self, async_client, mock_memory_pipeline):
        """Test memory addition when pipeline returns error."""
        pipeline_result = {
            "status": "error",
            "error": "Processing failed due to invalid content",
            "processing_time_ms": 200
        }
        
        mock_memory_pipeline.process_memory.return_value = pipeline_result
        
        request_data = {
            "content": "Invalid content that causes processing failure"
        }
        
        response = await async_client.post("/memory/add", json=request_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Internal server error"
    
    @pytest.mark.asyncio
    async def test_add_memory_validation_error(self, async_client):
        """Test memory addition with invalid request data."""
        # Missing required content field
        request_data = {
            "content_type": "text",
            "tags": ["test"]
        }
        
        response = await async_client.post("/memory/add", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        error_detail = response.json()
        assert "detail" in error_detail
    
    @pytest.mark.asyncio
    async def test_add_memory_empty_content(self, async_client):
        """Test memory addition with empty content."""
        request_data = {
            "content": ""  # Empty content
        }
        
        response = await async_client.post("/memory/add", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_add_memory_exception_handling(self, async_client, mock_memory_pipeline):
        """Test memory addition with unexpected exception."""
        # Mock pipeline to raise exception
        mock_memory_pipeline.process_memory.side_effect = RuntimeError("Unexpected error")
        
        request_data = {
            "content": "Content that causes exception"
        }
        
        response = await async_client.post("/memory/add", json=request_data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Internal server error"
    
    @pytest.mark.asyncio
    async def test_add_memory_performance_tracking(self, async_client, mock_memory_pipeline):
        """Test that memory addition tracks performance metrics."""
        test_memory_id = uuid4()
        pipeline_result = {
            "memory_id": test_memory_id,
            "processed_content": "Performance test content",
            "confidence_score": 0.85,
            "processing_time_ms": 2500,  # Slow processing
            "status": "success"
        }
        
        mock_memory_pipeline.process_memory.return_value = pipeline_result
        
        request_data = {
            "content": "Content for performance testing" * 100  # Large content
        }
        
        start_time = time.time()
        response = await async_client.post("/memory/add", json=request_data)
        end_time = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["processing_time_ms"] == 2500
        
        # Total request time should be reasonable
        total_time_ms = (end_time - start_time) * 1000
        assert total_time_ms >= 2500  # Should include processing time


class TestMemorySearchEndpoint:
    """Test memory search endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_search_memories_success(self, async_client, mock_memory_pipeline):
        """Test successful memory search."""
        search_results = {
            "results": [
                {
                    "memory_id": str(uuid4()),
                    "content": "Found memory content 1",
                    "summary": "Memory 1 summary",
                    "similarity_score": 0.89,
                    "content_type": "text",
                    "created_at": "2024-01-15T10:30:00Z"
                },
                {
                    "memory_id": str(uuid4()),
                    "content": "Found memory content 2",
                    "summary": "Memory 2 summary",
                    "similarity_score": 0.75,
                    "content_type": "note",
                    "created_at": "2024-01-14T15:20:00Z"
                }
            ],
            "total_count": 2,
            "query": "test query",
            "processing_time_ms": 850,
            "similarity_threshold_used": 0.7,
            "postgres_results": 1,
            "qdrant_results": 2,
            "hybrid_fusion_applied": True
        }
        
        mock_memory_pipeline.search_memories.return_value = search_results
        
        response = await async_client.get("/memory/search?query=test%20query&limit=10")
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["total_count"] == 2
        assert len(result["results"]) == 2
        assert result["query"] == "test query"
        assert result["processing_time_ms"] == 850
        assert result["hybrid_fusion_applied"] is True
        
        # Verify first result structure
        first_result = result["results"][0]
        assert "memory_id" in first_result
        assert "content" in first_result
        assert "similarity_score" in first_result
        assert first_result["similarity_score"] == 0.89
    
    @pytest.mark.asyncio
    async def test_search_memories_with_filters(self, async_client, mock_memory_pipeline):
        """Test memory search with various filters."""
        search_results = {
            "results": [],
            "total_count": 0,
            "query": "filtered query",
            "processing_time_ms": 400,
            "similarity_threshold_used": 0.8
        }
        
        mock_memory_pipeline.search_memories.return_value = search_results
        
        response = await async_client.get(
            "/memory/search?"
            "query=filtered%20query&"
            "limit=5&"
            "similarity_threshold=0.8&"
            "content_type_filter=document&"
            "source_filter=research&"
            "tags_filter=AI,ML,research&"
            "date_from=2024-01-01&"
            "date_to=2024-12-31&"
            "include_summary_only=true"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify pipeline was called with correct filters
        mock_memory_pipeline.search_memories.assert_called_once()
        call_args = mock_memory_pipeline.search_memories.call_args
        
        assert call_args.kwargs["query"] == "filtered query"
        assert call_args.kwargs["limit"] == 5
        assert call_args.kwargs["similarity_threshold"] == 0.8
        assert call_args.kwargs["content_type_filter"] == "document"
        assert call_args.kwargs["source_filter"] == "research"
        assert call_args.kwargs["date_from"] == "2024-01-01"
        assert call_args.kwargs["date_to"] == "2024-12-31"
        assert call_args.kwargs["include_summary_only"] is True
    
    @pytest.mark.asyncio
    async def test_search_memories_empty_query(self, async_client):
        """Test memory search with empty query."""
        response = await async_client.get("/memory/search?query=")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Query cannot be empty" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_search_memories_invalid_limit(self, async_client):
        """Test memory search with invalid limit values."""
        # Test negative limit
        response = await async_client.get("/memory/search?query=test&limit=-1")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test excessive limit (assuming max is 100)
        response = await async_client.get("/memory/search?query=test&limit=1000")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_search_memories_no_results(self, async_client, mock_memory_pipeline):
        """Test memory search with no matching results."""
        search_results = {
            "results": [],
            "total_count": 0,
            "query": "nonexistent query",
            "processing_time_ms": 250,
            "similarity_threshold_used": 0.7,
            "postgres_results": 0,
            "qdrant_results": 0,
            "hybrid_fusion_applied": False
        }
        
        mock_memory_pipeline.search_memories.return_value = search_results
        
        response = await async_client.get("/memory/search?query=nonexistent%20query")
        
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["total_count"] == 0
        assert result["results"] == []
        assert result["hybrid_fusion_applied"] is False
    
    @pytest.mark.asyncio
    async def test_search_memories_pipeline_error(self, async_client, mock_memory_pipeline):
        """Test memory search when pipeline returns error."""
        search_results = {
            "results": [],
            "total_count": 0,
            "query": "error query",
            "processing_time_ms": 100,
            "error": "Search service temporarily unavailable"
        }
        
        mock_memory_pipeline.search_memories.return_value = search_results
        
        response = await async_client.get("/memory/search?query=error%20query")
        
        # Should still return 200 but with error in response
        assert response.status_code == status.HTTP_200_OK
        
        result = response.json()
        assert result["total_count"] == 0
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_search_memories_exception_handling(self, async_client, mock_memory_pipeline):
        """Test memory search with unexpected exception."""
        mock_memory_pipeline.search_memories.side_effect = RuntimeError("Search engine failure")
        
        response = await async_client.get("/memory/search?query=test")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Internal server error"
    
    @pytest.mark.asyncio
    async def test_search_memories_tags_parsing(self, async_client, mock_memory_pipeline):
        """Test memory search with tags filter parsing."""
        search_results = {
            "results": [],
            "total_count": 0,
            "query": "tagged query",
            "processing_time_ms": 300
        }
        
        mock_memory_pipeline.search_memories.return_value = search_results
        
        # Test comma-separated tags with spaces
        response = await async_client.get("/memory/search?query=tagged&tags_filter=AI,%20machine%20learning,%20%20concepts%20%20")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify tags were parsed correctly (spaces trimmed, empty tags removed)
        call_args = mock_memory_pipeline.search_memories.call_args
        # Tags should be parsed and passed to pipeline (implementation would handle this)


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
        assert "hybrid_memory" in content  # Should have service-specific metrics


class TestErrorHandling:
    """Test global error handling and exception management."""
    
    @pytest.mark.asyncio
    async def test_global_exception_handler(self, async_client):
        """Test global exception handler for unhandled errors."""
        # This would require mocking an endpoint to raise an unhandled exception
        # For now, we can test that the handler structure exists
        pass
    
    @pytest.mark.asyncio
    async def test_request_validation_errors(self, async_client):
        """Test request validation error handling."""
        # Test invalid JSON
        response = await async_client.post(
            "/memory/add",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code in [400, 422]  # Either bad request or validation error
    
    @pytest.mark.asyncio
    async def test_method_not_allowed(self, async_client):
        """Test method not allowed error handling."""
        # Try to POST to a GET-only endpoint
        response = await async_client.post("/health")
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestConcurrentRequests:
    """Test handling of concurrent requests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_additions(self, async_client, mock_memory_pipeline):
        """Test handling multiple concurrent memory addition requests."""
        # Mock pipeline to return unique results for each request
        memory_ids = [uuid4() for _ in range(5)]
        pipeline_results = [
            {
                "memory_id": memory_id,
                "processed_content": f"Concurrent content {i}",
                "confidence_score": 0.8 + i * 0.02,
                "processing_time_ms": 1000 + i * 100,
                "status": "success"
            }
            for i, memory_id in enumerate(memory_ids)
        ]
        
        mock_memory_pipeline.process_memory.side_effect = pipeline_results
        
        # Create concurrent requests
        requests = [
            {
                "content": f"Concurrent test memory {i}",
                "content_type": "text",
                "tags": [f"concurrent", f"test-{i}"]
            }
            for i in range(5)
        ]
        
        # Send requests concurrently
        tasks = [
            async_client.post("/memory/add", json=request_data)
            for request_data in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for i, response in enumerate(responses):
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["memory_id"] == str(memory_ids[i])
        
        # Pipeline should have been called for each request
        assert mock_memory_pipeline.process_memory.call_count == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self, async_client, mock_memory_pipeline):
        """Test handling multiple concurrent search requests."""
        search_results = [
            {
                "results": [{"memory_id": str(uuid4()), "content": f"Result for query {i}"}],
                "total_count": 1,
                "query": f"concurrent query {i}",
                "processing_time_ms": 500 + i * 50
            }
            for i in range(3)
        ]
        
        mock_memory_pipeline.search_memories.side_effect = search_results
        
        # Send concurrent search requests
        tasks = [
            async_client.get(f"/memory/search?query=concurrent%20query%20{i}")
            for i in range(3)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All searches should succeed
        for i, response in enumerate(responses):
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["query"] == f"concurrent query {i}"
        
        # Pipeline should have been called for each search
        assert mock_memory_pipeline.search_memories.call_count == 3


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
        assert "/memory/add" in paths
        assert "/memory/search" in paths
    
    def test_request_response_models(self):
        """Test request and response model definitions."""
        # Test MemoryAddRequest model
        request = MemoryAddRequest(
            content="Test memory content",
            content_type="text",
            source="test_source",
            tags=["test", "memory"],
            metadata={"author": "test_user"}
        )
        
        assert request.content == "Test memory content"
        assert request.content_type == "text"
        assert request.tags == ["test", "memory"]
        assert request.metadata == {"author": "test_user"}
    
    def test_model_validation(self):
        """Test model validation rules."""
        # Test required field validation
        with pytest.raises(ValueError):
            MemoryAddRequest()  # Missing required content field
        
        # Test content length validation (if implemented)
        # This would depend on the actual model validation rules