"""add_task_feedback_table

Revision ID: c3d7a3a4d59c
Revises: 9d8e7f6a5b4c
Create Date: 2025-07-21 22:00:12.900424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d7a3a4d59c'
down_revision: Union[str, Sequence[str], None] = '9d8e7f6a5b4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add task_feedback table for storing task completion feedback."""
    op.create_table('task_feedback',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('opportunity_id', sa.String, sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('feeling', sa.String, nullable=False),
        sa.Column('difficulty', sa.Integer, nullable=False),
        sa.Column('energy', sa.Integer, nullable=False),
        sa.Column('category', sa.String, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('blockers_encountered', sa.Boolean, default=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop task_feedback table."""
    op.drop_table('task_feedback')
