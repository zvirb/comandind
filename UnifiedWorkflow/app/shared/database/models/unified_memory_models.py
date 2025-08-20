"""
Unified Memory Store Models for Simple Chat Context Awareness

Database models for the unified memory integration that enables context-aware
Simple Chat with RAG capabilities and cross-session continuity.

FIXED VERSION: Removed UnifiedMemoryVector class to resolve SQLAlchemy metadata conflict
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, Float, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from shared.utils.database_setup import Base


class ChatModeSession(Base):
    """
    Unified session management for all chat modes with context continuity.
    """
    __tablename__ = 'chat_mode_sessions'
    __table_args__ = (
        Index('idx_chat_mode_sessions_user_mode', 'user_id', 'chat_mode'),
        Index('idx_chat_mode_sessions_active', 'is_active', 'created_at'),
        Index('idx_chat_mode_sessions_config_gin', 'configuration', postgresql_using='gin'),
        Index('idx_chat_mode_sessions_metadata_gin', 'session_metadata', postgresql_using='gin'),
        {'extend_existing': True}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    session_id = Column(String, nullable=False, unique=True, index=True)
    chat_mode = Column(String(50), nullable=False, index=True)
    configuration = Column(JSONB, nullable=False, default={})
    unified_memory_id = Column(UUID(as_uuid=True), nullable=True)  # Future: link to consensus memory
    parent_session_id = Column(String, nullable=True)  # For session continuity
    is_active = Column(Boolean, nullable=False, default=True)
    session_metadata = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    simple_chat_contexts = relationship("SimpleChatContext", back_populates="session")
    router_decisions = relationship("RouterDecisionLog", back_populates="session")
    
    def __repr__(self):
        return f"<ChatModeSession(session_id='{self.session_id}', mode='{self.chat_mode}', user_id={self.user_id})>"


class RouterDecisionLog(Base):
    """
    Smart Router decision tracking for learning and analytics.
    """
    __tablename__ = 'router_decision_log'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, ForeignKey('chat_mode_sessions.session_id'), nullable=False, index=True)
    user_request = Column(Text, nullable=False)
    routing_decision = Column(JSONB, nullable=False)
    tools_invoked = Column(JSONB, nullable=False, default=[])
    complexity_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    processing_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_details = Column(JSONB, nullable=True)
    blackboard_event_id = Column(UUID(as_uuid=True), nullable=True)  # Future: link to blackboard events
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    session = relationship("ChatModeSession", back_populates="router_decisions")
    
    # Indexes for analytics and performance
    __table_args__ = (
        Index('idx_router_decision_performance', 'processing_time_ms', 'complexity_score'),
        Index('idx_router_decision_tools_gin', 'tools_invoked', postgresql_using='gin'),
        Index('idx_router_decision_routing_gin', 'routing_decision', postgresql_using='gin'),
        Index('idx_router_decision_success', 'success', 'created_at'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<RouterDecisionLog(session_id='{self.session_id}', success={self.success})>"


class SimpleChatContext(Base):
    """
    Simple Chat context storage for session-specific and persistent memories.
    """
    __tablename__ = 'simple_chat_context'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, ForeignKey('chat_mode_sessions.session_id'), nullable=False, index=True)
    context_key = Column(String, nullable=False)
    context_value = Column(JSONB, nullable=False)
    context_type = Column(String(50), nullable=False, default='conversation', index=True)
    access_level = Column(String(20), nullable=False, default='private')  # private, shared, public
    priority = Column(Integer, nullable=False, default=1)
    version = Column(Integer, nullable=False, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_persistent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    session = relationship("ChatModeSession", back_populates="simple_chat_contexts")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('session_id', 'context_key', name='_session_context_key_uc'),
        Index('idx_simple_chat_context_type', 'context_type', 'access_level'),
        Index('idx_simple_chat_context_expiry', 'expires_at'),
        Index('idx_simple_chat_context_value_gin', 'context_value', postgresql_using='gin'),
        Index('idx_simple_chat_context_priority', 'priority', 'version'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<SimpleChatContext(session_id='{self.session_id}', key='{self.context_key}')>"


class CrossServiceMemorySync(Base):
    """
    Cross-service memory synchronization for coordinated context sharing.
    """
    __tablename__ = 'cross_service_memory_sync'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_session_id = Column(String, ForeignKey('chat_mode_sessions.session_id'), nullable=False, index=True)
    target_session_id = Column(String, ForeignKey('chat_mode_sessions.session_id'), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False)  # context_transfer, knowledge_share, state_sync
    sync_status = Column(String(20), nullable=False, default='pending')  # pending, in_progress, completed, failed
    data_transferred = Column(JSONB, nullable=False)
    conflict_resolution = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    source_session = relationship("ChatModeSession", foreign_keys=[source_session_id])
    target_session = relationship("ChatModeSession", foreign_keys=[target_session_id])
    
    # Indexes for sync management
    __table_args__ = (
        Index('idx_cross_service_sync_status', 'sync_status', 'created_at'),
        Index('idx_cross_service_sync_type', 'sync_type'),
        Index('idx_cross_service_sync_data_gin', 'data_transferred', postgresql_using='gin'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<CrossServiceMemorySync(type='{self.sync_type}', status='{self.sync_status}')>"