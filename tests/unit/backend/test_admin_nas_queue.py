from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from backend.database import get_session
from backend.dependencies.services import get_lightrag_ingest_client
from backend.main import app
from backend.models.nas_file import NasFile


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, value):
        self.value = value

    async def execute(self, statement):
        return FakeResult(self.value)

    async def flush(self):
        pass


def make_pending_file():
    return NasFile(
        id=uuid4(),
        nas_path="/mnt/nas/manual/SOP.pdf",
        folder_type="manual",
        status="pending_review",
        file_hash="hash-1",
        created_at=datetime.now(timezone.utc),
    )


def override_db(fake_session):
    async def _override():
        yield fake_session

    app.dependency_overrides[get_session] = _override


def test_admin_nas_queue_router_imports():
    from backend.routers.admin import nas_queue

    assert nas_queue.router is not None


def test_admin_nas_queue_approve_triggers_ingestion(admin_client):
    nas_file = make_pending_file()
    fake_client = AsyncMock()
    fake_client.ingest_document.return_value = {"id": "doc-1", "status": "processing"}
    override_db(FakeSession(nas_file))
    app.dependency_overrides[get_lightrag_ingest_client] = lambda: fake_client

    response = admin_client.post(f"/api/admin/nas/queue/{nas_file.id}/action", json={"approve": True})

    assert response.status_code == 200
    assert response.json()["status"] == "indexed"
    assert nas_file.approved_by == "admin-id"
    assert nas_file.approved_at is not None
    fake_client.ingest_document.assert_awaited_once()


def test_admin_nas_queue_reject_does_not_trigger_ingestion(admin_client):
    nas_file = make_pending_file()
    fake_client = AsyncMock()
    override_db(FakeSession(nas_file))
    app.dependency_overrides[get_lightrag_ingest_client] = lambda: fake_client

    response = admin_client.post(
        f"/api/admin/nas/queue/{nas_file.id}/action",
        json={"approve": False, "reject_reason": "not needed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    fake_client.ingest_document.assert_not_awaited()
