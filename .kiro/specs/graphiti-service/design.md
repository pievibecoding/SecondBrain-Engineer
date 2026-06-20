# Design Document — Spec 6: Graphiti Conversation Memory

## Purpose

Spec 6 designs the Graphiti conversation memory service and how backend integrates with it. Conversation memory extracts entities/relations from chat turns, stores temporal graph facts, and allows the system to answer questions later using conversational evidence.

Principles:

- Best-effort: Graphiti must never block chat responses.
- Traceability: forward `X-Correlation-ID` for end-to-end tracing.
- Separation of concerns: extraction logic and graph writer live inside Graphiti service; backend only triggers and reads episode status.
- Idempotency: re-processing an episode must not duplicate facts.

---

## Components

1. graphiti-service (FastAPI app, port 9622)
   - routers/extract.py: `POST /extract`
   - services/extractor.py: LLM extraction logic + validation
   - services/graph_writer.py: upsert nodes/edges with temporal metadata
   - repositories/episode_repo.py: DB access for episodes
   - models/episode.py: SQLAlchemy model for episodes
   - logger.py: structlog wrapper -> Seq

2. backend/integrations/graphiti.py
   - HTTP client wrapper that forwards `X-Correlation-ID` and handles errors

3. backend/services/conversation_service.py (updated)
   - schedule background Graphiti trigger and mark `Message.graphiti_synced`

4. tests/ — unit tests for extractor, graph_writer, episode_repo, and backend trigger

---

## Data model (Graphiti DB schema)

Episodes table (simplified):

```sql
CREATE TABLE episodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id text NOT NULL,
  status text NOT NULL DEFAULT 'pending', -- pending|processing|done|failed
  entities_added int DEFAULT 0,
  relations_added int DEFAULT 0,
  error_msg text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

Graph store: use Apache AGE/PostgreSQL or the graphiti-core storage recommended in graphiti-api.md. Store nodes with canonical name and a mapping table for aliases.

Edges include: src_node_id, rel_type, tgt_node_id, episode_id, created_at, expired boolean default false.

---

## Extraction flow (detailed)

1. Graphiti `POST /extract` receives conversation_id, turns, timestamp.
2. Create episode row status=`pending`.
3. Enqueue extraction job (immediate background worker or asyncio task) — set status=`processing`.
4. Convert turns -> single text payload for LLM (with system prompt tuned to Robolinks taxonomy).
5. Call EXTRACT LLM (configured in Graphiti service settings) to return JSON
   {entities: [...], relations: [...]}.
6. Validate JSON shape, filter unknown types, deduplicate.
7. Upsert entities and edges to graph store with episode provenance and timestamps.
8. Update episode row with counts and set status=`done` or `failed` and `error_msg`.

Idempotency:

- Use episode id as provenance; upserts must check for existing edge with same (src,rel_type,tgt,episode_id) to prevent duplicates.

Temporal semantics & contradictions:

- When a new edge is inserted that contradicts an earlier edge (same src+rel_type but different tgt), mark older edge expired and keep provenance of both.

---

## Backend integration patterns

- backend/integrations/graphiti.py exports `extract(conversation_id, turns, correlation_id)` which returns parsed JSON or `{"ok": False}` on error.
- Backend chat flows call this via background task and update Message.graphiti_synced on success.
- All calls must forward `X-Correlation-ID` and log it.

---

## Operational notes

- Configure Graphiti LLM endpoint and DB via Pydantic Settings.
- Use Seq for structured logging; include correlation_id and episode_id.
- Implement graceful shutdown: finish current in-flight extraction then exit.
- Retries: for transient LLM or DB errors, retry with exponential backoff (max attempts configurable).

---

## Testing

- Unit test extractor with mocked LLM returning JSON strings.
- Unit test graph_writer to ensure upsert and expiry rules work using a SQLite/Postgres test DB.
- Integration-style tests mock Graphiti client from backend to verify background trigger and message flag update.
