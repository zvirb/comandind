"""Add unified cognitive state management system

Revision ID: c4d5e6f7a8b9
Revises: b0f9ada0f772
Create Date: 2025-08-02 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'b0f9ada0f772'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unified cognitive state management tables."""
    
    # Create enums
    op.execute("CREATE TYPE eventtype AS ENUM ('agent_contribution', 'conflict_detected', 'consensus_reached', 'task_delegated', 'memory_updated', 'state_synchronized', 'validation_completed', 'decision_made', 'goal_established', 'plan_created')")
    op.execute("CREATE TYPE performative AS ENUM ('inform', 'request', 'propose', 'accept', 'reject', 'confirm', 'cancel', 'query', 'assert', 'retract')")
    op.execute("CREATE TYPE memorytier AS ENUM ('private', 'shared', 'consensus')")
    op.execute("CREATE TYPE synchronizationstatus AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'conflict')")
    op.execute("CREATE TYPE validationstatus AS ENUM ('unvalidated', 'validating', 'validated', 'rejected', 'conflicted')")
    
    # Create blackboard_events table
    op.create_table('blackboard_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_sequence', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.Enum('agent_contribution', 'conflict_detected', 'consensus_reached', 'task_delegated', 'memory_updated', 'state_synchronized', 'validation_completed', 'decision_made', 'goal_established', 'plan_created', name='eventtype'), nullable=False),
        sa.Column('performative', sa.Enum('inform', 'request', 'propose', 'accept', 'reject', 'confirm', 'cancel', 'query', 'assert', 'retract', name='performative'), nullable=False),
        sa.Column('source_agent_id', sa.String(), nullable=False),
        sa.Column('target_agent_id', sa.String(), nullable=True),
        sa.Column('agent_role', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('event_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('semantic_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('parent_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('causality_chain', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('related_events', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('logical_timestamp', sa.Integer(), nullable=False),
        sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_event_id'], ['blackboard_events.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for blackboard_events
    op.create_index('idx_blackboard_events_agent_session', 'blackboard_events', ['source_agent_id', 'session_id'])
    op.create_index('idx_blackboard_events_causality', 'blackboard_events', ['parent_event_id', 'event_sequence'])
    op.create_index('idx_blackboard_events_payload_gin', 'blackboard_events', ['event_payload'], postgresql_using='gin')
    op.create_index('idx_blackboard_events_temporal', 'blackboard_events', ['created_at', 'logical_timestamp'])
    op.create_index(op.f('ix_blackboard_events_agent_role'), 'blackboard_events', ['agent_role'])
    op.create_index(op.f('ix_blackboard_events_conversation_id'), 'blackboard_events', ['conversation_id'])
    op.create_index(op.f('ix_blackboard_events_created_at'), 'blackboard_events', ['created_at'])
    op.create_index(op.f('ix_blackboard_events_event_sequence'), 'blackboard_events', ['event_sequence'])
    op.create_index(op.f('ix_blackboard_events_event_type'), 'blackboard_events', ['event_type'])
    op.create_index(op.f('ix_blackboard_events_logical_timestamp'), 'blackboard_events', ['logical_timestamp'])
    op.create_index(op.f('ix_blackboard_events_parent_event_id'), 'blackboard_events', ['parent_event_id'])
    op.create_index(op.f('ix_blackboard_events_performative'), 'blackboard_events', ['performative'])
    op.create_index(op.f('ix_blackboard_events_session_id'), 'blackboard_events', ['session_id'])
    op.create_index(op.f('ix_blackboard_events_source_agent_id'), 'blackboard_events', ['source_agent_id'])
    op.create_index(op.f('ix_blackboard_events_target_agent_id'), 'blackboard_events', ['target_agent_id'])
    op.create_index(op.f('ix_blackboard_events_user_id'), 'blackboard_events', ['user_id'])
    
    # Create agent_context_states table
    op.create_table('agent_context_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('agent_type', sa.String(), nullable=False),
        sa.Column('agent_role', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('memory_tier', sa.Enum('private', 'shared', 'consensus', name='memorytier'), nullable=False),
        sa.Column('context_key', sa.String(), nullable=False),
        sa.Column('context_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('context_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_shareable', sa.Boolean(), nullable=False),
        sa.Column('access_permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_persistent', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('last_synchronized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_checksum', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'session_id', 'context_key', name='_agent_session_context_uc')
    )
    
    # Create indexes for agent_context_states
    op.create_index('idx_agent_context_expiry', 'agent_context_states', ['expires_at'])
    op.create_index('idx_agent_context_memory_tier', 'agent_context_states', ['memory_tier', 'session_id'])
    op.create_index('idx_agent_context_value_gin', 'agent_context_states', ['context_value'], postgresql_using='gin')
    op.create_index(op.f('ix_agent_context_states_agent_id'), 'agent_context_states', ['agent_id'])
    op.create_index(op.f('ix_agent_context_states_agent_role'), 'agent_context_states', ['agent_role'])
    op.create_index(op.f('ix_agent_context_states_agent_type'), 'agent_context_states', ['agent_type'])
    op.create_index(op.f('ix_agent_context_states_memory_tier'), 'agent_context_states', ['memory_tier'])
    op.create_index(op.f('ix_agent_context_states_session_id'), 'agent_context_states', ['session_id'])
    op.create_index(op.f('ix_agent_context_states_user_id'), 'agent_context_states', ['user_id'])
    
    # Create consensus_memory_nodes table
    op.create_table('consensus_memory_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('node_key', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('validation_status', sa.Enum('unvalidated', 'validating', 'validated', 'rejected', 'conflicted', name='validationstatus'), nullable=False),
        sa.Column('consensus_score', sa.Float(), nullable=False),
        sa.Column('validation_count', sa.Integer(), nullable=False),
        sa.Column('source_events', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('contributing_agents', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('decision_rationale', sa.Text(), nullable=True),
        sa.Column('semantic_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('importance_weight', sa.Float(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('superseded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('established_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['superseded_by'], ['consensus_memory_nodes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'node_type', 'node_key', name='_user_consensus_node_uc')
    )
    
    # Create indexes for consensus_memory_nodes
    op.create_index('idx_consensus_memory_content_gin', 'consensus_memory_nodes', ['content'], postgresql_using='gin')
    op.create_index('idx_consensus_memory_domain', 'consensus_memory_nodes', ['domain', 'user_id'])
    op.create_index('idx_consensus_memory_tags_gin', 'consensus_memory_nodes', ['semantic_tags'], postgresql_using='gin')
    op.create_index('idx_consensus_memory_validation', 'consensus_memory_nodes', ['validation_status', 'consensus_score'])
    op.create_index(op.f('ix_consensus_memory_nodes_domain'), 'consensus_memory_nodes', ['domain'])
    op.create_index(op.f('ix_consensus_memory_nodes_node_key'), 'consensus_memory_nodes', ['node_key'])
    op.create_index(op.f('ix_consensus_memory_nodes_node_type'), 'consensus_memory_nodes', ['node_type'])
    op.create_index(op.f('ix_consensus_memory_nodes_session_id'), 'consensus_memory_nodes', ['session_id'])
    op.create_index(op.f('ix_consensus_memory_nodes_user_id'), 'consensus_memory_nodes', ['user_id'])
    op.create_index(op.f('ix_consensus_memory_nodes_validation_status'), 'consensus_memory_nodes', ['validation_status'])
    
    # Create consensus_memory_relations table
    op.create_table('consensus_memory_relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('strength', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('established_by_event', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('validation_status', sa.Enum('unvalidated', 'validating', 'validated', 'rejected', 'conflicted', name='validationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['established_by_event'], ['blackboard_events.id'], ),
        sa.ForeignKeyConstraint(['source_node_id'], ['consensus_memory_nodes.id'], ),
        sa.ForeignKeyConstraint(['target_node_id'], ['consensus_memory_nodes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_node_id', 'target_node_id', 'relation_type', name='_node_relation_uc')
    )
    
    # Create indexes for consensus_memory_relations
    op.create_index('idx_consensus_relations_type', 'consensus_memory_relations', ['relation_type', 'strength'])
    op.create_index('idx_consensus_relations_validation', 'consensus_memory_relations', ['validation_status'])
    op.create_index(op.f('ix_consensus_memory_relations_relation_type'), 'consensus_memory_relations', ['relation_type'])
    op.create_index(op.f('ix_consensus_memory_relations_source_node_id'), 'consensus_memory_relations', ['source_node_id'])
    op.create_index(op.f('ix_consensus_memory_relations_target_node_id'), 'consensus_memory_relations', ['target_node_id'])
    op.create_index(op.f('ix_consensus_memory_relations_user_id'), 'consensus_memory_relations', ['user_id'])
    
    # Create cognitive_state_synchronizations table
    op.create_table('cognitive_state_synchronizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('sync_scope', sa.String(), nullable=False),
        sa.Column('sync_type', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'failed', 'conflict', name='synchronizationstatus'), nullable=False),
        sa.Column('participating_agents', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('coordinator_agent', sa.String(), nullable=False),
        sa.Column('state_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('conflicts_detected', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('resolution_strategy', sa.String(), nullable=True),
        sa.Column('source_version', sa.Integer(), nullable=False),
        sa.Column('target_version', sa.Integer(), nullable=False),
        sa.Column('checksum_before', sa.String(), nullable=False),
        sa.Column('checksum_after', sa.String(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('conflict_count', sa.Integer(), nullable=False),
        sa.Column('resolution_count', sa.Integer(), nullable=False),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('initiated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for cognitive_state_synchronizations
    op.create_index('idx_cognitive_sync_conflicts', 'cognitive_state_synchronizations', ['conflict_count', 'status'])
    op.create_index('idx_cognitive_sync_session', 'cognitive_state_synchronizations', ['session_id', 'sync_scope'])
    op.create_index('idx_cognitive_sync_snapshot_gin', 'cognitive_state_synchronizations', ['state_snapshot'], postgresql_using='gin')
    op.create_index('idx_cognitive_sync_status', 'cognitive_state_synchronizations', ['status', 'initiated_at'])
    op.create_index(op.f('ix_cognitive_state_synchronizations_session_id'), 'cognitive_state_synchronizations', ['session_id'])
    op.create_index(op.f('ix_cognitive_state_synchronizations_status'), 'cognitive_state_synchronizations', ['status'])
    op.create_index(op.f('ix_cognitive_state_synchronizations_sync_scope'), 'cognitive_state_synchronizations', ['sync_scope'])
    op.create_index(op.f('ix_cognitive_state_synchronizations_sync_type'), 'cognitive_state_synchronizations', ['sync_type'])
    op.create_index(op.f('ix_cognitive_state_synchronizations_user_id'), 'cognitive_state_synchronizations', ['user_id'])
    
    # Create shared_ontology_terms table
    op.create_table('shared_ontology_terms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(), nullable=False),
        sa.Column('namespace', sa.String(), nullable=False),
        sa.Column('term_type', sa.String(), nullable=False),
        sa.Column('definition', sa.Text(), nullable=False),
        sa.Column('synonyms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('examples', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('parent_term_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('semantic_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('applicable_domains', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('agent_types', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_core_term', sa.Boolean(), nullable=False),
        sa.Column('approval_status', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_term_id'], ['shared_ontology_terms.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('namespace', 'term', name='_ontology_namespace_term_uc')
    )
    
    # Create indexes for shared_ontology_terms
    op.create_index('idx_ontology_domains_gin', 'shared_ontology_terms', ['applicable_domains'], postgresql_using='gin')
    op.create_index('idx_ontology_properties_gin', 'shared_ontology_terms', ['semantic_properties'], postgresql_using='gin')
    op.create_index('idx_ontology_term_type', 'shared_ontology_terms', ['term_type', 'namespace'])
    op.create_index('idx_ontology_usage', 'shared_ontology_terms', ['usage_count', 'last_used_at'])
    op.create_index(op.f('ix_shared_ontology_terms_namespace'), 'shared_ontology_terms', ['namespace'])
    op.create_index(op.f('ix_shared_ontology_terms_parent_term_id'), 'shared_ontology_terms', ['parent_term_id'])
    op.create_index(op.f('ix_shared_ontology_terms_term'), 'shared_ontology_terms', ['term'])
    op.create_index(op.f('ix_shared_ontology_terms_term_type'), 'shared_ontology_terms', ['term_type'])
    
    # Create quality_assurance_checkpoints table
    op.create_table('quality_assurance_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('checkpoint_type', sa.String(), nullable=False),
        sa.Column('target_entity_type', sa.String(), nullable=False),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('validation_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('validation_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('unvalidated', 'validating', 'validated', 'rejected', 'conflicted', name='validationstatus'), nullable=False),
        sa.Column('passed_validation', sa.Boolean(), nullable=False),
        sa.Column('issues_found', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('validator_agent', sa.String(), nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for quality_assurance_checkpoints
    op.create_index('idx_qa_checkpoint_results_gin', 'quality_assurance_checkpoints', ['validation_results'], postgresql_using='gin')
    op.create_index('idx_qa_checkpoint_score', 'quality_assurance_checkpoints', ['overall_score', 'passed_validation'])
    op.create_index('idx_qa_checkpoint_target', 'quality_assurance_checkpoints', ['target_entity_type', 'target_entity_id'])
    op.create_index('idx_qa_checkpoint_type_status', 'quality_assurance_checkpoints', ['checkpoint_type', 'status'])
    op.create_index(op.f('ix_quality_assurance_checkpoints_checkpoint_type'), 'quality_assurance_checkpoints', ['checkpoint_type'])
    op.create_index(op.f('ix_quality_assurance_checkpoints_session_id'), 'quality_assurance_checkpoints', ['session_id'])
    op.create_index(op.f('ix_quality_assurance_checkpoints_status'), 'quality_assurance_checkpoints', ['status'])
    op.create_index(op.f('ix_quality_assurance_checkpoints_target_entity_id'), 'quality_assurance_checkpoints', ['target_entity_id'])
    op.create_index(op.f('ix_quality_assurance_checkpoints_target_entity_type'), 'quality_assurance_checkpoints', ['target_entity_type'])
    op.create_index(op.f('ix_quality_assurance_checkpoints_user_id'), 'quality_assurance_checkpoints', ['user_id'])


def downgrade() -> None:
    """Remove unified cognitive state management tables."""
    
    # Drop tables in reverse order
    op.drop_table('quality_assurance_checkpoints')
    op.drop_table('shared_ontology_terms')
    op.drop_table('cognitive_state_synchronizations')
    op.drop_table('consensus_memory_relations')
    op.drop_table('consensus_memory_nodes')
    op.drop_table('agent_context_states')
    op.drop_table('blackboard_events')
    
    # Drop enums
    op.execute("DROP TYPE validationstatus")
    op.execute("DROP TYPE synchronizationstatus")
    op.execute("DROP TYPE memorytier")
    op.execute("DROP TYPE performative")
    op.execute("DROP TYPE eventtype")