from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.integrations.lightrag.errors import LightRAGError
from backend.models.nas_file import NasFile
from backend.services.document_parser import ParseResult
from backend.services.ingestion_service import build_lightrag_metadata, ingest_nas_file


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, value):
        self.value = value
        self.flush_count = 0

    async def execute(self, statement):
        return FakeResult(self.value)

    async def flush(self):
        self.flush_count += 1


def make_nas_file(status="queued"):
    return NasFile(
        id=uuid4(),
        nas_path="/mnt/nas/projects/a/SOP.pdf",
        folder_type="auto",
        status=status,
        file_hash="hash-1",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_ingestion_service_success_transitions_to_indexed():
    nas_file = make_nas_file()
    db = FakeSession(nas_file)
    client = AsyncMock()
    client.ingest_document.return_value = {"id": "doc-1", "status": "processing"}

    result = await ingest_nas_file(db, str(nas_file.id), client, "cid-1")

    assert result.status == "indexed"
    assert result.lightrag_doc_id == "doc-1"
    assert result.indexed_at is not None
    assert result.error_msg is None
    client.ingest_document.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingestion_service_missing_file_raises_404():
    db = FakeSession(None)
    client = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await ingest_nas_file(db, str(uuid4()), client, "cid-1")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ingestion_service_rejects_pending_review():
    nas_file = make_nas_file(status="pending_review")
    db = FakeSession(nas_file)
    client = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await ingest_nas_file(db, str(nas_file.id), client, "cid-1")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_ingestion_service_failure_marks_failed():
    nas_file = make_nas_file()
    db = FakeSession(nas_file)
    client = AsyncMock()
    client.ingest_document.side_effect = LightRAGError("boom", operation="ingest_document", status_code=500)

    result = await ingest_nas_file(db, str(nas_file.id), client, "cid-1")

    assert result.status == "failed"
    assert "boom" in result.error_msg


@pytest.mark.asyncio
async def test_ingestion_service_treats_duplicate_text_as_success(monkeypatch):
    nas_file = make_nas_file()
    db = FakeSession(nas_file)
    client = AsyncMock()
    monkeypatch.setattr(
        "backend.services.ingestion_service.parse_document_async",
        AsyncMock(return_value=ParseResult(text="hello world", parser_used="python-docx")),
    )
    client.ingest_text.side_effect = LightRAGError(
        "duplicate",
        operation="ingest_text",
        status_code=409,
        response_text='{"detail":"Document storage already contains"}',
    )

    result = await ingest_nas_file(db, str(nas_file.id), client, "cid-1")

    assert result.status == "indexed"
    assert result.lightrag_doc_id == "doc-5eb63bbbe01eeed093cb22bb8f5acdc3"
    client.delete_document.assert_not_called()
    client.ingest_text.assert_awaited_once()


def test_build_lightrag_metadata_includes_required_fields():
    nas_file = make_nas_file()

    metadata = build_lightrag_metadata(nas_file)

    assert metadata["source"] == "nas"
    assert metadata["nas_path"] == nas_file.nas_path
    assert metadata["folder"] == "/mnt/nas/projects/a"
    assert metadata["folder_type"] == "auto"
    assert metadata["uploaded_by"] == "system"
