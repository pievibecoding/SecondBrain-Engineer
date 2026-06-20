# EXP-004 — Retrieval Diagnostics, Prompt Provenance, and Context Quality

**Date:** 2026-06-19  
**Status:** In Progress  
**Component:** Admin Diagnostics, LightRAG query `mode=mix`  
**Scenario:** Tìm cảm biến phù hợp cho chức năng phát hiện chai nước

---

## Mục tiêu

Ghi lại kinh nghiệm debug khi câu trả lời của LLM có vẻ hợp lý, nhưng tab `retrieval`
không hiển thị đầy đủ source tương ứng. Mục tiêu là hiểu rõ:

- Input thật vào LLM gồm những phần nào.
- Vì sao `retrieval.sources` không đủ để kết luận toàn bộ provenance.
- Khi nào `retrieval_failed` là đúng.
- Cần cải thiện Diagnostics thế nào để đánh giá retrieval/context/prompt chính xác hơn.

---

## Câu hỏi test

```text
Tôi cần tìm 1 cảm biến phù hợp cho chức năng phát hiện chai nước?
```

Theo hiểu biết domain từ các source file trong NAS, các candidate phù hợp gồm:

| Candidate | Ghi chú kỳ vọng |
|-----------|-----------------|
| Autonics BF4 Series | Dòng cảm biến quang/fiber amplifier liên quan ứng dụng phát hiện vật thể |
| Omron E3Z Series | Đặc biệt E3Z-B cho chai nhựa/vật thể trong suốt |
| Autonics BMS Series | Dòng photoelectric sensor có thông tin target/sensing setup |

Một prompt/context tốt cho câu hỏi này nên kéo được ít nhất các candidate chính,
hoặc giải thích rõ vì sao chỉ recommend một candidate.

---

## Setup Diagnostics

Diagnostics được thêm vào `Admin > Diagnostics` với các tab:

| Tab | Ý nghĩa |
|-----|---------|
| `parse` | Text backend parse lại từ file target nếu có `file_id` |
| `chunks` | Chunks đã lưu trong LightRAG/PostgreSQL nếu có document target |
| `retrieval` | References/chunk sources LightRAG trả về |
| `context` | Nội dung chunk/source được gom lại để debug |
| `prompt` | Full prompt LightRAG dựng bằng `only_need_prompt=true` |
| `llm` | Answer/model/latency từ query thường |
| `raw` | Raw JSON đầy đủ để copy log |

Điểm quan trọng: tab `prompt` mới là thứ gần nhất với input thật vào LLM.

---

## Quan sát 1 — Retrieval fail khi expected terms/source quá cụ thể

Expected terms đã nhập:

```text
BMS
E3Z
bottle
transparent
photoelectric
```

Expected source paths đã nhập:

```text
/path/to/Khuech dai quang Autonic.pdf
/path/to/Datasheet-cam-bien-tiem-can-Omron-E3Z-Series.pdf
/path/to/Sensorguong.pdf
```

Kết quả retrieval:

```json
{
  "status": "ok",
  "source_hit": false,
  "term_hit_rate": 0.5
}
```

Các sources nổi bật được trả về:

```text
nf-thread_catalog.pdf
dataSheet_WFS3-40B41CA71_6058651_en.pdf
```

### Kết luận

`retrieval_failed` là đúng theo tiêu chí đang đặt:

- `source_hit=false` vì expected source paths dùng placeholder `/path/to/...`, không khớp `nas_path` thật.
- `term_hit_rate=0.5` vì retrieved chunks không chứa đủ `BMS`, `E3Z`, `bottle`, `transparent`, `photoelectric`.

Expected source paths nên dùng substring thực tế, ví dụ:

```text
Khuech dai quang Autonic
E3Z
Sensorguong
```

Hoặc để trống source paths trước, chỉ test expected terms.

---

## Quan sát 2 — Retrieval sources không giải thích hết answer

Có trường hợp `retrieval.sources` hiển thị chủ yếu:

```text
nf-thread_catalog.pdf
dataSheet_WFS3-40B41CA71_6058651_en.pdf
```

nhưng LLM lại recommend:

```text
Omron E3Z-B Series
Datasheet-cam-bien-tiem-can-Omron-E3Z-Series.pdf
```

Nhìn bề mặt đây là mâu thuẫn hợp lý để nghi ngờ.

### Phân tích

LightRAG `mode=mix` không chỉ đưa document chunks vào LLM. Full prompt gồm:

```text
Role / Instructions
Knowledge Graph Data
Document Chunks
Reference Document List
User Query
```

Trong tab `prompt`, Knowledge Graph Data có các entity rất liên quan:

```text
E3Z-B61: Cảm biến quang điện dòng E3Z-B dành cho chai nhựa trong suốt, đầu ra NPN.
E3Z-B81: Cảm biến quang điện dòng E3Z-B dành cho chai nhựa trong suốt, đầu ra PNP.
```

Vì vậy LLM recommend E3Z-B có thể không phải hallucination. Nó có thể dựa trên
Knowledge Graph Data, dù tab `retrieval.sources` không show rõ source chunk tương ứng.

### Kết luận

Nhận định "source retrieval không có E3Z mà answer có E3Z là vô lý" chỉ đúng nếu
full prompt cũng không có E3Z.

Debug đúng phải kiểm tra:

```text
Ctrl+F trong tab prompt:
- E3Z
- E3Z-B
- Omron
- chai nhựa trong suốt
- transparent
```

Nếu có trong `Knowledge Graph Data`, answer có căn cứ từ graph.
Nếu không có ở cả prompt, đó mới là LLM hallucination hoặc dùng kiến thức ngoài context.

---

## Quan sát 3 — Prompt instruction tốt, context packaging chưa tốt

Full prompt có instruction khá tốt:

- Chỉ trả lời dựa trên context.
- Trả lời cùng ngôn ngữ với user query.
- Yêu cầu citations/reference.
- Nếu không đủ thông tin thì nói không đủ thông tin.

Nhưng prompt từng có kích thước rất lớn:

```text
char_count ≈ 165,717
```

Và chứa nhiều noise:

```text
cirtceleotohP srosneS
Fiber Units
Fork Sensors
Maintenance
Mounting notes
Bảng dimension bị vỡ
```

### Đánh giá

| Thành phần | Điểm | Nhận xét |
|------------|------|----------|
| Instruction quality | 8/10 | Rõ, có grounding, có citation format |
| Evidence relevance | 6/10 | Có E3Z trong graph, nhưng chunk source bị nhiễu |
| Noise control | 2/10 | Quá nhiều catalog/table/layout noise |
| Context size control | 1/10 | Prompt quá dài cho câu hỏi đơn giản |
| Final prompt quality | 5/10 | Có thể trả lời đúng nhưng không ổn định |

---

## Bài học chính

### 1. `retrieval.sources` không phải toàn bộ LLM input

Trong LightRAG `mix`, LLM input có cả graph data. Vì vậy chỉ nhìn tab `retrieval`
có thể kết luận sai.

Nguồn sự thật để debug answer là:

```text
prompt tab > context tab > retrieval tab
```

### 2. `retrieval_failed` có thể đúng dù answer nhìn có vẻ đúng

Nếu expected terms/source paths không xuất hiện trong retrieved chunks, Diagnostics báo fail là đúng.
Nhưng answer vẫn có thể đúng nếu graph data chứa bằng chứng.

Điều này cho thấy cần tách metric:

```text
chunk_retrieval_hit
graph_hit
prompt_hit
answer_hit
```

Không nên chỉ có một `term_hit_rate` chung trên chunk context.

### 3. Prompt tốt cần có candidate đầy đủ

Với câu hỏi phát hiện chai nước, prompt tốt nên chứa các candidate:

```text
Autonics BF4 Series
Omron E3Z Series / E3Z-B Series
Autonics BMS Series
```

Nếu prompt chỉ có E3Z nhưng thiếu BF4/BMS, thì retrieval/context vẫn chưa đạt kỳ vọng.

### 4. Source provenance của graph cần rõ hơn

Graph entity như `E3Z-B61` có thể được dùng để trả lời, nhưng Diagnostics hiện chưa show rõ:

```text
Entity này được extract từ file nào?
Từ chunk nào?
Reference/source gốc là gì?
```

Đây là khoảng trống lớn khi audit answer.

---

## Quy trình debug chuẩn sau experiment này

### Bước 1 — Chạy Diagnostics không expected terms

Mục tiêu: xem hệ thống tự retrieve gì.

Kiểm tra:

```text
retrieval.sources
context.char_count
prompt.char_count
llm.answer
```

### Bước 2 — Ctrl+F trong prompt

Tìm các term domain:

```text
BF4
BMS
E3Z
E3Z-B
bottle
transparent
plastic bottle
chai nhựa trong suốt
photoelectric
```

Nếu term có trong prompt nhưng không có trong `retrieval.sources`, khả năng cao nó đến từ graph.

### Bước 3 — Chạy lại với expected terms

Nên dùng terms theo ngôn ngữ tài liệu:

```text
BF4
BMS
E3Z
transparent
photoelectric
```

Không nên dùng `bottle` nếu tài liệu không ghi chữ đó.

### Bước 4 — Expected source paths dùng substring thật

Không dùng placeholder:

```text
/path/to/file.pdf
```

Dùng substring từ `nas_path` thật:

```text
E3Z
Sensorguong
Autonic
BMS
```

### Bước 5 — Phân loại lỗi

| Hiện tượng | Lỗi nằm ở |
|------------|-----------|
| Parsed text không có BF4/BMS/E3Z | Parser hoặc file chưa ingest đúng |
| Parsed có nhưng chunks không có | Chunking/indexing |
| Chunks có nhưng prompt không có | Retrieval/rerank/context budget |
| Prompt có nhưng answer không dùng | LLM generation/prompt instruction |
| Answer có nhưng prompt không có | Hallucination hoặc model dùng kiến thức ngoài context |

---

## Action items đề xuất

### Diagnostics V2

- Thêm tab `graph` để hiển thị Knowledge Graph Data riêng.
- Tách tab `prompt` thành các section:
  - `instructions`
  - `knowledge_graph_data`
  - `document_chunks`
  - `reference_document_list`
  - `user_query`
- Tính metric riêng:
  - `chunk_term_hit_rate`
  - `graph_term_hit_rate`
  - `prompt_term_hit_rate`
  - `answer_term_hit_rate`
  - `source_hit`
- Hiển thị source/provenance cho graph entity nếu LightRAG/PostgreSQL có metadata.
- Thêm "Top Evidence" view: các đoạn ngắn nhất có chứa expected terms/candidates.

### Retrieval / Context

- Giảm noise bằng rerank hoặc post-filter theo expected/domain terms.
- Ưu tiên candidate/model chunks hơn mounting/maintenance chunks.
- Tăng khả năng match query tiếng Việt với tài liệu tiếng Anh bằng query expansion:

```text
chai nước → water bottle, plastic bottle, transparent bottle, clear object
cảm biến phù hợp → sensor selection, photoelectric sensor, detection target
```

### Parser / Index

- Kiểm tra các file chứa BF4/BMS/E3Z có thực sự parse ra text sạch không.
- Với catalog PDF nhiều bảng, cân nhắc parser tốt hơn hoặc pre-processing bảng.
- Lưu page/chunk provenance chi tiết hơn để citation/debug có giá trị.

---

## Kết luận hiện tại

Experiment này cho thấy vấn đề không chỉ là "LLM ngu" hay "retrieval ngu".
Vấn đề chính là observability chưa đủ:

```text
retrieval.sources chỉ phản ánh document chunk references,
trong khi final prompt còn có Knowledge Graph Data.
```

Do đó, để đánh giá answer đúng/sai, phải xem tab `prompt`, không chỉ xem `retrieval`.

Với câu hỏi phát hiện chai nước, hệ thống đã có tín hiệu tốt ở graph (`E3Z-B61`, `E3Z-B81`),
nhưng prompt/context vẫn chưa tốt vì thiếu hoặc không làm nổi bật đầy đủ `BF4`, `BMS`, `E3Z`
và bị nhiễu nhiều bởi catalog chunks không liên quan.

