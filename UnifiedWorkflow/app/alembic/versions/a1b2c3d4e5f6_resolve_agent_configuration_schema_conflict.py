"""resolve_agent_configuration_schema_conflict

Revision ID: a1b2c3d4e5f6
Revises: f3a8b9c4d7e2
Create Date: 2025-08-02 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a8b9c4d7e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Resolve AgentConfiguration schema conflict by renaming legacy tables."""
    
    # Rename legacy agent configuration tables to avoid conflicts with Helios Multi-Agent framework
    
    # Check if legacy tables exist and rename them
    connection = op.get_bind()
    
    # Check if the conflicting agent_configurations table exists (from Agent Abstraction Layer)
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'agent_configurations'
            AND NOT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'agent_configurations' 
                AND column_name = 'agent_id'
            )
        );
    """)).scalar()
    
    if result:
        # Rename the legacy agent_configurations table
        op.rename_table('agent_configurations', 'legacy_agent_configurations')
        
        # Rename related tables
        op.rename_table('agent_metrics', 'legacy_agent_metrics')
        op.rename_table('gpu_resource_allocations', 'legacy_gpu_resource_allocations')
        op.rename_table('model_instances', 'legacy_model_instances')
        
        # Update foreign key constraints
        op.drop_constraint('agent_metrics_agent_config_id_fkey', 'legacy_agent_metrics', type_='foreignkey')
        op.create_foreign_key(
            'legacy_agent_metrics_agent_config_id_fkey',
            'legacy_agent_metrics', 
            'legacy_agent_configurations',
            ['agent_config_id'], 
            ['id']
        )
        
        # Update indexes to reflect new table names
        try:
            op.drop_index('ix_agent_configurations_agent_type', table_name='legacy_agent_configurations')
            op.create_index('ix_legacy_agent_configurations_agent_type', 'legacy_agent_configurations', ['agent_type'])
        except:
            pass  # Index might not exist
            
        try:
            op.drop_index('ix_agent_configurations_agent_name', table_name='legacy_agent_configurations')
            op.create_index('ix_legacy_agent_configurations_agent_name', 'legacy_agent_configurations', ['agent_name'])
        except:
            pass  # Index might not exist


def downgrade() -> None:
    """Reverse the migration by restoring original table names."""
    
    # Check if legacy tables exist and rename them back
    connection = op.get_bind()
    
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'legacy_agent_configurations'
        );
    """)).scalar()
    
    if result:
        # Drop Helios Multi-Agent framework tables first to avoid conflicts
        try:
            op.drop_table('agent_configurations')  # Helios Multi-Agent version
        except:
            pass
            
        # Restore original table names
        op.rename_table('legacy_agent_configurations', 'agent_configurations')
        op.rename_table('legacy_agent_metrics', 'agent_metrics')
        op.rename_table('legacy_gpu_resource_allocations', 'gpu_resource_allocations')
        op.rename_table('legacy_model_instances', 'model_instances')
        
        # Restore foreign key constraints
        op.drop_constraint('legacy_agent_metrics_agent_config_id_fkey', 'agent_metrics', type_='foreignkey')
        op.create_foreign_key(
            'agent_metrics_agent_config_id_fkey',
            'agent_metrics', 
            'agent_configurations',
            ['agent_config_id'], 
            ['id']
        )
        
        # Restore indexes
        try:
            op.drop_index('ix_legacy_agent_configurations_agent_type', table_name='agent_configurations')
            op.create_index('ix_agent_configurations_agent_type', 'agent_configurations', ['agent_type'])
        except:
            pass
            
        try:
            op.drop_index('ix_legacy_agent_configurations_agent_name', table_name='agent_configurations')
            op.create_index('ix_agent_configurations_agent_name', 'agent_configurations', ['agent_name'])
        except:
            pass