# Requirements Document

## Introduction

Spec nay xay dung **LightRAG Integration + Ingestion Pipeline** cho SecondBrain. Backend se goi LightRAG v1.5 qua REST API de ingest tai lieu tu NAS, query knowledge voi `mode="mix"`, doc graph entity/edges, va quan ly danh sach documents da index.

Spec nay nam giua NAS Connector va cac tinh nang Chat/Wiki. NAS Connector chi report file events vao backend; backend moi la noi trigger LightRAG ingestion. LightRAG service chay rieng o port 9621 va luu graph/vector/doc status trong PostgreSQL theo cau hinh Spec 1.

**Dependency:** Spec 2 (Backend Foundation) va Spec 3 (NAS Connector) phai hoan thanh:
- Backend FastAPI, settings, logger, correlation middleware, `get_session`, `require_admin` da co
- `NasFile` va `NasFolder` ORM models da co
- `backend/schemas/nas.py` va admin NAS queue endpoints da co
- NAS Connector report file moi/thay doi/xoa vao backend DB, khong goi LightRAG truc tiep

**Definition of Done:**
- Approve file PDF trong manual-review folder -> backend trigger LightRAG `POST /api/v1/docs`
- Auto-sync file queued -> ingestion worker/client goi LightRAG ingest voi metadata dung
- `NasFile.status` chuyen `queued` -> `indexing` -> `indexed` khi LightRAG accept document
- LightRAG timeout/error duoc wrap thanh HTTP 502/504 hoac status `failed` voi `error_msg`
- `GET /admin/documents` tra danh sach documents voi status dung
- `POST /admin/documents/{id}/reindex` queue lai document va trigger ingest
- `DELETE /admin/documents/{id}` goi LightRAG delete neu co `lightrag_doc_id`
- `pytest tests/unit/backend/ -k lightrag -v` passes

---

## Glossary

- **LightRAG**: Graph + vector engine chay tai `LIGHTRAG_URL`, mac dinh `http://lightrag:9621`
- **Ingest**: Gui file path va metadata den LightRAG `POST /api/v1/docs` de LightRAG parse/chunk/embed/extract graph
- **Query mode mix**: LightRAG query mode bat buoc cho production, ket hop local/global/naive retrieval
- **Graph API**: LightRAG endpoints `GET /api/v1/graph/entity/{name}` va `GET /api/v1/graph/edges?entity=...`
- **Document admin API**: Backend endpoints `/admin/documents` de list/reindex/delete indexed NAS documents
- **LightRAG doc id**: ID LightRAG tra ve trong response ingest, luu vao `NasFile.lightrag_doc_id`
- **Ingestion trigger**: Backend logic chuyen `NasFile.status` sang `indexing`, goi LightRAG, roi cap nhat status
- **Correlation ID**: `X-Correlation-ID` header phai forward den LightRAG de trace logs
- **Resume-on-crash**: LightRAG co kha nang tiep tuc background processing; backend chi track trang thai o muc accepted/failed trong MVP

---

## Requirements

### Requirement 1 - LightRAG Ingest Client

**User Story:** As a backend developer, I want a LightRAG ingest client, so that backend services can submit NAS files to LightRAG without routers importing HTTP logic directly.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.1 (Workflow - Ingestion tai lieu tu NAS), Section 8 (API contracts), lightrag-api.md (Ingest Document)

#### Acceptance Criteria

1. THE `LightRAGIngestClient` SHALL be implemented in `backend/integrations/lightrag/ingest.py` using `httpx.AsyncClient`.
2. THE `LightRAGIngestClient` SHALL expose `async def ingest_document(file_path: str, metadata: dict, correlation_id: str) -> dict`.
3. THE `LightRAGIngestClient` SHALL call `POST {LIGHTRAG_URL}/api/v1/docs` with JSON body `{"file_path": file_path, "metadata": metadata}`.
4. THE request SHALL include headers `X-Correlation-ID` and `Content-Type: application/json`.
5. THE client SHALL use timeout `30.0` seconds by default.
6. WHEN LightRAG returns HTTP 2xx, THE client SHALL return the parsed JSON response.
7. WHEN LightRAG returns non-2xx, THE client SHALL raise `LightRAGError` containing status code and response text.
8. WHEN LightRAG times out, THE client SHALL raise `LightRAGTimeoutError`.
9. THE client SHALL NOT import FastAPI routers, SQLAlchemy models, or business services.

---

### Requirement 2 - LightRAG Query Client

**User Story:** As a backend developer, I want a LightRAG query client that always uses `mode="mix"`, so that Chat and future APIs get the best hybrid retrieval behavior by default.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** lightrag-api.md (Query Knowledge, Query Modes), pa3-design Section 5.2 (Chat workflow)

#### Acceptance Criteria

1. THE `LightRAGQueryClient` SHALL be implemented in `backend/integrations/lightrag/query.py` using `httpx.AsyncClient`.
2. THE client SHALL expose `async def query(query_text: str, correlation_id: str, mode: str = "mix") -> dict`.
3. THE client SHALL call `POST {LIGHTRAG_URL}/api/v1/query` with JSON body `{"query": query_text, "mode": "mix"}` by default.
4. THE client SHALL NOT use `naive`, `local`, `global`, or `hybrid` in production defaults.
5. THE client SHALL include `X-Correlation-ID` in every request.
6. THE client SHALL expose `async def query_stream(query_text: str, correlation_id: str, mode: str = "mix") -> AsyncIterator[str]` for future Chat API streaming.
7. THE streaming method SHALL call `POST {LIGHTRAG_URL}/api/v1/query/stream` and yield text chunks from `response.aiter_text()`.
8. WHEN LightRAG returns non-2xx or timeout, THE client SHALL raise `LightRAGError` or `LightRAGTimeoutError` consistently with the ingest client.

---

### Requirement 3 - LightRAG Graph Client

**User Story:** As a backend developer, I want a LightRAG graph client, so that Wiki and graph-related APIs can retrieve entity pages and relation edges without duplicating HTTP code.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** lightrag-api.md (Get Entity), pa3-design Section 11 (Wiki engine design)

#### Acceptance Criteria

1. THE `LightRAGGraphClient` SHALL be implemented in `backend/integrations/lightrag/graph.py` using `httpx.AsyncClient`.
2. THE client SHALL expose `async def get_entity(entity_name: str, correlation_id: str) -> dict`.
3. THE client SHALL call `GET {LIGHTRAG_URL}/api/v1/graph/entity/{entity_name}`.
4. THE client SHALL expose `async def get_edges(entity_name: str, correlation_id: str) -> list[dict]`.
5. THE client SHALL call `GET {LIGHTRAG_URL}/api/v1/graph/edges?entity={entity_name}`.
6. THE client SHALL include `X-Correlation-ID` in every request.
7. WHEN LightRAG returns HTTP 404 for an entity, THE client SHALL raise `LightRAGNotFoundError`.
8. WHEN LightRAG returns other non-2xx or timeout, THE client SHALL raise `LightRAGError` or `LightRAGTimeoutError`.

---

### Requirement 4 - LightRAG Error Types

**User Story:** As a backend developer, I want shared LightRAG integration error types, so that routers and services can convert external failures to consistent backend behavior.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 12 (Risks and mitigation), lightrag-api.md (integration code pattern)

#### Acceptance Criteria

1. THE LightRAG integration package SHALL define shared exceptions in `backend/integrations/lightrag/errors.py`.
2. THE package SHALL define `LightRAGError`, `LightRAGTimeoutError`, and `LightRAGNotFoundError`.
3. THE exceptions SHALL carry enough context for logging: operation name, status code when available, and response text when available.
4. THE clients SHALL use these exceptions instead of raising raw `httpx` exceptions to callers.
5. WHEN logging LightRAG failures, THE integration layer SHALL include `correlation_id` and operation name.

---

### Requirement 5 - Ingestion Service

**User Story:** As a backend developer, I want a business service that triggers ingestion for a `NasFile`, so that routers can queue/reindex documents without embedding LightRAG business rules.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `nas-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 5.1 (Ingestion workflow), Section 7 (Data model), Section 8 (Admin documents API)

#### Acceptance Criteria

1. THE `IngestionService` SHALL be implemented in `backend/services/ingestion_service.py`.
2. THE service SHALL expose `async def ingest_nas_file(db: AsyncSession, nas_file_id: str, lightrag_client: LightRAGIngestClient, correlation_id: str) -> NasFile`.
3. WHEN the `NasFile` does not exist, THE service SHALL raise HTTP 404 or a domain error convertible to HTTP 404.
4. WHEN `NasFile.status` is not `queued`, `failed`, or `indexed`, THE service SHALL reject ingestion with HTTP 409 or a domain error convertible to HTTP 409.
5. THE service SHALL set `NasFile.status="indexing"` before calling LightRAG.
6. THE service SHALL build LightRAG metadata containing at least `source="nas"`, `nas_path`, `folder`, `folder_type`, and `uploaded_by="system"`.
7. THE service SHALL call `lightrag_client.ingest_document(file_path=nas_file.nas_path, metadata=metadata, correlation_id=correlation_id)`.
8. WHEN LightRAG returns `{ "id": "...", "status": "processing" }`, THE service SHALL store `lightrag_doc_id`, set `status="indexed"`, set `indexed_at=now`, clear `error_msg`, and return the updated `NasFile`.
9. WHEN LightRAG raises an error, THE service SHALL set `status="failed"`, set `error_msg`, and re-raise or return an error according to caller context.
10. THE service SHALL not import `httpx`; LightRAG HTTP logic stays in `integrations/`.

---

### Requirement 6 - NAS Approval Triggers Ingestion

**User Story:** As an admin, I want approved manual-review files to start ingestion automatically, so that approved documents enter the knowledge base without another manual step.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `nas-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.1 (manual-review APPROVE flow), docs/brainstorm/spec-plan.md (Spec 4 cover)

#### Acceptance Criteria

1. WHEN `POST /admin/nas/queue/{file_id}/action` approves a file, THE backend SHALL set `NasFile.status="queued"` as defined in Spec 3.
2. AFTER approval succeeds, THE backend SHALL trigger `IngestionService.ingest_nas_file` for the approved file.
3. THE ingestion trigger SHALL use dependency-injected LightRAG ingest client from `backend/dependencies/services.py`.
4. THE trigger SHALL forward the current request correlation ID to LightRAG.
5. WHEN LightRAG ingestion succeeds, THE approved file SHALL end with `status="indexed"` and non-empty `lightrag_doc_id`.
6. WHEN LightRAG ingestion fails, THE approval response SHALL not lose approval metadata; `NasFile.status` SHALL become `failed` and `error_msg` SHALL be populated.
7. THE endpoint SHALL return `NasFileResponse` reflecting the final status after ingestion attempt for MVP synchronous behavior.

---

### Requirement 7 - Auto-Queued Files Can Be Processed

**User Story:** As a system operator, I want auto-sync files with `status="queued"` to be ingested, so that auto folders flow into LightRAG without admin approval.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `nas-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.1 (auto-sync folder), nas-rules.md (Folder Types)

#### Acceptance Criteria

1. THE backend SHALL expose an internal or admin-safe trigger to process a queued `NasFile` created by auto-sync folders.
2. THE trigger SHALL call `IngestionService.ingest_nas_file` for files with `status="queued"`.
3. WHEN a queued auto-sync file is processed successfully, THE `NasFile` SHALL transition `queued` -> `indexing` -> `indexed`.
4. WHEN LightRAG fails, THE `NasFile` SHALL transition to `failed` with `error_msg` populated.
5. THE trigger SHALL not ingest `pending_review` files before admin approval.

---

### Requirement 8 - Document Admin Schemas

**User Story:** As a frontend developer, I want document response schemas, so that the admin UI can display indexed, queued, failed, and pending documents consistently.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8 (API contracts - Admin documents), docs/brainstorm/spec-plan.md (DocumentResponse)

#### Acceptance Criteria

1. THE backend SHALL define `DocumentResponse` in `backend/schemas/nas.py` as an update to the existing NAS schemas file — NOT in a separate `documents.py`.
2. THE schema SHALL include fields: `id`, `nas_path`, `folder_type`, `status`, `file_hash`, `lightrag_doc_id`, `indexed_at`, `created_at`, `error_msg`, and `chunk_count`.
3. THE `chunk_count` field SHALL be `int | None` and MAY be `None` in MVP if LightRAG does not expose chunk count directly.
4. THE schema SHALL use `ConfigDict(from_attributes=True)`.
5. THE schema SHALL use Pydantic V2 syntax and `X | None` union syntax.

---

### Requirement 9 - Admin Documents Router

**User Story:** As an admin, I want document management endpoints, so that I can inspect indexed documents, reindex failed or changed files, and delete documents from the knowledge base.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `nas-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 8 (GET/POST/DELETE admin documents), lightrag-api.md (Delete Document)

#### Acceptance Criteria

1. THE `AdminDocumentsRouter` SHALL be implemented in `backend/routers/admin/documents.py` with all endpoints requiring `Depends(require_admin)`.
2. THE router SHALL implement `GET /admin/documents` returning list of `DocumentResponse`, ordered by `created_at DESC` by default.
3. THE `GET /admin/documents` endpoint SHALL support optional `status` query parameter to filter by `NasFile.status`.
4. THE router SHALL implement `POST /admin/documents/{file_id}/reindex`.
5. WHEN reindex is called for a missing file, THE endpoint SHALL return HTTP 404.
6. WHEN reindex is called for an existing file, THE endpoint SHALL set `status="queued"`, clear `error_msg`, and call `IngestionService.ingest_nas_file`.
7. THE router SHALL implement `DELETE /admin/documents/{file_id}`.
8. WHEN delete is called and `NasFile.lightrag_doc_id` exists, THE backend SHALL call LightRAG `DELETE /api/v1/docs/{doc_id}` before marking the local record deleted/rejected.
9. WHEN delete succeeds, THE endpoint SHALL set `NasFile.status="rejected"` and `reject_reason="Deleted by admin"` or remove the record according to implementation choice documented in design.
10. WHEN LightRAG delete fails, THE endpoint SHALL return HTTP 502 and preserve the local `NasFile` state.

---

### Requirement 10 - LightRAG Delete Client

**User Story:** As a backend developer, I want the LightRAG integration to delete documents, so that admin delete actions can remove documents from LightRAG storage when needed.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** lightrag-api.md (Delete Document), pa3-design Section 8 (Admin documents API)

#### Acceptance Criteria

1. THE LightRAG ingest or documents client SHALL expose `async def delete_document(doc_id: str, correlation_id: str) -> dict`.
2. THE client SHALL call `DELETE {LIGHTRAG_URL}/api/v1/docs/{doc_id}`.
3. THE request SHALL include `X-Correlation-ID`.
4. WHEN LightRAG returns 2xx, THE client SHALL return parsed JSON response or `{ "status": "deleted" }` if response body is empty.
5. WHEN LightRAG returns non-2xx or timeout, THE client SHALL raise shared LightRAG exceptions.

---

### Requirement 11 - Dependency Injection Updates

**User Story:** As a backend developer, I want LightRAG clients provided through FastAPI dependencies, so that routers can be tested with mocks and do not import integration modules directly.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** backend-rules.md (Service Injection Dependencies), pa3-design Section 4 (`backend/dependencies/services.py`)

#### Acceptance Criteria

1. THE `backend/dependencies/services.py` module SHALL provide dependencies for LightRAG ingest, query, and graph clients.
2. THE dependencies SHALL instantiate clients using `settings.LIGHTRAG_URL`.
3. THE dependencies SHALL NOT instantiate `httpx.AsyncClient` at module import time.
4. WHEN tests override dependencies via `app.dependency_overrides`, routers SHALL use mock clients without conditional logic.
5. THE admin documents router and NAS approval trigger SHALL receive LightRAG clients via `Depends`, not direct imports.

---

### Requirement 12 - Router Mounting

**User Story:** As an admin, I want the document management endpoints mounted in the backend app, so that they are accessible through the documented API paths.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8 (API contracts), docs/brainstorm/spec-plan.md (Spec 4 cover)

#### Acceptance Criteria

1. THE backend app SHALL include `AdminDocumentsRouter` in `backend/main.py`.
2. THE router SHALL be mounted with prefix `/admin/documents`.
3. THE router SHALL be tagged as `admin-documents` or equivalent.
4. THE mounted endpoints SHALL require admin auth through router dependencies.

---

### Requirement 13 - Unit Tests: LightRAG Integration Clients

**User Story:** As a developer, I want unit tests for LightRAG HTTP clients, so that endpoint paths, payloads, headers, and error handling are verified without running LightRAG.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Unit tests - backend/integrations/lightrag), lightrag-api.md

#### Acceptance Criteria

1. THE integration tests SHALL be implemented in `tests/unit/backend/test_lightrag_integration.py` or split under `tests/unit/backend/integrations/`.
2. THE tests SHALL use `pytest-httpx` or equivalent HTTP mocking.
3. THE ingest client test SHALL verify `POST /api/v1/docs` payload includes `file_path` and `metadata`.
4. THE query client test SHALL verify `POST /api/v1/query` payload uses `mode="mix"` by default.
5. THE stream query test SHALL verify `POST /api/v1/query/stream` is called and chunks are yielded.
6. THE graph client tests SHALL verify entity and edges endpoints.
7. THE delete client test SHALL verify `DELETE /api/v1/docs/{doc_id}` is called.
8. ALL client tests SHALL verify `X-Correlation-ID` header is present.
9. Error tests SHALL verify non-2xx responses raise `LightRAGError` and timeouts raise `LightRAGTimeoutError`.

---

### Requirement 14 - Unit Tests: Ingestion Service and Admin Documents

**User Story:** As a developer, I want unit tests for ingestion service and document endpoints, so that NAS file status transitions are correct and admin actions are safe.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `nas-rules.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Testing strategy), pa3-design Section 5.1 (Ingestion workflow)

#### Acceptance Criteria

1. THE service tests SHALL verify successful ingestion transitions `queued` -> `indexing` -> `indexed`.
2. THE service tests SHALL verify `lightrag_doc_id` and `indexed_at` are stored after success.
3. THE service tests SHALL verify LightRAG failure transitions file to `failed` and stores `error_msg`.
4. THE service tests SHALL verify `pending_review` files are not ingested before approval.
5. THE admin documents tests SHALL verify `GET /admin/documents` returns `DocumentResponse` list.
6. THE admin documents tests SHALL verify status filtering.
7. THE admin documents tests SHALL verify reindex calls ingestion service.
8. THE admin documents tests SHALL verify delete calls LightRAG delete when `lightrag_doc_id` exists.
9. ALL tests SHALL run without real LightRAG, real NAS, or Docker.
