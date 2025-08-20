"""add emoji and weights fields to user categories

Revision ID: a2b3c4d5e6f7
Revises: 9d8e7f6a5b4c
Create Date: 2025-01-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = '9d8e7f6a5b4c'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to user_categories table
    op.add_column('user_categories', sa.Column('emoji', sa.String(), nullable=True, server_default='📋'))
    op.add_column('user_categories', sa.Column('weights', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('user_categories', sa.Column('ai_generated', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Remove the columns
    op.drop_column('user_categories', 'ai_generated')
    op.drop_column('user_categories', 'weights')
    op.drop_column('user_categories', 'emoji')