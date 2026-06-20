# Implementation Plan: Backend Foundation

## Overview

Xây dựng nền tảng backend FastAPI cho SecondBrain: app entry point, config, database,
structured logging, middleware stack (correlation ID + logging + rate limit), dependency
injection, SQLAlchemy ORM models, Alembic migrations, auth schemas/service/router, và
unit tests.

Tất cả code Python. Không có UI. Không cần LightRAG hay Graphiti running — chỉ cần
PostgreSQL, Redis, và Seq (từ Spec 1).

---

## Tasks

- [x] 1. Khởi tạo cấu trúc thư mục và requirements
  - Tạo các thư mục với `__init__.py`: `backend/`, `backend/middleware/`, `backend/dependencies/`, `backend/schemas/`, `backend/models/`, `backend/services/`, `backend/routers/`, `backend/integrations/`, `backend/integrations/lightrag/`, `backend/mcp/`
  - Tạo `backend/requirements.txt` với các dependencies được pin version:
    ```
    fastapi==0.115.6
    uvicorn[standard]==0.32.1
    sqlalchemy[asyncio]==2.0.36
    asyncpg==0.30.0
    alembic==1.14.0
    pydantic==2.10.3
    pydantic-settings==2.7.0
    python-jose[cryptography]==3.3.0
    passlib[bcrypt]==1.7.4
    httpx==0.28.1
    structlog==24.4.0
    redis[hiredis]==5.2.1
    ```
  - Tạo `tests/unit/backend/` directory với `__init__.py`
  - _Requirements: 1, 2, 3, 4, 5, 6, 7, 8, 9_

- [x] 2. Viết `backend/config.py` — Pydantic Settings
  - Định nghĩa class `Settings(BaseSettings)` với `model_config = SettingsConfigDict(env_file=".env")`
  - Các required fields: `DATABASE_URL: str`, `SECRET_KEY: str`
  - Các optional fields với defaults: `REDIS_URL`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `LIGHTRAG_URL`, `GRAPHITI_URL`, `SEQ_URL`, `CORS_ORIGINS`, `MCP_RATE_LIMIT_PER_MINUTE`
  - Export singleton: `settings = Settings()`
  - _Requirements: 2.1–2.8_

- [x] 3. Viết `backend/logger.py` — Structured logging với structlog
  - Tạo `contextvars.ContextVar` tên `_correlation_id` với default `"no-correlation-id"`
  - Expose `set_correlation_id(cid: str)` và `get_correlation_id() -> str`
  - Configure `structlog` processors: add `correlation_id` từ context var, add `service="backend"`, JSON renderer cho production
  - Export module-level `logger = structlog.get_logger()` có thể gọi `logger.info("msg", field=value)`
  - Fallback to stdout khi `SEQ_URL` unreachable — KHÔNG raise exception
  - _Requirements: 4.1–4.8_

- [x] 4. Viết ORM Models
  - [x] 4.1 `backend/models/base.py`
    - Import `DeclarativeBase` từ SQLAlchemy
    - Định nghĩa `class Base(DeclarativeBase): pass`
    - _Requirements: 10.1_
  - [x] 4.2 `backend/models/user.py`
    - Columns: `id` (UUID PK, `server_default=text("gen_random_uuid()")`), `username` (TEXT unique not null), `email` (TEXT unique not null), `password_hash` (TEXT not null), `role` (TEXT not null default `"user"`), `created_at` (TIMESTAMPTZ `server_default=func.now()`)
    - `CheckConstraint("role IN ('user', 'admin')")` trên column `role`
    - _Requirements: 10.2–10.6_
  - [x] 4.3 `backend/models/conversation.py`
    - `Conversation`: `id` UUID PK, `user_id` UUID FK → users.id, `title` TEXT nullable, `created_at`, `updated_at`
    - `Message`: `id` UUID PK, `conversation_id` UUID FK → conversations.id, `role` TEXT not null, `content` TEXT not null, `citations` JSONB nullable, `graphiti_synced` BOOLEAN default false, `created_at`
    - `Conversation.messages` relationship với `lazy="selectin"`
    - `CheckConstraint("role IN ('user', 'assistant')")` trên Message.role
    - _Requirements: 11.1–11.6_
  - [x] 4.4 `backend/models/nas_file.py` và `backend/models/nas_folder.py`
    - `NasFile` đủ columns như design Section 3.1 kể cả `approved_by`, `reject_reason`, `indexed_at`, `error_msg`
    - `CheckConstraint` trên `status` với tất cả 7 giá trị hợp lệ
    - `NasFolder`: `id`, `path` (unique), `folder_type`, `is_active`, `last_scanned`, `created_at`
    - _Requirements: 12.1–12.6_

- [x] 5. Viết `backend/database.py` — Async SQLAlchemy engine
  - `create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)`
  - `AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)`
  - Async generator `get_session()`: `async with AsyncSessionLocal() as session: try: yield session; await session.commit() except: await session.rollback(); raise finally: await session.close()`
  - _Requirements: 3.1–3.6_

- [x] 6. Setup Alembic migrations
  - [x] 6.1 Khởi tạo Alembic trong `backend/migrations/`
    - `alembic.ini`: `script_location = migrations`, database URL để trống (defer to env.py)
    - `migrations/env.py`: import `Base` từ tất cả models, đọc `DATABASE_URL` từ `settings`, chạy async mode với `asyncio.run` và `AsyncEngine`
    - _Requirements: 13.1–13.4, 13.8_
  - [ ] 6.2 Tạo initial migration `versions/001_initial.py`
    - `upgrade()`: tạo 5 tables theo thứ tự dependency: `users` → `conversations` → `messages` → `nas_files` → `nas_folders`
    - `downgrade()`: drop theo thứ tự ngược lại
    - _Requirements: 13.5–13.7_

- [x] 7. Viết Middleware Stack
  - [x] 7.1 `backend/middleware/correlation.py`
    - Starlette `BaseHTTPMiddleware`
    - Check `X-Correlation-ID` header: dùng nếu có, uuid4() nếu không
    - `request.state.correlation_id = cid`
    - Gọi `logger.set_correlation_id(cid)` (context var)
    - Add header `X-Correlation-ID` vào response
    - _Requirements: 5.1–5.7_
  - [x] 7.2 `backend/middleware/logging.py`
    - Log INFO khi request đến: method, path, correlation_id, client_ip
    - Log INFO khi response ra: method, path, status_code, correlation_id, elapsed_ms
    - Skip paths bắt đầu bằng `/health`
    - KHÔNG log request/response body
    - Log ERROR nếu exception propagates
    - _Requirements: 6.1–6.6_
  - [x] 7.3 `backend/middleware/rate_limit.py`
    - Chỉ áp dụng cho paths bắt đầu `/mcp`
    - Redis sorted set sliding window: key = `f"mcp_rate:{token_or_anon}"`
    - Trả 429 với `{"detail": "Rate limit exceeded. Try again in {ttl} seconds."}` khi vượt limit
    - Allow-through + WARNING nếu Redis unreachable
    - _Requirements: 7.1–7.7_

- [x] 8. Viết Dependencies
  - [x] 8.1 `backend/dependencies/auth.py`
    - `get_current_user`: extract Bearer token, gọi `auth_service.verify_token()`, return `UserResponse` từ JWT claims (NO DB query)
    - `require_admin`: gọi `get_current_user`, check `role == "admin"`, raise 403 nếu không
    - _Requirements: 8.1–8.6_
  - [x] 8.2 `backend/dependencies/services.py`
    - `get_lightrag_query_client()`, `get_lightrag_ingest_client()`, `get_graphiti_client()`
    - Mỗi function trả instance của client tương ứng (từ `backend/integrations/`)
    - _Requirements: 9.1–9.6_

- [x] 9. Viết Integration Stubs
  - `backend/integrations/lightrag/ingest.py` — stub `async def ingest(...): raise NotImplementedError`
  - `backend/integrations/lightrag/query.py` — stub `async def query(...): raise NotImplementedError`
  - `backend/integrations/lightrag/graph.py` — stub `async def get_entity(...): raise NotImplementedError`
  - `backend/integrations/graphiti.py` — stub `async def extract(...): raise NotImplementedError`
  - `backend/mcp/server.py` — stub FastMCP instance: `mcp = FastMCP("SecondBrain")`
  - _Requirements: 9 (DI targets cần exist để import)_

- [x] 10. Viết Auth Schemas, Service, Router
  - [x] 10.1 `backend/schemas/auth.py`
    - `LoginRequest`: `email: str`, `password: str`
    - `RegisterRequest`: `username: str`, `email: str` (EmailStr), `password: str` (min_length=8)
    - `UserResponse`: `id: str`, `username: str`, `email: str`, `role: str`, `created_at: datetime`, `model_config = ConfigDict(from_attributes=True)`
    - `TokenResponse`: `access_token: str`, `token_type: str = "bearer"`, `user: UserResponse`
    - Dùng `X | None` syntax, KHÔNG `Optional[X]`
    - _Requirements: 14.1–14.9_
  - [x] 10.2 `backend/services/auth_service.py`
    - `create_access_token(data: dict, expires_delta: timedelta | None = None) -> str`
    - `verify_token(token: str) -> dict` — raise HTTPException 401 nếu expired/invalid
    - `hash_password(plain: str) -> str`
    - `verify_password(plain: str, hashed: str) -> bool`
    - KHÔNG import httpx, fastapi models, hay ORM — pure business logic
    - _Requirements: 15.1–15.8_
  - [x] 10.3 `backend/routers/auth.py`
    - `POST /register`: RegisterRequest → check dup email (409) → hash pw → INSERT User → trả TokenResponse 201
    - `POST /login`: LoginRequest → fetch user → verify pw → trả TokenResponse 200, cùng error message cho wrong email / wrong pw (401)
    - `GET /me`: `Depends(get_current_user)` → return UserResponse 200
    - Gọi `auth_service` cho JWT/bcrypt, `Depends(get_session)` cho DB — KHÔNG inline business logic
    - Token chứa claims: `sub`, `email`, `role`
    - _Requirements: 16.1–16.9_

- [x] 11. Viết `backend/main.py` — FastAPI Application Entry Point
  - Import và tạo `FastAPI(lifespan=lifespan)` với lifespan context manager
  - Mount middleware theo thứ tự: `add_middleware(CorrelationMiddleware)` sau cùng để chạy đầu tiên
  - Include auth router: `app.include_router(auth_router, prefix="/api/auth", tags=["auth"])`
  - Mount MCP stub: `app.mount("/mcp", mcp.http_app())`
  - Add CORS middleware với `settings.CORS_ORIGINS`
  - `GET /health` → `{"status": "ok"}` không cần auth
  - Startup log: `logger.info("SecondBrain backend started", port=8000)`
  - _Requirements: 1.1–1.9_

- [x] 12. Viết Unit Tests
  - [x] 12.1 `tests/conftest.py` — Shared fixtures
    - `fake_user` fixture: dict với `id`, `email`, `role="user"`, `username`
    - `fake_admin` fixture: dict với `role="admin"`
    - `client` fixture: `TestClient` với `get_current_user` → `fake_user`, cleanup sau test
    - `admin_client` fixture: `TestClient` với `get_current_user` → `fake_admin`
    - `mock_lightrag_query` fixture: monkeypatch `integrations.lightrag.query.query` với `AsyncMock`
    - `mock_graphiti` fixture: monkeypatch `integrations.graphiti.extract` với `AsyncMock`
    - _Requirements: 19.1–19.8_
  - [x] 12.2 `tests/unit/backend/test_schemas.py`
    - Test `RegisterRequest`: password < 8 chars → ValidationError
    - Test `RegisterRequest`: invalid email format → ValidationError
    - Test `LoginRequest`: empty email/password → ValidationError
    - Test `UserResponse.from_attributes` với mock object
    - _Requirements: 17.1–17.5_
  - [x] 12.3 `tests/unit/backend/test_auth_service.py`
    - Test `hash_password` / `verify_password` round-trip → True
    - Test `verify_password` với wrong password → False
    - Test `create_access_token` / `verify_token` round-trip → claims intact
    - Test `verify_token` với expired token → HTTPException 401
    - Test `verify_token` với malformed string → HTTPException 401
    - _Requirements: 17.6–17.12_
  - [x] 12.4 `tests/unit/backend/test_middleware.py`
    - Test response luôn có `X-Correlation-ID` header
    - Test custom ID được echo lại trong response
    - Test request không có ID → response có UUID v4 mới
    - Test 2 requests liên tiếp không có ID → nhận 2 ID khác nhau
    - Test `GET /health` → 200 + `X-Correlation-ID`
    - _Requirements: 18.1–18.7_

- [ ] 13. Checkpoint — Verify toàn bộ unit tests
  - Chạy `pytest tests/unit/backend/ -v` — tất cả tests phải pass
  - Chạy `alembic upgrade head` với PostgreSQL đang chạy — migration không lỗi
  - Kiểm tra 5 tables tồn tại: `users`, `conversations`, `messages`, `nas_files`, `nas_folders`
  - Chạy `alembic downgrade -1` — drop thành công
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Kiểm tra E2E Auth Flow (cần stack đang chạy)
  - Start backend: `uvicorn backend.main:app --reload`
  - `POST /api/auth/register` với `username`, `email`, `password` hợp lệ → HTTP 201 + `access_token`
  - `POST /api/auth/login` với credentials đã đăng ký → HTTP 200 + `access_token`
  - `GET /api/auth/me` với Bearer token từ bước trên → HTTP 200 + `UserResponse` đúng
  - `POST /api/auth/register` lần 2 với cùng email → HTTP 409
  - `GET /api/auth/me` không có token → HTTP 401
  - Kiểm tra Seq (port 80) có log entries với `correlation_id` field
  - Kiểm tra response header `X-Correlation-ID` xuất hiện trong mọi response
  - _Requirements: 20.1–20.7_

---

## Task Dependency Graph

- Tasks 2, 3, 4, 5 có thể làm song song — config, logger, models, database không phụ thuộc nhau
- Task 6 (Alembic) phụ thuộc Task 4 (models)
- Task 7 (middleware) phụ thuộc Task 3 (logger)
- Task 8 (dependencies) phụ thuộc Task 9 (integration stubs) để có thể import
- Task 9 (integration stubs) có thể làm song song với Tasks 2–7
- Task 10 (auth) phụ thuộc Tasks 4, 5, 8
- Task 11 (main.py) phụ thuộc tất cả Tasks 2–10
- Task 12 (unit tests) có thể viết song song với từng module
- Task 13 (checkpoint) phụ thuộc Tasks 11, 12
- Task 14 (E2E) phụ thuộc Task 13 và stack đang chạy

## Notes

- Tasks 2–5 có thể làm song song — config, logger, models, database không phụ thuộc nhau
- Task 6 (Alembic) cần Task 4 (models) hoàn thành trước
- Task 7 (middleware) cần Task 3 (logger) hoàn thành trước
- Task 10 (auth) cần Tasks 4, 5, 8 hoàn thành trước
- Task 11 (main.py) là tổng hợp — làm sau tất cả tasks khác
- Task 12 (tests) nên viết song song với từng module (test-driven nếu muốn)
- Integration stubs (Task 9) cần tồn tại trước Task 8 để `services.py` có thể import
- `SECRET_KEY` trong `.env` phải là random string >= 32 chars khi test E2E
- Spec 3 (NAS Connector) và Spec 4 (LightRAG Integration) sẽ implement các integration stubs đã tạo ở đây
