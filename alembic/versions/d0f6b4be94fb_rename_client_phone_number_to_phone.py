"""rename client phone_number to phone

Revision ID: d0f6b4be94fb
Revises: ab0185d63d95
Create Date: 2026-02-07 23:21:12.952380

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd0f6b4be94fb'
down_revision: Union[str, Sequence[str], None] = 'ab0185d63d95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('client', 'phone_number', new_column_name='phone')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('client', 'phone', new_column_name='phone_number')
