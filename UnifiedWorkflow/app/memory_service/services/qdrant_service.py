"""Qdrant vector database service for semantic memory operations.

Provides high-performance vector operations for memory similarity search,
clustering, and semantic retrieval with optimized batch processing.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

logger = structlog.get_logger(__name__)


class QdrantService:
    """High-performance Qdrant vector database service.
    
    Optimized for memory operations with automatic collection management,
    batch processing, and robust error handling.
    """
    
    def __init__(
        self, 
        url: str, 
        collection_name: str = "hybrid_memory_vectors",
        vector_size: int = 1536,
        timeout: int = 30
    ):
        """Initialize Qdrant service.
        
        Args:
            url: Qdrant server URL
            collection_name: Name of the vector collection
            vector_size: Dimensionality of vectors
            timeout: Request timeout in seconds
        """
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.timeout = timeout
        
        # Initialize client
        self.client: Optional[AsyncQdrantClient] = None
        self._collection_exists: Optional[bool] = None
        
        logger.info("Initializing Qdrant service", 
                   url=url, 
                   collection=collection_name,
                   vector_size=vector_size)
    
    async def initialize(self) -> None:
        """Initialize Qdrant client and ensure collection exists."""
        try:
            # Configure for HTTPS with self-signed certificates
            import ssl
            import httpx
            
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create HTTP client with disabled SSL verification
            http_client = httpx.AsyncClient(verify=False)
            
            self.client = AsyncQdrantClient(
                url=self.url,
                timeout=self.timeout,
                verify=False,
                https=None,  # Let it detect from URL
                # Pass the HTTP client with disabled verification
                http_client=http_client
            )
            
            # Test connection
            await self.health_check()
            
            # Ensure collection exists
            await self._ensure_collection_exists()
            
            logger.info("Qdrant service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Qdrant service", error=str(e))
            # Re-raise so the fallback in main.py can catch it
            raise RuntimeError(f"Qdrant initialization failed: {e}") from e
    
    async def close(self) -> None:
        """Close Qdrant client connection."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Qdrant client connection closed")
    
    async def health_check(self) -> bool:
        """Check Qdrant service health."""
        try:
            if not self.client:
                return False
                
            # Simple health check by getting collections
            collections = await self.client.get_collections()
            return True
            
        except Exception as e:
            logger.error("Qdrant health check failed", error=str(e))
            return False
    
    async def _ensure_collection_exists(self) -> None:
        """Ensure the vector collection exists with proper configuration."""
        if self._collection_exists:
            return
        
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                logger.info("Qdrant collection already exists", collection=self.collection_name)
                self._collection_exists = True
                return
            
            # Create collection with optimized settings
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.vector_size,
                    distance=qdrant_models.Distance.COSINE,
                    on_disk=True  # Enable disk storage for large collections
                ),
                optimizers_config=qdrant_models.OptimizersConfigDiff(
                    deleted_threshold=0.2,
                    vacuum_min_vector_number=1000,
                    default_segment_number=2,
                    max_segment_size=20000,
                    memmap_threshold=20000,
                    indexing_threshold=20000,
                    flush_interval_sec=5
                ),
                hnsw_config=qdrant_models.HnswConfigDiff(
                    m=16,  # Number of connections each new element has
                    ef_construct=200,  # Size of dynamic candidate list
                    full_scan_threshold=10000  # Use full scan for small datasets
                )
            )
            
            logger.info("Created Qdrant collection", 
                       collection=self.collection_name,
                       vector_size=self.vector_size)
            
            self._collection_exists = True
            
        except Exception as e:
            logger.error("Failed to ensure Qdrant collection exists", 
                        collection=self.collection_name, 
                        error=str(e))
            raise
    
    async def upsert_vector(
        self,
        memory_id: UUID,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Insert or update a single vector with metadata.
        
        Args:
            memory_id: Unique memory identifier
            vector: Vector embedding
            metadata: Associated metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_collection_exists()
            
            point = qdrant_models.PointStruct(
                id=str(memory_id),
                vector=vector,
                payload=metadata
            )
            
            result = await self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=True
            )
            
            logger.debug("Upserted vector to Qdrant", 
                        memory_id=memory_id,
                        vector_dim=len(vector),
                        status=result.status)
            
            return result.status == "completed"
            
        except Exception as e:
            logger.error("Failed to upsert vector to Qdrant", 
                        memory_id=memory_id,
                        error=str(e))
            return False
    
    async def batch_upsert_vectors(
        self,
        vectors_data: List[Tuple[UUID, List[float], Dict[str, Any]]]
    ) -> int:
        """Batch insert/update multiple vectors for better performance.
        
        Args:
            vectors_data: List of (memory_id, vector, metadata) tuples
            
        Returns:
            Number of successfully processed vectors
        """
        if not vectors_data:
            return 0
        
        try:
            await self._ensure_collection_exists()
            
            points = [
                qdrant_models.PointStruct(
                    id=str(memory_id),
                    vector=vector,
                    payload=metadata
                )
                for memory_id, vector, metadata in vectors_data
            ]
            
            result = await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            
            success_count = len(vectors_data) if result.status == "completed" else 0
            
            logger.info("Batch upserted vectors to Qdrant", 
                       count=len(vectors_data),
                       successful=success_count,
                       status=result.status)
            
            return success_count
            
        except Exception as e:
            logger.error("Failed to batch upsert vectors to Qdrant", 
                        count=len(vectors_data),
                        error=str(e))
            return 0
    
    async def search_similar_vectors(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using cosine similarity.
        
        Args:
            query_vector: Query vector for similarity search
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Additional filter conditions
            
        Returns:
            List of similar memory records with scores
        """
        try:
            await self._ensure_collection_exists()
            
            # Build search request
            search_params = {
                "collection_name": self.collection_name,
                "query_vector": query_vector,
                "limit": limit,
                "with_payload": True,
                "with_vectors": False  # Don't return vectors to save bandwidth
            }
            
            if score_threshold is not None:
                search_params["score_threshold"] = score_threshold
            
            if filter_conditions:
                search_params["query_filter"] = qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key=key,
                            match=qdrant_models.MatchValue(value=value)
                        )
                        for key, value in filter_conditions.items()
                    ]
                )
            
            # Perform search
            results = await self.client.search(**search_params)
            
            # Process results
            processed_results = []
            for hit in results:
                result_data = {
                    "memory_id": hit.id,
                    "similarity_score": hit.score,
                    "metadata": hit.payload
                }
                processed_results.append(result_data)
            
            logger.debug("Qdrant vector search completed", 
                        query_dim=len(query_vector),
                        results_count=len(processed_results),
                        limit=limit,
                        threshold=score_threshold)
            
            return processed_results
            
        except Exception as e:
            logger.error("Failed to search similar vectors in Qdrant", 
                        query_dim=len(query_vector),
                        limit=limit,
                        error=str(e))
            return []
    
    async def delete_vector(self, memory_id: UUID) -> bool:
        """Delete a vector by memory ID.
        
        Args:
            memory_id: Memory identifier to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_collection_exists()
            
            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=[str(memory_id)]
                ),
                wait=True
            )
            
            logger.debug("Deleted vector from Qdrant", 
                        memory_id=memory_id,
                        status=result.status)
            
            return result.status == "completed"
            
        except Exception as e:
            logger.error("Failed to delete vector from Qdrant", 
                        memory_id=memory_id,
                        error=str(e))
            return False
    
    async def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """Get collection information and statistics.
        
        Returns:
            Collection info dict or None if failed
        """
        try:
            await self._ensure_collection_exists()
            
            info = await self.client.get_collection(self.collection_name)
            
            return {
                "name": info.name,
                "status": info.status,
                "vectors_count": info.points_count,
                "segments_count": info.segments_count,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance,
                    "on_disk": info.config.params.vectors.on_disk
                }
            }
            
        except Exception as e:
            logger.error("Failed to get Qdrant collection info", 
                        collection=self.collection_name,
                        error=str(e))
            return None
    
    async def scroll_vectors(
        self,
        limit: int = 100,
        offset: Optional[str] = None,
        with_payload: bool = True,
        with_vectors: bool = False
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Scroll through vectors in the collection.
        
        Args:
            limit: Number of vectors to return
            offset: Pagination offset
            with_payload: Include payload data
            with_vectors: Include vector data
            
        Returns:
            Tuple of (results, next_offset)
        """
        try:
            await self._ensure_collection_exists()
            
            result = await self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=with_payload,
                with_vectors=with_vectors
            )
            
            processed_results = []
            for point in result[0]:  # result is (points, next_page_offset)
                point_data = {
                    "id": point.id,
                    "payload": point.payload if with_payload else None,
                    "vector": point.vector if with_vectors else None
                }
                processed_results.append(point_data)
            
            return processed_results, result[1]
            
        except Exception as e:
            logger.error("Failed to scroll Qdrant vectors", 
                        limit=limit,
                        error=str(e))
            return [], None