# Ball Screw Parser Smoke

**Run ID:** `ball-screw-parser-smoke`  
**Recommendation:** `candidate_improvement`  
**Recommended parser:** `pymupdf`

## Documents

### ball-screw

**Source:** `/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf`

| Parser | Status | Score | Anchors | Numeric Density | Artifacts | Broken Tokens | Latency ms |
|---|---|---:|---:|---:|---:|---:|---:|
| pdfplumber | ok | 67.30994 | 0.875 | 0.231004 | 12 | 11 | 4795.57 |
| pymupdf | ok | 71.709155 | 0.875 | 0.247723 | 0 | 2 | 543.85 |
