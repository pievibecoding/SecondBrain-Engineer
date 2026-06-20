# Design Document — PDF Parser Comparison & Quality Evaluation

## Overview

This spec adds a controlled parser comparison environment for PDF documents. It is inspired by
EXP-007, where the Ball Screws Selection Guide showed that `pdfplumber` produced non-empty but
layout-damaged text. The goal is to determine whether parser quality, chunking, retrieval, or LLM
generation is the root cause of poor answers.

V1 is evaluation-only:

```text
selected local-nas PDF
  -> parser adapters
  -> parser quality metrics
  -> optional table-aware normalization
  -> chunk strategy matrix
  -> JSON/Markdown report
  -> Admin UI visual review
```

No production NAS ingest, LightRAG document, vector DB, or graph data is mutated.

---

## Non-Goals

- Do not replace production ingestion parser in V1.
- Do not write parser-comparison output into LightRAG production documents in V1.
- Do not change NAS state machine behavior.
- Do not tune retrieval prompts or LLM models in this spec.
- Do not require heavy optional dependencies (`docling`, `marker`) for V1 startup.

---

## Architecture

### Evaluation Flow

```text
Admin UI
  -> useParserComparison hook
  -> frontend/src/api/admin.ts
  -> POST /api/admin/evaluations/pdf-parser-comparison/run
  -> backend parser comparison service
  -> parser adapters: pdfplumber, pymupdf, optional docling/marker
  -> parser metrics
  -> table-aware normalization
  -> chunk strategies
  -> report writer
  -> docs/experiments/artifacts/pdf-parser-comparison/*.json/*.md
  -> UI renders report
```

### Future Production Flow

Only after evidence gate passes:

```text
NAS file approved/indexed
  -> selected parser adapter
  -> normalized semantic text / markdown tables
  -> backend sends text to LightRAG /documents/text
  -> status/chunks/vector/graph pipeline
```

Future production integration must preserve:

- `X-Correlation-ID`
- folder semantics (`auto` vs `manual`)
- `NasFile` status transitions
- admin delete/reindex behavior
- rollback switch to current parser behavior

---

## Directory Layout

```text
backend/
├── schemas/
│   └── parser_evaluations.py
├── services/
│   ├── parser_comparison_service.py
│   └── pdf_parsers/
│       ├── base.py
│       ├── pdfplumber_parser.py
│       ├── pymupdf_parser.py
│       ├── docling_parser.py      # optional dependency adapter
│       └── marker_parser.py       # optional dependency adapter
└── routers/admin/
    └── evaluations.py

docs/experiments/artifacts/pdf-parser-comparison/
├── ball-screw-parser-comparison.json
└── ball-screw-parser-comparison.md
```

The exact module layout can be adjusted, but must preserve project rules:

- `schemas/` = Pydantic only
- `services/` = orchestration/business logic, no `httpx`
- `integrations/` = HTTP clients only

---

## Parser Interface

### `ParsedDocument`

```json
{
  "parser": "pymupdf",
  "status": "ok",
  "source_path": "/local-nas/...",
  "text": "...",
  "normalized_text": "...",
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "blocks": [
        {
          "type": "text",
          "text": "...",
          "bbox": [0, 0, 100, 100]
        }
      ]
    }
  ],
  "tables": [
    {
      "page_number": 3,
      "confidence": "low",
      "markdown": "| ... |",
      "caption": "..."
    }
  ],
  "metadata": {
    "latency_ms": 1200,
    "parser_version": "..."
  }
}
```

### Parser Adapter Contract

Each adapter should expose:

```python
class PdfParserAdapter(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def parse(self, path: Path) -> ParsedDocument: ...
```

Adapters must:

- normalize line endings
- return parser-specific errors without crashing the full run
- avoid HTTP calls
- include latency
- preserve raw text for provenance

---

## Parser Adapters

### `pdfplumber`

Role:

- baseline parser
- current known behavior
- useful for measuring whether alternatives improve quality

Risks:

- table flattening
- page artifact noise
- poor multi-column ordering on complex PDFs

### `PyMuPDF`

Role:

- first alternative parser
- lightweight and fast
- good candidate for block/coordinate extraction

Implementation notes:

- use `page.get_text("blocks")` or similar block mode
- sort blocks deterministically by page, y, x
- preserve page number and block bbox metadata
- output both raw text and block-aware text

### `Docling`

Role:

- optional heavier layout/document parser
- evaluate if PyMuPDF is insufficient for table-heavy catalogues

Rules:

- must be optional
- unavailable dependency should return `parser_unavailable`
- do not block backend startup

### `Marker`

Role:

- optional PDF-to-Markdown parser
- evaluate when OCR/layout recovery is needed

Rules:

- must be optional
- track runtime and Docker cost
- only move forward after PyMuPDF baseline is measured

---

## Table-Aware Extraction

V1 should add pragmatic table-aware normalization. It does not need perfect table extraction,
but it must avoid pretending flattened number streams are high-quality tables.

### Steps

1. Detect table candidates:
   - repeated numeric rows
   - dense columns
   - aligned text blocks when coordinates exist
   - nearby table captions
2. Reconstruct Markdown tables only when confidence is adequate.
3. Attach nearby heading/caption to table block.
4. Mark low-confidence regions:

```markdown
[Low-confidence table region, page 4]
raw text...
```

### Desired Output

```markdown
## Ball Screw Lead Accuracy

| Accuracy grade | Effective thread length | Allowable travel error |
|---|---:|---:|
| C3 | ... | ... |
```

---

## Parser Quality Metrics

Minimum V1 metrics:

| Metric | Meaning |
|---|---|
| `char_count` | Output size |
| `line_count` | Line structure |
| `empty_line_ratio` | Layout spacing noise |
| `header_footer_artifact_count` | Repeated page/header artifacts |
| `broken_token_count` | Artifacts such as `CC__006688...` |
| `numeric_density` | Ratio of numeric-heavy text indicating flattened tables |
| `heading_count` | Detected section headings |
| `table_candidate_count` | Possible tables detected |
| `reconstructed_table_count` | Tables reconstructed into Markdown |
| `semantic_anchor_hit_rate` | Expected headings preserved |
| `latency_ms` | Parser runtime |

### Semantic Anchors for Ball Screws

```text
Ball Screw Selection Procedure
Selection of Ball Screw Shaft Length
Ball Screw Lead Accuracy
Allowable Rotational Speed
Axial Load Capacity
Basic Dynamic Load Rating
Service Life
Support Units
```

---

## Backend API

### List Reports

```text
GET /api/admin/evaluations/pdf-parser-comparison
```

### Get Report

```text
GET /api/admin/evaluations/pdf-parser-comparison/{report_id}
```

### Run Evaluation

```text
POST /api/admin/evaluations/pdf-parser-comparison/run
```

Request:

```json
{
  "run_id": "ball-screw-parser-comparison",
  "title": "Ball Screw Parser Comparison",
  "documents": [
    {
      "document_id": "ball-screw",
      "source_path": "/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf"
    }
  ],
  "parsers": ["pdfplumber", "pymupdf"],
  "semantic_anchors": [
    "Ball Screw Selection Procedure",
    "Ball Screw Lead Accuracy"
  ],
  "candidate_terms": {
    "Lead": ["lead", "screw lead", "ball screw lead"]
  },
  "expected_terms": ["axial load", "critical speed"],
  "noise_terms": ["copyright", "contact", "CC__"]
}
```

Response:

```json
{
  "id": "ball-screw-parser-comparison",
  "summary": {
    "recommended_parser": "pymupdf",
    "recommendation": "needs_more_evidence"
  },
  "documents": [],
  "markdown": "...",
  "raw": {}
}
```

---

## Frontend UI

Route options:

```text
/admin/evaluations/pdf-parser-comparison
```

or extend current:

```text
/admin/evaluations/adaptive-chunking
```

Preferred V1: separate route to keep parser evaluation conceptually clear.

### UI Sections

| Section | Purpose |
|---|---|
| Run Parser Test | Source files, parser checkboxes, terms, anchors |
| Parser Summary | Recommended parser, quality score, latency |
| Parsed Text | Full parsed/normalized text per parser |
| Tables | Reconstructed/low-confidence table blocks |
| Metrics | Parser quality metrics |
| Parser + Chunk Matrix | Combined parser/chunk evidence |
| Raw Export | Copy JSON/Markdown |

---

## Production Integration Gate

Parser can be considered for production only when all pass:

1. Parser comparison shows better parser quality metrics than `pdfplumber`.
2. Diagnostics shows retrieved context quality improves on real questions.
3. At least one table-heavy PDF and one manual-style PDF improve.
4. DOCX/TXT behavior does not regress.
5. Ingestion preserves correlation ID and NAS status semantics.
6. Rollback switch is defined and tested.

Example gate case:

```text
Question:
How do I select ball screw lead accuracy and shaft diameter?

Expected evidence:
- Ball Screw Selection Procedure
- lead accuracy grade
- shaft diameter
- axial load capacity
- allowable rotational speed
```

---

## Risks

| Risk | Mitigation |
|---|---|
| PyMuPDF still flattens tables | Move to Docling/Marker evaluation |
| Heavy parser dependencies bloat Docker | Keep optional adapters, do not require in V1 |
| Metrics overfit Ball Screw PDF | Add multiple PDF cases before production gate |
| Parser output improves locally but retrieval does not | Require Diagnostics/RAG gate |
| Table reconstruction creates false structure | Mark low-confidence tables and preserve raw text |

---

## Open Questions

- Should parser comparison be a separate Admin route or integrated into Adaptive Chunking UI?
- Should table-aware extraction use parser-native table APIs or a custom post-processor first?
- Should production ingestion store parser metadata per `NasFile`?
- Should parser output be sent to LightRAG as full normalized text or section-level documents?
