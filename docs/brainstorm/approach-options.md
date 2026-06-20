# SecondBrain — 4 Phương Án Tiếp Cận

> Tài liệu brainstorming — chưa chốt. Cập nhật lần cuối: 2026-06-15

---

## Bối cảnh chung

| Yếu tố | Chi tiết |
|---|---|
| Mục tiêu | Web app lưu tài liệu doanh nghiệp từ NAS, tạo graph/node, cho nhân viên chat hỏi đáp với AI, **và tự động làm giàu knowledge graph từ các cuộc hội thoại** |
| Quy mô | ~20 người, tất cả đều truy cập tất cả tài liệu |
| Input (MVP) | Word, PDF, Excel, PPT từ NAS |
| Input (tương lai) | Video, PNG, DWG/DWT — để sau |
| NAS sync | Một số thư mục tự động, một số admin duyệt trước |
| AI interface | Nhân viên chat trực tiếp trên web UI của SecondBrain |
| Ngân sách vận hành | Rẻ hoặc free |
| Server | Chưa có — tương lai mua PC ~50 triệu VND |
| Ưu tiên | Deliver cho công ty dùng thực tế |

---

## So sánh nhanh 4 phương án

| | PA1 Fork Arkon | PA2 Tự build dần | PA3 LightRAG v1.5 | PA4 4-Block Architecture |
|---|---|---|---|---|
| **Time to demo** | 3–4 tuần | 4–6 tuần | **3–4 tuần** | 8–12 tuần |
| **Chất lượng retrieval** | ✅✅✅ Cao ngay | 🔶 70–80% → ✅✅✅ | ✅✅✅ Cao ngay | ✅✅✅ Cao nhất |
| **Graph search** | ✅✅ pgvector wiki | ❌ → ✅✅ phase 2 | ✅✅✅ LightRAG mix | ✅✅✅ Dual storage |
| **Conversation memory** | ❌ Không có | 🟡 Tự build | ✅ + Graphiti | ✅✅ Graphiti built-in PA4 |
| **Kiểm soát code** | 🟡 Wrapper only | ✅ 100% | ✅ 100% | ✅ 100% |
| **License tự do** | ❌ PolyForm | ✅ MIT | ✅ MIT | ✅ MIT |
| **Có thể productize** | ❌ Cần đàm phán | ✅ | ✅ | ✅ |
| **Multimodal sẵn** | 🟡 Roadmap Arkon | ❌ tự thêm | ✅ MinerU/Docling | ✅ tự thiết kế |
| **Web UI sẵn** | ✅ Arkon UI | ❌ tự build | ✅ LightRAG WebUI | ❌ tự build |
| **Học được nhiều** | 🟡 | ✅✅ | ✅✅ | ✅✅✅ |
| **Risk delivery** | Thấp | Trung bình | **Thấp** | Cao |
| **Chi phí vận hành** | $5–10/th → $0 | $5–10/th → $0 | $5–10/th → $0 | $5–10/th → $0 |

---

## Phương Án 1 — Fork Arkon + NAS Connector + Chat UI + Ollama

### Tóm tắt
Dùng Arkon làm core engine (đã hoạt động tốt), tự build thêm 2 module còn thiếu:
NAS Connector và Chat UI. Giai đoạn đầu dùng Gemini API, khi có server chuyển
sang Ollama hoàn toàn offline.

### Arkon là gì
Arkon ([github.com/nduckmink/arkon](https://github.com/nduckmink/arkon)) là Enterprise AI Knowledge Hub
do người Việt Nam phát triển (Nguyễn Đức Minh — Bitsness Technology), hiện ở v0.9.1,
988 stars, 233 forks. Đang active develop.

**Những gì Arkon đã làm sẵn:**
- MRP Pipeline: Map → Reduce → Plan-review → Refine → Verify → Commit
- Wiki browser 3 panel: page tree / content / backlinks & outlinks
- Knowledge graph visualization (interactive)
- Full-text + semantic search (pgvector)
- Version history + rollback mọi wiki page
- Draft proposal → editor review → approval workflow
- RBAC: Viewer / Contributor / Editor / Admin
- Pluggable LLM: Anthropic, Google Gemini, OpenAI
- Self-hosted qua Docker Compose
- Parse: PDF, DOCX, plain text, URL, embedded images

### Stack

```
┌─────────────────────────────────────────────┐
│              SecondBrain App                │
│                                             │
│  ┌──────────────┐    ┌────────────────────┐ │
│  │ NAS Connector│    │     Chat UI        │ │
│  │ (tự build)   │    │  (tự build)        │ │
│  │ SMB/WebDAV   │    │  React + shadcn/ui │ │
│  │ watcher      │    │  gọi Arkon API     │ │
│  └──────┬───────┘    └────────┬───────────┘ │
│         │ POST /api/upload    │ GET /search │
│  ┌──────▼────────────────────▼───────────┐  │
│  │           Arkon Core (fork)           │  │
│  │  MRP Pipeline · Wiki · Graph · Auth   │  │
│  │  FastAPI · PostgreSQL+pgvector        │  │
│  │  Redis · MinIO · Next.js              │  │
│  └──────────────────┬────────────────────┘  │
└─────────────────────┼──────────────────────┘
                      │
          ┌───────────▼──────────┐
          │  LLM (pluggable)     │
          │  GĐ1: Gemini Lite    │
          │  GĐ2: Ollama local   │
          └──────────────────────┘
```

### Workflow — Ingestion (đưa tài liệu vào)

```
[NAS]
  │
  ├─ Thư mục AUTO SYNC
  │     │
  │     ▼
  │  NAS Connector (poll mỗi 5 phút)
  │     │ phát hiện file mới/thay đổi
  │     ▼
  │  POST /api/upload → Arkon queue
  │     │
  │     ▼
  │  Arkon MRP Pipeline (background worker)
  │     ├─ Parse: pymupdf / python-docx / openpyxl
  │     ├─ Map: LLM phân tích từng chunk → topic/entity
  │     ├─ Reduce: tổng hợp → danh sách wiki page cần tạo/update
  │     ├─ Plan Review: admin xem plan (auto-approve hoặc manual)
  │     ├─ Write/Merge: LLM viết/merge wiki page
  │     ├─ Verify: LLM kiểm tra chất lượng output
  │     └─ Commit: lưu wiki + pgvector + graph
  │
  └─ Thư mục CẦN DUYỆT
        │
        ▼
     NAS Connector detect → notify admin qua UI
        │
        ▼
     Admin review trên Arkon UI → Approve / Reject
        │
        ▼ (nếu approved)
     Vào queue → MRP Pipeline như trên
```

### Workflow — Query (nhân viên hỏi)

```
Nhân viên gõ câu hỏi vào Chat UI
  │
  ▼
Chat UI gọi GET /api/search?q=... (Arkon REST API)
  │
  ▼
Arkon Query Engine:
  ├─ Embed câu hỏi → vector
  ├─ pgvector similarity search → top-k wiki chunks
  ├─ Graph traversal → context liên kết (backlinks, outlinks)
  └─ Merge + rerank kết quả
  │
  ▼
Chat UI nhận context → gọi LLM (Gemini/Ollama)
  │
  ▼
LLM sinh câu trả lời + cite nguồn (wiki page, tài liệu gốc)
  │
  ▼
Hiển thị cho nhân viên
```

### Tích hợp Ollama vào Arkon

```python
# Trong Arkon config — chỉ đổi env var
LLM_BASE_URL=http://server-ip:11434/v1
LLM_API_KEY=ollama   # Ollama không check key
LLM_MODEL=qwen2.5:14b
```

Ollama expose OpenAI-compatible API → Arkon dùng `openai` SDK, trỏ sang Ollama
là đủ. Không cần sửa logic Arkon.

### Timeline

```
Tuần 1:  Clone Arkon, deploy local, test MRP pipeline với file thật
Tuần 2:  Build NAS Connector (SMB/WebDAV watcher → Arkon upload API)
Tuần 3:  Build Chat UI (React → Arkon search API → LLM)
Tuần 4:  Test end-to-end, tune, deploy nội bộ
──────────────────────────────────────────────
→ Demo công ty dùng được: cuối tuần 4

Tháng 2: Auto-categorize, approval workflow, Excel/PPT ingestion
Khi có server: LLM_BASE_URL → Ollama, ingestion offline hoàn toàn
```

### Chi phí vận hành

| Giai đoạn | LLM | Embedding | Tổng/tháng |
|---|---|---|---|
| Chưa có server | Gemini Flash Lite | Gemini free tier | ~$5–10 |
| Có server (Ollama) | $0 | $0 (nomic local) | **$0** |

### Ưu điểm
- Nhanh nhất (3–4 tuần) để có sản phẩm dùng thực tế
- MRP pipeline, wiki merge, graph, version history — có hết ngay
- Tác giả người Việt, cộng đồng active, liên hệ được trực tiếp
- Đổi Gemini → Ollama chỉ 1 dòng config

### Nhược điểm
- License PolyForm — chỉ nội bộ, không bán/offer cho bên ngoài
- Phụ thuộc upstream v0.9.x đang thay đổi nhanh
- Cần đọc hiểu ~15k dòng trước khi customize sâu

### Phù hợp khi
- Ưu tiên deliver nhanh, công ty chỉ dùng nội bộ

---

## Phương Án 2 — Tự Build Simple RAG → Nâng Cấp Dần

### Tóm tắt
Build từ đầu, chia 2 phase. Phase 1 (4–6 tuần) Simple RAG dùng được ngay.
Phase 2 (tháng 3–5) nâng lên ngang Arkon với wiki engine và knowledge graph.

### Stack

```
┌─────────────────────────────────────────────┐
│              SecondBrain App                │
│                                             │
│  Frontend: React + shadcn/ui + Tailwind     │
│  ├── Chat UI        ├── Admin Panel         │
│  └── Document Browser                      │
│                                             │
│  Backend: FastAPI + Python                  │
│  ├── NAS Connector (SMB/WebDAV)             │
│  ├── Ingestion Pipeline                     │
│  │   ├── Parser: pymupdf, python-docx,      │
│  │   │          openpyxl, python-pptx       │
│  │   ├── Chunker (heading-aware)            │
│  │   └── Embedder → pgvector               │
│  ├── Retrieval: similarity search + rerank  │
│  └── Chat: LLM + context injection          │
│                                             │
│  PostgreSQL + pgvector · Redis · MinIO      │
└─────────────────────────────────────────────┘

LLM: Gemini Flash Lite → Ollama qwen2.5:14b
Embedding: nomic-embed-text (Ollama) hoặc Gemini text-embedding-004
```

### Workflow — Ingestion Phase 1 (Simple RAG)

```
[NAS]
  │
  ▼
NAS Connector (poll / event-based)
  ├─ Thư mục auto → queue thẳng vào pipeline
  └─ Thư mục cần duyệt → admin UI → approve → queue
  │
  ▼
Ingestion Worker (ARQ + Redis)
  ├─ Download file từ NAS về app server
  ├─ Parse:
  │   ├─ PDF      → pymupdf (text + layout)
  │   ├─ DOCX     → python-docx (giữ heading)
  │   ├─ XLSX     → openpyxl + pandas (table → text)
  │   └─ PPTX     → python-pptx (text từng slide)
  ├─ Chunk: cắt theo heading, giữ overlap 20%
  ├─ Embed: nomic-embed-text → float[]
  └─ Lưu:
      ├─ pgvector: chunk + embedding + metadata
      └─ MinIO: file gốc (để link trích dẫn)
```

### Workflow — Query Phase 1 (Simple RAG)

```
Nhân viên gõ câu hỏi → Chat UI
  │
  ▼
Backend: embed câu hỏi → vector
  │
  ▼
pgvector: cosine similarity search → top-5 chunks
  │
  ▼
Reranker (BGE reranker hoặc simple cross-encoder):
  └─ Loại bỏ chunk không liên quan, sắp xếp lại
  │
  ▼
Prompt Builder:
  └─ "Dựa vào các đoạn sau: [chunks]
      Trả lời câu hỏi: [question]
      Ghi rõ nguồn (tên file, trang)"
  │
  ▼
LLM (Gemini / Ollama) → câu trả lời + citation
  │
  ▼
Chat UI hiển thị + link đến file gốc trên MinIO
```

### Workflow — Ingestion Phase 2 (Wiki + Graph)

```
Tài liệu đã có trong pgvector
  │
  ▼
MRP-style Pipeline (tự viết, học từ Arkon):
  ├─ Map: LLM phân tích chunk → topic/entity/relation
  ├─ Reduce: gom → plan wiki page
  ├─ Plan Review: admin approve
  ├─ Write: LLM viết wiki page mới
  │         hoặc LLM merge wiki cũ + nội dung mới
  ├─ Verify: LLM kiểm tra chất lượng
  └─ Commit: lưu wiki + graph nodes/edges + version

Graph Builder:
  ├─ Entity: người, phòng ban, dự án, nhà cung cấp, quy trình
  ├─ Relation: A thuộc B, C quản lý D, X liên quan Y
  └─ Lưu: Apache Age (PostgreSQL extension) hoặc Neo4j
```

### Workflow — Query Phase 2 (Wiki + Graph)

```
Nhân viên hỏi → Chat UI
  │
  ▼
Query Engine:
  ├─ Vector path: similarity search chunks (simple queries)
  ├─ Graph path: entity lookup + traversal (relation queries)
  │   Ví dụ: "Dự án X liên quan nhà cung cấp nào?"
  │   → tìm node "Dự án X" → traverse edges → trả về liên kết
  └─ Hybrid: merge cả hai kết quả
  │
  ▼
Reranker + Prompt Builder → LLM → trả lời + cite wiki page + file gốc
```

### Timeline chi tiết

```
Tuần 1–2:  Setup, auth, DB schema, NAS connector
Tuần 3–4:  Parser + chunker + embedding pipeline
Tuần 5–6:  Chat UI + similarity search + LLM + citation
──────────────────────────────────────────────────────
→ Phase 1 demo: cuối tuần 6

Tháng 2:   Admin panel, approval workflow, document management UI
Tháng 3:   MRP-style wiki pipeline
Tháng 4:   Knowledge graph + Apache Age + graph visualization
Tháng 5:   Query router, reranker nâng cao, production hardening
──────────────────────────────────────────────────────
→ Phase 2 full: cuối tháng 5
```

### Ưu điểm
- Kiểm soát 100%, license tự do, có thể productize
- Phase 1 deliver giá trị trong 4–6 tuần
- Team hiểu sâu toàn bộ codebase

### Nhược điểm
- Phase 1 chỉ 70–80% (không có graph, wiki structure)
- Phase 2 tốn thời gian, gặp bug Arkon đã fix rồi
- Risk nếu team chưa có kinh nghiệm production

### Phù hợp khi
- Muốn kiểm soát hoàn toàn, có kế hoạch dài hạn productize

---

## Phương Án 3 — Tự Build, Dùng LightRAG v1.5 Làm Core Engine

### Tóm tắt
Deploy LightRAG v1.5 như một service độc lập (REST API + Web UI built-in), tự
build thêm NAS Connector và custom UI/workflow bên trên. LightRAG v1.5 đã có
sẵn phần lớn những gì cần — graph engine, vector store, reranker, document
parser, REST API, Web UI — nên team chỉ cần viết phần còn thiếu.
MIT License, kiểm soát 100%, có thể productize.

### LightRAG v1.5 là gì
LightRAG ([github.com/HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)):
- Nghiên cứu từ Đại học Hong Kong, paper EMNLP 2025
- **36.6k stars, 5.2k forks, MIT License** — community lớn nhất trong GraphRAG
- Dual-level search: Local (entity cụ thể) + Global (tổng quan) + Naive + Hybrid + Mix
- Knowledge graph tự động từ tài liệu — không cần cấu hình ontology thủ công
- **v1.5: Multimodal, REST API Server, Web UI, PostgreSQL all-in-one, Reranker built-in**
- Hỗ trợ Ollama native với role-specific LLM

### Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────┐
│             SecondBrain App Layer               │
│                                                 │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  NAS Connector  │  │   Custom UI (opt.)   │  │
│  │  (tự build)     │  │  React + shadcn/ui   │  │
│  │  SMB/WebDAV     │  │  (nếu cần UX riêng)  │  │
│  │  watcher        │  │                      │  │
│  └────────┬────────┘  └──────────┬───────────┘  │
│           │ POST /api/v1/docs     │ REST API     │
└───────────┼──────────────────────┼─────────────┘
            │                      │
┌───────────▼──────────────────────▼─────────────┐
│          LightRAG v1.5 Service                  │
│  (deploy như Docker service riêng)              │
│                                                 │
│  REST API Server (FastAPI built-in)             │
│  ├── POST /api/v1/docs          (ingest)        │
│  ├── POST /api/v1/query         (search)        │
│  ├── GET  /api/v1/graph/...     (graph data)    │
│  └── DELETE /api/v1/docs/{id}  (xóa tài liệu)  │
│                                                 │
│  Web UI built-in (lightrag_webui)              │
│  ├── Chat interface             (dùng luôn)     │
│  ├── Graph visualization        (dùng luôn)     │
│  ├── Document management        (dùng luôn)     │
│  └── Insert/query panel         (admin dùng)    │
│                                                 │
│  Document Processing Pipeline                  │
│  ├── MinerU / Docling parser   (PDF phức tạp)  │
│  ├── Native parser             (DOCX, XLSX...) │
│  └── VLM image analysis        (hình trong PDF)│
│                                                 │
│  Dual Storage (PostgreSQL all-in-one)          │
│  ├── KV Store  (LLM cache, chunk results)      │
│  ├── Vector Store (pgvector embeddings)        │
│  ├── Graph Store (knowledge graph)             │
│  └── Doc Status (trạng thái ingestion)         │
│                                                 │
│  Role-specific LLM (Ollama / Gemini)           │
│  ├── EXTRACT role: qwen2.5:14b  (entity NER)  │
│  ├── QUERY role: qwen2.5:7b     (chat)         │
│  ├── KEYWORDS role: qwen2.5:3b  (nhẹ, nhanh)  │
│  └── VLM role: llava:13b        (ảnh, future)  │
└─────────────────────────────────────────────────┘

Embedding: bge-m3 (multilingual, tiếng Việt tốt)
           hoặc nomic-embed-text (nhẹ hơn, CPU OK)
```

### LightRAG 5 Query Modes — Điểm đặc biệt nhất

```
local   — Tìm entity cụ thể + 1-hop neighbors trong graph
          → Dùng khi: "SOP quy trình X là gì?", "Thông số kỹ thuật Y?"

global  — Multi-hop graph traversal + relationship chains
          → Dùng khi: "Dự án X liên quan nhà cung cấp nào?"

naive   — Vector similarity search thuần túy (như RAG thường)
          → Nhanh nhất, đơn giản nhất

hybrid  — local + global song song → merge

mix ✅  — local + global + naive → merge → rerank
          → DEFAULT, kết quả tốt nhất, khuyến nghị dùng
```

### Role-specific LLM — Tối ưu chi phí với Ollama

```ini
# .env — mỗi task dùng model phù hợp

# EXTRACT: trích xuất entity khi ingestion — cần LLM mạnh nhất
LLM_BINDING=ollama
LLM_MODEL=qwen2.5:14b         # 10GB VRAM, chạy lúc ingestion

# QUERY: trả lời chat realtime — cần nhanh
QUERY_LLM_BINDING=ollama
QUERY_LLM_MODEL=qwen2.5:7b    # 5GB VRAM, ~25 tok/s

# KEYWORDS: trích keywords từ câu hỏi — task đơn giản
KEYWORDS_LLM_BINDING=ollama
KEYWORDS_LLM_MODEL=qwen2.5:3b  # 2GB VRAM, gần như instant

# VLM: phân tích ảnh trong tài liệu (tương lai)
VLM_LLM_BINDING=ollama
VLM_LLM_MODEL=llava:13b

# Tiếng Việt
SUMMARY_LANGUAGE=Vietnamese

# PostgreSQL all-in-one (thay vì file-based default)
KV_STORAGE=PGKVStorage
VECTOR_STORAGE=PGVectorStorage
GRAPH_STORAGE=PGGraphStorage
DOC_STATUS_STORAGE=PGDocStatusStorage
```

Với RTX 4060 Ti 16GB: chạy đồng thời qwen2.5:7b (chat) + qwen2.5:3b (keywords)
= ~7GB VRAM. Ingestion dùng qwen2.5:14b chạy background khi ít người dùng.

### Workflow — Ingestion

```
[NAS]
  │
  ├─ Thư mục AUTO SYNC
  │     ▼
  │  NAS Connector (poll mỗi 5 phút)
  │     │ detect file mới/thay đổi
  │     ▼
  │  POST /api/v1/docs (LightRAG REST API)
  │     │  {"file_path": "...", "metadata": {...}}
  │     ▼
  │  LightRAG Document Processing Pipeline
  │     ├─ Parser selection (theo file type):
  │     │   ├─ PDF thường     → Native parser
  │     │   ├─ PDF phức tạp   → MinerU parser (bảng, multi-col)
  │     │   ├─ DOCX/XLSX/PPTX → Native parser (built-in v1.5)
  │     │   └─ Ảnh trong PDF  → VLM analysis (LLaVA)
  │     ├─ Chunking (4 strategies: Fix/Recursive/Vector/Paragraph)
  │     ├─ Entity & Relation Extraction:
  │     │   └─ EXTRACT LLM (qwen2.5:14b) phân tích từng chunk:
  │     │       entities: [{name, type, description}]
  │     │       relations: [{src, tgt, rel_type, description}]
  │     ├─ Embedding (bge-m3) → pgvector
  │     └─ Graph upsert → PostgreSQL graph store
  │         (entity dedup, relation merge tự động)
  │
  └─ Thư mục CẦN DUYỆT
        ▼
     NAS Connector → notify admin qua SecondBrain UI
        ▼
     Admin approve trên LightRAG Web UI hoặc custom UI
        ▼ (approved)
     POST /api/v1/docs → pipeline như trên
```

### Workflow — Query (mix mode mặc định)

```
Nhân viên gõ câu hỏi → Chat UI (LightRAG Web UI hoặc custom)
  │
  ▼
POST /api/v1/query
  {"query": "Dự án X liên quan nhà cung cấp nào?", "mode": "mix"}
  │
  ▼
LightRAG Query Engine:
  │
  ├─ KEYWORDS LLM (qwen2.5:3b — nhanh):
  │   trích xuất low-level + high-level keywords từ câu hỏi
  │
  ├─ Chạy song song 3 luồng:
  │   │
  │   ├─ [local] entity lookup → 1-hop graph neighbors
  │   │          → subgraph context xung quanh entity
  │   │
  │   ├─ [global] relation traversal → multi-hop chains
  │   │           → relationship context rộng hơn
  │   │
  │   └─ [naive] vector similarity search → top-k chunks
  │
  ├─ Merge tất cả kết quả
  │
  ├─ BGE Reranker (built-in): score + sort → top context
  │
  └─ Prompt Builder:
      System: "Trả lời dựa trên context. Ghi nguồn rõ ràng."
      Context: [entities + relations + chunks]
      Question: [câu hỏi]
  │
  ▼
QUERY LLM (qwen2.5:7b): sinh câu trả lời + citations
  │
  ▼
Response: {answer, citations: [{file, page, chunk_id}]}
  │
  ▼
Chat UI: hiển thị câu trả lời + link file gốc có thể click
```

### Workflow — Admin

```
Admin vào LightRAG Web UI (port 9621 mặc định):
  │
  ├─ Document tab:
  │   ├─ Xem danh sách tài liệu đã index + status
  │   ├─ Upload thủ công thêm file
  │   ├─ Re-index file (khi file thay đổi)
  │   └─ Xóa file → graph tự rebuild tự động
  │
  ├─ Graph Explorer tab:
  │   ├─ Visualize toàn bộ knowledge graph
  │   ├─ Tìm entity theo tên
  │   ├─ Xem neighbors (ai/cái gì liên quan?)
  │   └─ Filter theo relationship type
  │
  └─ Query tab:
      └─ Test query trực tiếp với các mode khác nhau
         để tune chất lượng
```

### Tại sao Graphiti cho conversation memory — không phải LightRAG

Tính năng lưu hội thoại → knowledge graph cần **Graphiti** (standalone, không cần full Zep stack):

```
LightRAG giỏi:   tài liệu tĩnh, batch ingestion, document graph
Graphiti giỏi:   hội thoại realtime, incremental update, temporal graph

Workflow conversation memory với Graphiti:

Nhân viên hỏi: "Dự án Alpha dùng gì?"
AI trả lời: "Dự án Alpha dùng React, FastAPI, team Backend phụ trách"
    │
    ▼
Graphiti pipeline (chạy background sau mỗi chat):
    ├── Extract: entity [Dự án Alpha, React, FastAPI, team Backend]
    ├── Extract: relation [Alpha-dùng->React], [Alpha-phụ trách bởi->Backend]
    ├── Timestamp: 2026-06-15 10:32 (temporal — biết khi nào được nói)
    ├── Dedup: "Dự án Alpha" đã có trong graph → merge thêm edges mới
    └── Commit → knowledge graph chung (cùng graph với tài liệu NAS)

Lần sau hỏi: "Team Backend đang làm gì?"
    → Graph traversal: team Backend → [phụ trách] → Dự án Alpha, Beta, Gamma
    → Trả lời dù không có tài liệu nào ghi rõ điều này
```

**Graphiti standalone:**
```bash
pip install graphiti-core
# Dùng với Neo4j Community hoặc FalkorDB (nhẹ hơn)
# Không cần deploy full Zep stack
```



| Tính năng | LightRAG v1.5 có sẵn | Phải tự build |
|---|---|---|
| Graph engine | ✅ built-in | |
| Vector search | ✅ pgvector | |
| Reranker | ✅ BGE built-in | |
| REST API | ✅ FastAPI server | |
| Web UI (chat + graph + doc mgmt) | ✅ built-in | |
| PDF parser (phức tạp) | ✅ MinerU/Docling | |
| DOCX/XLSX/PPTX parser | ✅ Native parser | |
| Multimodal (ảnh trong PDF) | ✅ VLM pipeline | |
| Ollama integration | ✅ native | |
| Role-specific LLM | ✅ built-in | |
| PostgreSQL all-in-one | ✅ built-in | |
| Tiếng Việt (SUMMARY_LANGUAGE) | ✅ config | |
| Document deletion + graph rebuild | ✅ built-in | |
| **NAS Connector** | ❌ | ✅ tự build |
| **Admin approval workflow** | ❌ | ✅ tự build |
| **Custom branding/UI** | ❌ (nếu cần) | ✅ tự build |

### Config .env cơ bản

```ini
# LLM — Giai đoạn 1: Gemini Flash Lite
LLM_BINDING=gemini
LLM_MODEL=gemini-2.0-flash-lite
GEMINI_API_KEY=AIza...

# LLM — Giai đoạn 2: Ollama (đổi 3 dòng này)
# LLM_BINDING=ollama
# LLM_MODEL=qwen2.5:14b
# OLLAMA_HOST=http://server-ip:11434

# Embedding (dùng ngay từ đầu, CPU OK)
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=nomic-embed-text
# hoặc bge-m3 nếu muốn chất lượng cao hơn

# Tiếng Việt
SUMMARY_LANGUAGE=Vietnamese

# Storage — PostgreSQL all-in-one
KV_STORAGE=PGKVStorage
VECTOR_STORAGE=PGVectorStorage
GRAPH_STORAGE=PGGraphStorage
DOC_STATUS_STORAGE=PGDocStatusStorage
POSTGRES_URL=postgresql://user:pass@localhost:5432/lightrag
```

### Benchmark LightRAG vs các tool khác

| Metric | NaiveRAG | Microsoft GraphRAG | LightRAG |
|---|---|---|---|
| Comprehensiveness | 32–38% | 45–50% | **54–84%** |
| Diversity | 23–39% | 22–41% | **59–88%** |
| Overall | 32–43% | 45–50% | **49–85%** |
| Token cost | Thấp | **Rất cao** | Thấp |
| Ingestion speed | Nhanh | **Chậm** | Nhanh |

LightRAG thắng gần tuyệt đối về chất lượng, rẻ hơn Microsoft GraphRAG nhiều
lần về token cost.

### Timeline

```
Tuần 1:    Deploy LightRAG via Docker Compose
           Chạy thử với file thật, test các query mode
           Setup PostgreSQL all-in-one storage
Tuần 2:    Build NAS Connector (SMB/WebDAV → POST /api/v1/docs)
Tuần 3:    Tune config: SUMMARY_LANGUAGE, chunking strategy,
           role-specific LLM, reranker
Tuần 4:    Build admin approval UI (nếu cần thêm LightRAG Web UI)
           Test end-to-end với tài liệu thực của công ty
──────────────────────────────────────────────────────
→ Demo công ty dùng được: cuối tuần 4

Tháng 2:   NAS approval workflow hoàn chỉnh
           Custom chat UI (nếu cần branding riêng)
Khi có server: đổi LLM_BINDING=ollama, tất cả chạy offline
──────────────────────────────────────────────────────
→ Full product: tháng 2
```

### Chi phí vận hành

| Giai đoạn | LLM | Embedding | Tổng/tháng |
|---|---|---|---|
| Chưa có server | Gemini Flash Lite | nomic local (CPU) | ~$5–10 |
| Có server (Ollama) | $0 | $0 | **$0** |

### Ưu điểm
- LightRAG v1.5 **có sẵn Web UI + REST API + Graph viz + Reranker** — không phải
  tự build từ đầu như PA3 cũ mô tả
- MIT License — kiểm soát 100%, có thể productize
- Multimodal built-in (MinerU/Docling) — chuẩn bị sẵn cho roadmap DWG/video/ảnh
- Role-specific LLM — tối ưu chi phí và tốc độ cực tốt với Ollama
- 36k stars, active develop (commit hàng ngày), community lớn
- Timeline nhanh hơn PA3 cũ (~4 tuần vs 8 tuần) vì không tự build graph/UI
- Benchmark vượt trội so với NaiveRAG và ngang/hơn Microsoft GraphRAG

### Nhược điểm
- LightRAG Web UI mặc định có thể không match brand/UX của công ty → cần custom
- LightRAG recommend dùng qua REST API (không embed SDK) → thêm 1 service cần quản lý
- Ingestion tốn nhiều LLM call hơn naive RAG (entity extraction từng chunk)
  → Giai đoạn 1 dùng Gemini có thể tốn ~$0.5–2/tài liệu dày
- MinerU parser cần setup riêng nếu muốn dùng local (cloud có quota giới hạn)

### Phù hợp khi
- Muốn chất lượng graph search cao ngay từ tuần đầu
- Không muốn bị ràng buộc license (MIT)
- Có kế hoạch productize hoặc mở rộng sau
- Muốn tận dụng tối đa ecosystem LightRAG (VideoRAG, RAG-Anything...)

---

## Phương Án 4 — Kiến Trúc 4-Block (Full Custom, Production-Grade)

### Tóm tắt
Thiết kế kiến trúc tách biệt rõ ràng thành 4 block độc lập: Ingestion Pipeline,
Dual Storage (Vector + Graph tách riêng), AI Query Engine có Router thông minh,
và API + UI đầy đủ. Đây là kiến trúc production-grade nhất, linh hoạt nhất để
mở rộng về sau (video, OCR, multi-modal). Phù hợp nếu team muốn build đúng từ
đầu và chấp nhận timeline dài hơn.

### Kiến trúc tổng quan

```
┌──────────────────────────────────────────────────────┐
│              Block A — Ingestion Pipeline            │
│                                                      │
│  [NAS]──►[File Parser]──►[Chunker]──►[Entity        │
│                                        Extractor]   │
│  PDF/DOCX/XLSX         Semantic split  NER: người,  │
│  PNG→OCR (future)      Metadata tag    công ty,     │
│  Video→transcript                      dự án        │
│  (future)                              Relation      │
│                              └──────►[Embedder]     │
│                                       bge-m3 /      │
│                                       nomic-embed   │
└──────────────────┬───────────────────────┬──────────┘
                   │ chunks + metadata      │ entities + relations
                   ▼                        ▼
┌──────────────────────────────────────────────────────┐
│              Block B — Dual Storage                  │
│                                                      │
│  ┌─────────────────────┐   ┌──────────────────────┐  │
│  │    Vector Store      │   │  Knowledge Graph     │  │
│  │                      │   │  Store               │  │
│  │  pgvector            │   │  Graphiti standalone │  │
│  │  (self-hosted,       │   │  (hoặc Neo4j CE)     │  │
│  │   trong PostgreSQL)  │   │                      │  │
│  │                      │   │  Entity nodes        │  │
│  │  → Semantic search   │   │  Relation edges      │  │
│  │  → "Hỏi gần đúng"   │   │  Multi-hop A→B→C    │  │
│  │  → Nhanh, đơn giản  │   │  Temporal (cập nhật │  │
│  │                      │   │  theo thời gian)    │  │
│  └─────────────────────┘   └──────────────────────┘  │
│              │  kết hợp = Hybrid Search   │           │
└──────────────┼────────────────────────────┼──────────┘
               │                            │
               ▼                            ▼
┌──────────────────────────────────────────────────────┐
│              Block C — AI Query Engine               │
│                                                      │
│  ┌──────────────┐  ┌──────────────────┐  ┌────────┐ │
│  │ Query Router │→ │Retriever+Reranker│→ │Prompt  │ │
│  │              │  │                  │  │Builder │ │
│  │ Phân loại:   │  │ Top-k chunks     │  │        │ │
│  │ → Vector     │  │ BGE reranker     │  │Context │ │
│  │ → Graph      │  │ Subgraph context │  │+ query │ │
│  │ → Hybrid     │  │ Score + merge    │  │→ LLM   │ │
│  └──────────────┘  └──────────────────┘  └────────┘ │
└──────────────────────────────┬───────────────────────┘
                               │
               ┌───────────────▼──────────────┐
               │      LLM (pluggable)          │
               │  GĐ1: Gemini Flash Lite API   │
               │  GĐ2: Ollama qwen2.5:14b      │
               └───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────┐
│           Block D — API Surface + UI                 │
│                                                      │
│  ┌──────────┐ ┌─────────────┐ ┌──────────┐ ┌──────┐ │
│  │REST/MCP  │ │Doc Manager  │ │  Graph   │ │Chat  │ │
│  │  API     │ │    UI       │ │ Explorer │ │  UI  │ │
│  │          │ │             │ │          │ │      │ │
│  │FastAPI   │ │Upload/view  │ │Visualize │ │Hỏi   │ │
│  │Auth,     │ │Tag, folder  │ │entity    │ │đáp,  │ │
│  │rate limit│ │version      │ │node/edge │ │cite  │ │
│  └──────────┘ └─────────────┘ └──────────┘ └──────┘ │
└──────────────────────────────────────────────────────┘
```

### Stack chi tiết

| Block | Component | Tool |
|---|---|---|
| **A — Parser** | PDF | `pymupdf` + `LlamaParse` (PDF phức tạp) |
| | DOCX | `python-docx` + `mammoth` |
| | XLSX | `openpyxl` + `pandas` |
| | PPTX | `python-pptx` |
| | PNG/JPG (future) | `Tesseract OCR` + Vision LLM |
| | Video (future) | `Whisper` speech-to-text |
| **A — Chunker** | Semantic split | Heading-aware, 20% overlap |
| | Metadata tagger | file name, date, type, page |
| **A — Entity Extractor** | NER | LLM-based (Gemini/Ollama) |
| | Relation detection | Prompt: "extract entities and relations" |
| **A — Embedder** | Model | `bge-m3` (multilingual, tiếng Việt tốt) |
| | Fallback | `nomic-embed-text` (nhẹ hơn, CPU OK) |
| **B — Vector Store** | DB | PostgreSQL + `pgvector` |
| | Search | cosine similarity |
| **B — Graph Store** | Engine | `Graphiti` standalone (Zep's graph engine) |
| | Fallback | Neo4j Community Edition |
| | Query | Python API / Cypher |
| **C — Router** | LLM-based | phân loại câu hỏi → path |
| | Rule-based (MVP) | keyword detection (nhanh hơn, đủ cho MVP) |
| **C — Reranker** | Model | `bge-reranker-v2-m3` (Ollama hoặc API) |
| **C — LLM** | GĐ1 | Gemini Flash Lite |
| | GĐ2 | Ollama `qwen2.5:14b` |
| **D — Backend** | API | FastAPI + Python |
| | Queue | ARQ + Redis |
| | Storage | MinIO (file gốc) |
| **D — Frontend** | Framework | React + Next.js + shadcn/ui |
| | Graph viz | `vis.js` hoặc `D3.js` |
| | Chat UI | Custom hoặc embed Open WebUI |

### Workflow — Ingestion

```
[NAS]
  │
  ▼
NAS Connector (SMB/WebDAV watcher + poll)
  ├─ Auto-sync folder → queue thẳng vào pipeline
  └─ Manual-review folder → notify admin → approve → queue
  │
  ▼
[Block A] Ingestion Pipeline (ARQ worker)
  │
  ├─ Step 1: File Parser
  │   ├─ Detect file type
  │   ├─ PDF thường → pymupdf (extract text + layout)
  │   ├─ PDF phức tạp (nhiều bảng) → LlamaParse free tier
  │   ├─ DOCX → python-docx (giữ heading hierarchy)
  │   ├─ XLSX → pandas (mỗi sheet = 1 table → text)
  │   └─ PPTX → python-pptx (text từng slide có title)
  │
  ├─ Step 2: Chunker
  │   ├─ Cắt theo heading structure (H1 → H2 → H3)
  │   ├─ Max 512 tokens/chunk, overlap 20%
  │   └─ Tag metadata: {file, page, heading, date, type}
  │
  ├─ Step 3: Entity Extractor
  │   ├─ Prompt LLM: "Extract entities (person, org, project,
  │   │   process, location) and their relations from:"
  │   ├─ Output: [{entity, type, relations: [{target, rel_type}]}]
  │   └─ Deduplicate + normalize entity names
  │
  ├─ Step 4: Embedder
  │   ├─ Embed mỗi chunk → float[] (bge-m3 hoặc nomic-embed-text)
  │   └─ Lưu vào pgvector cùng metadata
  │
  └─ Step 5: Graph Builder
      ├─ Upsert entities vào Graphiti (node)
      ├─ Upsert relations (edge + timestamp)
      └─ Graphiti tự handle dedup + temporal update
```

### Workflow — Query (3 đường)

```
Nhân viên gõ câu hỏi → Chat UI → POST /api/chat
  │
  ▼
[Block C] Query Router:
  │
  ├─ Phân tích câu hỏi (rule-based cho MVP, LLM cho production):
  │   ├─ Câu hỏi về nội dung cụ thể trong tài liệu?
  │   │   → VECTOR PATH
  │   ├─ Câu hỏi về quan hệ giữa entities?
  │   │   (dự án X, nhà cung cấp nào, ai phụ trách...)
  │   │   → GRAPH PATH
  │   └─ Câu hỏi phức tạp / không rõ?
  │       → HYBRID PATH
  │
  ├─ VECTOR PATH:
  │   embed query → pgvector cosine search → top-10 chunks
  │   → BGE reranker → top-5
  │
  ├─ GRAPH PATH:
  │   extract entity từ query
  │   → Graphiti lookup node
  │   → traverse edges (1–3 hops)
  │   → lấy subgraph context
  │   → convert subgraph → text context
  │
  └─ HYBRID PATH:
      chạy song song Vector + Graph
      → merge results
      → BGE reranker score + merge → top-5
  │
  ▼
Prompt Builder:
  └─ System: "Bạn là trợ lý tài liệu doanh nghiệp. Chỉ trả lời
              dựa trên context được cung cấp."
     Context: [chunks + graph context]
     Question: [câu hỏi của user]
     Instruction: "Ghi rõ nguồn: tên file, trang, hoặc wiki page"
  │
  ▼
LLM (Gemini Flash Lite / Ollama qwen2.5:14b)
  │
  ▼
Response: câu trả lời + citations
  │
  ▼
Chat UI:
  ├─ Hiển thị câu trả lời (markdown)
  ├─ Citations có thể click → mở file gốc trên MinIO
  └─ "Xem graph liên quan" → mở Graph Explorer tại node đó
```

### Workflow — Admin

```
Admin đăng nhập → Admin Panel
  │
  ├─ Document Management:
  │   ├─ Xem danh sách file đã index (status, date, chunks)
  │   ├─ Xem queue đang chờ xử lý
  │   ├─ Approve/reject file từ NAS folder cần duyệt
  │   ├─ Re-index file (khi file thay đổi trên NAS)
  │   └─ Xóa file khỏi index
  │
  ├─ Graph Explorer:
  │   ├─ Visualize toàn bộ knowledge graph
  │   ├─ Tìm kiếm node theo tên entity
  │   ├─ Xem neighbors (ai liên quan đến entity này?)
  │   └─ Export subgraph
  │
  └─ NAS Connector Config:
      ├─ Thêm/xóa thư mục sync
      ├─ Set auto vs manual-review per folder
      └─ Xem sync log
```

### So sánh Graphiti vs Neo4j cho PA4

| | Graphiti (standalone) | Neo4j Community |
|---|---|---|
| Dễ setup | ✅ pip install graphiti-core | 🟡 Docker + config |
| RAM usage | Thấp | Cao (~2–4GB) |
| Temporal support | ✅ Built-in | 🟡 Phải tự implement |
| Query language | Python API | Cypher (cần học) |
| Scale | Đủ cho 20 người | Tốt hơn khi graph lớn |
| Recommendation | ✅ Dùng cho MVP | Nâng cấp khi cần |

### Tại sao tách Vector Store và Graph Store riêng (khác PA3)

PA3 dùng LightRAG gộp cả vector + graph vào 1 engine. PA4 tách riêng:

```
PA3: [LightRAG] = vector + graph (tất cả trong 1)
     ✅ Đơn giản hơn
     ❌ Ít kiểm soát từng layer
     ❌ Khó swap 1 component khi cần

PA4: [pgvector] + [Graphiti] tách biệt
     ✅ Swap từng component độc lập
     ✅ Scale từng layer riêng
     ✅ Debug rõ ràng hơn (biết bug ở layer nào)
     ❌ Phức tạp hơn khi setup
```

### Timeline

```
Tuần 1–2:  Setup toàn bộ infrastructure (DB, Redis, MinIO, Graphiti)
Tuần 3–4:  Block A — Parser + Chunker + Embedder → pgvector
Tuần 5–6:  Block A — Entity Extractor → Graphiti graph builder
Tuần 7–8:  Block C — Hybrid search (Vector + Graph) + Reranker
Tuần 9–10: Block D — Chat UI + Doc Manager UI
Tuần 11–12: Block D — Graph Explorer (vis.js) + Admin Panel
──────────────────────────────────────────────────────────
→ MVP đủ 4 block: cuối tuần 12

Tháng 4:   Query Router thông minh (LLM-based)
Tháng 4:   MRP-style wiki pipeline
Tháng 5:   NAS approval workflow, production hardening
Khi có server: Ollama qwen2.5:14b, bge-m3 local
──────────────────────────────────────────────────────────
→ Production ready: tháng 5
```

### Chi phí vận hành

Giống PA1–PA3: ~$5–10/tháng giai đoạn đầu, $0 khi có Ollama server.

### Ưu điểm
- Kiến trúc rõ ràng nhất, dễ mở rộng từng block độc lập
- Thiết kế sẵn cho multi-modal (video, OCR) — chỉ cần thêm parser
- Vector + Graph tách biệt → debug, optimize, swap dễ
- License hoàn toàn tự do, có thể productize
- Graph Explorer UI trực quan như Obsidian Canvas
- Graphiti temporal: tài liệu cập nhật → graph tự phản ánh thay đổi

### Nhược điểm
- Chậm nhất trong 4 PA (8–12 tuần đến MVP)
- Phức tạp nhất — nhiều component, nhiều integration point
- Query Router LLM-based tốn thêm 1 LLM call/query (~2–5s latency)
- Team cần kinh nghiệm để không bị overwhelmed

### Phù hợp khi
- Team có đủ thời gian và kinh nghiệm
- Muốn kiến trúc chuẩn, dễ mở rộng dài hạn
- Có kế hoạch thêm multi-modal (video, OCR) sau MVP
- Muốn productize hoặc bán cho khách hàng khác

---

## Câu hỏi để chốt phương án

1. **License** — Công ty có kế hoạch bán/offer SecondBrain cho khách hàng khác?
   - Có → PA2, PA3, hoặc PA4
   - Không → PA1 OK

2. **Timeline** — Công ty cần demo trong bao lâu?
   - < 1 tháng → PA1 hoặc **PA3** (cả hai ~3–4 tuần)
   - 1–2 tháng → PA2
   - 2–3 tháng OK → PA4

3. **Chất lượng graph ngay từ đầu?**
   - Bắt buộc có graph từ tuần đầu → PA1, **PA3**, hoặc PA4
   - Simple RAG chấp nhận được → PA2

4. **Conversation memory quan trọng thế nào?**
   - Quan trọng, cần thiết kế sẵn từ đầu → **PA3 + Graphiti** hoặc **PA4**
   - Thêm sau cũng được → PA1, PA2

5. **Multi-modal tương lai có quan trọng không?**
   - Quan trọng, cần thiết kế sẵn → **PA3** (MinerU built-in) hoặc PA4
   - Thêm sau cũng được → PA1, PA2

6. **Muốn kiểm soát hoàn toàn + license tự do?**
   - Có → PA2, **PA3**, PA4
   - Không cần → PA1

7. **Team kinh nghiệm production?**
   - Chưa nhiều → PA1 hoặc **PA3** (ít code nhất phải tự viết)
   - Có kinh nghiệm → PA2, PA4

---

## Ghi chú kỹ thuật chung (áp dụng mọi PA)

### NAS Connector

```python
import smbprotocol   # SMB/CIFS NAS
import webdav4       # WebDAV NAS
import watchdog      # theo dõi thay đổi file

# Flow:
# 1. Poll thư mục NAS mỗi 5 phút (hoặc event-based nếu NAS hỗ trợ)
# 2. So sánh với danh sách đã index trong DB
# 3. File mới/thay đổi → queue ARQ → ingestion worker
# 4. Thư mục manual-review → notify admin → chờ approve
```

### LLM Strategy (2 giai đoạn)

```
Giai đoạn 1 — Chưa có GPU server:
  LLM: Gemini Flash Lite ($0.075/1M input, $0.30/1M output)
  Embedding: Gemini text-embedding-004 (free 1500 req/ngày)
  → 20 người dùng vừa phải: ~$5–10/tháng

Giai đoạn 2 — Có server RTX 4060 Ti 16GB:
  LLM: Ollama qwen2.5:14b (10GB VRAM, ~15–20 tok/s, $0)
  Embedding: nomic-embed-text hoặc bge-m3 local ($0)
  → Đổi 1–2 env var, không cần sửa code logic
```

### Server 50 triệu (khuyến nghị)

| Component | Lựa chọn | Giá ước tính |
|---|---|---|
| GPU | RTX 4060 Ti 16GB | 12–14 triệu |
| CPU | Ryzen 7 7700 / i7-13700 | 6–8 triệu |
| RAM | 64GB DDR5 | 5–6 triệu |
| SSD | 2TB NVMe | 3–4 triệu |
| HDD | 4TB (lưu tài liệu) | 2–3 triệu |
| Mainboard + PSU + Case | Mid-range | 7–9 triệu |
| **Tổng** | | **~35–44 triệu** |

### File Types

| Format | Thư viện | Ghi chú |
|---|---|---|
| PDF thường | `pymupdf` | Text + layout |
| PDF phức tạp | `LlamaParse` free tier | Bảng biểu, multi-column |
| DOCX/DOC | `python-docx` + `mammoth` | Giữ heading |
| XLSX/XLS | `openpyxl` + `xlrd` + `pandas` | Table → text |
| PPTX | `python-pptx` | Text từng slide |
| PNG/JPG (future) | Vision LLM / Tesseract | OCR |
| Video (future) | `Whisper` | Speech-to-text |
| DWG/DWT (future) | Convert → PDF trước | LibreCAD SDK |

---

*Tài liệu này sẽ được cập nhật khi có quyết định chốt phương án.*
