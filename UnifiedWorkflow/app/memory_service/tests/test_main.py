"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

# Mock the services before importing the app
import sys
from unittest.mock import patch

# Mock services
mock_services = {
    'ollama': AsyncMock(),
    'database': AsyncMock(),
    'qdrant': AsyncMock(),
    'pipeline': AsyncMock()
}

with patch('hybrid_memory_service.main._services', mock_services):
    with patch('hybrid_memory_service.main.get_services', return_value=mock_services):
        from hybrid_memory_service.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    def test_health_check_healthy(self):
        """Test health check when all services are healthy."""
        # Mock successful health checks
        mock_services['database'].health_check.return_value = {
            'healthy': True,
            'memory_count': 10,
            'vector_count': 10,
            'connection_pool': {'status': 'ok'}
        }
        mock_services['qdrant'].health_check.return_value = True
        mock_services['qdrant'].get_collection_info.return_value = {
            'name': 'test_collection',
            'vectors_count': 10
        }
        mock_services['ollama'].health_check.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert data["version"] == "1.0.0"
    
    def test_health_check_unhealthy(self):
        """Test health check when services are unhealthy."""
        # Mock failed health checks
        mock_services['database'].health_check.side_effect = Exception("DB Error")
        mock_services['qdrant'].health_check.return_value = False
        mock_services['ollama'].health_check.return_value = False
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "checks" in data


class TestMemoryAddEndpoint:
    """Test the memory addition endpoint."""
    
    def test_add_memory_success(self):
        """Test successful memory addition."""
        # Mock pipeline response
        mock_services['pipeline'].process_memory.return_value = {
            'memory_id': '123e4567-e89b-12d3-a456-426614174000',
            'processed_content': 'Processed test content',
            'summary': 'Test summary',
            'confidence_score': 0.95,
            'related_memories': [],
            'processing_time_ms': 1500,
            'status': 'success'
        }
        
        request_data = {
            'content': 'This is a test memory content',
            'content_type': 'text',
            'source': 'test'
        }
        
        response = client.post("/memory/add", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['processed_content'] == 'Processed test content'
        assert data['confidence_score'] == 0.95
        assert 'memory_id' in data
    
    def test_add_memory_empty_content(self):
        """Test memory addition with empty content."""
        request_data = {
            'content': '',
            'content_type': 'text'
        }
        
        response = client.post("/memory/add", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_add_memory_processing_error(self):
        """Test memory addition with processing error."""
        # Mock pipeline error
        mock_services['pipeline'].process_memory.return_value = {
            'status': 'error',
            'error': 'Processing failed'
        }
        
        request_data = {
            'content': 'This is a test memory content',
            'content_type': 'text'
        }
        
        response = client.post("/memory/add", json=request_data)
        
        assert response.status_code == 500


class TestMemorySearchEndpoint:
    """Test the memory search endpoint."""
    
    def test_search_memory_success(self):
        """Test successful memory search."""
        # Mock pipeline response
        mock_services['pipeline'].search_memories.return_value = {
            'results': [
                {
                    'memory_id': '123e4567-e89b-12d3-a456-426614174000',
                    'content': 'Found memory content',
                    'summary': 'Found summary',
                    'similarity_score': 0.85,
                    'content_type': 'text',
                    'created_at': '2025-01-11T12:00:00Z',
                    'updated_at': '2025-01-11T12:00:00Z',
                    'access_count': 1,
                    'consolidation_count': 1
                }
            ],
            'total_count': 1,
            'query': 'test query',
            'processing_time_ms': 800,
            'similarity_threshold_used': 0.75,
            'postgres_results': 1,
            'qdrant_results': 1,
            'hybrid_fusion_applied': True
        }
        
        response = client.get("/memory/search?query=test query&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_count'] == 1
        assert len(data['results']) == 1
        assert data['query'] == 'test query'
        assert data['hybrid_fusion_applied'] == True
    
    def test_search_memory_empty_query(self):
        """Test memory search with empty query."""
        response = client.get("/memory/search?query=")
        
        assert response.status_code == 400
    
    def test_search_memory_invalid_limit(self):
        """Test memory search with invalid limit."""
        response = client.get("/memory/search?query=test&limit=0")
        
        assert response.status_code == 400
    
    def test_search_memory_with_filters(self):
        """Test memory search with filters."""
        # Mock pipeline response
        mock_services['pipeline'].search_memories.return_value = {
            'results': [],
            'total_count': 0,
            'query': 'test query',
            'processing_time_ms': 500,
            'similarity_threshold_used': 0.8,
            'postgres_results': 0,
            'qdrant_results': 0,
            'hybrid_fusion_applied': False
        }
        
        response = client.get(
            "/memory/search?"
            "query=test&"
            "content_type_filter=text&"
            "source_filter=api&"
            "similarity_threshold=0.8&"
            "limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['similarity_threshold_used'] == 0.8


class TestMetricsEndpoint:
    """Test the metrics endpoint."""
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        # Should return prometheus metrics format
        content = response.text
        assert isinstance(content, str)