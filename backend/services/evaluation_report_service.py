from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from backend.config import settings


REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _artifact_dir() -> Path:
    configured = Path(settings.ADAPTIVE_CHUNKING_ARTIFACT_DIR)
    if configured.exists():
        return configured

    cwd_candidate = Path.cwd() / "docs" / "experiments" / "artifacts" / "adaptive-chunking"
    if cwd_candidate.exists():
        return cwd_candidate

    backend_parent_candidate = Path(__file__).resolve().parents[2] / "docs" / "experiments" / "artifacts" / "adaptive-chunking"
    return backend_parent_candidate


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
        "document_count": int(summary.get("document_count") or len(report.get("documents") or [])),
        "path": str(path),
    }


def list_adaptive_chunking_reports() -> list[dict[str, Any]]:
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


def get_adaptive_chunking_report(report_id: str) -> dict[str, Any] | None:
    if not REPORT_ID_RE.match(report_id):
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

