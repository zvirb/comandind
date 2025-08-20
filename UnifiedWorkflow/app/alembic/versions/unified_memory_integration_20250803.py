"""Add unified memory store integration for Simple Chat and Smart Router

Revision ID: unified_memory_integration_20250803
Revises: e7f8a9b0c1d2
Create Date: 2025-08-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'unified_memory_integration_20250803'
down_revision: Union[str, Sequence[str], None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unified memory store integration tables."""
    
    # Create chat_mode_sessions table for unified session management
    op.create_table('chat_mode_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('chat_mode', sa.String(length=50), nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('unified_memory_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_session_id', sa.String(), nullable=True),  # For session continuity
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['unified_memory_id'], ['consensus_memory_nodes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create router_decision_log table for Smart Router tracking
    op.create_table('router_decision_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_request', sa.Text(), nullable=False),
        sa.Column('routing_decision', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('tools_invoked', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default='[]'),
        sa.Column('complexity_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('blackboard_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_mode_sessions.session_id'], ),
        sa.ForeignKeyConstraint(['blackboard_event_id'], ['blackboard_events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create simple_chat_context table for Simple Chat state management
    op.create_table('simple_chat_context',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('context_key', sa.String(), nullable=False),
        sa.Column('context_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('context_type', sa.String(length=50), nullable=False, default='conversation'),
        sa.Column('access_level', sa.String(length=20), nullable=False, default='private'),  # private, shared, public
        sa.Column('priority', sa.Integer(), nullable=False, default=1),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_persistent', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_mode_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'context_key', name='_session_context_key_uc')
    )
    
    # Create unified_memory_vectors table for RAG integration
    op.create_table('unified_memory_vectors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vector_type', sa.String(length=50), nullable=False),  # query, response, context, knowledge
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('qdrant_point_id', sa.String(), nullable=True),  # Reference to Qdrant point
        sa.Column('vector_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default='{}'),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['memory_node_id'], ['consensus_memory_nodes.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['chat_mode_sessions.session_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create cross_service_memory_sync table for memory synchronization
    op.create_table('cross_service_memory_sync',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_session_id', sa.String(), nullable=False),
        sa.Column('target_session_id', sa.String(), nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),  # context_transfer, knowledge_share, state_sync
        sa.Column('sync_status', sa.String(length=20), nullable=False, default='pending'),  # pending, in_progress, completed, failed
        sa.Column('data_transferred', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('conflict_resolution', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['source_session_id'], ['chat_mode_sessions.session_id'], ),
        sa.ForeignKeyConstraint(['target_session_id'], ['chat_mode_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for chat_mode_sessions
    op.create_index('idx_chat_mode_sessions_user_mode', 'chat_mode_sessions', ['user_id', 'chat_mode'])
    op.create_index('idx_chat_mode_sessions_active', 'chat_mode_sessions', ['is_active', 'created_at'])
    op.create_index('idx_chat_mode_sessions_config_gin', 'chat_mode_sessions', ['configuration'], postgresql_using='gin')
    op.create_index('idx_chat_mode_sessions_metadata_gin', 'chat_mode_sessions', ['session_metadata'], postgresql_using='gin')
    op.create_index(op.f('ix_chat_mode_sessions_user_id'), 'chat_mode_sessions', ['user_id'])
    op.create_index(op.f('ix_chat_mode_sessions_session_id'), 'chat_mode_sessions', ['session_id'])
    op.create_index(op.f('ix_chat_mode_sessions_chat_mode'), 'chat_mode_sessions', ['chat_mode'])
    
    # Create indexes for router_decision_log
    op.create_index('idx_router_decision_performance', 'router_decision_log', ['processing_time_ms', 'complexity_score'])
    op.create_index('idx_router_decision_tools_gin', 'router_decision_log', ['tools_invoked'], postgresql_using='gin')
    op.create_index('idx_router_decision_routing_gin', 'router_decision_log', ['routing_decision'], postgresql_using='gin')
    op.create_index('idx_router_decision_success', 'router_decision_log', ['success', 'created_at'])
    op.create_index(op.f('ix_router_decision_log_session_id'), 'router_decision_log', ['session_id'])
    op.create_index(op.f('ix_router_decision_log_created_at'), 'router_decision_log', ['created_at'])
    
    # Create indexes for simple_chat_context
    op.create_index('idx_simple_chat_context_type', 'simple_chat_context', ['context_type', 'access_level'])
    op.create_index('idx_simple_chat_context_expiry', 'simple_chat_context', ['expires_at'])
    op.create_index('idx_simple_chat_context_value_gin', 'simple_chat_context', ['context_value'], postgresql_using='gin')
    op.create_index('idx_simple_chat_context_priority', 'simple_chat_context', ['priority', 'version'])
    op.create_index(op.f('ix_simple_chat_context_session_id'), 'simple_chat_context', ['session_id'])
    op.create_index(op.f('ix_simple_chat_context_context_type'), 'simple_chat_context', ['context_type'])
    
    # Create indexes for unified_memory_vectors
    op.create_index('idx_unified_memory_vectors_type', 'unified_memory_vectors', ['vector_type', 'user_id'])
    op.create_index('idx_unified_memory_vectors_relevance', 'unified_memory_vectors', ['relevance_score'])
    op.create_index('idx_unified_memory_vectors_metadata_gin', 'unified_memory_vectors', ['vector_metadata'], postgresql_using='gin')
    op.create_index('idx_unified_memory_vectors_qdrant', 'unified_memory_vectors', ['qdrant_point_id'])
    op.create_index(op.f('ix_unified_memory_vectors_memory_node_id'), 'unified_memory_vectors', ['memory_node_id'])
    op.create_index(op.f('ix_unified_memory_vectors_session_id'), 'unified_memory_vectors', ['session_id'])
    op.create_index(op.f('ix_unified_memory_vectors_user_id'), 'unified_memory_vectors', ['user_id'])
    
    # Create indexes for cross_service_memory_sync
    op.create_index('idx_cross_service_sync_status', 'cross_service_memory_sync', ['sync_status', 'created_at'])
    op.create_index('idx_cross_service_sync_type', 'cross_service_memory_sync', ['sync_type'])
    op.create_index('idx_cross_service_sync_data_gin', 'cross_service_memory_sync', ['data_transferred'], postgresql_using='gin')
    op.create_index(op.f('ix_cross_service_memory_sync_source_session_id'), 'cross_service_memory_sync', ['source_session_id'])
    op.create_index(op.f('ix_cross_service_memory_sync_target_session_id'), 'cross_service_memory_sync', ['target_session_id'])


def downgrade() -> None:
    """Remove unified memory store integration tables."""
    
    # Drop tables in reverse order
    op.drop_table('cross_service_memory_sync')
    op.drop_table('unified_memory_vectors')
    op.drop_table('simple_chat_context')
    op.drop_table('router_decision_log')
    op.drop_table('chat_mode_sessions')