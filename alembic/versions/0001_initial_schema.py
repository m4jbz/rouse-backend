"""initial schema – consolidated migration

Revision ID: 0001
Revises: None
Create Date: 2026-03-01 00:00:00.000000

Creates all tables, enums, indexes, stored procedures, triggers,
and seeds the default admin users.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pre-computed bcrypt hashes for seed users
ADMIN_HASH = "$2b$12$HBL7whG2KJZCl7VZsqKOtuimg.RntbYkgJ5phcN5cRiS2xfHlkz4G"  # admin123
EDITOR_HASH = "$2b$12$p42J3hKoTsAnCsOgzaH7b.Br6tprYg0kOVq./6GMEnkZEQDMgv3q6"  # editor123


def upgrade() -> None:
    # =================================================================
    # TABLAS SIN DEPENDENCIAS (orden: user, client, category)
    # =================================================================

    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "user", name="role"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    op.create_table(
        "client",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_email", "client", ["email"], unique=True)

    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # =================================================================
    # TABLAS CON FK SIMPLES
    # =================================================================

    op.create_table(
        "client_cart_item",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.String(length=200), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("product_price", sa.Float(), nullable=False),
        sa.Column("product_image", sa.String(length=500), nullable=False),
        sa.Column("product_badge", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_cart_item_client_id", "client_cart_item", ["client_id"])

    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_category_id", "product", ["category_id"])

    op.create_table(
        "productvariant",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_productvariant_product_id", "productvariant", ["product_id"])

    # =================================================================
    # TABLA ORDER (con enums)
    # =================================================================

    op.create_table(
        "order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_number", sa.String(length=50), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("client_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("delivery_address", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pendiente", "confirmado", "preparando",
                "en_camino", "entregado", "cancelado",
                name="orderstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            sa.Enum("efectivo", "tarjeta", "transferencia", name="paymentmethod"),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.Enum("pendiente", "pagado", name="paymentstatus"),
            nullable=False,
        ),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_number"),
    )
    op.create_index("ix_order_client_id", "order", ["client_id"])
    op.create_index("ix_order_status", "order", ["status"])

    # =================================================================
    # TABLA ORDERDETAIL
    # =================================================================

    op.create_table(
        "orderdetail",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("variant_name", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orderdetail_order_id", "orderdetail", ["order_id"])
    op.create_index("ix_orderdetail_product_id", "orderdetail", ["product_id"])

    # =================================================================
    # TABLA ORDER_AUDIT
    # =================================================================

    op.create_table(
        "order_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("old_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=True),
        sa.Column("old_payment_status", sa.String(length=50), nullable=True),
        sa.Column("new_payment_status", sa.String(length=50), nullable=True),
        sa.Column("old_total", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("new_total", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("changed_by", sa.String(length=100), server_default=sa.text("current_user"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_audit_order_id", "order_audit", ["order_id"])
    op.create_index("ix_order_audit_action", "order_audit", ["action"])
    op.create_index("ix_order_audit_changed_at", "order_audit", ["changed_at"])

    # =================================================================
    # STORED PROCEDURE: sp_calcular_totales
    # =================================================================

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

    # =================================================================
    # TRIGGER: fn_estado_segun_pago (auto-confirmar al pagar)
    # =================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_estado_segun_pago()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.payment_status IS DISTINCT FROM NEW.payment_status THEN
                IF NEW.payment_status = 'pagado' AND NEW.status = 'pendiente' THEN
                    NEW.status := 'confirmado';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_estado_segun_pago
        BEFORE UPDATE ON "order"
        FOR EACH ROW
        EXECUTE FUNCTION fn_estado_segun_pago();
    """)

    # =================================================================
    # TRIGGER: fn_audit_order (auditoría de cambios en órdenes)
    # =================================================================

    op.execute("""
        CREATE OR REPLACE FUNCTION fn_audit_order()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO order_audit (order_id, action, new_status, new_payment_status, new_total)
                VALUES (NEW.id, 'INSERT', NEW.status, NEW.payment_status, NEW.total);
                RETURN NEW;

            ELSIF TG_OP = 'UPDATE' THEN
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

    # =================================================================
    # STORED PROCEDURE: sp_resumen_ventas
    # =================================================================

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
            SELECT COUNT(*)
            INTO out_total_pedidos
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin;

            SELECT COALESCE(SUM(total), 0)
            INTO out_ingresos_totales
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status = 'entregado'
              AND payment_status = 'pagado';

            IF out_total_pedidos > 0 THEN
                SELECT COALESCE(AVG(total), 0)
                INTO out_ticket_promedio
                FROM "order"
                WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
                  AND status != 'cancelado';
            ELSE
                out_ticket_promedio := 0;
            END IF;

            SELECT COUNT(*)
            INTO out_pedidos_entregados
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status = 'entregado';

            SELECT COUNT(*)
            INTO out_pedidos_cancelados
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status = 'cancelado';

            SELECT COUNT(*)
            INTO out_pedidos_pendientes
            FROM "order"
            WHERE created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND status IN ('pendiente', 'confirmado', 'preparando', 'en_camino');

            SELECT p.name, COALESCE(SUM(od.quantity), 0)
            INTO out_producto_mas_vendido, out_cantidad_mas_vendido
            FROM orderdetail od
            JOIN "order" o ON o.id = od.order_id
            JOIN product p ON p.id = od.product_id
            WHERE o.created_at BETWEEN p_fecha_inicio AND p_fecha_fin
              AND o.status != 'cancelado'
            GROUP BY p.id, p.name
            ORDER BY SUM(od.quantity) DESC
            LIMIT 1;

            IF out_producto_mas_vendido IS NULL THEN
                out_producto_mas_vendido := 'N/A';
                out_cantidad_mas_vendido := 0;
            END IF;
        END;
        $$;
    """)

    # =================================================================
    # SEED: usuarios admin y editor
    # =================================================================

    op.execute(
        f"""
        INSERT INTO "user" (id, username, password_hash, is_active, role, created_at)
        VALUES
            (gen_random_uuid(), 'admin', '{ADMIN_HASH}', true, 'admin', NOW()),
            (gen_random_uuid(), 'editor', '{EDITOR_HASH}', true, 'user', NOW())
        """
    )


def downgrade() -> None:
    # Procedures y triggers
    op.execute("DROP PROCEDURE IF EXISTS sp_resumen_ventas")
    op.execute('DROP TRIGGER IF EXISTS trg_audit_order ON "order"')
    op.execute("DROP FUNCTION IF EXISTS fn_audit_order()")
    op.execute('DROP TRIGGER IF EXISTS trg_estado_segun_pago ON "order"')
    op.execute("DROP FUNCTION IF EXISTS fn_estado_segun_pago()")
    op.execute("DROP PROCEDURE IF EXISTS sp_calcular_totales")

    # Tablas (orden inverso de dependencias)
    op.drop_table("order_audit")
    op.drop_table("orderdetail")
    op.drop_table("order")
    op.drop_table("productvariant")
    op.drop_table("product")
    op.drop_table("client_cart_item")
    op.drop_table("category")
    op.drop_table("client")
    op.drop_table("user")

    # Enums
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS paymentmethod")
    op.execute("DROP TYPE IF EXISTS role")
