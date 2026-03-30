"""
Alembic Environment Configuration
"""
import asyncio
from logging.config import fileConfig

import sqlalchemy as sa
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

import os

from app.core.config import get_settings

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No models metadata for now - we use manual migrations
target_metadata = None


def get_url():
    """Get database URL from environment or config"""
    settings = get_settings()
    url = os.getenv("DATABASE_URL") or settings.database_url or config.get_main_option("sqlalchemy.url")

    if not url or url.startswith("driver://"):
        raise RuntimeError("DATABASE_URL is not configured for Alembic migrations")

    if url and url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()

    if url and "+asyncpg" in url:
        asyncio.run(run_migrations_online_async(url))
        return

    configuration = config.get_section(config.config_ini_section) or {}
    if not url:
        raise RuntimeError("DATABASE_URL is not configured for Alembic migrations")
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


def do_run_migrations(connection) -> None:
    dialect_name = connection.dialect.name
    if dialect_name == "postgresql":
        connection.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(128) NOT NULL PRIMARY KEY
                )
                """
            )
        )
        connection.execute(
            sa.text(
                "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
            )
        )
        if connection.in_transaction():
            connection.commit()

    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online_async(url: str) -> None:
    connectable = create_async_engine(url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
