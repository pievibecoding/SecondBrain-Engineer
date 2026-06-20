# Requirements Document

## Introduction

Robust Document Ingestion Pipeline là hệ thống parse và ingest tài liệu từ Synology NAS của Robolinks
vào knowledge graph SecondBrain (LightRAG). Spec này giải quyết các vấn đề thực tế đã được phát hiện
qua EXP-001 và EXP-002: mất text khi parse DOCX chứa nhiều ảnh inline, LLM không ổn định khi xử lý
lâu dài, và thiếu khả năng resume khi lỗi giữa chừng.

Pipeline chạy hoàn toàn trong `backend/` — không thay đổi LightRAG Docker image. Khi text đã được
parse sạch, pipeline gọi LightRAG qua `POST /documents/text` thay vì `POST /api/v1/docs` (để bypass
native parser của LightRAG). Với metadata-only files (DWG, video, CAD), pipeline chỉ lưu metadata
vào PostgreSQL mà không gửi sang LightRAG.

---

## Glossary

- **Pipeline**: Hệ thống backend xử lý tài liệu từ parse → validate → chunk → ingest vào LightRAG.
- **Parser**: Module Python extract text và bảng từ một loại file cụ thể (ví dụ: `pymupdf`, `python-docx`).
- **Fallback_Chain**: Danh sách parser được thử tuần tự khi parser trước fail hoặc cho kết quả không đủ.
- **ParseResult**: Cấu trúc dữ liệu chứa text đã extract, danh sách bảng, metadata, và các chỉ số chất lượng.
- **Completeness_Score**: Tỷ lệ ước tính giữa số ký tự đã extract và số ký tự kỳ vọng dựa trên file size.
- **Ingestion_Job**: Một đơn vị công việc ingest tương ứng với một file NAS, có trạng thái lưu trong PostgreSQL.
- **Chunk_Checkpoint**: Bản ghi lưu tiến độ xử lý chunk theo từng chunk index, cho phép resume sau lỗi.
- **Metadata_Only_Mode**: Chế độ chỉ lưu metadata file (tên, kích thước, ngày sửa đổi, NAS path) mà không parse content.
- **NasFile**: SQLAlchemy model trong `backend/models/nas_file.py` lưu trạng thái file NAS.
- **Parser_Config**: Cấu hình do admin thiết lập, định nghĩa Fallback_Chain và tham số cho từng loại file extension.
- **LightRAG**: Graph + Vector engine chạy trên port 9621, nhận text đã parse qua `POST /documents/text`.
- **Ingestion_Service**: Business logic layer trong `backend/services/ingestion_service.py`.
- **Correlation_ID**: UUID duy nhất cho mỗi request, forward qua `X-Correlation-ID` header để trace log.

---

## Requirements

### Requirement 1 — Robust Text Extraction không mất content

**User Story:** As a Robolinks engineer, I want the pipeline to extract all text from DOCX files
including text blocks between inline images, so that documents like "Hướng dẫn vận hành_SATO.docx"
are fully indexed without missing content.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md, nas-rules.md
- **Skills:** task-breakdown, fastapi-expert, quality-assurance
- **Reference:** pa3-design Section 5.1 (Ingestion workflow), EXP-001 findings (native parser drop text)

#### Acceptance Criteria

1. WHEN a DOCX file is ingested, THE Parser SHALL traverse the document XML DOM sequentially and extract all paragraph runs including those interleaved between drawing or image elements.
2. WHEN a PDF file is ingested, THE Parser SHALL extract text using character-level extraction (not block-level) to preserve text fragments between figures.
3. THE Parser SHALL preserve reading order of text across all content types (paragraphs, table cells, list items, captions) within a single document.
4. WHEN a DOCX or PDF file with inline images is parsed, THE ParseResult SHALL contain at least 95% of the estimated text character count compared to a completeness baseline derived from file size.
5. THE Fallback_Chain for DOCX SHALL attempt parsers in this order: `python-docx` (DOM traversal) → `mammoth` → LightRAG legacy.
6. THE Fallback_Chain for PDF SHALL attempt parsers in this order: `pymupdf` (character-level) → `pdfplumber` → LightRAG native.
7. WHEN a parser in the Fallback_Chain raises an exception, THE Pipeline SHALL log the exception with the parser name and Correlation_ID, then proceed to the next parser in the chain.
8. WHEN all parsers in the Fallback_Chain fail, THE Pipeline SHALL set the Ingestion_Job status to `failed` and record the error from each parser attempt in `error_msg`.

---

### Requirement 2 — Table Extraction không bị sai hàng

**User Story:** As a Robolinks engineer, I want tables extracted with correct row-column alignment,
so that BOM tables and alarm tables in technical documents are readable and searchable in the knowledge graph.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md
- **Skills:** task-breakdown, quality-assurance
- **Reference:** pa3-design Section 5.1, EXP-002 (LightRAG analyze_multimodal table summary hiệu quả)

#### Acceptance Criteria

1. WHEN a DOCX file contains tables, THE Parser SHALL extract each table as a structured grid preserving row and column boundaries, then render it as Markdown table format in the ParseResult.
2. WHEN a PDF file contains tables, THE Parser SHALL use `pdfplumber` table detection to extract cell boundaries before extracting cell text.
3. WHEN a table row contains merged cells, THE Parser SHALL expand merged cells and repeat the cell value across all spanned positions to maintain column alignment.
4. THE ParseResult SHALL include a `tables` list where each entry contains: the table index, page number (if applicable), and the Markdown-formatted table string.
5. WHEN an XLSX or XLS file is ingested, THE Parser SHALL extract each worksheet as a separate table, preserving header rows and numeric cell values without format conversion.
6. WHEN a PPTX file contains tables in slides, THE Parser SHALL extract those tables using the same Markdown format as DOCX tables.

---

### Requirement 3 — Metadata-Only Mode cho binary files

**User Story:** As a Robolinks admin, I want DWG, video, and CAD files to be registered in the
knowledge base with their metadata only, so that engineers can find files by name and context
without requiring full content parsing.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, nas-rules.md
- **Skills:** task-breakdown, fastapi-expert
- **Reference:** pa3-design Section 5.1, nas-rules.md (METADATA_ONLY_EXTENSIONS)

#### Acceptance Criteria

1. WHEN a file with extension `.dwg`, `.dxf`, `.png`, `.jpg`, `.mp4`, `.avi`, `.step`, or `.stl` is detected, THE Pipeline SHALL run in Metadata_Only_Mode without invoking any content parser.
2. WHILE in Metadata_Only_Mode, THE Pipeline SHALL record the following metadata into PostgreSQL: `nas_path`, `file_name`, `file_extension`, `file_size_bytes`, `last_modified_at`, `nas_folder_context` (derived from folder path segments).
3. WHILE in Metadata_Only_Mode, THE Pipeline SHALL NOT send any request to LightRAG `POST /documents/text` or `POST /api/v1/docs`.
4. THE Pipeline SHALL set the NasFile status to `indexed` after successfully recording metadata in Metadata_Only_Mode.
5. WHERE the admin Parser_Config overrides a file extension from Metadata_Only_Mode to content-parse mode, THE Pipeline SHALL respect the override and attempt content parsing for that extension.

---

### Requirement 4 — Image Handling Strategy

**User Story:** As a Robolinks admin, I want to configure how images are handled during ingestion,
so that I can enable OCR or Vision LLM captions when needed without running expensive operations by default.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md
- **Skills:** task-breakdown, fastapi-expert
- **Reference:** pa3-design Section 5.1, project-context.md Section 7 (OUT OF SCOPE: OCR mặc định)

#### Acceptance Criteria

1. THE Pipeline SHALL default to `image_mode=skip` for standalone image files (`.png`, `.jpg`) unless the admin Parser_Config explicitly sets a different mode.
2. WHERE `image_mode=ocr` is configured for an extension, THE Pipeline SHALL invoke the configured OCR engine and include the OCR text in the ParseResult.
3. WHERE `image_mode=vision_caption` is configured for an extension, THE Pipeline SHALL call the configured Vision LLM and include the generated caption in the ParseResult.
4. WHEN `image_mode=ocr` is configured but the OCR engine is unavailable, THE Pipeline SHALL fall back to `image_mode=skip`, log a warning with Correlation_ID, and continue ingestion.
5. WHEN processing DOCX or PDF files, THE Parser SHALL extract alt-text and captions of inline images (if present) into the ParseResult regardless of `image_mode`.
6. THE Parser_Config SHALL support per-extension `image_mode` values: `skip`, `ocr`, `vision_caption`.

---

### Requirement 5 — Fallback Chain Config-Driven

**User Story:** As a Robolinks admin, I want to configure the parser stack per file type through
admin settings, so that I can switch to a better parser without redeploying code.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** task-breakdown, fastapi-expert
- **Reference:** pa3-design Section 5.1, Section 6 (Stack & config)

#### Acceptance Criteria

1. THE Ingestion_Service SHALL read Parser_Config from a configuration source (environment variable or database-backed admin setting) at ingestion startup, not hardcoded in source files.
2. WHEN Parser_Config defines a Fallback_Chain for a given extension, THE Pipeline SHALL use that chain in order without skipping any entry.
3. THE Parser_Config SHALL support the following per-extension settings: `fallback_chain` (ordered list of parser names), `image_mode`, `metadata_only` (boolean override), `timeout_seconds`.
4. WHEN Parser_Config does not define a chain for a specific extension, THE Pipeline SHALL use the default chain defined for that file category (text documents, spreadsheets, presentations).
5. WHEN an admin updates Parser_Config, THE change SHALL take effect on the next ingestion job without requiring a service restart.

---

### Requirement 6 — Resume-on-Failure (Chunk Checkpointing)

**User Story:** As a Robolinks engineer, I want the pipeline to resume from the last successful
chunk when an LLM timeout occurs, so that a 20-page document does not need to be re-parsed and
re-processed from scratch after a network blip.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md
- **Skills:** task-breakdown, fastapi-expert, quality-assurance
- **Reference:** pa3-design Section 5.1, EXP-001 (Bluesminds retry 10 lần, Gemini rate limit)

#### Acceptance Criteria

1. THE Ingestion_Service SHALL persist a Chunk_Checkpoint record to PostgreSQL after each chunk is successfully sent to LightRAG, containing: `nas_file_id`, `chunk_index`, `chunk_hash`, `sent_at`.
2. WHEN an Ingestion_Job resumes after a `failed` state, THE Ingestion_Service SHALL read existing Chunk_Checkpoints for that `nas_file_id` and skip all chunks with matching `chunk_hash` that have already been sent.
3. WHEN an LLM timeout or rate-limit error is returned by LightRAG during chunk processing, THE Pipeline SHALL set the NasFile status to `failed` with `error_msg` containing the failed `chunk_index` and retry count.
4. WHEN retrying a failed chunk, THE Pipeline SHALL wait an exponential backoff delay starting at 5 seconds, doubling on each retry, with a maximum of 120 seconds between retries.
5. THE Pipeline SHALL attempt a maximum of 5 retries per chunk before marking the chunk as permanently failed and setting NasFile status to `failed`.
6. WHEN all chunks are processed successfully, THE Ingestion_Service SHALL delete all Chunk_Checkpoint records for that `nas_file_id` to avoid stale data.

---

### Requirement 7 — Parse Result Validation (Completeness Check)

**User Story:** As a Robolinks engineer, I want the pipeline to detect when a parser has silently
dropped a significant portion of the document content, so that incomplete indexes are caught before
they enter the knowledge graph.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md
- **Skills:** task-breakdown, quality-assurance
- **Reference:** EXP-001 (SATO.docx thiếu ~50% content), pa3-design Section 5.1

#### Acceptance Criteria

1. THE Pipeline SHALL compute a Completeness_Score for each ParseResult as: `extracted_char_count / estimated_char_count`, where `estimated_char_count` is derived from `file_size_bytes * extension_char_density_factor`.
2. WHEN the Completeness_Score of a ParseResult is below the configured threshold (default 0.60 for text documents), THE Pipeline SHALL log a warning with: `nas_path`, `parser_name`, `completeness_score`, `Correlation_ID`.
3. WHEN the Completeness_Score is below the threshold AND a next parser exists in the Fallback_Chain, THE Pipeline SHALL discard the current ParseResult and invoke the next parser.
4. WHEN the Completeness_Score is below the threshold AND no further parser is available, THE Pipeline SHALL proceed with the best available ParseResult and set a `parse_quality=degraded` flag in the NasFile metadata.
5. THE char_density_factor SHALL be configurable per extension in Parser_Config with sensible defaults: `pdf=0.15`, `docx=0.20`, `xlsx=0.05`, `pptx=0.12`.
6. THE Pipeline SHALL include `completeness_score` and `parser_used` fields in the structured log entry for every completed parse operation.

---

### Requirement 8 — Performance: 20-Page Document ≤ 5 Minutes

**User Story:** As a Robolinks engineer, I want a typical 20-page technical document to be fully
ingested within 5 minutes, so that newly uploaded files are searchable in a reasonable time.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md
- **Skills:** task-breakdown, quality-assurance
- **Reference:** pa3-design Section 5.1, EXP-001 (Bluesminds chậm + retry), EXP-002 (Docling chậm 3-5x)

#### Acceptance Criteria

1. WHEN a text document with 20 pages or fewer is ingested end-to-end (parse → validate → send to LightRAG), THE Pipeline SHALL complete within 300 seconds under normal operating conditions (LLM available, no retries needed).
2. THE Parser SHALL complete the parse phase (text + table extraction only, excluding LLM calls) for a 20-page DOCX or PDF within 30 seconds on the production server.
3. THE Pipeline SHALL support concurrent processing of up to 3 Ingestion_Jobs simultaneously without exceeding the 300-second target for any single job.
4. WHEN the LightRAG `MAX_ASYNC_LLM` setting is set to 1 (sequential mode for rate-limited providers), THE Pipeline SHALL still complete a 20-page document within 300 seconds by optimizing chunk size to reduce the number of LLM calls.
5. THE Ingestion_Service SHALL log the elapsed time for each pipeline phase (parse, validate, send_chunks) in the structured log with Correlation_ID.

---

### Requirement 9 — Observability: Per-Step Structured Logging

**User Story:** As a Robolinks engineer, I want detailed structured logs for every step of the
ingestion pipeline sent to Seq, so that I can diagnose parse failures and LLM errors by filtering
on correlation_id without reading raw file system logs.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, lightrag-api.md, nas-rules.md
- **Skills:** task-breakdown, quality-assurance
- **Reference:** project-context.md Section 6 (Correlation ID), pa3-design Section 5.1, Section 15 (Test strategy)

#### Acceptance Criteria

1. THE Pipeline SHALL emit a structured log event at the start of each ingestion job containing: `event=ingestion_started`, `nas_path`, `file_extension`, `file_size_bytes`, `correlation_id`.
2. THE Pipeline SHALL emit a structured log event at the end of each parse attempt containing: `event=parse_completed`, `parser_name`, `completeness_score`, `char_count`, `table_count`, `duration_ms`, `correlation_id`.
3. WHEN a parser fails or is skipped, THE Pipeline SHALL emit: `event=parser_fallback`, `failed_parser`, `reason`, `next_parser`, `correlation_id`.
4. THE Pipeline SHALL emit a structured log event for each chunk sent to LightRAG containing: `event=chunk_sent`, `chunk_index`, `chunk_size_chars`, `duration_ms`, `correlation_id`.
5. WHEN a chunk send fails, THE Pipeline SHALL emit: `event=chunk_failed`, `chunk_index`, `retry_count`, `error_type`, `correlation_id`.
6. THE Pipeline SHALL emit a structured log event upon job completion containing: `event=ingestion_completed`, `status` (`indexed` or `failed`), `total_chunks`, `total_duration_ms`, `parser_used`, `parse_quality`, `correlation_id`.
7. ALL structured log events SHALL use the `backend.logger` module and SHALL include `correlation_id` as a top-level field to enable filtering in Seq.

---

### Requirement 10 — NasFile State Machine Integration

**User Story:** As a Robolinks admin, I want the ingestion pipeline to correctly update NasFile
status at each stage, so that the admin UI accurately reflects whether a file is being processed,
has succeeded, or has failed.

## Steering & Skills

- **Steering:** project-context.md, backend-rules.md, nas-rules.md
- **Skills:** task-breakdown, fastapi-expert
- **Reference:** project-context.md Section 5 (NAS File State Machine), nas-rules.md (state transitions)

#### Acceptance Criteria

1. WHEN an Ingestion_Job begins processing a NasFile, THE Ingestion_Service SHALL transition NasFile status from `queued` to `indexing` and persist the change to PostgreSQL before invoking any parser.
2. WHEN all chunks of a NasFile are successfully sent to LightRAG, THE Ingestion_Service SHALL transition NasFile status to `indexed`, set `indexed_at` to the current UTC timestamp, and record `lightrag_doc_id`.
3. WHEN any unrecoverable error occurs during ingestion (all retries exhausted, all parsers failed), THE Ingestion_Service SHALL transition NasFile status to `failed` and write a human-readable `error_msg` in Vietnamese or English describing the root cause.
4. THE Ingestion_Service SHALL NOT transition NasFile status directly from `queued` to `failed` without first transitioning through `indexing`, to preserve an accurate audit trail.
5. WHEN a NasFile is in `failed` state and an admin manually re-queues it, THE Ingestion_Service SHALL treat it as a fresh Ingestion_Job and resume using existing Chunk_Checkpoints where available.
6. THE Ingestion_Service SHALL record `file_hash` on the NasFile record after a successful parse, so that the nas-connector can detect future content changes for re-ingestion.
