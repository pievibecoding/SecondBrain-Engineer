# EXP-007 — PDF Parser Quality on Ball Screws Selection Guide

## Summary

Experiment này ghi lại kết quả kiểm tra tài liệu:

```text
D:\Robolinks Intern\Project\SecondBrain\local-nas\DATN_TLTK\7. Ball Screws Selection Guide.pdf
```

Mục tiêu ban đầu là đánh giá chunking, nhưng kết quả cho thấy vấn đề chính nằm ở parser PDF.
Parser hiện tại (`pdfplumber`) tạo ra text đầu vào bị rối layout, làm chunking và RAG phía sau
khó có thể hoạt động tốt.

Kết luận ngắn:

```text
Parser PDF hiện tại chưa đủ tốt cho catalogue / selection guide kỹ thuật nhiều bảng.
Vấn đề chính của case này là parser quality, không phải chunking strategy.
```

---

## Context

UI test được chạy qua:

```text
Admin > Adaptive Chunking > Run evaluation
```

Report artifact:

```text
docs/experiments/artifacts/adaptive-chunking/ball-screw-ui-test.json
```

Source:

```text
/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf
```

Parser:

```text
pdfplumber
```

Parser stats:

```json
{
  "char_count": 53527,
  "line_count": 779,
  "empty_line_ratio": 0.007702,
  "broken_layout_hits": 0
}
```

Important caveat:

The test report still used sensor-domain candidate terms (`E3Z`, `BMS`, `BF4`) instead of
Ball Screw terms. Therefore, the reported chunk winner (`fixed_chars`) is not reliable as a
chunking conclusion. However, the parsed/chunk text itself is sufficient to diagnose parser
quality problems.

---

## Observed Parser Problems

### 1. Header / page artifact noise

Parsed text contains repeated catalogue/page encoding artifacts, for example:

```text
CC__00668811--00668822__FF1100--0044__ccEENNGG cENG 2nd
```

This is not useful domain content. If indexed, it can pollute embeddings, graph extraction,
and retrieval context.

### 2. Layout-flattened tables

Many table regions are flattened into dense number streams, for example:

```text
10 4 2 0.008 or Less 1 1 5 5 0 0 3 4 8 4 0 5
```

This loses the relationship between columns, row labels, units, and values. For engineering
retrieval, this is serious because the useful knowledge is often inside tables.

### 3. Chunks start in the middle of sentences or page fragments

Some chunks begin with broken fragments such as:

```text
ng Figure 3. Since TAS is unstable...
```

or:

```text
eed rating. P.2226 • Life Confirm...
```

This happens partly because `fixed_chars` is mechanical, but the root issue is that the parser
output is already page/layout-oriented rather than semantic-section-oriented.

### 4. Section, figure, caption, and table content are mixed

The PDF contains selection procedure, product tables, formulas, figures, and cautions. The
current parser flattens them into one text stream. As a result:

- selection procedure text can be mixed with table values
- figure captions can appear near unrelated rows
- formulas can lose surrounding labels
- table values become hard to interpret without column headers

---

## Chunking Results Observed

Three strategies were compared:

```text
fixed_chars          - 28 chunks
paragraph_merge      - 27 chunks
heading_table_aware  - 30 chunks
```

The UI reported:

```text
winner = fixed_chars
```

But this winner is not trustworthy because the evaluation terms were still for the sensor case.
All strategies had zero candidate/expected coverage under that wrong term set.

Manual inspection suggests:

| Strategy | Assessment |
|---|---|
| `fixed_chars` | Baseline only. Often cuts through page fragments or sentences. Not recommended as a semantic winner for this PDF. |
| `paragraph_merge` | Better for narrative sections such as "Ball Screw Selection Procedure". |
| `heading_table_aware` | More promising for section/table-heavy documents, but limited by poor parser output. |

Example of a useful `paragraph_merge` chunk:

```text
1. Ball Screw Selection Procedure
Basic ball screw selection procedure and required evaluation items are shown below.
Determine the application parameters...
Temporary selection of ball screw lead accuracy grade...
Evaluation of various basic safety factors...
Axial Load Capacity...
```

Example of a useful `heading_table_aware` chunk:

```text
2. Ball Screw Lead Accuracy
Ball screw lead accuracy is defined by JIS Standards property parameters...
```

These are better semantically than arbitrary fixed-size cuts, but they still inherit parser
layout noise.

---

## Diagnosis

### Primary Failure

```text
parser_failed_quality
```

The parser does not fail technically; it returns text. But the returned text is low quality for
engineering RAG because it loses structure.

### Why Chunking Cannot Fix This Alone

Chunking operates on parsed text. If parsed text has:

- broken table structure
- page artifacts
- mixed captions and rows
- flattened numeric columns
- missing relationship between labels and values

then chunking can only choose how to split bad input. It cannot reliably reconstruct the original
document semantics.

This is the current situation:

```text
PDF layout -> weak parser -> noisy text -> noisy chunks -> weak retrieval context -> weak LLM answer
```

---

## Impact on RAG

Expected negative effects:

1. Embeddings become less meaningful because chunks contain mixed numeric/layout noise.
2. Retrieval can select chunks because they contain many repeated terms like "ball screw", but
   the chunk may not answer the actual engineering question.
3. Graph extraction can create poor entities from product codes, page artifacts, or table
   fragments.
4. LLM context can be long but still low-value, causing answers that feel vague or hallucinated.

---

## Recommended Parser Improvement Plan

### Phase 1 — Add Parser Comparison in Evaluation UI

Extend `Admin > Adaptive Chunking` into:

```text
Parser + Chunking Evaluation
```

Add parser choices:

```text
pdfplumber
pymupdf
docling
marker
```

For each parser, run the same chunk strategies:

```text
fixed_chars
paragraph_merge
heading_table_aware
```

Evaluate combinations:

```text
pdfplumber + fixed_chars
pdfplumber + paragraph_merge
pdfplumber + heading_table_aware
pymupdf + ...
docling + ...
marker + ...
```

The UI should show:

- parsed text preview
- table extraction preview
- chunk preview
- candidate/expected coverage
- noise score
- evidence chunks
- parser artifacts

### Phase 2 — Add Better PDF Parsers

#### Option A: PyMuPDF

Pros:

- lightweight
- fast
- easier to deploy than heavier document AI parsers
- often better coordinate/text block extraction than basic text extraction

Cons:

- table structure still needs custom handling
- may still flatten complex catalogue layouts

Recommended use:

```text
Add as the next baseline parser.
```

#### Option B: Docling

Pros:

- designed for document conversion
- stronger layout awareness
- can output structured Markdown-like content
- better candidate for technical PDFs with tables

Cons:

- heavier dependency
- may increase Docker image size and parse latency

Recommended use:

```text
Evaluate for catalogue/manual PDFs before production integration.
```

#### Option C: Marker

Pros:

- strong PDF-to-Markdown direction
- often better with structured documents
- useful if OCR/layout recovery is needed

Cons:

- heavier dependency
- may require GPU/CPU tradeoff decisions depending setup
- integration complexity higher

Recommended use:

```text
Evaluate if Docling/PyMuPDF still lose table semantics.
```

### Phase 3 — Table-Aware Extraction

For technical catalogues, table handling should be explicit:

- detect table regions
- preserve column headers
- preserve row labels
- emit Markdown tables where possible
- attach nearby heading/caption to the table

Desired output:

```markdown
## Ball Screw Lead Accuracy

| Accuracy grade | Effective thread length | Allowable travel error |
|---|---:|---:|
| C3 | ... | ... |
```

This is much better for retrieval than flattened number streams.

### Phase 4 — Parser Quality Metrics

Add parser-specific metrics to diagnostics:

| Metric | Purpose |
|---|---|
| `header_footer_artifact_count` | Detect repeated page/catalogue artifacts |
| `numeric_density` | Detect table flattening and low semantic value |
| `table_reconstruction_count` | Count recovered tables |
| `heading_count` | Detect whether section structure survives |
| `avg_line_length` | Detect layout flattening or OCR issues |
| `broken_token_count` | Detect artifacts like `CC__006688...` |
| `semantic_anchor_hit_rate` | Check if expected headings are preserved |

For Ball Screws, semantic anchors should include:

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

### Phase 5 — Production Integration Gate

Do not replace ingestion parser immediately. First require evidence that the new parser:

- reduces layout artifacts
- preserves headings
- preserves tables better
- improves evidence chunk quality
- improves Diagnostics retrieval for real questions
- does not significantly break DOCX/TXT flows

Only after that should backend ingestion consider using the improved parser before sending text
to LightRAG `/documents/text`.

---

## Immediate Next Actions

1. Re-run Ball Screw evaluation with Ball Screw-specific candidate/expected terms.
2. Add parser selection to the evaluation UI.
3. Implement PyMuPDF as the first alternative parser.
4. Add parsed text preview per parser.
5. Add parser quality metrics to report.
6. Compare:

```text
pdfplumber vs pymupdf
```

before trying heavier parsers like Docling or Marker.

---

## Final Conclusion

For the Ball Screws Selection Guide PDF, the current issue is not primarily chunk strategy.
The current issue is parser quality.

`pdfplumber` extracts technically non-empty text, but the extracted text is too layout-damaged
for reliable engineering RAG. Chunking improvements can help narrative sections, but they cannot
recover lost table structure or clean page artifacts.

Recommended direction:

```text
Prioritize parser comparison and table-aware PDF extraction before optimizing chunking further.
```
