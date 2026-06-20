from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report['run_id']}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_markdown_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report['run_id']}.md"
    lines = [
        f"# {report.get('title', 'Adaptive Chunking Evaluation')}",
        "",
        f"**Run ID:** `{report['run_id']}`  ",
        f"**Recommendation:** `{report['summary']['recommendation']}`",
        "",
        "## Aggregate",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Documents | {report['summary']['document_count']} |",
        f"| Evaluable documents | {report['summary']['evaluable_document_count']} |",
        f"| Average candidate coverage delta | {report['summary']['avg_candidate_coverage_delta']} |",
        f"| Average noise delta | {report['summary']['avg_noise_delta']} |",
        "",
        "## Documents",
        "",
    ]

    for document in report["documents"]:
        lines.extend([
            f"### {document['document_id']}",
            "",
            f"**Source:** `{document.get('source_path', '-')}`  ",
            f"**Winner:** `{document.get('winner', '-')}`  ",
            f"**Status:** `{document.get('status', '-')}`",
            "",
        ])
        if document.get("error"):
            lines.extend([f"**Error:** {document['error']}", ""])
            continue
        lines.extend([
            "| Strategy | Score | Candidate Coverage | Expected Coverage | Noise Hits | Max Chunk Chars |",
            "|----------|-------|--------------------|-------------------|------------|-----------------|",
        ])
        for strategy in document.get("strategies", []):
            metrics = strategy["metrics"]
            lines.append(
                f"| {strategy['name']} | {strategy['score']['score']} | "
                f"{metrics['candidate_coverage']['rate']} | "
                f"{metrics['expected_term_coverage']['rate']} | "
                f"{metrics['noise_hit_count']} | {metrics['max_chunk_chars']} |"
            )
        lines.extend(["", "#### Top Evidence", ""])
        winner = next((item for item in document.get("strategies", []) if item["name"] == document.get("winner")), None)
        evidence = (winner or {}).get("metrics", {}).get("top_evidence", [])
        if not evidence:
            lines.append("_No evidence chunks found._")
        for item in evidence[:3]:
            lines.extend([
                f"- score `{item['score']}`, chunk `{item['chunk_index']}`, chars `{item['char_count']}`",
                "",
                "```text",
                item["text"][:1000],
                "```",
                "",
            ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

