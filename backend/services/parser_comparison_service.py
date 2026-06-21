from __future__ import annotations

import importlib.metadata
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.schemas.parser_evaluations import ParserComparisonRunRequest
from backend.services.adaptive_chunking_evaluation_service import (
    _fixed_chars,
    _heading_table_aware,
    _paragraph_merge,
)
from backend.services.evaluation_report_service import REPORT_ID_RE


PARSER_REPORT_ID_RE = REPORT_ID_RE
SUPPORTED_PARSERS = {"pdfplumber", "pymupdf", "docling"}
ARTIFACT_DIR = Path("/app/docs/experiments/artifacts/pdf-parser-comparison")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _artifact_dir() -> Path:
    configured = ARTIFACT_DIR
    if configured.exists():
        return configured
    return _workspace_root() / "docs" / "experiments" / "artifacts" / "pdf-parser-comparison"


def _safe_run_id(value: str | None) -> str:
    candidate = (value or f"pdf-parser-comparison-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}").strip()
    candidate = re.sub(r"[^A-Za-z0-9_.-]+", "-", candidate).strip("-")
    if not candidate:
        candidate = f"pdf-parser-comparison-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    if not PARSER_REPORT_ID_RE.match(candidate):
        raise ValueError("Invalid run_id")
    return candidate


def _resolve_source_path(source_path: str) -> Path:
    raw = source_path.strip()
    if not raw:
        raise FileNotFoundError("Source path is empty")

    normalized = raw.replace("\\", "/")
    candidates: list[Path] = []
    if "/local-nas/" in normalized:
        suffix = normalized.split("/local-nas/", 1)[1]
        candidates.append(Path("/local-nas") / suffix)
        candidates.append(_workspace_root() / "local-nas" / suffix)
    elif normalized.startswith("local-nas/"):
        suffix = normalized.removeprefix("local-nas/")
        candidates.append(Path("/local-nas") / suffix)
        candidates.append(_workspace_root() / "local-nas" / suffix)
    elif normalized.startswith("/"):
        candidates.append(Path(normalized))
    else:
        candidates.append(_workspace_root() / raw)
    candidates.append(Path(raw))

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists():
            return resolved
    raise FileNotFoundError(f"Source path not found: {source_path}")


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _parse_with_pdfplumber(path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:
        return _parser_unavailable("pdfplumber", exc)

    pages: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            pages.append({"page_number": page_index, "text": text, "blocks": []})
    text = "\n\n".join(page["text"] for page in pages)
    normalized = _normalize_text(text)
    return {
        "parser": "pdfplumber",
        "status": "ok",
        "source_path": str(path),
        "text": text.replace("\r\n", "\n").replace("\r", "\n"),
        "normalized_text": normalized,
        "pages": pages,
        "tables": _detect_table_candidates(normalized),
        "metadata": {
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "parser_version": _package_version("pdfplumber"),
        },
    }


def _parse_with_pymupdf(path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        import fitz  # type: ignore
    except Exception as exc:
        return _parser_unavailable("pymupdf", exc)

    pages: list[dict[str, Any]] = []
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            raw_blocks = page.get_text("blocks")
            blocks: list[dict[str, Any]] = []
            for block_index, block in enumerate(raw_blocks):
                x0, y0, x1, y1, text, *_rest = block
                clean = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
                if clean:
                    blocks.append({
                        "type": "text",
                        "block_index": block_index,
                        "text": clean,
                        "bbox": [round(float(x0), 3), round(float(y0), 3), round(float(x1), 3), round(float(y1), 3)],
                    })
            blocks.sort(key=lambda item: (item["bbox"][1], item["bbox"][0], item["block_index"]))
            pages.append({
                "page_number": page_index,
                "text": "\n".join(block["text"] for block in blocks),
                "blocks": blocks,
            })
    text = "\n\n".join(page["text"] for page in pages)
    normalized = _normalize_text(text)
    return {
        "parser": "pymupdf",
        "status": "ok",
        "source_path": str(path),
        "text": text,
        "normalized_text": normalized,
        "pages": pages,
        "tables": _detect_table_candidates(normalized),
        "metadata": {
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "parser_version": _package_version("pymupdf") or _package_version("PyMuPDF"),
        },
    }


def _parse_with_docling(path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    worker = _run_external_parser("docling", path, Path("/opt/docling-venv/bin/python"), timeout_seconds=900)
    if worker.get("status") != "ok":
        return _external_parse_failed("docling", path, worker, started)

    markdown = str(worker.get("text") or "")
    normalized = _normalize_text(markdown)
    return {
        "parser": "docling",
        "status": "ok",
        "source_path": str(path),
        "text": markdown,
        "normalized_text": normalized,
        "pages": [{"page_number": None, "text": markdown, "blocks": []}],
        "tables": _extract_markdown_tables(normalized) or _detect_table_candidates(normalized),
        "metadata": {
            "latency_ms": worker.get("metadata", {}).get("latency_ms", round((time.perf_counter() - started) * 1000, 2)),
            "parser_version": worker.get("metadata", {}).get("parser_version"),
        },
    }


def _run_external_parser(parser: str, path: Path, python_path: Path, timeout_seconds: int) -> dict[str, Any]:
    if not python_path.exists():
        return {"status": "parser_unavailable", "error": f"{python_path} does not exist"}
    worker_path = Path(__file__).resolve().parent / "parser_worker.py"
    try:
        completed = subprocess.run(
            [str(python_path), str(worker_path), parser, str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "parse_failed", "error": f"{parser} timed out after {timeout_seconds}s"}

    stdout = completed.stdout.strip()
    if not stdout:
        return {"status": "parse_failed", "error": completed.stderr.strip() or f"{parser} returned no output"}
    try:
        payload = json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError:
        return {"status": "parse_failed", "error": f"{parser} returned non-JSON output: {stdout[-1000:]}"}
    if completed.returncode != 0 and payload.get("status") == "ok":
        payload["status"] = "parse_failed"
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()[-4000:]
    return payload


def _external_parse_failed(parser: str, path: Path, worker: dict[str, Any], started: float) -> dict[str, Any]:
    status = str(worker.get("status") or "parse_failed")
    if status not in {"parser_unavailable", "parse_failed"}:
        status = "parse_failed"
    return {
        "parser": parser,
        "status": status,
        "source_path": str(path),
        "text": "",
        "normalized_text": "",
        "pages": [],
        "tables": [],
        "metadata": {
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "parser_version": None,
        },
        "error": worker.get("error") or worker.get("stderr") or f"{parser} parse failed",
    }


def _parser_unavailable(parser: str, exc: Exception) -> dict[str, Any]:
    return {
        "parser": parser,
        "status": "parser_unavailable",
        "text": "",
        "normalized_text": "",
        "pages": [],
        "tables": [],
        "metadata": {"latency_ms": 0, "parser_version": None},
        "error": f"{parser} unavailable: {exc}",
    }


def _detect_table_candidates(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = text.splitlines()
    current: list[str] = []
    start_line = 0

    def is_numeric_dense(line: str) -> bool:
        tokens = line.split()
        if len(tokens) < 6:
            return False
        numeric = sum(1 for token in tokens if re.search(r"\d", token))
        return numeric / max(len(tokens), 1) >= 0.55

    def flush(end_line: int) -> None:
        nonlocal current
        if len(current) >= 2:
            tables.append({
                "type": "low_confidence_table_region",
                "confidence": "low",
                "start_line": start_line,
                "end_line": end_line,
                "markdown": "",
                "text": "\n".join(current)[:4000],
            })
        current = []

    for index, line in enumerate(lines):
        if is_numeric_dense(line):
            if not current:
                start_line = index + 1
            current.append(line)
        elif current:
            flush(index)
    if current:
        flush(len(lines))
    return tables[:25]


def _extract_markdown_tables(text: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    lines = text.splitlines()
    current: list[str] = []
    start_line = 0

    def is_table_line(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

    def flush(end_line: int) -> None:
        nonlocal current
        if len(current) >= 2 and any("---" in line for line in current[:3]):
            tables.append({
                "type": "markdown_table",
                "confidence": "medium",
                "start_line": start_line,
                "end_line": end_line,
                "markdown": "\n".join(current),
                "text": "\n".join(current),
            })
        current = []

    for index, line in enumerate(lines):
        if is_table_line(line):
            if not current:
                start_line = index + 1
            current.append(line)
        elif current:
            flush(index)
    if current:
        flush(len(lines))
    return tables[:50]


def _parser_metrics(parsed: dict[str, Any], semantic_anchors: list[str]) -> dict[str, Any]:
    text = str(parsed.get("normalized_text") or parsed.get("text") or "")
    lines = text.splitlines()
    empty_lines = sum(1 for line in lines if not line.strip())
    tokens = re.findall(r"\S+", text)
    numeric_tokens = sum(1 for token in tokens if re.search(r"\d", token))
    broken_tokens = len(re.findall(r"(?:[A-Z]{2}__\d+|_{2,}|[A-Za-z]{1,2}\d{4,}[A-Za-z]{1,2})", text))
    artifact_count = len(re.findall(r"(?:CC__|FF\d+|ccEENNGG|cENG\s+\d)", text))
    headings = [
        line for line in lines
        if 4 <= len(line) <= 120 and (
            bool(re.match(r"^\d+[\.\)]\s+[A-Z]", line))
            or line.isupper()
            or any(anchor.lower() in line.lower() for anchor in semantic_anchors)
        )
    ]
    anchor_hits = {anchor: anchor.lower() in text.lower() for anchor in semantic_anchors}
    anchor_total = max(len(anchor_hits), 1)
    tables = parsed.get("tables") if isinstance(parsed.get("tables"), list) else []
    reconstructed_tables = [table for table in tables if table.get("markdown")]
    low_quality = (
        bool(text)
        and (
            artifact_count > 5
            or broken_tokens > 20
            or numeric_tokens / max(len(tokens), 1) > 0.38
            or (semantic_anchors and sum(1 for hit in anchor_hits.values() if hit) == 0)
        )
    )
    return {
        "char_count": len(text),
        "line_count": len(lines),
        "empty_line_ratio": round(empty_lines / max(len(lines), 1), 6),
        "header_footer_artifact_count": artifact_count,
        "broken_token_count": broken_tokens,
        "numeric_density": round(numeric_tokens / max(len(tokens), 1), 6),
        "heading_count": len(headings),
        "table_candidate_count": len(tables),
        "reconstructed_table_count": len(reconstructed_tables),
        "semantic_anchor_hit_rate": round(sum(1 for hit in anchor_hits.values() if hit) / anchor_total, 6),
        "semantic_anchor_hits": anchor_hits,
        "latency_ms": parsed.get("metadata", {}).get("latency_ms", 0),
        "low_quality": low_quality,
    }


def _term_metrics(text: str, candidate_terms: dict[str, list[str]], expected_terms: list[str], noise_terms: list[str]) -> dict[str, Any]:
    lower = text.lower()
    by_candidate = {
        candidate: any(alias.lower() in lower for alias in aliases)
        for candidate, aliases in candidate_terms.items()
    }
    by_expected = {term: term.lower() in lower for term in expected_terms if term}
    noise_hit_count = sum(lower.count(term.lower()) for term in noise_terms if term)
    return {
        "candidate_coverage": {
            "rate": round(sum(1 for hit in by_candidate.values() if hit) / max(len(by_candidate), 1), 6),
            "by_candidate": by_candidate,
        },
        "expected_term_coverage": {
            "rate": round(sum(1 for hit in by_expected.values() if hit) / max(len(by_expected), 1), 6),
            "by_term": by_expected,
        },
        "noise_hit_count": noise_hit_count,
    }


def _chunk_matrix(parsed: dict[str, Any], payload: ParserComparisonRunRequest) -> list[dict[str, Any]]:
    text = str(parsed.get("normalized_text") or parsed.get("text") or "")
    source_path = str(parsed.get("source_path") or "")
    strategies = {
        "fixed_chars": _fixed_chars(text, source_path, payload.target_chars, payload.overlap_chars),
        "paragraph_merge": _paragraph_merge(text, source_path, payload.target_chars, payload.max_chars),
        "heading_table_aware": _heading_table_aware(text, source_path, payload.target_chars, payload.max_chars),
    }
    rows: list[dict[str, Any]] = []
    for name, chunks in strategies.items():
        joined = "\n\n".join(str(chunk.get("text", "")) for chunk in chunks)
        rows.append({
            "strategy": name,
            "chunk_count": len(chunks),
            "avg_chunk_chars": round(sum(int(chunk.get("char_count", 0)) for chunk in chunks) / max(len(chunks), 1), 2),
            "max_chunk_chars": max((int(chunk.get("char_count", 0)) for chunk in chunks), default=0),
            "term_metrics": _term_metrics(joined, payload.candidate_terms, payload.expected_terms, payload.noise_terms),
            "sample_chunks": chunks[:3],
        })
    return rows


def _parser_score(metrics: dict[str, Any], term_metrics: dict[str, Any]) -> float:
    score = 0.0
    score += float(metrics.get("semantic_anchor_hit_rate") or 0) * 35
    score += float(term_metrics.get("candidate_coverage", {}).get("rate") or 0) * 20
    score += float(term_metrics.get("expected_term_coverage", {}).get("rate") or 0) * 20
    score += min(int(metrics.get("heading_count") or 0), 20) * 0.5
    score -= min(float(metrics.get("numeric_density") or 0), 1) * 15
    score -= min(int(metrics.get("header_footer_artifact_count") or 0), 50) * 0.2
    score -= min(int(metrics.get("broken_token_count") or 0), 100) * 0.1
    score -= min(int(term_metrics.get("noise_hit_count") or 0), 50) * 0.15
    return round(score, 6)


def _parse(path: Path, parser: str) -> dict[str, Any]:
    if parser == "pdfplumber":
        return _parse_with_pdfplumber(path)
    if parser == "pymupdf":
        return _parse_with_pymupdf(path)
    if parser == "docling":
        return _parse_with_docling(path)
    return {
        "parser": parser,
        "status": "unsupported_parser",
        "text": "",
        "normalized_text": "",
        "pages": [],
        "tables": [],
        "metadata": {"latency_ms": 0, "parser_version": None},
        "error": f"Unsupported parser: {parser}",
    }


def _write_json_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{report['run_id']}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_markdown_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {report.get('title', 'PDF Parser Comparison')}",
        "",
        f"**Run ID:** `{report['run_id']}`  ",
        f"**Recommendation:** `{report['summary']['recommendation']}`  ",
        f"**Recommended parser:** `{report['summary'].get('recommended_parser') or '-'}`",
        "",
        "## Documents",
        "",
    ]
    for document in report["documents"]:
        lines.extend([
            f"### {document['document_id']}",
            "",
            f"**Source:** `{document.get('source_path', '-')}`",
            "",
            "| Parser | Status | Score | Anchors | Numeric Density | Artifacts | Broken Tokens | Latency ms |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ])
        for result in document.get("parser_results", []):
            metrics = result.get("metrics", {})
            lines.append(
                f"| {result.get('parser')} | {result.get('status')} | {result.get('score', 0)} | "
                f"{metrics.get('semantic_anchor_hit_rate', 0)} | {metrics.get('numeric_density', 0)} | "
                f"{metrics.get('header_footer_artifact_count', 0)} | {metrics.get('broken_token_count', 0)} | "
                f"{metrics.get('latency_ms', 0)} |"
            )
        lines.append("")
    (output_dir / f"{report['run_id']}.md").write_text("\n".join(lines), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_from_report(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    summary = report.get("summary") or {}
    return {
        "id": path.stem,
        "title": report.get("title") or path.stem,
        "created_at": report.get("created_at"),
        "recommendation": summary.get("recommendation") or "inconclusive",
        "recommended_parser": summary.get("recommended_parser"),
        "document_count": int(summary.get("document_count") or len(report.get("documents") or [])),
        "path": str(path),
    }


def list_pdf_parser_comparison_reports() -> list[dict[str, Any]]:
    root = _artifact_dir()
    if not root.exists():
        return []
    reports = []
    for path in sorted(root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            reports.append(_summary_from_report(path))
        except Exception:
            continue
    return reports


def get_pdf_parser_comparison_report(report_id: str) -> dict[str, Any] | None:
    if not PARSER_REPORT_ID_RE.match(report_id):
        return None
    root = _artifact_dir()
    path = (root / f"{report_id}.json").resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    if not path.exists():
        return None
    report = _load_json(path)
    markdown_path = path.with_suffix(".md")
    markdown = markdown_path.read_text(encoding="utf-8", errors="replace") if markdown_path.exists() else None
    return {
        "id": path.stem,
        "title": report.get("title") or path.stem,
        "created_at": report.get("created_at"),
        "summary": report.get("summary") or {},
        "documents": report.get("documents") or [],
        "markdown": markdown,
        "raw": report,
    }


def run_pdf_parser_comparison(payload: ParserComparisonRunRequest) -> dict[str, Any]:
    run_id = _safe_run_id(payload.run_id)
    output_dir = _artifact_dir()
    parsers = [parser.strip().lower() for parser in payload.parsers if parser.strip()]
    if not parsers:
        parsers = ["pdfplumber", "pymupdf"]
    documents: list[dict[str, Any]] = []
    parser_scores: dict[str, list[float]] = {}

    for index, document in enumerate(payload.documents, start=1):
        document_id = document.document_id or Path(document.source_path).stem or f"document-{index}"
        try:
            source_path = _resolve_source_path(document.source_path)
            if source_path.suffix.lower() != ".pdf":
                raise ValueError(f"Only PDF files are supported in parser comparison V1: {source_path.suffix}")
            parser_results: list[dict[str, Any]] = []
            for parser in parsers:
                parsed = _parse(source_path, parser)
                metrics = _parser_metrics(parsed, payload.semantic_anchors)
                terms = _term_metrics(str(parsed.get("normalized_text") or parsed.get("text") or ""), payload.candidate_terms, payload.expected_terms, payload.noise_terms)
                score = _parser_score(metrics, terms) if parsed.get("status") == "ok" else -999
                parser_scores.setdefault(parser, []).append(float(score))
                parser_results.append({
                    "parser": parser,
                    "status": parsed.get("status"),
                    "error": parsed.get("error"),
                    "score": score,
                    "metrics": metrics,
                    "term_metrics": terms,
                    "metadata": parsed.get("metadata") or {},
                    "text": parsed.get("text") or "",
                    "normalized_text": parsed.get("normalized_text") or "",
                    "pages": parsed.get("pages") or [],
                    "tables": parsed.get("tables") or [],
                    "chunk_matrix": _chunk_matrix(parsed, payload) if parsed.get("status") == "ok" else [],
                })
            best = max(parser_results, key=lambda item: float(item.get("score") or -999), default=None)
            documents.append({
                "document_id": document_id,
                "source_path": str(source_path),
                "status": "ok",
                "recommended_parser": best.get("parser") if best else None,
                "parser_results": parser_results,
            })
        except Exception as exc:
            documents.append({
                "document_id": document_id,
                "source_path": document.source_path,
                "status": "error",
                "error": str(exc),
                "parser_results": [],
            })

    average_scores = {
        parser: round(sum(scores) / max(len(scores), 1), 6)
        for parser, scores in parser_scores.items()
        if scores
    }
    recommended_parser = max(average_scores, key=average_scores.get) if average_scores else None
    recommendation = "needs_more_evidence"
    if recommended_parser and recommended_parser != "pdfplumber":
        recommendation = "candidate_improvement"
    elif recommended_parser == "pdfplumber":
        recommendation = "baseline_still_best"

    report = {
        "run_id": run_id,
        "title": payload.title or "PDF Parser Comparison",
        "created_at": datetime.now(UTC).isoformat(),
        "config": {
            "parsers": parsers,
            "semantic_anchors": payload.semantic_anchors,
            "candidate_terms": payload.candidate_terms,
            "expected_terms": payload.expected_terms,
            "noise_terms": payload.noise_terms,
            "target_chars": payload.target_chars,
            "overlap_chars": payload.overlap_chars,
            "max_chars": payload.max_chars,
        },
        "summary": {
            "recommendation": recommendation,
            "recommended_parser": recommended_parser,
            "average_scores": average_scores,
            "document_count": len(documents),
            "evaluable_document_count": sum(1 for document in documents if document.get("status") == "ok"),
        },
        "documents": documents,
    }
    _write_json_report(report, output_dir)
    _write_markdown_report(report, output_dir)
    detail = get_pdf_parser_comparison_report(run_id)
    if detail is None:
        raise RuntimeError("Parser comparison report was written but could not be read back")
    return detail
