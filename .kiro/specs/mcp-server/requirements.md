# Requirements Document

## Introduction

MCP Server là module cho phép các AI tool bên ngoài (Claude Desktop, Kiro, Cursor)
và các dự án future (OCR pipeline, video transcript service) truy vấn và cập nhật
knowledge base SecondBrain thông qua Model Context Protocol (MCP).

Server được implement bằng thư viện `fastmcp` Python, chạy **cùng process với
backend FastAPI**, mount tại endpoint `/mcp`. Phân quyền dùng chung hệ thống
Bearer token của backend. Public tools cho phép query; internal tool `push_knowledge`
chỉ accept internal service token (không phải user token thông thường).

**Dependencies:**
- Spec 5 — Chat API (LightRAG query integration, auth middleware)
- Spec 6 — Wiki Engine (entity/graph data, wiki_builder service)

---

## Glossary

- **MCP_Server**: FastMCP instance mount tại `/mcp`, phục vụ MCP protocol
- **MCP_Client**: AI tool kết nối đến MCP_Server (Claude Desktop, Kiro, Cursor...)
- **Bearer_Token**: JWT token dùng chung với backend, truyền qua header `Authorization: Bearer <token>`
- **Internal_Token**: Token đặc biệt cho internal services, phân biệt với user JWT thông thường
- **User_Token**: JWT token do người dùng đăng nhập lấy được qua `/api/auth/login`
- **LightRAG**: Graph + Vector engine tại port 9621, cung cấp `search_knowledge` và `get_entity`
- **NAS_Path**: Đường dẫn file trên Synology NAS, dạng `/projects/{project}/{stage}/{file}`
- **Rate_Limiter**: Middleware kiểm soát số request trên `/mcp` endpoint
- **Correlation_ID**: UUID được inject vào mỗi request để trace log qua các service

---

## Requirements

### Requirement 1: FastMCP Server Instance và Mount

**User Story:** As a Robolinks developer, I want the MCP server to run inside the
same FastAPI process, so that no additional infrastructure is needed and all
existing middleware (auth, logging, rate limit) applies automatically.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (MCP Server — Stack), Section 6.1 (Services và ports)

#### Acceptance Criteria

1. THE MCP_Server SHALL be instantiated as a `FastMCP` object in `backend/mcp/server.py`.
2. WHEN the backend FastAPI application starts, THE MCP_Server SHALL be mounted at the `/mcp` path via `app.mount("/mcp", mcp.get_asgi_app())` in `backend/main.py`.
3. WHEN a MCP_Client sends a request to `GET /mcp` or `POST /mcp`, THE MCP_Server SHALL return a valid MCP protocol response with HTTP status 200.
4. THE MCP_Server SHALL expose its name as `"SecondBrain — Robolinks Knowledge Hub"` in the MCP handshake response.
5. WHEN the backend starts successfully, THE MCP_Server SHALL register all public tools (`search_knowledge`, `get_entity`, `list_documents`, `get_document_context`) and one internal tool (`push_knowledge`) in its tool registry.

---

### Requirement 2: Xác thực Bearer Token cho MCP Endpoint

**User Story:** As a Robolinks security engineer, I want all MCP requests to require
a valid Bearer token, so that only authenticated users and services can access the
knowledge base through MCP.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (Bảo mật MCP), Section 8.1 (API contracts — /mcp endpoint)

#### Acceptance Criteria

1. WHEN a request arrives at `/mcp` without an `Authorization` header, THE MCP_Server SHALL return HTTP status 401.
2. WHEN a request arrives at `/mcp` with an invalid or expired Bearer token, THE MCP_Server SHALL return HTTP status 401 with a descriptive error message.
3. WHEN a request arrives at `/mcp` with a valid Bearer token, THE MCP_Server SHALL process the request and forward the decoded user identity to the tool handler.
4. THE MCP_Server SHALL validate Bearer tokens using the same JWT verification logic as `backend/dependencies/auth.py` — no separate auth implementation.
5. THE MCP_Server SHALL include `correlation_id` (extracted from `X-Correlation-ID` header or generated if absent) in all downstream calls to LightRAG and in structured logs.

---

### Requirement 3: Rate Limiting cho /mcp Endpoint

**User Story:** As a Robolinks infrastructure engineer, I want the `/mcp` endpoint
to be rate-limited, so that no single token can overload the backend or LightRAG
service with excessive requests.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (Bảo mật MCP — Rate limit: 100 req/min/token), spec-plan Spec 7 (Rate limit)

#### Acceptance Criteria

1. THE Rate_Limiter SHALL enforce a limit of 100 requests per minute per Bearer_Token on the `/mcp` endpoint.
2. WHEN a token exceeds 100 requests within a 60-second sliding window, THE Rate_Limiter SHALL return HTTP status 429 with a `Retry-After` header indicating seconds until the limit resets.
3. WHEN a token's request count is below 100 within the current window, THE Rate_Limiter SHALL allow the request to proceed without delay.
4. THE Rate_Limiter SHALL use Redis as the counter backend to ensure accurate counting across multiple worker processes.
5. THE Rate_Limiter SHALL count only requests to `/mcp` — other backend endpoints SHALL NOT be affected by MCP rate limit configuration.

---

### Requirement 4: Tool search_knowledge

**User Story:** As a Robolinks engineer using Claude Desktop, I want to search the
knowledge base using natural language, so that I can get answers about technical
specs, processes, and project history from within my AI tool.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (MCP Tools — search_knowledge), Section 8.1 (/mcp endpoint)

#### Acceptance Criteria

1. THE MCP_Server SHALL expose a tool named `search_knowledge` accepting parameters `query: str` (required) and `mode: str` (optional, default `"mix"`).
2. WHEN `search_knowledge` is called with a non-empty `query`, THE MCP_Server SHALL call `backend/integrations/lightrag/query.py` with the provided query and mode.
3. WHEN `search_knowledge` is called with `mode="mix"`, THE MCP_Server SHALL pass `mode="mix"` to LightRAG — no override to other modes unless explicitly provided.
4. WHEN LightRAG returns a successful response, THE MCP_Server SHALL return the answer text as a `str` result to the MCP_Client.
5. IF LightRAG returns an error or times out (30 seconds), THEN THE MCP_Server SHALL return a descriptive error string to the MCP_Client rather than raising an unhandled exception.
6. WHEN `search_knowledge` is called with an empty string as `query`, THE MCP_Server SHALL return a validation error without calling LightRAG.
7. THE `search_knowledge` tool docstring SHALL state: `"Tìm kiếm trong knowledge base Robolinks. mode: 'mix' (mặc định), 'local', 'global'"`.

---

### Requirement 5: Tool get_entity

**User Story:** As a developer using Kiro or Cursor, I want to retrieve detailed
information about a specific entity, so that I get structured data about a project,
equipment, or component without needing to run a full search.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (MCP Tools — get_entity), Section 11 (Wiki Engine), Section 14 (Entity taxonomy)

#### Acceptance Criteria

1. THE MCP_Server SHALL expose a tool named `get_entity` accepting parameter `entity_name: str` (required).
2. WHEN `get_entity` is called with a valid entity name, THE MCP_Server SHALL call `backend/integrations/lightrag/graph.py` to retrieve entity data from LightRAG.
3. WHEN LightRAG returns entity data, THE MCP_Server SHALL return a `dict` containing at minimum `name`, `type`, `description`, `relations`, and `sources` fields.
4. IF the entity does not exist in the knowledge graph, THEN THE MCP_Server SHALL return a dict with `{"error": "Entity not found", "entity_name": <name>}` rather than raising an exception.
5. WHEN `get_entity` is called, THE MCP_Server SHALL forward `X-Correlation-ID` to the LightRAG call for log traceability.
6. THE `get_entity` tool docstring SHALL state: `"Lấy thông tin chi tiết về một entity. Trả về: description, relations, source documents."`.

---

### Requirement 6: Tool list_documents

**User Story:** As a Robolinks engineer, I want to list indexed documents filtered
by project or document type, so that I can find relevant files without browsing
the NAS directly.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (MCP Tools — list_documents), Section 7.1 (NAS files DB schema)

#### Acceptance Criteria

1. THE MCP_Server SHALL expose a tool named `list_documents` accepting optional parameters `project: str` (default `None`) and `doc_type: str` (default `None`).
2. WHEN `list_documents` is called without filters, THE MCP_Server SHALL return a `list` of all indexed documents from the backend database (NasFile table with status=INDEXED).
3. WHEN `list_documents` is called with `project` filter, THE MCP_Server SHALL return only documents whose `nas_path` contains the project identifier.
4. WHEN `list_documents` is called with `doc_type` filter, THE MCP_Server SHALL return only documents matching the specified type (e.g., `"BOM"`, `"SOP"`, `"manual"`).
5. WHEN both `project` and `doc_type` filters are provided, THE MCP_Server SHALL apply both filters (AND logic).
6. THE MCP_Server SHALL return each document as a dict with at minimum `nas_path`, `status`, and `indexed_at` fields.
7. THE `list_documents` tool docstring SHALL state: `"Liệt kê tài liệu đã index. Filter theo dự án hoặc loại tài liệu."`.

---

### Requirement 7: Tool get_document_context

**User Story:** As a developer, I want to retrieve the indexed content and context
of a specific NAS file, so that I can access the actual text chunks and metadata
without downloading the original file.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (MCP Tools — get_document_context), Section 5.1 (Ingestion workflow)

#### Acceptance Criteria

1. THE MCP_Server SHALL expose a tool named `get_document_context` accepting parameter `nas_path: str` (required).
2. WHEN `get_document_context` is called with a valid NAS_Path, THE MCP_Server SHALL query LightRAG for the indexed chunks associated with that document.
3. WHEN LightRAG returns chunks for the document, THE MCP_Server SHALL return a `str` containing the concatenated context with metadata (nas_path, chunk count).
4. IF the specified `nas_path` has no indexed content (file not found or not indexed), THEN THE MCP_Server SHALL return a descriptive string indicating the file is not indexed rather than raising an exception.
5. THE `get_document_context` tool docstring SHALL state: `"Lấy nội dung/context của một file cụ thể trên NAS."`.

---

### Requirement 8: Tool push_knowledge (Internal Only)

**User Story:** As a future internal service (OCR pipeline, video transcript service),
I want to push new entities and relations into the knowledge graph via MCP, so that
knowledge from specialized pipelines can enrich SecondBrain without requiring direct
database access.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (MCP Tools — push_knowledge, Bảo mật MCP), Section 3 (Key Decisions — mcp/tools/internal/)

#### Acceptance Criteria

1. THE MCP_Server SHALL expose a tool named `push_knowledge` in `backend/mcp/tools/internal/push.py` accepting parameters `entity_name: str`, `entity_type: str`, `description: str`, `relations: list`, and `source: str`.
2. WHEN `push_knowledge` is called with a User_Token, THE MCP_Server SHALL return HTTP status 403 with message `"push_knowledge requires internal service token"`.
3. WHEN `push_knowledge` is called with a valid Internal_Token, THE MCP_Server SHALL upsert the entity and relations into the knowledge graph and return a `dict` with `{"ok": true, "entity_name": <name>, "relations_added": <count>}`.
4. THE MCP_Server SHALL verify token type before executing push — token type check MUST occur before any graph write operation.
5. THE `push_knowledge` tool SHALL reside exclusively in `backend/mcp/tools/internal/push.py` and SHALL NOT be importable from `backend/mcp/tools/` (public tools directory).
6. THE `push_knowledge` tool docstring SHALL state: `"[Internal only] Push entity/relation mới vào knowledge graph."`.
7. WHEN `push_knowledge` is called with missing required parameters, THE MCP_Server SHALL return a validation error without attempting any graph write.

---

### Requirement 9: Pydantic Schemas cho MCP Tools

**User Story:** As a backend developer, I want all MCP tool inputs and outputs
validated by Pydantic schemas, so that type safety is enforced consistently with
the rest of the backend codebase.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 4 (Folder structure — schemas/mcp.py), backend-rules.md (Pydantic V2 syntax)

#### Acceptance Criteria

1. THE MCP_Server SHALL define all tool input/output schemas in `backend/schemas/mcp.py` using Pydantic V2 `BaseModel`.
2. THE `SearchKnowledgeInput` schema SHALL define `query: str` and `mode: str = "mix"` using Pydantic V2 syntax (`str | None`, `@field_validator`).
3. THE `GetEntityOutput` schema SHALL define `name: str`, `type: str`, `description: str`, `relations: list`, and `sources: list` fields.
4. THE `PushKnowledgeInput` schema SHALL define `entity_name: str`, `entity_type: str`, `description: str`, `relations: list`, and `source: str` as required fields.
5. THE `PushKnowledgeOutput` schema SHALL define `ok: bool`, `entity_name: str`, and `relations_added: int` fields.
6. IF a tool receives input that fails schema validation, THEN THE MCP_Server SHALL return a validation error response without calling LightRAG or the database.

---

### Requirement 10: Claude Desktop Integration Documentation

**User Story:** As a Robolinks engineer, I want clear documentation on how to
connect Claude Desktop to SecondBrain MCP, so that I can start using Claude with
company knowledge without needing help from a developer.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 11b (Kết nối Claude Desktop)

#### Acceptance Criteria

1. THE MCP_Server module SHALL include a `docs/mcp-claude-desktop.md` file with setup instructions for Claude Desktop.
2. THE documentation SHALL include the exact JSON configuration block:
   ```json
   {
     "mcpServers": {
       "secondbrain-robolinks": {
         "url": "http://localhost:8000/mcp",
         "transport": "http"
       }
     }
   }
   ```
3. THE documentation SHALL specify the file path where `claude_desktop_config.json` is located on Windows (`%APPDATA%\Claude\claude_desktop_config.json`) and macOS (`~/Library/Application Support/Claude/claude_desktop_config.json`).
4. THE documentation SHALL include a recommended custom instruction for Claude: `"Khi trả lời câu hỏi về kỹ thuật, dự án, thiết bị của Robolinks, luôn dùng tool search_knowledge trước khi trả lời."`.
5. THE documentation SHALL list all available public tools with their parameters and example usage in Vietnamese.

---

### Requirement 11: Structured Logging và Observability

**User Story:** As a Robolinks DevOps engineer, I want all MCP tool invocations
logged with correlation IDs, so that I can trace a Claude Desktop request end-to-end
from MCP through LightRAG in Seq.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** mcp-builder, task-breakdown
- **Reference:** pa3-design Section 4 (Debug workflow với Seq), Section 6 (Correlation ID), backend-rules.md (Structured Logging)

#### Acceptance Criteria

1. WHEN any MCP tool is invoked, THE MCP_Server SHALL log a structured entry including `tool_name`, `correlation_id`, and `user_token_type` (user vs internal).
2. WHEN a tool call completes successfully, THE MCP_Server SHALL log `tool_name`, `correlation_id`, `duration_ms`, and `result_size` (character count of result).
3. IF a tool call fails, THEN THE MCP_Server SHALL log `tool_name`, `correlation_id`, `error_type`, and `error_message` at ERROR level.
4. THE MCP_Server SHALL forward `X-Correlation-ID` to every LightRAG integration call made from MCP tools.
5. WHEN `push_knowledge` is called with a User_Token (rejected with 403), THE MCP_Server SHALL log the attempt at WARNING level including `correlation_id` and token identity.
