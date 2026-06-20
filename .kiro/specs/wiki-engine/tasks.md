# Implementation Plan — Spec 6: Wiki Engine

## Overview

Implement Wiki Engine: wiki schemas, `WikiBuilder` service, wiki router, and unit tests. This spec adds read-only entity browsing on top of the LightRAG graph client from Spec 4.

Unit tests mock LightRAG graph client. No Docker required for unit tests.

---

## Tasks

- [x] 1. Create wiki schemas
  - Create `backend/schemas/wiki.py`
  - Implement `EntitySummaryResponse`, `RelationItem`, `SourceDocument`
  - Implement `GraphNode`, `GraphEdge`, `WikiPageResponse`
  - Use Pydantic V2, `X | None` syntax
  - No SQLAlchemy code in schemas
  - _Requirements: 1.1–1.8_

---

- [x] 2. Implement wiki builder service
  - Create `backend/services/wiki_builder.py`
  - Implement `build_entity_page(entity: dict, edges: list[dict]) -> WikiPageResponse | dict`
  - Normalize entity name/type/description from LightRAG entity dict
  - Normalize relations from entity.relations + edges list
  - Deduplicate relations by `(src, rel_type, tgt)`
  - Normalize sources — convert NAS path → MinIO URL when available, else `url=None`
  - Deduplicate sources by `(file, nas_path, page)`
  - Build mini graph: center node + neighbor nodes + edges from relations
  - Tolerate missing/null fields — return empty lists, never crash
  - Do NOT call any external HTTP service
  - _Requirements: 2.1–2.9_

---

- [x] 3. Implement wiki router
  - Create `backend/routers/wiki.py`
  - Implement `GET /api/wiki/entity/{entity_name}`
    - Inject `LightRAGGraphClient` via `Depends(get_lightrag_graph_client)`
    - Forward `request.state.correlation_id`
    - Call `get_entity` + `get_edges`, pass to `WikiBuilder.build_entity_page`
    - Map `LightRAGNotFoundError` → HTTP 404
    - Map LightRAG timeout → HTTP 504, other errors → HTTP 502
  - Implement `GET /api/wiki/search?q=...`
    - Use LightRAG query client or graph search
    - Return `list[EntitySummaryResponse]`
  - Implement `GET /api/wiki/entities?type=...`
    - Validate `type` against `VALID_ENTITY_TYPES`
    - Return `[]` with HTTP 200 (entity listing not supported in LightRAG v1.5 MVP)
    - Document limitation in code comment
  - All endpoints require `Depends(get_current_user)`
  - _Requirements: 3.1–3.11_

---

- [x] 4. Mount wiki router in `backend/main.py`
  - `app.include_router(wiki_router, prefix="/api/wiki", tags=["wiki"])`
  - Ensure auth dependency enforced
  - _Requirements: 4.1–4.3_

---

- [x] 5. Write unit tests
  - `tests/unit/backend/test_wiki_builder.py`
    - Assembly from fake entity + edge dicts → correct `WikiPageResponse` shape
    - Relations deduplicated by `(src, rel_type, tgt)`
    - Sources deduplicated by `(file, nas_path, page)`
    - Missing optional fields (null relations, null sources) → empty lists, no crash
  - `tests/unit/backend/test_wiki_router.py`
    - Mock `LightRAGGraphClient` via `dependency_overrides`
    - `GET /api/wiki/entity/{name}` returns `WikiPageResponse` shape
    - LightRAG not found → HTTP 404
    - `GET /api/wiki/search` returns list shape
    - `GET /api/wiki/entities` returns empty list HTTP 200
  - All tests use `client` fixture — no real LightRAG or Docker
  - _Requirements: 5.1–5.7_

---

- [x] 6. Checkpoint — run wiki unit tests
  - `pytest tests/unit/backend/ -k "wiki" -v`
  - All tests pass without real services

---

- [x] 7. Manual smoke test with running stack
  - Start backend with Spec 4 LightRAG available and some indexed documents
  - `GET /api/wiki/entity/Heineken-Binh-Duong-2024` — verify response has relations + sources
  - `GET /api/wiki/search?q=Heineken` — verify list of entities returned
  - `GET /api/wiki/entities?type=PROJECT` — verify HTTP 200 (list may be empty)
  - Check Seq logs for `X-Correlation-ID` forwarded to LightRAG

---

## Notes

- `wiki_builder.py` must never call external HTTP — pure data transformation only.
- Router must not import `httpx` — use injected `LightRAGGraphClient`.
- Entity listing via `GET /api/wiki/entities` is expected to return `[]` in MVP — this is intentional.
- Source URL conversion (NAS path → MinIO URL) requires MinIO integration; return `url=None` safely if metadata unavailable.
