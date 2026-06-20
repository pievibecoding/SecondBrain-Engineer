# EXP-009 — Docling and Marker Parser Comparison Attempt

## Summary

This experiment extends EXP-008 by enabling real Docling and Marker adapters for PDF parser
comparison.

Source:

```text
/local-nas/DATN_TLTK/7. Ball Screws Selection Guide.pdf
```

Artifacts:

```text
docs/experiments/artifacts/pdf-parser-comparison/ball-screw-docling-smoke.json
docs/experiments/artifacts/pdf-parser-comparison/ball-screw-all-parsers-smoke.json
```

Conclusion:

```text
Docling is a strong parser candidate for this PDF, but it is much slower than PyMuPDF.
Marker is installed and wired through a real adapter, but is not currently practical for this
local UI workflow on this machine because it timed out.
```

---

## Implementation Notes

Docling and Marker cannot safely share the main backend Python environment with `pdfplumber`
because of dependency conflicts around `pypdfium2`.

The backend now uses isolated virtual environments:

```text
/opt/docling-venv
/opt/marker-venv
```

The main backend calls a controlled worker script:

```text
backend/services/parser_worker.py
```

This keeps the Admin UI safe:

- UI does not execute arbitrary commands.
- Backend uses fixed parser worker paths.
- Parser-specific failures are returned as report rows.
- `pdfplumber` and `pymupdf` remain stable in the main environment.

---

## Docling Result

After adding required runtime libraries:

```text
libxcb1
libgl1
libglib2.0-0
```

Docling successfully parsed the Ball Screws PDF.

Result:

| Parser | Score | Anchor hit rate | Numeric density | Artifacts | Broken tokens | Latency |
|---|---:|---:|---:|---:|---:|---:|
| pdfplumber | 67.30994 | 0.875 | 0.231004 | 12 | 11 | ~5018 ms |
| pymupdf | 71.709155 | 0.875 | 0.247723 | 0 | 2 | ~596 ms |
| docling | 73.213165 | 0.875 | 0.160789 | 0 | 0 | ~242007 ms |

Interpretation:

- Docling produced the best score in V1 metrics.
- It eliminated header/footer artifacts and broken tokens.
- It reduced numeric density, which suggests less flattened table noise.
- It detected table regions.
- It is much slower: roughly 4 minutes for this file.

Decision:

```text
Docling is worth evaluating further for table-heavy PDFs, but should not become production
default without queue/background processing and more evidence.
```

---

## Marker Result

Marker was installed in an isolated venv and wired through the same parser worker.

However, for this Ball Screws PDF, Marker did not complete within the original 1200 second
timeout.

Observed status:

```text
marker parse_failed: marker timed out after 1200s
```

After this, the UI timeout was reduced to 300 seconds so a user does not wait too long when
selecting Marker.

Interpretation:

- Marker is too heavy for synchronous local UI evaluation on this machine.
- It pulls a large Torch/CUDA/Surya stack.
- It may still be useful as a separate offline/background parser, but not as a default UI
  parser button for quick tests.

Decision:

```text
Keep Marker as optional experimental parser only.
Do not use Marker in the normal local self-test loop unless running a dedicated long background job.
```

---

## Current Recommendation

For fast local comparison:

```text
pdfplumber + pymupdf
```

For deeper table-heavy PDF analysis:

```text
pdfplumber + pymupdf + docling
```

Avoid selecting Marker in the UI unless intentionally testing a long-running OCR/layout model.

---

## Next Actions

1. Add UI warning next to Marker: "very slow / experimental".
2. Add background-job mode before serious Marker evaluation.
3. Compare Docling output manually in the `Parsed` and `Tables` tabs.
4. Run Diagnostics/RAG evidence gate using PyMuPDF and Docling outputs before any production integration.
