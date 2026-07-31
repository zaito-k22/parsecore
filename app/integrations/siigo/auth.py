from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import settings


@dataclass
class SiigoToken:
    access_token: str
    expires_in: int
    token_type: str


class SiigoAuth:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls._instance.base_url = settings.siigo_base_url.rstrip("/")
            cls._instance._token = None
            cls._instance._expires_at = None

        return cls._instance

    async def authenticate(self) -> SiigoToken:
        if (
            self._token is not None
            and self._expires_at is not None
            and datetime.now(UTC) < self._expires_at
        ):
            return self._token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/auth",
                json={
                    "username": settings.siigo_username,
                    "access_key": settings.siigo_access_key,
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )

        if response.is_error:
            raise Exception(
                f"Siigo respondió {response.status_code}: {response.text}"
            )

        data = response.json()

        token = SiigoToken(
            access_token=data["access_token"],
            expires_in=data["expires_in"],
            token_type=data["token_type"],
        )

        self._token = token

        # Renovar 5 minutos antes de expirar
        self._expires_at = datetime.now(UTC) + timedelta(
            seconds=token.expires_in - 300
        )

        return token