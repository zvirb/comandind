"""Integration tests for Hybrid Memory Service API endpoints.

Tests the complete API functionality including request/response handling,
database integration, and cross-service interactions.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from fastapi import status
from httpx import AsyncClient
import numpy as np

from hybrid_memory_service.main import create_app
from hybrid_memory_service.models import MemoryAddRequest, MemorySearchRequest
from hybrid_memory_service.models.memory import Memory


@pytest.mark.integration
class TestMemoryAddIntegration:
    """Integration tests for the memory add endpoint."""
    
    @pytest.mark.asyncio
    async def test_memory_add_complete_workflow(self, sample_memory_data):
        """Test complete memory addition workflow."""
        app = create_app()
        
        # Mock pipeline with realistic response
        mock_pipeline = AsyncMock()
        test_memory_id = uuid4()
        pipeline_result = {
            "memory_id": test_memory_id,
            "processed_content": "Structured content about AI and machine learning concepts",
            "summary": "Overview of AI/ML concepts with focus on neural networks",
            "confidence_score": 0.89,
            "related_memories": [str(uuid4()), str(uuid4())],
            "processing_time_ms": 1850,
            "status": "success",
            "pipeline_metrics": {
                "phase1_time_ms": 800,
                "phase2_time_ms": 650,
                "total_time_ms": 1850,
                "related_memories_found": 2,
                "reconciliation_applied": True,
                "qdrant_storage_success": True
            }
        }
        mock_pipeline.process_memory.return_value = pipeline_result
        
        # Set up app with mock services
        app.state.services = {
            "pipeline": mock_pipeline,
            "ollama": AsyncMock(),
            "database": AsyncMock(),
            "qdrant": AsyncMock()
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/memory/add", json=sample_memory_data)
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert result["memory_id"] == str(test_memory_id)
            assert result["processed_content"] == pipeline_result["processed_content"]
            assert result["summary"] == pipeline_result["summary"]
            assert result["confidence_score"] == 0.89
            assert len(result["related_memories"]) == 2
            assert result["processing_time_ms"] == 1850
            assert result["status"] == "success"
            
            # Verify pipeline was called correctly
            mock_pipeline.process_memory.assert_called_once()
            call_args = mock_pipeline.process_memory.call_args
            assert call_args.kwargs["content"] == sample_memory_data["content"]
            assert call_args.kwargs["content_type"] == sample_memory_data["content_type"]
            assert call_args.kwargs["tags"] == sample_memory_data["tags"]
            assert call_args.kwargs["metadata"] == sample_memory_data["metadata"]
    
    @pytest.mark.asyncio
    async def test_memory_add_different_content_types(self):
        """Test memory addition with different content types."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        # Test different content types
        test_cases = [
            {
                "content_type": "text",
                "content": "Plain text memory about project management techniques",
                "expected_processing": "text_based_extraction"
            },
            {
                "content_type": "note",
                "content": "Quick note: Remember to follow up on client meeting",
                "expected_processing": "note_extraction"
            },
            {
                "content_type": "document",
                "content": "Formal document content with structured information about...",
                "expected_processing": "document_analysis"
            },
            {
                "content_type": "conversation",
                "content": "Chat log: User: How do I implement authentication? Bot: Here's how...",
                "expected_processing": "conversation_parsing"
            }
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            for test_case in test_cases:
                # Configure mock response for each content type
                test_memory_id = uuid4()
                mock_pipeline.process_memory.return_value = {
                    "memory_id": test_memory_id,
                    "processed_content": f"Processed {test_case['content_type']} content",
                    "summary": f"{test_case['content_type'].title()} summary",
                    "confidence_score": 0.85,
                    "related_memories": [],
                    "processing_time_ms": 1200,
                    "status": "success"
                }
                
                request_data = {
                    "content": test_case["content"],
                    "content_type": test_case["content_type"]
                }
                
                response = await client.post("/memory/add", json=request_data)
                
                assert response.status_code == status.HTTP_200_OK
                result = response.json()
                assert result["memory_id"] == str(test_memory_id)
                assert test_case["content_type"] in result["processed_content"]
    
    @pytest.mark.asyncio
    async def test_memory_add_with_reconciliation(self):
        """Test memory addition that triggers reconciliation with existing memories."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock pipeline result showing reconciliation occurred
        test_memory_id = uuid4()
        related_memory_ids = [str(uuid4()) for _ in range(3)]
        pipeline_result = {
            "memory_id": test_memory_id,
            "processed_content": "Reconciled content integrating new and existing information",
            "summary": "Integrated summary combining multiple memory sources",
            "confidence_score": 0.93,  # High confidence after reconciliation
            "related_memories": related_memory_ids,
            "processing_time_ms": 2800,  # Longer due to reconciliation
            "status": "success",
            "pipeline_metrics": {
                "phase1_time_ms": 900,
                "phase2_time_ms": 1500,  # Significant reconciliation time
                "total_time_ms": 2800,
                "related_memories_found": 3,
                "reconciliation_applied": True,
                "qdrant_storage_success": True
            }
        }
        mock_pipeline.process_memory.return_value = pipeline_result
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "content": "Additional information about neural network architectures that builds on previous notes",
                "content_type": "text",
                "tags": ["neural-networks", "deep-learning", "architecture"],
                "metadata": {"update": True, "builds_on": "previous_notes"}
            }
            
            response = await client.post("/memory/add", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert result["confidence_score"] == 0.93  # High confidence from reconciliation
            assert len(result["related_memories"]) == 3
            assert result["processing_time_ms"] == 2800
            assert "Reconciled content" in result["processed_content"]
            assert "Integrated summary" in result["summary"]
    
    @pytest.mark.asyncio
    async def test_memory_add_error_scenarios(self):
        """Test memory addition error handling and recovery."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test pipeline error
            mock_pipeline.process_memory.return_value = {
                "status": "error",
                "error": "LLM service temporarily unavailable",
                "processing_time_ms": 500
            }
            
            request_data = {
                "content": "Content that will cause processing error"
            }
            
            response = await client.post("/memory/add", json=request_data)
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Test pipeline exception
            mock_pipeline.process_memory.side_effect = RuntimeError("Database connection failed")
            
            response = await client.post("/memory/add", json=request_data)
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Test invalid request data
            invalid_request = {
                "content": "",  # Empty content
                "content_type": "invalid_type"
            }
            
            response = await client.post("/memory/add", json=invalid_request)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_memory_add_large_content(self):
        """Test memory addition with large content payloads."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock longer processing time for large content
        test_memory_id = uuid4()
        pipeline_result = {
            "memory_id": test_memory_id,
            "processed_content": "Processed large document with extracted key sections",
            "summary": "Summary of large document focusing on main concepts",
            "confidence_score": 0.87,
            "related_memories": [],
            "processing_time_ms": 4500,  # Longer processing for large content
            "status": "success"
        }
        mock_pipeline.process_memory.return_value = pipeline_result
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        # Generate large content (10KB+)
        large_content = "This is a comprehensive document about artificial intelligence. " * 500
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            request_data = {
                "content": large_content,
                "content_type": "document",
                "source": "research_paper",
                "metadata": {"size": "large", "pages": 20}
            }
            
            response = await client.post("/memory/add", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert result["memory_id"] == str(test_memory_id)
            assert result["processing_time_ms"] == 4500
            
            # Verify large content was passed to pipeline
            call_args = mock_pipeline.process_memory.call_args
            assert len(call_args.kwargs["content"]) > 10000


@pytest.mark.integration
class TestMemorySearchIntegration:
    """Integration tests for the memory search endpoint."""
    
    @pytest.mark.asyncio
    async def test_memory_search_comprehensive_workflow(self):
        """Test complete memory search workflow with hybrid results."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock comprehensive search results
        search_results = {
            "results": [
                {
                    "memory_id": str(uuid4()),
                    "content": "Advanced machine learning techniques for neural network optimization",
                    "summary": "ML optimization strategies",
                    "content_type": "document",
                    "source": "research_paper",
                    "tags": ["machine-learning", "optimization", "neural-networks"],
                    "similarity_score": 0.91,
                    "relevance_score": 0.89,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "access_count": 5,
                    "consolidation_count": 2
                },
                {
                    "memory_id": str(uuid4()),
                    "content": "Deep learning architecture patterns and best practices",
                    "summary": "DL architecture guide",
                    "content_type": "note",
                    "source": "study_notes",
                    "tags": ["deep-learning", "architecture", "best-practices"],
                    "similarity_score": 0.87,
                    "relevance_score": 0.85,
                    "created_at": "2024-01-14T15:20:00Z",
                    "updated_at": "2024-01-14T15:20:00Z",
                    "access_count": 12,
                    "consolidation_count": 1
                },
                {
                    "memory_id": str(uuid4()),
                    "content": "Transformer models and attention mechanisms explained",
                    "summary": "Transformer architecture guide",
                    "content_type": "text",
                    "source": "tutorial",
                    "tags": ["transformers", "attention", "nlp"],
                    "similarity_score": 0.82,
                    "relevance_score": 0.80,
                    "created_at": "2024-01-13T09:15:00Z",
                    "updated_at": "2024-01-13T09:15:00Z",
                    "access_count": 8,
                    "consolidation_count": 0
                }
            ],
            "total_count": 3,
            "query": "machine learning neural networks",
            "processing_time_ms": 750,
            "similarity_threshold_used": 0.75,
            "postgres_results": 2,
            "qdrant_results": 3,
            "hybrid_fusion_applied": True
        }
        mock_pipeline.search_memories.return_value = search_results
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/memory/search?query=machine%20learning%20neural%20networks&limit=10"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert result["total_count"] == 3
            assert len(result["results"]) == 3
            assert result["query"] == "machine learning neural networks"
            assert result["processing_time_ms"] == 750
            assert result["hybrid_fusion_applied"] is True
            
            # Verify result ordering (by similarity score descending)
            scores = [r["similarity_score"] for r in result["results"]]
            assert scores == sorted(scores, reverse=True)
            
            # Verify result structure
            first_result = result["results"][0]
            required_fields = ["memory_id", "content", "summary", "similarity_score", "created_at"]
            for field in required_fields:
                assert field in first_result
    
    @pytest.mark.asyncio
    async def test_memory_search_with_comprehensive_filters(self):
        """Test memory search with all available filters."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock filtered search results
        filtered_results = {
            "results": [
                {
                    "memory_id": str(uuid4()),
                    "content": "Research paper on computer vision applications",
                    "summary": "CV applications in industry",
                    "content_type": "document",
                    "source": "research_database",
                    "tags": ["computer-vision", "applications", "research"],
                    "similarity_score": 0.88,
                    "created_at": "2024-06-15T10:00:00Z"
                }
            ],
            "total_count": 1,
            "query": "computer vision applications",
            "processing_time_ms": 600,
            "similarity_threshold_used": 0.8,
            "postgres_results": 1,
            "qdrant_results": 1,
            "hybrid_fusion_applied": True
        }
        mock_pipeline.search_memories.return_value = filtered_results
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test with comprehensive filters
            response = await client.get(
                "/memory/search?"
                "query=computer%20vision%20applications&"
                "limit=5&"
                "similarity_threshold=0.8&"
                "content_type_filter=document&"
                "source_filter=research_database&"
                "tags_filter=computer-vision,applications,research&"
                "date_from=2024-01-01&"
                "date_to=2024-12-31&"
                "include_summary_only=false"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert result["total_count"] == 1
            assert result["similarity_threshold_used"] == 0.8
            
            # Verify pipeline was called with correct filters
            mock_pipeline.search_memories.assert_called_once()
            call_args = mock_pipeline.search_memories.call_args
            
            assert call_args.kwargs["query"] == "computer vision applications"
            assert call_args.kwargs["limit"] == 5
            assert call_args.kwargs["similarity_threshold"] == 0.8
            assert call_args.kwargs["content_type_filter"] == "document"
            assert call_args.kwargs["source_filter"] == "research_database"
            assert call_args.kwargs["date_from"] == "2024-01-01"
            assert call_args.kwargs["date_to"] == "2024-12-31"
            assert call_args.kwargs["include_summary_only"] is False
    
    @pytest.mark.asyncio
    async def test_memory_search_ranking_and_relevance(self):
        """Test memory search result ranking and relevance scoring."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock results with different ranking factors
        search_results = {
            "results": [
                {
                    "memory_id": str(uuid4()),
                    "content": "Highly relevant recent memory about the exact query topic",
                    "summary": "Perfect match summary",
                    "similarity_score": 0.95,  # Highest similarity
                    "relevance_score": 0.92,   # High relevance
                    "access_count": 15,        # Frequently accessed
                    "created_at": "2024-01-20T10:00:00Z"  # Recent
                },
                {
                    "memory_id": str(uuid4()),
                    "content": "Somewhat related content with moderate similarity",
                    "summary": "Moderately relevant summary",
                    "similarity_score": 0.78,  # Moderate similarity
                    "relevance_score": 0.75,   # Moderate relevance
                    "access_count": 3,         # Less accessed
                    "created_at": "2024-01-10T08:30:00Z"
                },
                {
                    "memory_id": str(uuid4()),
                    "content": "Tangentially related older content",
                    "summary": "Loosely related summary",
                    "similarity_score": 0.68,  # Lower similarity
                    "relevance_score": 0.65,   # Lower relevance
                    "access_count": 1,         # Rarely accessed
                    "created_at": "2023-12-15T14:20:00Z"  # Older
                }
            ],
            "total_count": 3,
            "query": "specific search query",
            "processing_time_ms": 850,
            "hybrid_fusion_applied": True
        }
        mock_pipeline.search_memories.return_value = search_results
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/memory/search?query=specific%20search%20query&limit=10")
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            results = result["results"]
            
            # Verify results are properly ranked
            assert results[0]["similarity_score"] == 0.95  # Highest first
            assert results[1]["similarity_score"] == 0.78  # Medium second
            assert results[2]["similarity_score"] == 0.68  # Lowest third
            
            # Verify relevance scores are included
            for memory_result in results:
                assert "relevance_score" in memory_result
                assert "access_count" in memory_result
                assert "created_at" in memory_result
    
    @pytest.mark.asyncio
    async def test_memory_search_no_results(self):
        """Test memory search with no matching results."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        mock_pipeline.search_memories.return_value = {
            "results": [],
            "total_count": 0,
            "query": "nonexistent query terms",
            "processing_time_ms": 350,
            "similarity_threshold_used": 0.75,
            "postgres_results": 0,
            "qdrant_results": 0,
            "hybrid_fusion_applied": False
        }
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/memory/search?query=nonexistent%20query%20terms")
            
            assert response.status_code == status.HTTP_200_OK
            
            result = response.json()
            assert result["total_count"] == 0
            assert result["results"] == []
            assert result["hybrid_fusion_applied"] is False
            assert "processing_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_memory_search_error_handling(self):
        """Test memory search error handling scenarios."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test empty query
            response = await client.get("/memory/search?query=")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Query cannot be empty" in response.json()["detail"]
            
            # Test invalid limit
            response = await client.get("/memory/search?query=test&limit=0")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            
            response = await client.get("/memory/search?query=test&limit=1000")
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            
            # Test pipeline error
            mock_pipeline.search_memories.return_value = {
                "results": [],
                "total_count": 0,
                "query": "error query",
                "processing_time_ms": 100,
                "error": "Vector database temporarily unavailable"
            }
            
            response = await client.get("/memory/search?query=error%20query")
            assert response.status_code == status.HTTP_200_OK  # Still returns 200 with error in body
            
            result = response.json()
            assert "error" in result
            
            # Test pipeline exception
            mock_pipeline.search_memories.side_effect = RuntimeError("Search index corrupted")
            
            response = await client.get("/memory/search?query=exception%20query")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.integration
class TestHealthEndpointIntegration:
    """Integration tests for the health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_all_services_integration(self):
        """Test health check with all service integrations."""
        app = create_app()
        
        # Mock all services as healthy
        mock_database = AsyncMock()
        mock_database.health_check.return_value = {
            "healthy": True,
            "memory_count": 15000,
            "vector_count": 15000,
            "connection_pool": {"active": 8, "idle": 12, "total": 20}
        }
        
        mock_qdrant = AsyncMock()
        mock_qdrant.health_check.return_value = True
        mock_qdrant.get_collection_info.return_value = {
            "points_count": 15000,
            "segments_count": 5,
            "status": "green",
            "config": {"distance": "cosine", "vector_size": 1536}
        }
        
        mock_ollama = AsyncMock()
        mock_ollama.health_check.return_value = True
        
        mock_pipeline = AsyncMock()
        
        app.state.services = {
            "database": mock_database,
            "qdrant": mock_qdrant,
            "ollama": mock_ollama,
            "pipeline": mock_pipeline
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
            assert "timestamp" in health_data
            assert "version" in health_data
            
            checks = health_data["checks"]
            assert checks["database"]["healthy"] is True
            assert checks["database"]["memory_count"] == 15000
            assert checks["database"]["connection_pool"]["total"] == 20
            
            assert checks["qdrant"]["healthy"] is True
            assert checks["qdrant"]["collection_info"]["points_count"] == 15000
            assert checks["qdrant"]["collection_info"]["status"] == "green"
            
            assert checks["ollama"]["healthy"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_partial_service_failures(self):
        """Test health check with some service failures."""
        app = create_app()
        
        # Mock mixed service states
        mock_database = AsyncMock()
        mock_database.health_check.side_effect = Exception("Database connection timeout")
        
        mock_qdrant = AsyncMock()
        mock_qdrant.health_check.return_value = True
        mock_qdrant.get_collection_info.return_value = {
            "points_count": 12000,
            "status": "yellow"  # Degraded but functional
        }
        
        mock_ollama = AsyncMock()
        mock_ollama.health_check.return_value = False  # Service down
        
        app.state.services = {
            "database": mock_database,
            "qdrant": mock_qdrant,
            "ollama": mock_ollama,
            "pipeline": AsyncMock()
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == status.HTTP_200_OK
            
            health_data = response.json()
            assert health_data["status"] == "unhealthy"
            
            checks = health_data["checks"]
            assert checks["database"]["healthy"] is False
            assert "error" in checks["database"]
            
            assert checks["qdrant"]["healthy"] is True
            assert checks["qdrant"]["collection_info"]["status"] == "yellow"
            
            assert checks["ollama"]["healthy"] is False


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """Integration tests focusing on performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_memory_operations_performance(self):
        """Test performance of memory operations under realistic conditions."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock realistic processing times
        async def realistic_memory_processing(*args, **kwargs):
            # Simulate variable processing time based on content size
            content_length = len(kwargs.get("content", ""))
            base_time = 800
            size_factor = min(content_length / 1000, 3)  # Max 3x multiplier
            processing_time = base_time + (size_factor * 500)
            
            await asyncio.sleep(processing_time / 10000)  # Scale down for testing
            
            return {
                "memory_id": uuid4(),
                "processed_content": "Processed content",
                "confidence_score": 0.85,
                "processing_time_ms": processing_time,
                "status": "success"
            }
        
        async def realistic_search(*args, **kwargs):
            # Simulate search time based on query complexity
            query_length = len(kwargs.get("query", ""))
            base_time = 400
            complexity_factor = min(query_length / 50, 2)  # Max 2x multiplier
            search_time = base_time + (complexity_factor * 200)
            
            await asyncio.sleep(search_time / 10000)  # Scale down for testing
            
            return {
                "results": [
                    {
                        "memory_id": str(uuid4()),
                        "content": "Search result content",
                        "similarity_score": 0.8,
                        "created_at": "2024-01-15T10:00:00Z"
                    }
                ],
                "total_count": 1,
                "processing_time_ms": search_time
            }
        
        mock_pipeline.process_memory.side_effect = realistic_memory_processing
        mock_pipeline.search_memories.side_effect = realistic_search
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test memory addition performance
            start_time = time.time()
            
            memory_request = {
                "content": "Medium-sized content for performance testing. " * 50,  # ~2KB
                "content_type": "text"
            }
            
            response = await client.post("/memory/add", json=memory_request)
            add_time = time.time() - start_time
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            
            # Verify processing time is reasonable (should be ~1300ms based on mock)
            assert 1000 <= result["processing_time_ms"] <= 2000
            assert add_time * 1000 <= 3000  # Total request time should be under 3s
            
            # Test search performance
            start_time = time.time()
            
            search_response = await client.get("/memory/search?query=performance%20testing%20query")
            search_time = time.time() - start_time
            
            assert search_response.status_code == status.HTTP_200_OK
            search_result = search_response.json()
            
            # Verify search time is reasonable (should be ~600ms based on mock)
            assert 400 <= search_result["processing_time_ms"] <= 1000
            assert search_time * 1000 <= 2000  # Total search time should be under 2s
    
    @pytest.mark.asyncio
    async def test_concurrent_mixed_operations(self):
        """Test performance under mixed concurrent operations."""
        app = create_app()
        
        mock_pipeline = AsyncMock()
        
        # Mock consistent performance for concurrent testing
        async def fast_processing(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms processing
            return {
                "memory_id": uuid4(),
                "processed_content": "Concurrent processed content",
                "confidence_score": 0.8,
                "processing_time_ms": 100,
                "status": "success"
            }
        
        async def fast_search(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms search
            return {
                "results": [{"memory_id": str(uuid4()), "content": "Result", "similarity_score": 0.8}],
                "total_count": 1,
                "processing_time_ms": 50
            }
        
        mock_pipeline.process_memory.side_effect = fast_processing
        mock_pipeline.search_memories.side_effect = fast_search
        
        app.state.services = {"pipeline": mock_pipeline, "ollama": AsyncMock(), "database": AsyncMock(), "qdrant": AsyncMock()}
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create mixed concurrent requests
            tasks = []
            
            # Add memory requests
            for i in range(10):
                memory_request = {
                    "content": f"Concurrent memory content {i}",
                    "content_type": "text"
                }
                task = client.post("/memory/add", json=memory_request)
                tasks.append(("add", task))
            
            # Add search requests
            for i in range(15):
                search_task = client.get(f"/memory/search?query=concurrent%20search%20{i}")
                tasks.append(("search", search_task))
            
            # Execute all concurrently
            start_time = time.time()
            results = await asyncio.gather(*[task for _, task in tasks])
            total_time = time.time() - start_time
            
            # Verify all requests succeeded
            for result in results:
                assert result.status_code == status.HTTP_200_OK
            
            # Calculate throughput
            total_requests = len(tasks)
            throughput = total_requests / total_time
            
            # Should handle reasonable concurrent load
            # With 100ms add and 50ms search, perfect concurrency would be very high
            # Allow for overhead, expect at least 50 req/sec
            assert throughput >= 50, f"Throughput too low: {throughput:.2f} req/sec"
            
            # Verify service was called for each request
            assert mock_pipeline.process_memory.call_count == 10  # Memory adds
            assert mock_pipeline.search_memories.call_count == 15  # Searches