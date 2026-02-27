"""add procedures and audit trigger

Revision ID: a1b2c3d4e5f6
Revises: d0f26b9ebe3c
Create Date: 2026-02-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd0f26b9ebe3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ================================================================
    # 1. CONVERTIR TRIGGER fn_calcular_totales A STORED PROCEDURE
    #    - Se elimina el trigger y la función trigger
    #    - Se crea un procedure sp_calcular_totales que recibe el order_id
    #      y recalcula subtotales de cada detalle + total de la orden
    # ================================================================

    # Eliminar el trigger y la función existentes
    op.execute('DROP TRIGGER IF EXISTS trg_calcular_totales ON orderdetail')
    op.execute('DROP FUNCTION IF EXISTS fn_calcular_totales()')

    # Crear el stored procedure que reemplaza al trigger
    op.execute("""
        CREATE OR REPLACE PROCEDURE sp_calcular_totales(p_order_id INTEGER)
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Recalcular subtotal de cada detalle de la orden
            UPDATE orderdetail
            SET subtotal = unit_price * quantity
            WHERE order_id = p_order_id;

            -- Recalcular el total de la orden sumando los subtotales
            UPDATE "order"
            SET total = COALESCE(
                (SELECT SUM(subtotal) FROM orderdetail WHERE order_id = p_order_id), 0
            )
            WHERE id = p_order_id;
        END;
        $$;
    """)

    # ================================================================
    # 2. TRIGGER DE AUDITORÍA SOBRE PEDIDOS
    #    - Crea tabla order_audit para registrar cambios en las órdenes
    #    - Crea trigger que registra INSERT, UPDATE y DELETE
    # ================================================================

    # Crear tabla de auditoría
    op.create_table(
        'order_audit',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=True),
        sa.Column('old_payment_status', sa.String(length=50), nullable=True),
        sa.Column('new_payment_status', sa.String(length=50), nullable=True),
        sa.Column('old_total', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('new_total', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column('changed_by', sa.String(length=100), server_default=sa.text("current_user"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_order_audit_order_id', 'order_audit', ['order_id'])
    op.create_index('ix_order_audit_action', 'order_audit', ['action'])
    op.create_index('ix_order_audit_changed_at', 'order_audit', ['changed_at'])

    # Crear función y trigger de auditoría
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_audit_order()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO order_audit (order_id, action, new_status, new_payment_status, new_total)
                VALUES (NEW.id, 'INSERT', NEW.status, NEW.payment_status, NEW.total);
                RETURN NEW;

            ELSIF TG_OP = 'UPDATE' THEN
                -- Solo registrar si cambió algo relevante
                IF OLD.status IS DISTINCT FROM NEW.status
                   OR OLD.payment_status IS DISTINCT FROM NEW.payment_status
                   OR OLD.total IS DISTINCT FROM NEW.total THEN

                    INSERT INTO order_audit (
                        order_id, action,
                        old_status, new_status,
                        old_payment_status, new_payment_status,
                        old_total, new_total
                    )
                    VALUES (
                        NEW.id, 'UPDATE',
                        OLD.status, NEW.status,
                        OLD.payment_status, NEW.payment_status,
                        OLD.total, NEW.total
                    );
                END IF;
                RETURN NEW;

            ELSIF TG_OP = 'DELETE' THEN
                INSERT INTO order_audit (order_id, action, old_status, old_payment_status, old_total)
                VALUES (OLD.id, 'DELETE', OLD.status, OLD.payment_status, OLD.total);
                RETURN OLD;
            END IF;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_audit_order
        AFTER INSERT OR UPDATE OR DELETE ON "order"
        FOR EACH ROW
        EXECUTE FUNCTION fn_audit_order();
    """)

    # ================================================================
    # 3. STORED PROCEDURE: RESUMEN DE VENTAS POR PERIODO
    #    - Recibe fecha inicio y fecha fin
    #    - Devuelve un resumen con: total de pedidos, ingresos totales,
    #      pedidos por estado, producto más vendido, ticket promedio
    # ================================================================

    op.execute("""
        CREATE OR REPLACE PROCEDURE sp_resumen_ventas(
            p_fecha_inicio TIMESTAMP,
            p_fecha_fin TIMESTAMP,
            OUT out_total_pedidos INTEGER,
            OUT out_ingresos_totales NUMERIC(12,2),
            OUT out_ticket_promedio NUMERIC(10,2),
            OUT out_pedidos_entregados INTEGER,
            OUT out_pedidos_cancelados INTEGER,
            OUT out_pedidos_pendientes INTEGER,
            OUT out_producto_mas_vendido VARCHAR(200),
            OUT out_cantidad_mas_vendido INTEGER
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Total de pedidos en el periodo
            SELECT COUNT(*)
            INTO out_total_pedidos
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin;

            -- Ingresos totales (solo pedidos entregados y pagados)
            SELECT COALESCE(SUM(total), 0)
            INTO out_ingresos_totales
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status = 'DELIVERED'
              AND payment_status = 'PAID';

            -- Ticket promedio
            IF out_total_pedidos > 0 THEN
                SELECT COALESCE(AVG(total), 0)
                INTO out_ticket_promedio
                FROM "order"
                WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
                  AND status != 'CANCELLED';
            ELSE
                out_ticket_promedio := 0;
            END IF;

            -- Pedidos por estado
            SELECT COUNT(*)
            INTO out_pedidos_entregados
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status = 'DELIVERED';

            SELECT COUNT(*)
            INTO out_pedidos_cancelados
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status = 'CANCELLED';

            SELECT COUNT(*)
            INTO out_pedidos_pendientes
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status IN ('PENDING', 'CONFIRMED', 'PREPARING', 'DELIVERING');

            -- Producto más vendido en el periodo
            SELECT p.name, COALESCE(SUM(od.quantity), 0)
            INTO out_producto_mas_vendido, out_cantidad_mas_vendido
            FROM orderdetail od
            JOIN "order" o ON o.id = od.order_id
            JOIN product p ON p.id = od.product_id
            WHERE o.created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND o.status != 'CANCELLED'
            GROUP BY p.id, p.name
            ORDER BY SUM(od.quantity) DESC
            LIMIT 1;

            -- Si no hay productos vendidos
            IF out_producto_mas_vendido IS NULL THEN
                out_producto_mas_vendido := 'N/A';
                out_cantidad_mas_vendido := 0;
            END IF;
        END;
        $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""

    # 3. Eliminar procedure de resumen de ventas
    op.execute("DROP PROCEDURE IF EXISTS sp_resumen_ventas")

    # 2. Eliminar trigger y tabla de auditoría
    op.execute('DROP TRIGGER IF EXISTS trg_audit_order ON "order"')
    op.execute("DROP FUNCTION IF EXISTS fn_audit_order()")
    op.drop_index('ix_order_audit_changed_at', table_name='order_audit')
    op.drop_index('ix_order_audit_action', table_name='order_audit')
    op.drop_index('ix_order_audit_order_id', table_name='order_audit')
    op.drop_table('order_audit')

    # 1. Eliminar procedure y restaurar trigger original
    op.execute("DROP PROCEDURE IF EXISTS sp_calcular_totales")
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_calcular_totales()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.subtotal := NEW.unit_price * NEW.quantity;

            UPDATE "order"
            SET total = COALESCE(
                (SELECT SUM(subtotal) FROM orderdetail WHERE order_id = NEW.order_id AND id != NEW.id), 0
            ) + NEW.subtotal
            WHERE id = NEW.order_id;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_calcular_totales
        BEFORE INSERT OR UPDATE ON orderdetail
        FOR EACH ROW
        EXECUTE FUNCTION fn_calcular_totales();
    """)
