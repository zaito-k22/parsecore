from datetime import UTC, datetime
from uuid import uuid4

from app.services.storage.local import LocalStorageBackend


def test_local_storage_path_and_content(tmp_path):
    storage = LocalStorageBackend(tmp_path)
    tenant_id = uuid4()
    public_id = uuid4()
    content = b"%PDF-1.4 synthetic"

    storage_uri = storage.save(
        content,
        tenant_id=tenant_id,
        public_id=public_id,
        extension=".PDF",
    )

    expected = (
        f"{tenant_id}/{datetime.now(UTC).year}/{public_id}.pdf"
    )

    assert storage_uri == expected
    assert storage.path_for(storage_uri).read_bytes() == content


def test_local_storage_rejects_unsafe_extension(tmp_path):
    storage = LocalStorageBackend(tmp_path)
    public_id = uuid4()

    storage_uri = storage.save(
        b"synthetic",
        tenant_id=uuid4(),
        public_id=public_id,
        extension="../../secret",
    )

    assert storage_uri.endswith(f"{public_id}.bin")
    assert storage.path_for(storage_uri).read_bytes() == b"synthetic"
