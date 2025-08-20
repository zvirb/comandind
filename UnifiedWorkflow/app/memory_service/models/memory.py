"""SQLAlchemy models for memory storage with pgvector support."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Memory(Base):
    """Core memory storage model.
    
    Stores processed memory content with metadata and relationships.
    Optimized for fast retrieval and semantic search operations.
    """
    __tablename__ = "memories"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Content fields
    original_content = Column(Text, nullable=False, comment="Original unprocessed memory content")
    processed_content = Column(Text, nullable=False, comment="LLM-processed and refined memory content")
    summary = Column(Text, nullable=True, comment="Brief summary of memory content")
    
    # Metadata
    content_type = Column(String(50), nullable=False, default="text", comment="Type of memory content")
    source = Column(String(100), nullable=True, comment="Source of the memory (user, system, etc.)")
    tags = Column(Text, nullable=True, comment="JSON array of tags for categorization")
    
    # Processing metadata
    extraction_model = Column(String(100), nullable=True, comment="Model used for initial extraction")
    reconciliation_model = Column(String(100), nullable=True, comment="Model used for reconciliation")
    processing_version = Column(String(20), nullable=False, default="1.0", comment="Processing pipeline version")
    
    # Quality metrics
    confidence_score = Column(Float, nullable=True, comment="Confidence in memory extraction quality")
    relevance_score = Column(Float, nullable=True, comment="Assessed relevance score")
    consolidation_count = Column(Integer, nullable=False, default=1, comment="Number of times this memory was consolidated")
    
    # Temporal tracking
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=True, comment="Last time this memory was retrieved")
    access_count = Column(Integer, nullable=False, default=0, comment="Number of times accessed")
    
    # Relationships
    vectors = relationship("MemoryVector", back_populates="memory", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_memories_created_at_desc", created_at.desc()),
        Index("idx_memories_updated_at_desc", updated_at.desc()),
        Index("idx_memories_content_type", content_type),
        Index("idx_memories_source", source),
        Index("idx_memories_confidence_score", confidence_score),
        Index("idx_memories_access_count", access_count),
    )
    
    def __repr__(self):
        return f"<Memory(id={self.id}, content_type={self.content_type}, created_at={self.created_at})>"
    
    def to_dict(self) -> dict:
        """Convert memory to dictionary representation."""
        return {
            "id": str(self.id),
            "original_content": self.original_content,
            "processed_content": self.processed_content,
            "summary": self.summary,
            "content_type": self.content_type,
            "source": self.source,
            "tags": self.tags,
            "confidence_score": self.confidence_score,
            "relevance_score": self.relevance_score,
            "consolidation_count": self.consolidation_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count
        }


class MemoryVector(Base):
    """Vector embeddings for memory content with pgvector support.
    
    Stores high-dimensional vector representations of memory content
    for semantic similarity search and clustering operations.
    """
    __tablename__ = "memory_vectors"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    memory_id = Column(UUID(as_uuid=True), nullable=False, index=True, comment="Reference to parent memory")
    
    # Vector data - using pgvector for efficient similarity operations
    embedding = Column(Vector(1536), nullable=False, comment="High-dimensional vector embedding")
    
    # Vector metadata
    vector_type = Column(String(50), nullable=False, default="semantic", 
                        comment="Type of vector (semantic, keyword, hybrid)")
    model_name = Column(String(100), nullable=False, comment="Model used to generate the vector")
    model_version = Column(String(20), nullable=True, comment="Version of the embedding model")
    
    # Quality metrics
    embedding_quality = Column(Float, nullable=True, comment="Quality score of the embedding")
    dimensionality = Column(Integer, nullable=False, default=1536, comment="Vector dimensionality")
    
    # Processing metadata
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    memory = relationship("Memory", back_populates="vectors")
    
    # Indexes for vector operations
    __table_args__ = (
        Index("idx_memory_vectors_memory_id", memory_id),
        Index("idx_memory_vectors_vector_type", vector_type),
        Index("idx_memory_vectors_model_name", model_name),
        Index("idx_memory_vectors_generated_at_desc", generated_at.desc()),
        # Vector similarity index (will be created via migration)
    )
    
    def __repr__(self):
        return f"<MemoryVector(id={self.id}, memory_id={self.memory_id}, vector_type={self.vector_type})>"
    
    def to_dict(self) -> dict:
        """Convert vector to dictionary representation."""
        return {
            "id": str(self.id),
            "memory_id": str(self.memory_id),
            "vector_type": self.vector_type,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "embedding_quality": self.embedding_quality,
            "dimensionality": self.dimensionality,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }