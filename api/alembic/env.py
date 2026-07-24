from __future__ import annotations

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.infrastructure.config.settings import get_settings
from app.infrastructure.persistence.database import Base, normalize_database_url
from app.infrastructure.persistence.models import base_model  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configured_database_url() -> str:
    environment_database_url = os.getenv("DATABASE_URL")
    if environment_database_url:
        return normalize_database_url(environment_database_url)

    configured_option = config.get_main_option("sqlalchemy.url")
    if configured_option:
        return normalize_database_url(configured_option)
    return normalize_database_url(get_settings().database_url)


def run_migrations_offline() -> None:
    url = _configured_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _configured_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
