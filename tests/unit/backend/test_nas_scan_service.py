from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.models.nas_file import NasFile
from backend.models.nas_folder import NasFolder
from backend.services.nas_scan_service import scan_nas_folder


class FakeResult:
    def __init__(self, values, value=None):
        self.values = values
        self.value = value

    def scalars(self):
        return self

    def all(self):
        return self.values

    def scalar_one_or_none(self):
        return self.value if self.value is not None else (self.values[0] if self.values else None)


class FakeSession:
    def __init__(self, files):
        self.files = files
        self.flush_count = 0
        self.add_count = 0

    async def execute(self, statement):
        params = statement.compile().params
        values = list(self.files)
        if any(key.endswith("id_1") or key == "id_1" for key in params):
            target_id = next((value for key, value in params.items() if key.endswith("id_1") or key == "id_1"), None)
            match = next((item for item in values if str(item.id) == str(target_id)), None)
            return FakeResult([match] if match else [], match)
        pattern = next((value for value in params.values() if isinstance(value, str) and value.endswith("%")), None)
        if pattern:
            prefix = pattern[:-1]
            values = [item for item in values if item.nas_path.startswith(prefix)]
        return FakeResult(values)

    async def flush(self):
        self.flush_count += 1

    def add(self, item):
        self.add_count += 1
        self.files.append(item)


def make_folder(tmp_path: Path, folder_type: str = "manual") -> NasFolder:
    return NasFolder(
        id=uuid4(),
        path=str(tmp_path),
        folder_type=folder_type,
        is_active=True,
        last_scanned=None,
        created_at=datetime.now(timezone.utc),
    )


def make_file(path: Path, status: str = "indexed", file_hash: str = "hash-1") -> NasFile:
    return NasFile(
        id=uuid4(),
        nas_path=str(path),
        folder_type="manual",
        status=status,
        file_hash=file_hash,
        lightrag_doc_id="doc-1" if status == "indexed" else None,
        reject_reason=None,
        error_msg=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_scan_manual_folder_creates_queue_and_marks_deleted(tmp_path):
    supported = tmp_path / "spec.docx"
    supported.write_bytes(b"not a real docx but good enough for hash")
    missing = tmp_path / "missing.pdf"
    existing_missing = make_file(missing, status="indexed", file_hash="old-hash")
    fake_session = FakeSession([existing_missing])
    fake_client = AsyncMock()
    folder = make_folder(tmp_path, folder_type="manual")

    result = await scan_nas_folder(fake_session, folder, fake_client, correlation_id="cid-1")

    assert result.new_count == 1
    assert result.updated_count == 0
    assert result.deleted_count == 1
    assert result.queued_count == 1
    assert result.ingested_count == 0
    assert result.error_count == 0
    assert folder.last_scanned is not None
    assert existing_missing.status == "rejected"
    assert existing_missing.reject_reason == "File deleted from NAS"


@pytest.mark.asyncio
async def test_scan_auto_folder_ingests_immediately(tmp_path):
    supported = tmp_path / "auto.docx"
    supported.write_bytes(b"fake docx payload")
    fake_session = FakeSession([])
    fake_client = SimpleNamespace(
        ingest_document=AsyncMock(return_value={"id": "doc-1", "status": "processing"})
    )
    folder = make_folder(tmp_path, folder_type="auto")

    result = await scan_nas_folder(fake_session, folder, fake_client, correlation_id="cid-2")

    assert result.new_count == 1
    assert result.queued_count == 1
    assert result.ingested_count == 1
    assert result.error_count == 0
    assert fake_client.ingest_document.await_count == 1
