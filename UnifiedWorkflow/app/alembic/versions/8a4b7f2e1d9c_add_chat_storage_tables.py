"""Add chat storage tables for messages and session summaries

Revision ID: 8a4b7f2e1d9c
Revises: 7f3e9d2c4b8a
Create Date: 2025-07-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8a4b7f2e1d9c'
down_revision = '6e8f9a0b1c2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add chat storage tables."""
    
    # Create chat_session_summaries table
    op.create_table('chat_session_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('session_id', sa.String(), nullable=False, index=True, unique=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        
        # Session metadata
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True),
        
        # Content summaries
        sa.Column('conversation_domain', sa.String(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('key_topics', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('decisions_made', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('user_preferences', postgresql.JSONB(), nullable=False, default=dict),
        
        # Technical details
        sa.Column('tools_used', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('plans_created', sa.Integer(), nullable=False, default=0),
        sa.Column('expert_questions_asked', sa.Integer(), nullable=False, default=0),
        
        # Quality metrics
        sa.Column('session_rating', sa.Float(), nullable=True),
        sa.Column('complexity_level', sa.String(), nullable=False, default='medium'),
        sa.Column('resolution_status', sa.String(), nullable=False, default='completed'),
        
        # Searchable content
        sa.Column('search_keywords', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('follow_up_suggested', sa.Boolean(), default=False),
        sa.Column('follow_up_tasks', postgresql.JSONB(), nullable=False, default=list),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('session_id', sa.String(), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        
        # Message content
        sa.Column('message_type', sa.String(), nullable=False),  # "human", "ai", "system"
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_order', sa.Integer(), nullable=False),
        
        # Context and metadata
        sa.Column('conversation_domain', sa.String(), nullable=True),
        sa.Column('tool_used', sa.String(), nullable=True),
        sa.Column('plan_step', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        
        # Vector database reference
        sa.Column('qdrant_point_id', sa.String(), nullable=True, index=True),
        sa.Column('embedding_model_used', sa.String(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_chat_summaries_user_domain', 'chat_session_summaries', ['user_id', 'conversation_domain'])
    op.create_index('idx_chat_summaries_started_at', 'chat_session_summaries', ['started_at'])
    op.create_index('idx_chat_summaries_search_keywords', 'chat_session_summaries', ['search_keywords'], postgresql_using='gin')
    
    op.create_index('idx_chat_messages_user_session', 'chat_messages', ['user_id', 'session_id'])
    op.create_index('idx_chat_messages_order', 'chat_messages', ['session_id', 'message_order'])
    op.create_index('idx_chat_messages_created_at', 'chat_messages', ['created_at'])


def downgrade() -> None:
    """Remove chat storage tables."""
    op.drop_table('chat_messages')
    op.drop_table('chat_session_summaries')