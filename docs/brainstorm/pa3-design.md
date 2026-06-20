# SecondBrain — Design Document (Phương Án 3)

> Phương án đã chốt: LightRAG v1.5 + Graphiti + NAS Connector
> Công ty: Robolinks — giải pháp kỹ thuật tự động hóa
> Tác giả: brainstorm session 2026-06-15
> Trạng thái: Draft — chưa đến bước implement

---

## 1. Tóm tắt quyết định

**Chọn PA3** vì:
- LightRAG v1.5 có sẵn REST API + Web UI + Graph viz + Reranker + Multimodal parser
- MIT License — kiểm soát 100%, có thể productize sau
- Graphiti xử lý conversation memory (temporal graph từ hội thoại)
- Timeline ~3–4 tuần đến demo, tương đương PA1 nhưng không bị ràng buộc license
- Ollama native support — đổi sang local LLM khi có server 50 triệu

---

## 2. Bối cảnh công ty — Robolinks

**Robolinks** là công ty cung cấp giải pháp kỹ thuật tự động hóa, bao gồm toàn bộ
vòng đời dự án: từ giao nhận → thiết kế → chế tạo → vận hành & bảo trì.

### Phạm vi tài liệu theo giai đoạn dự án

```
GIAO NHẬN DỰ ÁN
├── Hợp đồng, phụ lục hợp đồng (.docx, .pdf)
├── Báo giá, bảng tiên lượng (.xlsx, .pdf)
├── Yêu cầu kỹ thuật từ khách hàng — RFQ/RFP (.docx, .pdf)
├── Biên bản họp, biên bản nghiệm thu (.docx, .pdf)
└── Hồ sơ năng lực, catalog giải pháp (.pdf, .pptx)

THIẾT KẾ
├── Bản vẽ CAD/AutoCAD (.dwg, .dxf)
├── Model 3D SolidWorks (.sldprt, .sldasm, .step)
├── Sơ đồ điện, sơ đồ điều khiển (.dwg, .pdf)
├── Layout nhà máy, mặt bằng tổng thể (.dwg, .pdf)
├── BOM — Bill of Materials (.xlsx)
├── Thuyết minh thiết kế (.docx, .pdf)
└── Hình ảnh tham khảo, catalog thiết bị (.png, .jpg, .pdf)

CHẾ TẠO / THI CÔNG
├── Quy trình lắp ráp, hướng dẫn thi công (.docx, .pdf)
├── Checklist kiểm tra, biên bản FAT/SAT (.xlsx, .docx)
├── Nhật ký thi công (.docx, .xlsx)
├── Video máy tham khảo, video báo lỗi (.mp4, .avi)
├── Hình ảnh tiến độ, hình ảnh thiết bị (.jpg, .png)
└── Phiếu xuất kho, danh sách vật tư (.xlsx)

VẬN HÀNH & BẢO TRÌ
├── Hướng dẫn sử dụng (manual) (.pdf, .docx)
├── SOP vận hành từng máy (.docx, .pdf)
├── Lịch bảo trì định kỳ (.xlsx)
├── Troubleshooting guide — danh sách lỗi + xử lý (.docx, .xlsx)
├── Video hướng dẫn vận hành (.mp4)
└── Báo cáo bảo trì, lịch sử sự cố (.docx, .xlsx)

QUẢN LÝ NỘI BỘ
├── Quy định, quy trình nội bộ (.docx, .pdf)
├── HR: hợp đồng lao động, onboarding (.docx)
├── Tài chính: báo cáo, ngân sách dự án (.xlsx)
└── Đào tạo: slide training, tài liệu học (.pptx, .pdf)
```

### Loại câu hỏi nhân viên sẽ hỏi AI (tất cả đều quan trọng)

| Loại | Ví dụ câu hỏi thực tế |
|---|---|
| **Thông số kỹ thuật** | "Motor Siemens 1LE1 7.5kW dùng inverter nào?", "Tải trọng tối đa conveyor belt model X?" |
| **Quy trình** | "Quy trình FAT gồm những bước gì?", "Checklist lắp đặt tủ điện MCC?" |
| **Lịch sử dự án** | "Dự án nhà máy Heineken 2024 dùng giải pháp gì?", "Ai là kỹ sư thiết kế điện?" |
| **Troubleshooting** | "Lỗi F0011 trên Sinamics G120 là gì?", "Conveyor rung mạnh ở 60Hz xử lý thế nào?" |
| **Mua sắm** | "Nhà cung cấp encoder hiện tại là ai?", "Giá tham khảo sensor Sick WL12G?" |
| **Tìm file** | "Bản vẽ layout nhà máy Vinamilk Bình Dương ở đâu?", "Video lỗi conveyor dự án ABC?" |

### Yêu cầu xử lý theo loại file

| Loại file | Yêu cầu AI | Xử lý | Scope |
|---|---|---|---|
| PDF, DOCX, XLSX, PPTX | Hiểu nội dung đầy đủ | LightRAG MinerU/Docling parser | ✅ MVP |
| PDF/Word có hình kỹ thuật | Hiểu text + caption | VLM pipeline (LLaVA) | ✅ MVP (LightRAG built-in) |
| DWG, DXF, SolidWorks, STEP | Tìm được file + metadata | Index tên file + folder path context | ✅ MVP |
| PNG, JPG (thiết bị, tiến độ) | Tìm được file + metadata | Index tên file + folder context | ✅ MVP |
| MP4, AVI (video máy, lỗi) | Metadata + folder context | Index tên file + folder; transcript để sau | ✅ MVP (metadata only) |
| Scan PDF / ảnh chụp bản vẽ | — | **Không xử lý** — ngoài scope | ❌ Dự án khác |
| Video transcription (Whisper) | — | **Không xử lý** — ngoài scope | ❌ Dự án khác (kết nối MCP) |

> **Nguyên tắc scope:** SecondBrain xử lý file text-based và metadata của file binary.
> OCR, video transcript, DWG parsing sẽ là **dự án riêng**, kết nối vào SecondBrain qua MCP.

---

## 3. Mục tiêu sản phẩm

### Bài toán
Robolinks ~20 người, tài liệu phân tán trên NAS theo dự án và phòng ban:
- Kỹ sư mất thời gian tìm tài liệu cũ — "Lần trước dự án tương tự dùng giải pháp gì?"
- Troubleshooting phải nhớ hoặc hỏi đồng nghiệp — kiến thức không được tập trung
- Onboarding nhân viên mới chậm — không biết tài liệu ở đâu, quy trình ra sao
- Kiến thức kỹ thuật tích lũy theo năm tháng nhưng chỉ nằm trong đầu kỹ sư lâu năm

### Giải pháp
SecondBrain là **bộ nhớ kỹ thuật của Robolinks** với 2 nguồn tri thức:
1. **Tài liệu từ NAS** → parse → knowledge graph + vector index
2. **Hội thoại kỹ sư** → extract entity/relation → bổ sung graph tự động

Kết quả: AI hiểu ngữ cảnh kỹ thuật của Robolinks, trả lời được câu hỏi
liên kết nhiều tài liệu/dự án, và ngày càng thông minh hơn theo thời gian dùng.

### Success criteria (MVP)
- Kỹ sư hỏi bằng tiếng Việt → nhận câu trả lời có trích dẫn nguồn cụ thể
- "Dự án Heineken dùng motor gì?" → AI trả lời được từ BOM/hồ sơ thiết kế
- "Lỗi F0011 Sinamics G120" → AI trả lời từ troubleshooting guide
- "Bản vẽ layout nhà máy ABC ở đâu?" → AI trả lời đường dẫn file trên NAS
- Tài liệu mới trên NAS → tự động index trong vòng 10 phút
- Sau 2 tuần dùng → graph có thêm entities từ hội thoại kỹ sư

### Ngoài scope dự án này
- OCR scan PDF / ảnh chụp tài liệu → dự án riêng, kết nối MCP
- Video transcription (Whisper) → dự án riêng, kết nối MCP
- DWG/CAD content parsing → dự án riêng, kết nối MCP
- Mobile app

---

## 3. Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                         NAS                                     │
│  /auto-sync/    /manual-review/    /archive/                    │
└────────┬────────────────┬─────────────────────────────────────┘
         │                │
         ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  NAS Connector Service                          │
│  (Python — tự build)                                            │
│  ├── SMB/WebDAV watcher (poll mỗi 5 phút)                       │
│  ├── File change detection (so sánh với DB)                     │
│  ├── Auto folder → push thẳng vào LightRAG                      │
│  └── Manual folder → notify admin → chờ approve                │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /api/v1/docs
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               LightRAG v1.5 Service  (port 9621)                │
│                                                                 │
│  Document Processing Pipeline                                   │
│  ├── MinerU parser (PDF phức tạp, bảng, multi-column)           │
│  ├── Docling parser (DOCX, XLSX, PPTX)                          │
│  ├── Native parser (text, markdown)                             │
│  └── VLM (hình ảnh trong tài liệu — tương lai)                  │
│                                                                 │
│  Graph + Vector Engine                                          │
│  ├── Entity/Relation extraction (EXTRACT LLM)                   │
│  ├── Knowledge Graph (PostgreSQL graph storage)                 │
│  ├── Vector index (pgvector — bge-m3 embedding)                 │
│  └── 5 query modes: local/global/naive/hybrid/mix               │
│                                                                 │
│  REST API + Web UI built-in                                     │
│  ├── POST /api/v1/docs      (ingest)                            │
│  ├── POST /api/v1/query     (search)                            │
│  ├── GET  /api/v1/graph/... (graph data)                        │
│  └── lightrag_webui/        (graph explorer, doc mgmt)          │
└─────────────────────────────┬───────────────────────────────────┘
                              │ shared knowledge graph
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│               Graphiti Service  (conversation memory)           │
│  (Python standalone — pip install graphiti-core)                │
│                                                                 │
│  Sau mỗi cuộc hội thoại:                                        │
│  ├── Extract entity + relation từ chat history                  │
│  ├── Timestamp (temporal — biết info được nói lúc nào)          │
│  ├── Dedup + merge với graph hiện có                            │
│  ├── Mark edge "expired" nếu info cũ bị contradicted            │
│  └── Commit vào graph store (cùng PostgreSQL với LightRAG)      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│              SecondBrain App  (port 3000)                       │
│  (FastAPI + React — tự build)                                   │
│                                                                 │
│  Backend (FastAPI):                                             │
│  ├── Auth (JWT + bcrypt)                                        │
│  ├── NAS approval API (admin approve/reject file)               │
│  ├── Chat API (gọi LightRAG query + Graphiti memory)            │
│  ├── Conversation storage (lưu history, trigger Graphiti)       │
│  └── User management                                            │
│                                                                 │
│  Frontend (React + shadcn/ui):                                  │
│  ├── Chat UI (nhân viên hỏi đáp, xem citation)                  │
│  ├── Wiki UI (xem entity page, graph neighbors)                 │
│  ├── Admin panel (approve NAS files, monitor indexing)          │
│  └── Embed LightRAG Web UI (graph explorer, doc browser)        │
│                                                                 │
│  MCP Server (fastmcp — cùng process với backend):               │
│  ├── search_knowledge(query) → hybrid search kết quả            │
│  ├── get_entity(name) → entity + relations + sources            │
│  ├── list_documents(filter) → danh sách tài liệu đã index       │
│  └── get_document_context(nas_path) → context của 1 file        │
└─────────────────────────────────────────────────────────────────┘

Storage: PostgreSQL 18 + pgvector + Apache AGE (graph)
LLM GĐ1: Gemini Flash Lite API
LLM GĐ2: Ollama qwen2.5:14b (khi có server RTX 4060 Ti 16GB)
Embedding: bge-m3 (Ollama) hoặc nomic-embed-text
Queue: Redis + ARQ (background ingestion jobs)
File storage: MinIO (file gốc từ NAS)
```

---

## 4. Cấu trúc thư mục dự án

### Các vấn đề đã fix qua các phiên bản

| Vấn đề | Fix |
|---|---|
| SQLite vs PostgreSQL double tracking | `nas-connector` gọi backend API để check/update hash, không tự lưu SQLite |
| `episode_tracker` ranh giới mờ | Tách thành `repositories/episode_repo.py` (DB access) + `services/episode_tracker.py` (logic) |
| `push.py` quyền hạn không rõ | Tách vào `tools/internal/push.py` — visual phân biệt ngay |
| Frontend thiếu auth guard | Thêm `routes/_protected.tsx` wrapper enforce auth |
| `useAdmin` sẽ phình | Tách thành `useNasQueue`, `useDocuments`, `useFolders` |
| Thiếu `dependencies/` và `middleware/` | Thêm `backend/dependencies/` và `backend/middleware/` |
| `database/migrations/` tách khỏi backend | Chuyển vào `backend/migrations/` |
| Pydantic schemas lẫn ORM models | Tách `backend/schemas/` riêng cho request/response Pydantic models |
| `services/` trộn HTTP client với business logic | Tách `backend/integrations/` cho external HTTP clients |
| graphiti-service thiếu correlation_id trong log | `graphiti_client.py` luôn forward `X-Correlation-ID` khi gọi graphiti-service |

### Chiến lược debug multi-service

Mọi service đều ship structured log về **Seq** với `correlation_id`.
Mỗi HTTP request từ frontend → backend tạo UUID → forward qua header
`X-Correlation-ID` khi gọi LightRAG và Graphiti-service → tất cả log
cùng request có chung ID → filter 1 lần thấy toàn bộ flow.

### Cấu trúc

```
SecondBrain/
├── docker-compose.yml           ← production stack
├── docker-compose.dev.yml       ← override: hot reload, debug ports
├── .env.example                 ← template env cho toàn bộ stack
├── README.md
│
├── scripts/
│   ├── setup.sh                 ← first-time setup (tạo .env, pull images)
│   ├── re-embed.py              ← migration khi đổi embedding model
│   ├── seed-test-data.py        ← upload sample Robolinks files để test
│   └── backup-db.sh             ← backup PostgreSQL
│
├── prompts/                     ← LightRAG custom prompts (version controlled)
│   ├── extraction.txt           ← EXTRACT LLM prompt — Robolinks taxonomy
│   └── query.txt                ← QUERY LLM system prompt (optional)
│
├── lightrag/                    ← LightRAG v1.5 (Docker image)
│   ├── .env                     ← LightRAG config (LLM, embedding, storage, ENABLE_LLM_CACHE=false)
│   └── storage/                 ← working directory (gitignored)
│
├── nas-connector/               ← NAS watcher service
│   ├── main.py                  ← entry: start watcher + scheduler
│   ├── config.py                ← env (NAS IP, SMB credentials, share name, backend API URL)
│   ├── watcher.py               ← inotify/watchdog trên SMB mount, phát hiện file mới/thay đổi
│   ├── uploader.py              ← gọi backend API: report file + upload path
│   │                               (KHÔNG tự gọi LightRAG — backend quyết định)
│   ├── notifier.py              ← gọi backend API notify admin
│   ├── logger.py                ← structured log → Seq
│   └── requirements.txt
│   ─────────────────────────────
│   Synology NAS (LAN) → SMB mount vào Docker container
│   docker-compose: volumes: /mnt/synology:/mnt/nas:ro
│   Credentials: NAS_HOST, NAS_USER, NAS_PASS, NAS_SHARE trong .env
│   Single source of truth = backend PostgreSQL (NasFile table)
│
├── graphiti-service/            ← Conversation memory service
│   ├── main.py                  ← FastAPI entry
│   ├── config.py                ← env (Graphiti DB URL, Neo4j/FalkorDB)
│   ├── routers/
│   │   └── memory.py            ← POST /extract, GET /episodes/:id
│   ├── services/
│   │   ├── extractor.py         ← gọi LLM extract entity/relation từ chat turns
│   │   ├── graph_writer.py      ← upsert vào Graphiti graph (node + edge)
│   │   └── episode_tracker.py   ← logic: episode nào đã xử lý chưa?
│   ├── repositories/
│   │   └── episode_repo.py      ← DB access: lưu/đọc episode status
│   ├── models/
│   │   └── episode.py           ← Episode SQLAlchemy model
│   ├── logger.py                ← structured log → Seq
│   └── requirements.txt
│
├── backend/                     ← Main backend (orchestrator)
│   ├── main.py                  ← FastAPI app: mount routers + MCP + middleware
│   ├── config.py                ← Pydantic Settings
│   ├── database.py              ← SQLAlchemy async engine + get_session
│   ├── logger.py                ← structured log → Seq với correlation_id
│   │
│   ├── middleware/
│   │   ├── correlation.py       ← inject X-Correlation-ID vào mọi request/response
│   │   ├── logging.py           ← log mọi request/response tự động
│   │   └── rate_limit.py        ← rate limiting (đặc biệt cho /mcp endpoints)
│   │
│   ├── dependencies/
│   │   ├── auth.py              ← get_current_user, require_admin (FastAPI Depends)
│   │   └── services.py          ← inject integrations clients (DI)
│   │
│   ├── schemas/                 ← Pydantic request/response models (KHÔNG phải ORM)
│   │   ├── auth.py              ← LoginRequest, TokenResponse, UserResponse
│   │   ├── chat.py              ← ChatRequest, ChatResponse, CitationItem
│   │   ├── wiki.py              ← EntityResponse, WikiPageResponse, RelationItem
│   │   ├── nas.py               ← NasFileResponse, ApproveRequest, FolderRequest
│   │   └── mcp.py               ← MCP tool input/output schemas
│   │   ──────────────────────────
│   │   Phân biệt với models/:
│   │   models/ = SQLAlchemy ORM (DB tables)
│   │   schemas/ = Pydantic (API request/response shapes)
│   │
│   ├── routers/
│   │   ├── auth.py              ← POST /login, /register, GET /me
│   │   ├── chat.py              ← POST /chat/stream (SSE), GET /chat/history
│   │   ├── wiki.py              ← GET /wiki/entities, /wiki/entity/:name, /wiki/search
│   │   ├── admin/
│   │   │   ├── nas_queue.py     ← GET/POST /admin/nas/queue (approve/reject)
│   │   │   ├── nas_folders.py   ← CRUD /admin/nas/folders
│   │   │   └── documents.py     ← GET /admin/documents, re-index, delete
│   │   ├── internal/
│   │   │   └── nas.py           ← GET /api/internal/nas/hash (cho nas-connector)
│   │   │                           Bảo vệ bằng Docker network isolation
│   │   │                           (không expose port ra ngoài Docker network)
│   │   └── users.py             ← GET /admin/users (future)
│   │
│   ├── models/                  ← SQLAlchemy ORM models (DB tables)
│   │   ├── base.py              ← DeclarativeBase
│   │   ├── user.py              ← User (id, email, role, password_hash)
│   │   ├── conversation.py      ← Conversation + Message (+ graphiti_synced flag)
│   │   ├── nas_file.py          ← NasFile (nas_path, status, file_hash, lightrag_doc_id)
│   │   └── nas_folder.py        ← NasFolder (path, folder_type, is_active)
│   │
│   ├── services/                ← Business logic thuần (không gọi external HTTP)
│   │   ├── auth_service.py      ← JWT create/verify, bcrypt hash/verify
│   │   ├── conversation_service.py ← lưu history, trigger Graphiti sau chat
│   │   ├── wiki_builder.py      ← assemble wiki page từ graph data
│   │   └── nas_notify.py        ← in-app notification khi có file cần duyệt
│   │
│   ├── integrations/            ← External HTTP clients (giao tiếp service khác)
│   │   ├── lightrag/
│   │   │   ├── ingest.py        ← POST /api/v1/docs
│   │   │   ├── query.py         ← POST /api/v1/query (+ streaming adapter)
│   │   │   └── graph.py         ← GET /api/v1/graph/* (entity, neighbors, edges)
│   │   └── graphiti.py          ← POST /extract, luôn forward X-Correlation-ID
│   │                               header → graphiti-service log đúng trace
│   │   ──────────────────────────
│   │   Phân biệt với services/:
│   │   services/ = business logic, không biết về external services
│   │   integrations/ = HTTP adapters, biết URL/protocol của service khác
│   │
│   ├── mcp/
│   │   ├── server.py            ← FastMCP instance, mount tại /mcp
│   │   └── tools/
│   │       ├── search.py        ← search_knowledge (public)
│   │       ├── entity.py        ← get_entity (public)
│   │       ├── documents.py     ← list_documents, get_document_context (public)
│   │       └── internal/
│   │           └── push.py      ← push_knowledge (internal service token only)
│   │
│   ├── migrations/              ← Alembic migrations (cùng package với models)
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx              ← router setup
│   │   │
│   │   │   ══════════════════════════════════════════════
│   │   │   Data flow convention (bắt buộc):
│   │   │
│   │   │   Component → Hook → api/ → Backend
│   │   │
│   │   │   - Component KHÔNG import api/ trực tiếp
│   │   │   - Component KHÔNG gọi fetch()/axios trực tiếp
│   │   │   - Hook chịu trách nhiệm: state, loading, error, cache
│   │   │   - api/ chịu trách nhiệm: HTTP call, request/response shape
│   │   │   - Component chỉ nhận data và callback từ hook
│   │   │
│   │   │   Ví dụ đúng:
│   │   │     ChatInput.tsx → useChat() → api/chat.ts → POST /api/chat/stream
│   │   │
│   │   │   Ví dụ sai:
│   │   │     ChatInput.tsx → import { streamChat } from '@/api/chat' ← KHÔNG
│   │   │   ══════════════════════════════════════════════
│   │   │
│   │   ├── layouts/
│   │   │   ├── AppLayout.tsx    ← sidebar + topbar (authenticated)
│   │   │   └── AdminLayout.tsx  ← admin section layout
│   │   │
│   │   ├── routes/
│   │   │   ├── _protected.tsx   ← Auth guard: redirect /sign-in nếu chưa login
│   │   │   ├── sign-in.tsx
│   │   │   ├── chat/
│   │   │   │   └── index.tsx    ← dùng useChat(), useConversation()
│   │   │   ├── wiki/
│   │   │   │   ├── index.tsx    ← dùng useWikiCategories()
│   │   │   │   └── [name].tsx   ← dùng useWikiEntity(name)
│   │   │   ├── graph.tsx        ← LightRAG graph explorer (iframe embed)
│   │   │   └── admin/           ← _protected + require_admin
│   │   │       ├── queue.tsx    ← dùng useNasQueue()
│   │   │       ├── documents.tsx ← dùng useDocuments()
│   │   │       └── folders.tsx  ← dùng useFolders()
│   │   │
│   │   ├── components/
│   │   │   │   ── Nhận data qua props hoặc hook, KHÔNG gọi api/ trực tiếp ──
│   │   │   ├── chat/
│   │   │   │   ├── ChatMessage.tsx      ← props: message, citations
│   │   │   │   ├── ChatInput.tsx        ← props: onSubmit (từ useChat)
│   │   │   │   └── CitationCard.tsx     ← props: citation item
│   │   │   ├── wiki/
│   │   │   │   ├── WikiEntityCard.tsx   ← props: entity data
│   │   │   │   ├── RelationList.tsx     ← props: relations[]
│   │   │   │   └── RelationGraph.tsx    ← props: nodes[], edges[] (vis.js)
│   │   │   ├── admin/
│   │   │   │   ├── NasFileQueue.tsx     ← props: files[], onApprove, onReject
│   │   │   │   ├── DocumentTable.tsx    ← props: docs[], onReindex, onDelete
│   │   │   │   └── FolderConfig.tsx     ← props: folders[], onAdd, onDelete
│   │   │   └── ui/              ← shadcn/ui base components
│   │   │
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx  ← auth state, token, current user
│   │   │                           Exposed qua useAuth() hook
│   │   │
│   │   ├── hooks/               ← state + logic + gọi api/
│   │   │   │   ── Mỗi hook = 1 domain, return { data, loading, error, actions } ──
│   │   │   ├── useAuth.ts           ← login, logout, current user (wrap AuthContext)
│   │   │   ├── useChat.ts           ← SSE stream, send message, clear
│   │   │   ├── useConversation.ts   ← load history, pagination
│   │   │   ├── useWikiCategories.ts ← list entity types + counts
│   │   │   ├── useWikiEntity.ts     ← fetch 1 entity + relations + sources
│   │   │   ├── useWikiSearch.ts     ← search entity by name
│   │   │   ├── useNasQueue.ts       ← pending files, approve, reject
│   │   │   ├── useDocuments.ts      ← indexed docs, reindex, delete
│   │   │   └── useFolders.ts        ← NAS folder CRUD
│   │   │
│   │   └── api/                 ← HTTP calls only, không có state
│   │       │   ── Chỉ export async functions, không dùng useState/useEffect ──
│   │       ├── client.ts        ← base: auth header, correlation-id, error handling
│   │       ├── chat.ts          ← streamChat(), getChatHistory()
│   │       ├── wiki.ts          ← getEntities(), getEntity(), searchEntities()
│   │       └── admin.ts         ← getNasQueue(), approveFile(), getFolders()...
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                       ← pytest test suite
│   ├── conftest.py              ← shared fixtures (fake user, mock clients, test DB)
│   ├── unit/                    ← không cần Docker
│   │   ├── backend/
│   │   │   ├── test_schemas.py
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_wiki_builder.py
│   │   │   ├── test_middleware.py
│   │   │   └── test_routers.py  ← với dependency_overrides
│   │   ├── nas_connector/
│   │   │   └── test_watcher.py  ← với tmp_path fixture
│   │   └── graphiti_service/
│   │       └── test_extractor.py ← mock LLM
│   ├── integration/             ← cần PostgreSQL + Redis
│   │   ├── backend/
│   │   │   ├── test_models.py
│   │   │   └── test_conversation_service.py
│   │   └── nas_connector/
│   │       └── test_full_flow.py
│   ├── qa/
│   │   └── questions.md         ← bộ câu hỏi chuẩn để đánh giá chất lượng AI
│   └── docker-compose.test.yml  ← PostgreSQL + Redis cho integration test
│
└── docs/
    └── brainstorm/
        ├── pa3-design.md        ← file này
        ├── approach-options.md
        └── AI_RAG_Knowledge_Management_Tools_Comparison.md
```

### Debug workflow với Seq

```
Kỹ sư báo: "Hỏi câu về Heineken nhưng AI không trả lời được"

1. Mở Seq (http://server-ip:80)
2. Lấy correlation_id từ response header X-Correlation-ID của request đó
3. Filter Seq: correlation_id = "abc-123"
4. Thấy toàn bộ:

   [backend/chat]     POST /api/chat/stream — user: nguyen-van-a
   [backend/chat]     Gọi LightRAG query mode=mix, q="Heineken motor gì"
   [lightrag]         KEYWORDS LLM → ["Heineken", "motor", "thiết bị"]
   [lightrag]         Graph lookup: entity "Heineken Bình Dương 2024" → NOT FOUND
   [lightrag]         Vector search → 0 results
   [backend/chat]     Empty context → LLM: "Không tìm thấy thông tin"

→ Root cause: entity "Heineken Bình Dương 2024" chưa có trong graph
→ Filter thêm: service=backend, nas_path LIKE "%Heineken%"
   → NasFile: status=PENDING_REVIEW, created_at=2026-06-14
→ Admin chưa approve file → vào /admin/queue → approve → re-test
```

---

## 5. Workflows chi tiết

### 5.1 Workflow — Ingestion tài liệu từ NAS

```
[NAS Server]
    │
    ├── /auto-sync/ (thư mục tự động)
    │       │
    │       ▼
    │   NAS Connector polls mỗi 5 phút
    │       │ phát hiện file mới hoặc modified
    │       ▼
    │   Download file về /tmp/
    │       │
    │       ▼
    │   POST /api/v1/docs  (LightRAG REST API)
    │       {
    │         "file_path": "/tmp/sop-onboarding.pdf",
    │         "metadata": {
    │           "source": "nas",
    │           "folder": "/auto-sync/HR/",
    │           "uploaded_by": "system",
    │           "nas_path": "/HR/SOP/sop-onboarding.pdf"
    │         }
    │       }
    │       │
    │       ▼
    │   LightRAG Pipeline (background, ARQ queue):
    │       ├── Detect file type
    │       ├── Parse:
    │       │     PDF thường   → Native parser
    │       │     PDF phức tạp → MinerU (bảng, multi-column, scan)
    │       │     DOCX/PPTX    → Docling
    │       │     XLSX         → Docling → table → markdown text
    │       ├── Chunk (Paragraph strategy — giữ ngữ cảnh)
    │       ├── EXTRACT LLM (qwen2.5:14b / Gemini):
    │       │     "Extract all entities and relations:
    │       │      entities: [{name, type, description}]
    │       │      relations: [{src, rel_type, tgt, description}]"
    │       ├── Embed chunks → pgvector (bge-m3)
    │       ├── Upsert graph nodes/edges → PostgreSQL graph
    │       └── Update doc status → INDEXED
    │
    └── /manual-review/ (thư mục cần duyệt)
            │
            ▼
        NAS Connector phát hiện file mới
            │
            ▼
        INSERT vào backend DB: {file, status: PENDING_REVIEW}
            │
            ▼
        Notify admin qua SecondBrain UI (badge + notification)
            │
            ▼
        Admin review trên Admin Panel:
            ├── Xem preview file (tên, size, folder)
            ├── APPROVE → trigger POST /api/v1/docs → LightRAG pipeline
            └── REJECT  → xóa khỏi queue, log lý do
```

### 5.2 Workflow — Chat & Conversation Memory

```
Nhân viên mở Chat UI → gõ câu hỏi tiếng Việt
    │
    ▼
POST /api/chat  (SecondBrain backend)
    {
      "user_id": "nguyen-van-a",
      "message": "Dự án Alpha đang dùng tech stack gì?",
      "conversation_id": "conv-uuid-123"
    }
    │
    ▼
Backend:
    ├── Lấy conversation history (5 turns gần nhất) từ DB
    │
    ▼
POST /api/v1/query  (LightRAG)
    {
      "query": "Dự án Alpha tech stack",
      "mode": "mix",
      "conversation_history": [...]
    }
    │
    ▼
LightRAG Query Engine (mode=mix):
    │
    ├── KEYWORDS LLM (qwen2.5:3b — nhanh):
    │   trích keywords: ["Dự án Alpha", "tech stack", "framework"]
    │
    ├── [local] entity lookup "Dự án Alpha"
    │         → 1-hop: React, FastAPI, PostgreSQL, team Backend
    │
    ├── [global] relation traverse
    │         → Alpha -[dùng]-> React -[version]-> 18.x
    │         → Alpha -[phụ trách]-> team Backend -[gồm]-> Nguyễn Văn A
    │
    ├── [naive] vector search → top chunks từ tài liệu liên quan
    │
    └── BGE Reranker → top-5 context
    │
    ▼
QUERY LLM (qwen2.5:7b / Gemini Flash Lite):
    Prompt: "Trả lời dựa trên context. Ghi rõ nguồn."
    Context: [entity graph + relation chain + document chunks]
    │
    ▼
Response: {
    "answer": "Dự án Alpha đang dùng React 18, FastAPI (Python)...",
    "citations": [
        {"file": "DA-Alpha-techspec.docx", "page": 3},
        {"wiki_entity": "Dự án Alpha", "relation": "dùng"}
    ]
}
    │
    ▼
Chat UI hiển thị:
    ├── Câu trả lời (markdown)
    └── Citation chips có thể click → mở file gốc hoặc graph node
    │
    ▼ (background, sau khi trả lời xong)
Backend trigger Graphiti pipeline:
    POST /graphiti/extract
    {
      "conversation_id": "conv-uuid-123",
      "turns": [
        {"role": "user", "content": "Dự án Alpha dùng tech stack gì?"},
        {"role": "assistant", "content": "Dự án Alpha dùng React 18..."}
      ],
      "timestamp": "2026-06-15T10:32:00"
    }
    │
    ▼
Graphiti Service:
    ├── LLM extract từ hội thoại:
    │   entities: [Dự án Alpha, React 18, FastAPI, team Backend]
    │   relations: [Alpha-dùng->React 18], [Alpha-phụ trách->team Backend]
    ├── Check existing nodes trong graph
    ├── Merge: entity đã có → add new edges, update description
    ├── New entity → tạo node mới với timestamp
    ├── Expired check: info cũ bị contradicted → mark edge expired
    └── Commit → PostgreSQL graph (cùng DB với LightRAG)
```

### 5.3 Workflow — Admin Panel

```
Admin đăng nhập → Admin Panel
    │
    ├── [Tab: NAS Queue]
    │   ├── Danh sách file đang chờ duyệt (manual-review folder)
    │   │   Hiển thị: tên file, folder NAS, size, thời gian detect
    │   ├── APPROVE → trigger ingestion pipeline
    │   ├── REJECT → remove khỏi queue + log
    │   └── Bulk approve (chọn nhiều file cùng lúc)
    │
    ├── [Tab: Document Status]
    │   ├── Danh sách tất cả file đã index
    │   │   Status: INDEXED / INDEXING / FAILED / PENDING
    │   ├── Re-index (khi file thay đổi trên NAS)
    │   ├── Delete from index
    │   └── View indexing log (chunk count, entity count, errors)
    │
    ├── [Tab: Knowledge Graph] ← embed LightRAG Web UI
    │   ├── Visualize toàn bộ graph (nodes + edges)
    │   ├── Filter: chỉ xem nodes từ tài liệu, hoặc từ hội thoại
    │   ├── Search node theo tên entity
    │   ├── Xem neighbors của một node
    │   └── Export subgraph
    │
    └── [Tab: NAS Config]
        ├── Xem danh sách folder đang được watch
        ├── Thêm/xóa folder
        ├── Set auto-sync vs manual-review per folder
        └── Xem sync log (last check, files found, errors)
```

---

## 6. Stack chi tiết & config

### 6.1 Services và ports

| Service | Port | Công nghệ | Vai trò |
|---|---|---|---|
| `lightrag` | 9621 | Python + FastAPI | Graph engine, vector search, document processing |
| `graphiti-service` | 9622 | Python + FastAPI | Conversation memory, temporal graph |
| `nas-connector` | — | Python (background) | Watch NAS, push files |
| `backend` | 8000 | Python + FastAPI | Auth, chat API, wiki API, admin API, MCP |
| `frontend` | 3000 | React + Vite | Chat UI, wiki UI, admin panel |
| `postgres` | 5432 | PostgreSQL 18 + pgvector + AGE | Tất cả storage |
| `redis` | 6379 | Redis | Queue, cache |
| `minio` | 9000 | MinIO | File gốc từ NAS |
| `seq` | 80 | Seq (datalust) | Centralized logging — debug multi-service |
| `ollama` | 11434 | Ollama | LLM + embedding local (GĐ2) |

### 6.2 LightRAG `.env` config

```ini
# ── NAS — Synology SMB (LAN) ───────────────────────────────────
NAS_HOST=192.168.1.x             # IP Synology trên LAN
NAS_USER=secondbrain             # user read-only riêng, không dùng admin
NAS_PASS=...
NAS_SHARE=documents              # tên Shared Folder trên Synology DSM
NAS_MOUNT_PATH=/mnt/synology     # mount point trên host OS

# ── LLM Configuration ──────────────────────────────────────────

# Giai đoạn 1: Gemini Flash Lite (rẻ, tiếng Việt tốt)
LLM_BINDING=gemini
LLM_MODEL=gemini-2.0-flash-lite
GEMINI_API_KEY=AIza...

# Giai đoạn 2: Ollama local (đổi 3 dòng này, comment 2 dòng trên)
# LLM_BINDING=ollama
# LLM_MODEL=qwen2.5:14b
# OLLAMA_HOST=http://ollama:11434

# Role-specific LLM (tối ưu chi phí + tốc độ)
# EXTRACT role: cần LLM mạnh nhất — dùng cho entity extraction khi ingestion
# QUERY role: cần nhanh — dùng cho chat realtime
# KEYWORDS role: task đơn giản — model nhỏ nhất
# GĐ2 với Ollama:
# EXTRACT_LLM_BINDING=ollama
# EXTRACT_LLM_MODEL=qwen2.5:14b    # 10GB VRAM
# QUERY_LLM_BINDING=ollama
# QUERY_LLM_MODEL=qwen2.5:7b       # 5GB VRAM, ~25 tok/s
# KEYWORDS_LLM_BINDING=ollama
# KEYWORDS_LLM_MODEL=qwen2.5:3b    # 2GB VRAM, near instant

# ── Embedding ──────────────────────────────────────────────────
EMBEDDING_BINDING=ollama
EMBEDDING_MODEL=nomic-embed-text   # nhẹ, CPU OK, $0
EMBEDDING_DIM=768
# Nâng cấp: bge-m3 (multilingual, tiếng Việt tốt hơn, cần GPU)
# EMBEDDING_MODEL=bge-m3
# EMBEDDING_DIM=1024

# ── Storage — PostgreSQL all-in-one ────────────────────────────
KV_STORAGE=PGKVStorage
VECTOR_STORAGE=PGVectorStorage
GRAPH_STORAGE=PGGraphStorage
DOC_STATUS_STORAGE=PGDocStatusStorage
POSTGRES_URL=postgresql://secondbrain:password@postgres:5432/lightrag

# ── Document Processing ────────────────────────────────────────
# Parser pipeline: thử native trước, fallback MinerU nếu cần
LIGHTRAG_PARSER=*:native-iteP,*:mineru-iteP,*:legacy-R
VLM_PROCESS_ENABLE=false   # bật khi cần phân tích ảnh trong PDF
SUMMARY_LANGUAGE=Vietnamese

# ── Performance ────────────────────────────────────────────────
MAX_ASYNC_LLM=4            # concurrent LLM calls khi ingestion
MAX_PARALLEL_INSERT=2      # files xử lý song song
EMBEDDING_FUNC_MAX_ASYNC=8
EMBEDDING_BATCH_NUM=16

# ── Query ──────────────────────────────────────────────────────
ENABLE_LLM_CACHE=false     # tắt cache — tài liệu Robolinks cập nhật thường xuyên
                           # câu hỏi giống nhau có thể có câu trả lời khác sau khi index mới
```

### 6.3 `docker-compose.yml` skeleton

```yaml
version: "3.9"
services:
  postgres:
    image: pgvector/pgvector:pg18
    environment:
      POSTGRES_USER: secondbrain
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: secondbrain
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    ports: ["9000:9000", "9001:9001"]

  lightrag:
    image: ghcr.io/hkuds/lightrag:latest
    env_file: ./lightrag/.env
    depends_on: [postgres, redis]
    ports: ["9621:9621"]
    volumes:
      - ./lightrag/storage:/app/storage

  graphiti-service:
    build: ./graphiti-service
    env_file: .env
    depends_on: [postgres]
    ports: ["9622:9622"]

  nas-connector:
    build: ./nas-connector
    env_file: .env
    depends_on: [lightrag, backend]
    volumes:
      - /mnt/synology:/mnt/nas:ro   # Synology SMB mount — read-only
    # Synology mount trước khi chạy docker-compose:
    # sudo mount -t cifs //NAS_IP/ShareName /mnt/synology \
    #   -o username=NAS_USER,password=NAS_PASS,uid=1000,gid=1000

  backend:
    build: ./backend
    env_file: .env
    depends_on: [postgres, redis, lightrag, graphiti-service]
    ports: ["8000:8000"]

  frontend:
    build: ./frontend
    depends_on: [backend]
    ports: ["3000:3000"]

  seq:
    image: datalust/seq:latest
    ports: ["80:80", "5341:5341"]
    environment:
      ACCEPT_EULAS: "Y"
    volumes:
      - seq_data:/data

  # Giai đoạn 2: uncomment khi có GPU server
  # ollama:
  #   image: ollama/ollama
  #   deploy:
  #     resources:
  #       reservations:
  #         devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]
  #   ports: ["11434:11434"]
  #   volumes:
  #     - ollama_data:/root/.ollama

volumes:
  postgres_data:
  minio_data:
  seq_data:
  # ollama_data:
```

---

## 7. Data model

### 7.1 SecondBrain backend DB (PostgreSQL — schema riêng)

```sql
-- Users
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user',  -- 'user' | 'admin'
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Conversations (chat history)
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    title       TEXT,                          -- auto-generated từ turn đầu
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role            TEXT NOT NULL,             -- 'user' | 'assistant'
    content         TEXT NOT NULL,
    citations       JSONB,                     -- [{file, page, entity}]
    graphiti_synced BOOLEAN DEFAULT false,     -- đã extract vào graph chưa
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- NAS files queue
CREATE TABLE nas_files (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nas_path    TEXT NOT NULL,                 -- đường dẫn gốc trên NAS
    folder_type TEXT NOT NULL,                 -- 'auto' | 'manual'
    status      TEXT NOT NULL DEFAULT 'pending',
    -- pending → approved/rejected → indexing → indexed/failed
    file_hash   TEXT,                          -- detect thay đổi
    lightrag_doc_id TEXT,                      -- ID trong LightRAG sau khi index
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    reject_reason TEXT,
    indexed_at  TIMESTAMPTZ,
    error_msg   TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- NAS folders config
CREATE TABLE nas_folders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path        TEXT UNIQUE NOT NULL,
    folder_type TEXT NOT NULL,                 -- 'auto' | 'manual'
    is_active   BOOLEAN DEFAULT true,
    last_scanned TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

### 7.2 Knowledge Graph schema (PostgreSQL + pgvector + AGE)

LightRAG và Graphiti đều dùng chung PostgreSQL instance nhưng **schema riêng**:

```
lightrag schema:
  ├── kv_store          (LLM response cache, chunk data)
  ├── vector_store      (chunk embeddings — pgvector)
  ├── graph_store       (entity nodes, relation edges — Apache AGE)
  └── doc_status        (trạng thái ingestion từng file)

graphiti schema:
  ├── episodes          (conversation turns đã process)
  ├── entities          (nodes extracted từ hội thoại)
  ├── relations         (edges với timestamp, expiry)
  └── communities       (cluster của entities liên quan)
```

**Vấn đề cần giải quyết:** LightRAG và Graphiti hiện tại dùng graph schema khác nhau.
Về ngắn hạn (MVP): chạy 2 graph riêng, query engine merge kết quả ở tầng backend.
Về dài hạn: migrate cả 2 về chung 1 graph schema.

---

## 8. API contracts

### 8.1 SecondBrain Backend API

```
POST   /api/auth/login           → {access_token, user}
POST   /api/auth/register        → {access_token, user}
GET    /api/auth/me              → {user}

POST   /api/chat                 → {answer, citations, conversation_id}
GET    /api/chat/conversations   → [{id, title, updated_at}]
GET    /api/chat/conversations/:id/messages → [{role, content, citations}]

GET    /api/admin/nas/queue      → [{file, folder, status, created_at}]
POST   /api/admin/nas/approve    → {ok}   body: {file_id}
POST   /api/admin/nas/reject     → {ok}   body: {file_id, reason}
GET    /api/admin/nas/folders    → [{path, type, is_active}]
POST   /api/admin/nas/folders    → {ok}   body: {path, type}
DELETE /api/admin/nas/folders/:id → {ok}

GET    /api/admin/documents      → [{nas_path, status, indexed_at}]
POST   /api/admin/documents/:id/reindex → {ok}
DELETE /api/admin/documents/:id  → {ok}

# Wiki endpoints
GET    /api/wiki/entities        → [{name, type, description}]  ?type=PROJECT|EQUIPMENT|...
GET    /api/wiki/entity/:name    → {name, type, description, relations, sources}
GET    /api/wiki/search          → [{name, type, score}]  ?q=Heineken

# MCP endpoint
GET|POST /mcp                   → MCP protocol (fastmcp ASGI mount)
```

### 8.2 Chat request/response

```json
// Request
POST /api/chat
{
  "message": "Dự án Alpha dùng tech stack gì?",
  "conversation_id": "conv-uuid-123"   // null = new conversation
}

// Response
{
  "conversation_id": "conv-uuid-123",
  "answer": "Dự án Alpha đang sử dụng React 18 cho frontend...",
  "citations": [
    {
      "type": "document",
      "file": "DA-Alpha-techspec.docx",
      "page": 3,
      "excerpt": "Frontend stack: React 18, TypeScript..."
    },
    {
      "type": "graph_entity",
      "entity": "Dự án Alpha",
      "relation": "sử_dụng",
      "target": "React 18"
    }
  ],
  "query_mode": "mix",
  "latency_ms": 1840
}
```

---

## 9. Timeline triển khai

### Giai đoạn 1 — Core MVP (4 tuần)

```
Tuần 1: Infrastructure setup
    ├── Docker Compose toàn bộ stack (postgres, redis, minio, lightrag)
    ├── LightRAG config: Gemini Flash Lite + nomic-embed-text + PostgreSQL storage
    ├── Test ingestion với 5–10 file thật của công ty
    ├── Verify tiếng Việt (SUMMARY_LANGUAGE=Vietnamese)
    └── Backend skeleton: FastAPI + auth + DB schema

Tuần 2: NAS Connector
    ├── SMB client kết nối NAS thực tế
    ├── File change detection (so hash với DB)
    ├── Auto-sync folder → POST /api/v1/docs LightRAG
    ├── Manual-review folder → insert DB + notify
    └── Admin approval API + UI cơ bản

Tuần 3: Chat UI + Query + Wiki UI
    ├── Chat API backend (gọi LightRAG /api/v1/query mode=mix, streaming)
    ├── Conversation storage (lưu history, pagination)
    ├── React Chat UI: input, message list, citation display, streaming tokens
    ├── Wiki API backend (gọi LightRAG graph API → render entity page)
    ├── React Wiki UI: browse by category, entity page, mini graph (vis.js)
    └── MCP server (fastmcp): search_knowledge, get_entity, list_documents tools

Tuần 4: Integration + Test thực tế
    ├── Deploy nội bộ (máy dev hoặc VPS)
    ├── Load ~50 file thật của công ty
    ├── Nhân viên test: chat 20+ câu, browse wiki, thử Claude Desktop + MCP
    ├── Tune: chunking strategy, EXTRACT LLM prompt (Section 14), reranker
    └── Fix bugs, polish UI
───────────────────────────────────────────────
→ MILESTONE 1: Demo công ty dùng được
```

### Giai đoạn 2 — Conversation Memory (tuần 5–7)

```
Tuần 5: Graphiti setup
    ├── Deploy graphiti-service (pip install graphiti-core)
    ├── Config Graphiti → cùng PostgreSQL với LightRAG
    ├── Test: insert 10 cuộc hội thoại mẫu → verify graph được tạo
    └── API: POST /graphiti/extract

Tuần 6: Integration + Graph Explorer
    ├── Backend trigger Graphiti sau mỗi chat turn
    ├── Verify entities từ hội thoại xuất hiện trong graph
    ├── Embed LightRAG Web UI vào Admin panel (graph explorer)
    └── Test: hỏi câu về thứ chỉ được nhắc trong hội thoại

Tuần 7: Merge query context
    ├── Backend merge kết quả LightRAG + Graphiti khi query
    ├── Citation hiển thị rõ: từ tài liệu hay từ hội thoại
    └── Test end-to-end: upload file → chat → graph đầy đủ
───────────────────────────────────────────────
→ MILESTONE 2: Conversation memory hoạt động
```

### Giai đoạn 3 — Polish + Server (tháng 3–4)

```
Tháng 3:
    ├── Admin panel đầy đủ (NAS config, document management, monitoring)
    ├── Notification system (email/web push khi file cần duyệt)
    ├── Error handling + retry logic cho ingestion failures
    └── Logging + basic analytics (query count, popular topics)

Tháng 4 (khi có server 50 triệu):
    ├── Setup GPU server: Ubuntu + Docker + NVIDIA drivers
    ├── Ollama: pull qwen2.5:14b, qwen2.5:7b, qwen2.5:3b, bge-m3
    ├── Đổi config: LLM_BINDING=ollama, EMBEDDING_MODEL=bge-m3
    ├── Re-embed toàn bộ document (bge-m3 tốt hơn nomic-embed-text)
    └── Verify performance: latency, quality so sánh trước/sau
───────────────────────────────────────────────
→ MILESTONE 3: Full offline, $0 vận hành
```

---

## 10. Quyết định kiến trúc — Multi-service tradeoffs

Các nhược điểm của kiến trúc multi-service và quyết định xử lý:

### 10.1 Multi-service complexity — debug nhiều nơi
**Quyết định: Centralized logging với Seq**

Thêm Seq vào docker-compose. Tất cả service ship log về Seq, debug qua 1 UI,
filter theo `correlation_id` để trace toàn bộ 1 request qua nhiều service.

```yaml
# docker-compose.yml
seq:
  image: datalust/seq:latest
  ports: ["5341:5341", "80:80"]
  environment:
    ACCEPT_EULAS: "Y"
```

Mỗi request backend tạo 1 `correlation_id` (UUID), forward qua header khi gọi
LightRAG và Graphiti → tất cả log cùng request có chung ID để filter.

### 10.2 Latency — LLM là bottleneck thực sự
**Quyết định: Streaming response, không dùng LLM cache**

HTTP hop nội bộ giữa containers (~30–70ms tổng) không đáng kể so với LLM
inference (~1–3 giây). Vấn đề thực sự là UX người dùng chờ đợi.

**Giải pháp:** Streaming response — trả từng token về Chat UI ngay thay vì
chờ đủ response.

```python
# backend/routers/chat.py
from fastapi.responses import StreamingResponse

@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in lightrag_client.query_stream(request.message):
            yield f"data: {chunk}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

```typescript
// frontend — Chat UI dùng EventSource
const es = new EventSource("/api/chat/stream");
es.onmessage = (e) => appendToken(e.data);
```

**Lý do không dùng LLM cache (`ENABLE_LLM_CACHE=false`):**
Tài liệu Robolinks cập nhật thường xuyên. Câu hỏi giống nhau nhưng index
mới → câu trả lời phải khác. Cache cũ sẽ trả về thông tin lỗi thời.
→ **`ENABLE_LLM_CACHE=false` trong LightRAG `.env`**

### 10.3 Upstream breaking change
**Quyết định: Pin version cụ thể**

```yaml
# docker-compose.yml — KHÔNG dùng :latest
lightrag:
  image: ghcr.io/hkuds/lightrag:v1.5.4
```

```txt
# graphiti-service/requirements.txt
graphiti-core==0.4.2
```

Upgrade có chủ ý: đọc changelog → test dev → deploy production.

### 10.4 LightRAG Web UI không tùy biến
**Quyết định: Phân tách audience rõ ràng**

```
LightRAG Web UI (port 9621) → Admin/Dev only
  ├── Graph explorer
  ├── Document management
  └── Query testing
  Không expose ra nhân viên.

SecondBrain Chat UI (port 3000) → Nhân viên Robolinks
  ├── Tự build → tùy biến hoàn toàn
  └── Gọi LightRAG REST API
```

### 10.5 Customize LightRAG behavior
**Quyết định: Custom prompts qua `prompts/` directory**

LightRAG cho phép override entity extraction prompt mà không cần sửa source:

```
lightrag/
└── prompts/
    └── extraction.txt    ← System prompt Robolinks (Section 11.3)
```

`LIGHTRAG_PROMPT_DIR=./prompts` trong `.env`. 90% nhu cầu customize được qua
config + prompt. Edge case cần sâu hơn → fork LightRAG khi thực sự cần.

---

## 11. Wiki Engine — Hướng C (Graph-driven)

### Quyết định
Render wiki page trực tiếp từ data LightRAG graph — không cần LLM compile thêm.
LightRAG đã extract entity + description + relations + source chunks. Dùng data đó
để render wiki page cho nhân viên xem.

**Lý do chọn Hướng C trước:**
- Không cần thêm LLM call → không tốn thêm chi phí API
- Có thể làm trong tuần 3–4 cùng lúc với Chat UI
- Data đã có sẵn trong LightRAG graph sau ingestion
- Nâng lên Hướng A (LLM compile) sau khi MVP stable

### Wiki page là gì trong context Robolinks

Mỗi entity trong knowledge graph = 1 wiki page:

```
/wiki/entity/Heineken-Binh-Duong-2024
  Tên: Heineken Bình Dương 2024
  Loại: PROJECT
  Mô tả: [description từ LightRAG entity node]

  Liên kết:
  ├── CLIENT_OF     → Heineken Vietnam
  ├── USES          → Conveyor CB-01, Motor Siemens 1LE1, ...
  ├── RESPONSIBLE_FOR ← Nguyễn Văn A (KS Điện)
  └── LOCATED_AT    → Nhà máy Heineken Bình Dương

  Tài liệu nguồn:
  ├── DA-Heineken-2024-electrical-v3.pdf  [link NAS]
  ├── BOM-Heineken-2024-final.xlsx        [link NAS]
  └── Bien-ban-FAT-Heineken-2024.docx     [link NAS]

  [Mini graph — vis.js hiển thị entity + 1-hop neighbors]
```

### API cho Wiki

```
GET /api/wiki/entities?type=PROJECT          → danh sách project entities
GET /api/wiki/entities?type=EQUIPMENT        → danh sách equipment
GET /api/wiki/entity/{entity_name}           → chi tiết entity + relations + sources
GET /api/wiki/search?q=Heineken              → search entity theo tên
```

Backend gọi LightRAG:
```
GET /api/v1/graph/entity/{name}              → entity node + neighbors
GET /api/v1/graph/edges?entity={name}        → relations của entity
```

### Wiki UI flow

```
Nhân viên vào tab "Wiki"
  │
  ▼
Wiki Home: browse theo category
  ├── 🏗️ Dự án (PROJECT entities)
  ├── ⚙️ Thiết bị (EQUIPMENT entities)
  ├── 🔧 Linh kiện (COMPONENT entities)
  ├── 📋 Quy trình (PROCESS entities)
  └── 🚨 Lỗi thường gặp (ERROR_CODE entities)
  │
  ▼
Click vào entity → Wiki Page
  ├── Header: tên, loại, description
  ├── Relations panel (danh sách liên kết)
  ├── Mini graph (vis.js — interactive, click để navigate)
  ├── Source documents (link về file gốc trên NAS)
  └── "Hỏi AI về [entity này]" → mở Chat UI với context pre-filled

```

### Upgrade path lên Hướng A (khi cần)

Khi Hướng C không đủ (description entity quá ngắn, thiếu ngữ cảnh), thêm:
```
wiki_builder.py:
  GET entity + sources → LLM compile thành wiki page dài hơn
  → Cache kết quả (wiki content ít thay đổi)
  → Admin có thể trigger re-compile khi có tài liệu mới
```

---

## 11b. MCP Server

### Mục đích

MCP server để:
1. **Claude Desktop / AI tools bên ngoài** query SecondBrain knowledge trực tiếp
2. **Dự án future** (OCR pipeline, video transcript...) push thêm entity/relation vào graph
3. **Kiro / Cursor** của team dev query knowledge base khi làm việc

### Stack

`fastmcp` Python library — deploy **cùng process với backend FastAPI**, không cần service riêng.

```python
# backend/mcp/server.py
from fastmcp import FastMCP

mcp = FastMCP("SecondBrain — Robolinks Knowledge Hub")
```

Mount vào FastAPI app:
```python
# backend/main.py
from mcp.server import mcp
app.mount("/mcp", mcp.get_asgi_app())
```

### MCP Tools

```python
@mcp.tool()
async def search_knowledge(query: str, mode: str = "mix") -> str:
    """
    Tìm kiếm trong knowledge base Robolinks.
    Dùng khi cần tra cứu thông số kỹ thuật, quy trình, lịch sử dự án.
    mode: 'mix' (mặc định), 'local' (entity cụ thể), 'global' (tổng quan)
    """

@mcp.tool()
async def get_entity(entity_name: str) -> dict:
    """
    Lấy thông tin chi tiết về một entity (dự án, thiết bị, linh kiện, quy trình...).
    Trả về: description, relations, source documents.
    """

@mcp.tool()
async def list_documents(
    project: str = None,
    doc_type: str = None
) -> list:
    """
    Liệt kê tài liệu đã index.
    Filter theo dự án hoặc loại tài liệu (BOM, SOP, manual, bản vẽ...).
    """

@mcp.tool()
async def get_document_context(nas_path: str) -> str:
    """
    Lấy nội dung/context của một file cụ thể trên NAS.
    Trả về chunks đã index + metadata.
    """

@mcp.tool()
async def push_knowledge(
    entity_name: str,
    entity_type: str,
    description: str,
    relations: list,
    source: str
) -> dict:
    """
    [Dành cho dự án future] Push entity/relation mới vào knowledge graph.
    Dùng bởi OCR pipeline, video transcript service kết nối qua MCP.
    """
```

### Kết nối Claude Desktop

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "secondbrain-robolinks": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

Custom instruction cho Claude:
```
Khi trả lời câu hỏi về kỹ thuật, dự án, thiết bị của Robolinks,
luôn dùng tool search_knowledge trước khi trả lời.
```

### Bảo mật MCP

- Require Bearer token (dùng chung auth với backend)
- Rate limit: 100 requests/phút/token
- `push_knowledge` tool chỉ cho phép internal service tokens (không phải user token)

---

## 12. Rủi ro và mitigation

| Rủi ro | Khả năng | Mức độ | Mitigation |
|---|---|---|---|
| LightRAG MinerU cloud có quota giới hạn | Cao | Trung bình | Dùng Native parser trước, MinerU chỉ cho PDF phức tạp. Deploy MinerU local sau |
| Graphiti + LightRAG dùng graph schema khác nhau | Chắc chắn | Trung bình | MVP: 2 graph riêng, merge ở backend. Dài hạn: unified schema |
| Gemini API cost vượt dự kiến | Trung bình | Thấp | Đặt quota limit. Ước tính ~$0.5–2/tài liệu dày. Index batch 1 lần, query rẻ hơn nhiều |
| NAS Robolinks không hỗ trợ SMB/WebDAV | Thấp | Cao | Hỏi IT trước tuần 1. Fallback: mount NAS qua OS, connector đọc local path |
| Tiếng Việt + thuật ngữ kỹ thuật automation extract kém | Trung bình | Cao | Test với Gemini + bộ ví dụ domain-specific. Thêm Robolinks terminology vào system prompt EXTRACT LLM (Section 14) |
| Tài liệu CAD/DWG nhiều, metadata không đủ context | Trung bình | Trung bình | Dùng folder path convention để infer project/stage. README hoặc BOM trong cùng thư mục cung cấp thêm context |
| Kỹ sư không dùng → graph hội thoại không phong phú | Trung bình | Trung bình | Demo giá trị sớm (tuần 4). Tích hợp vào workflow hàng ngày thay vì tool riêng |
| Ingestion crash giữa chừng | Trung bình | Thấp | LightRAG có resume-on-crash built-in. ARQ queue có retry logic |

---

## 13. Chi phí vận hành

### Giai đoạn 1 (chưa có server)

| Item | Chi phí/tháng |
|---|---|
| Gemini Flash Lite (ingestion + chat) | ~$5–15 |
| Ollama nomic-embed-text (embedding, CPU) | $0 |
| VPS deploy (tùy chọn) | $5–10 |
| PostgreSQL, Redis, MinIO (self-hosted) | $0 |
| **Tổng** | **~$10–25/tháng** |

### Giai đoạn 2 (có server GPU 50 triệu)

| Item | Chi phí |
|---|---|
| Server hardware (one-time) | ~35–44 triệu |
| Điện (RTX 4060 Ti idle ~30W, load ~150W) | ~100–200k/tháng |
| Tất cả AI (Ollama local) | $0 |
| **Recurring cost** | **~100–200k VND/tháng** |

---

## 14. Knowledge Graph Schema — Robolinks Domain

Đây là phần quan trọng nhất trước khi implement. LightRAG và Graphiti dùng LLM
để tự động extract entity/relation. Nếu không định hướng domain rõ, LLM sẽ
extract entity chung chung, không phù hợp với Robolinks.

Taxonomy này cần đưa vào **system prompt của EXTRACT LLM**.

### 11.1 Entity Types

| Entity Type | Ví dụ thực tế Robolinks | Nguồn thường gặp |
|---|---|---|
| `PROJECT` | "Heineken Bình Dương 2024", "Vinamilk line 3" | Tên thư mục NAS, hợp đồng, biên bản |
| `CLIENT` | "Heineken Vietnam", "Vinamilk", "Mondelez" | Hợp đồng, báo giá |
| `EQUIPMENT` | "Conveyor belt CB-01", "Robot ABB IRB 1200", "Tủ điện MCC-03" | BOM, bản vẽ, manual |
| `COMPONENT` | "Motor Siemens 1LE1 7.5kW", "Inverter Sinamics G120", "Sensor Sick WL12G" | BOM, catalog, troubleshooting |
| `SUPPLIER` | "Siemens Vietnam", "Mitsubishi Electric", "Sick Vietnam" | BOM, báo giá mua sắm |
| `PERSON` | "Nguyễn Văn A — KS Điện", "Trần Thị B — PM" | Hợp đồng, biên bản, email |
| `PROCESS` | "Quy trình FAT", "SOP vận hành CB-01", "Checklist nghiệm thu" | SOP, checklist |
| `ERROR_CODE` | "F0011 Sinamics G120", "E007 biến tần Mitsubishi" | Troubleshooting guide, manual |
| `DOCUMENT` | "DA-Heineken-2024-electrical-v3.dwg", "BOM-line3-final.xlsx" | Metadata file |
| `LOCATION` | "Nhà máy Heineken Bình Dương", "Xưởng chế tạo Robolinks Q9" | Biên bản, bản vẽ layout |
| `STANDARD` | "IEC 60204-1", "TCVN 7447" | Thuyết minh thiết kế, manual |

### 11.2 Relation Types

| Relation | Từ → Đến | Ví dụ |
|---|---|---|
| `BELONGS_TO` | DOCUMENT/EQUIPMENT → PROJECT | Bản vẽ CB-01 thuộc dự án Heineken 2024 |
| `CLIENT_OF` | PROJECT → CLIENT | Dự án Heineken 2024 cho Heineken Vietnam |
| `USES` | PROJECT/EQUIPMENT → COMPONENT | Conveyor CB-01 dùng Motor Siemens 7.5kW |
| `SUPPLIED_BY` | COMPONENT → SUPPLIER | Motor Siemens 7.5kW cung cấp bởi Siemens VN |
| `RESPONSIBLE_FOR` | PERSON → PROJECT/EQUIPMENT | Nguyễn Văn A phụ trách thiết kế điện Heineken 2024 |
| `SOLVES` | PROCESS/DOCUMENT → ERROR_CODE | Troubleshooting guide giải quyết lỗi F0011 |
| `VERSION_OF` | DOCUMENT → DOCUMENT | v3 là bản cập nhật của v2 |
| `REFERENCES` | DOCUMENT → STANDARD | Thuyết minh tham chiếu IEC 60204-1 |
| `LOCATED_AT` | PROJECT/EQUIPMENT → LOCATION | Dự án Heineken 2024 tại nhà máy Bình Dương |
| `SIMILAR_TO` | PROJECT → PROJECT | Dự án Vinamilk Line 3 tương tự Heineken 2024 |
| `OCCURS_ON` | ERROR_CODE → COMPONENT/EQUIPMENT | F0011 xảy ra trên Sinamics G120 |
| `MAINTAINED_BY` | EQUIPMENT → PERSON | Conveyor CB-01 bảo trì bởi Trần Văn C |

### 11.3 System Prompt EXTRACT LLM (Robolinks domain)

```
Bạn là chuyên gia phân tích tài liệu kỹ thuật của công ty tự động hóa Robolinks.
Nhiệm vụ: trích xuất entity và relation từ đoạn văn bản dưới đây.

Entity types cần nhận diện:
- PROJECT: tên dự án (thường kèm tên khách hàng + năm, ví dụ "Heineken Bình Dương 2024")
- CLIENT: tên khách hàng/đối tác
- EQUIPMENT: tên thiết bị/máy móc cụ thể trong dự án (conveyor, robot, tủ điện...)
- COMPONENT: linh kiện, module với model cụ thể (Motor Siemens 1LE1, Inverter G120...)
- SUPPLIER: nhà cung cấp (Siemens, Mitsubishi, Sick, Omron, ABB, Schneider, Pilz...)
- PERSON: tên người + vai trò (kỹ sư điện, PM, kỹ thuật viên cơ khí...)
- PROCESS: tên quy trình/thủ tục (FAT, SAT, nghiệm thu, bảo trì định kỳ...)
- ERROR_CODE: mã lỗi thiết bị (F0011, E007, Alarm 32...)
- DOCUMENT: tên/mã tài liệu cụ thể (bản vẽ, BOM, manual...)
- LOCATION: địa điểm nhà máy, khu vực lắp đặt

Chỉ extract entity rõ ràng, không suy diễn. Output JSON:
{"entities": [{"name": "...", "type": "...", "description": "..."}],
 "relations": [{"src": "...", "rel_type": "...", "tgt": "...", "description": "..."}]}
```

### 11.4 Ví dụ graph — từ tài liệu thực tế Robolinks

**Từ file BOM `Heineken-2024-BOM.xlsx`:**
```
Nodes được tạo:
  [PROJECT]   Heineken Bình Dương 2024
  [CLIENT]    Heineken Vietnam
  [EQUIPMENT] Conveyor Belt CB-01
  [COMPONENT] Motor Siemens 1LE1 7.5kW 4P
  [COMPONENT] Inverter Sinamics G120 11kW
  [COMPONENT] Sensor Sick WL12G-3P2231
  [SUPPLIER]  Siemens Vietnam
  [SUPPLIER]  Sick Vietnam

Edges được tạo:
  CB-01             --[BELONGS_TO]--> Heineken 2024
  Heineken 2024     --[CLIENT_OF]-->  Heineken Vietnam
  CB-01             --[USES]-->       Motor Siemens 1LE1
  CB-01             --[USES]-->       Inverter Sinamics G120
  CB-01             --[USES]-->       Sensor Sick WL12G
  Motor Siemens     --[SUPPLIED_BY]-> Siemens Vietnam
  Sensor Sick WL12G --[SUPPLIED_BY]-> Sick Vietnam
```

**Từ troubleshooting guide + hội thoại kỹ sư (Graphiti):**
```
Kỹ sư hỏi: "Inverter G120 báo F0011 trên conveyor nhà Heineken là sao?"
AI trả lời: "F0011 là lỗi overcurrent phase U..."

Graphiti extract thêm (timestamp: 2026-06-15):
  [ERROR_CODE] F0011 Sinamics G120
  Edge: F0011 --[OCCURS_ON]-->  Inverter Sinamics G120
  Edge: F0011 --[RELATED_TO]--> CB-01 Heineken 2024

→ Lần sau hỏi "Conveyor Heineken hay gặp lỗi gì?":
  Graph traverse: CB-01 → [USES] → Sinamics G120 → [OCCURS_ON] ← F0011
  → AI trả lời được dù không có tài liệu nào ghi rõ điều này
```

**File binary (DWG, PNG, MP4) — index metadata only:**
```
File: /projects/Heineken-2024/design/electrical/DA-CB01-v3.dwg
→ Không parse nội dung CAD
→ Index: {
    name: "DA-CB01-v3.dwg",
    type: "DOCUMENT",
    project: "Heineken 2024",       ← từ folder path
    stage: "design/electrical",     ← từ folder path
    version: "v3",                  ← từ tên file
    nas_path: "/projects/Heineken-2024/design/electrical/DA-CB01-v3.dwg"
  }
→ Kỹ sư hỏi "Bản vẽ điện CB-01 Heineken" → AI trả về link file + metadata
```

> OCR, video transcript, DWG content parsing là **ngoài scope** dự án này.
> Sẽ được xử lý bởi dự án riêng và kết nối vào SecondBrain qua MCP.

---

## 15. Chiến lược Test & Kiểm nghiệm

### 3 tầng test

```
Unit tests       → test logic thuần, không cần external service
Integration tests → test với DB/service thật (Docker Compose subset)
E2E / QA manual  → test với toàn bộ stack + tài liệu thật của Robolinks
```

### Tầng 1 — Unit tests (chạy được ngay, không cần Docker)

**Mục tiêu:** Test logic thuần, mock toàn bộ external dependency.

**Thư viện:** `pytest`, `pytest-asyncio`, `unittest.mock`, `pytest-httpx`

| Module | Test gì | Mock gì |
|---|---|---|
| `backend/schemas/` | Validate request/response shape, required fields, type coercion | Không cần mock |
| `backend/services/auth_service.py` | JWT encode/decode, bcrypt hash/verify, token expiry | Không cần mock |
| `backend/services/wiki_builder.py` | Assemble wiki page từ dict graph data | Input dict giả |
| `backend/middleware/correlation.py` | X-Correlation-ID được inject vào request và response | FastAPI TestClient |
| `backend/routers/*` | Endpoint trả đúng status code, response shape đúng schema | `dependency_overrides`: mock `get_current_user`, mock `integrations/*` |
| `backend/integrations/lightrag/` | HTTP client gọi đúng URL, đúng payload, xử lý error response | `pytest-httpx` mock HTTP |
| `backend/integrations/graphiti.py` | Forward `X-Correlation-ID` header, đúng payload | `pytest-httpx` mock HTTP |
| `nas-connector/watcher.py` | Detect file mới, file changed, file deleted | `tmp_path` pytest fixture (local folder giả) |
| `nas-connector/uploader.py` | Gọi backend API đúng endpoint, đúng payload | `pytest-httpx` mock HTTP |
| `graphiti-service/services/extractor.py` | Extract entity/relation từ chat turns | Mock LLM response |

```python
# Ví dụ — test wiki_builder không cần LightRAG
def test_wiki_builder_assembles_page():
    fake_entity = {
        "name": "Heineken Bình Dương 2024",
        "type": "PROJECT",
        "description": "Dự án conveyor cho Heineken",
        "relations": [
            {"rel_type": "CLIENT_OF", "target": "Heineken Vietnam"}
        ],
        "sources": ["BOM-Heineken-2024.xlsx"]
    }
    page = wiki_builder.build(fake_entity)
    assert page["title"] == "Heineken Bình Dương 2024"
    assert len(page["relations"]) == 1
    assert "BOM-Heineken-2024.xlsx" in page["sources"]

# Ví dụ — test router với mock
def test_chat_returns_streaming_response(client, mock_lightrag_query):
    mock_lightrag_query.return_value = iter(["token1 ", "token2 ", "token3"])
    response = client.post("/api/chat/stream",
                           json={"message": "Heineken dùng motor gì?"},
                           headers={"Authorization": "Bearer fake-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
```

### Tầng 2 — Integration tests (cần Docker Compose subset)

**Mục tiêu:** Test với DB và service thật, không mock.

**Stack cần chạy:** PostgreSQL + Redis (không cần LightRAG, Graphiti, Ollama)

```bash
# Chạy subset cho integration test
docker compose -f docker-compose.test.yml up -d postgres redis
pytest tests/backend/integration/ -v
docker compose -f docker-compose.test.yml down
```

| Module | Test gì | Stack cần |
|---|---|---|
| `backend/models/` + `database.py` | CRUD operations, migrations chạy đúng | PostgreSQL |
| `backend/services/conversation_service.py` | Lưu/đọc conversation history, graphiti_synced flag | PostgreSQL |
| `nas-connector/` full flow | Detect file → gọi backend API → NasFile record được tạo | PostgreSQL + backend |
| `graphiti-service/repositories/episode_repo.py` | Lưu/đọc episode status | PostgreSQL |

```yaml
# docker-compose.test.yml
services:
  postgres:
    image: pgvector/pgvector:pg18
    environment:
      POSTGRES_DB: secondbrain_test   # DB riêng cho test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
  redis:
    image: redis:7-alpine
```

### Tầng 3 — E2E / QA manual (full stack)

**Mục tiêu:** Kiểm nghiệm với tài liệu thật của Robolinks, do con người đánh giá chất lượng AI.

**Không thể tự động hoàn toàn** — chất lượng câu trả lời AI cần người đánh giá.

**Checklist E2E mỗi sprint:**

```
Setup:
  □ docker compose up -d (full stack)
  □ Upload 10 file tài liệu thật Robolinks (BOM, SOP, troubleshooting guide)
  □ Chờ ingestion hoàn tất (check /admin/documents — tất cả INDEXED)

Test Chat (Tầng 1 — tài liệu có sẵn):
  □ "Dự án [tên thật] dùng motor loại gì?" → AI cite đúng BOM file
  □ "Quy trình FAT gồm những bước gì?" → AI cite đúng SOP file
  □ "Lỗi [mã lỗi thật] là gì và xử lý sao?" → AI cite troubleshooting guide
  □ "Bản vẽ layout [tên dự án] ở đâu?" → AI trả về đúng NAS path

Test Chat (Tầng 2 — quan hệ cross-document):
  □ "Nhà máy [khách hàng] dùng thiết bị của hãng nào?" → cần graph traverse
  □ "[Thiết bị] hay gặp lỗi gì?" → cần graph từ hội thoại trước

Test Wiki:
  □ Browse /wiki → thấy entity categories
  □ Click vào PROJECT entity → thấy relations đúng, sources đúng
  □ Mini graph hiển thị được neighbors

Test NAS Sync:
  □ Thêm file mới vào auto-sync folder → tự index trong 10 phút
  □ Thêm file vào manual-review folder → admin thấy notification
  □ Admin approve → file được index

Test MCP:
  □ Kết nối Claude Desktop → add secondbrain connector
  □ Hỏi Claude câu hỏi kỹ thuật → Claude dùng search_knowledge tool
  □ Response có citation từ SecondBrain

Regression:
  □ Câu hỏi từ sprint trước vẫn trả lời đúng
```

### Thứ tự implement để test được sớm

```
Tuần 1: backend/schemas + auth_service + models
        → Unit test chạy được ngay từ ngày đầu

Tuần 2: nas-connector (với tmp_path mock)
        → Watcher test không cần NAS thật

Tuần 3: backend/routers/chat + integrations/lightrag (mock)
        → Test chat flow với LightRAG mock

Tuần 4: Full stack + 10 file thật
        → E2E checklist lần 1 với tài liệu Robolinks thật
```

### Đánh giá chất lượng AI (không tự động được)

Tạo **bộ câu hỏi chuẩn** từ tài liệu thật của Robolinks — 20 câu covering đủ loại:

```
File: tests/qa/questions.md

Nhóm 1 — Tra cứu thông số (5 câu):
  Q: "Motor Siemens trên conveyor dự án X có công suất bao nhiêu?"
  Expected: Trả về từ BOM, cite file đúng

Nhóm 2 — Quy trình (5 câu):
  Q: "Checklist FAT gồm những hạng mục nào?"
  Expected: Trả về từ SOP, đủ các bước chính

Nhóm 3 — Troubleshooting (5 câu):
  Q: "Lỗi F0011 xử lý thế nào?"
  Expected: Cite troubleshooting guide, có bước xử lý cụ thể

Nhóm 4 — Quan hệ cross-document (5 câu):
  Q: "Dự án X liên quan đến nhà cung cấp nào?"
  Expected: Traverse graph qua nhiều tài liệu, không chỉ 1 file
```

Mỗi sprint chạy bộ câu hỏi này, rate từ 1–5 cho mỗi câu trả lời. Track điểm theo thời gian để thấy chất lượng cải thiện sau mỗi lần tune prompt.

---

## 16. Câu hỏi còn mở

1. ~~**NAS Robolinks loại gì?**~~ → ✅ **Đã xác nhận: Synology NAS, cùng LAN nội bộ, dùng SMB mount**

2. **Cấu trúc thư mục NAS hiện tại như thế nào?**
   Quan trọng để thiết kế metadata tagging — folder path convention quyết định
   AI biết file thuộc dự án nào, giai đoạn nào.
   Ví dụ lý tưởng: `/projects/Heineken-2024/design/electrical/DA-CB01-v3.dwg`
   → AI tự infer: PROJECT=Heineken-2024, STAGE=design, TYPE=electrical drawing
   → Cần xác nhận cấu trúc thực tế trước khi viết `watcher.py`

3. **Synology user account cho SecondBrain** — nên tạo user riêng (ví dụ `secondbrain`)
   với quyền **read-only** trên các shared folder cần sync. Không dùng admin account.

4. **Auto-mount SMB khi server reboot?**
   Cần thêm vào `/etc/fstab` hoặc dùng `autofs` để SMB mount tự động sau khi restart.
   Nếu mount fail → nas-connector không khởi động được.

5. **Conversation privacy** — Hội thoại kỹ sư A có được extract vào graph chung không?
   Câu hỏi kỹ thuật thường OK. Câu hỏi về báo giá/hợp đồng có thể nhạy cảm.
   → Quyết định: graph chung (đơn giản) hay filter theo keyword trước khi extract?

6. **Graph schema unification** — LightRAG và Graphiti dùng schema khác nhau.
   MVP: 2 graph riêng, merge ở backend. Dài hạn: unified schema.

7. **Re-embed khi nâng embedding model** — nomic-embed-text → bge-m3 cần migration script.
   Tính toán cost và downtime trước khi làm.

8. **Synology DSM version?** — DSM 7.x hỗ trợ SMBv3, DSM 6.x chỉ SMBv2.
   Ảnh hưởng đến mount options trong `fstab` và performance.
