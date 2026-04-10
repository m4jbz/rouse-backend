"""Reset Postgres autoincrement sequences

Revision ID: 0004
Revises: b5c0e9ec4cbd
Create Date: 2026-04-10

One-time data fix: if sequences got out of sync (e.g. after manual inserts,
restores, or seeds with explicit IDs), Postgres can raise duplicate key errors
when inserting new rows from the admin panel.

This migration syncs each table's `id` sequence to MAX(id)+1.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "b5c0e9ec4cbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep it resilient: if something is missing, skip it rather than failing deploy.
    op.execute(
        """
        DO $$
        DECLARE
            t record;
        BEGIN
            FOR t IN
                SELECT unnest(ARRAY[
                    'category',
                    'product',
                    'product_variant',
                    'order',
                    'order_detail',
                    'order_audit',
                    'client_cart_item',
                    'cake_flavor',
                    'cake_filling',
                    'cake_topping',
                    'custom_cake_request'
                ]) AS table_name
            LOOP
                BEGIN
                    EXECUTE format(
                        'SELECT setval(pg_get_serial_sequence(%L, %L), COALESCE((SELECT MAX(id) FROM %I), 0) + 1, false)',
                        t.table_name,
                        'id',
                        t.table_name
                    );
                EXCEPTION
                    WHEN undefined_table OR undefined_column OR null_value_not_allowed THEN
                        RAISE NOTICE 'Skipping sequence reset for %', t.table_name;
                    WHEN others THEN
                        RAISE NOTICE 'Skipping sequence reset for % (error: %)', t.table_name, SQLERRM;
                END;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    # No-op. This migration only syncs sequences to current data.
    pass
