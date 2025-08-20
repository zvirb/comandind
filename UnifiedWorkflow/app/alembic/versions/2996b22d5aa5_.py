"""empty message

Revision ID: 2996b22d5aa5
Revises: a2b3c4d5e6f7, add_2fa_device_management, add_password_reset_tokens
Create Date: 2025-07-28 21:49:12.060321

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2996b22d5aa5'
down_revision: Union[str, Sequence[str], None] = ('a2b3c4d5e6f7', 'add_2fa_device_management', 'add_password_reset_tokens')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
