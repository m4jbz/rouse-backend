"""remove refunded from paymentstatus

Revision ID: d0f26b9ebe3c
Revises: d0c2a283234d
Create Date: 2026-02-08 12:21:19.610919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0f26b9ebe3c'
down_revision: Union[str, Sequence[str], None] = 'd0c2a283234d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Crear tipo nuevo sin REFUNDED
    op.execute("CREATE TYPE paymentstatus_new AS ENUM ('PENDING', 'PAID')")

    # 2. Cambiar la columna al nuevo tipo
    op.execute("""
        ALTER TABLE "order"
            ALTER COLUMN payment_status TYPE paymentstatus_new
            USING payment_status::text::paymentstatus_new
    """)

    # 3. Borrar el tipo viejo
    op.execute("DROP TYPE paymentstatus")

    # 4. Renombrar el nuevo al nombre original
    op.execute("ALTER TYPE paymentstatus_new RENAME TO paymentstatus")

    # 5. Actualizar trigger: quitar la lógica de REFUNDED
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_estado_segun_pago()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.payment_status IS DISTINCT FROM NEW.payment_status THEN
                IF NEW.payment_status = 'PAID' AND NEW.status = 'PENDING' THEN
                    NEW.status := 'CONFIRMED';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Recrear tipo con REFUNDED
    op.execute("CREATE TYPE paymentstatus_old AS ENUM ('PENDING', 'PAID', 'REFUNDED')")

    # 2. Cambiar la columna al tipo viejo
    op.execute("""
        ALTER TABLE "order"
            ALTER COLUMN payment_status TYPE paymentstatus_old
            USING payment_status::text::paymentstatus_old
    """)

    # 3. Borrar el tipo actual
    op.execute("DROP TYPE paymentstatus")

    # 4. Renombrar
    op.execute("ALTER TYPE paymentstatus_old RENAME TO paymentstatus")

    # 5. Restaurar trigger con lógica de REFUNDED
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_estado_segun_pago()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.payment_status IS DISTINCT FROM NEW.payment_status THEN
                IF NEW.payment_status = 'PAID' AND NEW.status = 'PENDING' THEN
                    NEW.status := 'CONFIRMED';
                ELSIF NEW.payment_status = 'REFUNDED' THEN
                    NEW.status := 'CANCELLED';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
