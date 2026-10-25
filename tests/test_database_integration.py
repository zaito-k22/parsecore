import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def test_database_connection_and_safe_query(test_db_engine):
    with test_db_engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

        database, user = connection.execute(
            text("SELECT current_database(), current_user")
        ).one()

    assert database == "parsecore_test"
    assert user == "parsecore_test"
