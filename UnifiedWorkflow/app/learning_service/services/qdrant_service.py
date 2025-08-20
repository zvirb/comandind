"""
Qdrant Vector Database Service
=============================

Integration with Qdrant for semantic pattern matching,
similarity search, and vector-based pattern retrieval.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import QdrantException
import numpy as np

from models.patterns import LearningPattern, PatternMatch
from config import config


logger = logging.getLogger(__name__)


class QdrantService:
    """
    Service for vector-based pattern storage and semantic similarity matching.
    
    Provides:
    - Pattern embedding storage
    - Semantic similarity search
    - Vector-based pattern clustering
    - Pattern recommendation based on similarity
    - Batch operations for performance
    """
    
    def __init__(self):
        self.client: Optional[AsyncQdrantClient] = None
        self.connected = False
        self.collection_name = config.qdrant_collection
        self.vector_size = config.qdrant_vector_size
        
        logger.info("Qdrant Service initialized")
    
    async def initialize(self) -> None:
        """Initialize connection to Qdrant vector database."""
        try:
            # Parse Qdrant URL
            url_parts = config.qdrant_url.replace('http://', '').replace('https://', '')
            if ':' in url_parts:
                host, port = url_parts.split(':')
                port = int(port)
            else:
                host = url_parts
                port = 6333
            
            # Create Qdrant client with SSL verification disabled
            # Following proven pattern from memory service
            self.client = AsyncQdrantClient(
                host=host,
                port=port,
                timeout=10.0,
                verify=False  # Disable SSL verification for internal Docker network
            )
            
            # Test connection
            collections = await self.client.get_collections()
            self.connected = True
            
            # Initialize collection
            await self._initialize_collection()
            
            logger.info(f"Successfully connected to Qdrant at {config.qdrant_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant Service: {e}")
            self.connected = False
            raise
    
    async def close(self) -> None:
        """Close Qdrant connection."""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Qdrant connection closed")
    
    async def store_pattern_embedding(
        self,
        pattern_id: str,
        embedding: np.ndarray,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store a pattern embedding with metadata.
        
        Args:
            pattern_id: Unique pattern identifier
            embedding: Vector embedding for the pattern
            metadata: Pattern metadata
            
        Returns:
            Success status
        """
        if not self.connected:
            logger.warning("Qdrant not connected")
            return False
        
        try:
            # Ensure embedding is the correct size
            if len(embedding) != self.vector_size:
                # Resize embedding if needed
                if len(embedding) > self.vector_size:
                    embedding = embedding[:self.vector_size]
                else:
                    # Pad with zeros
                    padded = np.zeros(self.vector_size)
                    padded[:len(embedding)] = embedding
                    embedding = padded
            
            # Create point
            point = models.PointStruct(
                id=pattern_id,
                vector=embedding.tolist(),
                payload={
                    **metadata,
                    "stored_at": datetime.utcnow().isoformat(),
                    "vector_size": len(embedding)
                }
            )
            
            # Store in Qdrant
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Stored embedding for pattern {pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing pattern embedding: {e}")
            return False
    
    async def search_similar_patterns(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar patterns based on vector similarity.
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            filters: Optional filters for metadata
            
        Returns:
            List of (pattern_id, similarity_score, metadata) tuples
        """
        if not self.connected:
            return []
        
        try:
            # Ensure query embedding is the correct size
            if len(query_embedding) != self.vector_size:
                if len(query_embedding) > self.vector_size:
                    query_embedding = query_embedding[:self.vector_size]
                else:
                    padded = np.zeros(self.vector_size)
                    padded[:len(query_embedding)] = query_embedding
                    query_embedding = padded
            
            # Build search filter
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
                if conditions:
                    search_filter = models.Filter(must=conditions)
            
            # Perform similarity search
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                query_filter=search_filter,
                limit=limit,
                score_threshold=similarity_threshold
            )
            
            # Process results
            similar_patterns = []
            for result in results:
                similar_patterns.append((
                    str(result.id),
                    float(result.score),
                    result.payload or {}
                ))
            
            logger.debug(f"Found {len(similar_patterns)} similar patterns")
            return similar_patterns
            
        except Exception as e:
            logger.error(f"Error searching similar patterns: {e}")
            return []
    
    async def batch_store_embeddings(
        self,
        embeddings_data: List[Tuple[str, np.ndarray, Dict[str, Any]]]
    ) -> int:
        """
        Store multiple embeddings in batch for better performance.
        
        Args:
            embeddings_data: List of (pattern_id, embedding, metadata) tuples
            
        Returns:
            Number of successfully stored embeddings
        """
        if not self.connected:
            return 0
        
        try:
            points = []
            for pattern_id, embedding, metadata in embeddings_data:
                # Ensure embedding is the correct size
                if len(embedding) != self.vector_size:
                    if len(embedding) > self.vector_size:
                        embedding = embedding[:self.vector_size]
                    else:
                        padded = np.zeros(self.vector_size)
                        padded[:len(embedding)] = embedding
                        embedding = padded
                
                point = models.PointStruct(
                    id=pattern_id,
                    vector=embedding.tolist(),
                    payload={
                        **metadata,
                        "stored_at": datetime.utcnow().isoformat(),
                        "vector_size": len(embedding)
                    }
                )
                points.append(point)
            
            # Batch upsert
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Batch stored {len(points)} embeddings")
            return len(points)
            
        except Exception as e:
            logger.error(f"Error in batch storing embeddings: {e}")
            return 0
    
    async def delete_pattern_embedding(self, pattern_id: str) -> bool:
        """Delete a pattern embedding."""
        if not self.connected:
            return False
        
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[pattern_id]
                )
            )
            
            logger.debug(f"Deleted embedding for pattern {pattern_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting pattern embedding: {e}")
            return False
    
    async def get_pattern_embedding(
        self, 
        pattern_id: str
    ) -> Optional[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        Retrieve a specific pattern embedding.
        
        Args:
            pattern_id: Pattern identifier
            
        Returns:
            Tuple of (embedding, metadata) or None
        """
        if not self.connected:
            return None
        
        try:
            results = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[pattern_id],
                with_vectors=True,
                with_payload=True
            )
            
            if results:
                result = results[0]
                embedding = np.array(result.vector)
                metadata = result.payload or {}
                return embedding, metadata
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving pattern embedding: {e}")
            return None
    
    async def cluster_patterns(
        self,
        pattern_ids: List[str],
        num_clusters: int = 5
    ) -> Dict[int, List[str]]:
        """
        Cluster patterns based on their embeddings.
        
        Args:
            pattern_ids: List of pattern IDs to cluster
            num_clusters: Number of clusters
            
        Returns:
            Dictionary mapping cluster ID to list of pattern IDs
        """
        if not self.connected:
            return {}
        
        try:
            # Retrieve embeddings
            results = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=pattern_ids,
                with_vectors=True
            )
            
            if not results:
                return {}
            
            # Extract embeddings and IDs
            embeddings = []
            valid_ids = []
            
            for result in results:
                if result.vector:
                    embeddings.append(result.vector)
                    valid_ids.append(str(result.id))
            
            if len(embeddings) < num_clusters:
                # Not enough patterns for clustering
                return {0: valid_ids}
            
            # Perform clustering using sklearn KMeans
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=num_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(embeddings)
            
            # Group patterns by cluster
            clusters = {}
            for pattern_id, cluster_id in zip(valid_ids, cluster_labels):
                cluster_id = int(cluster_id)
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(pattern_id)
            
            logger.info(f"Clustered {len(valid_ids)} patterns into {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            logger.error(f"Error clustering patterns: {e}")
            return {}
    
    async def find_pattern_neighbors(
        self,
        pattern_id: str,
        k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find k nearest neighbors for a pattern.
        
        Args:
            pattern_id: Pattern to find neighbors for
            k: Number of neighbors
            
        Returns:
            List of (neighbor_pattern_id, similarity_score) tuples
        """
        if not self.connected:
            return []
        
        try:
            # Get the pattern's embedding
            embedding_data = await self.get_pattern_embedding(pattern_id)
            if not embedding_data:
                return []
            
            embedding, _ = embedding_data
            
            # Search for similar patterns
            similar_patterns = await self.search_similar_patterns(
                query_embedding=embedding,
                limit=k + 1,  # +1 because the pattern itself will be included
                similarity_threshold=0.0  # Get all results
            )
            
            # Filter out the pattern itself
            neighbors = [
                (pid, score) for pid, score, _ in similar_patterns 
                if pid != pattern_id
            ][:k]
            
            return neighbors
            
        except Exception as e:
            logger.error(f"Error finding pattern neighbors: {e}")
            return []
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the patterns collection."""
        if not self.connected:
            return {}
        
        try:
            info = await self.client.get_collection(self.collection_name)
            return {
                "total_patterns": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.name,
                "indexed": info.status == models.CollectionStatus.GREEN
            }
            
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
    
    # Private methods
    
    async def _initialize_collection(self) -> None:
        """Initialize the patterns collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE
                    ),
                    optimizers_config=models.OptimizersConfig(
                        deleted_threshold=0.2,
                        vacuum_min_vector_number=1000,
                        default_segment_number=0,
                        max_segment_size=None,
                        memmap_threshold=None,
                        indexing_threshold=20000,
                        flush_interval_sec=5,
                        max_optimization_threads=1
                    ),
                    wal_config=models.WalConfig(
                        wal_capacity_mb=32,
                        wal_segments_ahead=0
                    )
                )
                
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing Qdrant collection: {self.collection_name}")
            
            # Create indexes for better performance
            await self._create_payload_indexes()
            
        except Exception as e:
            logger.error(f"Error initializing collection: {e}")
            raise
    
    async def _create_payload_indexes(self) -> None:
        """Create indexes on payload fields for better filtering performance."""
        try:
            # Common fields to index
            index_fields = [
                "pattern_type",
                "pattern_scope", 
                "source_service",
                "confidence_score",
                "created_at"
            ]
            
            for field in index_fields:
                try:
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_type=models.PayloadSchemaType.KEYWORD
                    )
                    logger.debug(f"Created index for field: {field}")
                except QdrantException as e:
                    # Index might already exist
                    logger.debug(f"Index creation for {field}: {e}")
            
        except Exception as e:
            logger.warning(f"Error creating payload indexes: {e}")
    
    async def _ensure_vector_size(self, embedding: np.ndarray) -> np.ndarray:
        """Ensure embedding vector is the correct size."""
        if len(embedding) == self.vector_size:
            return embedding
        elif len(embedding) > self.vector_size:
            return embedding[:self.vector_size]
        else:
            # Pad with zeros
            padded = np.zeros(self.vector_size)
            padded[:len(embedding)] = embedding
            return padded