from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chunkers import run_strategies
from metrics import evaluate_chunks, score_metrics
from report_writer import write_json_report, write_markdown_report
from source_loader import load_source_text


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _upstream_status() -> dict[str, Any]:
    try:
        __import__("adaptive_chunking")
        return {"available": True, "mode": "upstream"}
    except Exception as exc:
        return {"available": False, "mode": "local_fallback", "reason": str(exc)}


def _recommendation(documents: list[dict[str, Any]]) -> str:
    evaluable = [document for document in documents if document.get("status") == "ok"]
    if not evaluable:
        return "inconclusive"
    improved = 0
    regressed = 0
    for document in evaluable:
        baseline = next((item for item in document["strategies"] if item["name"] == "fixed_chars"), None)
        winner = next((item for item in document["strategies"] if item["name"] == document["winner"]), None)
        if not baseline or not winner:
            continue
        delta = winner["metrics"]["candidate_coverage"]["rate"] - baseline["metrics"]["candidate_coverage"]["rate"]
        noise_delta = winner["metrics"]["noise_hit_count"] - baseline["metrics"]["noise_hit_count"]
        if delta > 0 or noise_delta < 0:
            improved += 1
        elif delta < 0 or noise_delta > 0:
            regressed += 1
    if improved and not regressed:
        return "recommended"
    if regressed > improved:
        return "not_recommended"
    return "inconclusive"


def run(config_path: Path) -> dict[str, Any]:
    workspace = _workspace_root()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = workspace / config.get("output_dir", "docs/experiments/artifacts/adaptive-chunking")
    chunking_config = config.get("chunking", {})
    max_chars = int(chunking_config.get("max_chars", 4200))
    documents: list[dict[str, Any]] = []

    for document_config in config.get("documents", []):
        document_id = document_config["document_id"]
        source_path = document_config["source_path"]
        document_result: dict[str, Any] = {
            "document_id": document_id,
            "source_path": source_path,
            "status": "ok",
            "strategies": [],
        }
        try:
            source = load_source_text(source_path, workspace)
            document_result["source_path"] = source["source_path"]
            document_result["parser"] = source["parser"]
            document_result["source_stats"] = source["stats"]
            strategy_chunks = run_strategies(source["text"], source["source_path"], chunking_config)
            chunks_output_dir = output_dir / "chunks"
            chunks_output_dir.mkdir(parents=True, exist_ok=True)

            for strategy_name, chunks in strategy_chunks.items():
                metrics = evaluate_chunks(
                    chunks,
                    config.get("candidate_terms", {}),
                    config.get("expected_terms", []),
                    config.get("noise_terms", []),
                )
                score = score_metrics(metrics, max_chars)
                chunks_path = chunks_output_dir / f"{document_id}-{strategy_name}.json"
                chunks_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
                document_result["strategies"].append({
                    "name": strategy_name,
                    "chunk_count": len(chunks),
                    "chunks_path": str(chunks_path.relative_to(workspace)),
                    "metrics": metrics,
                    "score": score,
                    "sample_chunks": chunks[:3],
                })
            document_result["winner"] = max(
                document_result["strategies"],
                key=lambda item: item["score"]["score"],
            )["name"]
        except Exception as exc:
            document_result.update({"status": "error", "error": str(exc), "winner": None})
        documents.append(document_result)

    evaluable = [document for document in documents if document.get("status") == "ok"]
    deltas: list[float] = []
    noise_deltas: list[int] = []
    for document in evaluable:
        baseline = next((item for item in document["strategies"] if item["name"] == "fixed_chars"), None)
        winner = next((item for item in document["strategies"] if item["name"] == document["winner"]), None)
        if baseline and winner:
            deltas.append(winner["metrics"]["candidate_coverage"]["rate"] - baseline["metrics"]["candidate_coverage"]["rate"])
            noise_deltas.append(winner["metrics"]["noise_hit_count"] - baseline["metrics"]["noise_hit_count"])

    report = {
        "run_id": config.get("run_id", f"adaptive-chunking-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"),
        "title": config.get("title", "Adaptive Chunking Evaluation"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "recommendation": _recommendation(documents),
            "document_count": len(documents),
            "evaluable_document_count": len(evaluable),
            "avg_candidate_coverage_delta": round(sum(deltas) / max(len(deltas), 1), 6),
            "avg_noise_delta": round(sum(noise_deltas) / max(len(noise_deltas), 1), 6),
        },
        "upstream_adaptive_chunking": _upstream_status(),
        "config": config,
        "documents": documents,
    }
    json_path = write_json_report(report, output_dir)
    markdown_path = write_markdown_report(report, output_dir)
    report["artifacts"] = {"json": str(json_path.relative_to(workspace)), "markdown": str(markdown_path.relative_to(workspace))}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run adaptive chunking evaluation")
    parser.add_argument("--config", required=True, help="Path to evaluation config JSON")
    args = parser.parse_args()
    report = run(Path(args.config).resolve())
    print(json.dumps({
        "run_id": report["run_id"],
        "recommendation": report["summary"]["recommendation"],
        "artifacts": report["artifacts"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
