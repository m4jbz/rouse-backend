"""update user schema: remove email/name, add username, seed admin users

Revision ID: e4f5a6b7c8d9
Revises: c3a4b5d6e7f8
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "e4f5a6b7c8d9"
down_revision = "c3a4b5d6e7f8"
branch_labels = None
depends_on = None

# Pre-computed bcrypt hashes
ADMIN_HASH = "$2b$12$HBL7whG2KJZCl7VZsqKOtuimg.RntbYkgJ5phcN5cRiS2xfHlkz4G"  # admin123
EDITOR_HASH = "$2b$12$p42J3hKoTsAnCsOgzaH7b.Br6tprYg0kOVq./6GMEnkZEQDMgv3q6"  # editor123


def upgrade() -> None:
    # 1. Add username column (nullable first so we can populate)
    op.add_column("user", sa.Column("username", sa.String(100), nullable=True))

    # 2. Drop old columns
    op.drop_index("ix_user_email", table_name="user")
    op.drop_column("user", "email")
    op.drop_column("user", "name")

    # 3. Delete any existing users (clean slate for admin seed)
    op.execute("DELETE FROM \"user\"")

    # 4. Make username NOT NULL and add unique index
    op.alter_column("user", "username", nullable=False)
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    # 5. Update is_active default to True
    op.alter_column(
        "user",
        "is_active",
        server_default=sa.text("true"),
    )

    # 6. Seed admin and editor users
    op.execute(
        f"""
        INSERT INTO "user" (id, username, password_hash, is_active, role, created_at)
        VALUES
            (gen_random_uuid(), 'admin', '{ADMIN_HASH}', true, 'ADMIN', NOW()),
            (gen_random_uuid(), 'editor', '{EDITOR_HASH}', true, 'USER', NOW())
        """
    )


def downgrade() -> None:
    # Remove seeded users
    op.execute("DELETE FROM \"user\" WHERE username IN ('admin', 'editor')")

    # Drop username
    op.drop_index("ix_user_username", table_name="user")
    op.drop_column("user", "username")

    # Re-add email and name
    op.add_column("user", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("name", sa.String(255), nullable=True))
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    # Revert is_active default
    op.alter_column("user", "is_active", server_default=sa.text("false"))
