import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.services.storage.backend import StorageBackend

_SAFE_EXTENSION = re.compile(r"^\.[a-z0-9]{1,10}$")


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def save(
        self,
        content: bytes,
        *,
        tenant_id: UUID,
        public_id: UUID,
        extension: str,
    ) -> str:
        suffix = self._safe_extension(extension)
        year = datetime.now(UTC).year
        relative_path = Path(str(tenant_id)) / str(year) / f"{public_id}{suffix}"
        destination = self.root / relative_path

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)

        return relative_path.as_posix()

    def path_for(self, storage_uri: str) -> Path:
        return self.root / storage_uri

    def _safe_extension(self, extension: str) -> str:
        normalized = extension.strip().lower()

        if _SAFE_EXTENSION.fullmatch(normalized):
            return normalized

        return ".bin"
