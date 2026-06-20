# Design Document - Spec 4: LightRAG Integration + Ingestion Pipeline

## Overview

Spec 4 ket noi backend SecondBrain voi LightRAG v1.5 service. Day la lop integration giua `NasFile` queue trong backend PostgreSQL va LightRAG REST API.

Muc tieu:
- Backend goi LightRAG ingest khi NAS file duoc approve hoac duoc queue tu auto-sync folder
- Backend expose admin document APIs de xem, reindex, delete documents
- Backend co LightRAG query/stream/graph clients cho Spec 5 Chat API va Spec 6 Wiki Engine dung lai
- Moi LightRAG call forward `X-Correlation-ID`
- Loi LightRAG duoc wrap thanh exception noi bo va mapped thanh HTTP/status transition ro rang

**Dependency:** Spec 2 va Spec 3 da hoan thanh. Spec 4 khong thay the NAS Connector; NAS Connector van chi report file events vao backend.

---

## Architecture

### Data Flow: Manual Review Approve -> LightRAG

```text
Admin UI
  -> POST /admin/nas/queue/{file_id}/action {approve: true}
  -> backend/routers/admin/nas_queue.py
  -> set NasFile.status="queued", approved_by, approved_at
  -> ingestion_service.ingest_nas_file(...)
  -> set NasFile.status="indexing"
  -> LightRAGIngestClient.ingest_document(...)
  -> POST http://lightrag:9621/api/v1/docs
       {
         "file_path": nas_file.nas_path,
         "metadata": {
           "source": "nas",
           "nas_path": "...",
           "folder": "...",
           "folder_type": "manual",
           "uploaded_by": "system"
         }
       }
  -> LightRAG returns {"id": "doc-uuid", "status": "processing"}
  -> backend stores lightrag_doc_id, status="indexed", indexed_at=now
  -> response NasFileResponse
```

### Data Flow: Auto-Sync Queued File

```text
NAS Connector
  -> POST /api/internal/nas/report {event: "new", ...}
  -> backend creates NasFile(status="queued", folder_type="auto")
  -> queued processor/admin trigger calls ingestion_service.ingest_nas_file
  -> same LightRAG ingest flow
```

### Data Flow: Admin Documents

```text
GET /admin/documents
  -> read NasFile rows
  -> return DocumentResponse[]

POST /admin/documents/{file_id}/reindex
  -> set status="queued", clear error_msg
  -> ingestion_service.ingest_nas_file
  -> return DocumentResponse

DELETE /admin/documents/{file_id}
  -> if lightrag_doc_id exists: DELETE /api/v1/docs/{doc_id}
  -> set local status="rejected", reject_reason="Deleted by admin"
  -> return {"ok": true}
```

---

## Components and Interfaces

### `backend/integrations/lightrag/errors.py`

**Responsibility:** Shared exception types for all LightRAG clients.

```python
class LightRAGError(Exception):
    def __init__(
        self,
        message: str,
        operation: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None: ...

class LightRAGTimeoutError(LightRAGError):
    pass

class LightRAGNotFoundError(LightRAGError):
    pass
```

Design notes:
- Integration layer raises these, not raw `httpx` exceptions.
- Routers/services decide whether to convert to HTTP 502/504 or file `failed` state.

### `backend/integrations/lightrag/ingest.py`

**Responsibility:** LightRAG document lifecycle HTTP calls: ingest and delete.

```python
class LightRAGIngestClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None: ...

    async def ingest_document(
        self,
        file_path: str,
        metadata: dict,
        correlation_id: str,
    ) -> dict: ...

    async def delete_document(
        self,
        doc_id: str,
        correlation_id: str,
    ) -> dict: ...
```

HTTP contracts:

```http
POST /api/v1/docs
Content-Type: application/json
X-Correlation-ID: {cid}

{
  "file_path": "/mnt/nas/projects/alpha/SOP.pdf",
  "metadata": {
    "source": "nas",
    "folder": "/projects/alpha",
    "folder_type": "auto",
    "uploaded_by": "system",
    "nas_path": "/mnt/nas/projects/alpha/SOP.pdf"
  }
}
```

```http
DELETE /api/v1/docs/{doc_id}
X-Correlation-ID: {cid}
```

### `backend/integrations/lightrag/query.py`

**Responsibility:** Query LightRAG with `mode="mix"` and provide streaming adapter for Spec 5.

```python
class LightRAGQueryClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None: ...

    async def query(
        self,
        query_text: str,
        correlation_id: str,
        mode: str = "mix",
    ) -> dict: ...

    async def query_stream(
        self,
        query_text: str,
        correlation_id: str,
        mode: str = "mix",
    ) -> AsyncIterator[str]: ...
```

Rules:
- Default mode is always `mix`.
- Do not hardcode `naive`, `local`, `global`, or `hybrid` in production paths unless explicitly required by a future spec.
- Forward `X-Correlation-ID` for both normal and streaming query.

### `backend/integrations/lightrag/graph.py`

**Responsibility:** Graph/entity calls for Spec 6 Wiki Engine.

```python
class LightRAGGraphClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None: ...

    async def get_entity(self, entity_name: str, correlation_id: str) -> dict: ...

    async def get_edges(self, entity_name: str, correlation_id: str) -> list[dict]: ...
```

HTTP contracts:

```http
GET /api/v1/graph/entity/{entity_name}
GET /api/v1/graph/edges?entity={entity_name}
```

### `backend/dependencies/services.py`

**Responsibility:** Provide LightRAG clients through DI.

```python
async def get_lightrag_ingest_client() -> LightRAGIngestClient:
    return LightRAGIngestClient(base_url=settings.LIGHTRAG_URL)

async def get_lightrag_query_client() -> LightRAGQueryClient:
    return LightRAGQueryClient(base_url=settings.LIGHTRAG_URL)

async def get_lightrag_graph_client() -> LightRAGGraphClient:
    return LightRAGGraphClient(base_url=settings.LIGHTRAG_URL)
```

Design notes:
- Do not instantiate `httpx.AsyncClient` at module import time.
- Tests override these dependency functions using `app.dependency_overrides`.

### `backend/services/ingestion_service.py`

**Responsibility:** Business logic for ingesting `NasFile` rows into LightRAG.

```python
async def ingest_nas_file(
    db: AsyncSession,
    nas_file_id: str,
    lightrag_client: LightRAGIngestClient,
    correlation_id: str,
) -> NasFile: ...
```

Algorithm:

```text
1. Load NasFile by id
2. If missing -> 404/domain error
3. If status not in queued/failed/indexed -> reject with conflict
4. Set status=indexing, commit/flush
5. Build LightRAG metadata
6. Call ingest_document(nas_path, metadata, correlation_id)
7. On success:
   - lightrag_doc_id = response["id"]
   - status = indexed
   - indexed_at = now
   - error_msg = None
8. On LightRAG error:
   - status = failed
   - error_msg = safe error summary
   - commit
   - raise or return depending caller
```

Metadata builder:

```python
def build_lightrag_metadata(nas_file: NasFile) -> dict:
    return {
        "source": "nas",
        "nas_path": nas_file.nas_path,
        "folder": str(Path(nas_file.nas_path).parent),
        "folder_type": nas_file.folder_type,
        "uploaded_by": "system",
    }
```

Design decision:
- MVP treats LightRAG `{status: "processing"}` as accepted and sets backend `indexed` after LightRAG accepts the job. A future spec can poll LightRAG doc status if the API exposes detailed progress.

### `backend/schemas/nas.py` (update)

**Responsibility:** Add `DocumentResponse` to the existing NAS schemas file — consistent with spec-plan which specifies `backend/schemas/nas.py` as the update target. Do NOT create a separate `documents.py`.

```python
class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nas_path: str
    folder_type: str
    status: str
    file_hash: str | None = None
    lightrag_doc_id: str | None = None
    indexed_at: datetime | None = None
    created_at: datetime
    error_msg: str | None = None
    chunk_count: int | None = None
```

Design note:
- `chunk_count` is nullable because LightRAG v1.5 API reference in this project does not define a direct chunk-count endpoint.

### `backend/routers/admin/documents.py`

**Responsibility:** Admin document management endpoints.

```python
router = APIRouter(dependencies=[Depends(require_admin)])

@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    status: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]: ...

@router.post("/{file_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    file_id: str,
    db: AsyncSession = Depends(get_session),
    lightrag: LightRAGIngestClient = Depends(get_lightrag_ingest_client),
) -> DocumentResponse: ...

@router.delete("/{file_id}")
async def delete_document(
    file_id: str,
    db: AsyncSession = Depends(get_session),
    lightrag: LightRAGIngestClient = Depends(get_lightrag_ingest_client),
) -> dict: ...
```

Delete design:
- If `lightrag_doc_id` exists, call LightRAG delete first.
- If LightRAG delete succeeds, set local `status="rejected"`, `reject_reason="Deleted by admin"`.
- If LightRAG delete fails, preserve local state and return HTTP 502/504.
- Keeping the local row preserves audit trail and avoids losing NAS history.

### Update `backend/routers/admin/nas_queue.py`

**Responsibility:** Trigger ingestion after approval.

After Spec 4, approve flow should:

```text
pending_review -> queued -> ingestion_service -> indexed or failed
```

The endpoint returns final `NasFileResponse` after the synchronous MVP ingestion attempt. This keeps implementation simple for 20-user internal MVP. A future worker/queue can make this async.

### Update `backend/main.py`

Mount admin documents router:

```python
app.include_router(
    documents.router,
    prefix="/admin/documents",
    tags=["admin-documents"],
)
```

---

## Error Handling

### LightRAG Error Mapping

| Source error | Integration exception | Router/service behavior |
|---|---|---|
| HTTP 404 on graph entity | `LightRAGNotFoundError` | Wiki later returns 404 |
| HTTP non-2xx ingest/query/delete | `LightRAGError` | Admin endpoints return 502; ingestion marks file failed |
| Timeout | `LightRAGTimeoutError` | Admin endpoints return 504 or file failed with timeout message |
| Invalid JSON response | `LightRAGError` | 502; log response text safely |

### Ingestion Failure Behavior

```text
queued -> indexing -> failed
```

On failure:
- `NasFile.error_msg` stores a short safe message
- `lightrag_doc_id` is not overwritten unless a valid id was returned
- Approval metadata remains preserved
- Correlation ID is included in logs

---

## Security

- All admin documents endpoints require `Depends(require_admin)`.
- Internal LightRAG URL is read from `settings.LIGHTRAG_URL`, default Docker network URL.
- Do not expose LightRAG API credentials or NAS credentials in error messages.
- Do not log file contents; log only paths, status, doc id, and correlation ID.

---

## Testing Strategy

### Unit Tests

| File | Target | Mock strategy |
|---|---|---|
| `tests/unit/backend/test_lightrag_integration.py` | LightRAG ingest/query/stream/graph/delete clients | `pytest-httpx` |
| `tests/unit/backend/test_ingestion_service.py` | `ingest_nas_file` transitions | fake DB/session or repository fixture + mock client |
| `tests/unit/backend/test_admin_documents.py` | document admin endpoints | `admin_client`, dependency override for LightRAG client |
| `tests/unit/backend/test_admin_nas_queue.py` update | approval triggers ingestion | mock ingestion service/client |

### Key Cases

```text
Client tests:
- ingest sends POST /api/v1/docs with file_path, metadata, X-Correlation-ID
- query sends mode=mix by default
- query_stream yields chunks
- graph entity/edges endpoints are called
- delete sends DELETE /api/v1/docs/{doc_id}
- non-2xx raises LightRAGError
- timeout raises LightRAGTimeoutError

Service tests:
- queued -> indexing -> indexed on success
- lightrag_doc_id and indexed_at stored
- pending_review cannot ingest
- LightRAGError -> failed + error_msg

Router tests:
- GET /admin/documents returns DocumentResponse[]
- status filter works
- reindex calls ingestion service
- delete calls LightRAG delete and marks local rejected
- non-admin receives 403
```

### Commands

```bash
pytest tests/unit/backend/ -k lightrag -v
pytest tests/unit/backend/ -k "ingestion or documents" -v
pytest tests/unit/backend/ -v
```

---

## Requirements Traceability

| Requirement | File(s) |
|---|---|
| R1 - Ingest client | `backend/integrations/lightrag/ingest.py` |
| R2 - Query client | `backend/integrations/lightrag/query.py` |
| R3 - Graph client | `backend/integrations/lightrag/graph.py` |
| R4 - Error types | `backend/integrations/lightrag/errors.py` |
| R5 - Ingestion service | `backend/services/ingestion_service.py` |
| R6 - Approval trigger | `backend/routers/admin/nas_queue.py` |
| R7 - Auto queued processing | `backend/services/ingestion_service.py`, admin/internal trigger |
| R8 - Document schemas | `backend/schemas/nas.py` (update) |
| R9 - Admin documents router | `backend/routers/admin/documents.py` |
| R10 - Delete client | `backend/integrations/lightrag/ingest.py` |
| R11 - DI updates | `backend/dependencies/services.py` |
| R12 - Router mount | `backend/main.py` |
| R13 - Client tests | `tests/unit/backend/test_lightrag_integration.py` |
| R14 - Service/router tests | `tests/unit/backend/test_ingestion_service.py`, `tests/unit/backend/test_admin_documents.py` |
