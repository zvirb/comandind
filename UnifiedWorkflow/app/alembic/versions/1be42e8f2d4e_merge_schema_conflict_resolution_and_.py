"""Merge schema conflict resolution and Helios framework

Revision ID: 1be42e8f2d4e
Revises: a1b2c3d4e5f6, e7f8a9b0c1d2
Create Date: 2025-08-02 23:27:47.987880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1be42e8f2d4e'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'e7f8a9b0c1d2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
