# EXP-001 — LightRAG LLM Model Comparison

**Date:** 2026-06-18  
**Component:** LightRAG v1.5

---

## Kết quả

| Model | Chất lượng | Vấn đề | Gốc rễ vấn đề |
|-------|------------|--------|----------------|
| Gemini (các model free) | Ổn | Rate limit — bị giới hạn số request/phút khi xài free tier | Free tier chỉ ~15 RPM, LightRAG gửi nhiều request song song khi chunk |
| Ollama Qwen2.5:7B (local) | Chưa test được | Máy không đủ VRAM để load model | Qwen2.5:7B cần ~5GB VRAM — model không load được từ đầu, không liên quan số chunk |
| GPT-4.1-mini, GPT-4.2-chat, GPT-4.5 qua Bluesminds | Xử lý được tài liệu 14 chunk | Response chậm, cần retry ~10 lần mới hoàn thành ingest | Proxy API latency cao + timeout dưới tải song song |

> **Lưu ý quan trọng:** Với Ollama, vấn đề là **VRAM không đủ để load model** —
> dù tài liệu có 1 chunk hay 100 chunk đều thất bại như nhau.
> Số chunk nhiều chỉ ảnh hưởng đến thời gian xử lý và số lần gọi LLM, không phải nguyên nhân crash.

---

## Trạng thái hiện tại

Chưa có model nào đáp ứng đủ yêu cầu. Cần tiếp tục tìm phương án.

---

## Các lựa chọn Ollama nhẹ hơn cho máy hiện tại

| Model | VRAM cần | Tiếng Việt | Ghi chú |
|-------|----------|------------|---------|
| Qwen2.5:7B | ~5GB | Tốt | ❌ Máy hiện tại không load được |
| Qwen2.5:3B | ~2GB | Khá | ✅ Khuyên dùng nếu muốn test local |
| Llama-3.2:3B | ~2GB | Trung bình | ✅ Load được nhưng tiếng Việt kém hơn Qwen |
| Qwen2.5:1.5B | ~1.5GB | Yếu | ✅ Load được, chất lượng thấp |

→ Nếu muốn test Ollama local: dùng **Qwen2.5:3B** thay vì Llama-3.2:3B vì Qwen tốt hơn cho tiếng Việt.

---

## Hướng tiếp theo

- [x] Đổi sang Qwen2.5:3B via Ollama — đang test
- [ ] Giảm `MAX_ASYNC_LLM=1` nếu muốn test Gemini Free ổn định (tuần tự, tránh rate limit)
- [ ] Thử Gemini paid tier để bỏ rate limit hoàn toàn
- [ ] Investigate tại sao Bluesminds chậm (network? cold start? cần tăng timeout?)
- [ ] Chờ có server GPU (RTX 4060 Ti 16GB) để chạy Qwen2.5:7B đúng cách — xem `project-context.md` Section 4

---

## Các ý tưởng đã đánh giá — KHÔNG ưu tiên hiện tại

### Failover multi-LLM (Gemini → Bluesminds → Ollama)
**Concept tốt, nhưng cách implement bị giới hạn bởi kiến trúc:**
LightRAG chạy như Docker service độc lập — không thể inject `llm_model_func` từ backend.
Muốn làm đúng cần dùng **LiteLLM proxy** đứng trước LightRAG (LightRAG gọi 1 endpoint,
LiteLLM lo fallback). Không cần fork LightRAG, dễ maintain khi upgrade version.

### 10 API keys Bluesminds song song (1 key = 1 chunk)
**Khả thi về mặt kỹ thuật, nhưng có rủi ro:**
- Bluesminds có thể detect nhiều key từ cùng IP gọi song song → block toàn bộ
- DB write bottleneck: 10 LLM responses về cùng lúc → race condition khi LightRAG merge entity vào graph
- `MAX_PARALLEL_INSERT=2` giúp giảm nhưng không triệt để
- Phù hợp để thử nghiệm, **không phù hợp cho production**
