# Design Document — Spec 5: Chat API + Streaming

## Overview

Spec 5 implements the Chat API for SecondBrain: SSE streaming endpoint, non-streaming endpoint, conversation persistence, and best-effort Graphiti extraction after each assistant turn.

This spec depends on Spec 4 LightRAG clients. It does not implement Wiki, document ingestion, or NAS watching.

Key rules:
- LightRAG query mode is always `mix` for chat.
- Backend integrations forward `X-Correlation-ID`.
- `backend/services/` contains business logic and no `httpx`.
- `backend/integrations/` contains HTTP clients and no business policy.

---

## Architecture

### Chat Streaming Flow

```text
Chat UI
  -> useChat()
  -> frontend/src/api/chat.ts
  -> POST /api/chat/stream
  -> backend/routers/chat.py
  -> ConversationService.get_or_create_conversation(...)
  -> ConversationService.add_message(role="user")
  -> LightRAGQueryClient.query_stream(message, correlation_id, mode="mix")
  -> stream SSE data chunks to frontend
  -> accumulate assistant text
  -> ConversationService.add_message(role="assistant", citations=...)
  -> trigger Graphiti extract in background (fire-and-forget)
  -> SSE data: [DONE]
```

### Chat Non-Streaming Flow

```text
POST /api/chat
  -> validate ChatRequest
  -> load/create conversation
  -> save user message
  -> LightRAGQueryClient.query(..., mode="mix")
  -> normalize answer and citations
  -> save assistant message
  -> trigger Graphiti extract best-effort
  -> return ChatResponse JSON
```

### Chat History Flow

```text
GET /api/chat/conversations
  -> current user from JWT
  -> ConversationService.list_conversations(user_id)
  -> ConversationResponse[]

GET /api/chat/conversations/{id}/messages
  -> current user from JWT
  -> ConversationService.list_messages(user_id, id)
  -> MessageResponse[]
```

---

## Components

### `backend/schemas/chat.py`

Pydantic V2 schemas for chat.

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class CitationItem(BaseModel):
    type: str                     # "document" | "graph_entity"
    file: str | None = None
    page: int | None = None
    excerpt: str | None = None
    entity: str | None = None
    relation: str | None = None
    target: str | None = None

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[CitationItem]
    query_mode: str = "mix"
    latency_ms: int | None = None

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list[dict] | None
    graphiti_synced: bool
    created_at: datetime
```

### `backend/services/conversation_service.py`

Business logic for conversation persistence. No `httpx` imports.

```python
async def get_or_create_conversation(
    db: AsyncSession,
    user_id: str,
    conversation_id: str | None,
    first_message: str,
) -> Conversation: ...

async def add_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
    graphiti_synced: bool = False,
) -> Message: ...

async def list_conversations(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Conversation]: ...

async def list_messages(
    db: AsyncSession,
    user_id: str,
    conversation_id: str,
) -> list[Message]: ...
```

Design notes:
- Title is derived from first message, truncated to 80 chars.
- Ownership is enforced in service methods.
- `updated_at` is refreshed on every `add_message` call.

### `backend/routers/chat.py`

Thin HTTP layer — validates input, gets dependencies, calls services/clients.

```http
POST /api/chat/stream    — SSE streaming
POST /api/chat           — non-streaming JSON
GET  /api/chat/conversations
GET  /api/chat/conversations/{conversation_id}/messages
```

Dependencies:
- `get_current_user`
- `get_session`
- `get_lightrag_query_client`
- `get_graphiti_client`

SSE wire format:

```text
data: Dự án\n\n
data: Heineken...\n\n
data: [DONE]\n\n
```

Error event:

```text
event: error
data: {"detail":"LightRAG service error"}\n\n
```

### Citation Normalization

LightRAG returns sources in different shapes. The router normalizes to `CitationItem`:
- Document source → `type="document"`, `file`, optional `page`/`excerpt`
- Graph entity → `type="graph_entity"`, `entity`, optional `relation`/`target`
- Unknown shape → keep safe fields, do not crash

### Graphiti Background Trigger

Triggered only after a successful assistant response is saved.

```text
1. Save assistant message with graphiti_synced=False
2. Schedule background task: extract(conversation_id, turns, correlation_id)
3. If success → update assistant message graphiti_synced=True
4. If failure → log warning, leave graphiti_synced=False, chat unaffected
```

For streaming endpoint: use `asyncio.create_task` with its own DB session after stream completion.
For non-streaming endpoint: use FastAPI `BackgroundTasks`.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Empty message | HTTP 422 from schema validation |
| Conversation missing or not owned | HTTP 404 |
| LightRAG timeout before stream starts | HTTP 504 |
| LightRAG non-2xx before stream starts | HTTP 502 |
| LightRAG fails during stream | SSE `error` event, stream closes |
| Graphiti fails | log warning, chat remains successful |

---

## Testing Strategy

### Unit Tests

Files:
```text
tests/unit/backend/test_chat_schemas.py
tests/unit/backend/test_conversation_service.py
tests/unit/backend/test_chat_router.py
```

Mocks:
- `LightRAGQueryClient` via `dependency_overrides`
- `GraphitiClient` via `dependency_overrides`
- Auth `get_current_user` → `fake_user` fixture

No unit test requires real LightRAG, Graphiti, NAS, Redis, or Docker.

Key cases:
- Schema rejects empty/whitespace message
- Service creates conversation and enforces ownership
- `POST /api/chat` payload sends `mode="mix"` to LightRAG
- `POST /api/chat/stream` returns `text/event-stream`
- Stream emits `data: {token}` and `data: [DONE]`
- LightRAG timeout → HTTP 504
- Graphiti failure → `graphiti_synced=False`, chat still 200
