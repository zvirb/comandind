"""Qdrant vector database mock for hybrid memory service testing."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
import numpy as np
from faker import Faker

fake = Faker()


class QdrantMockService:
    """Mock Qdrant vector database service."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_healthy = self.config.get("healthy", True)
        self.response_delay = self.config.get("response_delay", 0.0)
        self.error_rate = self.config.get("error_rate", 0.0)
        self.collection_name = self.config.get("collection_name", "test_memories")
        
        # Mock vector storage
        self.vectors = {}
        self.collection_info = {
            "points_count": 0,
            "segments_count": 1,
            "status": "green",
            "config": {
                "distance": "cosine",
                "vector_size": 1536
            }
        }
        
        # Populate sample data if requested
        if self.config.get("populate_sample_data", False):
            self._populate_sample_data()
    
    async def initialize(self):
        """Mock initialization."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Qdrant initialization failed")
    
    async def health_check(self) -> bool:
        """Mock health check."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Qdrant health check failed")
        
        return self.is_healthy
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Mock collection info retrieval."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to get collection info")
        
        # Update points count
        self.collection_info["points_count"] = len(self.vectors)
        return self.collection_info.copy()
    
    async def upsert_vector(
        self,
        memory_id: UUID,
        vector: List[float],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Mock vector upsert."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to upsert vector")
        
        self.vectors[str(memory_id)] = {
            "memory_id": str(memory_id),
            "vector": vector,
            "metadata": metadata or {},
            "created_at": datetime.now()
        }
        
        return True
    
    async def search_similar_vectors(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Mock similar vector search."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to search vectors")
        
        results = []
        
        for vector_id, vector_data in self.vectors.items():
            # Apply filters if specified
            if filter_conditions:
                metadata = vector_data.get("metadata", {})
                if not self._matches_filters(metadata, filter_conditions):
                    continue
            
            # Calculate similarity
            similarity = self._cosine_similarity(query_vector, vector_data["vector"])
            
            if similarity >= score_threshold:
                results.append({
                    "memory_id": vector_data["memory_id"],
                    "similarity_score": similarity,
                    "metadata": vector_data.get("metadata", {}),
                    "created_at": vector_data.get("created_at", datetime.now()).isoformat()
                })
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
    
    async def delete_vector(self, memory_id: UUID) -> bool:
        """Mock vector deletion."""
        await self._simulate_delay()
        
        if self._should_error():
            raise RuntimeError("Failed to delete vector")
        
        vector_id = str(memory_id)
        if vector_id in self.vectors:
            del self.vectors[vector_id]
            return True
        
        return False
    
    async def close(self):
        """Mock cleanup."""
        pass
    
    # Helper methods
    
    async def _simulate_delay(self):
        """Simulate operation delay."""
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
        
        return float(dot_product / (norm_v1 * norm_v2))
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches filter conditions."""
        for key, value in filters.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True
    
    def _populate_sample_data(self):
        """Populate mock with sample vector data."""
        sample_vectors = [
            {
                "memory_id": fake.uuid4(),
                "vector": np.random.rand(1536).tolist(),
                "metadata": {
                    "content_type": "text",
                    "source": "research_papers",
                    "created_at": fake.date_this_year().isoformat(),
                    "summary": "Deep learning research summary"
                }
            },
            {
                "memory_id": fake.uuid4(),
                "vector": np.random.rand(1536).tolist(),
                "metadata": {
                    "content_type": "text",
                    "source": "development_docs",
                    "created_at": fake.date_this_year().isoformat(),
                    "summary": "API development documentation"
                }
            },
            {
                "memory_id": fake.uuid4(),
                "vector": np.random.rand(1536).tolist(),
                "metadata": {
                    "content_type": "text",
                    "source": "data_science_notes",
                    "created_at": fake.date_this_year().isoformat(),
                    "summary": "Statistical analysis notes"
                }
            }
        ]
        
        for vector_data in sample_vectors:
            self.vectors[vector_data["memory_id"]] = {
                "memory_id": vector_data["memory_id"],
                "vector": vector_data["vector"],
                "metadata": vector_data["metadata"],
                "created_at": datetime.now()
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
    
    "slow_vector_db": {
        "healthy": True,
        "response_delay": 0.3,
        "error_rate": 0.0,
        "populate_sample_data": False
    },
    
    "unreliable": {
        "healthy": True,
        "response_delay": 0.05,
        "error_rate": 0.08,  # 8% error rate
        "populate_sample_data": False
    },
    
    "unhealthy": {
        "healthy": False,
        "response_delay": 0.0,
        "error_rate": 0.6,  # 60% error rate
        "populate_sample_data": False
    }
}


def create_qdrant_mock(config_name: str = "healthy_fast") -> QdrantMockService:
    """Create Qdrant mock with predefined configuration."""
    config = MOCK_CONFIGS.get(config_name, MOCK_CONFIGS["healthy_fast"])
    return QdrantMockService(config)