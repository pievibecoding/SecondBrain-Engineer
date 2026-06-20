# Design Document — Spec 7: MCP Server

## Overview

Spec 7 exposes SecondBrain knowledge to external AI tools (Claude Desktop, Kiro, Cursor) via the Model Context Protocol (MCP). The server runs inside the same FastAPI process using `fastmcp`, mounted at `/mcp`.

Public tools allow read-only queries. The internal `push_knowledge` tool is restricted to internal service tokens, reserved for future pipelines (OCR, video transcript).

This spec depends on:
- Spec 5 — Chat API: LightRAG query integration, auth middleware
- Spec 6 — Wiki Engine: entity/graph data, `WikiBuilder` service

---

## Architecture

```text
Claude Desktop / Kiro / Cursor
  -> HTTP Bearer token
  -> POST /mcp (MCP protocol)
  -> RateLimitMiddleware (100 req/min/token, Redis)
  -> JWT auth (same logic as backend/dependencies/auth.py)
  -> FastMCP tool dispatch
  -> search_knowledge   -> LightRAGQueryClient.query(mode="mix")
  -> get_entity         -> LightRAGGraphClient.get_entity + get_edges + WikiBuilder
  -> list_documents     -> DB query NasFile(status="indexed")
  -> get_document_context -> LightRAG search by nas_path
  -> push_knowledge     -> internal token check -> LightRAG upsert (future)
```

---

## Components

### `backend/mcp/server.py`

FastMCP instance. All tools registered here.

```python
from fastmcp import FastMCP

mcp = FastMCP("SecondBrain — Robolinks Knowledge Hub")
```

Mount in `backend/main.py`:

```python
from backend.mcp.server import mcp
app.mount("/mcp", mcp.get_asgi_app())
```

### `backend/mcp/tools/search.py`

```python
@mcp.tool()
async def search_knowledge(query: str, mode: str = "mix") -> str:
    """
    Tìm kiếm trong knowledge base Robolinks.
    mode: 'mix' (mặc định), 'local', 'global'
    """
```

Implementation:
- Validate `query` not empty, not whitespace
- Validate `mode` in `{"mix", "local", "global"}`
- Call `LightRAGQueryClient.query(query, correlation_id, mode)`
- Return `response["response"]` as str
- On timeout/error: return descriptive error string, do not raise

### `backend/mcp/tools/entity.py`

```python
@mcp.tool()
async def get_entity(entity_name: str) -> dict:
    """
    Lấy thông tin chi tiết về một entity.
    Trả về: description, relations, source documents.
    """
```

Implementation:
- Validate `entity_name` not empty
- Call `LightRAGGraphClient.get_entity` + `get_edges`
- Pass through `WikiBuilder.build_entity_page`
- On not found: return `{"error": "Entity not found", "entity_name": entity_name}`
- On timeout/error: return descriptive error dict

### `backend/mcp/tools/documents.py`

```python
@mcp.tool()
async def list_documents(project: str | None = None, doc_type: str | None = None) -> list:
    """
    Liệt kê tài liệu đã index.
    Filter theo dự án hoặc loại tài liệu.
    """

@mcp.tool()
async def get_document_context(nas_path: str) -> str:
    """
    Lấy nội dung/context của một file cụ thể trên NAS.
    """
```

`list_documents` implementation:
- Query `NasFile` table where `status="indexed"`
- Apply `project` filter: `nas_path ILIKE %project%`
- Apply `doc_type` filter: match filename extension or folder hint
- Return list of `{"nas_path": ..., "status": ..., "indexed_at": ...}`

`get_document_context` implementation:
- Look up `NasFile` by `nas_path`
- Call LightRAG query with `nas_path` as query context, or search chunks by path
- Return concatenated context string with metadata prefix
- If not indexed: return descriptive string, do not raise

### `backend/mcp/tools/internal/push.py`

```python
@mcp.tool()
async def push_knowledge(
    entity_name: str,
    entity_type: str,
    description: str,
    relations: list,
    source: str,
) -> dict:
    """
    [Internal only] Push entity/relation mới vào knowledge graph.
    """
```

Security:
- Extract token from MCP context
- If `token.type != "internal"`: return HTTP 403 `{"detail": "push_knowledge requires internal service token"}`
- Token type check MUST happen before any graph write
- If valid: upsert entity + relations via LightRAG, return `{"ok": true, "entity_name": ..., "relations_added": ...}`

Internal token distinction: JWT claims contain `type: "internal"` vs standard user tokens with `type: "user"`. Backend issues internal tokens separately via an admin endpoint (future spec).

### `backend/schemas/mcp.py`

```python
class SearchKnowledgeInput(BaseModel):
    query: str
    mode: str = "mix"

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()

    @field_validator("mode")
    @classmethod
    def mode_valid(cls, v: str) -> str:
        if v not in {"mix", "local", "global"}:
            raise ValueError("mode must be mix, local, or global")
        return v

class GetEntityOutput(BaseModel):
    name: str
    type: str
    description: str | None = None
    relations: list = []
    sources: list = []

class PushKnowledgeInput(BaseModel):
    entity_name: str
    entity_type: str
    description: str
    relations: list
    source: str

class PushKnowledgeOutput(BaseModel):
    ok: bool
    entity_name: str
    relations_added: int
```

---

## Auth & Security

| Layer | Implementation |
|---|---|
| Bearer token | Same JWT verification as `backend/dependencies/auth.py` |
| Rate limit | 100 req/min/token via Redis sliding window (shared with `RateLimitMiddleware`) |
| Anonymous | Falls into shared anonymous bucket, same 100 req/min limit |
| `push_knowledge` | Requires `token.type == "internal"` claim in JWT |

The MCP ASGI app is mounted after the middleware stack, so `CorrelationMiddleware`, `LoggingMiddleware`, and `RateLimitMiddleware` all apply to `/mcp` requests automatically.

For token verification inside tool handlers, use a context variable or request state populated by the JWT middleware before dispatching to tools.

---

## Logging

Every tool invocation logs:
- `tool_name`
- `correlation_id`
- `user_token_type` (user vs internal)

On completion:
- `duration_ms`
- `result_size` (char count)

On error:
- `error_type`, `error_message` at ERROR level

On `push_knowledge` with user token (rejected 403):
- WARNING level with `correlation_id` and token identity

---

## Claude Desktop Integration

Config file location:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Config:

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

Custom instruction:

```
Khi trả lời câu hỏi về kỹ thuật, dự án, thiết bị của Robolinks,
luôn dùng tool search_knowledge trước khi trả lời.
```

Documentation: `docs/mcp-claude-desktop.md`

---

## File Structure

```text
backend/mcp/
├── server.py                 ← FastMCP instance
└── tools/
    ├── search.py             ← search_knowledge
    ├── entity.py             ← get_entity
    ├── documents.py          ← list_documents, get_document_context
    └── internal/
        └── push.py           ← push_knowledge (internal token only)

backend/schemas/mcp.py        ← Pydantic V2 tool schemas
docs/mcp-claude-desktop.md    ← Claude Desktop setup guide
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| No Authorization header | HTTP 401 |
| Invalid/expired token | HTTP 401 |
| Rate limit exceeded | HTTP 429 + `Retry-After` |
| Redis unreachable | Allow request, log WARNING |
| `push_knowledge` with user token | HTTP 403 |
| LightRAG timeout in tool | Return error string/dict, do not raise |
| Schema validation failure | Return validation error without calling LightRAG |
