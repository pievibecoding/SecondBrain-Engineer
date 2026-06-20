# Ball Screw Parser Comparison

**Run ID:** `ball-screw-parser-comparison`  
**Recommendation:** `baseline_still_best`  
**Recommended parser:** `pdfplumber`

## Documents

### test

**Source:** `/local-nas/DATN_TLTK/test_no_text.pdf`

| Parser | Status | Score | Anchors | Numeric Density | Artifacts | Broken Tokens | Latency ms |
|---|---|---:|---:|---:|---:|---:|---:|
| pdfplumber | ok | 0.0 | 0.0 | 0.0 | 0 | 0 | 22.95 |
| pymupdf | ok | 0.0 | 0.0 | 0.0 | 0 | 0 | 52.01 |
| docling | ok | -0.627055 | 0.0 | 0.275137 | 0 | 0 | 61710.0 |
