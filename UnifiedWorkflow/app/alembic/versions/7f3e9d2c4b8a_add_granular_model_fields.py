"""Add granular node-specific model fields

Revision ID: 7f3e9d2c4b8a
Revises: 5b7c8d9e2f4a
Create Date: 2025-07-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7f3e9d2c4b8a'
down_revision = '5b7c8d9e2f4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add granular node-specific model fields to users table."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Get existing columns in users table
    user_columns = [col['name'] for col in inspector.get_columns('users')]
    
    # List of new granular model fields to add
    granular_model_fields = [
        'executive_assessment_model',
        'confidence_assessment_model', 
        'tool_routing_model',
        'simple_planning_model',
        'wave_function_specialist_model',
        'wave_function_refinement_model',
        'plan_validation_model',
        'plan_comparison_model',
        'reflection_model',
        'final_response_model'
    ]
    
    # Add each field if it doesn't exist
    for field in granular_model_fields:
        if field not in user_columns:
            # Set appropriate defaults for each field
            if field == 'wave_function_specialist_model':
                default_value = 'llama3.2:1b'
            elif field == 'wave_function_refinement_model':
                default_value = 'llama3.1:8b'
            else:
                default_value = 'llama3.2:3b'
                
            op.add_column('users', sa.Column(
                field, 
                sa.String(), 
                nullable=True, 
                default=default_value
            ))
            print(f"Added column: {field}")


def downgrade() -> None:
    """Remove granular node-specific model fields from users table."""
    granular_model_fields = [
        'executive_assessment_model',
        'confidence_assessment_model', 
        'tool_routing_model',
        'simple_planning_model',
        'wave_function_specialist_model',
        'wave_function_refinement_model',
        'plan_validation_model',
        'plan_comparison_model',
        'reflection_model',
        'final_response_model'
    ]
    
    # Remove each field
    for field in granular_model_fields:
        try:
            op.drop_column('users', field)
        except Exception:
            # Column might not exist, continue
            pass