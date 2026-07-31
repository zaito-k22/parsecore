from typing import Any

import httpx

from app.core.config import settings
from app.integrations.siigo.auth import SiigoAuth


class SiigoClient:
    _client: httpx.AsyncClient | None = None

    def __init__(self):
        self.base_url = f"{settings.siigo_base_url.rstrip('/')}/v1"
        self.auth = SiigoAuth()

    async def _http_client(self) -> httpx.AsyncClient:
        if self.__class__._client is None:
            self.__class__._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )

        return self.__class__._client

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        token = await self.auth.authenticate()

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Partner-Id": settings.siigo_partner_id,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        client = await self._http_client()

        response = await client.request(
            method=method,
            url=f"{self.base_url}{endpoint}",
            headers=headers,
            params=params,
            json=json,
        )

        if response.is_error:
            raise Exception(
                f"Siigo respondió {response.status_code}:\n{response.text}"
            )

        if response.content:
            return response.json()

        return {}

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            endpoint,
            params=params,
        )

    async def post(
        self,
        endpoint: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            endpoint,
            json=body,
        )

    async def put(
        self,
        endpoint: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._request(
            "PUT",
            endpoint,
            json=body,
        )

    async def delete(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            endpoint,
        )