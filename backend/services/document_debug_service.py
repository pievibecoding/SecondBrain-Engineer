from __future__ import annotations

import re
from difflib import SequenceMatcher, unified_diff
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logger import logger
from backend.models.nas_file import NasFile
from backend.services.document_parser import parse_document_async


def _normalize_for_compare(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _first_diff_index(left: str, right: str) -> int | None:
    limit = min(len(left), len(right))
    for idx in range(limit):
        if left[idx] != right[idx]:
            return idx
    if len(left) == len(right):
        return None
    return limit


def _window(value: str, index: int | None, radius: int = 180) -> str:
    if not value:
        return ""
    if index is None:
        return value[: radius * 2]
    start = max(0, index - radius)
    end = min(len(value), index + radius)
    return value[start:end]


async def build_document_compare_report(
    db: AsyncSession,
    nas_file: NasFile,
    correlation_id: str,
) -> dict:
    parse_result = await parse_document_async(nas_file.nas_path, correlation_id=correlation_id)
    parsed_text = parse_result.text if parse_result else ""

    chunk_rows = []
    chunk_text = ""
    chunk_error: str | None = None
    if nas_file.lightrag_doc_id:
        try:
            result = await db.execute(
                sql_text(
                    """
                    SELECT chunk_order_index, tokens, content
                    FROM lightrag_doc_chunks
                    WHERE full_doc_id = :doc_id
                    ORDER BY chunk_order_index
                    """
                ),
                {"doc_id": nas_file.lightrag_doc_id},
            )
            chunk_rows = list(result.mappings().all())
            chunk_text = "\n\n".join(str(row["content"] or "") for row in chunk_rows)
        except Exception as exc:
            chunk_error = str(exc)

    parsed_norm = _normalize_for_compare(parsed_text)
    chunk_norm = _normalize_for_compare(chunk_text)
    diff_index = _first_diff_index(parsed_norm, chunk_norm)
    diff = "\n".join(
        unified_diff(
            parsed_text.splitlines(),
            chunk_text.splitlines(),
            fromfile="parsed_text",
            tofile="chunk_text",
            lineterm="",
        )
    )

    report = {
        "file_id": str(nas_file.id),
        "nas_path": nas_file.nas_path,
        "status": nas_file.status,
        "folder_type": nas_file.folder_type,
        "lightrag_doc_id": nas_file.lightrag_doc_id,
        "parsed": {
            "success": bool(parse_result and parse_result.success),
            "parser_used": parse_result.parser_used if parse_result else None,
            "char_count": len(parsed_text),
            "line_count": len(parsed_text.splitlines()),
            "text": parsed_text,
        },
        "chunks": {
            "count": len(chunk_rows),
            "char_count": len(chunk_text),
            "line_count": len(chunk_text.splitlines()),
            "text": chunk_text,
            "items": [
                {
                    "chunk_order_index": row["chunk_order_index"],
                    "tokens": row["tokens"],
                    "content": row["content"],
                }
                for row in chunk_rows
            ],
            "error": chunk_error,
        },
        "compare": {
            "similarity_ratio": round(SequenceMatcher(None, parsed_norm, chunk_norm).ratio(), 6) if parsed_norm or chunk_norm else 1.0,
            "first_diff_index": diff_index,
            "parsed_window": _window(parsed_norm, diff_index),
            "chunk_window": _window(chunk_norm, diff_index),
            "diff_preview": diff,
        },
    }

    logger.info(
        "document_compare_generated",
        nas_file_id=str(nas_file.id),
        nas_path=nas_file.nas_path,
        lightrag_doc_id=nas_file.lightrag_doc_id,
        parsed_chars=len(parsed_text),
        chunk_chars=len(chunk_text),
        chunk_count=len(chunk_rows),
        similarity_ratio=report["compare"]["similarity_ratio"],
        correlation_id=correlation_id,
    )
    return report
