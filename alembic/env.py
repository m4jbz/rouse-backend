from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Importar los modelos de SQLModel para que Alembic los detecte
# y la config para obtener la DATABASE_URL
from sqlmodel import SQLModel

from app.core.config import settings
from app.models import *  # noqa: F401, F403 - necesario para registrar todos los modelos

config = context.config

# Setear la URL de la DB desde nuestro .env en vez de hardcodearla en alembic.ini
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Apuntar al metadata de SQLModel que contiene todos nuestros modelos
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
