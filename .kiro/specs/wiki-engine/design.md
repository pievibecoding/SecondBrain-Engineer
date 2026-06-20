# Design Document — Spec 6: Wiki Engine

## Overview

Spec 6 implements the Wiki Engine for SecondBrain: graph-driven entity browsing, entity page rendering, and entity search. It is a read-only view on top of the LightRAG knowledge graph built in Spec 4.

This spec depends on Spec 4 LightRAG graph client. It does not implement Chat, document ingestion, or NAS watching.

---

## Architecture

### Wiki Flow

```text
Wiki UI
  -> useWikiEntity(name) hook
  -> frontend/src/api/wiki.ts
  -> GET /api/wiki/entity/{name}
  -> backend/routers/wiki.py
  -> LightRAGGraphClient.get_entity(name, correlation_id)
  -> LightRAGGraphClient.get_edges(name, correlation_id)
  -> WikiBuilder.build_entity_page(entity, edges)
  -> WikiPageResponse JSON
```

### Wiki Search Flow

```text
GET /api/wiki/search?q=Heineken
  -> LightRAGQueryClient.query(q, mode="mix") or graph search
  -> normalize results to EntitySummaryResponse[]
```

### Wiki Entity Listing Flow

```text
GET /api/wiki/entities?type=PROJECT
  -> LightRAG does not expose entity listing by type in v1.5 MVP
  -> Return empty list [] with HTTP 200
  -> Document limitation in this design
```

---

## Components

### `backend/schemas/wiki.py`

Pydantic V2 schemas for wiki API responses.

```python
class EntitySummaryResponse(BaseModel):
    name: str
    type: str
    description: str | None = None
    score: float | None = None

class RelationItem(BaseModel):
    src: str
    rel_type: str
    tgt: str
    description: str | None = None
    source: str | None = None

class SourceDocument(BaseModel):
    file: str
    nas_path: str | None = None
    url: str | None = None      # MinIO URL when available
    page: int | None = None
    excerpt: str | None = None

class GraphNode(BaseModel):
    id: str
    label: str
    type: str | None = None

class GraphEdge(BaseModel):
    source: str
    target: str
    label: str | None = None

class WikiPageResponse(BaseModel):
    name: str
    type: str
    description: str | None = None
    relations: list[RelationItem] = []
    sources: list[SourceDocument] = []
    graph_nodes: list[GraphNode] = []
    graph_edges: list[GraphEdge] = []
```

### `backend/services/wiki_builder.py`

Converts raw LightRAG graph responses into stable wiki page data. No HTTP calls.

Algorithm:

```text
1. Read entity name/type/description from LightRAG entity dict
2. Normalize relations from entity.relations and graph edges response
3. Deduplicate relations by (src, rel_type, tgt)
4. Read sources from entity.sources fields
5. Convert NAS path → MinIO URL if available in metadata; otherwise url=None
6. Deduplicate sources by (file, nas_path, page)
7. Build mini graph:
   - center node = entity name + type
   - neighbor nodes = unique src/tgt values from relations (excluding center)
   - edges = (src, tgt, rel_type) from relations
8. Return WikiPageResponse-compatible dict
```

Tolerances:
- Missing `relations` → empty list
- Missing `sources` → empty list
- Missing `description` → `None`
- Unknown LightRAG response shape → return safe empty structures, do not crash

### `backend/routers/wiki.py`

Thin HTTP layer for Wiki UI.

Endpoints:

```http
GET /api/wiki/entity/{entity_name}
GET /api/wiki/search?q=...
GET /api/wiki/entities?type=...
```

Implementation notes:

- `GET /api/wiki/entity/{entity_name}` — primary MVP endpoint. Calls graph client for entity + edges, passes to WikiBuilder.
- `GET /api/wiki/entities?type=...` — MVP returns empty list (LightRAG v1.5 does not expose entity listing by type). Returns HTTP 200 with `[]`.
- `GET /api/wiki/search?q=...` — uses LightRAG query `mode="mix"` and normalizes to `EntitySummaryResponse[]`.

Entity types (Robolinks taxonomy from pa3-design Section 14):

```python
VALID_ENTITY_TYPES = {
    "PROJECT", "CLIENT", "EQUIPMENT", "COMPONENT", "SUPPLIER",
    "PERSON", "PROCESS", "ERROR_CODE", "DOCUMENT", "LOCATION", "STANDARD"
}
```

Dependency injection:

```python
@router.get("/entity/{entity_name}")
async def get_entity_page(
    entity_name: str,
    current_user = Depends(get_current_user),
    graph_client: LightRAGGraphClient = Depends(get_lightrag_graph_client),
    db: AsyncSession = Depends(get_session),
) -> WikiPageResponse:
    ...
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Entity not found | HTTP 404 |
| LightRAG graph timeout | HTTP 504 |
| LightRAG graph non-2xx | HTTP 502 |
| Missing optional fields | Empty arrays or null fields |
| Entity listing unsupported | HTTP 200 with empty list |

---

## Testing Strategy

### Unit Tests

Files:

```text
tests/unit/backend/test_wiki_builder.py
tests/unit/backend/test_wiki_router.py
```

`wiki_builder` tests use fake LightRAG entity dicts — no real LightRAG needed.

`wiki_router` tests mock `LightRAGGraphClient` via `dependency_overrides`.

Key cases:
- Assembly from fake entity + edges → correct name/type/description/relations/sources
- Deduplication: repeated relations → single entry
- Missing optional fields → empty lists, no crash
- `GET /api/wiki/entity/{name}` → `WikiPageResponse` shape
- LightRAG returns 404 → router returns HTTP 404
- `GET /api/wiki/search` → list shape
- `GET /api/wiki/entities` → empty list, HTTP 200
