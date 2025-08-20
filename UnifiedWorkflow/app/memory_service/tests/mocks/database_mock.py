"""Database service mock for hybrid memory service testing."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4, UUID
import numpy as np
from faker import Faker

fake = Faker()


class MockMemory:
    """Mock memory object matching the database model."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.original_content = kwargs.get("original_content", "")
        self.processed_content = kwargs.get("processed_content", "")
        self.summary = kwargs.get("summary", "")
        self.content_type = kwargs.get("content_type", "text")
        self.source = kwargs.get("source", "")
        self.tags = kwargs.get("tags", "[]")
        self.confidence_score = kwargs.get("confidence_score", 0.8)
        self.relevance_score = kwargs.get("relevance_score", 0.8)
        self.access_count = kwargs.get("access_count", 0)
        self.consolidation_count = kwargs.get("consolidation_count", 0)
        self.created_at = kwargs.get("created_at", datetime.now())
        self.updated_at = kwargs.get("updated_at", datetime.now())
        self.metadata_ = kwargs.get("metadata_", {})


class DatabaseMockService:
    """Mock database service for memory testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_healthy = self.config.get("healthy", True)
        self.response_delay = self.config.get("response_delay", 0.0)
        self.error_rate = self.config.get("error_rate", 0.0)
        
        # Mock data storage
        self.memories = {}
        self.memory_vectors = {}
        self.connection_pool_stats = {
            "active": 8,
            "idle": 12,
            "total": 20
        }
        
        # Populate with sample data if requested
        if self.config.get("populate_sample_data", False):
            self._populate_sample_data()
    
    async def initialize(self):
        """Mock initialization."""
        await self._simulate_delay()
        if self._should_error():
            raise RuntimeError("Database initialization failed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Database health check failed")
        
        return {
            "healthy": self.is_healthy,
            "memory_count": len(self.memories),
            "vector_count": len(self.memory_vectors),
            "connection_pool": self.connection_pool_stats
        }
    
    async def create_memory(
        self,
        original_content: str,
        processed_content: str,
        summary: Optional[str] = None,
        content_type: str = "text",
        source: Optional[str] = None,
        tags: Optional[str] = None,
        confidence_score: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MockMemory:
        """Mock memory creation."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to create memory")
        
        memory = MockMemory(
            original_content=original_content,
            processed_content=processed_content,
            summary=summary,
            content_type=content_type,
            source=source,
            tags=tags,
            confidence_score=confidence_score,
            metadata_=metadata or {}
        )
        
        self.memories[memory.id] = memory
        return memory
    
    async def create_memory_vector(
        self,
        memory_id: UUID,
        embedding: List[float],
        vector_type: str = "semantic",
        model_name: str = "llama2",
        embedding_quality: float = 0.8
    ):
        """Mock memory vector creation."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to create memory vector")
        
        self.memory_vectors[memory_id] = {
            "memory_id": memory_id,
            "embedding": embedding,
            "vector_type": vector_type,
            "model_name": model_name,
            "embedding_quality": embedding_quality,
            "created_at": datetime.now()
        }
    
    async def get_memory_by_id(self, memory_id: UUID) -> Optional[MockMemory]:
        """Mock memory retrieval by ID."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to get memory")
        
        return self.memories.get(memory_id)
    
    async def find_similar_memories(
        self,
        embedding: List[float],
        similarity_threshold: float = 0.7,
        limit: int = 10
    ) -> List[Tuple[MockMemory, float]]:
        """Mock similar memory finding using cosine similarity."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to find similar memories")
        
        results = []
        
        for memory_id, vector_data in self.memory_vectors.items():
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                stored_embedding = vector_data["embedding"]
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(embedding, stored_embedding)
                
                if similarity >= similarity_threshold:
                    results.append((memory, similarity))
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    async def search_memories_by_content(
        self,
        query: str,
        limit: int = 10,
        content_type_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[MockMemory]:
        """Mock content-based memory search."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to search memories")
        
        results = []
        query_lower = query.lower()
        
        for memory in self.memories.values():
            # Apply filters
            if content_type_filter and memory.content_type != content_type_filter:
                continue
            if source_filter and memory.source != source_filter:
                continue
            if date_from and memory.created_at < date_from:
                continue
            if date_to and memory.created_at > date_to:
                continue
            
            # Check content relevance
            content_match = (
                query_lower in memory.processed_content.lower() or
                query_lower in memory.summary.lower() if memory.summary else False
            )
            
            if content_match:
                results.append(memory)
        
        # Sort by relevance (mock scoring)
        results.sort(key=lambda m: m.relevance_score, reverse=True)
        return results[:limit]
    
    async def update_memory_access(self, memory_id: UUID):
        """Mock memory access tracking update."""
        await self._simulate_delay()
        
        if memory_id in self.memories:
            self.memories[memory_id].access_count += 1
    
    async def close(self):
        """Mock cleanup."""
        pass
    
    # Helper methods
    
    async def _simulate_delay(self):
        """Simulate database operation delay."""
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
    
    def _should_error(self) -> bool:
        """Determine if operation should error."""
        return np.random.random() < self.error_rate
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return dot_product / (norm_v1 * norm_v2)
    
    def _populate_sample_data(self):
        """Populate mock with sample data."""
        sample_memories = [
            {
                "original_content": "Deep learning neural networks for computer vision applications",
                "processed_content": "Comprehensive overview of deep learning architectures for image processing",
                "summary": "Deep learning for computer vision",
                "content_type": "text",
                "source": "research_papers",
                "confidence_score": 0.92
            },
            {
                "original_content": "RESTful API design patterns and best practices for microservices",
                "processed_content": "Guide to designing scalable REST APIs in microservice architectures",
                "summary": "REST API design for microservices",
                "content_type": "text", 
                "source": "development_docs",
                "confidence_score": 0.88
            },
            {
                "original_content": "Statistical analysis methods for large-scale data processing",
                "processed_content": "Statistical techniques for analyzing big data workflows",
                "summary": "Statistical methods for big data",
                "content_type": "text",
                "source": "data_science_notes",
                "confidence_score": 0.85
            }
        ]
        
        for i, mem_data in enumerate(sample_memories):
            memory = MockMemory(
                **mem_data,
                created_at=datetime.now() - timedelta(days=i+1)
            )
            self.memories[memory.id] = memory
            
            # Create corresponding vector
            embedding = np.random.rand(1536).tolist()
            self.memory_vectors[memory.id] = {
                "memory_id": memory.id,
                "embedding": embedding,
                "vector_type": "semantic",
                "model_name": "llama2",
                "embedding_quality": 0.9,
                "created_at": memory.created_at
            }


# Predefined mock configurations

MOCK_CONFIGS = {
    "healthy_fast": {
        "healthy": True,
        "response_delay": 0.01,
        "error_rate": 0.0,
        "populate_sample_data": False
    },
    
    "healthy_with_data": {
        "healthy": True,
        "response_delay": 0.02,
        "error_rate": 0.0,
        "populate_sample_data": True
    },
    
    "slow_database": {
        "healthy": True,
        "response_delay": 0.5,
        "error_rate": 0.0,
        "populate_sample_data": False
    },
    
    "unreliable": {
        "healthy": True,
        "response_delay": 0.1,
        "error_rate": 0.05,  # 5% error rate
        "populate_sample_data": False
    },
    
    "unhealthy": {
        "healthy": False,
        "response_delay": 0.0,
        "error_rate": 0.5,  # 50% error rate
        "populate_sample_data": False
    }
}


def create_database_mock(config_name: str = "healthy_fast") -> DatabaseMockService:
    """Create database mock with predefined configuration."""
    config = MOCK_CONFIGS.get(config_name, MOCK_CONFIGS["healthy_fast"])
    return DatabaseMockService(config)