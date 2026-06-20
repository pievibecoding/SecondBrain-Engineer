# Implementation Plan — Spec 6: Graphiti Conversation Memory

Implement Graphiti service and backend integration. Prioritise unit tests and non-blocking background behavior.

---

## Tasks

- [x] 1. Create `graphiti-service` package skeleton
  - files:
    - `graphiti-service/main.py` (FastAPI app)
    - `graphiti-service/routers/extract.py`
    - `graphiti-service/services/extractor.py`
    - `graphiti-service/services/graph_writer.py`
    - `graphiti-service/repositories/episode_repo.py`
    - `graphiti-service/models/episode.py`
    - `graphiti-service/logger.py`
  - Ensure `requirements.txt` pins `graphiti-core` if used and other deps
  - _Requirements: 1,2,3,4,8_

---

- [x] 2. Implement episode ORM model and repo
  - `models/episode.py` SQLAlchemy DeclarativeBase model per design
  - `repositories/episode_repo.py` with functions: `create_episode`, `update_episode_status`, `get_episode_by_conversation`
  - Write unit tests for repo using test DB fixture
  - _Requirements: 2.1-2.4, 7.1-7.3_

---

- [x] 3. Implement extractor service
  - `services/extractor.py` composes system prompt and calls LLM client
  - Validate JSON output shape and allowed types
  - Deduplicate entities, normalize names (trim, lower-case), attach confidence when present
  - Unit tests mock LLM responses (valid, invalid, partial)
  - _Requirements: 3.1-3.5, 7.1_

---

- [x] 4. Implement graph writer
  - `services/graph_writer.py` upserts nodes and edges with provenance and timestamp
  - Support marking edges expired when contradicted
  - Ensure idempotency by checking episode provenance
  - Unit tests verifying upsert, dedup, expire logic
  - _Requirements: 4.1-4.5, 7.2_

---

- [x] 5. Implement `POST /extract` router
  - Validate payload and correlation id header
  - Create episode via repo, schedule extraction job (background)
  - Return accepted response quickly with episode id and `ok: true`
  - Integration tests for router validation and accepted response
  - _Requirements: 1.1-1.6, 2.1-2.4_

---

- [x] 6. Implement backend integration client
  - `backend/integrations/graphiti.py` with `extract()` function per spec
  - Use `httpx.AsyncClient` and forward `X-Correlation-ID`
  - Unit tests using `pytest-httpx` to verify payload and header
  - Add dependency provider `get_graphiti_client` in `backend/dependencies/services.py`
  - _Requirements: 5.1-5.5, 11.1-11.4_

---

- [x] 7. Wire backend trigger after chat
  - Update `backend/services/conversation_service.py` to schedule background extraction after assistant message saved
  - Ensure background task uses its own DB session
  - Mark `Message.graphiti_synced=True` after successful extract
  - Unit tests mock `backend.integrations.graphiti.extract` to assert behavior
  - _Requirements: 6.1-6.5, 7.3_

---

- [x] 8. Logging, graceful shutdown, and retry
  - Graphiti logger to Seq via HTTP ingestion
  - Validate env vars at startup and exit on missing required settings
  - Implement SIGTERM/SIGINT handling to finish in-flight jobs
  - Implement retry policy for transient LLM/DB errors
  - _Requirements: 8.1-8.4_

---

- [x] 9. Tests
  - Unit tests for extractor, graph_writer, episode_repo
  - Backend unit tests for trigger and integration client
  - Add fixture for mock LLM and for test DB
  - Ensure tests run without external services
  - _Requirements: 7.1-7.4_

---

- [x] 10. Smoke test with local stack
  - Start Graphiti service and backend locally (or via docker compose subset)
  - Send `POST /extract` sample payload and verify episode created and updated to `done`
  - Trigger chat flow from Spec 5 and verify `graphiti_synced` updated after background job
  - Verify Seq logs include correlation_id and episode_id
  - _Requirements: overall_
