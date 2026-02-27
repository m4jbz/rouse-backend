"""add_client_cart_item_table

Revision ID: c3a4b5d6e7f8
Revises: 8ee8d47f0f46
Create Date: 2026-02-26 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a4b5d6e7f8'
down_revision: Union[str, Sequence[str], None] = '8ee8d47f0f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create client_cart_item table."""
    op.create_table(
        'client_cart_item',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Uuid(), sa.ForeignKey('client.id'), nullable=False, index=True),
        sa.Column('product_id', sa.String(length=200), nullable=False),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('product_price', sa.Float(), nullable=False),
        sa.Column('product_image', sa.String(length=500), nullable=False),
        sa.Column('product_badge', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default=sa.text('1')),
    )


def downgrade() -> None:
    """Drop client_cart_item table."""
    op.drop_table('client_cart_item')
