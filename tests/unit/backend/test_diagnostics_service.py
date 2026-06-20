from backend.services.diagnostics_service import _diagnose


def test_diagnose_retrieval_failed_when_expected_source_missing():
    stages = {
        "parse": {"status": "ok", "text": "Lỗi giới hạn trục cảm biến hành trình reset lỗi"},
        "chunks": {"status": "ok", "text": "Lỗi giới hạn trục cảm biến hành trình reset lỗi"},
        "retrieval": {"status": "ok", "source_hit": False, "term_hit_rate": 1.0},
        "llm": {"status": "ok", "answer": "Reset lỗi"},
    }

    diagnosis = _diagnose(stages, ["Lỗi giới hạn trục"], ["/expected.docx"])

    assert diagnosis.code == "retrieval_failed"


def test_diagnose_llm_bad_when_context_has_terms_but_answer_does_not():
    stages = {
        "parse": {"status": "ok", "text": "Lỗi giới hạn trục cảm biến hành trình reset lỗi"},
        "chunks": {"status": "ok", "text": "Lỗi giới hạn trục cảm biến hành trình reset lỗi"},
        "retrieval": {"status": "ok", "source_hit": True, "term_hit_rate": 1.0},
        "llm": {"status": "ok", "answer": "Không tìm thấy thông tin."},
    }

    diagnosis = _diagnose(stages, ["Lỗi giới hạn trục"], [])

    assert diagnosis.code == "llm_bad"
