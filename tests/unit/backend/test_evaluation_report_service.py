import json

from backend.services import evaluation_report_service


def test_list_and_get_adaptive_chunking_report(tmp_path, monkeypatch):
    report = {
        "run_id": "sample-report",
        "title": "Sample Report",
        "created_at": "2026-06-20T00:00:00Z",
        "summary": {"recommendation": "recommended", "document_count": 1},
        "documents": [{"document_id": "doc-1"}],
    }
    (tmp_path / "sample-report.json").write_text(json.dumps(report), encoding="utf-8")
    (tmp_path / "sample-report.md").write_text("# Sample Report", encoding="utf-8")
    monkeypatch.setattr(evaluation_report_service.settings, "ADAPTIVE_CHUNKING_ARTIFACT_DIR", str(tmp_path))

    reports = evaluation_report_service.list_adaptive_chunking_reports()
    detail = evaluation_report_service.get_adaptive_chunking_report("sample-report")

    assert reports[0]["id"] == "sample-report"
    assert reports[0]["recommendation"] == "recommended"
    assert detail is not None
    assert detail["markdown"] == "# Sample Report"


def test_get_adaptive_chunking_report_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation_report_service.settings, "ADAPTIVE_CHUNKING_ARTIFACT_DIR", str(tmp_path))

    assert evaluation_report_service.get_adaptive_chunking_report("../secret") is None

