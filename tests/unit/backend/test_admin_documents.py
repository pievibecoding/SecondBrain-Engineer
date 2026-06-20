from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from backend.database import get_session
from backend.dependencies.services import get_lightrag_ingest_client
from backend.integrations.lightrag.errors import LightRAGError
from backend.main import app
from backend.models.nas_file import NasFile


class FakeScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeResult:
    def __init__(self, values):
        self.values = values

    def scalar_one_or_none(self):
        if isinstance(self.values, list):
            return self.values[0] if self.values else None
        return self.values

    def scalars(self):
        return FakeScalarResult(self.values if isinstance(self.values, list) else [self.values])


class FakeSession:
    def __init__(self, files):
        self.files = files
        self.flush_count = 0
        self.delete_count = 0

    async def execute(self, statement):
        params = statement.compile().params
        values = list(self.files)
        if "status_1" in params:
            values = [file for file in values if file.status == params["status_1"]]
        if "id_1" in params:
            values = [file for file in values if str(file.id) == str(params["id_1"])]
        return FakeResult(values)

    async def flush(self):
        self.flush_count += 1

    async def delete(self, item):
        self.delete_count += 1
        self.files = [file for file in self.files if file is not item]


def make_file(status="indexed", lightrag_doc_id=None):
    return NasFile(
        id=uuid4(),
        nas_path="/mnt/nas/projects/a/SOP.pdf",
        folder_type="auto",
        status=status,
        file_hash="hash-1",
        lightrag_doc_id=lightrag_doc_id,
        created_at=datetime.now(timezone.utc),
    )


def override_db(fake_session):
    async def _override():
        yield fake_session

    app.dependency_overrides[get_session] = _override


def test_admin_documents_list_filters_by_status(admin_client):
    failed = make_file(status="failed")
    indexed = make_file(status="indexed")
    override_db(FakeSession([failed, indexed]))

    response = admin_client.get("/api/admin/documents?status=failed")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "failed"


def test_admin_documents_non_admin_rejected(client):
    override_db(FakeSession([]))

    response = client.get("/api/admin/documents")

    assert response.status_code == 403


def test_admin_documents_reindex_calls_ingestion(admin_client):
    nas_file = make_file(status="failed")
    fake_session = FakeSession([nas_file])
    fake_client = AsyncMock()
    fake_client.ingest_document.return_value = {"id": "doc-1", "status": "processing"}
    override_db(fake_session)
    app.dependency_overrides[get_lightrag_ingest_client] = lambda: fake_client

    response = admin_client.post(f"/api/admin/documents/{nas_file.id}/reindex")

    assert response.status_code == 200
    assert response.json()["status"] == "indexed"
    assert nas_file.lightrag_doc_id == "doc-1"
    fake_client.ingest_document.assert_awaited_once()


def test_admin_documents_delete_calls_lightrag(admin_client):
    nas_file = make_file(status="indexed", lightrag_doc_id="doc-1")
    fake_client = AsyncMock()
    fake_client.delete_document.return_value = {"status": "deleted"}
    fake_session = FakeSession([nas_file])
    override_db(fake_session)
    app.dependency_overrides[get_lightrag_ingest_client] = lambda: fake_client

    response = admin_client.delete(f"/api/admin/documents/{nas_file.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_session.delete_count == 1
    assert fake_session.files == []
    fake_client.delete_document.assert_awaited_once_with("doc-1", response.headers["x-correlation-id"])


def test_admin_documents_delete_preserves_state_on_lightrag_error(admin_client):
    nas_file = make_file(status="indexed", lightrag_doc_id="doc-1")
    fake_client = AsyncMock()
    fake_client.delete_document.side_effect = LightRAGError("boom", operation="delete_document")
    override_db(FakeSession([nas_file]))
    app.dependency_overrides[get_lightrag_ingest_client] = lambda: fake_client

    response = admin_client.delete(f"/api/admin/documents/{nas_file.id}")

    assert response.status_code == 502
    assert nas_file.status == "indexed"
    assert nas_file.reject_reason is None


def test_admin_documents_delete_ignores_missing_lightrag_doc(admin_client):
    nas_file = make_file(status="indexed", lightrag_doc_id="doc-missing")
    fake_client = AsyncMock()
    fake_client.delete_document.side_effect = LightRAGError("missing", operation="delete_document", status_code=404)
    fake_session = FakeSession([nas_file])
    override_db(fake_session)
    app.dependency_overrides[get_lightrag_ingest_client] = lambda: fake_client

    response = admin_client.delete(f"/api/admin/documents/{nas_file.id}")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_session.delete_count == 1
    assert fake_session.files == []
