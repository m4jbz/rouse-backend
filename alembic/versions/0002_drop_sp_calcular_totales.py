"""drop sp_calcular_totales – totals now computed in Python

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-07 00:00:00.000000

The stored procedure sp_calcular_totales was never wired to any trigger
and the application now calculates subtotals/totals in the backend before
inserting.  This migration removes the orphaned procedure.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP PROCEDURE IF EXISTS sp_calcular_totales")


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE PROCEDURE sp_calcular_totales(p_order_id INTEGER)
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE orderdetail
            SET subtotal = unit_price * quantity
            WHERE order_id = p_order_id;

            UPDATE "order"
            SET total = COALESCE(
                (SELECT SUM(subtotal) FROM orderdetail WHERE order_id = p_order_id), 0
            )
            WHERE id = p_order_id;
        END;
        $$;
    """)
