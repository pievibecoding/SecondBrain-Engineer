from __future__ import annotations

import re
from typing import Any


def _chunk(strategy: str, index: int, text: str, source_path: str, section_hint: str | None = None) -> dict[str, Any]:
    return {
        "strategy": strategy,
        "chunk_index": index,
        "text": text.strip(),
        "char_count": len(text.strip()),
        "metadata": {"source_path": source_path, "section_hint": section_hint},
    }


def fixed_chars(text: str, source_path: str, target_chars: int = 2200, overlap_chars: int = 220) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    step = max(target_chars - overlap_chars, 1)
    for index, start in enumerate(range(0, len(text), step)):
        part = text[start:start + target_chars]
        if part.strip():
            chunks.append(_chunk("fixed_chars", index, part, source_path))
    return chunks


def paragraph_merge(text: str, source_path: str, target_chars: int = 2200, max_chars: int = 4200) -> list[dict[str, Any]]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        next_len = current_len + len(paragraph) + 2
        if current and next_len > target_chars:
            chunks.append(_chunk("paragraph_merge", len(chunks), "\n\n".join(current), source_path))
            current = []
            current_len = 0
        if len(paragraph) > max_chars:
            for fixed in fixed_chars(paragraph, source_path, target_chars=target_chars, overlap_chars=0):
                fixed["strategy"] = "paragraph_merge"
                fixed["chunk_index"] = len(chunks)
                chunks.append(fixed)
            continue
        current.append(paragraph)
        current_len += len(paragraph) + 2

    if current:
        chunks.append(_chunk("paragraph_merge", len(chunks), "\n\n".join(current), source_path))
    return chunks


def heading_table_aware(text: str, source_path: str, target_chars: int = 2200, max_chars: int = 4200) -> list[dict[str, Any]]:
    lines = text.splitlines()
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append("\n".join(current).strip())
            current = []

    for line in lines:
        stripped = line.strip()
        is_heading = bool(stripped) and len(stripped) < 90 and (
            stripped.isupper()
            or re.match(r"^(\d+\.|[A-Z][A-Za-z0-9 -]+ Series\b)", stripped)
            or stripped.endswith("Series")
        )
        is_table = "|" in stripped or stripped.startswith("[Bảng")
        if is_heading and current and len("\n".join(current)) > target_chars * 0.35:
            flush()
        current.append(line)
        if not is_table and len("\n".join(current)) >= target_chars:
            flush()
        if len("\n".join(current)) >= max_chars:
            flush()
    flush()

    chunks: list[dict[str, Any]] = []
    for block in blocks:
        if len(block) <= max_chars:
            hint = next((line.strip() for line in block.splitlines() if line.strip()), None)
            chunks.append(_chunk("heading_table_aware", len(chunks), block, source_path, hint))
        else:
            for item in paragraph_merge(block, source_path, target_chars=target_chars, max_chars=max_chars):
                item["strategy"] = "heading_table_aware"
                item["chunk_index"] = len(chunks)
                chunks.append(item)
    return chunks


def run_strategies(text: str, source_path: str, config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    target = int(config.get("target_chars", 2200))
    overlap = int(config.get("overlap_chars", 220))
    max_chars = int(config.get("max_chars", 4200))
    return {
        "fixed_chars": fixed_chars(text, source_path, target, overlap),
        "paragraph_merge": paragraph_merge(text, source_path, target, max_chars),
        "heading_table_aware": heading_table_aware(text, source_path, target, max_chars),
    }

