---
inclusion: fileMatch
fileMatchPattern: tests/**,conftest.py,**/test_*.py
---

# Test Conventions — SecondBrain

> Load khi làm việc với tests/ hoặc conftest.py.

---

## Test Structure (3 tầng)

```
tests/
├── conftest.py              ← shared fixtures
├── unit/                    ← không cần Docker, chạy nhanh
│   ├── backend/
│   │   ├── test_schemas.py
│   │   ├── test_auth_service.py
│   │   ├── test_wiki_builder.py
│   │   ├── test_middleware.py
│   │   └── test_routers.py
│   ├── nas_connector/
│   │   └── test_watcher.py
│   └── graphiti_service/
│       └── test_extractor.py
├── integration/             ← cần PostgreSQL + Redis
│   └── docker-compose.test.yml
└── qa/
    └── questions.md         ← 20 câu hỏi đánh giá chất lượng AI
```

---

## Run commands

```bash
# Unit tests — không cần Docker
pytest tests/unit/ -v

# Nhanh — dừng ngay khi fail đầu tiên
pytest tests/unit/ -x -q

# Integration tests — cần PostgreSQL
docker compose -f tests/docker-compose.test.yml up -d
pytest tests/integration/ -v
docker compose -f tests/docker-compose.test.yml down

# Chạy 1 file cụ thể
pytest tests/unit/backend/test_schemas.py -v

# Chạy theo pattern
pytest tests/ -k "test_nas_file" -v
```

---

## conftest.py — shared fixtures

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

@pytest.fixture
def fake_user():
    return {"id": "test-user-id", "email": "test@robolinks.vn", "role": "user"}

@pytest.fixture
def fake_admin():
    return {"id": "admin-id", "email": "admin@robolinks.vn", "role": "admin"}

@pytest.fixture
def client(fake_user):
    """FastAPI TestClient với auth mock"""
    from backend.main import app
    from backend.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_lightrag_query(monkeypatch):
    """Mock LightRAG query — không cần LightRAG service"""
    mock = AsyncMock(return_value={
        "response": "Motor Siemens 1LE1 7.5kW",
        "sources": [{"file": "BOM-Heineken-2024.xlsx"}]
    })
    monkeypatch.setattr("backend.integrations.lightrag.query.query", mock)
    return mock

@pytest.fixture
def mock_graphiti(monkeypatch):
    """Mock Graphiti — không cần graphiti-service"""
    mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr("backend.integrations.graphiti.extract", mock)
    return mock
```

---

## Test naming convention

```python
# Pattern: test_{module}_{scenario}_{expected_outcome}

def test_nas_file_transitions_to_indexed_after_approval(): ...
def test_chat_router_returns_streaming_response(): ...
def test_wiki_builder_assembles_entity_page_with_relations(): ...
def test_auth_service_rejects_expired_token(): ...
def test_lightrag_client_forwards_correlation_id(): ...
```

---

## Unit test patterns

### Test schema validation
```python
# tests/unit/backend/test_schemas.py
import pytest
from pydantic import ValidationError
from backend.schemas.chat import ChatRequest

def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="", conversation_id=None)

def test_chat_request_strips_whitespace():
    req = ChatRequest(message="  Heineken dùng motor gì?  ")
    assert req.message == "Heineken dùng motor gì?"
```

### Test router với mock
```python
# tests/unit/backend/test_routers.py
def test_chat_returns_sse_content_type(client, mock_lightrag_query):
    response = client.post(
        "/api/chat/stream",
        json={"message": "Heineken dùng motor gì?"}
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

def test_admin_queue_requires_admin_role(client):
    # client fixture dùng fake_user (role="user"), không phải admin
    response = client.get("/api/admin/nas/queue")
    assert response.status_code == 403
```

### Test NAS connector với fake filesystem
```python
# tests/unit/nas_connector/test_watcher.py
import pytest
from pathlib import Path
from nas_connector.watcher import detect_new_files

def test_watcher_detects_new_pdf(tmp_path):
    # tmp_path là pytest fixture — tạo thư mục tạm, tự xóa sau test
    (tmp_path / "SOP-onboarding.pdf").write_bytes(b"fake pdf content")

    known_files = {}  # chưa có file nào được track
    new_files = detect_new_files(str(tmp_path), known_files)

    assert len(new_files) == 1
    assert new_files[0]["name"] == "SOP-onboarding.pdf"

def test_watcher_ignores_unsupported_extensions(tmp_path):
    (tmp_path / "drawing.dwg").write_bytes(b"cad data")
    (tmp_path / "report.pdf").write_bytes(b"pdf data")

    new_files = detect_new_files(str(tmp_path), {})
    names = [f["name"] for f in new_files]

    assert "report.pdf" in names
    assert "drawing.dwg" not in names  # DWG → metadata only, handled separately
```

---

## Integration test pattern

```python
# tests/integration/backend/test_models.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest_asyncio.fixture
async def db_session():
    # Dùng DB test riêng (docker-compose.test.yml)
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/secondbrain_test")
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_nas_file_crud(db_session):
    from backend.models.nas_file import NasFile
    from backend.models.base import Base

    file = NasFile(
        nas_path="/projects/Heineken-2024/BOM.xlsx",
        folder_type="auto",
        status="QUEUED"
    )
    db_session.add(file)
    await db_session.commit()

    result = await db_session.get(NasFile, file.id)
    assert result.status == "QUEUED"
    assert result.nas_path == "/projects/Heineken-2024/BOM.xlsx"
```

---

## Coverage target

- `backend/schemas/` → 95%+
- `backend/services/` → 80%+
- `backend/integrations/` → 70%+ (với mock HTTP)
- `nas-connector/` → 70%+
- Overall unit → 80%+
