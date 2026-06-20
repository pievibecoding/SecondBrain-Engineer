"""
push_knowledge — INTERNAL ONLY tool.

This file is intentionally placed in tools/internal/ and must NOT be
imported from backend/mcp/tools/. The internal boundary is enforced by
package structure.
"""
from backend.logger import logger, get_correlation_id
from backend.schemas.mcp import PushKnowledgeInput, PushKnowledgeOutput


async def push_knowledge(
    entity_name: str,
    entity_type: str,
    description: str,
    relations: list,
    source: str,
    token_type: str = "user",  # caller must pass "internal" for this to succeed
) -> dict:
    """[Internal only] Push entity/relation mới vào knowledge graph."""
    cid = get_correlation_id()

    # validate input BEFORE any token or graph check
    try:
        inp = PushKnowledgeInput(
            entity_name=entity_name,
            entity_type=entity_type,
            description=description,
            relations=relations,
            source=source,
        )
    except Exception as e:
        return {"error": f"[Validation] {e}", "ok": False}

    # token type check MUST happen before any graph write
    if token_type != "internal":
        logger.warning(
            "mcp_push_knowledge_unauthorized",
            tool_name="push_knowledge",
            correlation_id=cid,
            token_type=token_type,
        )
        return {"error": "push_knowledge requires internal service token", "ok": False, "status_code": 403}

    logger.info("mcp_tool_start", tool_name="push_knowledge", correlation_id=cid)

    # TODO: implement actual LightRAG upsert when LightRAG exposes a write entity API.
    # For MVP, this is a stub that confirms receipt and returns success shape.
    relations_added = len(inp.relations)
    output = PushKnowledgeOutput(ok=True, entity_name=inp.entity_name, relations_added=relations_added)
    logger.info(
        "mcp_tool_done",
        tool_name="push_knowledge",
        correlation_id=cid,
        entity_name=inp.entity_name,
        relations_added=relations_added,
    )
    return output.model_dump()
