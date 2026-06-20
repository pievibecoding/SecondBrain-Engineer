"""
Extractor service — composes Robolinks domain prompt, calls LLM, validates output.
In MVP (no LLM available) returns empty extraction. Swap in real client when ready.
"""
from __future__ import annotations

import json
import re
from typing import Any

from logger import logger

# ── Allowed entity / relation types from pa3-design Section 14 ───────────────

VALID_ENTITY_TYPES = {
    "PROJECT", "CLIENT", "EQUIPMENT", "COMPONENT", "SUPPLIER",
    "PERSON", "PROCESS", "ERROR_CODE", "DOCUMENT", "LOCATION", "STANDARD",
}

VALID_RELATION_TYPES = {
    "USES", "BELONGS_TO", "MANAGED_BY", "CLIENT_OF", "SUPPLIED_BY",
    "PART_OF", "DOCUMENTS", "LOCATED_AT", "RELATED_TO",
}

# ── System prompt (Vietnamese, Robolinks domain) ─────────────────────────────

SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích hội thoại kỹ thuật của công ty tự động hóa Robolinks.
Nhiệm vụ: trích xuất entity và relation từ đoạn hội thoại dưới đây.

Entity types: PROJECT, CLIENT, EQUIPMENT, COMPONENT, SUPPLIER, PERSON, PROCESS,
              ERROR_CODE, DOCUMENT, LOCATION, STANDARD

Chỉ extract entity rõ ràng được đề cập, không suy diễn.

Output JSON duy nhất (không có text khác):
{
  "entities": [{"name": "...", "type": "...", "description": "..."}],
  "relations": [{"src": "...", "rel_type": "...", "tgt": "...", "description": "..."}]
}
""".strip()


def _format_turns(turns: list[dict[str, Any]]) -> str:
    return "\n".join(f"[{t.get('role','?').upper()}]: {t.get('content','')}" for t in turns)


def _parse_llm_output(raw: str) -> dict:
    """Extract JSON from LLM output; tolerate markdown code fences."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output")
    return json.loads(match.group())


def _validate_and_normalise(data: dict) -> tuple[list[dict], list[dict]]:
    """Validate types, deduplicate by name (case-insensitive), return (entities, relations)."""
    entities = []
    seen_names: set[str] = set()
    for e in data.get("entities") or []:
        name = (e.get("name") or "").strip()
        etype = (e.get("type") or "").upper()
        if not name or etype not in VALID_ENTITY_TYPES:
            continue
        key = name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        entities.append({"name": name, "type": etype, "description": e.get("description")})

    relations = []
    for r in data.get("relations") or []:
        rel_type = (r.get("rel_type") or "").upper()
        if rel_type not in VALID_RELATION_TYPES:
            rel_type = "RELATED_TO"  # default fallback
        relations.append({
            "src": (r.get("src") or "").strip(),
            "rel_type": rel_type,
            "tgt": (r.get("tgt") or "").strip(),
            "description": r.get("description"),
        })

    return entities, relations


async def _call_llm(prompt: str, correlation_id: str | None) -> str:
    """
    Placeholder LLM call. Replace with real implementation:
    - Phase 1: Gemini Flash Lite API
    - Phase 2: Ollama qwen2.5:14b

    Raises RuntimeError when no LLM is configured (MVP fallback).
    """
    raise RuntimeError("LLM not configured — set LLM_BINDING in environment")


async def extract_entities(
    turns: list[dict[str, Any]],
    correlation_id: str | None = None,
) -> dict:
    """
    Extract entities/relations from conversation turns.

    Returns:
        {"entities_added": int, "relations_added": int,
         "entities": [...], "relations": [...]}

    Never raises — logs errors and returns zeros on failure.
    """
    if not turns:
        return {"entities_added": 0, "relations_added": 0, "entities": [], "relations": []}

    conversation_text = _format_turns(turns)
    full_prompt = f"{SYSTEM_PROMPT}\n\nHội thoại:\n{conversation_text}"

    try:
        raw_output = await _call_llm(full_prompt, correlation_id)
        data = _parse_llm_output(raw_output)
        entities, relations = _validate_and_normalise(data)
        logger.info(
            "extraction_done",
            entities_added=len(entities),
            relations_added=len(relations),
            correlation_id=correlation_id,
        )
        return {
            "entities_added": len(entities),
            "relations_added": len(relations),
            "entities": entities,
            "relations": relations,
        }
    except RuntimeError:
        # LLM not configured — expected in MVP
        logger.info("extraction_skipped_no_llm", correlation_id=correlation_id)
        return {"entities_added": 0, "relations_added": 0, "entities": [], "relations": []}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("extraction_parse_error", error=str(e), correlation_id=correlation_id)
        return {"entities_added": 0, "relations_added": 0, "entities": [], "relations": []}
    except Exception as e:
        logger.error("extraction_unexpected_error", error=str(e), correlation_id=correlation_id)
        return {"entities_added": 0, "relations_added": 0, "entities": [], "relations": []}
