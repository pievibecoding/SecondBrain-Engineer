# SecondBrain — Spec Plan

> Kế hoạch tạo specs cho từng module, dựa trên pa3-design.md
> Ngày lập: 2026-06-16
> Trạng thái: Chưa bắt đầu implement

---

## Tổng quan

9 specs, chia theo module độc lập, theo thứ tự dependency:

| # | Spec | Workflow | Dependency | Tuần |
|---|---|---|---|---|
| 1 | Infrastructure Setup | Fast-task | — | 1 |
| 2 | Backend Foundation | Requirements-first | Spec 1 | 1 |
| 3 | NAS Connector | Requirements-first | Spec 2 | 2 |
| 4 | LightRAG Integration | Requirements-first | Spec 2 | 2 |
| 5 | Chat API + Streaming | Requirements-first | Spec 4 | 3 |
| 6 | Wiki Engine | Requirements-first | Spec 4 | 3 |
| 7 | MCP Server | Requirements-first | Spec 5+6 | 3 cuối |
| 8 | Graphiti Service | Requirements-first | Spec 2 | 5–6 |
| 9 | Frontend | Design-first | Spec 5+6 | 3–4 |

---

## Spec 1: Infrastructure Setup

**Path:** `.kiro/specs/infrastructure-setup/`
**Workflow:** Fast-task (không cần requirements phức tạp)
**Steering:** `project-context.md`
**Skills:** `task-breakdown`
**Dependency:** Không — làm đầu tiên

**Cover:**
- Docker Compose stack: postgres (pgvector:pg18), redis, minio, lightrag, seq
- LightRAG `.env` config:
  - GĐ1: `LLM_BINDING=gemini`, `LLM_MODEL=gemini-2.0-flash-lite`
  - Storage: `KV_STORAGE=PGKVStorage`, `VECTOR_STORAGE=PGVectorStorage`, `GRAPH_STORAGE=PGGraphStorage`
  - `ENABLE_LLM_CACHE=false`
  - `SUMMARY_LANGUAGE=Vietnamese`
  - `LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R`
- `.env.example` cho toàn bộ stack (NAS, LLM, DB, MinIO)
- `prompts/extraction.txt` — Robolinks EXTRACT LLM prompt (pa3-design Section 14)
- `docker-compose.dev.yml` — override hot reload
- Pin versions: `image: ghcr.io/hkuds/lightrag:v1.5.4`

**Verify (Definition of Done):**
- `docker compose up -d` chạy không lỗi
- LightRAG Web UI accessible tại port 9621
- Seq accessible tại port 80
- POST 1 file test → LightRAG trả về `status: processing`
- Query test trả về kết quả (dù empty)

---

## Spec 2: Backend Foundation

**Path:** `.kiro/specs/backend-foundation/`
**Workflow:** Requirements-first
**Steering:** `project-context.md`, `backend-rules.md`
**Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
**Dependency:** Spec 1

**Cover:**
- `backend/main.py` — FastAPI app, mount routers + MCP + middleware
- `backend/config.py` — Pydantic Settings (env vars)
- `backend/database.py` — SQLAlchemy async engine + get_session
- `backend/logger.py` — structured log → Seq với correlation_id
- `backend/middleware/correlation.py` — inject X-Correlation-ID vào mọi request/response
- `backend/middleware/logging.py` — auto-log mọi request/response
- `backend/middleware/rate_limit.py` — rate limiting cho /mcp endpoints
- `backend/dependencies/auth.py` — get_current_user, require_admin (FastAPI Depends)
- `backend/dependencies/services.py` — inject integrations clients (DI)
- `backend/models/base.py` — DeclarativeBase
- `backend/models/user.py` — User (id UUID, email, role, password_hash)
- `backend/models/conversation.py` — Conversation + Message (+ graphiti_synced flag)
- `backend/models/nas_file.py` — NasFile (nas_path, status, file_hash, lightrag_doc_id)
- `backend/models/nas_folder.py` — NasFolder (path, folder_type, is_active)
- `backend/migrations/` — Alembic setup + initial migration (tất cả tables)
- `backend/schemas/auth.py` — LoginRequest, TokenResponse, UserResponse
- `backend/services/auth_service.py` — JWT create/verify, bcrypt hash/verify
- `backend/routers/auth.py` — POST /api/auth/login, /api/auth/register, GET /api/auth/me
- `tests/unit/backend/test_schemas.py` — validate Pydantic schemas
- `tests/unit/backend/test_auth_service.py` — JWT + bcrypt unit tests
- `tests/unit/backend/test_middleware.py` — correlation ID inject test
- `tests/conftest.py` — shared fixtures (fake_user, fake_admin, client, mock_lightrag)

**Verify (Definition of Done):**
- `pytest tests/unit/backend/ -v` passes
- Alembic migration chạy không lỗi
- POST /api/auth/register → trả JWT token
- POST /api/auth/login → trả JWT token
- GET /api/auth/me với valid token → trả user info
- X-Correlation-ID xuất hiện trong response headers và Seq logs

---

## Spec 3: NAS Connector

**Path:** `.kiro/specs/nas-connector/`
**Workflow:** Requirements-first (có state machine phức tạp)
**Steering:** `project-context.md`, `nas-rules.md`, `backend-rules.md`
**Skills:** `task-breakdown`, `quality-assurance`
**Dependency:** Spec 2

**Cover:**
- `nas-connector/config.py` — NAS_HOST, NAS_USER, NAS_SHARE, BACKEND_API_URL env
- `nas-connector/watcher.py` — watchdog trên SMB mount, detect file mới/changed/deleted
  - SUPPORTED_EXTENSIONS: `.pdf, .docx, .doc, .xlsx, .xls, .pptx, .ppt`
  - METADATA_ONLY_EXTENSIONS: `.dwg, .dxf, .png, .jpg, .mp4, .avi, .step, .stl`
  - Poll interval: 5 phút
- `nas-connector/uploader.py` — gọi backend API report file (KHÔNG gọi LightRAG trực tiếp)
- `nas-connector/notifier.py` — gọi backend API notify admin
- `nas-connector/logger.py` — structured log → Seq
- `backend/routers/internal/nas.py` — GET /api/internal/nas/hash?path=... (Docker network only)
- `backend/routers/admin/nas_queue.py` — GET/POST /admin/nas/queue (approve/reject)
- `backend/routers/admin/nas_folders.py` — CRUD /admin/nas/folders
- `backend/schemas/nas.py` — NasFileResponse, ApproveRequest, FolderRequest
- `backend/services/nas_notify.py` — in-app notification khi có file cần duyệt
- NasFile state machine transitions:
  - DETECTED → QUEUED (auto folder)
  - DETECTED → PENDING_REVIEW (manual folder)
  - QUEUED → INDEXING → INDEXED | FAILED
  - PENDING_REVIEW → QUEUED (approve) | REJECTED (reject)
- `tests/unit/nas_connector/test_watcher.py` — với `tmp_path` fixture
- `tests/unit/nas_connector/test_uploader.py` — mock HTTP calls

**Verify (Definition of Done):**
- Thêm file PDF vào auto-sync folder → NasFile record với status=QUEUED trong DB
- Thêm file vào manual-review folder → NasFile với status=PENDING_REVIEW
- Admin approve → status chuyển QUEUED
- `pytest tests/unit/nas_connector/ -v` passes

---

## Spec 4: LightRAG Integration + Ingestion Pipeline

**Path:** `.kiro/specs/lightrag-integration/`
**Workflow:** Requirements-first
**Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
**Skills:** `fastapi-expert`, `task-breakdown`
**Dependency:** Spec 2, Spec 3

**Cover:**
- `backend/integrations/lightrag/ingest.py` — POST /api/v1/docs (upload file path + metadata)
- `backend/integrations/lightrag/query.py` — POST /api/v1/query (mode=mix) + streaming adapter
- `backend/integrations/lightrag/graph.py` — GET /api/v1/graph/entity/:name, GET /api/v1/graph/edges
- `backend/routers/admin/documents.py` — GET /admin/documents, POST /:id/reindex, DELETE /:id
- `backend/schemas/nas.py` (update) — DocumentResponse (nas_path, status, indexed_at, chunk_count)
- Ingestion trigger: admin approve NasFile → backend gọi LightRAG ingest
- Error handling: LightRAG timeout (30s), 502 wrapper, resume-on-crash (built-in LightRAG)
- `tests/unit/backend/test_lightrag_integration.py` — mock HTTP với pytest-httpx

**Verify (Definition of Done):**
- Approve file PDF → LightRAG nhận được POST /api/v1/docs
- NasFile.status chuyển INDEXING → INDEXED sau khi hoàn tất
- GET /admin/documents trả danh sách với status đúng
- `pytest tests/unit/backend/ -k lightrag -v` passes

---

## Spec 5: Chat API + Streaming

**Path:** `.kiro/specs/chat-api/`
**Workflow:** Requirements-first (SSE streaming, nhiều edge case)
**Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `graphiti-api.md`
**Skills:** `fastapi-expert`, `task-breakdown`, `quality-assurance`
**Dependency:** Spec 4

**Cover:**
- `backend/schemas/chat.py` — ChatRequest, ChatResponse, CitationItem (type: document | graph_entity)
- `backend/routers/chat.py`:
  - POST /api/chat/stream (SSE) — query LightRAG mode=mix, stream tokens
  - GET /api/chat/conversations — list conversations
  - GET /api/chat/conversations/:id/messages — history
- `backend/services/conversation_service.py`:
  - Lưu Message vào DB (role, content, citations JSONB)
  - Trigger Graphiti fire-and-forget (asyncio.create_task, không await)
  - graphiti_synced flag
- `backend/integrations/graphiti.py`:
  - POST /extract với turns + timestamp
  - Forward X-Correlation-ID — BẮTBUỘC
  - Lỗi Graphiti KHÔNG block user (log warning, return {ok: False})
- Chat response format (pa3-design Section 8.2):
  ```json
  {
    "conversation_id": "...",
    "answer": "...",
    "citations": [
      {"type": "document", "file": "...", "page": 3, "excerpt": "..."},
      {"type": "graph_entity", "entity": "...", "relation": "...", "target": "..."}
    ],
    "query_mode": "mix",
    "latency_ms": 1840
  }
  ```
- SSE format: `data: {token}\n\n`, kết thúc bằng `data: [DONE]\n\n`
- `tests/unit/backend/test_chat_router.py` — mock LightRAG + Graphiti

**Verify (Definition of Done):**
- POST /api/chat/stream trả SSE content-type
- Tokens stream về đúng format
- Citations có trong response cuối
- Graphiti được gọi background (verify mock was called)
- `pytest tests/unit/backend/test_chat_router.py -v` passes

---

## Spec 6: Wiki Engine

**Path:** `.kiro/specs/wiki-engine/`
**Workflow:** Requirements-first
**Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
**Skills:** `fastapi-expert`, `task-breakdown`
**Dependency:** Spec 4

**Cover:**
- `backend/schemas/wiki.py` — EntityResponse, WikiPageResponse, RelationItem
- `backend/routers/wiki.py`:
  - GET /api/wiki/entities?type=PROJECT|EQUIPMENT|... — danh sách entities theo type
  - GET /api/wiki/entity/:name — chi tiết entity + relations + sources
  - GET /api/wiki/search?q=Heineken — search entity theo tên
- `backend/services/wiki_builder.py`:
  - Gọi LightRAG graph.get_entity() + graph.get_edges()
  - Assemble WikiPageResponse: name, type, description, relations[], sources[]
- Entity taxonomy từ pa3-design Section 14:
  - Types: PROJECT, CLIENT, EQUIPMENT, COMPONENT, SUPPLIER, PERSON, PROCESS, ERROR_CODE, DOCUMENT, LOCATION, STANDARD
- Wiki page includes source files link (NAS path → MinIO URL)
- `tests/unit/backend/test_wiki_builder.py` — fake entity dict, không cần LightRAG

**Verify (Definition of Done):**
- GET /api/wiki/entities?type=PROJECT trả danh sách
- GET /api/wiki/entity/Heineken-2024 trả đủ relations + sources
- GET /api/wiki/search?q=Heineken trả kết quả relevant
- `pytest tests/unit/backend/test_wiki_builder.py -v` passes

---

## Spec 7: MCP Server

**Path:** `.kiro/specs/mcp-server/`
**Workflow:** Requirements-first
**Steering:** `project-context.md`, `backend-rules.md`
**Skills:** `mcp-builder`, `task-breakdown`
**Dependency:** Spec 5, Spec 6

**Cover:**
- `backend/mcp/server.py` — FastMCP instance, mount tại `/mcp` trong main.py
- `backend/mcp/tools/search.py` — `search_knowledge(query, mode="mix")` (public)
- `backend/mcp/tools/entity.py` — `get_entity(entity_name)` (public)
- `backend/mcp/tools/documents.py` — `list_documents(project, doc_type)`, `get_document_context(nas_path)` (public)
- `backend/mcp/tools/internal/push.py` — `push_knowledge(entity_name, entity_type, description, relations, source)` (internal token only)
- `backend/schemas/mcp.py` — MCP tool input/output schemas
- Auth: Bearer token dùng chung với backend JWT
- Rate limit: 100 req/min/token cho /mcp endpoint
- `push_knowledge` chỉ accept internal service token (khác với user token)
- Claude Desktop config example trong docs

**Verify (Definition of Done):**
- `/mcp` endpoint accessible và trả MCP protocol response
- `search_knowledge("Heineken motor")` trả kết quả từ LightRAG
- `get_entity("Heineken Bình Dương 2024")` trả entity page
- `push_knowledge` với user token → 403 Forbidden
- `push_knowledge` với internal token → success

---

## Spec 8: Graphiti Service

**Path:** `.kiro/specs/graphiti-service/`
**Workflow:** Requirements-first
**Steering:** `project-context.md`, `graphiti-api.md`
**Skills:** `task-breakdown`, `quality-assurance`
**Dependency:** Spec 2 (shared PostgreSQL)

**Cover:**
- `graphiti-service/main.py` — FastAPI entry
- `graphiti-service/config.py` — GRAPHITI_DB_URL, LLM config
- `graphiti-service/routers/memory.py`:
  - POST /extract — nhận turns + timestamp, extract entities
  - GET /episodes/:conversation_id — get sync status
- `graphiti-service/services/extractor.py` — graphiti-core `add_episode()`
- `graphiti-service/services/graph_writer.py` — upsert nodes/edges vào graph
- `graphiti-service/services/episode_tracker.py` — avoid re-processing đã xử lý
- `graphiti-service/repositories/episode_repo.py` — DB access cho episode status
- `graphiti-service/models/episode.py` — Episode SQLAlchemy model
- `graphiti-service/logger.py` — structured log → Seq
- `graphiti-core==0.4.2` — pin version
- Temporal: timestamp, mark edge "expired" khi info bị contradicted
- `tests/unit/graphiti_service/test_extractor.py` — mock LLM response

**Verify (Definition of Done):**
- POST /extract với 2 turns → Graphiti graph có entities mới
- Sau 10 chat turns thực tế → graph có entities Robolinks (PROJECT, COMPONENT...)
- GET /episodes/:id → trả synced: true sau khi process xong
- `pytest tests/unit/graphiti_service/ -v` passes

---

## Spec 9: Frontend

**Path:** `.kiro/specs/frontend/`
**Workflow:** Design-first (UI phức tạp, nhiều component)
**Steering:** `project-context.md`, `frontend-rules.md`
**Skills:** `frontend-design`, `task-breakdown`, `webapp-testing`
**Dependency:** Spec 5 (chat API), Spec 6 (wiki API)

**Cover:**

**api/ layer** (HTTP calls only, no state):
- `frontend/src/api/client.ts` — base client: auth header, X-Correlation-ID, error handling
- `frontend/src/api/chat.ts` — streamChat() (SSE), getChatHistory()
- `frontend/src/api/wiki.ts` — getEntities(), getEntity(), searchEntities()
- `frontend/src/api/admin.ts` — getNasQueue(), approveFile(), getFolders(), getDocuments()

**hooks/ layer** (state + logic):
- `useAuth.ts` — login, logout, current user (wrap AuthContext)
- `useChat.ts` — SSE stream, send message, conversation state
- `useConversation.ts` — load history, pagination
- `useWikiCategories.ts` — list entity types + counts
- `useWikiEntity.ts` — fetch 1 entity + relations + sources
- `useWikiSearch.ts` — search entity by name
- `useNasQueue.ts` — pending files, approve, reject
- `useDocuments.ts` — indexed docs, reindex, delete
- `useFolders.ts` — NAS folder CRUD

**Chat UI** (`routes/chat/`):
- Streaming token display (append on SSE message)
- Citation chips: document (link to file) + graph_entity (link to wiki page)
- Conversation history sidebar

**Wiki UI** (`routes/wiki/`):
- `index.tsx` — browse by entity category (PROJECT, EQUIPMENT, COMPONENT, PROCESS, ERROR_CODE)
- `[name].tsx` — entity page: description + relations panel + mini graph (vis.js) + source files
- "Hỏi AI về [entity]" button → pre-fill Chat UI

**Admin UI** (`routes/admin/`):
- `queue.tsx` — NAS approval queue: tên file, folder, size, approve/reject buttons
- `documents.tsx` — indexed docs table: status badge, re-index, delete
- `folders.tsx` — NAS folder config: add/remove, auto vs manual-review toggle

**Graph page** (`routes/graph.tsx`):
- iframe embed LightRAG Web UI (port 9621)

**Auth** (`routes/_protected.tsx`):
- Redirect /sign-in nếu chưa login
- Admin routes cần require_admin

**E2E test** (webapp-testing skill):
- Playwright: login → chat query → verify citation appears
- Playwright: browse wiki → click entity → verify relations shown

**Verify (Definition of Done):**
- Chat UI stream tokens từng chữ
- Citation có thể click → mở file hoặc wiki page
- Wiki browse categories → entity page hiển thị đúng
- Admin approve flow end-to-end
- Playwright E2E tests pass

---

## Dependency Graph

```
Spec 1 (Infrastructure)
    └── Spec 2 (Backend Foundation)
            ├── Spec 3 (NAS Connector)
            │       └── Spec 4 (LightRAG Ingestion)
            │               ├── Spec 5 (Chat API)
            │               │       ├── Spec 7 (MCP Server)
            │               │       └── Spec 9 (Frontend)
            │               └── Spec 6 (Wiki Engine)
            │                       ├── Spec 7 (MCP Server)
            │                       └── Spec 9 (Frontend)
            └── Spec 8 (Graphiti Service) ← có thể làm song song Spec 3
```

---

## Skill Matrix

| Spec | fastapi-expert | task-breakdown | quality-assurance | mcp-builder | frontend-design | webapp-testing |
|---|---|---|---|---|---|---|
| 1 Infrastructure | | ✅ | | | | |
| 2 Backend Foundation | ✅ | ✅ | ✅ | | | |
| 3 NAS Connector | | ✅ | ✅ | | | |
| 4 LightRAG Integration | ✅ | ✅ | | | | |
| 5 Chat API | ✅ | ✅ | ✅ | | | |
| 6 Wiki Engine | ✅ | ✅ | | | | |
| 7 MCP Server | | ✅ | | ✅ | | |
| 8 Graphiti Service | | ✅ | ✅ | | | |
| 9 Frontend | | ✅ | | | ✅ | ✅ |
