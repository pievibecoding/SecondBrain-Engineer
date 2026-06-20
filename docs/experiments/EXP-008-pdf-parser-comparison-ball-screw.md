# EXP-008 — PDF Parser Comparison on Ball Screws Selection Guide

## Summary

Experiment này chạy parser comparison cho:

```text
/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf
```

Report artifact:

```text
docs/experiments/artifacts/pdf-parser-comparison/ball-screw-parser-smoke.json
docs/experiments/artifacts/pdf-parser-comparison/ball-screw-parser-smoke.md
```

Kết luận bước đầu:

```text
PyMuPDF tốt hơn pdfplumber cho case này theo parser quality metrics V1.
```

Đây chưa phải production integration decision. Đây là bằng chứng đầu tiên để tiếp tục đánh giá qua Diagnostics/RAG.

---

## Setup

Parsers compared:

```text
pdfplumber
pymupdf
```

Semantic anchors:

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

Candidate groups:

```text
Lead
Accuracy
Speed
```

Expected terms:

```text
shaft diameter
axial load capacity
basic dynamic load rating
service life
```

Noise terms:

```text
CC__
ccEENNGG
FF1100
copyright
```

---

## Results

| Parser | Score | Anchor hit rate | Numeric density | Header/footer artifacts | Broken tokens | Latency |
|---|---:|---:|---:|---:|---:|---:|
| pdfplumber | 67.30994 | 0.875 | 0.231004 | 12 | 11 | 4795.57 ms |
| pymupdf | 71.709155 | 0.875 | 0.247723 | 0 | 2 | 543.85 ms |

Report summary:

```json
{
  "recommendation": "candidate_improvement",
  "recommended_parser": "pymupdf",
  "average_scores": {
    "pdfplumber": 67.30994,
    "pymupdf": 71.709155
  },
  "document_count": 1,
  "evaluable_document_count": 1
}
```

---

## Interpretation

PyMuPDF preserved the same semantic anchor hit rate as pdfplumber:

```text
0.875
```

But it significantly reduced parser artifacts:

```text
pdfplumber artifacts: 12
pymupdf artifacts: 0
```

It also reduced broken tokens:

```text
pdfplumber broken tokens: 11
pymupdf broken tokens: 2
```

Latency was much better:

```text
pdfplumber: ~4.8s
pymupdf: ~0.54s
```

Numeric density was slightly higher for PyMuPDF:

```text
pdfplumber: 0.231004
pymupdf: 0.247723
```

This means PyMuPDF may preserve more numeric/table-like content, but V1 metrics cannot yet prove that table semantics are correctly reconstructed.

---

## Decision

Use PyMuPDF as the next parser candidate for evaluation.

Do not integrate production yet.

Required next evidence:

1. Inspect parsed text visually in `Admin > PDF Parser`.
2. Compare table-like regions for Ball Screw pages.
3. Run Diagnostics/RAG using PyMuPDF-normalized text in evaluation mode.
4. Test at least one additional manual-style PDF.
5. Confirm DOCX/TXT behavior is unaffected.

---

## Next Actions

1. Improve table-aware extraction beyond low-confidence numeric region detection.
2. Add a parser comparison report for another PDF type.
3. Add optional Docling/Marker evaluation only if PyMuPDF still fails table semantics.
4. Add automated tests for parser metrics and report read/write.
