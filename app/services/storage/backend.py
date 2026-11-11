from pathlib import Path
from typing import Protocol
from uuid import UUID


class StorageBackend(Protocol):
    def save(
        self,
        content: bytes,
        *,
        tenant_id: UUID,
        public_id: UUID,
        extension: str,
    ) -> str: ...

    def path_for(self, storage_uri: str) -> Path: ...
