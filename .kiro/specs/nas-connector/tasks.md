# Implementation Plan: NAS Connector

## Overview

Xay dung **Spec 3: NAS Connector** cho SecondBrain.

Spec nay bao gom 2 phan chinh:

1. **NAS Connector service** - Python background service doc Synology NAS qua SMB mount, poll file dinh ky, tinh hash, detect file moi/thay doi/xoa, roi report ve backend.
2. **Backend NAS APIs** - internal endpoints cho connector report file events va admin endpoints de quan ly queue/folder approval.

NAS Connector **khong goi LightRAG truc tiep**, khong luu SQLite local, khong tu quyet dinh business logic. Backend PostgreSQL (`NasFile`, `NasFolder`) la single source of truth.

**Dependency:** Spec 2 Backend Foundation da hoan thanh:
- FastAPI app chay duoc
- `NasFile`, `NasFolder` ORM models da ton tai
- `get_session`, `require_admin`, logger, middleware da hoat dong
- Auth dependencies da co

---

## Tasks

- [x] 1. Khoi tao cau truc thu muc NAS Connector va backend routers
  - Tao service folder `nas-connector/`
  - Tao Python package importable `nas_connector/` de tuong thich voi import style `from nas_connector.config import config`
  - Tao cac file:
    ```text
    nas-connector/
    ├── requirements.txt
    └── nas_connector/
        ├── __init__.py
        ├── main.py
        ├── config.py
        ├── watcher.py
        ├── uploader.py
        ├── notifier.py
        └── logger.py
    ```
  - Tao backend router folders neu chua co:
    ```text
    backend/routers/internal/
    backend/routers/admin/
    ```
  - Tao `__init__.py` cho cac router folders
  - Tao test folders:
    ```text
    tests/unit/nas_connector/
    ```
  - Tao `__init__.py` cho test package neu project convention yeu cau
  - Tao `nas-connector/requirements.txt` voi dependencies duoc pin version:
    ```text
    pydantic==2.10.3
    pydantic-settings==2.7.0
    httpx==0.28.1
    structlog==24.4.0
    pytest==8.3.4
    pytest-asyncio==0.24.0
    pytest-httpx==0.35.0
    ```
  - _Requirements: 1, 2, 4, 10, 11, 12, 13_

---

- [x] 2. Viet `nas_connector/config.py` - NAS Connector Settings
  - Dinh nghia `NASConfig(BaseSettings)` dung `pydantic-settings`
  - Required settings:
    - `NAS_HOST: str`
    - `NAS_USER: str`
    - `NAS_PASS: str`
    - `NAS_SHARE: str`
  - Optional/default settings:
    - `NAS_MOUNT_PATH: str = "/mnt/nas"`
    - `BACKEND_API_URL: str = "http://backend:8000"`
    - `POLL_INTERVAL_SECONDS: int = 300`
    - `SEQ_URL: str = "http://seq:5341"`
  - Cau hinh doc `.env` va environment variables
  - Export singleton:
    ```python
    config = NASConfig()
    ```
  - Ensure missing required settings raise `ValidationError` at startup
  - _Requirements: 1.1-1.6_

---

- [x] 3. Viet `nas_connector/logger.py` - Structured logging cho NAS Connector
  - Configure `structlog` cho JSON structured logs
  - Include field mac dinh:
    - `service="nas-connector"`
    - `correlation_id` khi available
  - Tao context var hoac helper de bind `correlation_id`
  - Ship logs den `SEQ_URL` neu co the
  - Fallback to stdout neu Seq unreachable
  - Export module-level logger:
    ```python
    logger = structlog.get_logger()
    ```
  - Khong raise exception neu logging backend loi
  - _Requirements: 10.1-10.6_

---

- [x] 4. Viet `nas_connector/uploader.py` - HTTP client report events ve backend
  - Implement class `Uploader`
  - Constructor nhan `backend_url: str`
  - Implement:
    ```python
    async def get_hash(self, nas_path: str) -> str | None
    async def report_new(self, nas_path: str, file_hash: str, extension: str, ingest_content: bool) -> None
    async def report_changed(self, nas_path: str, new_hash: str) -> None
    async def report_deleted(self, nas_path: str) -> None
    ```
  - `get_hash()` goi:
    ```http
    GET /api/internal/nas/hash?path=...
    ```
  - Khi backend tra 404, `get_hash()` return `None`
  - `report_new()` gui payload:
    ```json
    {
      "event": "new",
      "nas_path": "...",
      "file_hash": "...",
      "extension": "...",
      "ingest_content": true
    }
    ```
  - `report_changed()` gui payload:
    ```json
    {
      "event": "changed",
      "nas_path": "...",
      "file_hash": "..."
    }
    ```
  - `report_deleted()` gui payload:
    ```json
    {
      "event": "deleted",
      "nas_path": "..."
    }
    ```
  - Moi request phai co `X-Correlation-ID` UUID v4 header
  - Dung `httpx.AsyncClient`
  - Non-2xx response: log error, khong raise
  - Connection error / timeout: log warning, khong raise
  - _Requirements: 4.1-4.7_

---

- [x] 5. Viet `nas_connector/watcher.py` - file scan, hash, classification
  - Dinh nghia constants:
    ```python
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"
    }

    METADATA_ONLY_EXTENSIONS = {
        ".dwg", ".dxf", ".png", ".jpg", ".jpeg",
        ".mp4", ".avi", ".step", ".stl"
    }
    ```
  - Implement:
    ```python
    def compute_md5(file_path: Path) -> str
    async def poll_once(mount_path: str, uploader: Uploader) -> None
    ```
  - `compute_md5()` doc file dang binary theo chunk, vi du 8192 bytes
  - `poll_once()` recursively scan toan bo files duoi `mount_path`
  - Ignore unsupported extension silently
  - Voi supported extension:
    - `ingest_content=True`
    - goi `uploader.get_hash(nas_path)`
    - neu hash chua co thi `report_new(...)`
    - neu hash khac thi `report_changed(...)`
  - Voi metadata-only extension:
    - `ingest_content=False`
    - van report de backend index metadata
  - Khi xu ly mot file bi loi, log error voi:
    - `nas_path`
    - `correlation_id`
    - `error`
    - tiep tuc file tiep theo
  - Log INFO khi bat dau va ket thuc poll cycle
  - Count so file processed trong log cuoi
  - _Requirements: 2.1-2.10_

---

- [x] 6. Thiet ke deleted file detection trong watcher
  - Implement strategy de phat hien file deleted ma khong luu SQLite local
  - NAS Connector khong tu persist state local
  - Neu can danh sach known files, goi backend internal endpoint trong cung spec hoac defer explicit deleted detection den backend-based lookup
  - Preferred implementation:
    - Backend cung cap danh sach known active `nas_path` theo mount scope
    - Watcher so sanh voi scanned paths hien tai
    - Missing path -> `uploader.report_deleted(nas_path)`
  - Neu chua implement backend list endpoint trong MVP, document ro limitation: deleted detection chi duoc test qua injected previous snapshot trong unit test, khong persist local state
  - Khong tao SQLite hoac file state local
  - _Requirements: 2.5, 11.6, 12.6_

---

- [x] 7. Viet `nas_connector/main.py` - async entry point
  - Validate config khi startup
  - Check `NAS_MOUNT_PATH` ton tai
  - Check `NAS_MOUNT_PATH` readable
  - Neu config invalid hoac mount khong readable:
    - log error
    - exit code 1
  - Khoi tao `Uploader(config.BACKEND_API_URL)`
  - Chay infinite loop:
    ```python
    while not shutting_down:
        await poll_once(config.NAS_MOUNT_PATH, uploader)
        await asyncio.sleep(config.POLL_INTERVAL_SECONDS)
    ```
  - Handle `SIGTERM` va `SIGINT`
  - Khi nhan shutdown signal:
    - hoan thanh poll cycle hien tai
    - log shutdown message
    - exit gracefully
  - Khong tao SQLite, khong luu local DB
  - _Requirements: 11.1-11.6_

---

- [x] 8. Viet `nas_connector/notifier.py` stub
  - Tao file `nas_connector/notifier.py`
  - De stub cho future push/in-app notification neu can
  - Khong dung trong flow chinh hien tai
  - Khong goi backend truc tiep neu chua co requirement cu the
  - _Requirements: 6.1-6.5_

---

- [x] 9. Viet `backend/schemas/nas.py` - NAS Pydantic schemas
  - Dinh nghia Pydantic V2 schemas:
    ```python
    NasFileResponse
    NasReportRequest
    ApproveRequest
    FolderRequest
    NasFolderResponse
    ```
  - `NasFileResponse` fields:
    - `id: str`
    - `nas_path: str`
    - `folder_type: str`
    - `status: str`
    - `file_hash: str | None`
    - `lightrag_doc_id: str | None`
    - `approved_by: str | None`
    - `reject_reason: str | None`
    - `created_at: datetime`
    - `indexed_at: datetime | None`
  - `NasFileResponse` dung:
    ```python
    model_config = ConfigDict(from_attributes=True)
    ```
  - `NasReportRequest` fields:
    - `event: str`
    - `nas_path: str`
    - `file_hash: str | None = None`
    - `extension: str | None = None`
    - `ingest_content: bool = True`
  - Validate `event` chi nhan:
    - `"new"`
    - `"changed"`
    - `"deleted"`
  - `ApproveRequest` fields:
    - `approve: bool`
    - `reject_reason: str | None = None`
  - `FolderRequest` fields:
    - `path: str`
    - `folder_type: str`
    - `is_active: bool = True`
  - Validate `folder_type` chi nhan:
    - `"auto"`
    - `"manual"`
  - `NasFolderResponse` fields:
    - `id: str`
    - `path: str`
    - `folder_type: str`
    - `is_active: bool`
    - `last_scanned: datetime | None`
    - `created_at: datetime`
  - `NasFolderResponse` dung `from_attributes=True`
  - Dung `X | None`, khong dung `Optional[X]`
  - Khong import SQLAlchemy trong schemas
  - _Requirements: 7.1-7.9_

---

- [x] 10. Viet `backend/services/nas_notify.py` - admin notification service
  - Implement pure Python service:
    ```python
    def notify_admin(nas_file: NasFile) -> None
    ```
  - Log structured INFO event:
    ```json
    {
      "event": "nas_pending_review",
      "nas_path": "...",
      "nas_file_id": "...",
      "folder_type": "manual"
    }
    ```
  - Include `correlation_id` neu logger context co
  - Khong dung `httpx`
  - Khong goi external service
  - Neu logging failure hoac unexpected exception xay ra, catch va khong raise
  - _Requirements: 6.1-6.5_

---

- [x] 11. Viet helper functions cho NAS backend state machine
  - Tao helper functions trong router hoac service noi bo:
    ```python
    async def get_nas_file_by_path(db: AsyncSession, nas_path: str) -> NasFile | None
    async def get_nas_file_by_id(db: AsyncSession, file_id: str) -> NasFile | None
    async def find_folder_by_path(db: AsyncSession, nas_path: str) -> NasFolder | None
    ```
  - `find_folder_by_path()` match folder bang path prefix
  - Neu nhieu folder match, chon folder co path dai nhat de uu tien config cu the hon
  - Neu khong co folder config, default `folder_type="auto"`
  - Tat ca DB operations dung SQLAlchemy async `select`
  - Khong dung sync DB call
  - _Requirements: 3, 5, 8, 9_

---

- [x] 12. Viet `backend/routers/internal/nas.py` - hash lookup va report endpoint
  - Tao `APIRouter`
  - Implement:
    ```python
    GET /hash?path=...
    POST /report
    ```
  - `GET /hash`:
    - Accept query parameter `path`
    - Lookup `NasFile.nas_path == path`
    - Neu found, return:
      ```json
      {"path": "...", "hash": "..."}
      ```
    - Neu not found, return HTTP 404
    - Khong can Bearer token
  - `POST /report`:
    - Accept `NasReportRequest`
    - Log moi event voi `nas_path`, `event`, `correlation_id`
    - `event="new"`:
      - find folder by prefix
      - folder auto hoac default -> create `NasFile(status="queued")`
      - folder manual -> create `NasFile(status="pending_review")`
      - manual folder thi goi `nas_notify_service.notify_admin(nas_file)`
    - `event="changed"`:
      - neu record khong ton tai -> xu ly nhu new
      - neu record ton tai va `status="indexed"` -> update `file_hash`, set `status="queued"`
      - neu record ton tai o trang thai khac, update hash neu hop ly nhung khong pha state machine
    - `event="deleted"`:
      - neu record ton tai -> set `status="rejected"`, `reject_reason="File deleted from NAS"`
      - neu record khong ton tai -> return ok no-op
    - Return:
      ```json
      {"ok": true}
      ```
  - Endpoint mount duoi `/api/internal/nas`
  - _Requirements: 3.1-3.6, 5.1-5.9_

---

- [x] 13. Viet `backend/routers/admin/nas_queue.py` - admin approval queue
  - Tao `APIRouter`
  - Tat ca endpoints require:
    ```python
    Depends(require_admin)
    ```
  - Implement:
    ```http
    GET /admin/nas/queue
    POST /admin/nas/queue/{file_id}/action
    ```
  - `GET /admin/nas/queue`:
    - Return list `NasFileResponse`
    - Filter `status="pending_review"`
    - Order by `created_at DESC`
  - `POST /admin/nas/queue/{file_id}/action`:
    - Accept `ApproveRequest`
    - Neu file khong ton tai -> HTTP 404
    - Neu status khac `pending_review` -> HTTP 409:
      ```json
      {"detail": "File is not in pending_review status"}
      ```
    - Neu `approve=true`:
      - set `status="queued"`
      - set `approved_by=current_user.id`
      - set `approved_at=now`
      - return `NasFileResponse`
    - Neu `approve=false`:
      - neu thieu `reject_reason` -> HTTP 422:
        ```json
        {"detail": "reject_reason is required when rejecting"}
        ```
      - set `status="rejected"`
      - set `reject_reason`
      - return `NasFileResponse`
  - _Requirements: 8.1-8.8_

---

- [x] 14. Viet `backend/routers/admin/nas_folders.py` - admin folder config CRUD
  - Tao `APIRouter`
  - Tat ca endpoints require:
    ```python
    Depends(require_admin)
    ```
  - Implement:
    ```http
    GET /admin/nas/folders
    POST /admin/nas/folders
    PATCH /admin/nas/folders/{folder_id}
    DELETE /admin/nas/folders/{folder_id}
    ```
  - `GET /admin/nas/folders`:
    - Return list `NasFolderResponse`
    - Order by `path`
  - `POST /admin/nas/folders`:
    - Accept `FolderRequest`
    - Validate `folder_type`
    - Neu path da ton tai -> HTTP 409:
      ```json
      {"detail": "Folder path already configured"}
      ```
    - Create `NasFolder`
    - Return HTTP 201 + `NasFolderResponse`
  - `PATCH /admin/nas/folders/{folder_id}`:
    - Allow partial update:
      - `folder_type`
      - `is_active`
    - Validate `folder_type` neu provided
    - Neu folder khong ton tai -> HTTP 404
  - `DELETE /admin/nas/folders/{folder_id}`:
    - Delete folder config
    - Neu khong ton tai -> HTTP 404
  - _Requirements: 9.1-9.7_

---

- [x] 15. Mount NAS routers trong `backend/main.py`
  - Import routers:
    ```python
    from backend.routers.internal import nas as internal_nas
    from backend.routers.admin import nas_queue, nas_folders
    ```
  - Mount internal NAS router:
    ```python
    app.include_router(
        internal_nas.router,
        prefix="/api/internal/nas",
        tags=["internal-nas"],
    )
    ```
  - Mount admin queue router:
    ```python
    app.include_router(
        nas_queue.router,
        prefix="/admin/nas/queue",
        tags=["admin-nas-queue"],
    )
    ```
  - Mount admin folders router:
    ```python
    app.include_router(
        nas_folders.router,
        prefix="/admin/nas/folders",
        tags=["admin-nas-folders"],
    )
    ```
  - Ensure internal router has no auth dependency
  - Ensure admin routers use `require_admin` internally
  - _Requirements: 3.6, 8.1, 9.1_

---

- [x] 16. Viet unit tests cho `nas_connector/watcher.py`
  - Tao `tests/unit/nas_connector/test_watcher.py`
  - Dung `pytest`, `pytest-asyncio`, `tmp_path`, `AsyncMock`
  - Test `.pdf` new file:
    - create file in `tmp_path`
    - mock `uploader.get_hash` return `None`
    - verify `report_new(..., ingest_content=True)`
  - Test `.dwg` new file:
    - verify `ingest_content=False`
  - Test unsupported `.txt`:
    - verify no uploader call
  - Test changed file:
    - mock `get_hash` return old hash
    - verify `report_changed(...)`
  - Test deleted file detection neu implemented:
    - provide previous/known paths snapshot
    - remove file
    - verify `report_deleted(...)`
  - Test exception isolation:
    - first file causes `uploader.report_new` to raise
    - second file still processed
  - Tests khong can real NAS, real backend, Docker
  - _Requirements: 12.1-12.8_

---

- [x] 17. Viet unit tests cho `nas_connector/uploader.py`
  - Tao `tests/unit/nas_connector/test_uploader.py`
  - Dung `pytest`, `pytest-asyncio`, `pytest-httpx`
  - Test `get_hash()`:
    - 200 response returns hash string
    - 404 response returns `None`
  - Test `report_new()` sends:
    ```json
    {
      "event": "new",
      "nas_path": "...",
      "file_hash": "...",
      "extension": ".pdf",
      "ingest_content": true
    }
    ```
  - Test `.dwg` / metadata-only file sends `ingest_content=false`
  - Test `report_changed()` sends event `"changed"`
  - Test `report_deleted()` sends event `"deleted"`
  - Test 500 backend response does not raise
  - Test connection error does not raise
  - Test every outgoing request includes `X-Correlation-ID`
  - _Requirements: 13.1-13.9_

---

- [x] 18. Viet unit tests cho backend NAS schemas
  - Tao hoac update `tests/unit/backend/test_schemas.py`
  - Test `NasReportRequest` accepts valid events:
    - `"new"`
    - `"changed"`
    - `"deleted"`
  - Test invalid event raises `ValidationError`
  - Test `FolderRequest` accepts `folder_type="auto"` and `"manual"`
  - Test invalid folder type raises `ValidationError`
  - Test `NasFileResponse` can validate from ORM-like object using `from_attributes=True`
  - Test `NasFolderResponse` can validate from ORM-like object using `from_attributes=True`
  - _Requirements: 7.1-7.9_

---

- [x] 19. Viet unit tests cho backend internal NAS router
  - Tao `tests/unit/backend/test_internal_nas_router.py`
  - Mock DB session hoac dung test session fixture theo project convention
  - Test `GET /api/internal/nas/hash`:
    - existing path -> HTTP 200 + `{"path": ..., "hash": ...}`
    - missing path -> HTTP 404
  - Test `POST /api/internal/nas/report`:
    - new file under auto folder -> creates `NasFile(status="queued")`
    - new file under manual folder -> creates `NasFile(status="pending_review")`
    - manual new file calls `nas_notify_service.notify_admin`
    - changed indexed file -> status resets to `queued`
    - changed missing file -> treated as new
    - deleted existing file -> status `rejected`, reject_reason set
    - deleted missing file -> HTTP 200 no-op
  - Verify event log includes `nas_path`, `event`, `correlation_id`
  - _Requirements: 3.1-3.6, 5.1-5.9, 6.1-6.5_

---

- [x] 20. Viet unit tests cho admin NAS queue router
  - Tao `tests/unit/backend/test_admin_nas_queue.py`
  - Use `admin_client` fixture
  - Test `GET /admin/nas/queue` returns only `pending_review` files
  - Test queue sorted by `created_at DESC`
  - Test approve action:
    - status `pending_review` -> `queued`
    - set `approved_by`
    - set `approved_at`
  - Test reject action:
    - requires `reject_reason`
    - sets `status="rejected"`
    - stores `reject_reason`
  - Test reject without reason -> HTTP 422
  - Test missing file -> HTTP 404
  - Test action on non-`pending_review` file -> HTTP 409
  - Test normal user cannot access admin endpoints -> HTTP 403
  - _Requirements: 8.1-8.8_

---

- [x] 21. Viet unit tests cho admin NAS folders router
  - Tao `tests/unit/backend/test_admin_nas_folders.py`
  - Use `admin_client` fixture
  - Test `GET /admin/nas/folders` returns all folders ordered by path
  - Test `POST /admin/nas/folders` creates folder config
  - Test duplicate path returns HTTP 409
  - Test invalid folder type returns HTTP 422
  - Test `PATCH /admin/nas/folders/{folder_id}` updates `folder_type` and/or `is_active`
  - Test `PATCH` missing folder returns HTTP 404
  - Test `DELETE` removes folder config
  - Test `DELETE` missing folder returns HTTP 404
  - Test normal user cannot access admin endpoints -> HTTP 403
  - _Requirements: 9.1-9.7_

---

- [ ] 22. Checkpoint - run NAS Connector unit tests
  - Chay:
    ```bash
    pytest tests/unit/nas_connector/ -v
    ```
  - Verify:
    - watcher tests pass
    - uploader tests pass
    - khong can NAS that
    - khong can backend that
    - khong can Docker
  - _Requirements: 12, 13_

---

- [ ] 23. Checkpoint - run backend NAS unit tests
  - Chay:
    ```bash
    pytest tests/unit/backend/ -k "nas" -v
    ```
  - Verify:
    - schemas tests pass
    - internal NAS router tests pass
    - admin queue tests pass
    - admin folder tests pass
  - Ensure existing backend tests tu Spec 2 khong bi regression:
    ```bash
    pytest tests/unit/backend/ -v
    ```
  - _Requirements: 3, 5, 6, 7, 8, 9_

---

- [ ] 24. Manual verification voi running stack
  - Start stack tu Spec 1 + Spec 2:
    ```bash
    docker compose up -d
    ```
  - Ensure backend is reachable from connector network:
    ```bash
    curl http://localhost:8000/health
    ```
  - Create test folder config:
    - auto folder: `/projects/test-auto`
    - manual folder: `/projects/test-manual`
  - Add PDF vao auto-sync folder
  - Verify DB:
    - `NasFile.status == "queued"`
    - `folder_type == "auto"`
  - Add PDF vao manual-review folder
  - Verify DB:
    - `NasFile.status == "pending_review"`
    - `folder_type == "manual"`
  - Call admin approve endpoint
  - Verify status changes:
    - `pending_review` -> `queued`
  - Delete file from NAS
  - Verify:
    - `NasFile.status == "rejected"`
    - `reject_reason == "File deleted from NAS"`
  - Check Seq logs:
    - connector poll logs contain `service="nas-connector"`
    - backend report logs contain `correlation_id`
    - manual-review notification contains `event="nas_pending_review"`
  - _Requirements: 2, 3, 5, 6, 8, 10, 11_

---

## Task Dependency Graph

- Tasks 2 và 3 có thể làm song song (config và logger không phụ thuộc nhau)
- Task 4 (uploader) phụ thuộc Tasks 2 và 3
- Task 5 (watcher) phụ thuộc Task 4
- Task 6 (deleted file detection) phụ thuộc Task 5
- Task 7 (main.py) phụ thuộc Tasks 2, 4, 5
- Task 8 (notifier stub) có thể làm bất cứ lúc nào
- Task 9 (backend schemas) phụ thuộc cấu trúc backend từ Spec 2
- Task 10 (nas_notify service) phụ thuộc Task 9
- Task 11 (helper functions) phụ thuộc Task 9 và Spec 2 models
- Task 12 (internal router) phụ thuộc Tasks 9, 10, 11
- Task 13 (admin queue router) phụ thuộc Tasks 9, 11 và auth từ Spec 2
- Task 14 (admin folders router) phụ thuộc Tasks 9, 11 và auth từ Spec 2
- Task 15 (mount routers) phụ thuộc Tasks 12, 13, 14
- Tasks 16–21 (unit tests) nên viết song song với implementation tương ứng
- Task 22 phụ thuộc Tasks 16, 17
- Task 23 phụ thuộc Tasks 18, 19, 20, 21
- Task 24 phụ thuộc tất cả tasks trước và stack đang chạy

## Notes

- NAS Connector service must remain **stateless** locally.
- Do **not** add SQLite, JSON state files, or local cache as source of truth.
- Backend PostgreSQL tables `nas_files` and `nas_folders` are the only persistent state.
- NAS Connector must not call LightRAG directly. LightRAG ingestion is handled in Spec 4.
- `/api/internal/nas/*` endpoints are internal-only and rely on Docker network isolation for MVP.
- Admin endpoints must use `Depends(require_admin)`.
- `folder_type` valid values:
  - `"auto"`
  - `"manual"`
- `NasFile.status` values come from Spec 2 model:
  - `"pending"`
  - `"queued"`
  - `"indexing"`
  - `"indexed"`
  - `"failed"`
  - `"pending_review"`
  - `"rejected"`
- Watcher should process:
  - full-content extensions: `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`
  - metadata-only extensions: `.dwg`, `.dxf`, `.png`, `.jpg`, `.jpeg`, `.mp4`, `.avi`, `.step`, `.stl`
- Unsupported extensions are ignored silently.
- Any single-file failure during poll must not stop the whole poll cycle.
- All HTTP requests from NAS Connector to backend must forward `X-Correlation-ID`.
- Tests should run without real NAS, real backend, or Docker whenever possible.

---

## Dependency Notes

- Task 2 and Task 3 can be done in parallel.
- Task 4 depends on Task 2 and Task 3.
- Task 5 depends on Task 4.
- Task 7 depends on Task 2, Task 4, and Task 5.
- Task 9 depends on Spec 2 backend structure.
- Task 12 depends on Task 9, Task 10, and Task 11.
- Task 13 and Task 14 depend on Task 9 and existing auth dependencies from Spec 2.
- Task 15 depends on Tasks 12-14.
- Tests should be written alongside implementation where possible.
