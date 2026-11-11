import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.tenants import DEFAULT_TENANT_ID
from app.db.testing import TestDatabaseConfigurationError, load_test_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def test_database_url():
    try:
        return load_test_database_url()
    except TestDatabaseConfigurationError as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="session")
def test_db_engine(test_database_url) -> Iterator[Engine]:
    engine = create_engine(test_database_url, pool_pre_ping=True)

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def alembic_config(test_database_url) -> Iterator[Config]:
    previous = os.environ.get("TEST_DATABASE_URL")
    os.environ["TEST_DATABASE_URL"] = test_database_url.render_as_string(
        hide_password=False
    )
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    try:
        yield config
    finally:
        if previous is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def migrated_database(alembic_config) -> Config:
    command.upgrade(alembic_config, "head")
    return alembic_config


@pytest.fixture
def db_session(migrated_database, test_db_engine) -> Iterator[Session]:
    session_factory = sessionmaker(
        bind=test_db_engine,
        autoflush=False,
        autocommit=False,
    )
    session = session_factory()

    session.execute(
        text("TRUNCATE audit_events, extractions, invoices RESTART IDENTITY CASCADE")
    )
    session.execute(
        text(
            "INSERT INTO tenants (id, name) VALUES "
            "(CAST(:tenant_id AS uuid), 'default') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"tenant_id": DEFAULT_TENANT_ID},
    )
    session.commit()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
