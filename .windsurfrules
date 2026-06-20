# SecondBrain — AI Agent Rules
# Auto-generated from .kiro/steering/ — DO NOT EDIT DIRECTLY
# Run scripts/sync-ai-rules.ps1 to regenerate
# Last synced: 2026-06-16 13:56


<!-- === project-context === -->

# SecondBrain — Project Context

> Auto-loaded context for AI coding agents. Reflects PA3 design decisions.

---

## 1. Project Overview

**SecondBrain** là bộ nhớ kỹ thuật của **Robolinks** — công ty tự động hóa ~20 người.
Middleware app lưu tài liệu từ Synology NAS, tạo knowledge graph, cho kỹ sư chat hỏi đáp với AI,
và tự động làm giàu graph từ hội thoại hàng ngày.

| Layer | Tech | Port |
|---|---|---|
| Frontend | React + Vite + shadcn/ui | 3000 |
| Backend (orchestrator) | Python FastAPI | 8000 |
| LightRAG v1.5 | Graph + Vector engine | 9621 |
| Graphiti service | Conversation memory | 9622 |
| NAS Connector | Python background service | — |
| PostgreSQL 18 + pgvector + AGE | All storage | 5432 |
| Redis | Queue + cache | 6379 |
| MinIO | File storage (NAS originals) | 9000 |
| Seq | Centralized logging | 80 |

**NAS:** Synology NAS, LAN nội bộ, SMB mount tại `/mnt/synology`

---

## 2. Core Data Flows

### Ingestion
```
Synology NAS (SMB) → nas-connector (detect change)
  → backend API (report + approve/queue)
  → LightRAG POST /api/v1/docs
  → LightRAG pipeline (parse → chunk → embed → graph)
```

### Chat Query
```
User → frontend Chat UI → backend POST /api/chat/stream (SSE)
  → LightRAG POST /api/v1/query (mode=mix)
  → LLM → streaming response + citations
  → [background] Graphiti POST /extract (conversation memory)
```

### Wiki Browse
```
User → frontend Wiki UI → backend GET /api/wiki/entity/:name
  → LightRAG GET /api/v1/graph/entity/:name
  → render entity page (description + relations + sources)
```

---

## 3. Key Decisions (KHÔNG thay đổi trừ khi có approval)

- **`ENABLE_LLM_CACHE=false`** — tài liệu Robolinks cập nhật thường xuyên, cache cũ = sai
- **LightRAG query `mode=mix` mặc định** — không dùng naive/local/global riêng lẻ
- **nas-connector KHÔNG lưu SQLite** — single source of truth là backend PostgreSQL (NasFile table)
- **`schemas/` = Pydantic only** — KHÔNG phải SQLAlchemy
- **`models/` = SQLAlchemy ORM only** — KHÔNG phải Pydantic
- **`services/` = business logic only** — KHÔNG import httpx/requests
- **`integrations/` = external HTTP clients only** — KHÔNG có business logic
- **Component → Hook → api/ chain** — frontend component KHÔNG import api/ trực tiếp
- **`mcp/tools/internal/`** = restricted, KHÔNG expose ra public

---

## 4. LLM Strategy (2 giai đoạn)

```
GĐ1 (chưa có server): Gemini Flash Lite API (~$5-10/tháng)
GĐ2 (có server 50tr RTX 4060 Ti 16GB):
  EXTRACT role: qwen2.5:14b (10GB VRAM)
  QUERY role:   qwen2.5:7b  (5GB VRAM, chat realtime)
  KEYWORDS role: qwen2.5:3b (2GB VRAM, near-instant)
Embedding: nomic-embed-text → bge-m3 khi có GPU
```

---

## 5. NAS File State Machine

```
DETECTED → PENDING_REVIEW (manual folder)
         → QUEUED (auto folder)
QUEUED → INDEXING → INDEXED | FAILED
PENDING_REVIEW → QUEUED (admin approve) | REJECTED
```

---

## 6. Correlation ID cho debug

Mọi HTTP request tạo UUID correlation_id, forward qua `X-Correlation-ID` header
đến LightRAG và Graphiti. Filter Seq bằng correlation_id để trace toàn bộ flow.

---

## 7. Scope rõ ràng

**IN SCOPE:** PDF, DOCX, XLSX, PPTX từ NAS; metadata của DWG/PNG/MP4; conversation memory
**OUT OF SCOPE:** OCR, video transcript, DWG content parsing → dự án riêng, kết nối MCP sau

<!-- === backend-rules === -->

# Backend Rules — SecondBrain

> Load khi làm việc với backend/ hoặc bất kỳ Python service nào.

---

## Folder Structure Rules (BẮTBUỘC)

| Folder | Chứa gì | KHÔNG chứa |
|---|---|---|
| `backend/schemas/` | Pydantic request/response models | SQLAlchemy models |
| `backend/models/` | SQLAlchemy ORM models (DB tables) | Pydantic models |
| `backend/services/` | Business logic thuần | httpx, requests, HTTP calls |
| `backend/integrations/` | External HTTP clients | Business logic |
| `backend/routers/` | Thin layer: validate → call service → return schema | Business logic |
| `backend/dependencies/` | FastAPI Depends functions only | — |
| `backend/middleware/` | ASGI middleware only | — |
| `backend/mcp/tools/` | Public MCP tools | Internal-only tools |
| `backend/mcp/tools/internal/` | Internal-only MCP tools | Public tools |
| `backend/migrations/` | Alembic migrations | — |

---

## Import Rules

```python
# Router imports from:
from backend.schemas.chat import ChatRequest, ChatResponse  # OK
from backend.services.auth_service import get_current_user  # OK
from backend.dependencies.auth import require_admin          # OK

# Router KHÔNG import from:
from backend.integrations.lightrag.query import ...  # KHÔNG — dùng DI
from backend.models.user import User                 # KHÔNG trực tiếp

# Service imports from:
from backend.models.nas_file import NasFile          # OK
from backend.schemas.nas import NasFileResponse      # OK

# Service KHÔNG import from:
import httpx                                         # KHÔNG trong services/
from backend.integrations.lightrag import ...        # KHÔNG — inject qua DI
```

---

## Pydantic V2 (FastAPI)

```python
# ĐÚNG — Pydantic V2 syntax
from pydantic import BaseModel, field_validator, model_config

class ChatRequest(BaseModel):
    model_config = model_config(str_strip_whitespace=True)
    message: str
    conversation_id: str | None = None  # Dùng X | None, KHÔNG Optional[X]

    @field_validator("message")         # KHÔNG @validator (V1)
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v

# ĐÚNG — response_model với from_attributes
class UserResponse(BaseModel):
    model_config = model_config(from_attributes=True)
    id: str
    email: str
```

---

## Async SQLAlchemy

```python
# ĐÚNG — always async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_nas_file(db: AsyncSession, file_id: str) -> NasFile | None:
    result = await db.execute(select(NasFile).where(NasFile.id == file_id))
    return result.scalar_one_or_none()

# KHÔNG dùng synchronous DB operations
```

---

## Correlation ID (BẮTBUỘC cho integrations/)

```python
# Trong backend/integrations/graphiti.py — luôn forward header
async def extract_from_conversation(
    turns: list[dict],
    correlation_id: str  # lấy từ request header
) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{GRAPHITI_URL}/extract",
            json={"turns": turns},
            headers={"X-Correlation-ID": correlation_id}  # BẮTBUỘC
        )
```

---

## Error Handling

```python
# Dùng HTTPException với detail rõ ràng
from fastapi import HTTPException, status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"NasFile not found: {file_id}"
)

# Integrations/ phải handle httpx errors
try:
    response = await client.post(...)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    logger.error(f"LightRAG error: {e.response.status_code}", correlation_id=cid)
    raise HTTPException(status_code=502, detail="LightRAG service error")
```

---

## Structured Logging

```python
# Luôn include correlation_id trong log
from backend.logger import logger

logger.info("Ingestion started", nas_path=nas_path, correlation_id=cid)
logger.error("LightRAG query failed", error=str(e), correlation_id=cid)
```

<!-- === frontend-rules === -->

# Frontend Rules — SecondBrain

> Load khi làm việc với frontend/ files.

---

## Data Flow Convention (BẮTBUỘC — không có ngoại lệ)

```
Component → Hook → api/ → Backend
```

### Rules
- **Component KHÔNG import từ `api/` trực tiếp**
- **Component KHÔNG gọi `fetch()` hay `axios` trực tiếp**
- **Hook** chịu trách nhiệm: state, loading, error, retry
- **`api/`** chỉ export async functions — KHÔNG có `useState`/`useEffect`
- **Route page** dùng hooks, pass data xuống components qua props

### Ví dụ ĐÚNG
```typescript
// hooks/useWikiEntity.ts
export function useWikiEntity(name: string) {
    const [data, setData] = useState<EntityResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        setLoading(true);
        wikiApi.getEntity(name)
            .then(setData)
            .catch(setError)
            .finally(() => setLoading(false));
    }, [name]);

    return { data, loading, error };
}

// components/wiki/WikiEntityCard.tsx
// NHẬN data qua props — KHÔNG tự fetch
interface WikiEntityCardProps {
    entity: EntityResponse;
    onNavigate: (name: string) => void;
}
export function WikiEntityCard({ entity, onNavigate }: WikiEntityCardProps) { ... }

// routes/wiki/[name].tsx
export function WikiEntityPage() {
    const { name } = useParams();
    const { data, loading, error } = useWikiEntity(name);  // OK — hook
    return <WikiEntityCard entity={data} onNavigate={...} />;
}
```

### Ví dụ SAI
```typescript
// SAI — component gọi api/ trực tiếp
import { getEntity } from '@/api/wiki';  // KHÔNG
export function WikiEntityCard({ name }) {
    const [data] = useState(() => getEntity(name));  // KHÔNG
}
```

---

## Hook Naming Convention

```
use[Domain][Action].ts

useChat.ts           ← SSE streaming, send message
useConversation.ts   ← load history, pagination
useWikiEntity.ts     ← fetch 1 entity + relations + sources
useWikiCategories.ts ← list entity types + counts
useWikiSearch.ts     ← search entity by name
useNasQueue.ts       ← pending files, approve, reject
useDocuments.ts      ← indexed docs, reindex, delete
useFolders.ts        ← NAS folder CRUD
useAuth.ts           ← wrap AuthContext
```

Hook return shape:
```typescript
return { data, loading, error, ...actions }
// Ví dụ: { files, loading, error, approve, reject }
```

---

## SSE Streaming (Chat UI)

```typescript
// hooks/useChat.ts — dùng EventSource cho SSE
const streamChat = (message: string, onToken: (token: string) => void) => {
    const es = new EventSource(
        `/api/chat/stream?message=${encodeURIComponent(message)}`
    );
    es.onmessage = (e) => {
        if (e.data === '[DONE]') { es.close(); return; }
        onToken(e.data);
    };
    es.onerror = () => es.close();
};
```

---

## Auth Guard

- `routes/_protected.tsx` wrap tất cả authenticated routes
- Admin routes cần thêm `require_admin` check
- `AuthContext.tsx` là single source of truth cho auth state
- Dùng `useAuth()` hook, KHÔNG access AuthContext trực tiếp

---

## Component Props Pattern

```typescript
// Props rõ ràng, không pass callback chưa cần thiết
interface NasFileQueueProps {
    files: NasFileResponse[];
    onApprove: (fileId: string) => Promise<void>;
    onReject: (fileId: string, reason: string) => Promise<void>;
    isLoading?: boolean;
}
```

---

## Styling

- Dùng **shadcn/ui** components làm base
- Tailwind utility classes
- Không dùng inline styles trừ khi cần dynamic values
- Responsive: mobile-first

<!-- === nas-rules === -->

# NAS Connector Rules — SecondBrain

> Load khi làm việc với nas-connector/ hoặc NAS-related backend code.

---

## NAS Setup

| Item | Value |
|---|---|
| Type | Synology NAS |
| Network | LAN nội bộ (cùng subnet với server) |
| Protocol | SMB/CIFS (port 445) |
| Host OS mount | `//NAS_IP/SHARE_NAME` → `/mnt/synology` |
| Docker volume | `/mnt/synology:/mnt/nas:ro` (read-only) |
| User | `secondbrain` — dedicated account, read-only permissions |

---

## Environment Variables

```ini
NAS_HOST=192.168.1.x        # IP Synology trên LAN
NAS_USER=secondbrain         # Dedicated user, NOT admin
NAS_PASS=...
NAS_SHARE=documents          # Synology Shared Folder name
NAS_MOUNT_PATH=/mnt/synology # Host OS mount point
BACKEND_API_URL=http://backend:8000
```

---

## Single Source of Truth (QUAN TRỌNG)

**nas-connector KHÔNG tự lưu file state.**
Mọi file hash tracking đều qua backend API:

```python
# ĐÚNG — gọi backend để check hash
async def file_changed(nas_path: str, current_hash: str) -> bool:
    resp = await httpx.get(
        f"{BACKEND_URL}/api/internal/nas/hash",
        params={"path": nas_path}
    )
    stored_hash = resp.json().get("hash")
    return stored_hash != current_hash

# SAI — KHÔNG lưu SQLite local
import sqlite3  # KHÔNG trong nas-connector
```

---

## NasFile State Machine

```
DETECTED
  ├── auto folder → QUEUED → backend triggers LightRAG ingestion
  └── manual folder → PENDING_REVIEW → admin approves → QUEUED

QUEUED → INDEXING → INDEXED (success)
                  → FAILED (error, có error_msg)

PENDING_REVIEW → QUEUED (admin approve)
               → REJECTED (admin reject, có reject_reason)
```

State transitions chỉ được thực hiện bởi **backend API** — nas-connector chỉ REPORT file mới, không tự chuyển state.

---

## Folder Types

```
auto-sync folder:
  nas-connector detect → POST /api/internal/nas/report → backend tự QUEUE

manual-review folder:
  nas-connector detect → POST /api/internal/nas/report → backend set PENDING_REVIEW
                      → backend notify admin → admin approve/reject qua UI
```

---

## SMB Mount (Host OS setup — chạy trước docker-compose)

```bash
# Tạo mount point
sudo mkdir -p /mnt/synology

# Mount Synology share
sudo mount -t cifs //NAS_IP/documents /mnt/synology \
  -o username=secondbrain,password=NAS_PASS,uid=1000,gid=1000,vers=3.0

# Auto-mount khi reboot — thêm vào /etc/fstab
//NAS_IP/documents /mnt/synology cifs username=secondbrain,password=NAS_PASS,uid=1000,gid=1000,vers=3.0 0 0
```

---

## File Change Detection

nas-connector so sánh hash của file để phát hiện thay đổi.
Poll interval: mỗi 5 phút.

```python
# Supported file types cho ingestion
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt'}

# Binary files — chỉ index metadata, không parse content
METADATA_ONLY_EXTENSIONS = {'.dwg', '.dxf', '.png', '.jpg', '.mp4', '.avi', '.step', '.stl'}
```

---

## Folder Path Convention (Important for AI context extraction)

LightRAG extract entity từ folder path — **convention này ảnh hưởng đến chất lượng AI**:

```
/projects/{ProjectName}-{Year}/{stage}/{type}/filename.ext

Ví dụ:
/projects/Heineken-BinhDuong-2024/design/electrical/DA-CB01-v3.dwg
/projects/Vinamilk-Line3-2023/documentation/SOP-vận-hành-CB01.pdf
/internal/HR/onboarding/quy-trinh-onboarding-2024.docx

→ AI infer: PROJECT=Heineken-BinhDuong-2024, STAGE=design, TYPE=electrical
```

Nếu NAS của Robolinks chưa theo convention này → note trong config để LightRAG adjust metadata extraction.

<!-- === lightrag-api === -->

# LightRAG API Reference — SecondBrain

> Load khi làm việc với backend/integrations/lightrag/ hoặc LightRAG config.

---

## Endpoints (LightRAG v1.5, port 9621)

### Ingest Document
```
POST /api/v1/docs
Content-Type: application/json

{
  "file_path": "/tmp/sop-onboarding.pdf",
  "metadata": {
    "source": "nas",
    "folder": "/auto-sync/HR/",
    "uploaded_by": "system",
    "nas_path": "/HR/SOP/sop-onboarding.pdf"
  }
}
→ { "id": "doc-uuid", "status": "processing" }
```

### Query Knowledge
```
POST /api/v1/query
Content-Type: application/json

{
  "query": "Dự án Heineken dùng motor gì?",
  "mode": "mix"  ← LUÔN dùng "mix" (default tốt nhất)
}
→ {
    "response": "...",
    "sources": [...],
    "context": {...}
  }
```

### Query với streaming
```python
# backend/integrations/lightrag/query.py
import httpx

async def query_stream(query: str, correlation_id: str):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{LIGHTRAG_URL}/api/v1/query/stream",
            json={"query": query, "mode": "mix"},
            headers={"X-Correlation-ID": correlation_id}
        ) as response:
            async for chunk in response.aiter_text():
                yield chunk
```

### Get Entity (Wiki)
```
GET /api/v1/graph/entity/{entity_name}
→ {
    "name": "Heineken Bình Dương 2024",
    "type": "PROJECT",
    "description": "...",
    "relations": [
      {"rel_type": "CLIENT_OF", "target": "Heineken Vietnam"},
      {"rel_type": "USES", "target": "Conveyor CB-01"}
    ],
    "sources": ["BOM-Heineken-2024.xlsx", "DA-CB01-v3.pdf"]
  }

GET /api/v1/graph/edges?entity={entity_name}
→ [{"src": "...", "rel_type": "...", "tgt": "...", "description": "..."}]
```

### Delete Document
```
DELETE /api/v1/docs/{doc_id}
→ { "status": "deleted" }
```

---

## Key Config (KHÔNG thay đổi)

```ini
ENABLE_LLM_CACHE=false       # BẮTBUỘC false — tài liệu cập nhật thường xuyên
SUMMARY_LANGUAGE=Vietnamese  # entity names bằng tiếng Việt
LIGHTRAG_PROMPT_DIR=./prompts  # custom extraction prompt cho Robolinks domain
```

---

## Query Modes

| Mode | Dùng khi | Tốc độ |
|---|---|---|
| `mix` ✅ DEFAULT | Mọi trường hợp — tốt nhất | ~1.5x naive |
| `local` | Entity lookup cụ thể | Fast |
| `global` | Tổng quan, trend analysis | Medium |
| `naive` | Vector search thuần — KHÔNG dùng cho production | Fastest |
| `hybrid` | local + global, không có naive | Medium |

**KHÔNG bao giờ hardcode mode khác `mix` trong production code trừ khi có lý do rõ ràng.**

---

## Parser Pipeline

```ini
LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
```

Thứ tự: Native → MinerU (cho PDF phức tạp) → Legacy fallback.
MinerU cloud có quota — nếu quota hết, Native vẫn chạy được cho DOCX/XLSX/PPTX.

---

## LightRAG integration code pattern

```python
# backend/integrations/lightrag/query.py
import httpx
from backend.config import settings

LIGHTRAG_URL = settings.LIGHTRAG_URL  # http://lightrag:9621

async def query(
    query_text: str,
    correlation_id: str,
    mode: str = "mix"  # luôn mix nếu không có lý do đặc biệt
) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{LIGHTRAG_URL}/api/v1/query",
                json={"query": query_text, "mode": mode},
                headers={
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise LightRAGError(f"Query failed: {e.response.status_code}")
        except httpx.TimeoutException:
            raise LightRAGError("LightRAG query timeout")
```

---

## LightRAG Docker image

```yaml
# docker-compose.yml — pin version, KHÔNG dùng :latest
lightrag:
  image: ghcr.io/hkuds/lightrag:v1.5.4
  env_file: ./lightrag/.env
  depends_on: [postgres, redis]
  ports: ["9621:9621"]
  volumes:
    - ./lightrag/storage:/app/storage
    - ./prompts:/app/prompts  # custom Robolinks extraction prompt
```

<!-- === graphiti-api === -->

# Graphiti Service API Reference — SecondBrain

> Load khi làm việc với graphiti-service/ hoặc backend/integrations/graphiti.py.

---

## Graphiti là gì

Graphiti xử lý **conversation memory** — extract entity/relation từ hội thoại,
lưu vào temporal graph (biết info được nói khi nào, mark edge "expired" nếu cũ).

**Khác LightRAG:** LightRAG xử lý tài liệu tĩnh. Graphiti xử lý hội thoại động.

---

## graphiti-service endpoints (port 9622)

### Extract từ conversation
```
POST /extract
Content-Type: application/json
X-Correlation-ID: {uuid}   ← BẮTBUỘC forward từ backend

{
  "conversation_id": "conv-uuid-123",
  "turns": [
    {"role": "user", "content": "Dự án Alpha dùng tech stack gì?"},
    {"role": "assistant", "content": "Dự án Alpha dùng React 18, FastAPI..."}
  ],
  "timestamp": "2026-06-15T10:32:00"
}
→ { "ok": true, "entities_added": 4, "relations_added": 2 }
```

### Get episode status
```
GET /episodes/{conversation_id}
→ { "conversation_id": "...", "synced": true, "entities": [...] }
```

---

## Khi nào trigger Graphiti

Graphiti chạy **background sau khi chat response đã trả về** — không blocking user.

```python
# backend/services/conversation_service.py

async def save_message_and_trigger_graphiti(
    db: AsyncSession,
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    correlation_id: str
) -> None:
    # 1. Lưu message vào DB
    message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_response,
        graphiti_synced=False  # chưa sync
    )
    db.add(message)
    await db.commit()

    # 2. Trigger Graphiti background (không await — fire and forget)
    asyncio.create_task(
        graphiti_client.extract(
            conversation_id=conversation_id,
            turns=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ],
            correlation_id=correlation_id
        )
    )
```

---

## Graphiti integration code pattern

```python
# backend/integrations/graphiti.py
import httpx
from backend.config import settings

GRAPHITI_URL = settings.GRAPHITI_URL  # http://graphiti-service:9622

async def extract(
    conversation_id: str,
    turns: list[dict],
    correlation_id: str  # BẮTBUỘC — để log trace được
) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{GRAPHITI_URL}/extract",
                json={
                    "conversation_id": conversation_id,
                    "turns": turns,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-Correlation-ID": correlation_id  # BẮTBUỘC forward
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Log nhưng không raise — Graphiti failure không block user
            logger.warning(
                "Graphiti extract failed",
                status=e.response.status_code,
                correlation_id=correlation_id
            )
            return {"ok": False}
        except Exception as e:
            logger.warning("Graphiti extract error", error=str(e))
            return {"ok": False}
```

---

## graphiti-service internal structure

```python
# graphiti-service/services/extractor.py
# Dùng graphiti-core để extract entity/relation từ chat turns

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

async def extract_from_turns(
    turns: list[dict],
    conversation_id: str,
    timestamp: str
) -> None:
    client = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    await client.add_episode(
        name=f"conversation-{conversation_id}",
        episode_body=format_turns_as_text(turns),
        source=EpisodeType.text,
        source_description="SecondBrain chat conversation",
        reference_time=datetime.fromisoformat(timestamp)
    )
```

---

## Graphiti vs LightRAG — không lẫn lộn

| | LightRAG | Graphiti |
|---|---|---|
| Input | Tài liệu (PDF, DOCX...) | Hội thoại (chat turns) |
| Graph update | Batch khi ingest | Real-time sau mỗi chat |
| Temporal | Không | Có — biết khi nào info được nói |
| Port | 9621 | 9622 |
| Integration | `backend/integrations/lightrag/` | `backend/integrations/graphiti.py` |

---

## Docker setup

```yaml
# docker-compose.yml — pin version
graphiti-service:
  build: ./graphiti-service
  env_file: .env
  depends_on: [postgres]
  ports: ["9622:9622"]

# graphiti-service/requirements.txt
graphiti-core==0.4.2  # pin version — KHÔNG dùng >=
```

<!-- === test-conventions === -->

# Test Conventions — SecondBrain

> Load khi làm việc với tests/ hoặc conftest.py.

---

## Test Structure (3 tầng)

```
tests/
├── conftest.py              ← shared fixtures
├── unit/                    ← không cần Docker, chạy nhanh
│   ├── backend/
│   │   ├── test_schemas.py
│   │   ├── test_auth_service.py
│   │   ├── test_wiki_builder.py
│   │   ├── test_middleware.py
│   │   └── test_routers.py
│   ├── nas_connector/
│   │   └── test_watcher.py
│   └── graphiti_service/
│       └── test_extractor.py
├── integration/             ← cần PostgreSQL + Redis
│   └── docker-compose.test.yml
└── qa/
    └── questions.md         ← 20 câu hỏi đánh giá chất lượng AI
```

---

## Run commands

```bash
# Unit tests — không cần Docker
pytest tests/unit/ -v

# Nhanh — dừng ngay khi fail đầu tiên
pytest tests/unit/ -x -q

# Integration tests — cần PostgreSQL
docker compose -f tests/docker-compose.test.yml up -d
pytest tests/integration/ -v
docker compose -f tests/docker-compose.test.yml down

# Chạy 1 file cụ thể
pytest tests/unit/backend/test_schemas.py -v

# Chạy theo pattern
pytest tests/ -k "test_nas_file" -v
```

---

## conftest.py — shared fixtures

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

@pytest.fixture
def fake_user():
    return {"id": "test-user-id", "email": "test@robolinks.vn", "role": "user"}

@pytest.fixture
def fake_admin():
    return {"id": "admin-id", "email": "admin@robolinks.vn", "role": "admin"}

@pytest.fixture
def client(fake_user):
    """FastAPI TestClient với auth mock"""
    from backend.main import app
    from backend.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: fake_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def mock_lightrag_query(monkeypatch):
    """Mock LightRAG query — không cần LightRAG service"""
    mock = AsyncMock(return_value={
        "response": "Motor Siemens 1LE1 7.5kW",
        "sources": [{"file": "BOM-Heineken-2024.xlsx"}]
    })
    monkeypatch.setattr("backend.integrations.lightrag.query.query", mock)
    return mock

@pytest.fixture
def mock_graphiti(monkeypatch):
    """Mock Graphiti — không cần graphiti-service"""
    mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr("backend.integrations.graphiti.extract", mock)
    return mock
```

---

## Test naming convention

```python
# Pattern: test_{module}_{scenario}_{expected_outcome}

def test_nas_file_transitions_to_indexed_after_approval(): ...
def test_chat_router_returns_streaming_response(): ...
def test_wiki_builder_assembles_entity_page_with_relations(): ...
def test_auth_service_rejects_expired_token(): ...
def test_lightrag_client_forwards_correlation_id(): ...
```

---

## Unit test patterns

### Test schema validation
```python
# tests/unit/backend/test_schemas.py
import pytest
from pydantic import ValidationError
from backend.schemas.chat import ChatRequest

def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="", conversation_id=None)

def test_chat_request_strips_whitespace():
    req = ChatRequest(message="  Heineken dùng motor gì?  ")
    assert req.message == "Heineken dùng motor gì?"
```

### Test router với mock
```python
# tests/unit/backend/test_routers.py
def test_chat_returns_sse_content_type(client, mock_lightrag_query):
    response = client.post(
        "/api/chat/stream",
        json={"message": "Heineken dùng motor gì?"}
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

def test_admin_queue_requires_admin_role(client):
    # client fixture dùng fake_user (role="user"), không phải admin
    response = client.get("/api/admin/nas/queue")
    assert response.status_code == 403
```

### Test NAS connector với fake filesystem
```python
# tests/unit/nas_connector/test_watcher.py
import pytest
from pathlib import Path
from nas_connector.watcher import detect_new_files

def test_watcher_detects_new_pdf(tmp_path):
    # tmp_path là pytest fixture — tạo thư mục tạm, tự xóa sau test
    (tmp_path / "SOP-onboarding.pdf").write_bytes(b"fake pdf content")

    known_files = {}  # chưa có file nào được track
    new_files = detect_new_files(str(tmp_path), known_files)

    assert len(new_files) == 1
    assert new_files[0]["name"] == "SOP-onboarding.pdf"

def test_watcher_ignores_unsupported_extensions(tmp_path):
    (tmp_path / "drawing.dwg").write_bytes(b"cad data")
    (tmp_path / "report.pdf").write_bytes(b"pdf data")

    new_files = detect_new_files(str(tmp_path), {})
    names = [f["name"] for f in new_files]

    assert "report.pdf" in names
    assert "drawing.dwg" not in names  # DWG → metadata only, handled separately
```

---

## Integration test pattern

```python
# tests/integration/backend/test_models.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest_asyncio.fixture
async def db_session():
    # Dùng DB test riêng (docker-compose.test.yml)
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/secondbrain_test")
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_nas_file_crud(db_session):
    from backend.models.nas_file import NasFile
    from backend.models.base import Base

    file = NasFile(
        nas_path="/projects/Heineken-2024/BOM.xlsx",
        folder_type="auto",
        status="QUEUED"
    )
    db_session.add(file)
    await db_session.commit()

    result = await db_session.get(NasFile, file.id)
    assert result.status == "QUEUED"
    assert result.nas_path == "/projects/Heineken-2024/BOM.xlsx"
```

---

## Coverage target

- `backend/schemas/` → 95%+
- `backend/services/` → 80%+
- `backend/integrations/` → 70%+ (với mock HTTP)
- `nas-connector/` → 70%+
- Overall unit → 80%+
