"""Add section to category, size/flavor to variants, custom cake tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-30

Adds:
- section field to category table (pasteles, postres)
- size and flavor fields to product_variant table
- cake_flavor, cake_filling, cake_topping tables (predefined options)
- custom_cake_request table for custom cake orders
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =================================================================
    # 1. Add 'section' column to category table
    # =================================================================
    op.add_column(
        "category",
        sa.Column("section", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_category_section", "category", ["section"])

    # =================================================================
    # 2. Add 'size' and 'flavor' columns to product_variant table
    # =================================================================
    op.add_column(
        "product_variant",
        sa.Column("size", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "product_variant",
        sa.Column("flavor", sa.String(length=100), nullable=True),
    )

    # =================================================================
    # 3. Create cake_flavor table (predefined flavors)
    # =================================================================
    op.create_table(
        "cake_flavor",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default flavors
    op.execute("""
        INSERT INTO cake_flavor (name) VALUES
        ('Vainilla'),
        ('Chocolate'),
        ('Red Velvet'),
        ('Zanahoria'),
        ('Limón'),
        ('Café'),
        ('Fresa'),
        ('Durazno'),
        ('Coco'),
        ('Nuez')
    """)

    # =================================================================
    # 4. Create cake_filling table (predefined fillings)
    # =================================================================
    op.create_table(
        "cake_filling",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default fillings
    op.execute("""
        INSERT INTO cake_filling (name) VALUES
        ('Crema pastelera'),
        ('Nutella'),
        ('Cajeta'),
        ('Queso crema'),
        ('Frutas frescas'),
        ('Mermelada de fresa'),
        ('Dulce de leche'),
        ('Crema de chocolate'),
        ('Crema de avellana'),
        ('Sin relleno')
    """)

    # =================================================================
    # 5. Create cake_topping table (predefined toppings)
    # =================================================================
    op.create_table(
        "cake_topping",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default toppings
    op.execute("""
        INSERT INTO cake_topping (name) VALUES
        ('Fondant'),
        ('Buttercream'),
        ('Ganache de chocolate'),
        ('Crema batida'),
        ('Glaseado'),
        ('Merengue'),
        ('Frutas'),
        ('Chantilly'),
        ('Chocolate rallado'),
        ('Sin cobertura')
    """)

    # =================================================================
    # 6. Create custom_cake_request table with ENUM
    # Note: The ENUM type will be created automatically by SQLAlchemy
    # =================================================================
    op.create_table(
        "custom_cake_request",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("client_name", sa.String(length=150), nullable=False),
        sa.Column("client_email", sa.String(length=255), nullable=False),
        sa.Column("client_phone", sa.String(length=20), nullable=False),
        sa.Column("cake_size", sa.String(length=50), nullable=False),  # chico, mediano, grande
        sa.Column("cake_layers", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("cake_flavor", sa.String(length=100), nullable=False),
        sa.Column("filling", sa.String(length=100), nullable=True),
        sa.Column("topping", sa.String(length=100), nullable=True),
        sa.Column("custom_text", sa.String(length=500), nullable=True),
        sa.Column("reference_images", sa.JSON(), nullable=True),  # Array of URLs
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("delivery_time", sa.String(length=50), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pendiente", "cotizado", "aceptado",
                "en_proceso", "completado", "cancelado",
                name="customcakerequeststatus",
                create_type=True,  # Let SQLAlchemy create the ENUM
            ),
            server_default=sa.text("'pendiente'"),
            nullable=False,
        ),
        sa.Column("quoted_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custom_cake_request_client_id", "custom_cake_request", ["client_id"])
    op.create_index("ix_custom_cake_request_status", "custom_cake_request", ["status"])
    op.create_index("ix_custom_cake_request_delivery_date", "custom_cake_request", ["delivery_date"])


def downgrade() -> None:
    # Drop custom_cake_request table
    op.drop_index("ix_custom_cake_request_delivery_date", table_name="custom_cake_request")
    op.drop_index("ix_custom_cake_request_status", table_name="custom_cake_request")
    op.drop_index("ix_custom_cake_request_client_id", table_name="custom_cake_request")
    op.drop_table("custom_cake_request")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS customcakerequeststatus")

    # Drop cake options tables
    op.drop_table("cake_topping")
    op.drop_table("cake_filling")
    op.drop_table("cake_flavor")

    # Remove columns from product_variant
    op.drop_column("product_variant", "flavor")
    op.drop_column("product_variant", "size")

    # Remove section column from category
    op.drop_index("ix_category_section", table_name="category")
    op.drop_column("category", "section")
