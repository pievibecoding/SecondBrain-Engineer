# Design Document — Adaptive Chunking Evaluation

## Overview

This spec creates an offline evaluation harness for adaptive chunking. It is intentionally
separate from production ingestion so the team can test chunk quality improvements without
risking NAS ingest, LightRAG document state, or graph/vector storage.

The main question:

```text
Does adaptive/document-aware chunking produce better retrievable evidence for Robolinks
technical documents than the current baseline chunks?
```

The first target case is sensor selection for bottle detection, where the expected candidates
are:

```text
Autonics BF4 Series
Omron E3Z Series / E3Z-B Series
Autonics BMS Series
```

---

## Non-Goals

- Do not replace the current LightRAG ingestion pipeline in V1.
- Do not write adaptive chunks into production LightRAG tables in V1.
- Do not modify `NasFile.status`, `NasFolder`, or NAS queue behavior.
- Do not solve graph entity canonicalization in this spec.
- Do not tune the LLM model in this spec.

---

## Architecture

### Offline Evaluation Flow

```text
Selected source files / exported parsed_text
  -> source_text_loader
  -> baseline chunker
  -> adaptive chunking strategies
  -> intrinsic/domain metrics
  -> strategy selector
  -> JSON report
  -> Markdown report / EXP-006
```

### Optional Future Integration Flow

```text
NAS file indexed by backend
  -> deterministic parser/layout extraction
  -> adaptive chunk selection
  -> selected chunks/text sent to LightRAG /documents/text
  -> LightRAG embed + graph extraction
```

This future flow is out of scope for V1, but the experiment report should provide enough
evidence to decide whether it is worth building.

---

## Directory Layout

```text
tools/experiments/adaptive-chunking/
├── README.md
├── config.sensor.json
├── run_evaluation.py
├── source_loader.py
├── chunkers.py
├── metrics.py
└── report_writer.py

docs/experiments/artifacts/adaptive-chunking/
├── sensor-eval-report.json
├── sensor-eval-report.md
└── chunks/
    ├── baseline-*.json
    └── adaptive-*.json
```

If the upstream `ekimetrics/adaptive-chunking` repo is cloned, place it under an ignored
external/deps area, for example:

```text
external/adaptive-chunking/
```

The experiment scripts should not require this folder to exist. They should fallback to local
strategies if the dependency is unavailable.

---

## Admin UI Viewer + Self-Test Runner

The experiment should have a visual review surface in Admin. The UI can read existing
artifacts and can also run a controlled self-test from selected `local-nas` source paths.
This still does not mutate production ingestion, LightRAG, Graphiti, or graph/vector data.

### Data Flow

```text
Admin UI
  -> useAdaptiveChunkingEvaluation hook
  -> frontend/src/api/admin.ts
  -> GET /api/admin/evaluations/adaptive-chunking
  -> GET /api/admin/evaluations/adaptive-chunking/{report_id}
  -> POST /api/admin/evaluations/adaptive-chunking/run
  -> backend reads docs/experiments/artifacts/adaptive-chunking/*.json
  -> backend writes a new JSON/Markdown artifact for controlled UI runs
  -> UI renders visual comparison
```

The backend must not execute arbitrary terminal commands from an HTTP request. UI runs use
an in-process backend service that reuses the same local parser/chunker/metrics logic.

### Proposed Backend API

```text
GET /api/admin/evaluations/adaptive-chunking
```

Response:

```json
{
  "reports": [
    {
      "id": "sensor-eval-report",
      "title": "Sensor Adaptive Chunking Evaluation",
      "created_at": "2026-06-20T00:00:00Z",
      "recommendation": "recommended",
      "document_count": 3,
      "path": "docs/experiments/artifacts/adaptive-chunking/sensor-eval-report.json"
    }
  ]
}
```

```text
GET /api/admin/evaluations/adaptive-chunking/{report_id}
```

Response:

```json
{
  "id": "sensor-eval-report",
  "summary": {
    "recommendation": "recommended",
    "candidate_coverage_delta": 0.25,
    "noise_delta": -0.4
  },
  "documents": [],
  "raw": {}
}
```

```text
POST /api/admin/evaluations/adaptive-chunking/run
```

Request:

```json
{
  "run_id": "sensor-ui-test",
  "title": "Sensor Adaptive Chunking UI Test",
  "documents": [
    {
      "document_id": "omron-e3z",
      "source_path": "/local-nas/projects/Demo/Sensor/Omron/Datasheet-cam-bien-tiem-can-Omron-E3Z-Series.pdf"
    }
  ],
  "candidate_terms": {
    "E3Z": ["E3Z", "E3Z-B", "Omron E3Z"]
  },
  "expected_terms": ["transparent bottle", "photoelectric sensor"],
  "noise_terms": ["mounting screw", "fork sensor"],
  "target_chars": 2200,
  "overlap_chars": 220,
  "max_chars": 4200
}
```

Response:

```json
{
  "id": "sensor-ui-test",
  "summary": {},
  "documents": [],
  "markdown": "...",
  "raw": {}
}
```

### Proposed Frontend Route

```text
/admin/evaluations/adaptive-chunking
```

Navigation label:

```text
Evaluations
```

or:

```text
Adaptive Chunking
```

### UI Sections

| Section | Purpose |
|---------|---------|
| Report selector | Choose report artifact |
| Run New Test | Configure files, terms, and chunking parameters |
| Verdict card | recommended / not recommended / inconclusive |
| Aggregate metrics | Candidate coverage, noise, chunk size deltas |
| Per-document table | Winner strategy and metric deltas per file |
| Candidate coverage | BF4/BMS/E3Z presence by strategy |
| Evidence chunks | Top chunks supporting each candidate |
| Noise inspection | Chunks/terms causing noise |
| Raw export | Copy JSON / Copy Markdown |

### Visual Guidelines

- Use compact comparison cards, not only raw JSON.
- Highlight winning strategy per document.
- Use color sparingly:
  - green for improved coverage/noise reduction
  - amber for inconclusive
  - red for regression
- Long chunks must be scrollable and copyable without truncation.
- The page must make it obvious that this is an offline evaluation viewer, not production ingest.

---

## Components

### `source_loader.py`

Responsibilities:

- Load plain text exported from Diagnostics.
- Optionally read raw source files if parser support is available.
- Normalize line endings.
- Compute source text stats:
  - `char_count`
  - `line_count`
  - empty-line ratio
  - broken-layout indicators

Output:

```json
{
  "document_id": "omron-e3z",
  "source_path": "...",
  "text": "...",
  "stats": {
    "char_count": 12345,
    "line_count": 300
  }
}
```

### `chunkers.py`

Responsibilities:

- Provide a baseline chunker approximating current fixed chunk behavior.
- Provide at least one structure-aware fallback strategy.
- Optionally wrap `ekimetrics/adaptive-chunking` strategies.

Initial local strategies:

| Strategy | Description |
|----------|-------------|
| `fixed_chars` | Simple fixed-size chunks with overlap |
| `paragraph_merge` | Merge paragraphs until target size |
| `heading_table_aware` | Try to keep headings and markdown tables together |

Output chunk shape:

```json
{
  "strategy": "paragraph_merge",
  "chunk_index": 0,
  "text": "...",
  "char_count": 1200,
  "metadata": {
    "source_path": "...",
    "section_hint": "BMS Series"
  }
}
```

### `metrics.py`

Responsibilities:

- Compute intrinsic metrics where feasible.
- Compute domain metrics for the sensor case.
- Compute noise indicators.

Minimum metrics:

| Metric | Meaning |
|--------|---------|
| `candidate_coverage` | BF4/BMS/E3Z presence in chunks |
| `expected_term_coverage` | Coverage of transparent/bottle/photoelectric terms |
| `noise_hit_count` | Mentions of maintenance/mounting/fork/zip tie noise terms |
| `max_chunk_chars` | Largest chunk size |
| `avg_chunk_chars` | Average chunk size |
| `chunk_count` | Number of chunks |
| `table_fragment_ratio` | Simple heuristic for broken markdown tables |

If upstream adaptive-chunking is available, also capture:

```text
RC, ICC, DCC, BI, SC
```

### `report_writer.py`

Responsibilities:

- Write JSON report for machine inspection.
- Write Markdown report for humans.
- Include top evidence chunks per candidate.
- Include recommendation:
  - `recommended`
  - `not_recommended`
  - `inconclusive`

---

## Sensor Evaluation Terms

### Candidate Terms

```text
BF4
BF4 Series
Autonics BF4
BMS
BMS Series
Autonics BMS
E3Z
E3Z-B
Omron E3Z
E3Z-B61
E3Z-B81
```

### Query Expansion Terms

```text
chai nước
water bottle
plastic bottle
transparent bottle
clear object
transparent object
photoelectric sensor
retroreflective sensor
sensing target
sensing distance
```

### Noise Terms

```text
mounting screw
zip tie
maintenance
cleaning
fork sensor
label detection
housing
dimension
cirtceleotohP
broken table
```

---

## Selection Logic

V1 selection can be rule-based:

1. Reject strategy if max chunk size exceeds configured limit.
2. Prefer strategy with higher candidate coverage.
3. Prefer strategy with higher expected term coverage.
4. Penalize high noise hit count.
5. Penalize broken table indicators.
6. If tied, prefer fewer/lower average chunks for prompt compactness.

Example scoring:

```text
score =
  candidate_coverage * 40
  + expected_term_coverage * 25
  - normalized_noise * 20
  - table_fragment_ratio * 10
  - oversize_penalty
```

This does not need to be perfect. The goal is to produce repeatable evidence for the next
implementation decision.

---

## Report Shape

### JSON

```json
{
  "run_id": "2026-06-20-sensor-adaptive-chunking",
  "documents": [
    {
      "document_id": "omron-e3z",
      "source_path": "...",
      "strategies": [
        {
          "name": "baseline",
          "metrics": {},
          "sample_chunks": []
        }
      ],
      "winner": "paragraph_merge",
      "recommendation": "recommended"
    }
  ],
  "aggregate": {
    "candidate_coverage_delta": 0.25,
    "noise_delta": -0.4
  }
}
```

### Markdown

The Markdown report should include:

- Summary verdict.
- Per-document comparison table.
- Candidate coverage table.
- Noise comparison table.
- Sample evidence chunks.
- Integration recommendation.
- Known limitations.

---

## Future Production Integration

If experiment results are positive, a later spec may add:

- Backend pre-processing before LightRAG ingestion.
- `LightRAGIngestClient.insert_text(...)` using `/documents/text`.
- Storage of adaptive strategy metadata.
- Admin UI to compare original parse vs selected chunks.
- Rollback switch to current LightRAG-native parsing/chunking.

Future integration must preserve:

- `X-Correlation-ID`
- NAS folder semantics (`auto` vs `manual`)
- `NasFile` status transitions
- Admin delete/reindex behavior

---

## Risks

| Risk | Mitigation |
|------|------------|
| Upstream dependency heavy or incompatible | Provide mini fallback strategies |
| Better chunks do not improve retrieval | Report as inconclusive; do not integrate |
| Parser output is already too broken | Separate parser-loss from chunking-loss |
| Domain terms are incomplete | Keep config editable |
| Metrics overfit one query | Add more Robolinks evaluation cases later |

---

## Open Questions

- Should adaptive chunking run per document or per section?
- Should selected chunks be written to LightRAG as one text document or multiple text documents?
- Can graph provenance survive `/documents/text` ingestion with pre-chunked content?
- Should query expansion and rerank be implemented before adaptive chunking integration?
