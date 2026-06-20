# SecondBrain — Robolinks Knowledge Hub

**Bộ nhớ kỹ thuật** của Robolinks — middleware app giúp lưu trữ và kết nối toàn bộ
tài liệu dự án từ NAS, tự động tạo knowledge graph, và cho kỹ sư tra cứu thông tin
kỹ thuật nhanh qua AI chat. Graph tự làm giàu thêm từ các cuộc hội thoại hàng ngày.

---

## Vấn đề cần giải quyết

Robolinks ~20 người, tài liệu kỹ thuật phân tán trên NAS theo dự án và phòng ban:

- Kỹ sư mất thời gian tìm tài liệu cũ — "Dự án tương tự năm ngoái dùng giải pháp gì?"
- Troubleshooting phụ thuộc vào trí nhớ người — "Lỗi này đã gặp chưa, xử lý sao?"
- Onboarding chậm — nhân viên mới không biết tài liệu ở đâu, quy trình ra sao
- Kiến thức kỹ thuật tích lũy nhiều năm nhưng chỉ nằm trong đầu kỹ sư lâu năm

SecondBrain làm lớp trung gian với 2 nguồn tri thức:
1. **Tài liệu từ NAS** → xử lý → graph/vector DB
2. **Hội thoại của nhân viên** → tự động extract entity/relation → bổ sung vào graph → tri thức ngày càng sâu hơn theo thời gian

---

## Kiến trúc tổng quan

```
NAS (nguồn tài liệu)          Hội thoại nhân viên
    │                               │
    ▼                               ▼
[SecondBrain App]
    ├── Document Ingestion Pipeline
    │     ├── Đọc file từ NAS (PDF, DOCX, Excel, PPT...)
    │     ├── Parse & chunk tài liệu
    │     ├── Trích xuất entity/relation bằng LLM
    │     └── Lưu vào Graph DB + Vector DB
    │
    ├── Conversation Memory Pipeline  ← MỚI
    │     ├── Lưu lịch sử chat của nhân viên
    │     ├── Extract entity/relation từ hội thoại (Graphiti)
    │     ├── Temporal graph: biết info được nói lúc nào
    │     └── Merge vào knowledge graph chung    │
    ├── Query API
    │     ├── Hybrid search (vector + graph traversal)
    │     └── Trả context cho AI/chatbot
    │
    └── Web UI (quản lý)
          ├── Chat UI cho nhân viên hỏi đáp
          ├── Xem danh sách tài liệu đã index
          ├── Visualize knowledge graph (tài liệu + hội thoại)
          └── Admin panel
```

---

## Tech stack (đang đánh giá)

| Layer | Ứng viên | Ghi chú |
|---|---|---|
| Document parsing + Graph engine | **LightRAG v1.5** | GraphRAG, REST API, Web UI, Ollama native, MIT |
| Conversation memory + Temporal graph | **Graphiti** (standalone) | Extract entity từ hội thoại, temporal, incremental |
| NAS connector | Tự build (SMB/WebDAV) | Tất cả PA đều cần tự build phần này |
| LLM | Gemini Flash Lite → Ollama qwen2.5:14b | GĐ1: API rẻ, GĐ2: local $0 |
| Embedding | nomic-embed-text hoặc bge-m3 (Ollama) | $0, CPU chạy được |
| Web UI | React + shadcn/ui hoặc LightRAG Web UI built-in | Tùy PA chọn |
| Backend | FastAPI + Python | |

> **Ưu tiên:** open-source, self-hosted, chi phí thấp nhất có thể. Xem thêm phân tích tại [`docs/approach-options.md`](./docs/approach-options.md) và [`AI_RAG_Knowledge_Management_Tools_Comparison.md`](./AI_RAG_Knowledge_Management_Tools_Comparison.md).

---

## Luồng dữ liệu chi tiết

### Ingestion — Tài liệu từ NAS

```
1. Watch thư mục NAS → phát hiện file mới/thay đổi
2. Download file về app server
3. Parse nội dung (text, bảng, tiêu đề cấu trúc)
4. Chunk theo ngữ cảnh (không cắt bừa theo ký tự)
5. LLM trích xuất: entity (người, phòng ban, quy trình...) + relation
6. Lưu:
   ├── Nodes/Edges → Knowledge Graph (LightRAG / Graphiti)
   └── Chunk embeddings → Vector DB (pgvector)
```

### Ingestion — Hội thoại nhân viên (MỚI)

```
1. Nhân viên chat hỏi đáp với AI
2. Sau mỗi cuộc hội thoại → Graphiti pipeline:
   ├── Extract entity + relation từ nội dung hội thoại
   ├── Gán timestamp (temporal: biết info được nói lúc nào)
   ├── Nếu entity đã tồn tại trong graph → merge/update
   ├── Nếu info cũ bị outdated → mark edge "expired", không xóa
   └── Commit vào knowledge graph chung
3. Kết quả: graph ngày càng phong phú theo thời gian
   Ví dụ: nhân viên hỏi về "Dự án Alpha" 10 lần
   → graph biết Alpha liên quan React, FastAPI, team Backend,
     deadline Q3, nhà cung cấp XYZ... dù không có tài liệu nào ghi rõ
```

### Retrieval (AI hỏi)

```
1. AI gửi query
2. Hybrid search:
   ├── Vector search → top-k chunks liên quan nhất
   └── Graph traversal → context liên kết (ai liên quan, tài liệu nào trích dẫn...)
3. Rerank + merge kết quả
4. Trả về context cho LLM sinh câu trả lời
```

---

## Tính năng mục tiêu (MVP)

- [ ] Kết nối và đọc file từ NAS
- [ ] Pipeline ingestion tự động khi có file mới
- [ ] Lưu trữ dưới dạng graph (node = tài liệu/entity, edge = quan hệ)
- [ ] Chat UI cho nhân viên hỏi đáp (hybrid search: vector + graph)
- [ ] **Lưu hội thoại → tự động extract entity/relation → bổ sung knowledge graph**
- [ ] Web UI xem danh sách tài liệu đã index
- [ ] Web UI visualize knowledge graph (tài liệu + hội thoại)
- [ ] Admin panel: approval workflow, quản lý tài liệu
- [ ] Phân quyền truy cập theo user (tất cả thấy tất cả — MVP)

### Ngoài scope MVP

- Real-time sync phức tạp
- Multi-tenant / phân quyền theo phòng ban
- Video, DWG/DWT parsing
- Mobile app

---

## Cấu trúc thư mục (dự kiến)

```
SecondBrain/
├── backend/              # FastAPI — ingestion pipeline + query API
│   ├── ingestion/        # NAS connector, parser, chunker, graph builder
│   ├── retrieval/        # hybrid search, reranker
│   └── api/              # REST endpoints
├── frontend/             # React — web UI quản lý
├── docker-compose.yml    # Neo4j + backend + frontend
├── docs/
│   └── specs/            # Design docs từng tính năng
└── README.md
```

---

## Yêu cầu môi trường

- Docker & Docker Compose
- NAS có hỗ trợ SMB hoặc WebDAV
- LLM API key (Gemini Flash) **hoặc** Ollama chạy local

---

## Bắt đầu (WIP)

```bash
# Clone repo
git clone <repo-url>
cd SecondBrain

# Cấu hình môi trường
cp .env.example .env
# Điền NAS_URL, LLM_API_KEY...

# Chạy toàn bộ stack
docker-compose up -d
```

> Hướng dẫn chi tiết sẽ cập nhật khi MVP hoàn thiện.

---

## Tài liệu tham khảo

- [So sánh 11 tool RAG/AI](./AI_RAG_Knowledge_Management_Tools_Comparison.md)
- [LightRAG](https://github.com/HKUDS/LightRAG)
- [RAGFlow](https://github.com/infiniflow/ragflow)
- [Neo4j Community](https://neo4j.com/download/)
- [Arkon](https://github.com/contextmachine/arkon)

---

## Team

Dự án nội bộ — Robolinks Intern Program.
