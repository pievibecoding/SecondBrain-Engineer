# EXP-005 — Knowledge Graph Entity Resolution, Hub Bias, and Multilingual Retrieval

**Date:** 2026-06-20  
**Status:** Research / Remediation Plan  
**Component:** LightRAG Knowledge Graph, Admin Graph UI, Retrieval Diagnostics  
**Scenario:** Entity lớn/nhỏ, legend/type, duplicate entity, đa tài liệu và đa ngôn ngữ

---

## Mục tiêu

Ghi lại các vấn đề đã phát hiện khi quan sát graph và debug retrieval:

- Vì sao có entity lớn và entity nhỏ.
- Legend/type của node được quyết định bởi gì.
- Các node gần nhau có chắc là có quan hệ hay không.
- Hai tài liệu khác nhau có entity giống nhau thì graph xử lý thế nào.
- Hai tài liệu cùng nội dung nhưng khác ngôn ngữ thì rủi ro gì.
- Entity lớn/hub ảnh hưởng retrieval ra sao.
- Phương án dự kiến để khắc phục các vấn đề trên.

---

## Bối cảnh

Khi test câu hỏi:

```text
Tôi cần tìm 1 cảm biến phù hợp cho chức năng phát hiện chai nước?
```

Graph UI cho thấy nhiều node lớn/hub, ví dụ:

```text
CSS High Resolution
E3Z
BR Series
LR-TB Series
Sensor
Photoelectric Sensors
```

Một số candidate đúng theo domain:

```text
Autonics BF4 Series
Omron E3Z Series
Autonics BMS Series
```

Nhưng prompt/retrieval đôi khi kéo nhiều context nhiễu:

```text
nf-thread_catalog.pdf
dataSheet_WFS3-40B41CA71_6058651_en.pdf
Fiber mounting
Fork sensor label detection
Maintenance
Broken catalog tables
```

Điều này dẫn tới prompt lớn, graph evidence bị trộn, và khó biết answer dựa trên source nào.

---

## Vấn đề 1 — Vì sao có thực thể lớn?

Trong graph visualization, node lớn thường là node có nhiều cạnh hoặc centrality cao.

Các nguyên nhân thường gặp:

### 1. Nhiều tài liệu nhắc tới cùng entity

Ví dụ `Sensor`, `Photoelectric Sensor`, `E3Z` xuất hiện trong nhiều PDF/catalog/manual.
Mỗi lần LightRAG extract được relation, node đó có thêm cạnh.

```text
Sensor
→ E3Z
→ BMS
→ BF4
→ Output Mode
→ Housing
→ Sensing Distance
→ Indicator
```

### 2. Entity quá chung chung

Các entity như sau dễ trở thành hub:

```text
Sensor
Cảm biến
Photoelectric Sensor
Output Mode
Housing
Indicator
Data
Method
```

Chúng đúng về mặt ngữ nghĩa nhưng quá rộng, nên dễ kéo nhiều relation không liên quan trực tiếp tới câu hỏi.

### 3. Document/product chính có nhiều thuộc tính

Một node như `CSS High Resolution` có thể là tên sản phẩm/tài liệu. Nếu manual nói rất nhiều về nó:

```text
housing
output mode
job
teach-in
display
maintenance
IP rating
connection
```

thì node này trở thành node lớn dù không liên quan tới câu hỏi hiện tại.

### 4. UI phóng to theo degree/importance

Kích thước node trong graph UI thường phản ánh:

```text
- degree cao
- nhiều relation
- centrality cao
- weight/frequency cao
```

Node lớn không đồng nghĩa với "phù hợp nhất cho query".

---

## Vấn đề 2 — Legend/type được quyết định bởi gì?

Legend trong graph UI:

```text
Artifact
Unknown
Organization
Method
Natural Object
Concept
Data
Content
Person
Other
Location
Event
```

được quyết định bởi `entity_type` mà LLM/entity extractor gán trong lúc ingest.

Luồng:

```text
Document
→ parser
→ chunks
→ LLM extraction
→ entity name + entity type + description + relations
→ graph storage
→ UI tô màu theo entity type
```

Ví dụ:

```text
E3Z-B61 → Artifact
Omron → Organization
Output Mode → Concept / Method
IP67 → Concept / Data
Plastic bottle → Natural Object
```

### Rủi ro

LLM có thể gán type không nhất quán:

```text
Photoelectric Sensor → Artifact
Photoelectric Sensors → Concept
Cảm biến quang điện → Unknown
Sensor → Artifact / Concept
```

Điều này làm graph khó clean, khó merge entity, và có thể ảnh hưởng retrieval/rerank.

---

## Vấn đề 3 — Node gần nhau có chắc là có quan hệ không?

Không chắc.

Trong force-directed graph, node gần nhau có thể vì:

```text
1. Có edge trực tiếp.
2. Có edge gián tiếp qua hub chung.
3. Cùng kết nối tới node lớn như Sensor/Photoelectric Sensor.
4. Layout engine kéo gần vì lực graph, không phải vì quan hệ domain mạnh.
```

Ví dụ gần nhau có giá trị thấp:

```text
E3Z-B61 → Sensor ← WFS Fork Sensor
```

Hai node cùng là sensor nhưng không cùng bài toán.

Ví dụ gần nhau có giá trị cao:

```text
E3Z-B61 → suitable_for → transparent plastic bottle
BMS Series → detects → transparent object
```

Muốn đánh giá graph tốt, không chỉ nhìn khoảng cách. Cần xem:

```text
- Có edge trực tiếp không?
- Edge label là gì?
- Cùng nối qua hub nào?
- Hub đó chung chung hay specific?
- Relation có source/citation không?
```

---

## Vấn đề 4 — Hai tài liệu khác nhau có thực thể giống nhau nhưng type khác

Nếu hai tài liệu nhắc cùng một thực thể nhưng LLM extract khác tên hoặc khác type, có thể xảy ra:

```text
1 node được merge
```

hoặc:

```text
2+ node riêng biệt
```

Ví dụ cùng một concept:

```text
Document A: E3Z-B Series
Document B: Omron E3Z Series
```

Nếu normalize tốt:

```text
E3Z-B Series / Omron E3Z Series → 1 canonical node
```

Nếu normalize kém:

```text
E3Z
E3Z Series
E3Z-B
E3Z-B61
Omron E3Z-B61 2M
```

có thể trở thành nhiều node rời rạc.

### Name giống nhưng type khác

Nếu name giống hệt:

```text
Sensor / Artifact
Sensor / Concept
```

khả năng cao vẫn là một node `Sensor`, nhưng type/description có thể bị chọn một bên hoặc merge tùy implementation.

Nếu name khác ngôn ngữ:

```text
Sensor
Cảm biến
```

khả năng cao là hai node riêng.

Đây là vấn đề entity resolution / entity deduplication / canonicalization.

---

## Vấn đề 5 — Hai tài liệu giống nội dung nhưng khác ngôn ngữ

Nếu hai tài liệu có cùng nội dung nhưng khác ngôn ngữ, graph có thể xử lý theo ba kịch bản.

### Kịch bản tốt

Gộp được entity song ngữ:

```text
Photoelectric Sensor
Cảm biến quang điện
→ Photoelectric Sensor
```

Hoặc:

```text
Omron E3Z Series
Dòng Omron E3Z
→ Omron E3Z Series
```

Graph mạnh hơn vì cùng entity có evidence từ cả tiếng Anh và tiếng Việt.

### Kịch bản thường gặp

Tạo node riêng:

```text
Photoelectric Sensor
Cảm biến quang điện
```

hoặc:

```text
Transparent bottle
Chai nhựa trong suốt
```

Evidence bị tách đôi, retrieval dễ bỏ sót.

### Kịch bản xấu

Tách node và type khác nhau:

```text
Photoelectric Sensor        Artifact
Cảm biến quang điện         Concept / Unknown

Transparent bottle          Natural Object
Chai nước                   Artifact / Unknown
```

Graph bị phân mảnh, query tiếng Việt khó kéo tài liệu tiếng Anh.

---

## Vấn đề 6 — Hub bias ảnh hưởng retrieval

Entity lớn/hub có thể làm retrieval bị hút vào context quá rộng.

Ví dụ:

```text
Query: cảm biến phát hiện chai nước
→ match Sensor / Photoelectric Sensor
→ kéo rất nhiều relation/chunk
→ prompt có cả fork sensor, fiber mounting, maintenance
→ candidate đúng BF4/BMS/E3Z bị chôn
```

Node lớn có ích khi hỏi tổng quan:

```text
Có những loại cảm biến nào?
Photoelectric sensor là gì?
```

Nhưng với câu hỏi chọn model cụ thể, node nhỏ/cụ thể quan trọng hơn:

```text
E3Z-B61
E3Z-B81
Autonics BF4 Series
Autonics BMS Series
```

---

## Nhận định hiện tại

Graph hiện tại có thông tin đúng, nhưng observability và retrieval control chưa đủ.

Các dấu hiệu đã thấy:

- Prompt có thể rất lớn.
- Context bị nhiễu bởi catalog/table/mounting/maintenance.
- `retrieval.sources` không đại diện toàn bộ input vào LLM vì `mode=mix` còn đưa graph data.
- Entity lớn như `Sensor`, `Photoelectric Sensors`, `CSS High Resolution` có thể kéo context rộng.
- Entity cụ thể như `E3Z`, `BF4 Series`, `BMS Series` cần được ưu tiên hơn cho bài toán chọn sensor.
- Duplicate/synonym đa ngôn ngữ có thể làm graph phân mảnh.

---

## Phương án khắc phục đề xuất

### Phase 1 — Diagnostics tốt hơn

Mục tiêu: nhìn rõ lỗi nằm ở graph, chunk, prompt hay answer.

Việc cần làm:

- Thêm tab `graph` trong Diagnostics để hiển thị Knowledge Graph Data riêng.
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
- Hiển thị prompt size warning:

```text
OK: < 20k chars
Warning: 20k-60k chars
Bad: > 60k chars
```

- Hiển thị "Top Evidence" view: đoạn ngắn nhất chứa expected terms/candidates.

### Phase 2 — Query Expansion song ngữ

Mục tiêu: nối câu hỏi tiếng Việt với tài liệu/catalog tiếng Anh.

Ví dụ:

```text
chai nước
→ water bottle
→ plastic bottle
→ transparent bottle
→ clear object
→ transparent object

cảm biến quang điện
→ photoelectric sensor
→ optical sensor
→ retroreflective sensor
```

Query nội bộ nên có dạng:

```text
Tôi cần tìm cảm biến phát hiện chai nước.
Related terms: water bottle, plastic bottle, transparent bottle, clear object,
transparent object, photoelectric sensor, retroreflective sensor.
```

Với case sensor:

```text
Expanded candidates:
- Omron E3Z
- Omron E3Z-B
- Autonics BF4
- Autonics BMS
```

### Phase 3 — Alias / Canonical Dictionary

Tạo dictionary domain để chuẩn hóa các entity quan trọng.

Ví dụ:

```text
Omron E3Z Series:
- E3Z
- E3Z-B
- E3Z-B61
- E3Z-B81
- Omron E3Z
- Dòng E3Z

Autonics BMS Series:
- BMS
- BMS Series
- Autonics BMS
- BMS2M
- BMS5M

Autonics BF4 Series:
- BF4
- BF4 Series
- BF4R
- BF4G
- Fiber amplifier BF4

Photoelectric Sensor:
- cảm biến quang điện
- photoelectric sensor
- optical sensor
```

Dùng dictionary ở 3 chỗ:

```text
1. Trước retrieval: expand query.
2. Sau graph extraction: chuẩn hóa/alias entity.
3. Trong Graph UI: group alias về canonical node.
```

### Phase 4 — Rerank / Filter sau retrieval

Sau khi LightRAG retrieve top N chunks/entities, backend chấm lại theo domain relevance.

Boost nếu có:

```text
E3Z
BF4
BMS
transparent
plastic bottle
photoelectric
sensing target
sensing distance
NPN
PNP
```

Penalize nếu có:

```text
mounting screw
maintenance
fork sensor label detection
housing cleaning
zip tie
broken dimension table
```

Flow đề xuất:

```text
LightRAG retrieve top 30
→ Backend rerank/filter
→ còn top 5-10 evidence tốt nhất
→ tạo prompt gọn hơn
```

### Phase 5 — Graph Cleanup / Entity Resolution

Có hai mức.

#### Mức an toàn: thêm relation alias/equivalent

Không merge node thật ngay, chỉ thêm relation:

```text
Cảm biến quang điện --equivalent_to--> Photoelectric Sensor
Chai nước --equivalent_to--> Water Bottle
E3Z --alias_of--> Omron E3Z Series
BMS --alias_of--> Autonics BMS Series
BF4 --alias_of--> Autonics BF4 Series
```

Ưu điểm:

- Ít rủi ro mất dữ liệu.
- Dễ rollback.
- Giữ source gốc.

#### Mức mạnh: merge canonical node

Gộp node thật:

```text
E3Z, E3Z-B, Omron E3Z Series → Omron E3Z Series
BMS, BMS Series → Autonics BMS Series
BF4, BF4 Series → Autonics BF4 Series
```

Ưu điểm:

- Graph sạch hơn.
- Retrieval tốt hơn.

Rủi ro:

- Merge sai làm hỏng graph.
- Cần audit/provenance trước khi merge.

---

## Acceptance Criteria cho cải thiện

Với câu hỏi:

```text
Tôi cần tìm 1 cảm biến phù hợp cho chức năng phát hiện chai nước?
```

Prompt tốt hơn nên có:

```text
Omron E3Z / E3Z-B
Autonics BF4
Autonics BMS
transparent bottle / plastic bottle / clear object
photoelectric sensor
sensing target / sensing distance
```

Prompt không nên bị thống trị bởi:

```text
CSS maintenance
fork sensor label detection
fiber zip tie mounting
broken catalog dimension tables
generic Sensor hub
```

Metric kỳ vọng:

| Metric | Target |
|--------|--------|
| prompt char_count | < 20,000 preferred |
| top candidate coverage | BF4, BMS, E3Z xuất hiện |
| graph hub ratio | entity generic không vượt quá 30% graph context |
| chunk noise ratio | mounting/maintenance noise thấp |
| answer provenance | mỗi recommendation có source hoặc graph provenance |

---

## Kết luận

Vấn đề hiện tại không chỉ nằm ở model LLM. Các rủi ro chính nằm ở:

```text
entity extraction inconsistency
duplicate/cross-language entity fragmentation
generic hub bias
retrieval không rerank theo domain
prompt/context quá lớn và nhiễu
graph provenance chưa đủ rõ
```

Hướng khắc phục nên đi theo thứ tự:

```text
1. Diagnostics observability
2. Query expansion song ngữ
3. Alias/canonical dictionary
4. Rerank/filter context
5. Graph cleanup/entity resolution
```

Đây là hướng giúp SecondBrain trả lời ổn định hơn cho các bài toán kỹ thuật thực tế,
đặc biệt là khi user hỏi tiếng Việt nhưng tài liệu NAS có nhiều catalog tiếng Anh.

