# Requirements Document

## Introduction

Spec này xây dựng một experiment/offline evaluation pipeline cho **Adaptive Chunking**
trong SecondBrain. Mục tiêu là kiểm chứng liệu `ekimetrics/adaptive-chunking`
hoặc một mini adaptive chunking tương đương có cải thiện chất lượng chunk/retrieval
cho tài liệu kỹ thuật Robolinks hay không, trước khi tích hợp vào ingestion production.

Trọng tâm ban đầu là case sensor:

```text
Tôi cần tìm 1 cảm biến phù hợp cho chức năng phát hiện chai nước?
```

Các candidate kỳ vọng trong source NAS:

```text
Autonics BF4 Series
Omron E3Z Series / E3Z-B Series
Autonics BMS Series
```

Spec này KHÔNG thay đổi behavior chat/ingestion production trong V1. Tất cả thử nghiệm
chạy offline, xuất report để đánh giá.

**Definition of Done:**

- Có script offline chạy adaptive chunking evaluation trên tập file sensor.
- Có output JSON/Markdown so sánh chunk hiện tại và chunk adaptive.
- Có UI trong Admin để xem trực quan kết quả evaluation từ artifacts/report.
- Có UI trong Admin để tự chạy test mới từ danh sách file local-nas và terms mà không cần terminal.
- Report trả lời rõ adaptive chunking có giảm noise, giữ block/spec tốt hơn, và tăng candidate coverage hay không.
- Có EXP-006 ghi lại kết quả experiment.
- Không làm thay đổi luồng NAS ingest/LightRAG production khi chưa có quyết định tích hợp.

---

## Glossary

- **Adaptive Chunking:** Framework chọn strategy chunking tốt nhất theo từng tài liệu bằng intrinsic metrics.
- **Candidate coverage:** Mức độ chunk/prompt chứa các candidate domain như BF4, BMS, E3Z.
- **Noise:** Nội dung không hữu ích cho query hiện tại như mounting screw, maintenance, broken dimension table, fork label sensor.
- **Current chunks:** Chunks hiện đang nằm trong LightRAG/PostgreSQL sau ingestion hiện tại.
- **Adaptive chunks:** Chunks sinh bởi adaptive chunking experiment.
- **Intrinsic metrics:** Các chỉ số đánh giá chunk không cần labeled QA như RC, ICC, DCC, BI, SC.
- **No production mutation:** Experiment không ghi vào LightRAG production tables và không thay đổi `NasFile.status`.

---

## Requirements

### Requirement 1 — Offline Experiment Harness

**User Story:** As a Robolinks engineer, I want to run adaptive chunking offline on selected NAS documents, so that I can evaluate chunk quality without affecting production ingestion.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-002 adaptive chunking evaluation, EXP-003 parser quality comparison, EXP-004 retrieval diagnostics, EXP-005 graph entity resolution

#### Acceptance Criteria

1. THE experiment SHALL provide a script under `tools/experiments/adaptive-chunking/`.
2. THE script SHALL accept a config/list of input files or parsed text files.
3. THE script SHALL run without modifying backend database rows, LightRAG documents, or NAS file status.
4. THE script SHALL write all outputs under `docs/experiments/artifacts/adaptive-chunking/` or another clearly marked artifact directory.
5. THE script SHALL log input file path, parser source, chunking strategies evaluated, metrics, and selected strategy.
6. WHEN an input file cannot be parsed or evaluated, THE script SHALL record the error in the report and continue with remaining files.

---

### Requirement 2 — Source Text Extraction for Evaluation

**User Story:** As a developer, I want the experiment to reuse current parser output where possible, so that chunking quality can be compared independently from parser quality.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-003 parser quality comparison, lightrag-api.md parser pipeline

#### Acceptance Criteria

1. THE experiment SHALL support using already exported `parsed_text` from Diagnostics.
2. THE experiment MAY support parsing source files directly as a convenience path.
3. THE report SHALL distinguish parser quality issues from chunking strategy issues.
4. THE report SHALL include `char_count`, `line_count`, and basic noise indicators for source text.
5. THE experiment SHALL NOT require uploading documents through the UI to run.

---

### Requirement 3 — Chunking Strategy Evaluation

**User Story:** As a retrieval evaluator, I want to compare multiple chunking strategies on the same document, so that the best strategy can be selected per document type.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-002 adaptive chunking evaluation, ekimetrics/adaptive-chunking framework

#### Acceptance Criteria

1. THE experiment SHALL evaluate at least the current/fixed chunking baseline.
2. THE experiment SHALL evaluate at least one structure-aware or adaptive strategy.
3. THE experiment SHOULD support plugging in `ekimetrics/adaptive-chunking` if dependencies can be installed.
4. WHEN the upstream library cannot be installed or run, THE experiment SHALL support a mini fallback evaluator with local strategies.
5. THE metrics SHALL include candidate coverage for BF4, BMS, E3Z, and related transparent-bottle terms.
6. THE metrics SHALL include noise indicators for mounting, maintenance, fork sensor label detection, and broken table text.
7. THE selected strategy SHALL be recorded with its metric values and rationale.

---

### Requirement 4 — Sensor Domain Evaluation Case

**User Story:** As a Robolinks engineer, I want the experiment to focus on the known sensor-selection failure case, so that improvements are measured against a real debugging problem.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-004 retrieval diagnostics prompt provenance, EXP-005 knowledge graph entity resolution

#### Acceptance Criteria

1. THE default evaluation case SHALL include expected candidates `BF4`, `BMS`, and `E3Z`.
2. THE default expected terms SHALL include bilingual equivalents for bottle/object detection.
3. THE report SHALL show whether each candidate appears in parsed text, baseline chunks, and adaptive chunks.
4. THE report SHALL highlight top evidence chunks for each candidate.
5. THE report SHALL identify if a candidate is missing because of parser loss, chunking loss, or retrieval/query mismatch.
6. THE report SHALL include a recommended next action for each missing candidate.

---

### Requirement 5 — Comparison Report

**User Story:** As a project maintainer, I want a concise report comparing baseline and adaptive chunking, so that I can decide whether to integrate adaptive chunking into ingestion.

## Steering & Skills

- **Steering:** `project-context.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`
- **Reference:** EXP-002, EXP-003, EXP-004, EXP-005

#### Acceptance Criteria

1. THE experiment SHALL produce a machine-readable JSON report.
2. THE experiment SHALL produce a human-readable Markdown report.
3. THE report SHALL include per-document metrics.
4. THE report SHALL include aggregate metrics across all tested documents.
5. THE report SHALL include sample chunks for the winning and baseline strategies.
6. THE report SHALL clearly state whether adaptive chunking is recommended, not recommended, or inconclusive.
7. THE report SHALL be saved as EXP-006 or linked from EXP-006.

---

### Requirement 6 — Optional Integration Decision Gate

**User Story:** As a maintainer, I want a decision gate before production integration, so that experimental chunking does not destabilize NAS ingest.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `lightrag-api.md`, `nas-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`
- **Reference:** pa3-design Section 5.1 (Ingestion workflow), lightrag-api.md (documents/text), EXP-002

#### Acceptance Criteria

1. THE experiment SHALL NOT modify production ingestion in V1.
2. THE design SHALL document what would be required to integrate adaptive chunks through LightRAG `/documents/text` in a future phase.
3. THE future integration path SHALL preserve `X-Correlation-ID`.
4. THE future integration path SHALL preserve NAS state machine semantics.
5. THE future integration path SHALL define rollback to current LightRAG-native parsing/chunking.
6. THE decision to integrate SHALL require evidence that candidate coverage improves and noise decreases on the sensor test set.

---

### Requirement 7 — Admin UI Evaluation Viewer

**User Story:** As a Robolinks engineer, I want to inspect adaptive chunking evaluation results visually in the Admin UI, so that I can compare baseline vs adaptive chunks without opening raw JSON files.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `frontend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`, `frontend-design`
- **Reference:** pa3-design Section 5.3 (Admin panel workflow), EXP-004 Diagnostics UI, EXP-005 graph/retrieval evaluation

#### Acceptance Criteria

1. THE backend SHALL expose an admin-only API to list available adaptive chunking evaluation reports.
2. THE backend SHALL expose an admin-only API to read one evaluation report by report id or filename.
3. THE backend SHALL read reports from the experiment artifact directory and SHALL NOT execute experiment scripts from the request path.
4. THE API SHALL return summary metrics, per-document metrics, strategy comparison, candidate coverage, noise indicators, verdict, and sample chunks.
5. THE frontend SHALL add an Admin page or tab for Adaptive Chunking Evaluation.
6. THE frontend SHALL follow Component → Hook → api/ → Backend and SHALL NOT call backend directly from the component.
7. THE UI SHALL show a visual summary with:
   - verdict/recommendation
   - aggregate candidate coverage
   - aggregate noise comparison
   - prompt/chunk size comparison
   - per-document winner
8. THE UI SHALL show per-document details:
   - baseline vs adaptive metrics table
   - candidate coverage for BF4/BMS/E3Z
   - top evidence chunks
   - noisy chunks or noise indicators
9. THE UI SHALL provide `Copy JSON` and `Copy Markdown` actions for debugging handoff.
10. WHEN no reports exist, THE UI SHALL show an empty state explaining how to run the offline experiment.
11. THE UI SHALL NOT trigger production ingestion, LightRAG reindexing, or graph mutation.

---

### Requirement 8 — Admin UI Self-Test Runner

**User Story:** As a Robolinks engineer, I want to configure and run an adaptive chunking test directly from the Admin UI, so that I can iterate on source files and evaluation terms without using terminal commands.

## Steering & Skills

- **Steering:** `project-context.md`, `backend-rules.md`, `frontend-rules.md`, `test-conventions.md`
- **Skills:** `task-breakdown`, `quality-assurance`, `fastapi-expert`, `frontend-design`
- **Reference:** Requirement 7 Admin UI Evaluation Viewer, EXP-006 adaptive chunking evaluation

#### Acceptance Criteria

1. THE backend SHALL expose an admin-only `POST /api/admin/evaluations/adaptive-chunking/run` endpoint.
2. THE endpoint SHALL accept source file paths, candidate terms, expected terms, noise terms, and chunking parameters.
3. THE endpoint SHALL run parse/chunk/metrics/report generation in-process and SHALL NOT execute arbitrary terminal commands.
4. THE endpoint SHALL write JSON/Markdown artifacts under `docs/experiments/artifacts/adaptive-chunking/`.
5. THE endpoint SHALL NOT mutate NAS queue, LightRAG documents, Graphiti, PostgreSQL production records, or graph/vector data.
6. THE frontend SHALL provide a form for run id, title, source files, candidate terms, expected terms, noise terms, and chunking parameters.
7. THE frontend SHALL render the newly generated report immediately after the run finishes.
8. THE frontend SHALL preserve Component → Hook → api/ → Backend flow.
9. WHEN a file cannot be parsed, THE report SHALL show the per-document error and continue evaluating other files.
10. THE local Docker backend SHALL mount `docs/` writable for report artifact generation.
