# Ball Screw All Parsers Smoke

**Run ID:** `ball-screw-all-parsers-smoke`  
**Recommendation:** `candidate_improvement`  
**Recommended parser:** `pymupdf`

## Documents

### ball-screw

**Source:** `/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf`

| Parser | Status | Score | Anchors | Numeric Density | Artifacts | Broken Tokens | Latency ms |
|---|---|---:|---:|---:|---:|---:|---:|
| pdfplumber | ok | 67.30994 | 0.875 | 0.231004 | 12 | 11 | 5563.34 |
| pymupdf | ok | 71.709155 | 0.875 | 0.247723 | 0 | 2 | 584.58 |
| docling | parse_failed | -999 | 0.0 | 0.0 | 0 | 0 | 49728.2 |
| marker | parse_failed | -999 | 0.0 | 0.0 | 0 | 0 | 1201132.61 |
