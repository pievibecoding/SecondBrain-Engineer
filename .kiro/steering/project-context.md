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
  → LightRAG POST /query (mode=mix)
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
