"""add_fast_conversational_model_field

Revision ID: 9d8e7f6a5b4c
Revises: 8a4b7f2e1d9c
Create Date: 2025-07-21 14:13:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d8e7f6a5b4c'
down_revision = '8a4b7f2e1d9c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add fast_conversational_model field to users table
    op.add_column('users', sa.Column('fast_conversational_model', sa.String(), nullable=True))
    
    # Set default value for existing users
    op.execute("UPDATE users SET fast_conversational_model = 'llama3.2:1b' WHERE fast_conversational_model IS NULL")


def downgrade() -> None:
    # Remove fast_conversational_model field from users table
    op.drop_column('users', 'fast_conversational_model')