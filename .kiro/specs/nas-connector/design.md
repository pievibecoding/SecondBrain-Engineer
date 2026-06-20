# Design Document — NAS Connector

## Overview

Tài liệu này mô tả thiết kế kỹ thuật cho **Spec 3: NAS Connector** — Python background
service giám sát Synology NAS qua SMB mount và các backend API endpoints để quản lý
NAS file queue.

NAS Connector là service **stateless về local storage** — không lưu SQLite, không tự
quyết định business logic. Tất cả state nằm trong backend PostgreSQL (`NasFile` table).

**Dependency:** Spec 2 (Backend Foundation) — `NasFile`, `NasFolder` ORM models phải
tồn tại, `backend/dependencies/auth.py` (`require_admin`) phải hoạt động.

---

## 1. Kiến trúc tổng thể

### 1.1 Data Flow

```
Synology NAS (SMB)
    │
    │  /mnt/synology → mount host OS
    │  /mnt/synology:/mnt/nas:ro → Docker volume (read-only)
    │
    ▼
nas-connector (container)
    │
    ├── watcher.py — poll /mnt/nas mỗi 5 phút
    │       │ compute md5 hash của mỗi file
    │       │
    │       ├── hash changed? → report_changed(nas_path, new_hash)
    │       ├── new file?     → report_new(nas_path, hash, ext, ingest_content)
    │       └── file deleted? → report_deleted(nas_path)
    │
    └── uploader.py — HTTP client
            │
            POST /api/internal/nas/report  (Docker network only)
            GET  /api/internal/nas/hash    (hash lookup)
            │
            ▼
backend (container)
    │
    ├── routers/internal/nas.py
    │       │
    │       ├── Nhận report → áp dụng state machine
    │       │       "new" + auto folder → status=queued
    │       │       "new" + manual folder → status=pending_review + notify_admin
    │       │       "changed" + indexed → status=queued (re-ingest)
    │       │       "deleted" → status=rejected
    │       │
    │       └── Hash lookup → trả file_hash hoặc 404
    │
    ├── routers/admin/nas_queue.py — approve/reject (require_admin)
    └── routers/admin/nas_folders.py — CRUD folder config (require_admin)
```

### 1.2 Service Boundaries

| Component | Location | Responsibility |
|---|---|---|
| `watcher.py` | `nas-connector/` | Detect file changes, compute hash |
| `uploader.py` | `nas-connector/` | HTTP client → backend report endpoint |
| `notifier.py` | `nas-connector/` | (stub) — future: real-time push notification |
| `routers/internal/nas.py` | `backend/` | Receive reports, apply state machine |
| `routers/admin/nas_queue.py` | `backend/` | Admin approve/reject |
| `routers/admin/nas_folders.py` | `backend/` | Admin folder CRUD |
| `services/nas_notify.py` | `backend/` | Structured log notification |

---

## 2. NAS Connector File Structure

```
nas-connector/
├── main.py          ← async entry point, lifespan loop, signal handling
├── config.py        ← Pydantic Settings (NAS_HOST, NAS_USER, NAS_PASS, ...)
├── watcher.py       ← poll loop, hash compute, classify extensions
├── uploader.py      ← httpx async HTTP client → backend internal API
├── notifier.py      ← stub for future push notification
├── logger.py        ← structlog → Seq (same pattern as backend)
└── requirements.txt
    ├── pydantic-settings==2.7.0
    ├── httpx==0.28.1
    ├── structlog==24.4.0
    └── pytest-httpx==0.35.0  # dev dependency
```

---

## 3. Backend File Structure (additions)

```
backend/
├── schemas/
│   └── nas.py               ← NasReportRequest, NasFileResponse, ApproveRequest,
│                               FolderRequest, NasFolderResponse
├── routers/
│   ├── internal/
│   │   ├── __init__.py
│   │   └── nas.py           ← GET /hash, POST /report (Docker network only)
│   └── admin/
│       ├── __init__.py
│       ├── nas_queue.py     ← GET/POST queue (require_admin)
│       └── nas_folders.py   ← CRUD folders (require_admin)
└── services/
    └── nas_notify.py        ← log-based admin notification
```

---

## 4. NasFile State Machine

### 4.1 States và Transitions

```
                       ┌─────────────────────────────────────────────┐
                       │           NasFile.status values              │
                       └─────────────────────────────────────────────┘

  NAS Connector detects file
            │
            ▼
        [INSERT NasFile]
            │
     ┌──────┴──────┐
     │             │
  auto folder   manual folder
     │             │
     ▼             ▼
  "queued"   "pending_review" ──── admin reject ──→ "rejected"
     │             │
     │         admin approve
     │             │
     └──────┬──────┘
            │
            ▼  (Spec 4: LightRAG Integration triggers this)
        "indexing"
            │
     ┌──────┴──────┐
     │             │
  success       failure
     │             │
     ▼             ▼
  "indexed"     "failed"

  Note: "changed" event trên file "indexed" → back to "queued" (re-ingest)
```

### 4.2 Transition Rules

| Event | Điều kiện | Transition | Ghi chú |
|---|---|---|---|
| `new` | folder_type=auto | — → `queued` | Tự động queue |
| `new` | folder_type=manual | — → `pending_review` | Chờ admin |
| `changed` | status=indexed | `indexed` → `queued` | Re-ingest |
| `changed` | không có record | — → xử lý như `new` | |
| `deleted` | bất kỳ | `* → rejected` | reject_reason="File deleted from NAS" |
| admin approve | status=pending_review | `pending_review` → `queued` | |
| admin reject | status=pending_review | `pending_review` → `rejected` | Cần reject_reason |
| LightRAG start | status=queued | `queued` → `indexing` | Spec 4 |
| LightRAG done | status=indexing | `indexing` → `indexed` | Spec 4 |
| LightRAG fail | status=indexing | `indexing` → `failed` | Spec 4 |

---

## 5. Watcher Design

### 5.1 Poll Cycle Algorithm

```python
# nas-connector/watcher.py

async def poll_once(mount_path: str, uploader: Uploader) -> None:
    logger.info("Poll cycle started", mount_path=mount_path)
    count = 0

    for file_path in Path(mount_path).rglob("*"):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS and ext not in METADATA_ONLY_EXTENSIONS:
            continue

        nas_path = str(file_path)
        ingest_content = ext in SUPPORTED_EXTENSIONS

        try:
            current_hash = compute_md5(file_path)
            stored_hash = await uploader.get_hash(nas_path)  # None if 404

            if stored_hash is None:
                await uploader.report_new(nas_path, current_hash, ext, ingest_content)
            elif stored_hash != current_hash:
                await uploader.report_changed(nas_path, current_hash)

            count += 1
        except Exception as e:
            logger.error("File processing error", nas_path=nas_path, error=str(e))
            # Continue — one file failure does not stop the cycle

    # Deleted file detection: compare stored paths with scanned paths
    # (backend tracks known paths; poll returns list of paths for this connector)
    # Implementation: GET /api/internal/nas/paths → find missing → report_deleted

    logger.info("Poll cycle done", files_processed=count)
```

### 5.2 Extension Classification

```python
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt'
}

METADATA_ONLY_EXTENSIONS = {
    '.dwg', '.dxf', '.png', '.jpg', '.jpeg',
    '.mp4', '.avi', '.step', '.stl'
}
```

### 5.3 Hash Computation

```python
import hashlib

def compute_md5(file_path: Path) -> str:
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```

---

## 6. Uploader Design

### 6.1 HTTP Client Pattern

```python
# nas-connector/uploader.py
import httpx

class Uploader:
    def __init__(self, backend_url: str):
        self._url = backend_url

    async def get_hash(self, nas_path: str) -> str | None:
        """Returns stored hash or None if not found."""
        cid = str(uuid4())
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self._url}/api/internal/nas/hash",
                    params={"path": nas_path},
                    headers={"X-Correlation-ID": cid}
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()["hash"]
            except httpx.ConnectError:
                logger.warning("Backend unreachable for hash lookup", nas_path=nas_path)
                return None  # Treat as "no stored hash" → will re-report as new

    async def report_new(
        self, nas_path: str, file_hash: str,
        extension: str, ingest_content: bool
    ) -> None:
        await self._report({
            "event": "new",
            "nas_path": nas_path,
            "file_hash": file_hash,
            "extension": extension,
            "ingest_content": ingest_content
        })

    async def _report(self, payload: dict) -> None:
        cid = str(uuid4())
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{self._url}/api/internal/nas/report",
                    json=payload,
                    headers={"X-Correlation-ID": cid}
                )
                if not resp.is_success:
                    logger.error(
                        "Backend report failed",
                        status=resp.status_code,
                        nas_path=payload.get("nas_path"),
                        correlation_id=cid
                    )
            except (httpx.ConnectError, httpx.TimeoutException):
                logger.warning(
                    "Backend unreachable for report",
                    nas_path=payload.get("nas_path"),
                    correlation_id=cid
                )
```

---

## 7. Backend Internal Router Design

### 7.1 Report Endpoint Logic

```python
# backend/routers/internal/nas.py

@router.post("/report")
async def report_nas_event(
    payload: NasReportRequest,
    db: AsyncSession = Depends(get_session),
    correlation_id: str = Depends(get_correlation_id),
) -> dict:
    # Determine folder type by matching NasFolder path prefix
    folder = await find_folder_by_path(db, payload.nas_path)
    folder_type = folder.folder_type if folder else "auto"  # default auto

    if payload.event == "new":
        nas_file = NasFile(
            nas_path=payload.nas_path,
            folder_type=folder_type,
            file_hash=payload.file_hash,
            status="queued" if folder_type == "auto" else "pending_review",
        )
        db.add(nas_file)
        await db.commit()

        if folder_type == "manual":
            await nas_notify_service.notify_admin(nas_file)

    elif payload.event == "changed":
        nas_file = await get_nas_file_by_path(db, payload.nas_path)
        if nas_file is None:
            # treat as new
            ...
        elif nas_file.status == "indexed":
            nas_file.file_hash = payload.file_hash
            nas_file.status = "queued"
            await db.commit()

    elif payload.event == "deleted":
        nas_file = await get_nas_file_by_path(db, payload.nas_path)
        if nas_file:
            nas_file.status = "rejected"
            nas_file.reject_reason = "File deleted from NAS"
            await db.commit()

    logger.info("NAS event processed", event=payload.event,
                nas_path=payload.nas_path, correlation_id=correlation_id)
    return {"ok": True}
```

### 7.2 Admin Queue Endpoint Logic

```python
# backend/routers/admin/nas_queue.py

@router.post("/{file_id}/action")
async def action_on_file(
    file_id: str,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserResponse = Depends(require_admin),
) -> NasFileResponse:
    nas_file = await get_nas_file_by_id(db, file_id)
    if nas_file is None:
        raise HTTPException(404, f"NasFile not found: {file_id}")
    if nas_file.status != "pending_review":
        raise HTTPException(409, "File is not in pending_review status")

    if body.approve:
        nas_file.status = "queued"
        nas_file.approved_by = current_user.id
        nas_file.approved_at = datetime.utcnow()
    else:
        if not body.reject_reason:
            raise HTTPException(422, "reject_reason is required when rejecting")
        nas_file.status = "rejected"
        nas_file.reject_reason = body.reject_reason

    await db.commit()
    return NasFileResponse.model_validate(nas_file)
```

---

## 8. Security: Internal Endpoints

`/api/internal/` endpoints bảo vệ bằng **Docker network isolation**:

- `backend` container KHÔNG expose port `8000` ra ngoài host khi production (hoặc chỉ expose `127.0.0.1:8000`)
- `nas-connector` gọi `http://backend:8000/api/internal/...` qua Docker internal network
- Không cần Bearer token cho internal endpoints — network isolation là đủ cho MVP
- Trong `backend/main.py`: mount internal router với prefix `/api/internal` (không có auth middleware)

---

## 9. Testing Strategy

### 9.1 Unit Tests

| File | Mock target | Kiểm tra |
|---|---|---|
| `test_watcher.py` | `uploader.*` (AsyncMock), `tmp_path` | Extension classification, hash change detection, deleted file, exception isolation |
| `test_uploader.py` | `pytest-httpx` `httpx_mock` | Payload shape per event, 500 → no raise, connection error → no raise, X-Correlation-ID present |

### 9.2 Key Test Cases

```python
# test_watcher.py — verify extension classification
async def test_pdf_triggers_report_new_with_content(tmp_path, mock_uploader):
    (tmp_path / "test.pdf").write_bytes(b"fake pdf content")
    await poll_once(str(tmp_path), mock_uploader)
    mock_uploader.report_new.assert_called_once()
    _, kwargs = mock_uploader.report_new.call_args
    assert kwargs["ingest_content"] is True

async def test_dwg_triggers_report_new_without_content(tmp_path, mock_uploader):
    (tmp_path / "drawing.dwg").write_bytes(b"fake dwg")
    await poll_once(str(tmp_path), mock_uploader)
    mock_uploader.report_new.assert_called_once()
    _, kwargs = mock_uploader.report_new.call_args
    assert kwargs["ingest_content"] is False

async def test_txt_file_ignored(tmp_path, mock_uploader):
    (tmp_path / "notes.txt").write_text("some notes")
    await poll_once(str(tmp_path), mock_uploader)
    mock_uploader.report_new.assert_not_called()
```

---

## 10. Requirements Traceability

| Requirement | File(s) tạo ra |
|---|---|
| R1 — NAS Config | `nas-connector/config.py` |
| R2 — File Change Detection | `nas-connector/watcher.py` |
| R3 — Hash Lookup Endpoint | `backend/routers/internal/nas.py` (GET /hash) |
| R4 — Report Uploader | `nas-connector/uploader.py` |
| R5 — Report Endpoint | `backend/routers/internal/nas.py` (POST /report) |
| R6 — Admin Notification | `backend/services/nas_notify.py` |
| R7 — NAS Schemas | `backend/schemas/nas.py` |
| R8 — Admin Queue | `backend/routers/admin/nas_queue.py` |
| R9 — Admin Folders | `backend/routers/admin/nas_folders.py` |
| R10 — NAS Logger | `nas-connector/logger.py` |
| R11 — Entry Point | `nas-connector/main.py` |
| R12 — Watcher Tests | `tests/unit/nas_connector/test_watcher.py` |
| R13 — Uploader Tests | `tests/unit/nas_connector/test_uploader.py` |
