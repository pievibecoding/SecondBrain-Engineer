# Requirements Document — PDF Parser Comparison & Quality Evaluation

## Introduction

Spec này xây dựng một môi trường đánh giá parser PDF cho tài liệu kỹ thuật Robolinks.
Động lực đến từ EXP-007: file `7. Ball Screws Selection Guide.pdf` cho thấy parser hiện tại
(`pdfplumber`) trả về text không rỗng nhưng chất lượng layout kém: bảng bị flatten, header/page
artifact lẫn vào nội dung, section/caption/table bị trộn, làm chunking và RAG phía sau yếu đi.

Mục tiêu là thêm parser comparison vào UI/Admin evaluation để phân biệt rõ:

```text
PDF source -> parser quality -> chunk quality -> retrieval context -> LLM answer
```

Spec này KHÔNG thay parser production ngay. V1 chỉ phục vụ evaluation và evidence gate.

**Definition of Done:**

- Admin UI cho phép chọn parser khi chạy evaluation.
- Có parser baseline hiện tại `pdfplumber`.
- Có parser alternative đầu tiên `PyMuPDF`.
- Có thiết kế để sau đó đánh giá `Docling` và `Marker`.
- Có table-aware extraction / normalization bước đầu.
- Có parser quality metrics.
- Có report JSON/Markdown và UI trực quan để so sánh parser + chunk strategy.
- Chỉ đề xuất production integration khi Diagnostics/RAG test chứng minh retrieval tốt hơn.

---

## Glossary

- **Parser quality:** Mức độ parser giữ được semantic structure của PDF: heading, paragraph, table, caption, formula, units.
- **Layout artifact:** Text rác do PDF layout/header/footer/page encoding, ví dụ `CC__006688...`.
- **Table-aware extraction:** Cách extract table giữ được column headers, row labels, units, values.
- **Parser matrix:** Ma trận so sánh parser x chunk strategy, ví dụ `pdfplumber + paragraph_merge`, `pymupdf + heading_table_aware`.
- **Evidence gate:** Điều kiện bằng chứng trước khi tích hợp vào production ingestion.
- **No production mutation:** Evaluation không ghi LightRAG documents, graph, vector DB, NAS state machine.

---

## Requirements

### Requirement 1 — Parser Comparison Evaluation Runner

**User Story:** As a Robolinks engineer, I want to compare multiple PDF parsers on the same document, so that I can identify whether poor RAG quality comes from parsing or chunking.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`
- **Reference:** EXP-007 PDF parser quality, pa3-design Section 5.1 (Ingestion workflow), Section 15 (Test strategy)

#### Acceptance Criteria

1. THE system SHALL support running parser comparison without mutating production NAS, LightRAG, Graphiti, PostgreSQL vector, or graph data.
2. THE runner SHALL accept selected source files from `local-nas`.
3. THE runner SHALL evaluate at least `pdfplumber` and `pymupdf` in V1.
4. THE runner SHALL keep parser output separate from chunking output.
5. THE runner SHALL continue evaluating remaining files/parsers when one parser fails.
6. THE runner SHALL write JSON/Markdown artifacts under `docs/experiments/artifacts/pdf-parser-comparison/`.
7. THE runner SHALL record parser name, version when available, latency, errors, and output stats.

---

### Requirement 2 — Admin UI Parser Comparison

**User Story:** As a Robolinks engineer, I want to run parser comparison from the Admin UI, so that I can self-test PDF documents without terminal commands.

## Steering & Skills

- **Steering:** `project-context.md`, `frontend-rules.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `frontend-design`, `fastapi-expert`, `quality-assurance`
- **Reference:** pa3-design Section 5.3 (Admin panel workflow), EXP-006 Adaptive Chunking UI, EXP-007 PDF parser quality

#### Acceptance Criteria

1. THE frontend SHALL add a parser selection UI to the evaluation console.
2. THE UI SHALL support selecting one or more parsers for a run.
3. THE UI SHALL preserve Component → Hook → api/ → Backend flow.
4. THE UI SHALL show parsed text preview per parser.
5. THE UI SHALL show parser quality metrics per parser.
6. THE UI SHALL show parser + chunk strategy matrix results.
7. THE UI SHALL provide `Copy Parsed Text`, `Copy Chunks`, `Copy JSON`, and `Copy Markdown`.
8. THE UI SHALL show full long text in scrollable panels without backend/frontend truncation.
9. WHEN a parser fails, THE UI SHALL show the parser-specific error while keeping other parser results visible.

---

### Requirement 3 — PyMuPDF Parser Adapter

**User Story:** As a developer, I want to add PyMuPDF as the first alternative PDF parser, so that I can compare a lightweight parser against the current pdfplumber baseline.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`
- **Reference:** EXP-007 recommended parser improvement plan

#### Acceptance Criteria

1. THE backend SHALL implement a `pymupdf` parser adapter behind a common parser interface.
2. THE adapter SHALL extract text block order in a deterministic way.
3. THE adapter SHOULD preserve page number metadata.
4. THE adapter SHOULD preserve block coordinates when available.
5. THE adapter SHALL normalize line endings to `\n`.
6. THE adapter SHALL return parser metadata including parser name and parse latency.
7. THE adapter SHALL not call external HTTP services.

---

### Requirement 4 — Future Docling and Marker Evaluation Path

**User Story:** As a maintainer, I want a documented path for heavier document parsers, so that we can evaluate Docling and Marker only after the lightweight baseline is measured.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-007 parser improvement plan

#### Acceptance Criteria

1. THE design SHALL define optional parser adapters for `docling` and `marker`.
2. THE system SHALL not require Docling or Marker dependencies for V1 startup.
3. WHEN optional parser dependencies are unavailable, THE API SHALL report parser unavailable rather than failing the whole run.
4. THE design SHALL document Docker image size, latency, and deployment risks for optional parsers.
5. THE design SHALL define criteria for when to move from PyMuPDF evaluation to Docling/Marker evaluation.

---

### Requirement 5 — Table-Aware Extraction and Normalization

**User Story:** As a retrieval evaluator, I want parser output to preserve table semantics, so that engineering specs, units, and values remain retrievable.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`
- **Reference:** EXP-007 table-aware extraction recommendation

#### Acceptance Criteria

1. THE parser evaluation SHALL detect table-like regions where possible.
2. THE parser evaluation SHOULD emit Markdown tables when table structure can be reconstructed.
3. THE output SHALL attach nearby heading/caption text to table blocks when possible.
4. THE output SHALL preserve units, row labels, and column labels when available.
5. THE output SHALL mark uncertain table extraction rather than pretending low-confidence flattened rows are valid tables.
6. THE report SHALL compare raw extracted text against normalized/table-aware text.
7. THE system SHALL keep original parsed text for debugging provenance.

---

### Requirement 6 — Parser Quality Metrics

**User Story:** As a maintainer, I want objective parser quality metrics, so that parser selection is not based only on subjective visual inspection.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-007 parser quality metrics

#### Acceptance Criteria

1. THE report SHALL include `char_count`, `line_count`, and `empty_line_ratio`.
2. THE report SHALL include `header_footer_artifact_count`.
3. THE report SHALL include `broken_token_count`.
4. THE report SHALL include `numeric_density`.
5. THE report SHALL include `heading_count`.
6. THE report SHALL include `table_candidate_count` and `reconstructed_table_count`.
7. THE report SHALL include `semantic_anchor_hit_rate`.
8. THE report SHALL include parse latency per parser.
9. THE report SHALL clearly flag parser output that is non-empty but low quality.

---

### Requirement 7 — Diagnostics/RAG Evidence Gate

**User Story:** As a project maintainer, I want production parser integration gated by RAG evidence, so that parser changes improve real retrieval instead of only local metrics.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `frontend-rules.md`, `lightrag-api.md`, `nas-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`
- **Reference:** pa3-design Section 5.1 (Ingestion workflow), lightrag-api.md, EXP-004 Retrieval Diagnostics, EXP-007 PDF parser quality

#### Acceptance Criteria

1. THE spec SHALL define a production integration gate before changing NAS ingest behavior.
2. THE gate SHALL require parser comparison evidence on at least one table-heavy PDF and one manual-style PDF.
3. THE gate SHALL require Diagnostics/RAG evidence showing improved retrieved context quality.
4. THE gate SHALL require no regression on DOCX/TXT ingestion.
5. THE future production integration SHALL preserve `X-Correlation-ID`.
6. THE future production integration SHALL preserve NAS folder semantics and status transitions.
7. THE future production integration SHALL include rollback to current parser behavior.
8. THE future production integration SHALL not hardcode LightRAG query mode away from `mix`.
