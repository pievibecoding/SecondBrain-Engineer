# Requirements Document

## Introduction

Spec này xây dựng **NAS Connector service** và các backend API endpoints cần thiết để
quản lý file từ Synology NAS. NAS Connector là Python background service chạy watchdog
trên SMB mount, phát hiện file mới/thay đổi, rồi report lên backend API — không bao giờ
gọi LightRAG trực tiếp.

Backend nhận report từ NAS Connector, thực hiện state transitions trên `NasFile` table,
thông báo admin khi có file cần duyệt, và expose các admin endpoints để approve/reject.

**Dependency:** Spec 2 (Backend Foundation) phải hoàn thành — PostgreSQL, auth, ORM models
`NasFile`/`NasFolder` đã tồn tại.

**Definition of Done:**
- Thêm file PDF vào auto-sync folder → `NasFile` record với `status=queued` trong DB
- Thêm file vào manual-review folder → `NasFile` với `status=pending_review`
- Admin approve → status chuyển `queued`
- `pytest tests/unit/nas_connector/ -v` passes

---

## Glossary

- **NAS Connector**: Python background service (`nas-connector/`) poll SMB mount mỗi 5 phút
- **SMB Mount**: Synology NAS được mount vào host OS tại `/mnt/synology`, expose vào container qua `volumes: /mnt/synology:/mnt/nas:ro`
- **SUPPORTED_EXTENSIONS**: `.pdf, .docx, .doc, .xlsx, .xls, .pptx, .ppt` — files được parse content
- **METADATA_ONLY_EXTENSIONS**: `.dwg, .dxf, .png, .jpg, .mp4, .avi, .step, .stl` — chỉ index tên file + folder path
- **auto folder**: NAS folder config với `folder_type="auto"` — file detect xong tự QUEUE
- **manual folder**: NAS folder config với `folder_type="manual"` — file detect xong chờ admin duyệt
- **Report**: NAS Connector gọi `POST /api/internal/nas/report` để thông báo file mới/changed/deleted
- **State Machine**: Chuỗi transitions của `NasFile.status`: `pending_review` / `queued` → `indexing` → `indexed` / `failed`
- **Internal endpoint**: `GET /api/internal/nas/hash` — chỉ accessible từ Docker network, không expose ra ngoài
- **NasFileResponse**: Pydantic schema biểu diễn NasFile cho API response
- **ApproveRequest**: Pydantic schema cho admin approve/reject action
- **FolderRequest**: Pydantic schema cho CRUD NAS folder config

---

## Requirements

### Requirement 1 — NAS Connector Configuration

**User Story:** As a system operator, I want the NAS Connector configured via environment
variables, so that NAS credentials and connection details can be changed without modifying code.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** nas-rules.md (Environment Variables section), pa3-design Section 4 (`nas-connector/config.py`)

#### Acceptance Criteria

1. THE `NASConfig` SHALL be implemented in `nas-connector/config.py` using `pydantic-settings` `BaseSettings`.
2. THE `NASConfig` SHALL expose the following required settings: `NAS_HOST` (Synology IP), `NAS_USER` (dedicated read-only account), `NAS_PASS`, `NAS_SHARE` (shared folder name), `NAS_MOUNT_PATH` (default `/mnt/nas`), `BACKEND_API_URL` (default `http://backend:8000`).
3. THE `NASConfig` SHALL expose `POLL_INTERVAL_SECONDS` (default `300` — 5 minutes).
4. THE `NASConfig` SHALL expose `SEQ_URL` (default `http://seq:5341`) for structured logging.
5. WHEN a required setting is missing, THE `NASConfig` SHALL raise `ValidationError` at startup with the missing field name.
6. THE `NASConfig` SHALL provide a singleton `config` importable as `from nas_connector.config import config`.

---

### Requirement 2 — File Change Detection (Watcher)

**User Story:** As a system operator, I want the NAS Connector to automatically detect new,
modified, and deleted files on the NAS share, so that the knowledge base stays up to date
without manual intervention.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** nas-rules.md (File Change Detection, Folder Path Convention), pa3-design Section 5.1 (Ingestion workflow)

#### Acceptance Criteria

1. THE `Watcher` SHALL be implemented in `nas-connector/watcher.py` and poll `NAS_MOUNT_PATH` every `POLL_INTERVAL_SECONDS`.
2. THE `Watcher` SHALL recursively scan all files under `NAS_MOUNT_PATH` and compute `md5` hash for each file.
3. WHEN a file with a supported extension is found that has no record in the backend (hash lookup returns 404), THE `Watcher` SHALL call `uploader.report_new(nas_path, file_hash, extension)`.
4. WHEN a file's current md5 hash differs from the hash stored in backend, THE `Watcher` SHALL call `uploader.report_changed(nas_path, new_hash)`.
5. WHEN a file previously seen is no longer present on the mount, THE `Watcher` SHALL call `uploader.report_deleted(nas_path)`.
6. THE `Watcher` SHALL process `SUPPORTED_EXTENSIONS` files (`.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`) with full content flag `ingest_content=true`.
7. THE `Watcher` SHALL process `METADATA_ONLY_EXTENSIONS` files (`.dwg`, `.dxf`, `.png`, `.jpg`, `.mp4`, `.avi`, `.step`, `.stl`) with flag `ingest_content=false` — metadata index only.
8. THE `Watcher` SHALL ignore all other file extensions silently.
9. WHEN an exception occurs while processing a single file, THE `Watcher` SHALL log the error with `nas_path` and `correlation_id`, then continue processing remaining files — one file failure SHALL NOT stop the poll cycle.
10. THE `Watcher` SHALL log at INFO level at the start and end of each poll cycle with count of files processed.

---

### Requirement 3 — File Hash Lookup (Internal Backend Endpoint)

**User Story:** As the NAS Connector service, I want to query the backend for the stored hash
of a given NAS path, so that I can determine whether a file has changed since last indexing.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** nas-rules.md (Single Source of Truth section), pa3-design Section 4 (`backend/routers/internal/nas.py`)

#### Acceptance Criteria

1. THE `InternalNasRouter` SHALL implement `GET /api/internal/nas/hash` in `backend/routers/internal/nas.py`.
2. THE endpoint SHALL accept query parameter `path` (the NAS path string).
3. WHEN a `NasFile` record exists for the given `path`, THE endpoint SHALL return `{"path": "...", "hash": "..."}` with HTTP 200.
4. WHEN no `NasFile` record exists for the given `path`, THE endpoint SHALL return HTTP 404.
5. THE endpoint SHALL be protected by Docker network isolation only — no Bearer token required (accessed only by nas-connector container on internal network).
6. THE endpoint SHALL be mounted under `/api/internal/` prefix in `backend/main.py` and NEVER exposed via public port mapping.

---

### Requirement 4 — Report New/Changed/Deleted Files (Uploader)

**User Story:** As the NAS Connector, I want to report file events to the backend API, so that
the backend can apply the correct state machine transition without the connector needing to know
business rules.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** nas-rules.md (Single Source of Truth — NAS connector gọi backend API, không tự lưu), pa3-design Section 5.1

#### Acceptance Criteria

1. THE `Uploader` SHALL be implemented in `nas-connector/uploader.py` using `httpx.AsyncClient`.
2. THE `Uploader` SHALL implement `report_new(nas_path, file_hash, extension, ingest_content) -> None` that calls `POST /api/internal/nas/report` with `{"event": "new", "nas_path": ..., "file_hash": ..., "extension": ..., "ingest_content": ...}`.
3. THE `Uploader` SHALL implement `report_changed(nas_path, new_hash) -> None` that calls `POST /api/internal/nas/report` with `{"event": "changed", "nas_path": ..., "file_hash": ...}`.
4. THE `Uploader` SHALL implement `report_deleted(nas_path) -> None` that calls `POST /api/internal/nas/report` with `{"event": "deleted", "nas_path": ...}`.
5. THE `Uploader` SHALL include a `X-Correlation-ID` header (generated per report call) in all requests.
6. WHEN the backend returns a non-2xx status, THE `Uploader` SHALL log an error with `nas_path`, status code, and `correlation_id`, then NOT raise — connector failure SHALL NOT crash the watcher loop.
7. WHEN the backend is unreachable (connection error / timeout), THE `Uploader` SHALL log a WARNING and silently continue — to be retried on next poll cycle.

---

### Requirement 5 — Report Endpoint (Internal Backend)

**User Story:** As a backend developer, I want an internal endpoint to receive NAS file event
reports, so that the backend can apply state machine transitions and notify admin as needed.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.1 (NAS state machine transitions), nas-rules.md (Folder Types)

#### Acceptance Criteria

1. THE `InternalNasRouter` SHALL implement `POST /api/internal/nas/report` in `backend/routers/internal/nas.py`.
2. THE endpoint SHALL accept `NasReportRequest` schema with fields: `event` (str: `"new"` | `"changed"` | `"deleted"`), `nas_path` (str), `file_hash` (str | None), `extension` (str | None), `ingest_content` (bool, default `true`).
3. WHEN `event="new"` and the NAS path belongs to an **auto** folder (lookup `NasFolder` by path prefix), THE endpoint SHALL create a `NasFile` record with `status="queued"`.
4. WHEN `event="new"` and the NAS path belongs to a **manual** folder, THE endpoint SHALL create a `NasFile` record with `status="pending_review"` and call `nas_notify_service.notify_admin(nas_file)`.
5. WHEN `event="changed"` and a `NasFile` record exists with `status="indexed"`, THE endpoint SHALL update `file_hash` and set `status="queued"` (re-ingest).
6. WHEN `event="changed"` and no existing `NasFile` record exists, THE endpoint SHALL treat it as `event="new"`.
7. WHEN `event="deleted"` and a `NasFile` record exists, THE endpoint SHALL set `status="rejected"` with `reject_reason="File deleted from NAS"`.
8. THE endpoint SHALL return `{"ok": true}` with HTTP 200 on success.
9. THE endpoint SHALL log every received event at INFO level with `nas_path`, `event`, and `correlation_id`.

---

### Requirement 6 — Admin Notification Service

**User Story:** As an admin, I want to be notified in the SecondBrain UI when a new file is
detected in a manual-review folder, so that I can review and approve or reject it promptly.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 5.1 (manual folder flow — notify admin), Section 5.3 (Admin panel workflow)

#### Acceptance Criteria

1. THE `NasNotifyService` SHALL be implemented in `backend/services/nas_notify.py`.
2. THE `NasNotifyService` SHALL provide `notify_admin(nas_file: NasFile) -> None` that logs a structured INFO entry: `{"event": "nas_pending_review", "nas_path": ..., "nas_file_id": ...}`.
3. THE notification log entry SHALL include `nas_path`, `nas_file_id`, and `folder_type` fields so that Seq can be filtered to show all pending files.
4. THE `NasNotifyService` SHALL be a pure Python service — NO httpx, NO external HTTP calls.
5. WHEN the notify call fails (e.g., logging error), THE service SHALL NOT raise — admin notification failure must NOT block file reporting.

> **Note:** In-app push notifications (WebSocket/SSE to frontend) are out of scope for this spec.
> Seq log entry is sufficient for MVP — admin checks admin panel periodically.

---

### Requirement 7 — NAS Schemas (Pydantic)

**User Story:** As a backend developer, I want Pydantic V2 schemas for NAS-related API
request/response, so that all NAS endpoints have consistent, validated data shapes.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8 (API contracts — admin NAS endpoints), Section 3 (Key Decisions — `schemas/` = Pydantic only)

#### Acceptance Criteria

1. THE `NasSchemas` SHALL be defined in `backend/schemas/nas.py` using Pydantic V2 `BaseModel`.
2. THE `NasSchemas` SHALL define `NasFileResponse` with fields: `id` (str), `nas_path` (str), `folder_type` (str), `status` (str), `file_hash` (str | None), `lightrag_doc_id` (str | None), `approved_by` (str | None), `reject_reason` (str | None), `created_at` (datetime), `indexed_at` (datetime | None).
3. THE `NasFileResponse` SHALL have `model_config = ConfigDict(from_attributes=True)`.
4. THE `NasSchemas` SHALL define `NasReportRequest` with fields: `event` (str), `nas_path` (str), `file_hash` (str | None = None), `extension` (str | None = None), `ingest_content` (bool = True).
5. THE `NasSchemas` SHALL define `ApproveRequest` with field: `approve` (bool) and `reject_reason` (str | None = None).
6. THE `NasSchemas` SHALL define `FolderRequest` with fields: `path` (str), `folder_type` (str — `"auto"` | `"manual"`), `is_active` (bool = True).
7. THE `NasSchemas` SHALL define `NasFolderResponse` with fields: `id` (str), `path` (str), `folder_type` (str), `is_active` (bool), `last_scanned` (datetime | None), `created_at` (datetime). With `model_config = ConfigDict(from_attributes=True)`.
8. THE `NasSchemas` SHALL use `X | None` union syntax — NOT `Optional[X]`.
9. THE `NasSchemas` SHALL NOT contain any SQLAlchemy code.

---

### Requirement 8 — Admin NAS Queue Endpoints

**User Story:** As an admin, I want to view files pending review and approve or reject them
via API, so that I can control which documents get indexed into the knowledge base.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.3 (Admin panel — approve/reject flow), Section 8 (API contracts — `/admin/nas/queue`)

#### Acceptance Criteria

1. THE `AdminNasQueueRouter` SHALL be implemented in `backend/routers/admin/nas_queue.py` with all endpoints requiring `Depends(require_admin)`.
2. THE `AdminNasQueueRouter` SHALL implement `GET /admin/nas/queue` that returns a list of `NasFileResponse` with `status="pending_review"`, ordered by `created_at` desc.
3. THE `AdminNasQueueRouter` SHALL implement `POST /admin/nas/queue/{file_id}/action` that accepts `ApproveRequest`.
4. WHEN `approve=true` is submitted, THE endpoint SHALL set `NasFile.status="queued"`, set `approved_by` to current user ID, set `approved_at` to now, and return `NasFileResponse` with HTTP 200.
5. WHEN `approve=false` is submitted with a `reject_reason`, THE endpoint SHALL set `NasFile.status="rejected"`, store `reject_reason`, and return `NasFileResponse` with HTTP 200.
6. WHEN `approve=false` is submitted WITHOUT a `reject_reason`, THE endpoint SHALL return HTTP 422 with detail `"reject_reason is required when rejecting"`.
7. WHEN the `file_id` does not exist, THE endpoint SHALL return HTTP 404.
8. WHEN the file's current status is NOT `"pending_review"`, THE endpoint SHALL return HTTP 409 with detail `"File is not in pending_review status"`.

---

### Requirement 9 — Admin NAS Folder Config Endpoints

**User Story:** As an admin, I want to manage which NAS folders are watched and whether
they require manual review, so that I can control the ingestion pipeline per folder.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `nas-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.3 (Admin panel — folder config), Section 4 (`backend/routers/admin/nas_folders.py`), nas-rules.md (Folder Types)

#### Acceptance Criteria

1. THE `AdminNasFoldersRouter` SHALL be implemented in `backend/routers/admin/nas_folders.py` with all endpoints requiring `Depends(require_admin)`.
2. THE `AdminNasFoldersRouter` SHALL implement `GET /admin/nas/folders` returning a list of all `NasFolderResponse`, ordered by `path`.
3. THE `AdminNasFoldersRouter` SHALL implement `POST /admin/nas/folders` accepting `FolderRequest` to create a new `NasFolder` record, returning `NasFolderResponse` with HTTP 201.
4. WHEN `POST /admin/nas/folders` is called with a `path` that already exists, THE endpoint SHALL return HTTP 409 with detail `"Folder path already configured"`.
5. THE `AdminNasFoldersRouter` SHALL implement `PATCH /admin/nas/folders/{folder_id}` accepting partial `FolderRequest` fields to update `folder_type` and/or `is_active`.
6. THE `AdminNasFoldersRouter` SHALL implement `DELETE /admin/nas/folders/{folder_id}` that deletes the folder config. WHEN the folder_id does not exist, return HTTP 404.
7. THE `AdminNasFoldersRouter` SHALL validate that `folder_type` is one of `"auto"` or `"manual"` — return HTTP 422 for invalid values.

---

### Requirement 10 — NAS Connector Logger

**User Story:** As a system operator, I want the NAS Connector to ship structured logs to Seq,
so that I can trace file detection events alongside backend logs using the same `correlation_id`.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 4 (`nas-connector/logger.py`), Section 10.1 (Centralized logging — correlation_id)

#### Acceptance Criteria

1. THE `NASLogger` SHALL be implemented in `nas-connector/logger.py` using `structlog`.
2. THE `NASLogger` SHALL include `service="nas-connector"` in every log entry.
3. THE `NASLogger` SHALL include `correlation_id` as a top-level field when available.
4. THE `NASLogger` SHALL ship logs to `SEQ_URL` from config using HTTP ingestion.
5. WHEN `SEQ_URL` is unreachable, THE `NASLogger` SHALL fall back to stdout — NOT raise an exception.
6. THE `NASLogger` SHALL expose a module-level `logger` importable as `from nas_connector.logger import logger`.

---

### Requirement 11 — NAS Connector Entry Point

**User Story:** As a system operator, I want to start the NAS Connector as a single command,
so that the service initializes, validates config, and begins polling automatically.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 4 (`nas-connector/main.py`), Section 3 (Key Decisions — no SQLite local storage)

#### Acceptance Criteria

1. THE `NASMain` SHALL be implemented in `nas-connector/main.py` as an async entry point.
2. THE `NASMain` SHALL validate config at startup — if required env vars are missing, log error and exit with code 1.
3. THE `NASMain` SHALL check that `NAS_MOUNT_PATH` exists and is readable at startup — if not, log error and exit with code 1.
4. THE `NASMain` SHALL start an infinite poll loop: run watcher scan → sleep `POLL_INTERVAL_SECONDS` → repeat.
5. WHEN `SIGTERM` or `SIGINT` is received, THE `NASMain` SHALL complete the current poll cycle and exit gracefully.
6. THE `NASMain` SHALL NOT create any local SQLite database — all state is in backend PostgreSQL.

---

### Requirement 12 — Unit Tests: NAS Connector Watcher

**User Story:** As a developer, I want unit tests for the NAS Connector watcher using a
temporary directory, so that file detection logic is verified without a real NAS mount.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Tầng 1 — Unit tests, `tests/unit/nas_connector/test_watcher.py`)

#### Acceptance Criteria

1. THE `WatcherTests` SHALL be implemented in `tests/unit/nas_connector/test_watcher.py` using `pytest` and `tmp_path` fixture.
2. THE `WatcherTests` SHALL verify that a new `.pdf` file placed in `tmp_path` causes `uploader.report_new` to be called with the correct `nas_path` and `ingest_content=True`.
3. THE `WatcherTests` SHALL verify that a `.dwg` file causes `uploader.report_new` to be called with `ingest_content=False`.
4. THE `WatcherTests` SHALL verify that a `.txt` file (unsupported extension) does NOT trigger any uploader call.
5. THE `WatcherTests` SHALL verify that when a previously-seen file's content changes (different hash), `uploader.report_changed` is called.
6. THE `WatcherTests` SHALL verify that when a previously-seen file is removed, `uploader.report_deleted` is called.
7. THE `WatcherTests` SHALL verify that an exception thrown by `uploader.report_new` for one file does NOT prevent processing of subsequent files.
8. ALL watcher tests SHALL run without a real NAS mount, real backend, or Docker.

---

### Requirement 13 — Unit Tests: NAS Connector Uploader

**User Story:** As a developer, I want unit tests for the uploader that mock HTTP calls, so that
I can verify report payloads and error handling without a running backend.

### Steering & Skills

- **Steering:** `project-context.md`, `nas-rules.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (`tests/unit/nas_connector/test_uploader.py`)

#### Acceptance Criteria

1. THE `UploaderTests` SHALL be implemented in `tests/unit/nas_connector/test_uploader.py` using `pytest` and `pytest-httpx` to mock HTTP calls.
2. THE `UploaderTests` SHALL verify that `report_new` sends `POST /api/internal/nas/report` with `{"event": "new", "nas_path": ..., "file_hash": ..., "ingest_content": true}`.
3. THE `UploaderTests` SHALL verify that `report_new` with a `.dwg` file sends `ingest_content=false`.
4. THE `UploaderTests` SHALL verify that `report_changed` sends correct payload with `event="changed"`.
5. THE `UploaderTests` SHALL verify that `report_deleted` sends correct payload with `event="deleted"`.
6. THE `UploaderTests` SHALL verify that a 500 response from backend does NOT raise an exception (error is logged, not re-raised).
7. THE `UploaderTests` SHALL verify that a connection error (backend unreachable) does NOT raise an exception (warning logged, not re-raised).
8. THE `UploaderTests` SHALL verify that the `X-Correlation-ID` header is present in all outgoing requests.
9. ALL uploader tests SHALL run without a real backend, NAS, or Docker.
