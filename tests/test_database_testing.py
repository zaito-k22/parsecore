import pytest
from pydantic_settings import SettingsConfigDict

from app.db import testing
from app.db.testing import TestDatabaseConfigurationError as DatabaseConfigurationError
from app.db.testing import load_test_database_url


def test_load_test_database_url_rejects_invalid_utf8_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_bytes(b"TEST_DB_PASSWORD=fake-secret-value-\xff\n")

    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DB_PASSWORD", raising=False)
    monkeypatch.setattr(testing, "TEST_ENV_FILE", env_file)
    monkeypatch.setattr(
        testing._TestDatabaseEnvironment,
        "model_config",
        SettingsConfigDict(
            env_file=env_file,
            env_file_encoding="utf-8",
            extra="ignore",
        ),
    )

    with pytest.raises(DatabaseConfigurationError) as exc_info:
        load_test_database_url()

    message = str(exc_info.value)
    assert message == "TEST_DB_PASSWORD no está definida correctamente en .env.test."
    assert "fake-secret-value" not in message
    assert isinstance(exc_info.value.__context__, UnicodeDecodeError)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
