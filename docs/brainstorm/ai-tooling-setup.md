# SecondBrain — AI Tooling Setup

> Thiết kế cách dùng AI coding agents (Kiro, Claude Code, Codex, Windsurf, Cursor)
> để implement SecondBrain hiệu quả — đúng conventions, đúng kiến trúc, đúng từ đầu.
> Tài liệu này là output của brainstorm session 2026-06-15.

---

## 1. Nguyên tắc cốt lõi

### Single source of truth

Tất cả AI agents đều đọc từ **cùng 1 bộ rules**. Không viết riêng cho từng tool.

```
docs/ai-rules/                  ← SINGLE SOURCE OF TRUTH
    project-context.md          ← stack, ports, services, data flow
    backend-rules.md            ← Python conventions, folder structure
    frontend-rules.md           ← Component→Hook→api/ chain
    nas-rules.md                ← Synology SMB, NasFile state machine
    (future) git-workflow.md
    (future) test-rules.md

sync script → distribute sang format từng tool:
    .kiro/steering/*.md         ← Kiro
    CLAUDE.md                   ← Claude Code / Codex CLI
    .windsurfrules              ← Windsurf
    .cursorrules                ← Cursor
```

### Script sync (chạy mỗi khi sửa rules)

```bash
# scripts/sync-ai-rules.sh
#!/bin/bash

# Kiro steering — copy từng file
cp docs/ai-rules/project-context.md .kiro/steering/project-context.md
cp docs/ai-rules/backend-rules.md   .kiro/steering/backend-rules.md
cp docs/ai-rules/frontend-rules.md  .kiro/steering/frontend-rules.md
cp docs/ai-rules/nas-rules.md       .kiro/steering/nas-rules.md

# Claude Code / Codex — merge tất cả vào CLAUDE.md
cat docs/ai-rules/project-context.md \
    docs/ai-rules/backend-rules.md \
    docs/ai-rules/frontend-rules.md \
    docs/ai-rules/nas-rules.md \
    > CLAUDE.md

# Windsurf — same as CLAUDE.md
cp CLAUDE.md .windsurfrules

# Cursor — same
cp CLAUDE.md .cursorrules

echo "AI rules synced to all agents."
```

> Chạy: `bash scripts/sync-ai-rules.sh` sau mỗi lần sửa `docs/ai-rules/`

---

## 2. Project Context vs Code Graph — khi nào dùng gì

| | Project Context (steering) | Code Graph tool |
|---|---|---|
| **Khi nào hoạt động** | Ngay từ đầu — trước khi có code | Chỉ khi đã có codebase |
| **Biết gì** | Intent, conventions, trade-offs, *tại sao* | Dependency graph, call graph, *cái gì* |
| **Multi-agent** | ✅ Tất cả đều đọc được | 🟡 Mỗi tool có MCP riêng |
| **Maintain** | Thủ công khi architecture thay đổi | Tự động — luôn sync với code |
| **Token cost** | Thấp — chọn lọc được | Cao hơn — graph có thể lớn |

**Quyết định:**
- **Giai đoạn 1 (hiện tại → tháng 2):** Chỉ dùng Project Context steering files
- **Giai đoạn 2 (khi codebase đủ lớn):** Thêm code graph MCP — không thay thế steering

---

## 3. Steering Files — nội dung

### 3.1 `project-context.md`

File quan trọng nhất. Tóm gọn toàn bộ kiến trúc để AI luôn có context.

```markdown
# SecondBrain — Project Context

## Stack
- Backend: FastAPI (Python) — port 8000
- Frontend: React + Vite — port 3000
- LightRAG v1.5: graph+vector engine — port 9621
- Graphiti service: conversation memory — port 9622
- NAS Connector: Synology SMB watcher (background, no HTTP port)
- PostgreSQL 18 + pgvector + AGE — port 5432
- Redis — port 6379
- MinIO — port 9000
- Seq (logging) — port 80

## Core data flow
NAS (Synology SMB) → nas-connector → backend API → LightRAG ingestion
User chat → frontend → backend /api/chat/stream → LightRAG query (mode=mix)
           → Graphiti extract entities → knowledge graph grows over time

## Key decisions (không được thay đổi trừ khi có approval)
- ENABLE_LLM_CACHE=false — tài liệu cập nhật thường xuyên, cache cũ = sai
- LightRAG query mode=mix mặc định — không dùng naive, local, global riêng lẻ
- Component→Hook→api/ chain — component không import api/ trực tiếp
- nas-connector không lưu SQLite — single source of truth là backend PostgreSQL
- schemas/ = Pydantic (API shapes), models/ = SQLAlchemy (DB tables)
- services/ = business logic, integrations/ = external HTTP clients

## File naming conventions
- backend/schemas/chat.py — Pydantic request/response
- backend/models/conversation.py — SQLAlchemy ORM
- backend/services/auth_service.py — business logic
- backend/integrations/lightrag/query.py — HTTP client
```

### 3.2 `backend-rules.md`

```markdown
# Backend Rules — SecondBrain

## Folder structure rules
- schemas/ → Pydantic models only (request/response shapes)
- models/ → SQLAlchemy ORM models only (DB tables)
- services/ → business logic, KHÔNG import httpx/requests
- integrations/ → external HTTP clients, KHÔNG có business logic
- routers/ → thin layer: validate input → call service → return schema
- dependencies/ → FastAPI Depends functions only
- middleware/ → ASGI middleware only
- mcp/tools/public/ → MCP tools accessible by users
- mcp/tools/internal/ → MCP tools for internal services only

## Import rules
Router imports from: schemas/, services/, dependencies/
Service imports from: models/, repositories/ (if any)
Integration imports from: schemas/ (for request shapes), config
Router KHÔNG import from: integrations/ directly
Service KHÔNG import from: integrations/ directly
  → Inject integrations via dependencies/services.py

## Correlation ID
Every outbound HTTP call in integrations/ MUST forward X-Correlation-ID header.
backend/integrations/graphiti.py example:
  headers={"X-Correlation-ID": request.headers.get("X-Correlation-ID")}

## Error handling
All integrations/ functions must handle httpx.HTTPStatusError
Return typed schemas, never raw dicts from routers
```

### 3.3 `frontend-rules.md`

```markdown
# Frontend Rules — SecondBrain

## Data flow (BẮTBUỘC — không có ngoại lệ)
Component → Hook → api/ → Backend

## Rules
- Component KHÔNG import từ api/ trực tiếp
- Component KHÔNG gọi fetch() hay axios trực tiếp
- Hook chịu trách nhiệm: state, loading, error, retry, cache
- api/ chỉ export async functions, không có useState/useEffect
- routes/ page components dùng hooks, pass data xuống components qua props

## Hook naming
- use[Domain][Action].ts — ví dụ: useWikiEntity.ts, useNasQueue.ts
- Mỗi hook return: { data, loading, error, ...actions }

## Component props
- Component nhận data qua props, không tự fetch
- Event handlers (onApprove, onDelete...) được pass từ parent/hook

## Auth guard
- routes/_protected.tsx wrap tất cả authenticated routes
- admin/ routes cần thêm require_admin check
```

### 3.4 `nas-rules.md`

```markdown
# NAS Connector Rules — SecondBrain

## NAS setup
- Type: Synology NAS, LAN nội bộ
- Protocol: SMB mount (cifs)
- Mount: //NAS_HOST/NAS_SHARE → /mnt/synology (host OS)
- Docker volume: /mnt/synology:/mnt/nas:ro (read-only)
- User: dedicated 'secondbrain' account, read-only permissions

## File hash tracking
- nas-connector KHÔNG tự lưu SQLite
- Single source of truth: backend PostgreSQL, table NasFile
- Hash check: GET /api/internal/nas/hash?path=<nas_path>
- Hash update: POST /api/internal/nas/hash sau khi upload

## NasFile state machine
DETECTED → PENDING_REVIEW (manual folder) hoặc QUEUED (auto folder)
QUEUED → INDEXING → INDEXED hoặc FAILED
PENDING_REVIEW → QUEUED (khi admin approve) hoặc REJECTED

## Folder types
- auto: watcher phát hiện file mới → push thẳng vào ingestion queue
- manual: watcher phát hiện → notify admin → chờ approve trước khi index
```

---

## 4. Skills

### Skills đã có
- `brainstorming.md` — explore ideas trước khi implement

### Skills cần thêm

**`writing-plans.md`** — tạo implementation plan từ design doc
- Nguồn: [obra/superpowers/skills/writing-plans](https://github.com/obra/superpowers/tree/main/skills)
- Dùng khi: có design doc (như pa3-design.md) → cần break down thành task list tuần-by-tuần
- Cài vào: `.kiro/skills/writing-plans.md`

**`code-review.md`** — review code theo conventions project
- Tự viết ngắn (20–30 dòng) dựa trên backend-rules + frontend-rules
- Dùng khi: review PR, check conventions trước khi merge
- Cài vào: `.kiro/skills/code-review.md`

### Khi nào activate từng skill

| Việc cần làm | Skill dùng |
|---|---|
| Brainstorm tính năng mới | `/brainstorming` |
| Tạo task list từ design doc | `/writing-plans` |
| Review code trước merge | `/code-review` |
| Implement (không có skill riêng) | Dùng steering context + Kiro Spec |

---

## 5. MCP Tools

### Hiện tại cần: context7

**`context7`** ([upstash/context7](https://github.com/upstash/context7)) — tra cứu docs thư viện trực tiếp trong chat.

Tại sao cần: LightRAG v1.5 còn mới (ra 2025–2026), Graphiti cũng vậy. AI training data outdated — context7 lấy docs mới nhất từ GitHub/npm/PyPI.

```json
// .kiro/settings/mcp.json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

Dùng trong chat:
```
"Cách config LightRAG với PostgreSQL storage use context7"
"Graphiti episode ingestion API use context7"
```

### Giai đoạn 2 (tháng 2–3): Code Graph MCP

Khi codebase đủ lớn (~2000+ dòng), thêm code graph tool để AI navigate dependency.

Candidates:
- **`@modelcontextprotocol/server-code-graph`** — nếu available
- **`tree-sitter` based MCP** — parse Python/TypeScript AST, build call graph

Trigger để thêm: khi AI bắt đầu sửa sai file vì không biết dependency chain, hoặc khi team thường xuyên phải giải thích "file này import từ đâu".

---

## 6. Kiro Spec Workflow

Dùng **Spec session** (không phải Vibe session) cho các module lớn, độc lập.

### Module nào nên dùng Spec

| Module | Lý do |
|---|---|
| `nas-connector/` | Độc lập, có state machine rõ ràng (NasFile states) |
| `graphiti-service/` | Độc lập, interface rõ (POST /extract) |
| `backend/routers/chat` + streaming | Complex flow, nhiều edge case |
| `frontend/routes/wiki/` | UI phức tạp (entity page + mini graph) |

### Module nào dùng Vibe (chat thông thường)

| Module | Lý do |
|---|---|
| `backend/schemas/` | Đơn giản, chỉ viết Pydantic models |
| `backend/services/auth_service.py` | Standard JWT/bcrypt, không có gì đặc biệt |
| `backend/middleware/` | Boilerplate, follow FastAPI docs |
| `frontend/components/` nhỏ | UI components đơn giản |

### Spec workflow cho 1 module

```
1. Chat: "Tạo spec cho nas-connector module"
   → Kiro đọc pa3-design.md + nas-rules.md
   → Tạo requirements.md → design.md → tasks.md

2. Review tasks.md — check task granularity, dependencies

3. Implement từng task:
   → Kiro implement, bạn review
   → Task done → check off → next task

4. Sau khi xong module → chạy unit tests
```

---

## 7. Thứ tự setup

```
Ngay bây giờ (trước khi code):
  □ Tạo docs/ai-rules/ với 4 file
  □ Tạo scripts/sync-ai-rules.sh
  □ Chạy sync → .kiro/steering/, CLAUDE.md, .windsurfrules, .cursorrules
  □ Cài context7 MCP vào .kiro/settings/mcp.json
  □ Cài writing-plans skill

Khi bắt đầu implement (tuần 1):
  □ Dùng writing-plans skill → tạo task list từ pa3-design.md
  □ Dùng Spec session cho nas-connector

Khi codebase lớn dần (tháng 2–3):
  □ Đánh giá có cần code graph MCP không
  □ Tạo code-review skill nếu team có PR workflow
  □ Cập nhật docs/ai-rules/ khi architecture thay đổi → chạy sync script
```

---

## 8. Câu hỏi còn mở

1. **writing-plans skill** — cài từ obra/superpowers hay tự viết version đơn giản hơn?
   obra/superpowers version khá phức tạp (có visual companion, commit to git...).
   Với project này có thể tự viết 30 dòng là đủ.

2. **code-review skill** — nội dung cụ thể sẽ được viết khi có code thực tế để review.
   Placeholder: "review theo backend-rules và frontend-rules".

3. **Git workflow rules** — chưa quyết định nhưng nên thêm vào giai đoạn 2:
   branch naming (`feature/nas-connector`, `fix/chat-streaming`),
   commit style (conventional commits), không push thẳng main.

4. **Test rules** — thêm vào khi team bắt đầu viết test:
   pytest conventions, mock strategy, fixture patterns.

---

*Brainstorm session: 2026-06-15*
*Liên quan: pa3-design.md — Section 9 (Timeline), Section 15 (Test Strategy)*
