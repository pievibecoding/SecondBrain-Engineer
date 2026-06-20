# Requirements Document

## Introduction

Spec 6 xây dựng **Wiki Engine** cho SecondBrain — backend API để browse knowledge graph theo entity taxonomy của Robolinks, render entity page với relations và source documents, và search entity theo tên.

Wiki Engine là read-only view trên LightRAG graph: gọi `LightRAGGraphClient` (từ Spec 4), assemble data qua `WikiBuilder` service, trả về response ổn định cho frontend.

**Dependency:** Spec 4 (LightRAG Integration) phải hoàn thành:
- `LightRAGGraphClient` (get_entity + get_edges) đã có và được inject qua `backend/dependencies/services.py`

**Definition of Done:**
- `GET /api/wiki/entity/{name}` trả `WikiPageResponse` với relations + sources + mini graph
- `GET /api/wiki/search?q=Heineken` trả danh sách entities relevant
- `GET /api/wiki/entities?type=PROJECT` trả danh sách (hoặc empty list có HTTP 200 nếu LightRAG chưa hỗ trợ listing)
- Wiki page include source files link (NAS path → MinIO URL khi có metadata)
- `pytest tests/unit/backend/ -k "wiki" -v` passes

---

## Glossary

- **Wiki Entity**: Một node trong LightRAG knowledge graph, render thành wiki page
- **WikiBuilder**: Service thu gom entity, relations, sources thành response shape ổn định cho frontend
- **RelationItem**: Một cạnh trong graph: src → rel_type → tgt
- **SourceDocument**: File tài liệu liên quan đến entity, có NAS path và optional MinIO URL
- **Mini Graph**: One-hop graph với center node và neighbor nodes từ relations, dùng vis.js
- **Entity Taxonomy**: Các loại entity Robolinks: PROJECT, CLIENT, EQUIPMENT, COMPONENT, SUPPLIER, PERSON, PROCESS, ERROR_CODE, DOCUMENT, LOCATION, STANDARD
- **Correlation ID**: `X-Correlation-ID` phải forward đến LightRAG cho mọi graph call

---

## Requirements

### Requirement 1: Wiki Pydantic Schemas

**User Story:** As a frontend developer, I want stable wiki schemas, so that Wiki UI can render entity pages and graph neighbors without coupling to LightRAG raw responses.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 11 (Wiki Engine), Section 14 (Knowledge Graph Schema)

#### Acceptance Criteria

1. THE backend SHALL define wiki schemas in `backend/schemas/wiki.py` using Pydantic V2.
2. THE `EntitySummaryResponse` schema SHALL include `name`, `type`, `description`, and `score: float | None`.
3. THE `RelationItem` schema SHALL include `src`, `rel_type`, `tgt`, `description: str | None`, and `source: str | None`.
4. THE `SourceDocument` schema SHALL include `file`, `nas_path: str | None`, `url: str | None`, `page: int | None`, and `excerpt: str | None`.
5. THE `GraphNode` schema SHALL include `id`, `label`, and `type: str | None`.
6. THE `GraphEdge` schema SHALL include `source`, `target`, and `label: str | None`.
7. THE `WikiPageResponse` schema SHALL include `name`, `type`, `description`, `relations`, `sources`, `graph_nodes`, and `graph_edges`.
8. THE schemas SHALL use `X | None` syntax and SHALL NOT contain SQLAlchemy code.

---

### Requirement 2: Wiki Builder Service

**User Story:** As a backend developer, I want raw LightRAG graph data assembled in one service, so that routers stay thin and Wiki UI receives a consistent page shape.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 11 (Graph-driven Wiki), Section 15 (Unit tests for `wiki_builder.py`)

#### Acceptance Criteria

1. THE `WikiBuilder` SHALL be implemented in `backend/services/wiki_builder.py`.
2. THE service SHALL expose `build_entity_page(entity: dict, edges: list[dict]) -> WikiPageResponse | dict`.
3. THE service SHALL normalize LightRAG entity data into `name`, `type`, `description`, `relations`, and `sources`.
4. THE service SHALL normalize LightRAG edges into `RelationItem` list.
5. THE service SHALL build a one-hop mini graph with one center node and neighbor nodes from relations.
6. THE service SHALL deduplicate repeated sources and relations.
7. THE service SHALL tolerate missing optional fields from LightRAG by returning empty lists or `None`, not crashing.
8. THE service SHALL NOT call LightRAG, Graphiti, or any external HTTP service directly.
9. THE service SHALL include source file links by converting NAS paths to MinIO URLs when the required metadata is available, otherwise it SHALL return `url=None` safely.

---

### Requirement 3: Wiki Backend Router

**User Story:** As a Robolinks engineer, I want to browse project, equipment, component, process, and error-code entities, so that I can navigate knowledge without asking chat every time.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 11 (Wiki APIs), Section 14 (Entity taxonomy)

#### Acceptance Criteria

1. THE `WikiRouter` SHALL be implemented in `backend/routers/wiki.py`.
2. THE router SHALL implement `GET /api/wiki/entity/{entity_name}` requiring authenticated user.
3. THE entity endpoint SHALL call `LightRAGGraphClient.get_entity` and `LightRAGGraphClient.get_edges` through dependency injection.
4. THE entity endpoint SHALL return `WikiPageResponse` built by `WikiBuilder`.
5. WHEN LightRAG reports entity not found, THE endpoint SHALL return HTTP 404.
6. THE router SHALL implement `GET /api/wiki/search?q=...` requiring authenticated user.
7. THE search endpoint SHALL return `list[EntitySummaryResponse]` and MAY use LightRAG query or graph search depending on available Spec 4 client methods.
8. THE router SHALL implement `GET /api/wiki/entities?type=PROJECT` requiring authenticated user.
9. THE entities endpoint SHALL support known Robolinks entity types: `PROJECT`, `CLIENT`, `EQUIPMENT`, `COMPONENT`, `SUPPLIER`, `PERSON`, `PROCESS`, `ERROR_CODE`, `DOCUMENT`, `LOCATION`, and `STANDARD`.
10. WHEN the underlying LightRAG API does not support direct entity listing in MVP, THE endpoint SHALL return an empty list with HTTP 200 and document the limitation in design.
11. THE router SHALL forward `X-Correlation-ID` to LightRAG for every graph/query call.

---

### Requirement 4: Router Mounting

**User Story:** As a developer, I want the Wiki API mounted under the documented path, so that frontend calls it consistently.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`
- **Skills:** `fastapi-expert`, `task-breakdown`
- **Reference:** pa3-design Section 8.1 (API contracts), Section 4 (`backend/main.py`)

#### Acceptance Criteria

1. THE backend app SHALL include the wiki router in `backend/main.py` with prefix `/api/wiki`.
2. THE wiki router SHALL be tagged as `wiki` or equivalent.
3. THE mounted endpoints SHALL require authentication — anonymous access SHALL NOT be permitted.

---

### Requirement 5: Unit Tests: Backend Wiki

**User Story:** As a developer, I want unit tests for wiki builder and router, so that graph data is rendered safely even when LightRAG returns partial fields.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `test-conventions.md`
- **Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
- **Reference:** pa3-design Section 15 (Unit tests for `wiki_builder.py`), Section 11 (Wiki APIs)

#### Acceptance Criteria

1. THE wiki builder tests SHALL verify entity page assembly from fake LightRAG entity and edge dicts.
2. THE wiki builder tests SHALL verify relation/source deduplication.
3. THE wiki builder tests SHALL verify missing optional fields do not crash page building.
4. THE wiki router tests SHALL mock `LightRAGGraphClient` and verify `/api/wiki/entity/{name}` returns `WikiPageResponse`.
5. THE wiki router tests SHALL verify LightRAG not found maps to HTTP 404.
6. THE wiki router tests SHALL verify `/api/wiki/search` and `/api/wiki/entities` return lists with expected response shape.
7. ALL tests SHALL run without real LightRAG or Docker.
