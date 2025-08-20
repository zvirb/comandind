"""Database service for PostgreSQL operations with async SQLAlchemy.

Provides high-performance database operations for memory storage,
retrieval, and management with connection pooling and optimization.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

import structlog
from sqlalchemy import create_engine, func, text, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

try:
    from ..models.memory import Memory, MemoryVector, Base
except ImportError:
    # Fallback for module execution in Docker
    from models.memory import Memory, MemoryVector, Base

logger = structlog.get_logger(__name__)


class DatabaseService:
    """Async PostgreSQL database service for memory operations.
    
    Handles all database operations with connection pooling,
    transaction management, and performance optimization.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 30,
        echo: bool = False
    ):
        """Initialize database service.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            echo: Enable SQL query logging
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=echo,
            future=True,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
        )
        
        # Create session factory
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Initialized database service", 
                   pool_size=pool_size,
                   max_overflow=max_overflow)
    
    async def initialize(self) -> None:
        """Initialize database connection and create tables if needed."""
        try:
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info("Database connection established")
            
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()
        logger.info("Database connections closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and return statistics."""
        try:
            async with self.SessionLocal() as session:
                # Test basic connectivity
                result = await session.execute(text("SELECT 1"))
                
                # Get memory count
                memory_count_result = await session.execute(
                    select(func.count(Memory.id))
                )
                memory_count = memory_count_result.scalar()
                
                # Get vector count
                vector_count_result = await session.execute(
                    select(func.count(MemoryVector.id))
                )
                vector_count = vector_count_result.scalar()
                
                # Get pool status
                pool = self.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalid": pool.invalid()
                }
                
                return {
                    "healthy": True,
                    "memory_count": memory_count,
                    "vector_count": vector_count,
                    "connection_pool": pool_status
                }
                
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "healthy": False,
                "error": str(e),
                "connection_pool": {"status": "unknown"}
            }
    
    async def create_memory(
        self,
        original_content: str,
        processed_content: str,
        summary: Optional[str] = None,
        content_type: str = "text",
        source: Optional[str] = None,
        tags: Optional[str] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """Create a new memory record.
        
        Args:
            original_content: Raw memory content
            processed_content: LLM-processed content
            summary: Optional summary
            content_type: Type of content
            source: Content source
            tags: JSON string of tags
            confidence_score: Processing confidence
            metadata: Additional metadata
            
        Returns:
            Created Memory object
        """
        try:
            async with self.SessionLocal() as session:
                memory = Memory(
                    original_content=original_content,
                    processed_content=processed_content,
                    summary=summary,
                    content_type=content_type,
                    source=source,
                    tags=tags,
                    confidence_score=confidence_score,
                    extraction_model=metadata.get('extraction_model') if metadata else None,
                    reconciliation_model=metadata.get('reconciliation_model') if metadata else None
                )
                
                session.add(memory)
                await session.commit()
                await session.refresh(memory)
                
                logger.debug("Created memory record", 
                           memory_id=memory.id,
                           content_type=content_type,
                           content_length=len(original_content))
                
                return memory
                
        except IntegrityError as e:
            logger.error("Memory creation failed - integrity error", 
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to create memory", error=str(e))
            raise
    
    async def create_memory_vector(
        self,
        memory_id: UUID,
        embedding: List[float],
        vector_type: str = "semantic",
        model_name: str = "llama3.2:3b",
        model_version: Optional[str] = None,
        embedding_quality: Optional[float] = None
    ) -> MemoryVector:
        """Create a vector embedding for a memory.
        
        Args:
            memory_id: Associated memory ID
            embedding: Vector embedding
            vector_type: Type of vector
            model_name: Model used for embedding
            model_version: Model version
            embedding_quality: Quality score
            
        Returns:
            Created MemoryVector object
        """
        try:
            async with self.SessionLocal() as session:
                vector = MemoryVector(
                    memory_id=memory_id,
                    embedding=embedding,
                    vector_type=vector_type,
                    model_name=model_name,
                    model_version=model_version,
                    embedding_quality=embedding_quality,
                    dimensionality=len(embedding)
                )
                
                session.add(vector)
                await session.commit()
                await session.refresh(vector)
                
                logger.debug("Created memory vector", 
                           vector_id=vector.id,
                           memory_id=memory_id,
                           dimensions=len(embedding))
                
                return vector
                
        except IntegrityError as e:
            logger.error("Memory vector creation failed - integrity error", 
                        memory_id=memory_id, 
                        error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to create memory vector", 
                        memory_id=memory_id,
                        error=str(e))
            raise
    
    async def get_memory_by_id(self, memory_id: UUID) -> Optional[Memory]:
        """Get a memory by ID with vectors loaded.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            Memory object or None if not found
        """
        try:
            async with self.SessionLocal() as session:
                result = await session.execute(
                    select(Memory)
                    .options(selectinload(Memory.vectors))
                    .where(Memory.id == memory_id)
                )
                
                memory = result.scalar_one_or_none()
                
                if memory:
                    # Update access tracking
                    memory.last_accessed = datetime.utcnow()
                    memory.access_count += 1
                    await session.commit()
                
                return memory
                
        except Exception as e:
            logger.error("Failed to get memory by ID", 
                        memory_id=memory_id,
                        error=str(e))
            return None
    
    async def search_memories_by_content(
        self,
        query: str,
        limit: int = 10,
        content_type_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Memory]:
        """Search memories using PostgreSQL text search.
        
        Args:
            query: Search query
            limit: Maximum results
            content_type_filter: Filter by content type
            source_filter: Filter by source
            date_from: Search from date
            date_to: Search to date
            
        Returns:
            List of matching Memory objects
        """
        try:
            async with self.SessionLocal() as session:
                # Build base query with text search (SQL injection safe)
                # Escape special characters for ILIKE
                escaped_query = query.replace('%', '\\%').replace('_', '\\_').replace('[', '\\[')
                search_pattern = f"%{escaped_query}%"
                query_stmt = select(Memory).where(
                    or_(
                        Memory.processed_content.ilike(search_pattern),
                        Memory.summary.ilike(search_pattern),
                        Memory.original_content.ilike(search_pattern)
                    )
                )
                
                # Apply filters
                conditions = []
                
                if content_type_filter:
                    conditions.append(Memory.content_type == content_type_filter)
                
                if source_filter:
                    conditions.append(Memory.source == source_filter)
                
                if date_from:
                    conditions.append(Memory.created_at >= date_from)
                
                if date_to:
                    conditions.append(Memory.created_at <= date_to)
                
                if conditions:
                    query_stmt = query_stmt.where(and_(*conditions))
                
                # Order by relevance (access count, then creation date)
                query_stmt = query_stmt.order_by(
                    Memory.access_count.desc(),
                    Memory.created_at.desc()
                ).limit(limit)
                
                result = await session.execute(query_stmt)
                memories = result.scalars().all()
                
                logger.debug("PostgreSQL text search completed", 
                           query=query,
                           results_count=len(memories),
                           limit=limit)
                
                return list(memories)
                
        except Exception as e:
            logger.error("Failed to search memories by content", 
                        query=query,
                        error=str(e))
            return []
    
    async def find_similar_memories(
        self,
        embedding: List[float],
        similarity_threshold: float = 0.75,
        limit: int = 5,
        exclude_memory_id: Optional[UUID] = None
    ) -> List[Tuple[Memory, float]]:
        """Find similar memories using pgvector cosine similarity.
        
        Args:
            embedding: Query vector
            similarity_threshold: Minimum similarity score
            limit: Maximum results
            exclude_memory_id: Memory ID to exclude from results
            
        Returns:
            List of (Memory, similarity_score) tuples
        """
        try:
            async with self.SessionLocal() as session:
                # Build similarity query using pgvector
                query_stmt = (
                    select(
                        Memory,
                        MemoryVector.embedding.cosine_distance(embedding).label('distance')
                    )
                    .join(MemoryVector, Memory.id == MemoryVector.memory_id)
                    .where(
                        MemoryVector.embedding.cosine_distance(embedding) < (1 - similarity_threshold)
                    )
                )
                
                if exclude_memory_id:
                    query_stmt = query_stmt.where(Memory.id != exclude_memory_id)
                
                query_stmt = query_stmt.order_by('distance').limit(limit)
                
                result = await session.execute(query_stmt)
                rows = result.all()
                
                # Convert distance to similarity score
                similar_memories = []
                for memory, distance in rows:
                    similarity_score = 1 - distance  # Convert distance to similarity
                    similar_memories.append((memory, similarity_score))
                
                logger.debug("pgvector similarity search completed", 
                           results_count=len(similar_memories),
                           threshold=similarity_threshold,
                           limit=limit)
                
                return similar_memories
                
        except Exception as e:
            logger.error("Failed to find similar memories with pgvector", 
                        threshold=similarity_threshold,
                        error=str(e))
            return []
    
    async def update_memory_access(self, memory_id: UUID) -> None:
        """Update memory access tracking.
        
        Args:
            memory_id: Memory identifier
        """
        try:
            async with self.SessionLocal() as session:
                await session.execute(
                    text("""
                        UPDATE memories 
                        SET last_accessed = NOW(), access_count = access_count + 1 
                        WHERE id = :memory_id
                    """),
                    {"memory_id": memory_id}
                )
                await session.commit()
                
        except Exception as e:
            logger.warning("Failed to update memory access", 
                          memory_id=memory_id,
                          error=str(e))
    
    async def delete_memory(self, memory_id: UUID) -> bool:
        """Delete a memory and its vectors.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            True if deleted, False if not found
        """
        try:
            async with self.SessionLocal() as session:
                # Get memory to delete
                result = await session.execute(
                    select(Memory).where(Memory.id == memory_id)
                )
                memory = result.scalar_one_or_none()
                
                if not memory:
                    return False
                
                # Delete memory (vectors will cascade)
                await session.delete(memory)
                await session.commit()
                
                logger.info("Deleted memory", memory_id=memory_id)
                return True
                
        except Exception as e:
            logger.error("Failed to delete memory", 
                        memory_id=memory_id,
                        error=str(e))
            return False
    
    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Get database statistics for monitoring.
        
        Returns:
            Statistics dictionary
        """
        try:
            async with self.SessionLocal() as session:
                # Memory statistics
                memory_stats = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_memories,
                            COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as memories_24h,
                            COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as memories_7d,
                            AVG(confidence_score) as avg_confidence,
                            MAX(access_count) as max_access_count
                        FROM memories
                    """)
                )
                
                memory_row = memory_stats.fetchone()
                
                # Vector statistics  
                vector_stats = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_vectors,
                            AVG(embedding_quality) as avg_quality
                        FROM memory_vectors
                    """)
                )
                
                vector_row = vector_stats.fetchone()
                
                return {
                    "total_memories": memory_row[0] if memory_row else 0,
                    "memories_24h": memory_row[1] if memory_row else 0,
                    "memories_7d": memory_row[2] if memory_row else 0,
                    "avg_confidence": float(memory_row[3]) if memory_row and memory_row[3] else 0.0,
                    "max_access_count": memory_row[4] if memory_row else 0,
                    "total_vectors": vector_row[0] if vector_row else 0,
                    "avg_embedding_quality": float(vector_row[1]) if vector_row and vector_row[1] else 0.0
                }
                
        except Exception as e:
            logger.error("Failed to get memory statistics", error=str(e))
            return {}