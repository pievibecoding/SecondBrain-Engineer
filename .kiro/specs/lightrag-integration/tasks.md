# Implementation Plan: LightRAG Integration + Ingestion Pipeline

## Overview

Xay dung Spec 4 cho SecondBrain: LightRAG HTTP clients, ingestion service, admin document endpoints, va integration trigger tu NAS approval sang LightRAG ingest.

Spec nay chi implement backend integration. Khong can LightRAG service that trong unit tests; dung `pytest-httpx` va dependency overrides.

---

## Tasks

- [x] 1. Khoi tao LightRAG integration package
  - Ensure folder `backend/integrations/lightrag/` ton tai
  - Tao/update files:
    ```text
    backend/integrations/lightrag/
    ├── __init__.py
    ├── errors.py
    ├── ingest.py
    ├── query.py
    └── graph.py
    ```
  - Ensure test dependency `pytest-httpx` co trong dev/test requirements neu chua co
  - _Requirements: 1, 2, 3, 4, 10, 13_

---

- [x] 2. Viet `backend/integrations/lightrag/errors.py`
  - Define `LightRAGError`
  - Define `LightRAGTimeoutError(LightRAGError)`
  - Define `LightRAGNotFoundError(LightRAGError)`
  - Store context fields:
    - `operation: str`
    - `status_code: int | None`
    - `response_text: str | None`
  - Ensure `str(error)` is safe for logs and does not expose secrets
  - _Requirements: 4.1-4.5_

---

- [x] 3. Viet `backend/integrations/lightrag/ingest.py`
  - Implement `LightRAGIngestClient`
  - Constructor:
    ```python
    def __init__(self, base_url: str, timeout: float = 30.0) -> None
    ```
  - Implement:
    ```python
    async def ingest_document(file_path: str, metadata: dict, correlation_id: str) -> dict
    async def delete_document(doc_id: str, correlation_id: str) -> dict
    ```
  - `ingest_document()` calls `POST {base_url}/api/v1/docs`
  - Payload:
    ```json
    {"file_path": "...", "metadata": {...}}
    ```
  - `delete_document()` calls `DELETE {base_url}/api/v1/docs/{doc_id}`
  - Include headers:
    - `X-Correlation-ID`
    - `Content-Type: application/json` for POST
  - Use `httpx.AsyncClient(timeout=30.0)`
  - 2xx response returns parsed JSON
  - Empty delete response returns `{"status": "deleted"}`
  - Non-2xx raises `LightRAGError`
  - Timeout raises `LightRAGTimeoutError`
  - Do not import routers, services, or ORM models
  - _Requirements: 1.1-1.9, 10.1-10.5_

---

- [x] 4. Viet `backend/integrations/lightrag/query.py`
  - Implement `LightRAGQueryClient`
  - Constructor:
    ```python
    def __init__(self, base_url: str, timeout: float = 30.0) -> None
    ```
  - Implement:
    ```python
    async def query(query_text: str, correlation_id: str, mode: str = "mix") -> dict
    async def query_stream(query_text: str, correlation_id: str, mode: str = "mix") -> AsyncIterator[str]
    ```
  - `query()` calls `POST {base_url}/api/v1/query`
  - `query_stream()` calls `POST {base_url}/api/v1/query/stream`
  - Default mode must be `mix`
  - Include `X-Correlation-ID` in both methods
  - Yield streaming chunks via `response.aiter_text()`
  - Non-2xx raises `LightRAGError`
  - Timeout raises `LightRAGTimeoutError`
  - _Requirements: 2.1-2.8_

---

- [x] 5. Viet `backend/integrations/lightrag/graph.py`
  - Implement `LightRAGGraphClient`
  - Constructor:
    ```python
    def __init__(self, base_url: str, timeout: float = 30.0) -> None
    ```
  - Implement:
    ```python
    async def get_entity(entity_name: str, correlation_id: str) -> dict
    async def get_edges(entity_name: str, correlation_id: str) -> list[dict]
    ```
  - `get_entity()` calls `GET {base_url}/api/v1/graph/entity/{entity_name}`
  - `get_edges()` calls `GET {base_url}/api/v1/graph/edges?entity={entity_name}`
  - Include `X-Correlation-ID`
  - HTTP 404 raises `LightRAGNotFoundError`
  - Other non-2xx raises `LightRAGError`
  - Timeout raises `LightRAGTimeoutError`
  - _Requirements: 3.1-3.8_

---

- [x] 6. Update `backend/dependencies/services.py` for LightRAG clients
  - Import client classes from integrations package
  - Implement/update dependencies:
    ```python
    async def get_lightrag_ingest_client() -> LightRAGIngestClient
    async def get_lightrag_query_client() -> LightRAGQueryClient
    async def get_lightrag_graph_client() -> LightRAGGraphClient
    ```
  - Each dependency uses `settings.LIGHTRAG_URL`
  - Do not instantiate `httpx.AsyncClient` at module import time
  - Keep dependency override pattern testable
  - _Requirements: 11.1-11.5_

---

- [x] 7. Viet `backend/services/ingestion_service.py`
  - Implement helper:
    ```python
    def build_lightrag_metadata(nas_file: NasFile) -> dict
    ```
  - Metadata must include:
    - `source="nas"`
    - `nas_path`
    - `folder`
    - `folder_type`
    - `uploaded_by="system"`
  - Implement:
    ```python
    async def ingest_nas_file(
        db: AsyncSession,
        nas_file_id: str,
        lightrag_client: LightRAGIngestClient,
        correlation_id: str,
    ) -> NasFile
    ```
  - Load `NasFile` by id
  - Missing file -> HTTP 404 or domain error convertible to HTTP 404
  - Reject statuses outside `queued`, `failed`, `indexed` with HTTP 409/domain conflict
  - Set `status="indexing"` before LightRAG call
  - Call `lightrag_client.ingest_document(...)`
  - On success:
    - set `lightrag_doc_id`
    - set `status="indexed"`
    - set `indexed_at=now`
    - clear `error_msg`
  - On LightRAG error:
    - set `status="failed"`
    - set `error_msg`
    - preserve approval metadata
  - Do not import `httpx`
  - _Requirements: 5.1-5.10, 7.1-7.5_

---

- [x] 8. Add `DocumentResponse` schema to `backend/schemas/nas.py`
  - Update `backend/schemas/nas.py` — do NOT create a separate `backend/schemas/documents.py`
  - Fields:
    - `id: str`
    - `nas_path: str`
    - `folder_type: str`
    - `status: str`
    - `file_hash: str | None`
    - `lightrag_doc_id: str | None`
    - `indexed_at: datetime | None`
    - `created_at: datetime`
    - `error_msg: str | None`
    - `chunk_count: int | None = None`
  - Use `ConfigDict(from_attributes=True)`
  - Use Pydantic V2 and `X | None` syntax
  - _Requirements: 8.1-8.5_

---

- [x] 9. Viet `backend/routers/admin/documents.py`
  - Create `APIRouter`
  - Require admin auth for all endpoints with `Depends(require_admin)`
  - Implement:
    ```http
    GET /admin/documents
    POST /admin/documents/{file_id}/reindex
    DELETE /admin/documents/{file_id}
    ```
  - `GET /admin/documents`:
    - returns list of `DocumentResponse`
    - order by `created_at DESC`
    - optional `status` query filter
  - `POST /admin/documents/{file_id}/reindex`:
    - missing file -> HTTP 404
    - set `status="queued"`
    - clear `error_msg`
    - call `ingestion_service.ingest_nas_file`
    - return `DocumentResponse`
  - `DELETE /admin/documents/{file_id}`:
    - missing file -> HTTP 404
    - if `lightrag_doc_id` exists, call `delete_document`
    - LightRAG delete failure -> HTTP 502/504 and preserve local state
    - success -> set `status="rejected"`, `reject_reason="Deleted by admin"`
    - return `{"ok": true}`
  - _Requirements: 9.1-9.10_

---

- [x] 10. Update NAS approval flow to trigger ingestion
  - Update `backend/routers/admin/nas_queue.py`
  - After approve sets `status="queued"`, call `ingestion_service.ingest_nas_file`
  - Get LightRAG ingest client via `Depends(get_lightrag_ingest_client)`
  - Forward current request correlation ID
  - Return final `NasFileResponse` after ingestion attempt
  - Ensure approval metadata remains preserved if ingestion fails
  - Do not trigger ingestion on reject
  - _Requirements: 6.1-6.7_

---

- [x] 11. Add queued-file processing trigger for auto-sync files
  - Provide admin-safe or internal trigger to process an existing queued `NasFile`
  - Accept only files with `status="queued"` or use `ingestion_service` validation
  - Do not ingest `pending_review` files
  - Can be implemented via `POST /admin/documents/{file_id}/reindex` for MVP if documented as the queued processor entry point
  - Ensure auto-sync file can transition `queued` -> `indexing` -> `indexed`
  - _Requirements: 7.1-7.5_

---

- [x] 12. Mount admin documents router in `backend/main.py`
  - Import `backend.routers.admin.documents`
  - Include router:
    ```python
    app.include_router(
        documents.router,
        prefix="/admin/documents",
        tags=["admin-documents"],
    )
    ```
  - Ensure endpoints require admin auth inside router
  - _Requirements: 12.1-12.4_

---

- [x] 13. Write LightRAG client unit tests
  - Create `tests/unit/backend/test_lightrag_integration.py` or package-specific files
  - Use `pytest`, `pytest-asyncio`, `pytest-httpx`
  - Test ingest client:
    - sends `POST /api/v1/docs`
    - payload has `file_path` and `metadata`
    - has `X-Correlation-ID`
  - Test delete client:
    - sends `DELETE /api/v1/docs/{doc_id}`
    - handles empty response as deleted
  - Test query client:
    - sends `POST /api/v1/query`
    - default payload has `mode="mix"`
    - has `X-Correlation-ID`
  - Test query stream:
    - calls `/api/v1/query/stream`
    - yields chunks
  - Test graph client:
    - calls entity endpoint
    - calls edges endpoint
  - Test errors:
    - non-2xx raises `LightRAGError`
    - 404 entity raises `LightRAGNotFoundError`
    - timeout raises `LightRAGTimeoutError`
  - _Requirements: 13.1-13.9_

---

- [x] 14. Write ingestion service unit tests
  - Create `tests/unit/backend/test_ingestion_service.py`
  - Use fake/mock LightRAG ingest client
  - Test success transition:
    - `queued` -> `indexing` -> `indexed`
    - `lightrag_doc_id` stored
    - `indexed_at` set
    - `error_msg` cleared
  - Test missing file -> 404/domain error
  - Test `pending_review` file cannot ingest
  - Test LightRAG failure:
    - status becomes `failed`
    - `error_msg` populated
  - Test metadata builder includes required fields
  - _Requirements: 5.1-5.10, 14.1-14.4_

---

- [x] 15. Write admin documents router unit tests
  - Create `tests/unit/backend/test_admin_documents.py`
  - Use `admin_client` and dependency overrides
  - Test `GET /admin/documents` returns `DocumentResponse` list
  - Test `GET /admin/documents?status=failed` filters correctly
  - Test non-admin receives HTTP 403
  - Test `POST /admin/documents/{file_id}/reindex` calls ingestion service/client
  - Test reindex missing file -> HTTP 404
  - Test `DELETE /admin/documents/{file_id}` calls LightRAG delete when `lightrag_doc_id` exists
  - Test delete preserves local state when LightRAG delete fails
  - _Requirements: 9.1-9.10, 14.5-14.9_

---

- [x] 16. Update NAS queue approval tests
  - Update `tests/unit/backend/test_admin_nas_queue.py`
  - Mock LightRAG ingest client or ingestion service
  - Verify approve action triggers ingestion
  - Verify reject action does not trigger ingestion
  - Verify ingestion failure preserves `approved_by` and `approved_at`
  - Verify final response reflects `indexed` or `failed`
  - _Requirements: 6.1-6.7_

---

- [x] 17. Checkpoint - run LightRAG-related unit tests
  - Run:
    ```bash
    pytest tests/unit/backend/ -k lightrag -v
    ```
  - Verify integration client tests pass without real LightRAG
  - Run:
    ```bash
    pytest tests/unit/backend/ -k "ingestion or documents" -v
    ```
  - Verify service and router tests pass without NAS or Docker
  - _Requirements: 13, 14_

---

- [x] 18. Checkpoint - run backend regression tests
  - Run:
    ```bash
    pytest tests/unit/backend/ -v
    ```
  - Ensure Spec 2 and Spec 3 backend tests still pass
  - Ensure dependency overrides are cleaned after tests
  - _Requirements: 11, 12, 13, 14_

---

- [ ] 19. Manual verification with running stack
  - Start stack:
    ```bash
    docker compose up -d
    ```
  - Ensure LightRAG is reachable at port 9621
  - Create or identify a `NasFile(status="queued")`
  - Trigger reindex:
    ```http
    POST /admin/documents/{file_id}/reindex
    ```
  - Verify LightRAG receives `POST /api/v1/docs`
  - Verify DB status becomes `indexed`
  - Verify `lightrag_doc_id` is stored
  - Verify `GET /admin/documents` shows document
  - Delete document:
    ```http
    DELETE /admin/documents/{file_id}
    ```
  - Verify LightRAG delete is called and local status becomes `rejected`
  - Check Seq logs contain `correlation_id` for backend and LightRAG calls
  - _Requirements: Definition of Done, 1, 5, 9, 10_

---

## Task Dependency Graph

- Tasks 2, 3, 4, 5 (errors, ingest, query, graph clients) có thể làm song song
- Task 6 (update dependencies) phụ thuộc Tasks 3, 4, 5
- Task 7 (ingestion service) phụ thuộc Task 3 và NasFile ORM model từ Spec 2
- Task 8 (DocumentResponse schema) phụ thuộc cấu trúc backend từ Spec 2
- Task 9 (admin documents router) phụ thuộc Tasks 7 và 8
- Task 10 (NAS approval trigger) phụ thuộc Tasks 6, 7 và Spec 3 admin queue router
- Task 11 (queued-file trigger) phụ thuộc Task 7
- Task 12 (mount router) phụ thuộc Task 9
- Tasks 13–16 (unit tests) nên viết song song với implementation tương ứng
- Task 17 phụ thuộc Task 13
- Task 18 phụ thuộc Tasks 13–16
- Task 19 phụ thuộc tất cả tasks trước và stack đang chạy

## Notes

- LightRAG query mode default must remain `mix`.
- Do not let routers import `httpx` or call LightRAG URLs directly.
- `services/` contains business logic only; `integrations/` contains HTTP logic only.
- Always forward `X-Correlation-ID` to LightRAG.
- For MVP, LightRAG response `{status: "processing"}` is treated as accepted and backend may mark `NasFile.status="indexed"` immediately after accepting the job.
- A future worker can poll LightRAG doc status if the API exposes detailed progress.
- Preserve local `NasFile` audit history on delete by marking `rejected` instead of deleting the row.
- LightRAG failures should not erase approval metadata.

---

## Dependency Notes

- Tasks 2-5 can be implemented in parallel.
- Task 6 depends on Tasks 3-5.
- Task 7 depends on Task 3 and existing `NasFile` ORM model.
- Task 9 depends on Tasks 7 and 8.
- Task 10 depends on Tasks 6 and 7 plus Spec 3 admin queue router.
- Task 12 depends on Task 9.
- Tests should be written alongside their modules where possible.
