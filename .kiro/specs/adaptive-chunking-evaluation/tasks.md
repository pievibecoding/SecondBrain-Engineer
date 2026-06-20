# Implementation Plan — Adaptive Chunking Evaluation

## Overview

Build an offline experiment harness to evaluate adaptive chunking for SecondBrain technical
documents, starting with the sensor-selection failure case. This is an experiment spec, not a
production ingestion change.

---

## Tasks

- [x] 1. Create experiment folder structure
  - Create:
    ```text
    tools/experiments/adaptive-chunking/
    docs/experiments/artifacts/adaptive-chunking/
    ```
  - Add README explaining the offline-only goal
  - Add `.gitignore` entries if large artifacts/dependency clones should not be committed
  - _Requirements: 1.1, 1.4_

---

- [x] 2. Add sensor evaluation config
  - Create `tools/experiments/adaptive-chunking/config.sensor.json`
  - Include document list placeholders for:
    - Omron E3Z
    - Autonics BMS
    - Autonics BF4
  - Include candidate terms:
    - `BF4`, `BMS`, `E3Z`, `E3Z-B`
  - Include query expansion terms:
    - `water bottle`, `plastic bottle`, `transparent bottle`, `clear object`, `photoelectric sensor`
  - Include noise terms:
    - `mounting`, `maintenance`, `fork sensor`, `zip tie`, `dimension`
  - _Requirements: 4.1, 4.2_

---

- [x] 3. Implement source text loader
  - Create `source_loader.py`
  - Support plain `.txt` files exported from Diagnostics
  - Normalize line endings
  - Compute:
    - `char_count`
    - `line_count`
    - empty-line ratio
    - broken layout indicators
  - Record load errors without aborting full run
  - _Requirements: 1.2, 1.6, 2.1-2.5_

---

- [x] 4. Implement baseline and fallback chunkers
  - Create `chunkers.py`
  - Implement `fixed_chars` baseline
  - Implement `paragraph_merge`
  - Implement `heading_table_aware`
  - Use stable output schema:
    ```json
    {"strategy": "...", "chunk_index": 0, "text": "...", "metadata": {}}
    ```
  - _Requirements: 3.1, 3.2, 3.4_

---

- [x] 5. Add optional upstream adaptive-chunking adapter
  - Detect whether `ekimetrics/adaptive-chunking` dependency is available
  - If available, run its strategies/metrics
  - If unavailable, log fallback mode and continue
  - Do not require upstream dependency for basic experiment run
  - _Requirements: 3.3, 3.4_

---

- [x] 6. Implement metrics
  - Create `metrics.py`
  - Implement candidate coverage metric
  - Implement expected term coverage metric
  - Implement noise hit count
  - Implement chunk size metrics
  - Implement table fragmentation heuristic
  - Capture upstream intrinsic metrics if available:
    - RC
    - ICC
    - DCC
    - BI
    - SC
  - _Requirements: 3.5, 3.6, 4.3-4.5_

---

- [x] 7. Implement strategy selection
  - Create rule-based scoring
  - Prefer strategies with higher candidate/expected term coverage
  - Penalize noise and broken table indicators
  - Penalize oversized chunks
  - Record selected strategy and rationale
  - _Requirements: 3.7, 5.3, 5.4_

---

- [x] 8. Implement report writer
  - Create `report_writer.py`
  - Write JSON report
  - Write Markdown report
  - Include:
    - summary verdict
    - per-document metrics
    - aggregate metrics
    - top evidence chunks
    - baseline vs adaptive sample chunks
    - recommendation
  - _Requirements: 5.1-5.7_

---

- [x] 9. Implement CLI runner
  - Create `run_evaluation.py`
  - Accept config path argument
  - Load documents
  - Run chunkers
  - Compute metrics
  - Select winner
  - Write reports
  - Exit non-zero only for invalid config or no evaluable documents
  - _Requirements: 1.1-1.6, 5.1-5.7_

---

- [x] 10. Run first sensor experiment
  - Export or locate parsed text for:
    - Omron E3Z
    - Autonics BMS
    - Autonics BF4
  - Run CLI with `config.sensor.json`
  - Save artifacts under `docs/experiments/artifacts/adaptive-chunking/`
  - _Requirements: 4.1-4.6_

---

- [x] 11. Write EXP-006 results document
  - Create `docs/experiments/EXP-006-adaptive-chunking-sensor-evaluation.md`
  - Link JSON/Markdown artifacts
  - Summarize whether adaptive chunking is:
    - recommended
    - not recommended
    - inconclusive
  - Include next-step decision
  - _Requirements: 5.6, 5.7, 6.6_

---

- [x] 12. Document future integration gate
  - In EXP-006 or a follow-up design note, document:
    - how `/documents/text` integration would work
    - rollback to current LightRAG-native ingest
    - correlation ID requirements
    - NAS state machine preservation
  - Do not implement production integration in this spec
  - _Requirements: 6.1-6.6_

---

- [x] 13. Add backend API for evaluation report viewer
  - Add admin-only router for adaptive chunking evaluation reports
  - Implement:
    ```text
    GET /api/admin/evaluations/adaptive-chunking
    GET /api/admin/evaluations/adaptive-chunking/{report_id}
    ```
  - Read JSON/Markdown artifacts from `docs/experiments/artifacts/adaptive-chunking/`
  - Do not execute experiment scripts from the API
  - Return safe 404 when report is missing
  - _Requirements: 7.1-7.4, 7.10-7.11_

---

- [x] 14. Add frontend API and hook for evaluation reports
  - Add API client methods in `frontend/src/api/admin.ts`
  - Add hook such as `useAdaptiveChunkingEvaluations`
  - Keep Component → Hook → api/ → Backend flow
  - Handle loading, error, empty report list, and selected report state
  - _Requirements: 7.5-7.6, 7.10_

---

- [x] 15. Add Admin UI page for adaptive chunking evaluation
  - Add route under Admin
  - Add navigation item
  - Render:
    - report selector
    - verdict card
    - aggregate metrics
    - per-document comparison table
    - candidate coverage for BF4/BMS/E3Z
    - evidence chunks
    - noise indicators
    - raw JSON/Markdown copy actions
  - Long chunks must be scrollable and not truncated
  - _Requirements: 7.5, 7.7-7.11_

---

- [x] 16. Add tests for local experiment utilities
  - Add tests for:
    - source loader
    - candidate coverage metric
    - noise metric
    - scoring/selection
  - Tests should not require LightRAG or Docker
  - _Requirements: 1.3, 3.5-3.7, 5.1_

---

- [ ] 17. Add tests for evaluation viewer
  - Backend tests:
    - list reports
    - get report
    - missing report 404
    - no script execution from request path
  - Frontend tests:
    - empty state
    - report selector
    - verdict/metrics render
    - copy JSON/Markdown actions
  - _Requirements: 7.1-7.11_

---

- [x] 18. Add backend self-test runner API
  - Add admin-only:
    ```text
    POST /api/admin/evaluations/adaptive-chunking/run
    ```
  - Accept source files, candidate terms, expected terms, noise terms, and chunking params
  - Run parser/chunker/metrics/report generation in-process
  - Write JSON/Markdown artifacts under `docs/experiments/artifacts/adaptive-chunking/`
  - Do not execute terminal commands or mutate production ingestion/LightRAG/graph data
  - _Requirements: 8.1-8.5, 8.9_

---

- [x] 19. Redesign Admin UI as self-test console
  - Add Run New Test form
  - Support editable source files, candidate terms, expected terms, noise terms, and chunk params
  - Run through hook/API chain only
  - Render newly generated report immediately
  - Add coverage tab with candidate hit/miss chips
  - _Requirements: 8.6-8.8_

---

- [x] 20. Enable local Docker report writes
  - Mount `./docs:/app/docs` writable for backend in `docker-compose.local.yml`
  - Keep `local-nas` read-only
  - _Requirements: 8.10_

---

- [ ] 21. Add tests for self-test runner
  - Backend tests:
    - successful run writes report
    - invalid source records per-document error
    - no command execution path
  - Frontend tests:
    - form validation
    - run button loading state
    - new report renders after run
  - _Requirements: 8.1-8.10_
