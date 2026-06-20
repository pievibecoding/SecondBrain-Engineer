# Implementation Plan — Spec 5: Chat API + Streaming

## Overview

Implement Chat API: SSE streaming endpoint, non-streaming endpoint, conversation persistence, Graphiti best-effort trigger, and unit tests.

Unit tests mock LightRAG and Graphiti. No Docker required for unit tests.

---

## Tasks

- [x] 1. Create chat schemas
  - Create `backend/schemas/chat.py`
  - Implement `ChatRequest` with `message` (strip + reject empty) and `conversation_id: str | None`
  - Implement `CitationItem` with all optional fields
  - Implement `ChatResponse`, `ConversationResponse`, `MessageResponse`
  - Use Pydantic V2 `field_validator`, `ConfigDict(from_attributes=True)`, `X | None` syntax
  - _Requirements: 1.1–1.9_

---

- [x] 2. Implement conversation service
  - Create `backend/services/conversation_service.py`
  - Implement `get_or_create_conversation(db, user_id, conversation_id, first_message)`
  - Implement `add_message(db, conversation_id, role, content, citations, graphiti_synced)`
  - Implement `list_conversations(db, user_id, limit, offset)` ordered by `updated_at DESC`
  - Implement `list_messages(db, user_id, conversation_id)` ordered by `created_at ASC`
  - Enforce ownership — raise domain error convertible to HTTP 404 when violated
  - Generate title from first_message truncated to 80 chars
  - Update `Conversation.updated_at` on `add_message`
  - Do NOT import `httpx` or integration modules
  - _Requirements: 2.1–2.11_

---

- [x] 3. Add citation normalization helper
  - Add `normalize_citations(raw_sources: list | dict | None) -> list[CitationItem]` in router or helper module
  - Map document sources → `type="document"`
  - Map graph entity sources → `type="graph_entity"`
  - Tolerate unknown shape without crashing
  - _Requirements: 3.10, 4.7_

---

- [x] 4. Implement non-streaming chat endpoint
  - Create/update `backend/routers/chat.py`
  - Implement `POST /api/chat` returning `ChatResponse`
  - Require `get_current_user`, inject `get_lightrag_query_client`, `get_session`
  - Create/load conversation, save user message before LightRAG call
  - Call LightRAG with `mode="mix"`
  - Save assistant message after success
  - Map LightRAG non-2xx → HTTP 502, timeout → HTTP 504
  - Do NOT save assistant message on LightRAG failure
  - _Requirements: 4.1–4.8_

---

- [x] 5. Implement SSE streaming endpoint
  - Implement `POST /api/chat/stream` returning `StreamingResponse(text/event-stream)`
  - Save user message, then call `LightRAGQueryClient.query_stream(..., mode="mix")`
  - Forward `request.state.correlation_id`
  - Emit `data: {token}\n\n` per chunk while accumulating full answer
  - Save assistant message with accumulated text and normalized citations after stream ends
  - Emit `data: [DONE]\n\n` after saving
  - On LightRAG error before stream: return HTTP 502/504
  - On LightRAG error during stream: emit `event: error\ndata: {...}\n\n` and close
  - Log start/completion/error with `conversation_id`, `user_id`, `correlation_id`
  - _Requirements: 3.1–3.14_

---

- [x] 6. Implement Graphiti best-effort trigger
  - After assistant message saved, schedule background Graphiti extract
  - Streaming endpoint: `asyncio.create_task` with own DB session
  - Non-streaming endpoint: `BackgroundTasks`
  - Send `conversation_id`, user turn, assistant turn, ISO timestamp
  - Forward `X-Correlation-ID`
  - On success: update `Message.graphiti_synced=True`
  - On failure: `logger.warning(...)`, leave `graphiti_synced=False`
  - Skip if assistant content is empty
  - Do NOT import `httpx` in router
  - _Requirements: 5.1–5.8_

---

- [x] 7. Implement chat history endpoints
  - Implement `GET /api/chat/conversations` with `limit` + `offset` params
  - Return only current user's conversations ordered `updated_at DESC`
  - Implement `GET /api/chat/conversations/{conversation_id}/messages`
  - Return HTTP 404 for missing or non-owned conversation
  - Return messages ordered `created_at ASC`
  - _Requirements: 6.1–6.8_

---

- [x] 8. Mount chat router in `backend/main.py`
  - `app.include_router(chat_router, prefix="/api/chat", tags=["chat"])`
  - Ensure auth dependency is enforced
  - _Requirements: 7.1–7.3_

---

- [x] 9. Write unit tests
  - `tests/unit/backend/test_chat_schemas.py`
    - empty message → ValidationError
    - whitespace-only message → ValidationError
    - valid message passes
  - `tests/unit/backend/test_conversation_service.py`
    - create conversation when `conversation_id=None`
    - ownership enforced — wrong user gets 404
    - `updated_at` refreshed on add_message
  - `tests/unit/backend/test_chat_router.py`
    - `POST /api/chat` calls LightRAG with `mode="mix"`
    - `POST /api/chat/stream` returns `text/event-stream`
    - stream emits token events and `[DONE]`
    - LightRAG timeout → HTTP 504
    - Graphiti failure → chat returns 200, `graphiti_synced=False`
  - All tests use `client` fixture and `dependency_overrides` — no real LightRAG/Graphiti/Docker
  - _Requirements: 8.1–8.8_

---

- [x] 10. Checkpoint — run chat unit tests
  - `pytest tests/unit/backend/ -k "chat" -v`
  - All tests pass without real services
  - _Requirements: 8_

---

- [x] 11. Manual smoke test with running stack
  - Start backend with Spec 4 LightRAG available
  - `POST /api/chat/stream` with `{"message": "Dự án Heineken dùng motor gì?"}`
  - Verify SSE tokens stream, `[DONE]` received
  - `GET /api/chat/conversations` — verify saved conversation
  - `GET /api/chat/conversations/{id}/messages` — verify user + assistant messages
  - Check Seq logs for `correlation_id` forwarded to LightRAG

---

## Task Dependency Graph

- Task 1 (chat schemas) có thể làm đầu tiên, độc lập
- Task 2 (conversation service) phụ thuộc Conversation/Message ORM models từ Spec 2
- Task 3 (citation normalization) có thể làm song song với Task 2
- Task 4 (non-streaming endpoint) phụ thuộc Tasks 1, 2, 3
- Task 5 (SSE streaming endpoint) phụ thuộc Tasks 1, 2, 3, 4
- Task 6 (Graphiti trigger) phụ thuộc Tasks 2, 5
- Task 7 (history endpoints) phụ thuộc Task 2
- Task 8 (mount router) phụ thuộc Tasks 4, 5, 6, 7
- Task 9 (unit tests) nên viết song song với implementation
- Task 10 (checkpoint) phụ thuộc Task 9
- Task 11 (smoke test) phụ thuộc Task 10 và stack đang chạy

## Notes

- LightRAG query mode default must always be `mix`.
- Router must not import `httpx` — use injected clients.
- `services/conversation_service.py` must not import `httpx`.
- Graphiti failure must never change chat HTTP/SSE result.
- Background Graphiti task must use its own DB session, not the request session.
