import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL, make_url

import app.models  # noqa: F401  (registra los modelos en Base.metadata)
from app.db.base import Base
from app.db.testing import TEST_DATABASE_URL_ENV, require_safe_test_database_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def _get_database_url() -> URL:
    test_database_url = os.environ.get(TEST_DATABASE_URL_ENV)

    if test_database_url:
        return require_safe_test_database_url(test_database_url)

    from app.core.config import settings

    return make_url(settings.database_url)


_database_url = _get_database_url()
config.set_main_option(
    "sqlalchemy.url",
    _database_url.render_as_string(hide_password=True).replace("%", "%%"),
)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

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
    """Run migrations in 'online' mode."""

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()