from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Engine, create_engine

from app.db.testing import TestDatabaseConfigurationError, load_test_database_url


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
