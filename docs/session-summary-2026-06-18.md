# Session Summary — 2026-06-18

**Chủ đề:** Testing LightRAG pipeline — LLM models, parser quality, VLM, và implement custom parser  
**Thời gian:** ~1 ngày làm việc  
**Kết quả chính:** Implement python-docx parser giải quyết vấn đề mất ~50% content khi ingest DOCX

---

## 1. Nhật ký thử nghiệm

### EXP-001 — LLM Model Comparison
**File:** `docs/experiments/EXP-001-lightrag-llm-comparison.md`

| Model | Kết quả |
|-------|---------|
| Gemini Free | Ổn nhưng rate limit 15 RPM |
| Ollama Qwen2.5:7B | Không load được — thiếu VRAM |
| Ollama Qwen2.5:3B | Load được, nhưng timeout + không follow JSON format cho entity extraction |
| Bluesminds GPT | Xử lý được 14 chunk, nhưng chậm, retry ~10 lần |

**Kết luận:** Gemini + `MAX_ASYNC_LLM=1` = ổn định nhất hiện tại. Entity extraction thành công 14/14 chunks không timeout.

---

### EXP-002 — Adaptive Chunking Evaluation
**File:** `docs/experiments/EXP-002-adaptive-chunking-evaluation.md`

Nghiên cứu thư viện [ekimetrics/adaptive-chunking](https://github.com/ekimetrics/adaptive-chunking) (LREC 2026). Kết luận: không giải quyết được vấn đề mất text vì vấn đề nằm ở tầng parser, không phải chunker. Adaptive Chunking là optimization, không phải fix.

---

### EXP-003 — Parser Quality Comparison
**File:** `docs/experiments/EXP-003-parser-quality-comparison.md`

So sánh 7 test cases trên cùng file `Hướng dẫn vận hành_SATO.docx`:

| Test | Parser | Chunks | Completeness | Thời gian |
|------|--------|--------|-------------|-----------|
| 1 | LightRAG native (DOCX) | 14 | ~50% — mất Alarm, History, Login, Bước 4–6 | ~4 phút |
| 2 | LightRAG native (PDF export) | 7 | ~35% — text nối liền, không có bảng | ~3 phút |
| 3 | python-docx DOM traversal | — | ✅ 100% — 94/94 paragraphs, 6/6 bảng | 0.4s |
| 4 | pdfplumber + pymupdf (PDF) | — | ~90% — 14 bảng detected | ~2s |
| 5 | Datasheet sensor PDF | — | Font encoding issue (MMooddeell) | — |
| 6 | VLM_PROCESS_ENABLE=true | 14 | Không hoạt động — src="" trong drawing tag | — |
| **7** | **python-docx → /documents/text** | **6** | **✅ 100% content** | **36s** |

**Root cause mất text:** LightRAG native parser xử lý DOCX theo XML block — text ngắn nằm giữa ảnh bị drop. python-docx DOM traversal đọc theo thứ tự paragraph-level nên không bỏ sót.

**VLM finding:** `VLM_PROCESS_ENABLE=true` không hoạt động vì native parser không embed image bytes vào `src` field trong sidecar. Cả DOCX lẫn PDF đều bị ảnh hưởng.

---

## 2. Phát hiện kỹ thuật quan trọng

### Parser stack tốt nhất cho từng loại file

| File type | Parser | Ghi chú |
|-----------|--------|---------|
| DOCX | `python-docx` DOM traversal | ✅ Implement xong |
| PDF text-based | `pdfplumber` (bảng) + `pymupdf` (text) | ✅ Implement xong |
| XLSX | `openpyxl` | ✅ Implement xong, chưa test |
| PPTX | LightRAG native | Chưa implement custom |
| DWG/Video/CAD | Metadata only | Không parse content |

### PostgreSQL connection issue
- Windows có PostgreSQL native chạy sẵn trên port 5432
- Docker postgres bị conflict → đổi expose port sang 5433 trong `docker-compose.local.yml`
- DBeaver connect qua `localhost:5433`, password `secondbrain`
- SQLTools bị bug với SCRAM-SHA-256 trên PG18 → không dùng được

---

## 3. Code đã implement

### Files mới/thay đổi

**`backend/services/document_parser.py`** *(mới)*
- Parser layer: python-docx, pdfplumber+pymupdf, openpyxl
- Fallback về LightRAG native nếu parse fail hoặc extension không support
- `parse_document()` sync + `parse_document_async()` async wrapper

**`backend/integrations/lightrag/ingest.py`** *(thêm method)*
- `ingest_text()` → `POST /documents/text` (bypass native parser)
- `ingest_document()` giữ nguyên → `POST /api/v1/docs` (LightRAG native, fallback)

**`backend/services/ingestion_service.py`** *(refactor)*
- Thêm `_ingest_with_parser()` — try pre-process trước, fallback về native
- Logic: parse → nếu ok gửi `/documents/text`, nếu fail/skip gửi `/api/v1/docs`

**`backend/requirements.txt`** *(thêm dependencies)*
- `python-docx==1.2.0`
- `pdfplumber==0.11.10`
- `pymupdf==1.27.2.3`
- `openpyxl==3.1.5`

### Scripts test

| Script | Mục đích |
|--------|---------|
| `scripts/test_docx_parser.py` | Test python-docx DOM traversal độc lập |
| `scripts/test_pdf_parser.py` | So sánh pdfplumber vs pymupdf |
| `scripts/test_pipeline_e2e.py` | Test end-to-end: parse → /documents/text → poll status |

### Docs tạo ra

| File | Nội dung |
|------|---------|
| `docs/experiments/EXP-001-lightrag-llm-comparison.md` | LLM model testing log |
| `docs/experiments/EXP-002-adaptive-chunking-evaluation.md` | Adaptive Chunking research |
| `docs/experiments/EXP-003-parser-quality-comparison.md` | Parser quality comparison (7 tests) |
| `docs/local-testing-guide.md` | Hướng dẫn test local: Docker, SQL queries, lỗi thường gặp |
| `.kiro/specs/robust-document-ingestion-pipeline/requirements.md` | 10 requirements cho parser pipeline cải tiến |

---

## 4. Config thay đổi

**`lightrag/.env`**
```ini
LLM_BINDING=openai
LLM_MODEL=gemini-3.1-flash-lite
LLM_BINDING_HOST=https://generativelanguage.googleapis.com/v1beta/openai/
MAX_ASYNC_LLM=1        # sequential để tránh rate limit
MAX_PARALLEL_INSERT=1
TIMEOUT_SECONDS=480
VLM_PROCESS_ENABLE=false  # không hoạt động với native parser
```

**`docker-compose.local.yml`**
```yaml
postgres:
  ports:
    - "5433:5432"  # tránh conflict với Windows PostgreSQL
```

---

## 5. Spec đã tạo

**`.kiro/specs/robust-document-ingestion-pipeline/requirements.md`**

10 requirements bao phủ:
1. Robust text extraction (không mất content)
2. Table extraction đúng hàng cột
3. Metadata-only mode cho binary files
4. Image handling strategy (OCR/VLM optional)
5. Config-driven parser selection
6. Resume-on-failure (chunk checkpointing)
7. Parse completeness validation
8. Performance ≤ 5 phút cho file 20 trang
9. Structured logging per-step
10. NasFile state machine integration

---

## 6. Việc còn lại (TODO)

- [ ] Test XLSX với openpyxl
- [ ] Test PDF pipeline qua backend (ingest_service mới)
- [ ] Test chat query với doc đã ingest bằng python-docx để verify entity quality
- [ ] Implement image caption (extract ảnh → gọi Vision LLM → bake vào text)
- [ ] Implement PPTX parser
- [ ] Multi-file ingest test
- [ ] Generate tech design và tasks cho spec `robust-document-ingestion-pipeline`
