"""Add Helios Multi-Agent framework database extension

Revision ID: e7f8a9b0c1d2
Revises: c4d5e6f7a8b9
Create Date: 2025-08-02 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Helios Multi-Agent framework tables."""
    
    # Create enums for Helios Multi-Agent framework
    op.execute("CREATE TYPE agentstatus AS ENUM ('online', 'working', 'idle', 'offline', 'error', 'overloaded')")
    op.execute("CREATE TYPE taskdelegationstatus AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled', 'timeout')")
    op.execute("CREATE TYPE conversationphase AS ENUM ('initialization', 'ingestion', 'planning', 'delegation', 'processing', 'synthesis', 'review', 'completion')")
    op.execute("CREATE TYPE gpuallocationstatus AS ENUM ('active', 'idle', 'overloaded', 'error', 'maintenance')")
    op.execute("CREATE TYPE modelprovider AS ENUM ('ollama', 'openai', 'anthropic', 'google', 'huggingface')")
    
    # Create gpu_resources table
    op.create_table('gpu_resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gpu_name', sa.String(length=100), nullable=False),
        sa.Column('gpu_model', sa.String(length=100), nullable=False),
        sa.Column('total_memory_mb', sa.Integer(), nullable=False),
        sa.Column('compute_capability', sa.String(length=20), nullable=False),
        sa.Column('cuda_cores', sa.Integer(), nullable=True),
        sa.Column('base_clock_mhz', sa.Integer(), nullable=True),
        sa.Column('boost_clock_mhz', sa.Integer(), nullable=True),
        sa.Column('memory_bandwidth_gbps', sa.Float(), nullable=True),
        sa.Column('power_limit_watts', sa.Integer(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('maintenance_mode', sa.Boolean(), nullable=False),
        sa.Column('max_concurrent_agents', sa.Integer(), nullable=False),
        sa.Column('reserved_memory_mb', sa.Integer(), nullable=False),
        sa.Column('current_utilization_percent', sa.Float(), nullable=False),
        sa.Column('current_memory_used_mb', sa.Integer(), nullable=False),
        sa.Column('current_temperature_c', sa.Float(), nullable=True),
        sa.Column('current_power_usage_watts', sa.Float(), nullable=True),
        sa.Column('average_utilization_24h', sa.Float(), nullable=True),
        sa.Column('peak_utilization_24h', sa.Float(), nullable=True),
        sa.Column('uptime_hours', sa.Float(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create agent_configurations table
    op.create_table('agent_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('agent_role', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('assigned_llm', sa.String(length=100), nullable=False),
        sa.Column('model_provider', sa.Enum('ollama', 'openai', 'anthropic', 'google', 'huggingface', name='modelprovider'), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('gpu_assignment', sa.Integer(), nullable=True),
        sa.Column('allocated_memory_mb', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_requests', sa.Integer(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('specializations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False),
        sa.Column('retry_attempts', sa.Integer(), nullable=False),
        sa.Column('priority_level', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_global_default', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'agent_id', name='_user_agent_config_uc')
    )
    
    # Create agent_profiles table
    op.create_table('agent_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('profile_image_url', sa.String(length=500), nullable=True),
        sa.Column('avatar_style', sa.String(length=50), nullable=False),
        sa.Column('expertise_areas', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('skill_ratings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('typical_response_time', sa.Integer(), nullable=True),
        sa.Column('communication_style', sa.String(length=50), nullable=False),
        sa.Column('interaction_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('personality_traits', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('current_status', sa.Enum('online', 'working', 'idle', 'offline', 'error', 'overloaded', name='agentstatus'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_workload', sa.Integer(), nullable=False),
        sa.Column('max_workload', sa.Integer(), nullable=False),
        sa.Column('total_tasks_completed', sa.Integer(), nullable=False),
        sa.Column('average_response_time', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('user_satisfaction_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['config_id'], ['agent_configurations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create gpu_allocations table
    op.create_table('gpu_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gpu_id', sa.Integer(), nullable=False),
        sa.Column('agent_config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('allocated_memory_mb', sa.Integer(), nullable=False),
        sa.Column('reserved_memory_mb', sa.Integer(), nullable=False),
        sa.Column('priority_level', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('active', 'idle', 'overloaded', 'error', 'maintenance', name='gpuallocationstatus'), nullable=False),
        sa.Column('current_memory_usage_mb', sa.Integer(), nullable=False),
        sa.Column('current_utilization_percent', sa.Float(), nullable=False),
        sa.Column('average_utilization_percent', sa.Float(), nullable=True),
        sa.Column('total_inference_time_seconds', sa.Float(), nullable=False),
        sa.Column('total_requests_processed', sa.Integer(), nullable=False),
        sa.Column('last_request_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('allocated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_config_id'], ['agent_configurations.id'], ),
        sa.ForeignKeyConstraint(['gpu_id'], ['gpu_resources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_config_id', name='_agent_gpu_allocation_uc')
    )
    
    # Create task_delegations table
    op.create_table('task_delegations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('pm_agent_id', sa.String(length=50), nullable=False),
        sa.Column('target_agent_id', sa.String(length=50), nullable=False),
        sa.Column('agent_role', sa.String(length=100), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('delegation_directive', sa.Text(), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('priority_level', sa.Integer(), nullable=False),
        sa.Column('context_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expected_deliverables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'failed', 'cancelled', 'timeout', name='taskdelegationstatus'), nullable=False),
        sa.Column('progress_percentage', sa.Integer(), nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('blackboard_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('consensus_node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['blackboard_event_id'], ['blackboard_events.id'], ),
        sa.ForeignKeyConstraint(['consensus_node_id'], ['consensus_memory_nodes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create agent_responses table
    op.create_table('agent_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_delegation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('response_type', sa.String(length=50), nullable=False),
        sa.Column('response_format', sa.String(length=20), nullable=False),
        sa.Column('key_findings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('concerns_raised', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('deliverables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('references', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('has_been_validated', sa.Boolean(), nullable=False),
        sa.Column('validation_feedback', sa.Text(), nullable=True),
        sa.Column('processing_time_seconds', sa.Float(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('blackboard_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['blackboard_event_id'], ['blackboard_events.id'], ),
        sa.ForeignKeyConstraint(['task_delegation_id'], ['task_delegations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create task_synthesis table
    op.create_table('task_synthesis',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('synthesis_type', sa.String(length=50), nullable=False),
        sa.Column('synthesizer_agent_id', sa.String(length=50), nullable=False),
        sa.Column('source_task_delegations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source_agent_responses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('contributing_agents', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('synthesized_response', sa.Text(), nullable=False),
        sa.Column('key_conclusions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('consolidated_recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('areas_of_consensus', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('areas_of_disagreement', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('synthesis_confidence', sa.Float(), nullable=False),
        sa.Column('completeness_score', sa.Float(), nullable=False),
        sa.Column('coherence_score', sa.Float(), nullable=False),
        sa.Column('synthesis_time_seconds', sa.Float(), nullable=False),
        sa.Column('total_tokens_processed', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('user_satisfaction_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('consensus_node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['consensus_node_id'], ['consensus_memory_nodes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create multi_agent_conversations table
    op.create_table('multi_agent_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('conversation_title', sa.String(length=200), nullable=False),
        sa.Column('conversation_description', sa.Text(), nullable=True),
        sa.Column('conversation_type', sa.String(length=50), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('current_phase', sa.Enum('initialization', 'ingestion', 'planning', 'delegation', 'processing', 'synthesis', 'review', 'completion', name='conversationphase'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('participating_agents', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('coordinator_agent_id', sa.String(length=50), nullable=False),
        sa.Column('total_agents', sa.Integer(), nullable=False),
        sa.Column('active_agents', sa.Integer(), nullable=False),
        sa.Column('total_tasks_delegated', sa.Integer(), nullable=False),
        sa.Column('tasks_completed', sa.Integer(), nullable=False),
        sa.Column('total_agent_responses', sa.Integer(), nullable=False),
        sa.Column('synthesis_count', sa.Integer(), nullable=False),
        sa.Column('total_processing_time_seconds', sa.Float(), nullable=False),
        sa.Column('average_response_time_seconds', sa.Float(), nullable=True),
        sa.Column('total_tokens_used', sa.Integer(), nullable=True),
        sa.Column('overall_satisfaction_score', sa.Float(), nullable=True),
        sa.Column('completion_status', sa.String(length=20), nullable=False),
        sa.Column('final_outcome', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create agent_participations table
    op.create_table('agent_participations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(length=50), nullable=False),
        sa.Column('agent_role', sa.String(length=100), nullable=False),
        sa.Column('participation_type', sa.String(length=50), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_contribution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_currently_active', sa.Boolean(), nullable=False),
        sa.Column('total_contributions', sa.Integer(), nullable=False),
        sa.Column('tasks_assigned', sa.Integer(), nullable=False),
        sa.Column('tasks_completed', sa.Integer(), nullable=False),
        sa.Column('responses_provided', sa.Integer(), nullable=False),
        sa.Column('average_response_time_seconds', sa.Float(), nullable=True),
        sa.Column('total_processing_time_seconds', sa.Float(), nullable=False),
        sa.Column('contribution_quality_score', sa.Float(), nullable=True),
        sa.Column('current_status', sa.Enum('online', 'working', 'idle', 'offline', 'error', 'overloaded', name='agentstatus'), nullable=False),
        sa.Column('current_workload', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['multi_agent_conversations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', 'agent_id', name='_conversation_agent_participation_uc')
    )
    
    # Create load_balancing_rules table
    op.create_table('load_balancing_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('thresholds', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('weights', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('applicable_agent_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('applicable_model_providers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority_level', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('times_applied', sa.Integer(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('last_applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_name')
    )
    
    # Create resource_constraints table
    op.create_table('resource_constraints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_provider', sa.Enum('ollama', 'openai', 'anthropic', 'google', 'huggingface', name='modelprovider'), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('min_memory_mb', sa.Integer(), nullable=False),
        sa.Column('recommended_memory_mb', sa.Integer(), nullable=False),
        sa.Column('max_memory_mb', sa.Integer(), nullable=True),
        sa.Column('min_compute_capability', sa.String(length=20), nullable=False),
        sa.Column('preferred_batch_size', sa.Integer(), nullable=False),
        sa.Column('max_concurrent_requests', sa.Integer(), nullable=False),
        sa.Column('typical_inference_time_ms', sa.Integer(), nullable=True),
        sa.Column('max_inference_time_ms', sa.Integer(), nullable=True),
        sa.Column('warmup_time_ms', sa.Integer(), nullable=True),
        sa.Column('requires_fp16', sa.Boolean(), nullable=False),
        sa.Column('requires_int8', sa.Boolean(), nullable=False),
        sa.Column('supports_quantization', sa.Boolean(), nullable=False),
        sa.Column('optimization_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('compatibility_notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name', 'model_provider', 'model_version', name='_model_constraint_uc')
    )
    
    # Create indexes for gpu_resources
    op.create_index('idx_gpu_resource_availability', 'gpu_resources', ['is_available', 'maintenance_mode'])
    op.create_index('idx_gpu_resource_performance', 'gpu_resources', ['average_utilization_24h', 'uptime_hours'])
    op.create_index('idx_gpu_resource_utilization', 'gpu_resources', ['current_utilization_percent', 'current_memory_used_mb'])
    
    # Create indexes for agent_configurations
    op.create_index('idx_agent_config_constraints_gin', 'agent_configurations', ['constraints'], postgresql_using='gin')
    op.create_index('idx_agent_config_gpu', 'agent_configurations', ['gpu_assignment', 'is_active'])
    op.create_index('idx_agent_config_provider', 'agent_configurations', ['model_provider', 'agent_type'])
    op.create_index(op.f('ix_agent_configurations_agent_id'), 'agent_configurations', ['agent_id'])
    op.create_index(op.f('ix_agent_configurations_agent_type'), 'agent_configurations', ['agent_type'])
    op.create_index(op.f('ix_agent_configurations_gpu_assignment'), 'agent_configurations', ['gpu_assignment'])
    op.create_index(op.f('ix_agent_configurations_model_provider'), 'agent_configurations', ['model_provider'])
    op.create_index(op.f('ix_agent_configurations_user_id'), 'agent_configurations', ['user_id'])
    
    # Create indexes for agent_profiles
    op.create_index('idx_agent_profile_expertise_gin', 'agent_profiles', ['expertise_areas'], postgresql_using='gin')
    op.create_index('idx_agent_profile_performance', 'agent_profiles', ['success_rate', 'user_satisfaction_score'])
    op.create_index('idx_agent_profile_status', 'agent_profiles', ['current_status', 'last_active_at'])
    op.create_index('idx_agent_profile_workload', 'agent_profiles', ['current_workload', 'max_workload'])
    op.create_index(op.f('ix_agent_profiles_agent_id'), 'agent_profiles', ['agent_id'])
    op.create_index(op.f('ix_agent_profiles_config_id'), 'agent_profiles', ['config_id'])
    op.create_index(op.f('ix_agent_profiles_current_status'), 'agent_profiles', ['current_status'])
    
    # Create indexes for gpu_allocations
    op.create_index('idx_gpu_allocation_performance', 'gpu_allocations', ['average_utilization_percent', 'total_requests_processed'])
    op.create_index('idx_gpu_allocation_status', 'gpu_allocations', ['status', 'allocated_at'])
    op.create_index('idx_gpu_allocation_utilization', 'gpu_allocations', ['current_utilization_percent', 'current_memory_usage_mb'])
    op.create_index(op.f('ix_gpu_allocations_agent_config_id'), 'gpu_allocations', ['agent_config_id'])
    op.create_index(op.f('ix_gpu_allocations_agent_id'), 'gpu_allocations', ['agent_id'])
    op.create_index(op.f('ix_gpu_allocations_gpu_id'), 'gpu_allocations', ['gpu_id'])
    op.create_index(op.f('ix_gpu_allocations_status'), 'gpu_allocations', ['status'])
    
    # Create indexes for task_delegations
    op.create_index('idx_task_delegation_agents', 'task_delegations', ['pm_agent_id', 'target_agent_id'])
    op.create_index('idx_task_delegation_context_gin', 'task_delegations', ['context_data'], postgresql_using='gin')
    op.create_index('idx_task_delegation_session', 'task_delegations', ['session_id', 'status'])
    op.create_index('idx_task_delegation_timing', 'task_delegations', ['created_at', 'deadline'])
    op.create_index(op.f('ix_task_delegations_blackboard_event_id'), 'task_delegations', ['blackboard_event_id'])
    op.create_index(op.f('ix_task_delegations_consensus_node_id'), 'task_delegations', ['consensus_node_id'])
    op.create_index(op.f('ix_task_delegations_conversation_id'), 'task_delegations', ['conversation_id'])
    op.create_index(op.f('ix_task_delegations_pm_agent_id'), 'task_delegations', ['pm_agent_id'])
    op.create_index(op.f('ix_task_delegations_session_id'), 'task_delegations', ['session_id'])
    op.create_index(op.f('ix_task_delegations_status'), 'task_delegations', ['status'])
    op.create_index(op.f('ix_task_delegations_target_agent_id'), 'task_delegations', ['target_agent_id'])
    op.create_index(op.f('ix_task_delegations_task_type'), 'task_delegations', ['task_type'])
    op.create_index(op.f('ix_task_delegations_user_id'), 'task_delegations', ['user_id'])
    
    # Create indexes for agent_responses
    op.create_index('idx_agent_response_deliverables_gin', 'agent_responses', ['deliverables'], postgresql_using='gin')
    op.create_index('idx_agent_response_performance', 'agent_responses', ['processing_time_seconds', 'tokens_used'])
    op.create_index('idx_agent_response_quality', 'agent_responses', ['quality_score', 'has_been_validated'])
    op.create_index('idx_agent_response_type', 'agent_responses', ['response_type', 'confidence_score'])
    op.create_index(op.f('ix_agent_responses_agent_id'), 'agent_responses', ['agent_id'])
    op.create_index(op.f('ix_agent_responses_blackboard_event_id'), 'agent_responses', ['blackboard_event_id'])
    op.create_index(op.f('ix_agent_responses_response_type'), 'agent_responses', ['response_type'])
    op.create_index(op.f('ix_agent_responses_task_delegation_id'), 'agent_responses', ['task_delegation_id'])
    
    # Create indexes for task_synthesis
    op.create_index('idx_task_synthesis_performance', 'task_synthesis', ['synthesis_time_seconds', 'total_tokens_processed'])
    op.create_index('idx_task_synthesis_quality', 'task_synthesis', ['synthesis_confidence', 'completeness_score', 'coherence_score'])
    op.create_index('idx_task_synthesis_session', 'task_synthesis', ['session_id', 'synthesis_type'])
    op.create_index('idx_task_synthesis_sources_gin', 'task_synthesis', ['source_agent_responses'], postgresql_using='gin')
    op.create_index(op.f('ix_task_synthesis_consensus_node_id'), 'task_synthesis', ['consensus_node_id'])
    op.create_index(op.f('ix_task_synthesis_conversation_id'), 'task_synthesis', ['conversation_id'])
    op.create_index(op.f('ix_task_synthesis_session_id'), 'task_synthesis', ['session_id'])
    op.create_index(op.f('ix_task_synthesis_synthesis_type'), 'task_synthesis', ['synthesis_type'])
    op.create_index(op.f('ix_task_synthesis_synthesizer_agent_id'), 'task_synthesis', ['synthesizer_agent_id'])
    op.create_index(op.f('ix_task_synthesis_user_id'), 'task_synthesis', ['user_id'])
    
    # Create indexes for multi_agent_conversations
    op.create_index('idx_multi_agent_conversation_agents_gin', 'multi_agent_conversations', ['participating_agents'], postgresql_using='gin')
    op.create_index('idx_multi_agent_conversation_performance', 'multi_agent_conversations', ['total_processing_time_seconds', 'average_response_time_seconds'])
    op.create_index('idx_multi_agent_conversation_phase', 'multi_agent_conversations', ['current_phase', 'is_active'])
    op.create_index('idx_multi_agent_conversation_progress', 'multi_agent_conversations', ['tasks_completed', 'total_tasks_delegated'])
    op.create_index(op.f('ix_multi_agent_conversations_conversation_id'), 'multi_agent_conversations', ['conversation_id'])
    op.create_index(op.f('ix_multi_agent_conversations_conversation_type'), 'multi_agent_conversations', ['conversation_type'])
    op.create_index(op.f('ix_multi_agent_conversations_coordinator_agent_id'), 'multi_agent_conversations', ['coordinator_agent_id'])
    op.create_index(op.f('ix_multi_agent_conversations_current_phase'), 'multi_agent_conversations', ['current_phase'])
    op.create_index(op.f('ix_multi_agent_conversations_domain'), 'multi_agent_conversations', ['domain'])
    op.create_index(op.f('ix_multi_agent_conversations_session_id'), 'multi_agent_conversations', ['session_id'])
    op.create_index(op.f('ix_multi_agent_conversations_user_id'), 'multi_agent_conversations', ['user_id'])
    
    # Create indexes for agent_participations
    op.create_index('idx_agent_participation_metrics', 'agent_participations', ['total_contributions', 'contribution_quality_score'])
    op.create_index('idx_agent_participation_status', 'agent_participations', ['current_status', 'is_currently_active'])
    op.create_index('idx_agent_participation_workload', 'agent_participations', ['current_workload', 'tasks_assigned'])
    op.create_index(op.f('ix_agent_participations_agent_id'), 'agent_participations', ['agent_id'])
    op.create_index(op.f('ix_agent_participations_conversation_id'), 'agent_participations', ['conversation_id'])
    op.create_index(op.f('ix_agent_participations_current_status'), 'agent_participations', ['current_status'])
    op.create_index(op.f('ix_agent_participations_participation_type'), 'agent_participations', ['participation_type'])
    
    # Create indexes for load_balancing_rules
    op.create_index('idx_load_balancing_rule_agents_gin', 'load_balancing_rules', ['applicable_agent_types'], postgresql_using='gin')
    op.create_index('idx_load_balancing_rule_criteria_gin', 'load_balancing_rules', ['criteria'], postgresql_using='gin')
    op.create_index('idx_load_balancing_rule_priority', 'load_balancing_rules', ['priority_level', 'is_default'])
    op.create_index('idx_load_balancing_rule_type', 'load_balancing_rules', ['rule_type', 'is_active'])
    op.create_index(op.f('ix_load_balancing_rules_rule_type'), 'load_balancing_rules', ['rule_type'])
    
    # Create indexes for resource_constraints
    op.create_index('idx_resource_constraint_memory', 'resource_constraints', ['min_memory_mb', 'recommended_memory_mb'])
    op.create_index('idx_resource_constraint_optimization_gin', 'resource_constraints', ['optimization_settings'], postgresql_using='gin')
    op.create_index('idx_resource_constraint_performance', 'resource_constraints', ['max_concurrent_requests', 'typical_inference_time_ms'])
    op.create_index('idx_resource_constraint_requirements', 'resource_constraints', ['requires_fp16', 'requires_int8', 'supports_quantization'])
    op.create_index(op.f('ix_resource_constraints_model_name'), 'resource_constraints', ['model_name'])
    op.create_index(op.f('ix_resource_constraints_model_provider'), 'resource_constraints', ['model_provider'])


def downgrade() -> None:
    """Remove Helios Multi-Agent framework tables."""
    
    # Drop tables in reverse order
    op.drop_table('resource_constraints')
    op.drop_table('load_balancing_rules')
    op.drop_table('agent_participations')
    op.drop_table('multi_agent_conversations')
    op.drop_table('task_synthesis')
    op.drop_table('agent_responses')
    op.drop_table('task_delegations')
    op.drop_table('gpu_allocations')
    op.drop_table('agent_profiles')
    op.drop_table('agent_configurations')
    op.drop_table('gpu_resources')
    
    # Drop enums
    op.execute("DROP TYPE modelprovider")
    op.execute("DROP TYPE gpuallocationstatus")
    op.execute("DROP TYPE conversationphase")
    op.execute("DROP TYPE taskdelegationstatus")
    op.execute("DROP TYPE agentstatus")