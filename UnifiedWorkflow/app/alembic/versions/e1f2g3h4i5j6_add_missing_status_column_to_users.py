"""Add missing status column to users table

Revision ID: e1f2g3h4i5j6
Revises: d1e2f3g4h5i6
Create Date: 2025-08-06 21:58:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: str = 'd1e2f3g4h5i6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to users table to match SQLAlchemy model."""
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Create enums if they don't exist
    result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'userstatus'"))
    if not result.fetchone():
        op.execute("CREATE TYPE userstatus AS ENUM ('pending_approval', 'active', 'disabled')")
    
    result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'userrole'"))
    if not result.fetchone():
        op.execute("CREATE TYPE userrole AS ENUM ('admin', 'user')")
    
    # Add missing status column
    if 'status' not in columns:
        op.add_column('users', 
            sa.Column('status', postgresql.ENUM('pending_approval', 'active', 'disabled', name='userstatus'), nullable=True)
        )
        op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
        op.alter_column('users', 'status', nullable=False)
    
    # Add missing tfa_enabled column
    if 'tfa_enabled' not in columns:
        op.add_column('users', sa.Column('tfa_enabled', sa.Boolean(), nullable=True))
        op.execute("UPDATE users SET tfa_enabled = false WHERE tfa_enabled IS NULL")
        op.alter_column('users', 'tfa_enabled', nullable=False)
    
    # Add missing tfa_secret column  
    if 'tfa_secret' not in columns:
        op.add_column('users', sa.Column('tfa_secret', sa.String(), nullable=True))
    
    # Add missing user settings columns
    user_settings_columns = [
        ('theme', sa.String(), 'dark'),
        ('selected_model', sa.String(), 'llama3.2:3b'),
        ('timezone', sa.String(), 'UTC'),
        ('chat_model', sa.String(), 'llama3.2:3b'),
        ('initial_assessment_model', sa.String(), 'llama3.2:3b'),
        ('tool_selection_model', sa.String(), 'llama3.2:3b'),
        ('embeddings_model', sa.String(), 'llama3.2:3b'),
        ('coding_model', sa.String(), 'llama3.2:3b'),
        ('executive_assessment_model', sa.String(), 'llama3.2:3b'),
        ('confidence_assessment_model', sa.String(), 'llama3.2:3b'),
        ('tool_routing_model', sa.String(), 'llama3.2:3b'),
        ('simple_planning_model', sa.String(), 'llama3.2:3b'),
        ('wave_function_specialist_model', sa.String(), 'llama3.2:1b'),
        ('wave_function_refinement_model', sa.String(), 'llama3.1:8b'),
        ('plan_validation_model', sa.String(), 'llama3.2:3b'),
        ('plan_comparison_model', sa.String(), 'llama3.2:3b'),
        ('reflection_model', sa.String(), 'llama3.2:3b'),
        ('final_response_model', sa.String(), 'llama3.2:3b'),
        ('fast_conversational_model', sa.String(), 'llama3.2:1b'),
    ]
    
    for column_name, column_type, default_value in user_settings_columns:
        if column_name not in columns:
            op.add_column('users', sa.Column(column_name, column_type, default=default_value, nullable=True))
    
    # Handle notifications_enabled separately since it's boolean
    if 'notifications_enabled' not in columns:
        op.add_column('users', sa.Column('notifications_enabled', sa.Boolean(), nullable=True))
        op.execute("UPDATE users SET notifications_enabled = true WHERE notifications_enabled IS NULL")
        op.alter_column('users', 'notifications_enabled', nullable=False)
    
    # Add JSONB columns
    if 'calendar_event_weights' not in columns:
        op.add_column('users', sa.Column('calendar_event_weights', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Update role column to use proper enum if it's not already
    current_role_column = next((col for col in inspector.get_columns('users') if col['name'] == 'role'), None)
    if current_role_column and str(current_role_column['type']) != 'USER-DEFINED':
        # First drop the default value, then convert to enum, then restore default
        op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
        op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'::userrole")


def downgrade() -> None:
    """Remove added columns from users table."""
    
    # Drop all added columns (reverse order of creation)
    columns_to_drop = [
        'calendar_event_weights',
        'fast_conversational_model',
        'final_response_model', 
        'reflection_model',
        'plan_comparison_model',
        'plan_validation_model',
        'wave_function_refinement_model',
        'wave_function_specialist_model',
        'simple_planning_model',
        'tool_routing_model',
        'confidence_assessment_model',
        'executive_assessment_model',
        'coding_model',
        'embeddings_model',
        'tool_selection_model',
        'initial_assessment_model',
        'chat_model',
        'timezone',
        'selected_model',
        'notifications_enabled',
        'theme',
        'tfa_secret',
        'tfa_enabled',
        'status'
    ]
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = [col['name'] for col in inspector.get_columns('users')]
    
    for column_name in columns_to_drop:
        if column_name in existing_columns:
            op.drop_column('users', column_name)
    
    # Note: We don't drop the enum types in case other migrations depend on them