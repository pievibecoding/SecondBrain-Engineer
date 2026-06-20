import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "experiments" / "adaptive-chunking" / "metrics.py"
spec = importlib.util.spec_from_file_location("adaptive_metrics", MODULE_PATH)
metrics = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(metrics)


def test_candidate_coverage_and_noise_metrics():
    chunks = [
        {"text": "Omron E3Z-B detects transparent bottle with photoelectric sensor."},
        {"text": "Mounting screw and maintenance note."},
    ]

    result = metrics.evaluate_chunks(
        chunks,
        {"E3Z": ["E3Z"], "BMS": ["BMS"]},
        ["transparent bottle", "photoelectric sensor"],
        ["mounting screw", "maintenance"],
    )

    assert result["candidate_coverage"]["rate"] == 0.5
    assert result["expected_term_coverage"]["rate"] == 1.0
    assert result["noise_hit_count"] == 2

