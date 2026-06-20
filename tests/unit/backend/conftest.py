import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/secondbrain_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from backend.main import app
from backend.dependencies.auth import get_current_user
from backend.schemas.auth import UserResponse
from unittest.mock import AsyncMock


@pytest.fixture
def fake_user():
    return {"id": "test-user-id", "email": "test@robolinks.vn", "role": "user", "username": "testuser", "created_at": "2026-01-01T00:00:00"}


@pytest.fixture
def fake_admin():
    return {"id": "admin-id", "email": "admin@robolinks.vn", "role": "admin", "username": "admin", "created_at": "2026-01-01T00:00:00"}


@pytest.fixture
def client(fake_user):
    app.dependency_overrides[get_current_user] = lambda: UserResponse.model_validate(fake_user)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(fake_admin):
    app.dependency_overrides[get_current_user] = lambda: UserResponse.model_validate(fake_admin)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_lightrag_query(monkeypatch):
    mock = AsyncMock(return_value={"response": "Motor Siemens 1LE1 7.5kW", "sources": [{"file": "BOM-Heineken-2024.xlsx"}]})
    monkeypatch.setattr("backend.integrations.lightrag.query.query", mock)
    return mock


@pytest.fixture
def mock_graphiti(monkeypatch):
    mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr("backend.integrations.graphiti.extract", mock)
    return mock
