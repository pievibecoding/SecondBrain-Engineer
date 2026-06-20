# Implementation Plan — Spec 7: MCP Server

## Overview

Implement MCP Server for SecondBrain: FastMCP instance mounted at `/mcp`, 4 public tools, 1 internal tool, Pydantic schemas, auth/rate-limit integration, and Claude Desktop documentation.

This spec wires existing Spec 4–6 integrations (LightRAG query/graph clients, WikiBuilder, NasFile DB) into MCP tool handlers. No new external services needed.

Unit tests mock LightRAG clients and DB. No Docker required for unit tests.

---

## Tasks

- [x] 1. Setup MCP package structure
  - Ensure folder `backend/mcp/` exists (stub created in Spec 2)
  - Create files:
    ```text
    backend/mcp/
    ├── __init__.py
    ├── server.py
    └── tools/
        ├── __init__.py
        ├── search.py
        ├── entity.py
        ├── documents.py
        └── internal/
            ├── __init__.py
            └── push.py
    ```
  - Add `fastmcp` to `backend/requirements.txt` with pinned version
  - _Requirements: 1.1, 1.5_

---

- [x] 2. Implement `backend/mcp/server.py` — FastMCP instance
  - Instantiate `mcp = FastMCP("SecondBrain — Robolinks Knowledge Hub")`
  - Import and register all tools from `tools/` and `tools/internal/`
  - Export `mcp` for mounting in `backend/main.py`
  - _Requirements: 1.1, 1.4, 1.5_

---

- [x] 3. Update `backend/main.py` to mount MCP
  - Import `mcp` from `backend.mcp.server`
  - Mount: `app.mount("/mcp", mcp.get_asgi_app())`
  - Ensure mount is after middleware stack so `CorrelationMiddleware`, `LoggingMiddleware`, and `RateLimitMiddleware` apply to `/mcp`
  - _Requirements: 1.2, 1.3_

---

- [x] 4. Implement `backend/schemas/mcp.py` — Pydantic V2 schemas
  - `SearchKnowledgeInput`: `query: str` (validate not empty/whitespace), `mode: str = "mix"` (validate in `{"mix", "local", "global"}`)
  - `GetEntityOutput`: `name`, `type`, `description: str | None`, `relations: list`, `sources: list`
  - `PushKnowledgeInput`: `entity_name`, `entity_type`, `description`, `relations: list`, `source` (all required)
  - `PushKnowledgeOutput`: `ok: bool`, `entity_name: str`, `relations_added: int`
  - Use `@field_validator`, `X | None` syntax, no SQLAlchemy
  - _Requirements: 9.1–9.6_

---

- [x] 5. Implement `backend/mcp/tools/search.py` — `search_knowledge`
  - Decorate with `@mcp.tool()`
  - Accept `query: str`, `mode: str = "mix"`
  - Validate via `SearchKnowledgeInput` schema — reject empty query without calling LightRAG
  - Call `LightRAGQueryClient.query(query, correlation_id, mode)` via dependency/context
  - Return `response["response"]` as `str`
  - On LightRAG timeout or error: return descriptive error string, do not raise
  - Log: tool_name, correlation_id, user_token_type on start; duration_ms + result_size on success; error details on failure
  - Docstring: `"Tìm kiếm trong knowledge base Robolinks. mode: 'mix' (mặc định), 'local', 'global'"`
  - _Requirements: 4.1–4.7, 11.1–11.4_

---

- [x] 6. Implement `backend/mcp/tools/entity.py` — `get_entity`
  - Decorate with `@mcp.tool()`
  - Accept `entity_name: str` (validate not empty, max 200 chars)
  - Call `LightRAGGraphClient.get_entity` + `get_edges`, pass to `WikiBuilder.build_entity_page`
  - Forward `X-Correlation-ID` to LightRAG call
  - On not found: return `{"error": "Entity not found", "entity_name": entity_name}`
  - On timeout/error: return descriptive error dict
  - Log tool invocation and result
  - Docstring: `"Lấy thông tin chi tiết về một entity. Trả về: description, relations, source documents."`
  - _Requirements: 5.1–5.6, 11.1–11.4_

---

- [x] 7. Implement `backend/mcp/tools/documents.py` — `list_documents` + `get_document_context`
  - `list_documents(project: str | None = None, doc_type: str | None = None) -> list`
    - Query `NasFile` table where `status="indexed"` via injected DB session
    - Apply `project` filter: `nas_path ILIKE %project%` when provided
    - Apply `doc_type` filter: match against filename or folder path when provided
    - AND logic when both filters provided
    - Return list of dicts: `{"nas_path": ..., "status": ..., "indexed_at": ...}`
    - Docstring: `"Liệt kê tài liệu đã index. Filter theo dự án hoặc loại tài liệu."`
  - `get_document_context(nas_path: str) -> str`
    - Look up `NasFile` by `nas_path`
    - If not found or not indexed: return descriptive string, do not raise
    - Query LightRAG for chunks associated with document
    - Return concatenated context string with metadata prefix
    - Docstring: `"Lấy nội dung/context của một file cụ thể trên NAS."`
  - Log both tool invocations
  - _Requirements: 6.1–6.7, 7.1–7.5, 11.1–11.4_

---

- [x] 8. Implement `backend/mcp/tools/internal/push.py` — `push_knowledge`
  - Decorate with `@mcp.tool()`
  - Accept: `entity_name`, `entity_type`, `description`, `relations: list`, `source`
  - Extract token from MCP request context
  - **Check token type BEFORE any graph write**:
    - If `token.type != "internal"`: return HTTP 403 `"push_knowledge requires internal service token"`
    - Log WARNING with correlation_id and token identity
  - If valid internal token: upsert entity + relations via LightRAG
  - Return `{"ok": True, "entity_name": ..., "relations_added": len(relations)}`
  - On missing parameters: return validation error, no graph write
  - Ensure file is ONLY in `backend/mcp/tools/internal/` — NOT importable from `backend/mcp/tools/`
  - Docstring: `"[Internal only] Push entity/relation mới vào knowledge graph."`
  - _Requirements: 8.1–8.7, 11.5_

---

- [x] 9. Wire auth for MCP endpoint
  - Implement JWT verification middleware or decorator for MCP tool handlers
  - Reuse `auth_service.verify_token()` from `backend/services/auth_service.py` — no separate implementation
  - On missing `Authorization` header: return HTTP 401
  - On invalid/expired token: return HTTP 401
  - Forward decoded user identity (user_id, role, token_type) to tool handlers via context
  - _Requirements: 2.1–2.5_

---

- [x] 10. Verify rate limiting applies to `/mcp`
  - `RateLimitMiddleware` from Spec 2 already covers paths starting with `/mcp`
  - Verify Redis sliding window enforces 100 req/min/token on `/mcp`
  - Verify HTTP 429 + `Retry-After` header when limit exceeded
  - Verify Redis failure falls back to allow-through with WARNING log
  - _Requirements: 3.1–3.5_

---

- [x] 11. Write `docs/mcp-claude-desktop.md`
  - Create `docs/mcp-claude-desktop.md`
  - Include exact JSON config block for Claude Desktop
  - Specify config file paths for Windows and macOS
  - Include recommended custom instruction in Vietnamese
  - List all public tools with parameters and example usage in Vietnamese
  - _Requirements: 10.1–10.5_

---

- [x] 12. Write unit tests
  - `tests/unit/backend/test_mcp_schemas.py`
    - `SearchKnowledgeInput` rejects empty query → ValidationError
    - `SearchKnowledgeInput` rejects invalid mode → ValidationError
    - `PushKnowledgeInput` rejects missing fields → ValidationError
  - `tests/unit/backend/test_mcp_tools.py`
    - `search_knowledge` empty query → error string without calling LightRAG (mock)
    - `search_knowledge` valid query → calls LightRAG with `mode="mix"`, returns answer string
    - `search_knowledge` LightRAG timeout → returns error string, no exception raised
    - `get_entity` valid name → calls graph client, passes through WikiBuilder
    - `get_entity` not found → returns `{"error": "Entity not found", ...}`
    - `list_documents` no filters → returns all indexed NasFiles
    - `list_documents` with `project` filter → filtered list
    - `get_document_context` unknown path → descriptive string, no exception
    - `push_knowledge` with user token → HTTP 403, WARNING logged, no graph write
    - `push_knowledge` with internal token → returns `{"ok": True, ...}`
  - All tests mock LightRAG clients and DB — no real services or Docker
  - _Requirements: 1–11_

---

- [x] 13. Checkpoint — run MCP unit tests
  - `pytest tests/unit/backend/ -k "mcp" -v`
  - All tests pass without real LightRAG or Docker

---

- [x] 14. Manual verification with running stack
  - Start backend with Spec 4–6 available
  - Verify `GET /mcp` or `POST /mcp` returns MCP protocol response
  - Set up Claude Desktop with `docs/mcp-claude-desktop.md` instructions
  - Ask Claude: `"Dự án Heineken dùng motor gì?"` → verify `search_knowledge` tool is called, answer contains citation
  - Call `get_entity` with `"Heineken Bình Dương 2024"` → verify entity page returned
  - Call `push_knowledge` with user JWT → verify HTTP 403
  - Check Seq logs for `tool_name`, `correlation_id`, `duration_ms`
  - _Requirements: Definition of Done_

---

## Notes

- `push_knowledge` token type check must happen before any graph write — no exceptions.
- `backend/mcp/tools/internal/push.py` must not be importable from `backend/mcp/tools/` — keep the internal boundary.
- MCP tools reuse existing LightRAG/DB integrations — do not duplicate HTTP logic.
- Rate limiting is already handled by `RateLimitMiddleware` from Spec 2 — no separate MCP rate limit needed if middleware is correctly scoped to `/mcp`.
- Tool docstrings must be in Vietnamese — they appear in Claude's tool list.
- Always forward `X-Correlation-ID` from MCP request context to LightRAG calls.
