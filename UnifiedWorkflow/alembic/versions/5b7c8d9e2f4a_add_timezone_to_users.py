"""Add timezone field to users table

Revision ID: 5b7c8d9e2f4a
Revises: 4a8b9c2d1e3f
Create Date: 2025-07-15 01:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5b7c8d9e2f4a'
down_revision = '4a8b9c2d1e3f'
branch_labels = None
depends_on = None


def upgrade():
    # Add timezone column to users table (idempotent)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'timezone' not in columns:
        op.add_column('users', sa.Column('timezone', sa.String(), nullable=True))


def downgrade():
    # Remove timezone column from users table
    op.drop_column('users', 'timezone')