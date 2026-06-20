# Implementation Plan — PDF Parser Comparison & Quality Evaluation

## Overview

Build a controlled parser comparison workflow for PDF documents. V1 is evaluation-only and
must not alter production NAS ingest, LightRAG documents, graph, vector DB, or chat behavior.

---

## Tasks

- [x] 1. Create parser comparison artifact structure
  - Create:
    ```text
    docs/experiments/artifacts/pdf-parser-comparison/
    ```
  - Decide whether large generated artifacts should be ignored or committed selectively
  - _Requirements: 1.6_

---

- [x] 2. Add parser evaluation schemas
  - Create `backend/schemas/parser_evaluations.py`
  - Add request/response schemas:
    - parser run document
    - parser comparison run request
    - parser comparison report summary
    - parser comparison report detail
  - Keep schemas Pydantic-only
  - _Requirements: 1.2, 1.3, 2.1-2.9_

---

- [x] 3. Add common PDF parser adapter interface
  - Create parser adapter module under backend services
  - Define parser output shape:
    - raw text
    - normalized text
    - pages
    - blocks
    - tables
    - metadata
    - errors
  - Ensure services do not use `httpx`
  - _Requirements: 1.4, 3.1-3.7_

---

- [x] 4. Wrap current pdfplumber parser as baseline
  - Implement `pdfplumber` adapter
  - Preserve current behavior for comparison
  - Add parser metadata and latency
  - Record page text where possible
  - _Requirements: 1.3, 1.7_

---

- [x] 5. Implement PyMuPDF parser adapter
  - Add dependency if not already present
  - Implement `pymupdf` parser adapter
  - Extract block text with deterministic ordering
  - Preserve page number and block bbox metadata
  - Normalize line endings
  - Return parser unavailable if dependency is missing
  - _Requirements: 3.1-3.7_

---

- [x] 6. Add optional Docling and Marker adapters
  - Add adapters that are optional and dependency-gated
  - Add heavy dependencies after explicit approval
  - Return `parser_unavailable` when dependency is missing
  - Return parser-specific `parse_failed` when model/runtime conversion fails
  - Document install/runtime risks
  - _Requirements: 4.1-4.5_

---

- [x] 7. Implement parser quality metrics
  - Add metrics:
    - `char_count`
    - `line_count`
    - `empty_line_ratio`
    - `header_footer_artifact_count`
    - `broken_token_count`
    - `numeric_density`
    - `heading_count`
    - `table_candidate_count`
    - `reconstructed_table_count`
    - `semantic_anchor_hit_rate`
    - `latency_ms`
  - Flag non-empty but low-quality parsed text
  - _Requirements: 6.1-6.9_

---

- [x] 8. Implement table-aware normalization V1
  - Detect table-like regions
  - Preserve raw text
  - Emit Markdown table only when confidence is adequate
  - Mark low-confidence table regions
  - Attach nearby headings/captions when possible
  - _Requirements: 5.1-5.7_

---

- [x] 9. Implement parser comparison service
  - Orchestrate documents x parsers
  - Continue on parser/document errors
  - Compute metrics
  - Run selected chunk strategies on parser output if needed
  - Select recommended parser only as evaluation recommendation
  - Do not mutate production data
  - _Requirements: 1.1-1.7, 7.1_

---

- [x] 10. Add report writer
  - Write JSON report
  - Write Markdown report
  - Include:
    - summary
    - parser metrics
    - parsed text preview/full text
    - table blocks
    - parser + chunk matrix
    - errors/unavailable parsers
    - recommendation and caveats
  - _Requirements: 1.6, 2.4-2.8, 6.1-6.9_

---

- [x] 11. Add backend admin endpoints
  - Add:
    ```text
    GET /api/admin/evaluations/pdf-parser-comparison
    GET /api/admin/evaluations/pdf-parser-comparison/{report_id}
    POST /api/admin/evaluations/pdf-parser-comparison/run
    ```
  - Require admin auth
  - Return safe 404 for missing reports
  - Validate report id to avoid path traversal
  - _Requirements: 1.1, 2.1-2.9_

---

- [x] 12. Add frontend API and hook
  - Add API methods in `frontend/src/api/admin.ts`
  - Add hook such as `usePdfParserComparison`
  - Keep Component → Hook → api/ → Backend
  - Handle loading, running, errors, selected report
  - _Requirements: 2.1-2.9_

---

- [x] 13. Add Admin UI route
  - Add route:
    ```text
    /admin/evaluations/pdf-parser-comparison
    ```
  - Add Admin navigation item
  - Add Run Parser Test form:
    - source files
    - parser checkboxes
    - semantic anchors
    - expected terms
    - noise terms
  - _Requirements: 2.1-2.3_

---

- [x] 14. Add parser comparison result UI
  - Render tabs:
    - Summary
    - Parsed Text
    - Tables
    - Metrics
    - Parser + Chunk Matrix
    - Raw
  - Provide:
    - Copy Parsed Text
    - Copy Chunks
    - Copy JSON
    - Copy Markdown
  - Long logs must be scrollable and not truncated
  - _Requirements: 2.4-2.9_

---

- [x] 15. Run first Ball Screws parser comparison
  - Use source:
    ```text
    /local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf
    ```
  - Compare:
    ```text
    pdfplumber
    pymupdf
    ```
  - Use semantic anchors:
    - Ball Screw Selection Procedure
    - Selection of Ball Screw Shaft Length
    - Ball Screw Lead Accuracy
    - Allowable Rotational Speed
    - Axial Load Capacity
    - Basic Dynamic Load Rating
    - Service Life
    - Support Units
  - Save artifact
  - _Requirements: 1.1-1.7, 6.1-6.9_

---

- [x] 16. Write EXP result for parser comparison
  - Create follow-up experiment doc after running PyMuPDF comparison
  - Compare with EXP-007 baseline
  - State whether PyMuPDF improves parser quality
  - Decide whether to evaluate Docling/Marker next
  - _Requirements: 4.5, 7.1-7.3_

---

- [ ] 17. Add Diagnostics/RAG evidence gate test
  - Use improved parser output in evaluation mode
  - Compare retrieved context quality via Diagnostics
  - Do not mutate production ingest yet
  - Record whether context improves for real questions
  - _Requirements: 7.1-7.8_

---

- [ ] 18. Add backend unit tests
  - Test parser adapter availability handling
  - Test parser metrics
  - Test path/report id validation
  - Test report read/write
  - Test parser failure does not abort full run
  - _Requirements: 1.5, 1.6, 3.1-3.7, 6.1-6.9_

---

- [ ] 19. Add frontend tests
  - Test parser checkbox form
  - Test loading/error states
  - Test parsed text and metrics render
  - Test copy actions for long content
  - _Requirements: 2.1-2.9_

---

- [ ] 20. Document production integration decision
  - Add a decision note stating:
    - do not integrate yet
    - required evidence
    - rollback plan
    - NAS/LightRAG correlation ID constraints
  - Only mark production integration ready after Diagnostics/RAG evidence passes
  - _Requirements: 7.1-7.8_
