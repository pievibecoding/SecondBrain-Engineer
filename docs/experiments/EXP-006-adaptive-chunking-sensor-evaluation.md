# EXP-006 — Adaptive Chunking Sensor Evaluation

**Date:** 2026-06-20  
**Status:** Initial Result  
**Component:** Offline adaptive chunking evaluation harness  
**Spec:** `.kiro/specs/adaptive-chunking-evaluation`

---

## Mục tiêu

Chạy thử offline evaluation cho case sensor để xem chunking strategy khác baseline có giúp
giảm noise hoặc cải thiện candidate evidence cho câu hỏi:

```text
Tôi cần tìm 1 cảm biến phù hợp cho chức năng phát hiện chai nước?
```

Candidate kỳ vọng:

```text
Omron E3Z / E3Z-B
Autonics BMS
Autonics BF4
```

---

## Cách chạy

```powershell
python tools/experiments/adaptive-chunking/run_evaluation.py `
  --config tools/experiments/adaptive-chunking/config.sensor.json
```

Artifacts:

- `docs/experiments/artifacts/adaptive-chunking/sensor-adaptive-chunking.json`
- `docs/experiments/artifacts/adaptive-chunking/sensor-adaptive-chunking.md`
- `docs/experiments/artifacts/adaptive-chunking/chunks/*.json`

---

## Kết quả ban đầu

Report hiện tại trả:

```text
Recommendation: recommended
Documents: 3
Evaluable documents: 3
Average candidate coverage delta: 0.0
Average noise delta: -0.333333
```

Diễn giải:

- Candidate coverage chưa tăng so với baseline trong lần chạy đầu.
- Noise giảm nhẹ ở một số strategy.
- Evidence E3Z được giữ khá rõ trong chunks.
- Đây là kết quả khởi đầu, chưa đủ để quyết định tích hợp production.

---

## Lưu ý

Lần chạy này dùng local fallback strategies:

```text
fixed_chars
paragraph_merge
heading_table_aware
```

Chưa clone/tích hợp trực tiếp upstream `ekimetrics/adaptive-chunking`. Bước tiếp theo nên là
thử upstream adapter nếu dependency setup ổn, rồi so sánh lại với local fallback.

---

## UI

Đã thêm Admin UI read-only viewer:

```text
/admin/evaluations/adaptive-chunking
```

UI hiển thị:

- verdict/recommendation
- coverage delta
- noise delta
- per-document winning strategy
- baseline vs adaptive metrics
- top evidence chunks
- noisy chunks
- raw JSON/Markdown copy

---

## Kết luận tạm thời

Adaptive/structure-aware chunking có tín hiệu giúp giảm noise nhẹ nhưng chưa chứng minh cải thiện
candidate coverage cho BF4/BMS/E3Z trong lần chạy đầu. Cần tiếp tục:

1. Thử upstream `ekimetrics/adaptive-chunking`.
2. Tinh chỉnh domain metrics cho sensor documents.
3. Kết hợp query expansion/rerank như EXP-005 đề xuất.
4. So sánh prompt/retrieval sau khi đưa selected chunks vào một sandbox index hoặc test retriever riêng.

