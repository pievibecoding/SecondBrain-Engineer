# Requirements Document

## Introduction

Spec 5 xây dựng **Chat API + Streaming** cho SecondBrain. Backend expose endpoint SSE streaming để kỹ sư Robolinks hỏi đáp bằng tiếng Việt, nhận câu trả lời realtime với citations, lưu lịch sử hội thoại, và trigger Graphiti memory best-effort sau mỗi turn.

Backend là orchestrator: router validate → gọi `LightRAGQueryClient` (từ Spec 4) → stream về frontend → lưu `Message` vào DB → fire-and-forget Graphiti.

**Dependency:** Spec 4 (LightRAG Integration) phải hoàn thành:
- `LightRAGQueryClient` (query + query_stream) đã có và được inject qua `backend/dependencies/services.py`
- `Conversation` và `Message` ORM models đã có từ Spec 2
- Correlation middleware, auth dependencies đã có từ Spec 2

**Definition of Done:**
- `POST /api/chat/stream` trả `text/event-stream`, stream token về frontend theo format `data: {token}\n\n`, kết thúc bằng `data: [DONE]\n\n`, và lưu đầy đủ user/assistant messages
- LightRAG query trong chat mặc định và bắt buộc dùng `mode="mix"`
- Chat response hiển thị citations dạng document hoặc graph entity
- `GET /api/chat/conversations` và `GET /api/chat/conversations/{id}/messages` trả lịch sử của user hiện tại
- Sau khi assistant response hoàn tất, backend trigger Graphiti extract best-effort và không block user
- `pytest tests/unit/backend/ -k "chat" -v` passes

---

## Glossary

- **Chat SSE**: Server-Sent Events stream từ backend về frontend cho câu trả lời realtime
- **Conversation**: Một phiên hội thoại của user, lưu trong bảng `conversations`
- **Message**: Một turn user/assistant trong bảng `messages`, có `citations` và `graphiti_synced`
- **Citation**: Nguồn được LightRAG trả về, gồm document source hoặc graph entity/relation
- **Graphiti trigger**: Background best-effort call đến `graphiti-service /extract` sau khi chat response xong
- **Query mode mix**: Mode LightRAG bắt buộc cho chat production path
- **Correlation ID**: `X-Correlation-ID` phải forward đến LightRAG và Graphiti

---

## Requirements

### Requirement 1: Chat Pydantic Schemas

**User Story:** As a frontend developer, I want stable chat request and response schemas, so that Chat UI can validate inputs and render streamed messages with citations consistently.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 5.2 (Chat workflow), Section 8.2 (Chat request/response)

#### Acceptance Criteria

1. THE backend SHALL define chat schemas in `backend/schemas/chat.py` using Pydantic V2.
2. THE `ChatRequest` schema SHALL include `message: str` and `conversation_id: str | None = None`.
3. THE `ChatRequest.message` field SHALL reject empty or whitespace-only messages.
4. THE `CitationItem` schema SHALL include `type: str`, `file: str | None`, `page: int | None`, `excerpt: str | None`, `entity: str | None`, `relation: str | None`, and `target: str | None`.
5. THE `ChatResponse` schema SHALL include `conversation_id: str`, `answer: str`, `citations: list[CitationItem]`, `query_mode: str`, and `latency_ms: int | None`.
6. THE `ConversationResponse` schema SHALL include `id`, `title`, `created_at`, and `updated_at`.
7. THE `MessageResponse` schema SHALL include `id`, `conversation_id`, `role`, `content`, `citations`, `graphiti_synced`, and `created_at`.
8. THE schemas SHALL use `ConfigDict(from_attributes=True)` for ORM-backed responses.
9. THE schemas SHALL use `X | None` syntax and SHALL NOT contain SQLAlchemy code.

---

### Requirement 2: Conversation Service

**User Story:** As a Robolinks engineer, I want chat history saved automatically, so that I can continue previous conversations and audit answers later.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `graphiti-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 5.2 (Conversation storage), Section 7.1 (`conversations` and `messages` tables)

#### Acceptance Criteria

1. THE `ConversationService` SHALL be implemented in `backend/services/conversation_service.py`.
2. THE service SHALL expose `get_or_create_conversation(db, user_id, conversation_id, first_message) -> Conversation`.
3. WHEN `conversation_id` is `None`, THE service SHALL create a new conversation for `user_id`.
4. WHEN `conversation_id` is provided, THE service SHALL load only a conversation owned by `user_id`.
5. WHEN the conversation does not exist or belongs to another user, THE service SHALL raise a domain error convertible to HTTP 404.
6. THE service SHALL generate a conversation title from the first user message, truncated to a safe display length.
7. THE service SHALL expose `add_message(db, conversation_id, role, content, citations=None, graphiti_synced=False) -> Message`.
8. THE service SHALL update `Conversation.updated_at` whenever a message is added.
9. THE service SHALL expose `list_conversations(db, user_id, limit, offset) -> list[Conversation]` ordered by `updated_at DESC`.
10. THE service SHALL expose `list_messages(db, user_id, conversation_id) -> list[Message]` and enforce conversation ownership.
11. THE service SHALL NOT import `httpx` or LightRAG/Graphiti integration modules directly.

---

### Requirement 3: Chat Streaming Router

**User Story:** As a Robolinks engineer, I want answers to stream token-by-token, so that I can read responses immediately instead of waiting for the full LLM answer.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `graphiti-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 5.2 (Chat workflow), Section 8.2 (Chat response)

#### Acceptance Criteria

1. THE `ChatRouter` SHALL be implemented in `backend/routers/chat.py` as a thin FastAPI router.
2. THE router SHALL implement `POST /api/chat/stream` accepting `ChatRequest` and requiring authenticated user.
3. THE endpoint SHALL return `StreamingResponse` with media type `text/event-stream`.
4. THE endpoint SHALL get `LightRAGQueryClient` through `Depends(get_lightrag_query_client)`.
5. THE endpoint SHALL forward `request.state.correlation_id` to LightRAG.
6. THE endpoint SHALL call LightRAG streaming query with `mode="mix"` by default and SHALL NOT use `naive`, `local`, `global`, or `hybrid` as production default.
7. BEFORE streaming assistant tokens, THE endpoint SHALL create/load the conversation and save the user message.
8. DURING streaming, THE endpoint SHALL emit token chunks as plain SSE data lines in the format `data: {token}\n\n`.
9. AFTER streaming completes, THE endpoint SHALL save the assistant message with full accumulated answer and parsed citations.
10. WHEN LightRAG returns citations/sources metadata, THE endpoint SHALL normalize them into `CitationItem` shape.
11. WHEN LightRAG errors before streaming starts, THE endpoint SHALL return HTTP 502 or 504 with a safe detail.
12. WHEN LightRAG errors during streaming, THE endpoint SHALL emit an `error` SSE event and close the stream.
13. THE endpoint SHALL log start, completion, and error events with `conversation_id`, `user_id`, and `correlation_id`.
14. AFTER successful completion, THE endpoint SHALL emit final completion as `data: [DONE]\n\n`.

---

### Requirement 4: Chat Non-Streaming Endpoint

**User Story:** As a backend or MCP caller, I want a non-streaming chat endpoint, so that automated clients can receive one JSON response without parsing SSE.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8.1 (POST `/api/chat`), Section 8.2 (Chat response format)

#### Acceptance Criteria

1. THE `ChatRouter` SHALL implement `POST /api/chat` accepting `ChatRequest` and returning `ChatResponse`.
2. THE endpoint SHALL require authenticated user.
3. THE endpoint SHALL use `LightRAGQueryClient.query(..., mode="mix")`.
4. THE endpoint SHALL save the user message before querying LightRAG.
5. THE endpoint SHALL save the assistant message after receiving LightRAG response.
6. THE endpoint SHALL return `query_mode="mix"` in the response.
7. THE endpoint SHALL include normalized citations from LightRAG sources/context.
8. WHEN LightRAG fails, THE endpoint SHALL return HTTP 502 or 504 and SHALL not save an assistant message as if it succeeded.

---

### Requirement 5: Graphiti Background Trigger

**User Story:** As a Robolinks engineer, I want useful facts from conversations to enrich the graph, so that SecondBrain improves as engineers use chat daily.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `graphiti-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 5.2 (Graphiti pipeline), graphiti-api.md (Extract from conversation)

#### Acceptance Criteria

1. THE backend SHALL trigger Graphiti extraction after a successful assistant response is saved.
2. THE trigger SHALL be best-effort background work and SHALL NOT block chat response delivery.
3. THE trigger SHALL send `conversation_id`, the user turn, the assistant turn, and timestamp to Graphiti.
4. THE trigger SHALL forward the same `X-Correlation-ID` used by the chat request.
5. WHEN Graphiti returns success, THE backend SHALL mark the assistant `Message.graphiti_synced=True`.
6. WHEN Graphiti fails, THE backend SHALL log a warning and keep `graphiti_synced=False`.
7. THE trigger SHALL avoid sending empty assistant responses to Graphiti.
8. THE trigger SHALL be testable with dependency override or injected client; router code SHALL NOT import `httpx`.

---

### Requirement 6: Chat History Endpoints

**User Story:** As a Robolinks engineer, I want to see my previous conversations and messages, so that I can resume prior work and verify what was answered.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8.1 (Chat conversation endpoints), Section 7.1 (Conversation and Message tables)

#### Acceptance Criteria

1. THE `ChatRouter` SHALL implement `GET /api/chat/conversations` requiring authenticated user.
2. THE endpoint SHALL return only conversations owned by the current user.
3. THE endpoint SHALL support `limit` and `offset` query parameters with safe defaults.
4. THE endpoint SHALL order conversations by `updated_at DESC`.
5. THE `ChatRouter` SHALL implement `GET /api/chat/conversations/{conversation_id}/messages` requiring authenticated user.
6. THE messages endpoint SHALL return only messages for a conversation owned by the current user.
7. WHEN a conversation is missing or belongs to another user, THE endpoint SHALL return HTTP 404.
8. THE messages endpoint SHALL order messages by `created_at ASC`.

---

### Requirement 7: Router Mounting

**User Story:** As a developer, I want the Chat API mounted under the documented path, so that frontend and other callers reach it consistently.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8.1 (API contracts), Section 4 (`backend/main.py`)

#### Acceptance Criteria

1. THE backend app SHALL include the chat router in `backend/main.py` with prefix `/api/chat`.
2. THE chat router SHALL be tagged as `chat` or equivalent.
3. THE mounted endpoints SHALL rely on auth dependencies and SHALL NOT expose user chat data anonymously.

---

### Requirement 8: Unit Tests: Backend Chat

**User Story:** As a developer, I want unit tests for chat schemas, service, and router, so that streaming behavior and conversation persistence are safe without running LightRAG.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `graphiti-api.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Unit tests), test-conventions.md (Router with mocks)

#### Acceptance Criteria

1. THE backend tests SHALL cover `ChatRequest` validation and citation schema shape.
2. THE conversation service tests SHALL cover creating conversations, adding messages, ownership enforcement, and ordering.
3. THE chat router tests SHALL mock `LightRAGQueryClient` and verify `POST /api/chat` uses `mode="mix"`.
4. THE chat streaming tests SHALL verify `POST /api/chat/stream` returns `text/event-stream`.
5. THE streaming tests SHALL verify token and done events are emitted for a successful mock stream.
6. THE router tests SHALL verify LightRAG errors map to safe HTTP or SSE error behavior.
7. THE Graphiti trigger tests SHALL verify success marks `graphiti_synced=True` and failure leaves it `False` without failing chat.
8. ALL tests SHALL run without real LightRAG, real Graphiti, PostgreSQL Docker, or NAS.
