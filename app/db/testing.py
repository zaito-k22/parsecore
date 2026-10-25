import os
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"

TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"
TEST_DB_DRIVER = "postgresql+psycopg"
TEST_DB_USER = "parsecore_test"
TEST_DB_HOST = "127.0.0.1"
TEST_DB_PORT = 55432
TEST_DB_NAME = "parsecore_test"

_EXPECTED_URL = (
    f"{TEST_DB_DRIVER}://{TEST_DB_USER}:<password>@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
)


class TestDatabaseConfigurationError(RuntimeError):
    """Falta la configuración local necesaria para las pruebas de base de datos."""


class UnsafeTestDatabaseError(RuntimeError):
    """La URL de pruebas no apunta a la base aislada esperada."""


class _TestDatabaseEnvironment(BaseSettings):
    test_db_password: SecretStr

    model_config = SettingsConfigDict(
        env_file=TEST_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_test_database_url() -> URL:
    override = os.environ.get(TEST_DATABASE_URL_ENV)

    if override:
        return require_safe_test_database_url(override)

    if not TEST_ENV_FILE.is_file():
        raise TestDatabaseConfigurationError(
            "No existe .env.test. Créalo a partir de compose.test.env.example "
            "antes de ejecutar pruebas de base de datos."
        )

    try:
        password = _TestDatabaseEnvironment().test_db_password.get_secret_value()
    except (OSError, ValueError):
        raise TestDatabaseConfigurationError(
            "TEST_DB_PASSWORD no está definida correctamente en .env.test."
        ) from None

    if not password:
        raise TestDatabaseConfigurationError("TEST_DB_PASSWORD no puede estar vacía.")

    url = URL.create(
        drivername=TEST_DB_DRIVER,
        username=TEST_DB_USER,
        password=password,
        host=TEST_DB_HOST,
        port=TEST_DB_PORT,
        database=TEST_DB_NAME,
    )

    return require_safe_test_database_url(url)


def require_safe_test_database_url(raw_url: str | URL) -> URL:
    if isinstance(raw_url, URL):
        url = raw_url
    else:
        try:
            url = make_url(raw_url)
        except (ArgumentError, ValueError):
            raise UnsafeTestDatabaseError(
                f"La URL de pruebas no es válida. Se exige {_EXPECTED_URL}."
            ) from None

    is_safe = (
        url.drivername == TEST_DB_DRIVER
        and url.username == TEST_DB_USER
        and url.host == TEST_DB_HOST
        and url.port == TEST_DB_PORT
        and url.database == TEST_DB_NAME
        and bool(url.password)
        and not url.query
    )

    if not is_safe:
        raise UnsafeTestDatabaseError(
            f"La URL de pruebas no corresponde a la base aislada. Se exige {_EXPECTED_URL}."
        )

    return url


def main() -> None:
    require_safe_test_database_url(load_test_database_url())
    print("Configuración de base de datos de pruebas validada; no se ha conectado.")


if __name__ == "__main__":
    main()
