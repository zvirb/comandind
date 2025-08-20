"""Unit tests for Hybrid Memory Service MemoryPipeline.

Tests the core two-phase memory processing pipeline with comprehensive
mocking of LLM, database, and vector database interactions.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
import pytest
import numpy as np

from hybrid_memory_service.services.memory_pipeline import MemoryPipeline
from hybrid_memory_service.models.memory import Memory


class TestMemoryPipelineInit:
    """Test MemoryPipeline initialization and configuration."""
    
    def test_pipeline_initialization(self, mock_ollama_service, mock_database_service, mock_qdrant_service):
        """Test proper pipeline initialization with default settings."""
        pipeline = MemoryPipeline(
            ollama_service=mock_ollama_service,
            database_service=mock_database_service,
            qdrant_service=mock_qdrant_service,
            extraction_prompt="Extract key information",
            reconciliation_prompt="Reconcile with existing memories"
        )
        
        assert pipeline.ollama == mock_ollama_service
        assert pipeline.database == mock_database_service
        assert pipeline.qdrant == mock_qdrant_service
        assert pipeline.similarity_threshold == 0.75
        assert pipeline.max_related_memories == 5
    
    def test_pipeline_initialization_with_custom_params(
        self, mock_ollama_service, mock_database_service, mock_qdrant_service
    ):
        """Test pipeline initialization with custom parameters."""
        pipeline = MemoryPipeline(
            ollama_service=mock_ollama_service,
            database_service=mock_database_service,
            qdrant_service=mock_qdrant_service,
            extraction_prompt="Custom extraction",
            reconciliation_prompt="Custom reconciliation",
            similarity_threshold=0.85,
            max_related_memories=10
        )
        
        assert pipeline.similarity_threshold == 0.85
        assert pipeline.max_related_memories == 10
        assert pipeline.extraction_prompt == "Custom extraction"
        assert pipeline.reconciliation_prompt == "Custom reconciliation"


class TestMemoryProcessing:
    """Test core memory processing functionality."""
    
    @pytest.mark.asyncio
    async def test_process_memory_success(self, mock_memory_pipeline):
        """Test successful memory processing through both phases."""
        test_content = "This is a test memory about machine learning concepts."
        
        # Mock phase 1 extraction
        extraction_result = {
            "processed_content": "Structured information about machine learning concepts",
            "summary": "ML concepts overview",
            "confidence": 0.9,
            "key_topics": ["machine learning", "concepts"]
        }
        
        with patch.object(mock_memory_pipeline, '_phase1_extract', return_value=extraction_result):
            # Mock embedding generation
            test_embedding = np.random.rand(1536).tolist()
            mock_memory_pipeline.ollama.generate_embeddings.return_value = test_embedding
            
            # Mock related memory search (no related memories found)
            with patch.object(mock_memory_pipeline, '_find_related_memories', return_value=[]):
                
                # Mock database operations
                mock_memory = Memory(
                    id=uuid4(),
                    original_content=test_content,
                    processed_content=extraction_result["processed_content"],
                    content_type="text",
                    confidence_score=0.9
                )
                mock_memory_pipeline.database.create_memory.return_value = mock_memory
                mock_memory_pipeline.database.create_memory_vector.return_value = None
                mock_memory_pipeline.qdrant.upsert_vector.return_value = True
                
                result = await mock_memory_pipeline.process_memory(
                    content=test_content,
                    content_type="text",
                    request_id="test-123"
                )
                
                assert result["status"] == "success"
                assert result["memory_id"] == mock_memory.id
                assert result["processed_content"] == extraction_result["processed_content"]
                assert result["confidence_score"] == 0.9
                assert "processing_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_process_memory_with_reconciliation(self, mock_memory_pipeline):
        """Test memory processing with phase 2 reconciliation."""
        test_content = "Updated information about neural networks."
        
        # Mock phase 1 extraction
        extraction_result = {
            "processed_content": "Information about neural networks",
            "summary": "Neural network update",
            "confidence": 0.85
        }
        
        # Mock related memory
        related_memory = Memory(
            id=uuid4(),
            processed_content="Previous neural network information",
            summary="Old neural network data",
            confidence_score=0.8
        )
        related_memories = [(related_memory, 0.82)]
        
        # Mock reconciliation result
        reconciliation_result = {
            "reconciled_content": "Integrated neural network information with updates",
            "confidence": 0.92,
            "changes_made": ["integrated new concepts", "resolved conflicts"]
        }
        
        with patch.object(mock_memory_pipeline, '_phase1_extract', return_value=extraction_result):
            test_embedding = np.random.rand(1536).tolist()
            mock_memory_pipeline.ollama.generate_embeddings.return_value = test_embedding
            
            with patch.object(mock_memory_pipeline, '_find_related_memories', return_value=related_memories):
                with patch.object(mock_memory_pipeline, '_phase2_reconcile', return_value=reconciliation_result):
                    
                    # Mock database operations
                    mock_memory = Memory(
                        id=uuid4(),
                        original_content=test_content,
                        processed_content=reconciliation_result["reconciled_content"],
                        content_type="text",
                        confidence_score=0.92
                    )
                    mock_memory_pipeline.database.create_memory.return_value = mock_memory
                    mock_memory_pipeline.database.create_memory_vector.return_value = None
                    mock_memory_pipeline.qdrant.upsert_vector.return_value = True
                    
                    result = await mock_memory_pipeline.process_memory(
                        content=test_content,
                        content_type="text",
                        request_id="test-456"
                    )
                    
                    assert result["status"] == "success"
                    assert result["processed_content"] == reconciliation_result["reconciled_content"]
                    assert result["confidence_score"] == 0.92
                    assert len(result["related_memories"]) == 1
                    assert result["pipeline_metrics"]["reconciliation_applied"] is True
    
    @pytest.mark.asyncio
    async def test_process_memory_phase1_failure(self, mock_memory_pipeline):
        """Test memory processing when phase 1 extraction fails."""
        test_content = "Test content for extraction failure"
        
        # Mock phase 1 extraction failure
        with patch.object(mock_memory_pipeline, '_phase1_extract', return_value=None):
            
            result = await mock_memory_pipeline.process_memory(
                content=test_content,
                request_id="test-fail"
            )
            
            assert result["status"] == "error"
            assert "Phase 1 extraction failed" in result["error"]
            assert "processing_time_ms" in result
    
    @pytest.mark.asyncio
    async def test_process_memory_embedding_fallback(self, mock_memory_pipeline):
        """Test memory processing with embedding generation fallback."""
        test_content = "Content for embedding fallback test"
        
        extraction_result = {
            "processed_content": "Processed content",
            "summary": "Test summary",
            "confidence": 0.8
        }
        
        with patch.object(mock_memory_pipeline, '_phase1_extract', return_value=extraction_result):
            # Mock embedding failure
            mock_memory_pipeline.ollama.generate_embeddings.return_value = None
            
            # Mock fallback embedding generation
            fallback_embedding = list(range(1536))
            with patch.object(mock_memory_pipeline, '_generate_fallback_embedding', return_value=fallback_embedding):
                
                with patch.object(mock_memory_pipeline, '_find_related_memories', return_value=[]):
                    
                    mock_memory = Memory(id=uuid4(), processed_content="test", content_type="text")
                    mock_memory_pipeline.database.create_memory.return_value = mock_memory
                    mock_memory_pipeline.database.create_memory_vector.return_value = None
                    mock_memory_pipeline.qdrant.upsert_vector.return_value = True
                    
                    result = await mock_memory_pipeline.process_memory(
                        content=test_content,
                        request_id="test-fallback"
                    )
                    
                    assert result["status"] == "success"
                    # Verify fallback embedding was used
                    mock_memory_pipeline._generate_fallback_embedding.assert_called_once_with(test_content)


class TestPhase1Extraction:
    """Test phase 1 extraction functionality."""
    
    @pytest.mark.asyncio
    async def test_phase1_extract_success(self, mock_memory_pipeline):
        """Test successful phase 1 extraction."""
        test_content = "Content to extract"
        extraction_result = {
            "processed_content": "Extracted structured content",
            "summary": "Content summary",
            "confidence": 0.88,
            "key_concepts": ["concept1", "concept2"]
        }
        
        mock_memory_pipeline.ollama.extract_memory.return_value = extraction_result
        
        result = await mock_memory_pipeline._phase1_extract(test_content, "test-123")
        
        assert result == extraction_result
        mock_memory_pipeline.ollama.extract_memory.assert_called_once_with(
            test_content, mock_memory_pipeline.extraction_prompt, "test-123"
        )
    
    @pytest.mark.asyncio
    async def test_phase1_extract_empty_content(self, mock_memory_pipeline):
        """Test phase 1 extraction with empty processed content."""
        test_content = "Content to extract"
        extraction_result = {
            "processed_content": "",  # Empty content
            "summary": "Summary",
            "confidence": 0.5
        }
        
        mock_memory_pipeline.ollama.extract_memory.return_value = extraction_result
        
        result = await mock_memory_pipeline._phase1_extract(test_content, "test-empty")
        
        assert result is None  # Should return None for empty content
    
    @pytest.mark.asyncio
    async def test_phase1_extract_low_confidence(self, mock_memory_pipeline):
        """Test phase 1 extraction with low confidence result."""
        test_content = "Ambiguous content"
        extraction_result = {
            "processed_content": "Low confidence extraction",
            "summary": "Uncertain summary",
            "confidence": 0.2  # Very low confidence
        }
        
        mock_memory_pipeline.ollama.extract_memory.return_value = extraction_result
        
        result = await mock_memory_pipeline._phase1_extract(test_content, "test-low-conf")
        
        # Should still return result but log warning
        assert result == extraction_result
    
    @pytest.mark.asyncio
    async def test_phase1_extract_service_error(self, mock_memory_pipeline):
        """Test phase 1 extraction with service error."""
        test_content = "Content to extract"
        
        mock_memory_pipeline.ollama.extract_memory.side_effect = RuntimeError("Service error")
        
        result = await mock_memory_pipeline._phase1_extract(test_content, "test-error")
        
        assert result is None


class TestPhase2Reconciliation:
    """Test phase 2 reconciliation functionality."""
    
    @pytest.mark.asyncio
    async def test_phase2_reconcile_success(self, mock_memory_pipeline):
        """Test successful phase 2 reconciliation."""
        new_content = "New memory content"
        
        related_memory1 = Memory(
            id=uuid4(),
            processed_content="Related content 1",
            summary="Summary 1",
            access_count=5
        )
        related_memory2 = Memory(
            id=uuid4(),
            processed_content="Related content 2",
            summary="Summary 2",
            access_count=3
        )
        
        related_memories = [(related_memory1, 0.85), (related_memory2, 0.78)]
        
        reconciliation_result = {
            "reconciled_content": "Reconciled memory content",
            "confidence": 0.91,
            "integration_changes": ["merged concepts", "resolved duplicates"]
        }
        
        mock_memory_pipeline.ollama.reconcile_memories.return_value = reconciliation_result
        
        result = await mock_memory_pipeline._phase2_reconcile(
            new_content, related_memories, "test-reconcile"
        )
        
        assert result == reconciliation_result
        
        # Verify correct data was passed to reconciliation
        call_args = mock_memory_pipeline.ollama.reconcile_memories.call_args
        related_data = call_args[0][1]  # Second argument is related_data
        
        assert len(related_data) == 2
        assert related_data[0]["processed_content"] == "Related content 1"
        assert related_data[0]["similarity_score"] == 0.85
        assert related_data[1]["similarity_score"] == 0.78
    
    @pytest.mark.asyncio
    async def test_phase2_reconcile_no_related_memories(self, mock_memory_pipeline):
        """Test phase 2 reconciliation with no related memories."""
        new_content = "New memory content"
        related_memories = []
        
        result = await mock_memory_pipeline._phase2_reconcile(
            new_content, related_memories, "test-no-related"
        )
        
        assert result is None
        mock_memory_pipeline.ollama.reconcile_memories.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_phase2_reconcile_empty_result(self, mock_memory_pipeline):
        """Test phase 2 reconciliation with empty reconciled content."""
        new_content = "New memory content"
        related_memory = Memory(id=uuid4(), processed_content="Related", summary="Sum")
        related_memories = [(related_memory, 0.8)]
        
        # Mock empty reconciliation result
        reconciliation_result = {
            "reconciled_content": "",  # Empty result
            "confidence": 0.5
        }
        
        mock_memory_pipeline.ollama.reconcile_memories.return_value = reconciliation_result
        
        result = await mock_memory_pipeline._phase2_reconcile(
            new_content, related_memories, "test-empty-reconcile"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_phase2_reconcile_max_related_limit(self, mock_memory_pipeline):
        """Test phase 2 reconciliation respects max related memories limit."""
        new_content = "New memory content"
        
        # Create more related memories than the max limit
        related_memories = [
            (Memory(id=uuid4(), processed_content=f"Related {i}", summary=f"Sum {i}"), 0.9 - i*0.1)
            for i in range(10)  # 10 related memories
        ]
        
        # Set max to 3
        mock_memory_pipeline.max_related_memories = 3
        
        reconciliation_result = {
            "reconciled_content": "Reconciled with top 3",
            "confidence": 0.89
        }
        
        mock_memory_pipeline.ollama.reconcile_memories.return_value = reconciliation_result
        
        result = await mock_memory_pipeline._phase2_reconcile(
            new_content, related_memories, "test-max-limit"
        )
        
        assert result == reconciliation_result
        
        # Verify only top 3 memories were passed
        call_args = mock_memory_pipeline.ollama.reconcile_memories.call_args
        related_data = call_args[0][1]
        
        assert len(related_data) == 3  # Should be limited to max
        # Should be the top 3 by similarity score
        assert related_data[0]["similarity_score"] == 0.9
        assert related_data[1]["similarity_score"] == 0.8
        assert related_data[2]["similarity_score"] == 0.7


class TestRelatedMemorySearch:
    """Test related memory search functionality."""
    
    @pytest.mark.asyncio
    async def test_find_related_memories_hybrid_search(self, mock_memory_pipeline):
        """Test finding related memories using hybrid search."""
        test_embedding = np.random.rand(1536).tolist()
        test_content = "Search content"
        
        # Mock PostgreSQL results
        postgres_memory1 = Memory(id=uuid4(), processed_content="Postgres result 1")
        postgres_memory2 = Memory(id=uuid4(), processed_content="Postgres result 2")
        postgres_results = [(postgres_memory1, 0.8), (postgres_memory2, 0.75)]
        
        # Mock Qdrant results
        qdrant_memory_id = uuid4()
        qdrant_results = [
            {
                "memory_id": str(qdrant_memory_id),
                "similarity_score": 0.85
            }
        ]
        
        # Mock Qdrant memory fetch
        qdrant_memory = Memory(id=qdrant_memory_id, processed_content="Qdrant result")
        
        mock_memory_pipeline.database.find_similar_memories.return_value = postgres_results
        mock_memory_pipeline.qdrant.search_similar_vectors.return_value = qdrant_results
        mock_memory_pipeline.database.get_memory_by_id.return_value = qdrant_memory
        
        results = await mock_memory_pipeline._find_related_memories(
            test_embedding, test_content, "test-hybrid"
        )
        
        # Should have combined results
        assert len(results) <= 3  # postgres(2) + qdrant(1), but deduplicated
        
        # Verify services were called
        mock_memory_pipeline.database.find_similar_memories.assert_called_once()
        mock_memory_pipeline.qdrant.search_similar_vectors.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_related_memories_postgres_error(self, mock_memory_pipeline):
        """Test related memory search when PostgreSQL fails."""
        test_embedding = np.random.rand(1536).tolist()
        test_content = "Search content"
        
        # Mock PostgreSQL error
        mock_memory_pipeline.database.find_similar_memories.side_effect = RuntimeError("DB error")
        
        # Mock successful Qdrant results
        qdrant_results = [{
            "memory_id": str(uuid4()),
            "similarity_score": 0.8
        }]
        qdrant_memory = Memory(id=uuid4(), processed_content="Qdrant only")
        
        mock_memory_pipeline.qdrant.search_similar_vectors.return_value = qdrant_results
        mock_memory_pipeline.database.get_memory_by_id.return_value = qdrant_memory
        
        results = await mock_memory_pipeline._find_related_memories(
            test_embedding, test_content, "test-postgres-error"
        )
        
        # Should still return Qdrant results
        assert len(results) == 1
        assert results[0][0] == qdrant_memory
        assert results[0][1] == 0.8
    
    @pytest.mark.asyncio
    async def test_find_related_memories_qdrant_error(self, mock_memory_pipeline):
        """Test related memory search when Qdrant fails."""
        test_embedding = np.random.rand(1536).tolist()
        test_content = "Search content"
        
        # Mock successful PostgreSQL results
        postgres_memory = Memory(id=uuid4(), processed_content="Postgres only")
        postgres_results = [(postgres_memory, 0.82)]
        
        mock_memory_pipeline.database.find_similar_memories.return_value = postgres_results
        
        # Mock Qdrant error
        mock_memory_pipeline.qdrant.search_similar_vectors.side_effect = RuntimeError("Qdrant error")
        
        results = await mock_memory_pipeline._find_related_memories(
            test_embedding, test_content, "test-qdrant-error"
        )
        
        # Should still return PostgreSQL results
        assert len(results) == 1
        assert results[0][0] == postgres_memory
        assert results[0][1] == 0.82
    
    @pytest.mark.asyncio
    async def test_find_related_memories_deduplication(self, mock_memory_pipeline):
        """Test deduplication when same memory appears in both searches."""
        test_embedding = np.random.rand(1536).tolist()
        test_content = "Search content"
        
        # Same memory ID in both results with different scores
        shared_memory_id = uuid4()
        shared_memory = Memory(id=shared_memory_id, processed_content="Shared result")
        
        # PostgreSQL result (lower score)
        postgres_results = [(shared_memory, 0.75)]
        
        # Qdrant result (higher score for same memory)
        qdrant_results = [{
            "memory_id": str(shared_memory_id),
            "similarity_score": 0.88
        }]
        
        mock_memory_pipeline.database.find_similar_memories.return_value = postgres_results
        mock_memory_pipeline.qdrant.search_similar_vectors.return_value = qdrant_results
        mock_memory_pipeline.database.get_memory_by_id.return_value = shared_memory
        
        results = await mock_memory_pipeline._find_related_memories(
            test_embedding, test_content, "test-dedup"
        )
        
        # Should have only one result with the higher score
        assert len(results) == 1
        assert results[0][0] == shared_memory
        assert results[0][1] == 0.88  # Higher Qdrant score should be kept


class TestFallbackEmbedding:
    """Test fallback embedding generation."""
    
    def test_generate_fallback_embedding(self, mock_memory_pipeline):
        """Test fallback embedding generation from content hash."""
        test_content = "Test content for fallback embedding"
        
        embedding = mock_memory_pipeline._generate_fallback_embedding(test_content)
        
        assert len(embedding) == 1536
        assert all(isinstance(v, float) for v in embedding)
        assert all(-1.0 <= v <= 1.0 for v in embedding)  # Normalized range
    
    def test_generate_fallback_embedding_consistency(self, mock_memory_pipeline):
        """Test that fallback embedding is consistent for same content."""
        test_content = "Consistent content"
        
        embedding1 = mock_memory_pipeline._generate_fallback_embedding(test_content)
        embedding2 = mock_memory_pipeline._generate_fallback_embedding(test_content)
        
        assert embedding1 == embedding2  # Should be deterministic
    
    def test_generate_fallback_embedding_different_content(self, mock_memory_pipeline):
        """Test that different content produces different embeddings."""
        content1 = "First content"
        content2 = "Second content"
        
        embedding1 = mock_memory_pipeline._generate_fallback_embedding(content1)
        embedding2 = mock_memory_pipeline._generate_fallback_embedding(content2)
        
        assert embedding1 != embedding2  # Should be different for different content


class TestMemorySearch:
    """Test memory search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_memories_success(self, mock_memory_pipeline):
        """Test successful memory search with hybrid results."""
        query = "machine learning concepts"
        
        # Mock query embedding
        query_embedding = np.random.rand(1536).tolist()
        mock_memory_pipeline.ollama.generate_embeddings.return_value = query_embedding
        
        # Mock PostgreSQL search results
        postgres_memory = Memory(
            id=uuid4(),
            processed_content="ML content from postgres",
            summary="ML summary",
            content_type="text"
        )
        postgres_results = [postgres_memory]
        
        # Mock Qdrant search results
        qdrant_memory_id = uuid4()
        qdrant_results = [{
            "memory_id": str(qdrant_memory_id),
            "similarity_score": 0.85
        }]
        qdrant_memory = Memory(
            id=qdrant_memory_id,
            processed_content="ML content from qdrant",
            summary="ML vector summary",
            content_type="text"
        )
        
        # Mock hybrid fusion results
        hybrid_results = [(postgres_memory, 0.78), (qdrant_memory, 0.85)]
        
        # Setup mocks
        mock_memory_pipeline.database.search_memories_by_content.return_value = postgres_results
        mock_memory_pipeline.qdrant.search_similar_vectors.return_value = qdrant_results
        mock_memory_pipeline.database.get_memory_by_id.return_value = qdrant_memory
        mock_memory_pipeline.database.update_memory_access.return_value = None
        
        with patch.object(mock_memory_pipeline, '_hybrid_fusion_ranking', return_value=hybrid_results):
            
            result = await mock_memory_pipeline.search_memories(
                query=query,
                limit=10,
                request_id="test-search"
            )
            
            assert result["total_count"] == 2
            assert len(result["results"]) == 2
            assert result["query"] == query
            assert result["hybrid_fusion_applied"] is True
            assert "processing_time_ms" in result
            
            # Verify result format
            first_result = result["results"][0]
            assert "memory_id" in first_result
            assert "content" in first_result
            assert "similarity_score" in first_result
            assert "created_at" in first_result
    
    @pytest.mark.asyncio
    async def test_search_memories_with_filters(self, mock_memory_pipeline):
        """Test memory search with content type and source filters."""
        query = "filtered search"
        
        query_embedding = np.random.rand(1536).tolist()
        mock_memory_pipeline.ollama.generate_embeddings.return_value = query_embedding
        
        # Mock empty results for simplicity
        mock_memory_pipeline.database.search_memories_by_content.return_value = []
        mock_memory_pipeline.qdrant.search_similar_vectors.return_value = []
        
        with patch.object(mock_memory_pipeline, '_hybrid_fusion_ranking', return_value=[]):
            
            result = await mock_memory_pipeline.search_memories(
                query=query,
                limit=5,
                content_type_filter="document",
                source_filter="research_papers",
                date_from="2024-01-01",
                date_to="2024-12-31",
                request_id="test-filtered"
            )
            
            # Verify filters were passed correctly
            postgres_call = mock_memory_pipeline.database.search_memories_by_content.call_args
            assert postgres_call.kwargs["content_type_filter"] == "document"
            assert postgres_call.kwargs["source_filter"] == "research_papers"
            
            qdrant_call = mock_memory_pipeline.qdrant.search_similar_vectors.call_args
            qdrant_filters = qdrant_call.kwargs.get("filter_conditions")
            assert qdrant_filters["content_type"] == "document"
            assert qdrant_filters["source"] == "research_papers"
    
    @pytest.mark.asyncio
    async def test_search_memories_embedding_fallback(self, mock_memory_pipeline):
        """Test memory search with embedding generation fallback."""
        query = "search query"
        
        # Mock embedding failure
        mock_memory_pipeline.ollama.generate_embeddings.return_value = None
        
        # Mock fallback embedding
        fallback_embedding = list(range(1536))
        with patch.object(mock_memory_pipeline, '_generate_fallback_embedding', return_value=fallback_embedding):
            
            mock_memory_pipeline.database.search_memories_by_content.return_value = []
            mock_memory_pipeline.qdrant.search_similar_vectors.return_value = []
            
            with patch.object(mock_memory_pipeline, '_hybrid_fusion_ranking', return_value=[]):
                
                result = await mock_memory_pipeline.search_memories(
                    query=query,
                    request_id="test-fallback-search"
                )
                
                assert result["total_count"] == 0
                # Verify fallback was used
                mock_memory_pipeline._generate_fallback_embedding.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_search_memories_error_handling(self, mock_memory_pipeline):
        """Test memory search error handling."""
        query = "error search"
        
        # Mock embedding generation failure that propagates
        mock_memory_pipeline.ollama.generate_embeddings.side_effect = RuntimeError("Embedding error")
        
        # Mock fallback also failing
        with patch.object(mock_memory_pipeline, '_generate_fallback_embedding', side_effect=RuntimeError("Fallback error")):
            
            result = await mock_memory_pipeline.search_memories(
                query=query,
                request_id="test-error-search"
            )
            
            assert result["total_count"] == 0
            assert "error" in result
            assert result["results"] == []
            assert "processing_time_ms" in result


class TestHybridFusionRanking:
    """Test hybrid fusion ranking algorithm."""
    
    @pytest.mark.asyncio
    async def test_hybrid_fusion_ranking_combined_results(self, mock_memory_pipeline):
        """Test hybrid fusion ranking with both PostgreSQL and Qdrant results."""
        query_embedding = np.random.rand(1536).tolist()
        
        # PostgreSQL results (text search)
        postgres_memory1 = Memory(id=uuid4(), processed_content="Text result 1")
        postgres_memory2 = Memory(id=uuid4(), processed_content="Text result 2")
        postgres_results = [postgres_memory1, postgres_memory2]
        
        # Qdrant results (vector search)
        qdrant_memory_id = uuid4()
        qdrant_results = [{
            "memory_id": str(qdrant_memory_id),
            "similarity_score": 0.9
        }]
        
        # Mock memory fetch
        qdrant_memory = Memory(id=qdrant_memory_id, processed_content="Vector result")
        mock_memory_pipeline.database.get_memory_by_id.return_value = qdrant_memory
        
        results = await mock_memory_pipeline._hybrid_fusion_ranking(
            postgres_results, qdrant_results, query_embedding, "test-fusion"
        )
        
        # Should have combined results with proper scoring
        assert len(results) == 3
        
        # Verify scores are computed (vector results should rank higher due to 60% weight)
        memory_scores = {memory.id: score for memory, score in results}
        qdrant_score = memory_scores[qdrant_memory_id]
        
        # Qdrant result should have high score due to vector similarity
        assert qdrant_score > 0.5  # 0.9 * 0.6 = 0.54
    
    @pytest.mark.asyncio
    async def test_hybrid_fusion_ranking_text_only(self, mock_memory_pipeline):
        """Test hybrid fusion ranking with only PostgreSQL results."""
        query_embedding = np.random.rand(1536).tolist()
        
        postgres_memory = Memory(id=uuid4(), processed_content="Text only result")
        postgres_results = [postgres_memory]
        qdrant_results = []
        
        results = await mock_memory_pipeline._hybrid_fusion_ranking(
            postgres_results, qdrant_results, query_embedding, "test-text-only"
        )
        
        assert len(results) == 1
        assert results[0][0] == postgres_memory
        # Text-only result should get 40% weight (0.4 for rank 1)
        assert results[0][1] == 0.4
    
    @pytest.mark.asyncio
    async def test_hybrid_fusion_ranking_vector_only(self, mock_memory_pipeline):
        """Test hybrid fusion ranking with only Qdrant results."""
        query_embedding = np.random.rand(1536).tolist()
        
        postgres_results = []
        qdrant_results = [{
            "memory_id": str(uuid4()),
            "similarity_score": 0.85
        }]
        
        qdrant_memory = Memory(id=UUID(qdrant_results[0]["memory_id"]), processed_content="Vector only")
        mock_memory_pipeline.database.get_memory_by_id.return_value = qdrant_memory
        
        results = await mock_memory_pipeline._hybrid_fusion_ranking(
            postgres_results, qdrant_results, query_embedding, "test-vector-only"
        )
        
        assert len(results) == 1
        assert results[0][0] == qdrant_memory
        # Vector-only result should get 60% weight (0.85 * 0.6 = 0.51)
        assert abs(results[0][1] - 0.51) < 0.01
    
    @pytest.mark.asyncio
    async def test_hybrid_fusion_ranking_overlap_higher_score(self, mock_memory_pipeline):
        """Test hybrid fusion ranking when same memory appears in both with score combination."""
        query_embedding = np.random.rand(1536).tolist()
        
        # Same memory in both results
        shared_memory = Memory(id=uuid4(), processed_content="Shared memory")
        postgres_results = [shared_memory]  # Rank 1, score = 1.0 * 0.4 = 0.4
        
        qdrant_results = [{
            "memory_id": str(shared_memory.id),
            "similarity_score": 0.8  # Score = 0.8 * 0.6 = 0.48
        }]
        
        results = await mock_memory_pipeline._hybrid_fusion_ranking(
            postgres_results, qdrant_results, query_embedding, "test-overlap"
        )
        
        assert len(results) == 1
        assert results[0][0] == shared_memory
        # Combined score = text_score * 0.4 + vector_score * 0.6 = 1.0 * 0.4 + 0.8 * 0.6 = 0.88
        assert abs(results[0][1] - 0.88) < 0.01


@pytest.mark.unit
@pytest.mark.pipeline
class TestPerformanceMetrics:
    """Test pipeline performance metrics and timing."""
    
    @pytest.mark.asyncio
    async def test_processing_time_measurement(self, mock_memory_pipeline):
        """Test that processing times are accurately measured."""
        test_content = "Content for timing test"
        
        # Mock delays to test timing
        async def slow_extraction(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms delay
            return {
                "processed_content": "Extracted content",
                "confidence": 0.8
            }
        
        async def slow_embedding(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms delay
            return np.random.rand(1536).tolist()
        
        with patch.object(mock_memory_pipeline, '_phase1_extract', side_effect=slow_extraction):
            mock_memory_pipeline.ollama.generate_embeddings.side_effect = slow_embedding
            
            with patch.object(mock_memory_pipeline, '_find_related_memories', return_value=[]):
                
                mock_memory = Memory(id=uuid4(), processed_content="test", content_type="text")
                mock_memory_pipeline.database.create_memory.return_value = mock_memory
                mock_memory_pipeline.database.create_memory_vector.return_value = None
                mock_memory_pipeline.qdrant.upsert_vector.return_value = True
                
                result = await mock_memory_pipeline.process_memory(
                    content=test_content,
                    request_id="test-timing"
                )
                
                # Total time should be at least 150ms due to our delays
                assert result["processing_time_ms"] >= 150
                
                # Phase metrics should be available
                metrics = result["pipeline_metrics"]
                assert metrics["phase1_time_ms"] >= 100
                assert metrics["total_time_ms"] >= 150