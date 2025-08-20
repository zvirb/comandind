"""Two-phase memory pipeline with LLM-driven extraction and reconciliation.

Implements the core memory processing workflow:
1. Phase 1: Extract and structure memory content using LLM
2. Phase 2: Reconcile with existing memories for consistency and deduplication

Optimized for >95% curation accuracy and MRR >0.85 performance targets.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

import structlog

from .ollama_service import OllamaService
from .database_service import DatabaseService
from .qdrant_service import QdrantService
try:
    from ..models.memory import Memory
except ImportError:
    # Fallback for module execution in Docker
    from models.memory import Memory

logger = structlog.get_logger(__name__)


class MemoryPipeline:
    """Two-phase memory processing pipeline.
    
    Orchestrates the complete memory lifecycle from raw content to
    searchable, reconciled memory with dual-database storage.
    """
    
    def __init__(
        self,
        ollama_service: OllamaService,
        database_service: DatabaseService,
        qdrant_service: QdrantService,
        extraction_prompt: str,
        reconciliation_prompt: str,
        similarity_threshold: float = 0.75,
        max_related_memories: int = 5
    ):
        """Initialize memory pipeline.
        
        Args:
            ollama_service: LLM service for processing
            database_service: PostgreSQL service
            qdrant_service: Vector database service
            extraction_prompt: Prompt for extraction phase
            reconciliation_prompt: Prompt for reconciliation phase
            similarity_threshold: Similarity threshold for finding related memories
            max_related_memories: Maximum related memories to consider
        """
        self.ollama = ollama_service
        self.database = database_service
        self.qdrant = qdrant_service
        self.extraction_prompt = extraction_prompt
        self.reconciliation_prompt = reconciliation_prompt
        self.similarity_threshold = similarity_threshold
        self.max_related_memories = max_related_memories
        
        logger.info("Initialized memory pipeline", 
                   similarity_threshold=similarity_threshold,
                   max_related_memories=max_related_memories)
    
    async def process_memory(
        self,
        content: str,
        content_type: str = "text",
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process new memory content through the two-phase pipeline.
        
        Args:
            content: Raw memory content to process
            content_type: Type of content
            source: Content source
            tags: Associated tags
            metadata: Additional metadata
            request_id: Request tracking ID
            
        Returns:
            Processing result with memory ID, processed content, and metrics
        """
        pipeline_start = time.time()
        
        logger.info("Starting memory pipeline", 
                   request_id=request_id,
                   content_length=len(content),
                   content_type=content_type)
        
        try:
            # Phase 1: Extract and structure content
            phase1_start = time.time()
            extraction_result = await self._phase1_extract(
                content, request_id
            )
            phase1_time = time.time() - phase1_start
            
            if not extraction_result:
                raise RuntimeError("Phase 1 extraction failed")
            
            logger.info("Phase 1 extraction completed",
                       request_id=request_id,
                       processing_time_ms=round(phase1_time * 1000, 2),
                       confidence=extraction_result.get("confidence", 0.0))
            
            # Generate embeddings for similarity search
            embedding = await self.ollama.generate_embeddings(
                extraction_result["processed_content"], 
                request_id
            )
            
            if not embedding:
                logger.warning("Failed to generate embeddings, using content hash fallback")
                embedding = self._generate_fallback_embedding(content)
            
            # Phase 2: Find related memories and reconcile
            phase2_start = time.time()
            
            # Find similar memories using both PostgreSQL and Qdrant
            similar_memories = await self._find_related_memories(
                embedding, extraction_result["processed_content"], request_id
            )
            
            # Reconcile if similar memories found
            reconciliation_result = None
            if similar_memories:
                reconciliation_result = await self._phase2_reconcile(
                    extraction_result["processed_content"],
                    similar_memories,
                    request_id
                )
            
            phase2_time = time.time() - phase2_start
            
            logger.info("Phase 2 reconciliation completed",
                       request_id=request_id,
                       processing_time_ms=round(phase2_time * 1000, 2),
                       related_memories_count=len(similar_memories),
                       reconciliation_applied=reconciliation_result is not None)
            
            # Use reconciled content if available
            final_content = (
                reconciliation_result.get("reconciled_content") 
                if reconciliation_result 
                else extraction_result["processed_content"]
            )
            
            final_confidence = (
                reconciliation_result.get("confidence")
                if reconciliation_result
                else extraction_result.get("confidence", 0.8)
            )
            
            # Store in PostgreSQL
            memory = await self.database.create_memory(
                original_content=content,
                processed_content=final_content,
                summary=extraction_result.get("summary"),
                content_type=content_type,
                source=source,
                tags=json.dumps(tags) if tags else None,
                confidence_score=final_confidence,
                metadata={
                    "extraction_model": self.ollama.model,
                    "reconciliation_model": self.ollama.model if reconciliation_result else None,
                    "related_memories_count": len(similar_memories),
                    "processing_version": "1.0",
                    **(metadata or {})
                }
            )
            
            # Create vector record in PostgreSQL
            await self.database.create_memory_vector(
                memory_id=memory.id,
                embedding=embedding,
                vector_type="semantic",
                model_name=self.ollama.model,
                embedding_quality=final_confidence
            )
            
            # Store vector in Qdrant
            qdrant_metadata = {
                "memory_id": str(memory.id),
                "content_type": content_type,
                "source": source,
                "created_at": memory.created_at.isoformat(),
                "summary": extraction_result.get("summary", "")[:200]  # Truncate for Qdrant
            }
            
            qdrant_success = await self.qdrant.upsert_vector(
                memory.id, embedding, qdrant_metadata
            )
            
            if not qdrant_success:
                logger.warning("Failed to store vector in Qdrant", 
                             memory_id=memory.id)
            
            # Calculate total processing time
            total_time = time.time() - pipeline_start
            
            # Prepare result
            result = {
                "memory_id": memory.id,
                "processed_content": final_content,
                "summary": extraction_result.get("summary"),
                "confidence_score": final_confidence,
                "related_memories": [str(mem.id) for mem, _ in similar_memories],
                "processing_time_ms": round(total_time * 1000, 2),
                "status": "success",
                "pipeline_metrics": {
                    "phase1_time_ms": round(phase1_time * 1000, 2),
                    "phase2_time_ms": round(phase2_time * 1000, 2),
                    "total_time_ms": round(total_time * 1000, 2),
                    "related_memories_found": len(similar_memories),
                    "reconciliation_applied": reconciliation_result is not None,
                    "qdrant_storage_success": qdrant_success
                }
            }
            
            logger.info("Memory pipeline completed successfully",
                       request_id=request_id,
                       memory_id=memory.id,
                       total_time_ms=round(total_time * 1000, 2),
                       confidence=final_confidence)
            
            return result
            
        except Exception as e:
            total_time = time.time() - pipeline_start
            
            logger.error("Memory pipeline failed",
                        request_id=request_id,
                        error=str(e),
                        processing_time_ms=round(total_time * 1000, 2))
            
            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": round(total_time * 1000, 2)
            }
    
    async def _phase1_extract(
        self,
        content: str,
        request_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Phase 1: Extract and structure memory content.
        
        Args:
            content: Raw content to extract
            request_id: Request tracking ID
            
        Returns:
            Extraction result with processed content and metadata
        """
        try:
            result = await self.ollama.extract_memory(
                content, self.extraction_prompt, request_id
            )
            
            # Validate extraction result
            if not result.get("processed_content"):
                logger.warning("Empty processed content from extraction", 
                             request_id=request_id)
                return None
            
            # Ensure minimum quality threshold
            confidence = result.get("confidence", 0.5)
            if confidence < 0.3:
                logger.warning("Low confidence extraction result", 
                             confidence=confidence,
                             request_id=request_id)
                # Still proceed but flag the low confidence
            
            return result
            
        except Exception as e:
            logger.error("Phase 1 extraction failed", 
                        request_id=request_id,
                        error=str(e))
            return None
    
    async def _phase2_reconcile(
        self,
        new_content: str,
        related_memories: List[Tuple[Memory, float]],
        request_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Phase 2: Reconcile new memory with related existing memories.
        
        Args:
            new_content: New memory content
            related_memories: List of (Memory, similarity_score) tuples
            request_id: Request tracking ID
            
        Returns:
            Reconciliation result with refined content
        """
        try:
            if not related_memories:
                return None
            
            # Prepare related memory data for reconciliation
            related_data = []
            for memory, similarity_score in related_memories[:self.max_related_memories]:
                related_data.append({
                    "processed_content": memory.processed_content,
                    "summary": memory.summary,
                    "similarity_score": similarity_score,
                    "created_at": memory.created_at.isoformat(),
                    "access_count": memory.access_count
                })
            
            result = await self.ollama.reconcile_memories(
                new_content, related_data, self.reconciliation_prompt, request_id
            )
            
            # Validate reconciliation result
            if not result.get("reconciled_content"):
                logger.warning("Empty reconciled content", request_id=request_id)
                return None
            
            return result
            
        except Exception as e:
            logger.error("Phase 2 reconciliation failed", 
                        request_id=request_id,
                        error=str(e))
            return None
    
    async def _find_related_memories(
        self,
        embedding: List[float],
        content: str,
        request_id: Optional[str] = None
    ) -> List[Tuple[Memory, float]]:
        """Find related memories using hybrid search (PostgreSQL + Qdrant).
        
        Args:
            embedding: Query vector embedding
            content: Content for text-based search
            request_id: Request tracking ID
            
        Returns:
            List of (Memory, similarity_score) tuples
        """
        try:
            # Run both searches concurrently for better performance
            postgres_task = self.database.find_similar_memories(
                embedding,
                similarity_threshold=self.similarity_threshold,
                limit=self.max_related_memories
            )
            
            qdrant_task = self.qdrant.search_similar_vectors(
                embedding,
                limit=self.max_related_memories,
                score_threshold=self.similarity_threshold
            )
            
            postgres_results, qdrant_results = await asyncio.gather(
                postgres_task, qdrant_task, return_exceptions=True
            )
            
            # Handle potential errors
            if isinstance(postgres_results, Exception):
                logger.warning("PostgreSQL similarity search failed", 
                             error=str(postgres_results))
                postgres_results = []
            
            if isinstance(qdrant_results, Exception):
                logger.warning("Qdrant similarity search failed", 
                             error=str(qdrant_results))
                qdrant_results = []
            
            # Combine and deduplicate results
            combined_results = {}
            
            # Add PostgreSQL results
            for memory, similarity_score in postgres_results:
                combined_results[memory.id] = (memory, similarity_score, "postgres")
            
            # Add Qdrant results (may override with different scores)
            for qdrant_result in qdrant_results:
                memory_id = UUID(qdrant_result["memory_id"])
                similarity_score = qdrant_result["similarity_score"]
                
                if memory_id in combined_results:
                    # Take the higher similarity score
                    existing_memory, existing_score, existing_source = combined_results[memory_id]
                    if similarity_score > existing_score:
                        combined_results[memory_id] = (existing_memory, similarity_score, "qdrant")
                else:
                    # Need to fetch memory from database
                    memory = await self.database.get_memory_by_id(memory_id)
                    if memory:
                        combined_results[memory_id] = (memory, similarity_score, "qdrant")
            
            # Sort by similarity score and return top results
            final_results = [
                (memory, score) for memory, score, source in combined_results.values()
            ]
            final_results.sort(key=lambda x: x[1], reverse=True)
            final_results = final_results[:self.max_related_memories]
            
            logger.debug("Related memories search completed",
                        request_id=request_id,
                        postgres_count=len(postgres_results) if isinstance(postgres_results, list) else 0,
                        qdrant_count=len(qdrant_results) if isinstance(qdrant_results, list) else 0,
                        combined_count=len(final_results))
            
            return final_results
            
        except Exception as e:
            logger.error("Failed to find related memories", 
                        request_id=request_id,
                        error=str(e))
            return []
    
    def _generate_fallback_embedding(self, content: str) -> List[float]:
        """Generate a simple fallback embedding when LLM embedding fails.
        
        Args:
            content: Content to embed
            
        Returns:
            Fallback vector embedding
        """
        import hashlib
        
        # Generate hash-based embedding
        hash_obj = hashlib.sha256(content.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert hash to vector
        vector = []
        for i in range(0, len(hash_hex), 2):
            byte_val = int(hash_hex[i:i+2], 16)
            normalized_val = (byte_val - 127.5) / 127.5  # Normalize to [-1, 1]
            vector.append(normalized_val)
        
        # Pad or truncate to 1536 dimensions
        while len(vector) < 1536:
            vector.extend(vector[:min(len(vector), 1536 - len(vector))])
        vector = vector[:1536]
        
        logger.debug("Generated fallback embedding", 
                   content_length=len(content),
                   vector_dim=len(vector))
        
        return vector
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        content_type_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_summary_only: bool = False,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search memories using hybrid approach (text + vector).
        
        Args:
            query: Search query
            limit: Maximum results
            similarity_threshold: Minimum similarity score
            content_type_filter: Filter by content type
            source_filter: Filter by source
            date_from: Search from date
            date_to: Search to date
            include_summary_only: Return only summaries
            request_id: Request tracking ID
            
        Returns:
            Search results with memories and metadata
        """
        search_start = time.time()
        threshold = similarity_threshold or self.similarity_threshold
        
        logger.info("Starting memory search",
                   request_id=request_id,
                   query_length=len(query),
                   limit=limit,
                   threshold=threshold)
        
        try:
            # Generate query embedding for vector search
            query_embedding = await self.ollama.generate_embeddings(query, request_id)
            
            if not query_embedding:
                query_embedding = self._generate_fallback_embedding(query)
            
            # Run parallel searches
            from datetime import datetime
            
            # Convert date strings if provided
            date_from_obj = datetime.fromisoformat(date_from) if date_from else None
            date_to_obj = datetime.fromisoformat(date_to) if date_to else None
            
            # PostgreSQL text search
            postgres_task = self.database.search_memories_by_content(
                query=query,
                limit=limit,
                content_type_filter=content_type_filter,
                source_filter=source_filter,
                date_from=date_from_obj,
                date_to=date_to_obj
            )
            
            # Qdrant vector search
            qdrant_filters = {}
            if content_type_filter:
                qdrant_filters["content_type"] = content_type_filter
            if source_filter:
                qdrant_filters["source"] = source_filter
            
            qdrant_task = self.qdrant.search_similar_vectors(
                query_vector=query_embedding,
                limit=limit,
                score_threshold=threshold,
                filter_conditions=qdrant_filters if qdrant_filters else None
            )
            
            # Execute searches concurrently
            postgres_results, qdrant_results = await asyncio.gather(
                postgres_task, qdrant_task, return_exceptions=True
            )
            
            # Handle errors
            if isinstance(postgres_results, Exception):
                logger.warning("PostgreSQL search failed", error=str(postgres_results))
                postgres_results = []
            
            if isinstance(qdrant_results, Exception):
                logger.warning("Qdrant search failed", error=str(qdrant_results))
                qdrant_results = []
            
            # Combine and rank results using hybrid fusion
            combined_results = await self._hybrid_fusion_ranking(
                postgres_results, qdrant_results, query_embedding, request_id
            )
            
            # Apply final limit
            final_results = combined_results[:limit]
            
            # Format results
            formatted_results = []
            for memory, similarity_score in final_results:
                # Update access tracking
                await self.database.update_memory_access(memory.id)
                
                result_data = {
                    "memory_id": memory.id,
                    "content": memory.summary if include_summary_only else memory.processed_content,
                    "summary": memory.summary,
                    "content_type": memory.content_type,
                    "source": memory.source,
                    "tags": json.loads(memory.tags) if memory.tags else [],
                    "similarity_score": similarity_score,
                    "relevance_score": memory.relevance_score,
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at,
                    "access_count": memory.access_count + 1,  # Account for this access
                    "consolidation_count": memory.consolidation_count
                }
                formatted_results.append(result_data)
            
            search_time = time.time() - search_start
            
            result = {
                "results": formatted_results,
                "total_count": len(formatted_results),
                "query": query,
                "processing_time_ms": round(search_time * 1000, 2),
                "similarity_threshold_used": threshold,
                "postgres_results": len(postgres_results) if isinstance(postgres_results, list) else 0,
                "qdrant_results": len(qdrant_results) if isinstance(qdrant_results, list) else 0,
                "hybrid_fusion_applied": len(postgres_results) > 0 and len(qdrant_results) > 0
            }
            
            logger.info("Memory search completed",
                       request_id=request_id,
                       results_count=len(formatted_results),
                       processing_time_ms=round(search_time * 1000, 2))
            
            return result
            
        except Exception as e:
            search_time = time.time() - search_start
            
            logger.error("Memory search failed",
                        request_id=request_id,
                        error=str(e),
                        processing_time_ms=round(search_time * 1000, 2))
            
            return {
                "results": [],
                "total_count": 0,
                "query": query,
                "processing_time_ms": round(search_time * 1000, 2),
                "similarity_threshold_used": threshold,
                "error": str(e)
            }
    
    async def _hybrid_fusion_ranking(
        self,
        postgres_results: List,
        qdrant_results: List,
        query_embedding: List[float],
        request_id: Optional[str] = None
    ) -> List[Tuple[Memory, float]]:
        """Combine and rank results from PostgreSQL and Qdrant using fusion scoring.
        
        Args:
            postgres_results: Results from PostgreSQL text search
            qdrant_results: Results from Qdrant vector search
            query_embedding: Query vector for additional scoring
            request_id: Request tracking ID
            
        Returns:
            Combined and ranked list of (Memory, score) tuples
        """
        try:
            # Combine results with fusion scoring
            memory_scores = {}
            
            # Score PostgreSQL results (text relevance)
            for i, memory in enumerate(postgres_results):
                # Rank-based scoring for text search
                text_score = 1.0 - (i / max(len(postgres_results), 1))
                memory_scores[memory.id] = {
                    "memory": memory,
                    "text_score": text_score,
                    "vector_score": 0.0,
                    "combined_score": text_score * 0.4  # 40% weight for text
                }
            
            # Score Qdrant results (vector similarity)
            for qdrant_result in qdrant_results:
                memory_id = UUID(qdrant_result["memory_id"])
                vector_score = qdrant_result["similarity_score"]
                
                if memory_id in memory_scores:
                    # Update existing entry
                    memory_scores[memory_id]["vector_score"] = vector_score
                    memory_scores[memory_id]["combined_score"] = (
                        memory_scores[memory_id]["text_score"] * 0.4 +
                        vector_score * 0.6  # 60% weight for vector similarity
                    )
                else:
                    # New entry from vector search
                    memory = await self.database.get_memory_by_id(memory_id)
                    if memory:
                        memory_scores[memory_id] = {
                            "memory": memory,
                            "text_score": 0.0,
                            "vector_score": vector_score,
                            "combined_score": vector_score * 0.6
                        }
            
            # Sort by combined score
            ranked_results = [
                (data["memory"], data["combined_score"])
                for data in memory_scores.values()
            ]
            ranked_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.debug("Hybrid fusion ranking completed",
                        request_id=request_id,
                        postgres_count=len(postgres_results),
                        qdrant_count=len(qdrant_results),
                        combined_count=len(ranked_results))
            
            return ranked_results
            
        except Exception as e:
            logger.error("Hybrid fusion ranking failed",
                        request_id=request_id,
                        error=str(e))
            
            # Fallback: just return PostgreSQL results with default scores
            return [(memory, 0.5) for memory in postgres_results[:10]]