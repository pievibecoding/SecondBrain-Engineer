# EXP-002 — Đánh giá Adaptive Chunking cho SecondBrain

**Date:** 2026-06-18  
**Status:** Research / Pre-implementation  
**Ref:** https://github.com/ekimetrics/adaptive-chunking (LREC 2026)

---

## Tóm tắt

Adaptive Chunking là framework tự động chọn chiến lược chia nhỏ văn bản (chunking)
tối ưu nhất cho từng tài liệu, thay vì dùng một kích thước cố định cho tất cả.
Được chấp nhận tại hội nghị khoa học LREC 2026.

---

## Cách nó hoạt động (3 bước chính)

```
Tài liệu thô
    → [1] Parse cấu trúc (Docling — nhận diện bảng, tiêu đề, danh sách)
    → [2] Chạy 3–5 chiến lược chia chunk song song (RecursiveSplitter, SemanticSplitter, LLM-Regex...)
    → [3] Chấm điểm mỗi chiến lược bằng 5 chỉ số nội tại → chọn chiến lược thắng
    → Trả về danh sách chunks tối ưu
```

**5 chỉ số chấm điểm (không cần dữ liệu gán nhãn):**

| Chỉ số | Đo lường |
|--------|----------|
| SC — Size Compliance | Chunk có vừa giới hạn token không? |
| ICC — Intrachunk Cohesion | Các câu trong 1 chunk có cùng chủ đề không? |
| DCC — Doc Contextual Coherence | Chunk có liền mạch với phần xung quanh không? |
| BI — Block Integrity | Bảng biểu/danh sách có bị cắt ngang không? |
| RC — Reference Completeness | Đại từ thay thế ("nó", "dự án này") có bị tách khỏi chủ ngữ không? |

---

## Điểm tích hợp vào SecondBrain

LightRAG v1.5 **có endpoint nhận text thô** — không cần đụng vào LightRAG:

```
POST /documents/text
Body: { "text": "...", "file_source": "...", "chunking": {...} }
```

Vị trí can thiệp duy nhất là **backend**, trước khi gọi LightRAG:

```
Hiện tại:
ingestion_service.py → ingest.py → POST /api/v1/docs  (gửi file_path, LightRAG tự parse+chunk)

Sau khi tích hợp:
ingestion_service.py → [Docling parse + Adaptive Chunking] → ingest.py → POST /documents/text
                                                                           (gửi text đã chunk sẵn)
```

Chỉ cần thêm 1 bước vào `ingestion_service.py` và thêm method vào `LightRAGIngestClient` —
**không đụng đến LightRAG, không rebuild Docker image.**

---

## Đánh giá thực tế cho SecondBrain

### Lợi ích rõ ràng

- **Bảng BOM nhiều cột** trong Excel/PDF kỹ thuật sẽ không bị cắt ngang dòng nhờ chỉ số BI
- **Tài liệu SOP** dạng danh sách bước thực hiện sẽ được giữ nguyên vẹn từng bước
- **Trích xuất thực thể của LightRAG sẽ chính xác hơn** vì nhận được chunk có ngữ nghĩa trọn vẹn
- Giảm số chunk rác → giảm số lần gọi LLM extraction → **giảm chi phí + tốc độ nhanh hơn**

### Rủi ro / Nhược điểm

- **Docling nặng:** Nhận diện bố cục bằng AI, tốn CPU đáng kể — ingest sẽ chậm hơn ~3–5x
  so với hiện tại (đặc biệt trên máy không có GPU)
- **Thêm dependency:** `adaptive-chunking`, `docling` vào `requirements.txt` backend
- **Chưa test tiếng Việt:** Các chỉ số ICC/DCC dùng embedding để đo ngữ nghĩa —
  cần dùng `bge-m3` (đã config sẵn trong `lightrag/.env`) thay vì model English-only
- **Maturity của thư viện:** Mới được accept tại LREC 2026, chưa battle-tested ở production

### Không phải giải pháp cho vấn đề LLM hiện tại

Adaptive Chunking **không giải quyết** vấn đề rate limit / retry của LLM (EXP-001).
Nó cải thiện _chất lượng_ đầu vào cho LightRAG, không cải thiện _độ ổn định_ của LLM calls.
Cần giải quyết EXP-001 trước.

---

## Kết luận

| Câu hỏi | Trả lời |
|---------|---------|
| Có áp dụng được không? | Có — tích hợp ở tầng backend, không đụng LightRAG |
| Nên làm ngay không? | Không — giải quyết LLM stability (EXP-001) trước |
| Ưu tiên khi nào? | Khi ingest ổn định rồi, muốn cải thiện chất lượng extraction |
| Rủi ro lớn nhất? | Docling chậm trên máy yếu + thư viện còn mới |

---

## Hướng tiếp theo (nếu muốn thử)

- [ ] Benchmark Docling parse tốc độ trên 1 file PDF kỹ thuật thực tế (~20 trang)
- [ ] Test `bge-m3` (đã có) với câu tiếng Việt để đánh giá ICC/DCC accuracy
- [ ] Thử semantic chunking đơn giản hơn (LangChain `SemanticChunker`) trước khi dùng full Adaptive Chunking
- [ ] Đọc paper gốc: https://huggingface.co/papers/2603.25333
