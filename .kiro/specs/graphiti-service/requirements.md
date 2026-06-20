# Requirements Document

## Introduction

Spec 6 xây dựng **Conversation Memory (Graphiti) service + Backend integration** cho SecondBrain. Mục tiêu: extract entity/relation từ hội thoại, lưu temporal graph (biết timestamp, expired edges), và cung cấp endpoint để backend trigger / kiểm tra trạng thái episode.

Graphiti khác LightRAG: Graphiti xử lý hội thoại (temporal), LightRAG xử lý tài liệu tĩnh. MVP Spec 6 giữ 2 graph riêng và backend merge kết quả khi trả lời.

**Dependency:** Spec 2 (Backend Foundation) — shared PostgreSQL. Graphiti Service có thể implement song song với Spec 3 và 4. Spec 5 (Chat API) sẽ trigger Graphiti nhưng không phải dependency build-time của service này.

**Definition of Done:**

- `graphiti-service` chạy (port 9622) và chấp nhận `POST /extract` với `X-Correlation-ID` forwarded
- Backend có `backend/integrations/graphiti.py` client, forward correlation id, return parsed result
- Sau chat trả về, backend trigger Graphiti background task (fire-and-forget) và assistant message `graphiti_synced` được cập nhật khi success
- `graphiti-service` có repository/DB models để track episodes và status
- Unit tests cover extractor logic, episode_repo, and backend integration client

---

## Glossary

- Episode: một batch hội thoại (conversation_id + turns) được gửi cho Graphiti
- Extract: hành động dùng LLM để tìm entity/relation từ turns
- Temporal Graph: graph với timestamped edges, có cơ chế mark expired
- graphiti_synced: flag trên Message khi extract thành công

---

## Requirements

### Requirement 1 — Graphiti Service: POST /extract

**User Story:** As a backend developer, I want a Graphiti HTTP endpoint to accept conversation turns and extract entities/relations, so that conversation facts are persisted to a temporal graph.

## Steering & Skills

- **Steering:** `project-context.md`, `graphiti-api.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** graphiti-api.md (Extract from conversation), pa3-design Section 9 (Conversation Memory)

#### Acceptance Criteria

1. THE `graphiti-service` SHALL implement `POST /extract` accepting JSON body: `{ "conversation_id": str, "turns": [{"role":"user"|"assistant","content":str}], "timestamp": iso8601 }`.
2. THE endpoint SHALL require `X-Correlation-ID` header; when missing, it SHALL still accept but log a warning.
3. THE endpoint SHALL validate `turns` length (>=1) and reject invalid payload with HTTP 422.
4. THE endpoint SHALL run extraction logic (LLM extract + graph writer) asynchronously inside the Graphiti service and return quickly with `{"ok": true, "entities_added": int, "relations_added": int}` when accepted.
5. WHEN extraction fails synchronously (validation/parse errors), THE endpoint SHALL return HTTP 400 with safe detail.
6. WHEN extraction background job fails, THE service SHALL record failure in episode status and return `{"ok": false}` in the stored episode record; the original `POST /extract` response can still be HTTP 200 for accepted background processing.

---

### Requirement 2 — Graphiti Service: Episode Tracking

**User Story:** As an operator, I want episode status and history stored, so that I can inspect which conversation extracts succeeded/failed and retry if needed.

## Steering & Skills

- **Steering:** `graphiti-api.md`, `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** graphiti-api.md (Get episode status)

#### Acceptance Criteria

1. THE Graphiti service SHALL persist episodes in PostgreSQL table `episodes` with fields: `id` (PK), `conversation_id`, `status` (`pending`|`processing`|`done`|`failed`), `entities_added` (int), `relations_added` (int), `error_msg` (text|null), `created_at`, `updated_at`.
2. THE `POST /extract` SHALL create an `episodes` row with `status="pending"` and transition to `processing` when extraction starts.
3. AFTER extraction completes successfully, THE episode row SHALL update `status="done"`, `entities_added`, `relations_added`, and `updated_at`.
4. WHEN extraction fails, THE episode row SHALL update `status="failed"` and `error_msg` with safe summary.
5. THE service SHALL expose `GET /episodes/{conversation_id}` that returns episode status and summary.

---

### Requirement 3 — Extraction Logic & Prompts

**User Story:** As a knowledge engineer, I want a robust extraction pipeline (system prompt + validators) tuned to Robolinks taxonomy, so that extracted entities/relations map to the project taxonomy.

## Steering & Skills

- **Steering:** `project-context.md`, `lightrag-api.md`, `graphiti-api.md`, `spec-creation-rules.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`
- **Reference:** pa3-design Section 14 (Knowledge Graph Schema), `prompts/extraction.txt` from Spec 1/Infrastructure

#### Acceptance Criteria

1. THE Graphiti extractor SHALL use a domain-specific system prompt (Vietnamese) that enumerates entity types and relation types from pa3-design Section 14.
2. THE extractor SHALL output strictly-typed JSON with `entities: [{name,type,description}]` and `relations: [{src,rel_type,tgt,description}]`.
3. THE extractor SHALL validate extracted items against allowed entity types and relation types and drop or mark invalid entries.
4. THE extractor SHALL deduplicate entity names case-insensitively before writing to graph.
5. THE extractor SHALL attach extraction confidence metadata where available.

---

### Requirement 4 — Graph Writer & Temporal Semantics

**User Story:** As a knowledge engineer, I want extracted facts to be timestamped and discoverable with temporal semantics (know when a fact was added and when it was expired/contradicted), so that conversation memory respects recency and contradictions.

## Steering & Skills

- **Steering:** `project-context.md`, `graphiti-api.md`, `backend-rules.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 9 (Temporal graph), graphiti-api.md (Graphiti internal structure)

#### Acceptance Criteria

1. THE graph writer SHALL persist nodes (entities) and edges (relations) with timestamps and source metadata (episode id).
2. THE graph writer SHALL support marking edges `expired=true` when a newer extraction contradicts older info for the same subject/property.
3. THE graph writer SHALL merge entities by canonicalization rules (case-insensitive, trim, optionally lemmatize) and provide a way to map aliases to canonical node ids.
4. THE graph writer SHALL record provenance: episode id, conversation_id, timestamp, and optional message turn index.
5. THE graph writer SHALL ensure idempotency: re-sending the same episode should not create duplicate nodes/edges.

---

### Requirement 5 — Backend Integration Client

**User Story:** As a backend developer, I want a Graphiti client in `backend/integrations/graphiti.py` that forwards `X-Correlation-ID` and provides a simple API for triggering extraction, so that routers/services can call Graphiti without importing HTTP logic directly.

## Steering & Skills

- **Steering:** `backend-rules.md`, `graphiti-api.md`, `project-context.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** graphiti-api.md (integration pattern)

#### Acceptance Criteria

1. THE integration client SHALL implement `async def extract(conversation_id: str, turns: list[dict], correlation_id: str) -> dict`.
2. THE client SHALL call `POST {GRAPHITI_URL}/extract` with the JSON body and include `X-Correlation-ID` header.
3. THE client SHALL handle HTTP errors: log and return `{"ok": False}` to caller; it SHALL NOT raise raw `httpx` exceptions to routers.
4. THE client SHALL use `httpx.AsyncClient` with a sensible timeout (default 60s) and SHALL be created per-call or via dependency (not at import time).
5. THE client SHALL be injectable via `backend/dependencies/services.py` as `get_graphiti_client`.

---

### Requirement 6 — Backend Trigger & Ownership

**User Story:** As a backend developer, I want chat flow to trigger Graphiti in background after assistant response, and to mark `Message.graphiti_synced` on success.

## Steering & Skills

- **Steering:** `graphiti-api.md`, `backend-rules.md`, `project-context.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** graphiti-api.md (Trigger Graphiti after chat)

#### Acceptance Criteria

1. AFTER an assistant response is saved, the backend SHALL schedule a background task that calls `graphiti_client.extract(...)` with the two latest turns (user + assistant) or N recent turns as configured.
2. THE scheduled task SHALL forward `X-Correlation-ID` from the original request.
3. WHEN Graphiti returns success (`ok: True`), THE backend SHALL mark the corresponding `Message.graphiti_synced=True` and update DB.
4. WHEN Graphiti fails, THE backend SHALL log a warning with `correlation_id` and leave `graphiti_synced=False`.
5. THE backend SHALL ensure the background task has its own DB session and does not reuse a request-bound session.

---

### Requirement 6b — Episode Tracker Service

**User Story:** As a developer, I want a dedicated episode tracker service, so that logic for deciding whether an episode was already processed is centralized and testable separately from the DB repository.

## Steering & Skills

- **Steering:** `project-context.md`, `graphiti-api.md`, `backend-rules.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 4 (Cấu trúc thư mục — `graphiti-service/services/episode_tracker.py`), spec-plan Spec 8 (Cover)

#### Acceptance Criteria

1. THE `EpisodeTracker` SHALL be implemented in `graphiti-service/services/episode_tracker.py`.
2. THE `EpisodeTracker` SHALL expose logic to determine whether a given `conversation_id` has already been processed (has an episode with `status="done"`).
3. THE `EpisodeTracker` SHALL delegate all DB reads/writes to `repositories/episode_repo.py` — it SHALL NOT import SQLAlchemy directly.
4. THE `EpisodeTracker` SHALL be the entry point for idempotency checks before running extraction to avoid re-processing the same episode.

---

### Requirement 6c — Dependency Pinning

**User Story:** As a developer, I want the graphiti-core version pinned exactly, so that the service behavior is deterministic and does not break on upstream releases.

## Steering & Skills

- **Steering:** `project-context.md`, `graphiti-api.md`
- **Skills:** `task-breakdown`
- **Reference:** graphiti-api.md (Docker setup — `graphiti-core==0.4.2`), spec-plan Spec 8 (Cover)

#### Acceptance Criteria

1. THE `graphiti-service/requirements.txt` SHALL pin `graphiti-core==0.4.2` — NOT `>=0.4.2` or unpinned.
2. THE `graphiti-service/requirements.txt` SHALL pin all direct dependencies with exact versions.
3. WHEN a newer version of `graphiti-core` is needed, THE version bump SHALL be done intentionally and tested explicitly — not via a wildcard upgrade.

---

### Requirement 7 — Tests and CI

**User Story:** As a developer, I want unit tests for Graphiti extractor logic, episode repo, and backend integration, so that the conversation memory feature is reliable without running the Graphiti service.

## Steering & Skills

- **Steering:** `test-conventions.md`, `backend-rules.md`, `graphiti-api.md`
- **Skills:** `quality-assurance`, `task-breakdown`, `fastapi-expert`
- **Reference:** test-conventions.md (unit/integration tiers), graphiti-api.md

#### Acceptance Criteria

1. THE Graphiti extractor unit tests SHALL be located in `tests/unit/graphiti_service/` and mock LLM calls.
2. THE episode_repo tests SHALL run against an in-memory or test PostgreSQL instance mocked via fixtures.
3. THE backend integration tests SHALL mock `backend.integrations.graphiti.extract` to verify background trigger and `graphiti_synced` flag behavior.
4. ALL unit tests SHALL run without a real Graphiti service or external LLM.

---

### Requirement 8 — Operational Considerations

**User Story:** As an operator, I want Graphiti service to log structured messages with correlation_id and support graceful shutdown and retries, so that production is observable and resilient.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `graphiti-api.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 10 (Multi-service debug), graphiti-api.md

#### Acceptance Criteria

1. THE Graphiti service SHALL ship structured logs to Seq including fields: `service="graphiti-service"`, `correlation_id`, `episode_id`, and `conversation_id` when available.
2. THE Graphiti service SHALL validate environment variables at startup and exit with code 1 when required settings are missing.
3. THE Graphiti service SHALL handle SIGTERM/SIGINT gracefully: finish current extraction job and exit.
4. THE extraction process SHALL implement idempotency and retries with exponential backoff for transient failures when calling LLM or DB writes.
