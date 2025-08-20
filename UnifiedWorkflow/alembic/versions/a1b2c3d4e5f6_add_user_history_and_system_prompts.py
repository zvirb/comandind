"""Add user history summary and system prompt tables

Revision ID: a1b2c3d4e5f6
Revises: 8a4b7f2e1d9c
Create Date: 2025-07-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'c3d7a3a4d59c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user history summary and system prompt tables."""
    
    # Create user_history_summaries table
    op.create_table('user_history_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        
        # Summary metadata
        sa.Column('summary_period', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        
        # Aggregated statistics
        sa.Column('total_sessions', sa.Integer(), nullable=False, default=0),
        sa.Column('total_messages', sa.Integer(), nullable=False, default=0),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True),
        
        # Content analysis (JSONB fields)
        sa.Column('primary_domains', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('frequent_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('key_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('skill_areas', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        
        # Behavioral patterns
        sa.Column('preferred_tools', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('interaction_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('complexity_preference', sa.String(), nullable=False, default='medium'),
        
        # Summary content
        sa.Column('executive_summary', sa.Text(), nullable=False),
        sa.Column('important_context', sa.Text(), nullable=True),
        sa.Column('recurring_themes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        
        # Quality metrics
        sa.Column('engagement_score', sa.Float(), nullable=True),
        sa.Column('satisfaction_indicators', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create system_prompts table
    op.create_table('system_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        
        # Prompt identification
        sa.Column('prompt_key', sa.String(), nullable=False, index=True),
        sa.Column('prompt_category', sa.String(), nullable=False, index=True),
        sa.Column('prompt_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Prompt content
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Metadata
        sa.Column('is_factory_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        
        # Usage tracking
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        
        # Performance metrics
        sa.Column('average_satisfaction', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'prompt_key', name='_user_prompt_key_uc')
    )


def downgrade() -> None:
    """Remove user history summary and system prompt tables."""
    op.drop_table('system_prompts')
    op.drop_table('user_history_summaries')