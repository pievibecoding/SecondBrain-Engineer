# Requirements Document

## Introduction

Spec này xây dựng toàn bộ nền tảng backend cho dự án SecondBrain của Robolinks.
Backend là **orchestrator trung tâm** viết bằng Python FastAPI, chịu trách nhiệm:
auth (JWT + bcrypt), quản lý DB qua SQLAlchemy async, structured logging vào Seq với
`correlation_id`, middleware tự động inject `X-Correlation-ID` và log mọi request,
rate limiting cho `/mcp` endpoints, dependency injection cho auth và integration clients,
ORM models cho tất cả bảng DB, Alembic migrations, Pydantic schemas cho auth,
service layer cho JWT/bcrypt, và Auth router.

**Dependency:** Spec 1 (Infrastructure Setup) phải hoàn thành trước — PostgreSQL,
Redis, Seq phải đang chạy.

**Definition of Done:**
- `pytest tests/unit/backend/ -v` passes
- Alembic migration chạy không lỗi
- POST `/api/auth/register` → trả JWT token
- POST `/api/auth/login` → trả JWT token
- GET `/api/auth/me` với valid token → trả user info
- `X-Correlation-ID` xuất hiện trong response headers và Seq logs

---

## Glossary

- **Backend**: FastAPI application tại `backend/`, port 8000 — orchestrator chính của SecondBrain
- **Correlation_ID**: UUID v4 được tạo cho mỗi HTTP request, dùng để trace log xuyên suốt multi-service
- **JWT**: JSON Web Token — access token có expiry, dùng cho auth stateless
- **Bcrypt**: Thuật toán hash password một chiều — không thể reverse
- **DeclarativeBase**: SQLAlchemy base class cho tất cả ORM models
- **AsyncSession**: SQLAlchemy async database session — bắt buộc dùng `await`
- **Pydantic Settings**: `pydantic-settings` BaseSettings class đọc config từ env vars và `.env`
- **Alembic**: Migration tool cho SQLAlchemy — quản lý schema DB theo version
- **FastAPI Depends**: Dependency injection mechanism của FastAPI
- **ASGI Middleware**: Middleware layer xử lý request/response trước khi vào router
- **Seq**: Centralized structured logging server (port 80), nhận log JSON qua HTTP
- **MCP**: Model Context Protocol — endpoint `/mcp` mount FastMCP ASGI app
- **NasFile**: ORM model track file từ Synology NAS (path, status, hash, lightrag_doc_id)
- **NasFolder**: ORM model lưu config folder NAS cần watch (path, folder_type, is_active)
- **graphiti_synced**: Flag trong Message model — `true` khi turn đã được Graphiti extract
- **role**: User role — `"user"` (mặc định) hoặc `"admin"` (có quyền approve NAS files)


---

## Requirements

### Requirement 1: FastAPI Application Entry Point

**User Story:** As a Robolinks engineer, I want a FastAPI application entry point that mounts all routers, MCP server, and middleware, so that the backend starts up correctly and all endpoints are accessible.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 4 (Cấu trúc thư mục — `backend/main.py`), Section 11b (MCP Server — mount `/mcp`)

#### Acceptance Criteria

1. THE `Backend` SHALL define a FastAPI application instance in `backend/main.py`.
2. THE `Backend` SHALL mount the `CorrelationMiddleware` before all other middleware so that `X-Correlation-ID` is available to downstream handlers.
3. THE `Backend` SHALL mount the `LoggingMiddleware` to log every request and response automatically.
4. THE `Backend` SHALL mount the `RateLimitMiddleware` to enforce rate limiting on `/mcp` endpoints.
5. THE `Backend` SHALL include the auth router at prefix `/api/auth`.
6. THE `Backend` SHALL mount the FastMCP ASGI application at path `/mcp`.
7. WHEN the FastAPI application starts, THE `Backend` SHALL log a startup message containing the application name and listening port to Seq.
8. THE `Backend` SHALL expose a `GET /health` endpoint that returns `{"status": "ok"}` with HTTP 200, requiring no authentication.
9. THE `Backend` SHALL use `lifespan` context manager (not deprecated `on_event`) for startup and shutdown hooks.


---

### Requirement 2: Configuration Management

**User Story:** As a developer, I want all environment variables loaded via Pydantic Settings, so that the backend can be configured for different environments without code changes.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 6.1 (Services và ports), Section 6.2 (env vars pattern)

#### Acceptance Criteria

1. THE `Config` SHALL define a `Settings` class in `backend/config.py` using `pydantic-settings` `BaseSettings`.
2. THE `Config` SHALL read configuration from environment variables and a `.env` file, with environment variables taking precedence.
3. THE `Config` SHALL expose the following required settings: `DATABASE_URL` (PostgreSQL async URL), `REDIS_URL`, `SECRET_KEY` (JWT signing key), `ALGORITHM` (JWT algorithm, default `"HS256"`), `ACCESS_TOKEN_EXPIRE_MINUTES` (default `60`).
4. THE `Config` SHALL expose service URLs: `LIGHTRAG_URL` (default `"http://lightrag:9621"`), `GRAPHITI_URL` (default `"http://graphiti-service:9622"`), `SEQ_URL` (default `"http://seq:5341"`).
5. THE `Config` SHALL expose `CORS_ORIGINS` as a list of allowed origins (default `["http://localhost:3000"]`).
6. THE `Config` SHALL expose `MCP_RATE_LIMIT_PER_MINUTE` (default `100`) for `/mcp` endpoint rate limiting.
7. THE `Config` SHALL provide a single `settings` singleton instance importable as `from backend.config import settings`.
8. WHEN a required setting is missing from the environment, THE `Config` SHALL raise a `ValidationError` at application startup with a descriptive message identifying the missing field.


---

### Requirement 3: Async Database Engine và Session

**User Story:** As a developer, I want an async SQLAlchemy engine and session factory, so that all database operations are non-blocking and compatible with FastAPI's async handlers.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 7.1 (SecondBrain backend DB schema), Section 4 (`backend/database.py`)

#### Acceptance Criteria

1. THE `Database` SHALL create an async SQLAlchemy engine in `backend/database.py` using `create_async_engine` with the `DATABASE_URL` from settings.
2. THE `Database` SHALL create an `AsyncSessionLocal` factory using `async_sessionmaker` with `expire_on_commit=False`.
3. THE `Database` SHALL provide an async generator `get_session` that yields an `AsyncSession` and commits on success or rolls back on exception, then closes the session.
4. THE `get_session` generator SHALL be usable as a FastAPI `Depends` parameter in router functions.
5. THE `Database` SHALL configure the engine with a connection pool suitable for async use (`pool_pre_ping=True` to detect stale connections).
6. WHEN a database connection error occurs during session acquisition, THE `Database` SHALL raise the exception so FastAPI returns HTTP 503 to the caller.


---

### Requirement 4: Structured Logger với Correlation ID

**User Story:** As a Robolinks engineer, I want all backend logs shipped to Seq as structured JSON with a `correlation_id` field, so that I can trace any request across all services by filtering on one ID.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 4 (`backend/logger.py`), Section 10.1 (Centralized logging với Seq — correlation_id strategy)

#### Acceptance Criteria

1. THE `Logger` SHALL be configured in `backend/logger.py` to output structured JSON logs.
2. THE `Logger` SHALL ship logs to Seq at `SEQ_URL` from settings using HTTP ingestion (port 5341).
3. THE `Logger` SHALL include `correlation_id` as a top-level field in every log entry when a correlation ID is available in the current context.
4. THE `Logger` SHALL include `service` field with value `"backend"` in every log entry.
5. THE `Logger` SHALL support log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`.
6. THE `Logger` SHALL expose a module-level `logger` instance importable as `from backend.logger import logger`.
7. WHEN called with extra keyword arguments, THE `Logger` SHALL include those fields in the structured log output (e.g., `logger.info("msg", nas_path=path, correlation_id=cid)`).
8. WHEN `SEQ_URL` is unreachable, THE `Logger` SHALL fall back to stdout logging and NOT raise an exception that would crash the application.


---

### Requirement 5: Correlation ID Middleware

**User Story:** As a Robolinks engineer, I want every HTTP request to automatically receive a `X-Correlation-ID` header, so that I can trace the full lifecycle of any request through backend logs and downstream service logs in Seq.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 4 (`backend/middleware/correlation.py`), Section 6 (Correlation ID cho debug — mọi request tạo UUID correlation_id)

#### Acceptance Criteria

1. THE `CorrelationMiddleware` SHALL be implemented as an ASGI Starlette middleware in `backend/middleware/correlation.py`.
2. WHEN an incoming request contains an `X-Correlation-ID` header with a non-empty value, THE `CorrelationMiddleware` SHALL use that value as the correlation ID for the request.
3. WHEN an incoming request does NOT contain an `X-Correlation-ID` header, THE `CorrelationMiddleware` SHALL generate a new UUID v4 as the correlation ID.
4. THE `CorrelationMiddleware` SHALL attach the correlation ID to the request state as `request.state.correlation_id`.
5. THE `CorrelationMiddleware` SHALL include the `X-Correlation-ID` header in the HTTP response with the same correlation ID value.
6. THE `CorrelationMiddleware` SHALL make the correlation ID available via a context variable so that the Logger can include it in log entries without explicit passing.
7. WHEN unit-tested with FastAPI `TestClient`, THE `CorrelationMiddleware` SHALL produce a response containing `X-Correlation-ID` header for every request regardless of endpoint.


---

### Requirement 6: Request/Response Logging Middleware

**User Story:** As a developer, I want every HTTP request and response automatically logged to Seq, so that I can audit traffic and diagnose issues without adding log calls to every router.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 4 (`backend/middleware/logging.py`), Section 10.1 (debug multi-service với Seq)

#### Acceptance Criteria

1. THE `LoggingMiddleware` SHALL be implemented as an ASGI middleware in `backend/middleware/logging.py`.
2. WHEN a request arrives, THE `LoggingMiddleware` SHALL log at INFO level: HTTP method, URL path, `correlation_id`, and client IP.
3. WHEN a response is sent, THE `LoggingMiddleware` SHALL log at INFO level: HTTP method, URL path, response status code, `correlation_id`, and elapsed time in milliseconds.
4. WHEN a request to any path under `/health` is received, THE `LoggingMiddleware` SHALL skip logging to avoid polluting logs with health check noise.
5. THE `LoggingMiddleware` SHALL NOT log request or response body content (to avoid logging sensitive data such as passwords).
6. WHEN an unhandled exception propagates through the middleware, THE `LoggingMiddleware` SHALL log at ERROR level with the exception message and `correlation_id` before re-raising the exception.


---

### Requirement 7: Rate Limiting Middleware cho /mcp Endpoints

**User Story:** As a system administrator, I want rate limiting applied to `/mcp` endpoints, so that external MCP clients cannot overload the backend or LightRAG with excessive requests.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 4 (`backend/middleware/rate_limit.py`), Section 11b (Bảo mật MCP — 100 req/min/token)

#### Acceptance Criteria

1. THE `RateLimitMiddleware` SHALL be implemented in `backend/middleware/rate_limit.py`.
2. THE `RateLimitMiddleware` SHALL apply rate limiting ONLY to requests whose path starts with `/mcp`.
3. THE `RateLimitMiddleware` SHALL enforce a limit of `MCP_RATE_LIMIT_PER_MINUTE` requests per minute per Bearer token value.
4. WHEN a request to `/mcp` carries no `Authorization` header, THE `RateLimitMiddleware` SHALL count against a shared anonymous bucket with the same limit.
5. WHEN the rate limit is exceeded, THE `RateLimitMiddleware` SHALL return HTTP 429 with JSON body `{"detail": "Rate limit exceeded. Try again in {seconds} seconds."}`.
6. THE `RateLimitMiddleware` SHALL use Redis (via `settings.REDIS_URL`) to store request counts with a sliding window of 60 seconds.
7. WHEN Redis is unreachable, THE `RateLimitMiddleware` SHALL allow the request through and log a WARNING — rate limiting SHALL NOT block legitimate traffic due to Redis failure.


---

### Requirement 8: Auth Dependencies (get_current_user, require_admin)

**User Story:** As a developer, I want reusable FastAPI Depends functions for authentication and authorization, so that any router can protect its endpoints with a single line of code.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 4 (`backend/dependencies/auth.py`), Section 8.1 (API contracts — protected endpoints)

#### Acceptance Criteria

1. THE `AuthDependencies` SHALL implement `get_current_user` as an async FastAPI dependency in `backend/dependencies/auth.py`.
2. WHEN a request includes a valid Bearer JWT in the `Authorization` header, THE `get_current_user` dependency SHALL decode the token and return a `UserResponse` object containing the user's id, email, and role.
3. WHEN a request is missing the `Authorization` header or the token is invalid/expired, THE `get_current_user` dependency SHALL raise `HTTPException` with status 401 and detail `"Could not validate credentials"`.
4. THE `AuthDependencies` SHALL implement `require_admin` as an async FastAPI dependency that calls `get_current_user` and additionally checks that `role == "admin"`.
5. WHEN the authenticated user's role is NOT `"admin"`, THE `require_admin` dependency SHALL raise `HTTPException` with status 403 and detail `"Admin access required"`.
6. THE `get_current_user` dependency SHALL NOT query the database on every call — it SHALL rely solely on JWT claims to avoid unnecessary DB round-trips per request.


---

### Requirement 9: Service Injection Dependencies

**User Story:** As a developer, I want integration clients injected via FastAPI Depends, so that routers never import integration modules directly and tests can swap real clients for mocks easily.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 4 (`backend/dependencies/services.py`), Section 3 (Key Decisions — `integrations/` external HTTP clients only)

#### Acceptance Criteria

1. THE `ServiceDependencies` SHALL be implemented in `backend/dependencies/services.py`.
2. THE `ServiceDependencies` SHALL provide a dependency `get_lightrag_query_client` that returns the LightRAG query integration client.
3. THE `ServiceDependencies` SHALL provide a dependency `get_lightrag_ingest_client` that returns the LightRAG ingest integration client.
4. THE `ServiceDependencies` SHALL provide a dependency `get_graphiti_client` that returns the Graphiti integration client.
5. WHEN tests override these dependencies via `app.dependency_overrides`, THE `Backend` SHALL use the mock client instead of the real implementation — no conditional logic needed in routers.
6. THE `ServiceDependencies` SHALL NOT instantiate `httpx.AsyncClient` at module import time — clients SHALL be created per-request or per-lifespan to avoid event loop issues.


---

### Requirement 10: ORM Models: Base và User

**User Story:** As a developer, I want SQLAlchemy ORM models for the User table, so that the authentication system has a persistent data store following the project's `models/` conventions.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 7.1 (`users` table DDL), Section 3 (Key Decisions — `models/` = SQLAlchemy ORM only)

#### Acceptance Criteria

1. THE `Base` model SHALL define a `DeclarativeBase` subclass in `backend/models/base.py` that all other ORM models inherit from.
2. THE `User` model SHALL be defined in `backend/models/user.py` and inherit from `Base`.
3. THE `User` model SHALL map to table `users` with columns: `id` (UUID primary key, server default `gen_random_uuid()`), `username` (TEXT, unique, not null), `email` (TEXT, unique, not null), `password_hash` (TEXT, not null), `role` (TEXT, not null, default `"user"`), `created_at` (TIMESTAMPTZ, server default `now()`).
4. THE `User` model SHALL NOT contain any Pydantic code — it is a pure SQLAlchemy ORM model.
5. THE `User` model SHALL NOT store plaintext passwords — `password_hash` SHALL only be populated by `auth_service.hash_password()`.
6. THE `User.role` field SHALL accept only the values `"user"` or `"admin"` — a check constraint or application-level validation SHALL enforce this.


---

### Requirement 11: ORM Models: Conversation và Message

**User Story:** As a developer, I want SQLAlchemy ORM models for Conversation and Message tables, so that chat history is persisted and the `graphiti_synced` flag tracks which turns have been sent to Graphiti.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 7.1 (`conversations` và `messages` table DDL), Section 5.2 (Chat workflow — `graphiti_synced` flag)

#### Acceptance Criteria

1. THE `Conversation` model SHALL be defined in `backend/models/conversation.py` and inherit from `Base`.
2. THE `Conversation` model SHALL map to table `conversations` with columns: `id` (UUID PK), `user_id` (UUID FK → `users.id`), `title` (TEXT, nullable — auto-generated from first turn), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
3. THE `Message` model SHALL be defined in the same file `backend/models/conversation.py` and inherit from `Base`.
4. THE `Message` model SHALL map to table `messages` with columns: `id` (UUID PK), `conversation_id` (UUID FK → `conversations.id`), `role` (TEXT, not null — `"user"` or `"assistant"`), `content` (TEXT, not null), `citations` (JSONB, nullable), `graphiti_synced` (BOOLEAN, default `false`), `created_at` (TIMESTAMPTZ).
5. THE `Message.citations` JSONB field SHALL store citation objects matching the structure: `[{"type": "document"|"graph_entity", "file": "...", "page": int}]`.
6. THE `Conversation` model SHALL define a `messages` relationship to `Message` with `lazy="selectin"` for async compatibility.


---

### Requirement 12: ORM Models: NasFile và NasFolder

**User Story:** As a developer, I want SQLAlchemy ORM models for NasFile and NasFolder, so that the backend has a single source of truth for NAS file tracking and folder configuration.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 7.1 (`nas_files` và `nas_folders` table DDL), Section 3 (Key Decisions — nas-connector KHÔNG lưu SQLite, single source of truth là backend PostgreSQL)

#### Acceptance Criteria

1. THE `NasFile` model SHALL be defined in `backend/models/nas_file.py` and inherit from `Base`.
2. THE `NasFile` model SHALL map to table `nas_files` with columns: `id` (UUID PK), `nas_path` (TEXT, not null — đường dẫn gốc trên NAS), `folder_type` (TEXT, not null — `"auto"` hoặc `"manual"`), `status` (TEXT, not null, default `"pending"`), `file_hash` (TEXT, nullable), `lightrag_doc_id` (TEXT, nullable), `approved_by` (UUID FK → `users.id`, nullable), `approved_at` (TIMESTAMPTZ, nullable), `reject_reason` (TEXT, nullable), `indexed_at` (TIMESTAMPTZ, nullable), `error_msg` (TEXT, nullable), `created_at` (TIMESTAMPTZ, default `now()`).
3. THE `NasFile.status` field SHALL support the state machine values: `"pending"`, `"queued"`, `"indexing"`, `"indexed"`, `"failed"`, `"pending_review"`, `"rejected"`.
4. THE `NasFolder` model SHALL be defined in `backend/models/nas_folder.py` and inherit from `Base`.
5. THE `NasFolder` model SHALL map to table `nas_folders` with columns: `id` (UUID PK), `path` (TEXT, unique, not null), `folder_type` (TEXT, not null — `"auto"` hoặc `"manual"`), `is_active` (BOOLEAN, default `true`), `last_scanned` (TIMESTAMPTZ, nullable), `created_at` (TIMESTAMPTZ, default `now()`).
6. THE `NasFile` model SHALL NOT contain any Pydantic code — it is a pure SQLAlchemy ORM model.


---

### Requirement 13: Alembic Migrations

**User Story:** As a developer, I want Alembic migrations set up inside `backend/migrations/`, so that the database schema is version-controlled and can be applied or rolled back reliably.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `task-breakdown`
- **Reference:** pa3-design Section 4 (`backend/migrations/` — Alembic setup + initial migration), Section 7.1 (tất cả table DDL)

#### Acceptance Criteria

1. THE `Migrations` SHALL be configured in `backend/migrations/` with files: `env.py`, `alembic.ini`, and `versions/` directory.
2. THE `Migrations` `env.py` SHALL import `Base` from `backend/models/base.py` so that Alembic auto-generates migrations from ORM models.
3. THE `Migrations` `env.py` SHALL read `DATABASE_URL` from `backend/config.py` settings — NOT from a hardcoded string.
4. THE `Migrations` `env.py` SHALL run in async mode using `asyncio.run` and `AsyncEngine` to be compatible with the async SQLAlchemy setup.
5. THE initial migration in `versions/` SHALL create all four tables: `users`, `conversations`, `messages`, `nas_files`, `nas_folders`.
6. WHEN `alembic upgrade head` is run against a fresh PostgreSQL instance, THE `Migrations` SHALL complete without errors and all five tables SHALL exist.
7. WHEN `alembic downgrade -1` is run, THE `Migrations` SHALL drop the tables created by the initial migration without errors.
8. THE `alembic.ini` SHALL NOT contain the database URL in plaintext — it SHALL defer to `env.py` which reads from settings.


---

### Requirement 14: Auth Pydantic Schemas

**User Story:** As a developer, I want Pydantic V2 schemas for authentication request/response, so that API inputs are validated and outputs are consistently shaped across all auth endpoints.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8.1 (API contracts — `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`), Section 3 (Key Decisions — `schemas/` = Pydantic only)

#### Acceptance Criteria

1. THE `AuthSchemas` SHALL define all auth schemas in `backend/schemas/auth.py` using Pydantic V2 `BaseModel`.
2. THE `AuthSchemas` SHALL define `LoginRequest` with fields: `email` (str, required) and `password` (str, required).
3. THE `AuthSchemas` SHALL define `RegisterRequest` with fields: `username` (str, required), `email` (str, required, must be valid email format), `password` (str, required, minimum 8 characters).
4. THE `AuthSchemas` SHALL define `TokenResponse` with fields: `access_token` (str), `token_type` (str, default `"bearer"`), `user` (`UserResponse`).
5. THE `AuthSchemas` SHALL define `UserResponse` with fields: `id` (str), `username` (str), `email` (str), `role` (str), `created_at` (datetime).
6. THE `UserResponse` SHALL have `model_config = ConfigDict(from_attributes=True)` so it can be constructed from a SQLAlchemy `User` ORM instance.
7. THE `RegisterRequest.password` SHALL be validated to have a minimum length of 8 characters — WHEN the password is shorter, THE schema SHALL raise a `ValidationError` with a descriptive message.
8. THE `AuthSchemas` SHALL use `X | None` union syntax (Pydantic V2 style), NOT `Optional[X]`.
9. THE `AuthSchemas` SHALL NOT contain any SQLAlchemy code.


---

### Requirement 15: Auth Service (JWT + Bcrypt)

**User Story:** As a developer, I want a pure business-logic service for JWT token management and bcrypt password hashing, so that auth logic is centralized, tested independently, and never mixed with HTTP concerns.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 4 (`backend/services/auth_service.py`), Section 8.1 (auth endpoints), Section 15 (Unit tests — `test_auth_service.py`)

#### Acceptance Criteria

1. THE `AuthService` SHALL implement all auth logic in `backend/services/auth_service.py`.
2. THE `AuthService` SHALL provide `create_access_token(data: dict, expires_delta: timedelta | None) -> str` that encodes a JWT with `exp` claim using `SECRET_KEY` and `ALGORITHM` from settings.
3. THE `AuthService` SHALL provide `verify_token(token: str) -> dict` that decodes a JWT and returns the claims dict — WHEN the token is expired or invalid, THE function SHALL raise `HTTPException` with status 401.
4. THE `AuthService` SHALL provide `hash_password(plain: str) -> str` that returns a bcrypt hash of the plain password.
5. THE `AuthService` SHALL provide `verify_password(plain: str, hashed: str) -> bool` that returns `True` if the plain password matches the bcrypt hash, `False` otherwise.
6. THE `AuthService` SHALL use the `python-jose` library for JWT and `passlib[bcrypt]` for password hashing.
7. THE `AuthService` SHALL NOT import `httpx`, `fastapi`, or any ORM module — it is pure business logic with no external dependencies beyond `python-jose` and `passlib`.
8. WHEN `create_access_token` is called without `expires_delta`, THE `AuthService` SHALL use `ACCESS_TOKEN_EXPIRE_MINUTES` from settings as the default expiry.


---

### Requirement 16: Auth Router

**User Story:** As a Robolinks engineer, I want POST /api/auth/register, POST /api/auth/login, and GET /api/auth/me endpoints, so that users can create accounts, log in to receive JWT tokens, and retrieve their profile.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8.1 (API contracts — `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me`), Section 4 (`backend/routers/auth.py`)

#### Acceptance Criteria

1. THE `AuthRouter` SHALL be implemented in `backend/routers/auth.py` as a FastAPI `APIRouter` with prefix `""` (prefix applied at mount in `main.py`).
2. THE `AuthRouter` SHALL implement `POST /register` that: accepts `RegisterRequest`, checks for duplicate email in DB, hashes the password via `auth_service.hash_password`, creates a `User` record, and returns `TokenResponse` with HTTP 201.
3. WHEN `POST /register` is called with an already-existing email, THE `AuthRouter` SHALL return HTTP 409 with detail `"Email already registered"`.
4. THE `AuthRouter` SHALL implement `POST /login` that: accepts `LoginRequest`, fetches the user by email from DB, verifies password via `auth_service.verify_password`, and returns `TokenResponse` with HTTP 200.
5. WHEN `POST /login` is called with a non-existent email or wrong password, THE `AuthRouter` SHALL return HTTP 401 with detail `"Invalid email or password"` — the same message for both cases to prevent user enumeration.
6. THE `AuthRouter` SHALL implement `GET /me` that: requires `get_current_user` dependency and returns `UserResponse` for the authenticated user with HTTP 200.
7. THE `AuthRouter` SHALL be a thin layer — it SHALL call `auth_service` for JWT/bcrypt operations and SHALL NOT implement business logic inline.
8. THE `AuthRouter` SHALL use `Depends(get_session)` for database access and SHALL NOT call `get_session()` directly.
9. THE `TokenResponse.access_token` returned by `/register` and `/login` SHALL be decodable by `auth_service.verify_token` and SHALL contain `sub` (user id), `email`, and `role` claims.


---

### Requirement 17: Unit Tests: Schemas và Auth Service

**User Story:** As a developer, I want unit tests for Pydantic schemas and auth_service that run without Docker, so that I get fast feedback on business logic correctness during development.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Tầng 1 — Unit tests, `test_schemas.py`, `test_auth_service.py`), Section 15 (Coverage target — `schemas/` 95%+, `services/` 80%+)

#### Acceptance Criteria

1. THE `SchemaTests` SHALL be implemented in `tests/unit/backend/test_schemas.py` using `pytest`.
2. THE `SchemaTests` SHALL verify that `RegisterRequest` raises `ValidationError` when `password` is fewer than 8 characters.
3. THE `SchemaTests` SHALL verify that `RegisterRequest` raises `ValidationError` when `email` is not a valid email format.
4. THE `SchemaTests` SHALL verify that `LoginRequest` raises `ValidationError` when `email` or `password` is empty.
5. THE `SchemaTests` SHALL verify that `UserResponse` can be constructed `from_attributes=True` from a mock object with matching fields.
6. THE `AuthServiceTests` SHALL be implemented in `tests/unit/backend/test_auth_service.py` using `pytest`.
7. THE `AuthServiceTests` SHALL verify that `hash_password` returns a string different from the input and that `verify_password(plain, hash_password(plain))` returns `True` (round-trip property).
8. THE `AuthServiceTests` SHALL verify that `verify_password` returns `False` when called with a wrong plain password.
9. THE `AuthServiceTests` SHALL verify that a token created by `create_access_token` can be decoded by `verify_token` and contains the original claims (round-trip property).
10. THE `AuthServiceTests` SHALL verify that `verify_token` raises `HTTPException` with status 401 when called with an expired token.
11. THE `AuthServiceTests` SHALL verify that `verify_token` raises `HTTPException` with status 401 when called with a malformed token string.
12. ALL tests in `tests/unit/backend/` SHALL run with `pytest tests/unit/backend/ -v` without requiring Docker, PostgreSQL, or any running service.


---

### Requirement 18: Unit Tests: Middleware

**User Story:** As a developer, I want unit tests for the correlation ID middleware, so that I can verify the X-Correlation-ID header contract is always upheld without running a full Docker stack.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Tầng 1 — `test_middleware.py`), Section 6 (Correlation ID cho debug)

#### Acceptance Criteria

1. THE `MiddlewareTests` SHALL be implemented in `tests/unit/backend/test_middleware.py` using `pytest` and FastAPI `TestClient`.
2. THE `MiddlewareTests` SHALL verify that a response to any endpoint contains the `X-Correlation-ID` header.
3. THE `MiddlewareTests` SHALL verify that WHEN a request includes `X-Correlation-ID: custom-id-123`, the response echoes back `X-Correlation-ID: custom-id-123`.
4. THE `MiddlewareTests` SHALL verify that WHEN a request does NOT include `X-Correlation-ID`, the response contains a newly generated UUID v4 in the `X-Correlation-ID` header.
5. THE `MiddlewareTests` SHALL verify that two consecutive requests without `X-Correlation-ID` receive different correlation IDs in their responses.
6. THE `MiddlewareTests` SHALL verify that a request to `GET /health` receives HTTP 200 and a `X-Correlation-ID` header.
7. ALL middleware tests SHALL run without requiring PostgreSQL, Redis, or any external service.


---

### Requirement 19: Shared Test Fixtures (conftest.py)

**User Story:** As a developer, I want shared pytest fixtures in `tests/conftest.py`, so that all unit tests across backend, NAS connector, and Graphiti service modules can reuse common setup without duplicating code.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (conftest.py pattern), `test-conventions.md` (shared fixtures — `fake_user`, `fake_admin`, `client`, `mock_lightrag_query`, `mock_graphiti`)

#### Acceptance Criteria

1. THE `Conftest` SHALL be implemented in `tests/conftest.py`.
2. THE `Conftest` SHALL provide a `fake_user` fixture returning a dict `{"id": "test-user-id", "email": "test@robolinks.vn", "role": "user", "username": "testuser"}`.
3. THE `Conftest` SHALL provide a `fake_admin` fixture returning a dict `{"id": "admin-id", "email": "admin@robolinks.vn", "role": "admin", "username": "admin"}`.
4. THE `Conftest` SHALL provide a `client` fixture that creates a FastAPI `TestClient` with `get_current_user` dependency overridden to return `fake_user`, and clears `dependency_overrides` after the test.
5. THE `Conftest` SHALL provide an `admin_client` fixture that creates a FastAPI `TestClient` with `get_current_user` dependency overridden to return `fake_admin`.
6. THE `Conftest` SHALL provide a `mock_lightrag_query` fixture using `monkeypatch` that replaces `backend.integrations.lightrag.query.query` with an `AsyncMock` returning `{"response": "Motor Siemens 1LE1 7.5kW", "sources": [{"file": "BOM-Heineken-2024.xlsx"}]}`.
7. THE `Conftest` SHALL provide a `mock_graphiti` fixture using `monkeypatch` that replaces `backend.integrations.graphiti.extract` with an `AsyncMock` returning `{"ok": True}`.
8. WHEN tests use the `client` or `admin_client` fixture, THE `Conftest` SHALL ensure `dependency_overrides` is cleared after each test to prevent state leakage between tests.


---

### Requirement 20: End-to-End Auth Flow Verification

**User Story:** As a Robolinks engineer, I want the full auth flow (register → login → /me) to work correctly against a real database, so that I can verify the system functions end-to-end before integrating other specs.

### Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 8.1 (Auth API contracts), Section 9 (Tuần 1 — "Backend skeleton: FastAPI + auth + DB schema"), Section 15 (Definition of Done — auth endpoints)

#### Acceptance Criteria

1. WHEN `POST /api/auth/register` is called with valid `username`, `email`, and `password`, THE `AuthRouter` SHALL return HTTP 201 with a `TokenResponse` containing a non-empty `access_token` and a `user` object matching the registered data.
2. WHEN `POST /api/auth/login` is called with valid `email` and `password` of an existing user, THE `AuthRouter` SHALL return HTTP 200 with a `TokenResponse` containing a valid `access_token`.
3. WHEN `GET /api/auth/me` is called with the `Authorization: Bearer <token>` header from a successful login or register, THE `AuthRouter` SHALL return HTTP 200 with a `UserResponse` containing the correct `email`, `username`, and `role`.
4. WHEN `POST /api/auth/register` is called twice with the same email, THE `AuthRouter` SHALL return HTTP 409 on the second call.
5. WHEN `POST /api/auth/login` is called with a valid email but wrong password, THE `AuthRouter` SHALL return HTTP 401.
6. WHEN `GET /api/auth/me` is called without an `Authorization` header, THE `AuthRouter` SHALL return HTTP 401.
7. THE `access_token` returned by `/register` and `/login` SHALL both be accepted by `GET /api/auth/me` — verifying the round-trip: register → use token → get profile.

