"""Add password reset tokens table

Revision ID: add_password_reset_tokens
Revises: latest
Create Date: 2025-07-28 07:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_password_reset_tokens'
down_revision = None  # Set this to the actual latest revision ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add password_reset_tokens table."""
    op.create_table(
        'password_reset_tokens',
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), default=False, nullable=False),
        sa.PrimaryKeyConstraint('token'),
        sa.Index('ix_password_reset_tokens_token', 'token'),
        sa.Index('ix_password_reset_tokens_user_id', 'user_id'),
    )


def downgrade() -> None:
    """Drop password_reset_tokens table."""
    op.drop_table('password_reset_tokens')