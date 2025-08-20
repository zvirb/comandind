"""add_agent_abstraction_layer_models

Revision ID: f3a8b9c4d7e2
Revises: b0f9ada0f772
Create Date: 2025-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f3a8b9c4d7e2'
down_revision: Union[str, Sequence[str], None] = 'b0f9ada0f772'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add Agent Abstraction Layer models."""
    
    # Create enums
    llm_provider_enum = sa.Enum('OPENAI', 'ANTHROPIC', 'GOOGLE', 'OLLAMA', name='llmprovider')
    llm_provider_enum.create(op.get_bind())
    
    agent_type_enum = sa.Enum(
        'PROJECT_MANAGER', 'RESEARCH_SPECIALIST', 'BUSINESS_ANALYST', 'TECHNICAL_EXPERT',
        'FINANCIAL_ADVISOR', 'CREATIVE_DIRECTOR', 'QUALITY_ASSURANCE', 'DATA_SCIENTIST',
        'PERSONAL_ASSISTANT', 'LEGAL_ADVISOR', 'MARKETING_SPECIALIST', 'OPERATIONS_MANAGER',
        name='agenttype'
    )
    agent_type_enum.create(op.get_bind())
    
    gpu_assignment_strategy_enum = sa.Enum('EXCLUSIVE', 'SHARED', 'AUTO', 'NONE', name='gpuassignmentstrategy')
    gpu_assignment_strategy_enum.create(op.get_bind())
    
    model_load_strategy_enum = sa.Enum('PRELOAD', 'ON_DEMAND', 'SHARED', name='modelloadstrategy')
    model_load_strategy_enum.create(op.get_bind())
    
    # Create agent_configurations table
    op.create_table(
        'agent_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_type', agent_type_enum, nullable=False),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('agent_description', sa.Text(), nullable=True),
        sa.Column('llm_provider', llm_provider_enum, nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('model_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('gpu_assignment', sa.Integer(), nullable=True),
        sa.Column('gpu_assignment_strategy', gpu_assignment_strategy_enum, nullable=False),
        sa.Column('model_load_strategy', model_load_strategy_enum, nullable=False),
        sa.Column('max_context_length', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('memory_limit_mb', sa.Integer(), nullable=True),
        sa.Column('token_budget_per_hour', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_requests', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_configurations_agent_type'), 'agent_configurations', ['agent_type'], unique=False)
    op.create_index(op.f('ix_agent_configurations_agent_name'), 'agent_configurations', ['agent_name'], unique=False)
    op.create_index(op.f('ix_agent_configurations_id'), 'agent_configurations', ['id'], unique=False)
    
    # Create agent_metrics table
    op.create_table(
        'agent_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_config_id', sa.Integer(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('total_tokens_consumed', sa.Integer(), nullable=False),
        sa.Column('total_processing_time_ms', sa.Integer(), nullable=False),
        sa.Column('average_response_time_ms', sa.Float(), nullable=True),
        sa.Column('success_rate_percent', sa.Float(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False),
        sa.Column('gpu_memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('cpu_usage_percent', sa.Float(), nullable=True),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_config_id'], ['agent_configurations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_metrics_agent_config_id'), 'agent_metrics', ['agent_config_id'], unique=False)
    op.create_index(op.f('ix_agent_metrics_id'), 'agent_metrics', ['id'], unique=False)
    
    # Create gpu_resource_allocations table
    op.create_table(
        'gpu_resource_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gpu_id', sa.Integer(), nullable=False),
        sa.Column('gpu_name', sa.String(length=255), nullable=False),
        sa.Column('gpu_memory_total_mb', sa.Float(), nullable=False),
        sa.Column('allocated_memory_mb', sa.Float(), nullable=False),
        sa.Column('available_memory_mb', sa.Float(), nullable=False),
        sa.Column('active_agent_count', sa.Integer(), nullable=False),
        sa.Column('utilization_percent', sa.Float(), nullable=True),
        sa.Column('temperature_celsius', sa.Float(), nullable=True),
        sa.Column('power_draw_watts', sa.Float(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('maintenance_mode', sa.Boolean(), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gpu_resource_allocations_gpu_id'), 'gpu_resource_allocations', ['gpu_id'], unique=False)
    op.create_index(op.f('ix_gpu_resource_allocations_id'), 'gpu_resource_allocations', ['id'], unique=False)
    
    # Create model_instances table
    op.create_table(
        'model_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('model_provider', llm_provider_enum, nullable=False),
        sa.Column('model_size_mb', sa.Float(), nullable=True),
        sa.Column('gpu_id', sa.Integer(), nullable=True),
        sa.Column('memory_allocated_mb', sa.Float(), nullable=True),
        sa.Column('reference_count', sa.Integer(), nullable=False),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('load_time_ms', sa.Integer(), nullable=True),
        sa.Column('is_loaded', sa.Boolean(), nullable=False),
        sa.Column('is_shared', sa.Boolean(), nullable=False),
        sa.Column('load_strategy', model_load_strategy_enum, nullable=False),
        sa.Column('loaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_instances_model_name'), 'model_instances', ['model_name'], unique=False)
    op.create_index(op.f('ix_model_instances_gpu_id'), 'model_instances', ['gpu_id'], unique=False)
    op.create_index(op.f('ix_model_instances_id'), 'model_instances', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - Remove Agent Abstraction Layer models."""
    
    # Drop tables in reverse order
    op.drop_index(op.f('ix_model_instances_id'), table_name='model_instances')
    op.drop_index(op.f('ix_model_instances_gpu_id'), table_name='model_instances')
    op.drop_index(op.f('ix_model_instances_model_name'), table_name='model_instances')
    op.drop_table('model_instances')
    
    op.drop_index(op.f('ix_gpu_resource_allocations_id'), table_name='gpu_resource_allocations')
    op.drop_index(op.f('ix_gpu_resource_allocations_gpu_id'), table_name='gpu_resource_allocations')
    op.drop_table('gpu_resource_allocations')
    
    op.drop_index(op.f('ix_agent_metrics_id'), table_name='agent_metrics')
    op.drop_index(op.f('ix_agent_metrics_agent_config_id'), table_name='agent_metrics')
    op.drop_table('agent_metrics')
    
    op.drop_index(op.f('ix_agent_configurations_id'), table_name='agent_configurations')
    op.drop_index(op.f('ix_agent_configurations_agent_name'), table_name='agent_configurations')
    op.drop_index(op.f('ix_agent_configurations_agent_type'), table_name='agent_configurations')
    op.drop_table('agent_configurations')
    
    # Drop enums
    sa.Enum(name='modelloadstrategy').drop(op.get_bind())
    sa.Enum(name='gpuassignmentstrategy').drop(op.get_bind())
    sa.Enum(name='agenttype').drop(op.get_bind())
    sa.Enum(name='llmprovider').drop(op.get_bind())