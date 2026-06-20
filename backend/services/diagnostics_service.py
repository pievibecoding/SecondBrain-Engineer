from __future__ import annotations

from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.integrations.lightrag.errors import LightRAGError
from backend.integrations.lightrag.query import LightRAGQueryClient
from backend.models.nas_file import NasFile
from backend.schemas.diagnostics import DiagnosticDiagnosis, DiagnosticRequest
from backend.services.document_debug_service import build_document_compare_report


def _contains_all_terms(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return all(term.lower() in lower for term in terms if term.strip())


def _term_hit_rate(text: str, terms: list[str]) -> float:
    clean_terms = [term for term in terms if term.strip()]
    if not clean_terms:
        return 1.0
    lower = text.lower()
    hits = sum(1 for term in clean_terms if term.lower() in lower)
    return round(hits / len(clean_terms), 6)


def _extract_sources(raw_response: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sources = raw_response.get("sources") or raw_response.get("source") or raw_response.get("references") or []
    if isinstance(raw_sources, dict):
        raw_sources = raw_sources.get("sources", [])
    if not isinstance(raw_sources, list):
        return []

    sources: list[dict[str, Any]] = []
    for index, source in enumerate(raw_sources, start=1):
        if isinstance(source, dict):
            raw_content = source.get("content") or source.get("excerpt") or source.get("text") or ""
            if isinstance(raw_content, list):
                content = "\n\n".join(str(item) for item in raw_content)
            else:
                content = str(raw_content)
            nas_path = (
                source.get("nas_path")
                or source.get("file_path")
                or source.get("file")
                or source.get("source")
                or source.get("url")
            )
            sources.append({
                "rank": index,
                "nas_path": nas_path,
                "content": content,
                "raw": source,
            })
        else:
            sources.append({"rank": index, "nas_path": str(source), "content": "", "raw": source})
    return sources


def _source_hit(sources: list[dict[str, Any]], expected_paths: list[str]) -> bool:
    if not expected_paths:
        return True
    source_paths = [str(source.get("nas_path") or "") for source in sources]
    return any(expected in source_path for expected in expected_paths for source_path in source_paths)


def _build_context_text(sources: list[dict[str, Any]]) -> str:
    return "\n\n".join(str(source.get("content") or "") for source in sources)


def _diagnose(stages: dict[str, Any], expected_terms: list[str], expected_source_paths: list[str]) -> DiagnosticDiagnosis:
    parse = stages.get("parse")
    chunks = stages.get("chunks")
    retrieval = stages.get("retrieval", {})
    prompt = stages.get("prompt", {})
    llm = stages.get("llm", {})

    if llm.get("status") == "error" or retrieval.get("status") == "error" or prompt.get("status") == "error":
        error = str(
            retrieval.get("error")
            or prompt.get("error")
            or llm.get("error")
            or "unknown LightRAG error"
        )
        return DiagnosticDiagnosis(
            code="api_failed",
            reason=f"LightRAG query failed before diagnostics could evaluate retrieval or answer quality. Error: {error[:1200]}",
            next_action="Inspect the LightRAG tab/logs, model quota, configured LLM_MODEL, and correlation_id.",
        )

    if parse and parse.get("status") != "ok":
        return DiagnosticDiagnosis(
            code="parse_failed",
            reason=parse.get("error") or "Parser did not produce usable text.",
            next_action="Inspect parser output for this file and improve parser/fallback behavior.",
        )

    if parse and expected_terms and not _contains_all_terms(parse.get("text", ""), expected_terms):
        return DiagnosticDiagnosis(
            code="parse_failed",
            reason="Expected terms are missing from parsed_text.",
            next_action="Fix parser quality or verify the expected terms are present in the source document.",
        )

    if chunks and expected_terms and not _contains_all_terms(chunks.get("text", ""), expected_terms):
        return DiagnosticDiagnosis(
            code="chunk_failed",
            reason="Expected terms exist before retrieval checks but are missing from indexed chunks.",
            next_action="Inspect chunking/indexing output and reindex the document.",
        )

    if expected_source_paths and not retrieval.get("source_hit", True):
        return DiagnosticDiagnosis(
            code="retrieval_failed",
            reason="Expected source path was not returned by retrieval.",
            next_action="Tune retrieval configuration, embeddings, or query phrasing.",
        )

    if expected_terms and retrieval.get("term_hit_rate", 1.0) < 1.0:
        return DiagnosticDiagnosis(
            code="retrieval_failed",
            reason="Retrieved sources do not contain all expected terms.",
            next_action="Inspect retrieved chunks and compare against indexed chunks.",
        )

    answer = llm.get("answer", "")
    if expected_terms and not _contains_all_terms(answer, expected_terms):
        return DiagnosticDiagnosis(
            code="llm_bad",
            reason="Context appears relevant, but answer does not include expected evidence terms.",
            next_action="Compare model output on the same context and adjust prompt/model.",
        )

    return DiagnosticDiagnosis(
        code="ok",
        reason="Diagnostics did not find a clear failure in parse, chunk, retrieval, or LLM stages.",
        next_action="Add stricter expected terms/source paths if the answer still feels wrong.",
    )


async def run_diagnostic(
    db: AsyncSession,
    payload: DiagnosticRequest,
    lightrag: LightRAGQueryClient,
    correlation_id: str,
) -> dict[str, Any]:
    stages: dict[str, Any] = {}
    raw_log: dict[str, Any] = {}

    nas_file: NasFile | None = None
    if payload.file_id:
        result = await db.execute(select(NasFile).where(NasFile.id == payload.file_id))
        nas_file = result.scalar_one_or_none()
        if nas_file is None:
            stages["parse"] = {"status": "error", "error": f"NasFile not found: {payload.file_id}"}
        else:
            compare = await build_document_compare_report(db, nas_file, correlation_id)
            stages["parse"] = {
                "status": "ok" if compare["parsed"]["success"] else "error",
                "parser_used": compare["parsed"]["parser_used"],
                "char_count": compare["parsed"]["char_count"],
                "line_count": compare["parsed"]["line_count"],
                "text": compare["parsed"]["text"],
                "error": None if compare["parsed"]["success"] else "Parser failed or returned empty result.",
            }
            stages["chunks"] = {
                "status": "error" if compare["chunks"]["error"] else "ok",
                "chunk_count": compare["chunks"]["count"],
                "char_count": compare["chunks"]["char_count"],
                "line_count": compare["chunks"]["line_count"],
                "text": compare["chunks"]["text"],
                "similarity_ratio": compare["compare"]["similarity_ratio"],
                "diff": compare["compare"]["diff_preview"],
                "items": compare["chunks"]["items"],
                "error": compare["chunks"]["error"],
            }
            raw_log["document_compare"] = compare

    try:
        prompt_start = perf_counter()
        prompt_response = await lightrag.query(
            payload.query,
            correlation_id,
            mode="mix",
            include_references=True,
            include_chunk_content=True,
            only_need_prompt=True,
        )
        prompt_latency_ms = int((perf_counter() - prompt_start) * 1000)
        prompt_text = prompt_response.get("response") or prompt_response.get("prompt") or prompt_response.get("answer") or ""
        stages["prompt"] = {
            "status": "ok",
            "mode": "mix",
            "char_count": len(prompt_text),
            "text": prompt_text,
            "latency_ms": prompt_latency_ms,
        }
        raw_log["lightrag_prompt_response"] = prompt_response

        query_start = perf_counter()
        raw_response = await lightrag.query(
            payload.query,
            correlation_id,
            mode="mix",
            include_references=True,
            include_chunk_content=True,
        )
        latency_ms = int((perf_counter() - query_start) * 1000)
        sources = _extract_sources(raw_response)
        context_text = _build_context_text(sources)
        answer = raw_response.get("response") or raw_response.get("answer") or ""

        stages["retrieval"] = {
            "status": "ok",
            "mode": "mix",
            "sources": sources,
            "source_hit": _source_hit(sources, payload.expected_source_paths),
            "term_hit_rate": _term_hit_rate(context_text, payload.expected_terms),
        }
        stages["context"] = {
            "status": "ok",
            "char_count": len(context_text),
            "text": context_text,
            "term_hit_rate": _term_hit_rate(context_text, payload.expected_terms),
        }
        stages["llm"] = {
            "status": "ok",
            "model": "configured-in-lightrag",
            "answer": answer,
            "latency_ms": latency_ms,
        }
        raw_log["lightrag_response"] = raw_response
    except LightRAGError as exc:
        stages["retrieval"] = {
            "status": "error",
            "mode": "mix",
            "sources": [],
            "source_hit": False,
            "term_hit_rate": 0.0,
            "error": str(exc),
        }
        stages["context"] = {"status": "error", "char_count": 0, "text": "", "term_hit_rate": 0.0, "error": str(exc)}
        stages.setdefault(
            "prompt",
            {"status": "error", "mode": "mix", "char_count": 0, "text": "", "latency_ms": None, "error": str(exc)},
        )
        stages["llm"] = {"status": "error", "model": "configured-in-lightrag", "answer": "", "latency_ms": None, "error": str(exc)}
        raw_log["lightrag_error"] = str(exc)

    diagnosis = _diagnose(stages, payload.expected_terms, payload.expected_source_paths)
    return {
        "correlation_id": correlation_id,
        "query": payload.query,
        "diagnosis": diagnosis.model_dump(),
        "stages": stages,
        "raw_log": {
            **raw_log,
            "request": payload.model_dump(),
            "correlation_id": correlation_id,
        },
    }
