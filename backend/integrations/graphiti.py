import httpx
from backend.logger import logger
from backend.config import settings


async def extract(conversation_id: str, turns: list[dict], correlation_id: str | None = None) -> dict:
    """Call Graphiti service POST /extract and return parsed result.

    Returns {'ok': True} on success or {'ok': False, 'error': '...'} on failure.
    """
    url = settings.GRAPHITI_URL.rstrip("/") + "/extract"
    headers = {"Content-Type": "application/json"}
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id

    from datetime import datetime, timezone
    payload = {
        "conversation_id": conversation_id,
        "turns": turns,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        logger.error("graphiti_timeout", conversation_id=conversation_id, correlation_id=correlation_id)
        return {"ok": False, "error": "timeout"}
    except httpx.RequestError as exc:
        logger.error("graphiti_request_error", error=str(exc), conversation_id=conversation_id, correlation_id=correlation_id)
        return {"ok": False, "error": "request_error"}

    if not resp.is_success:
        logger.error("graphiti_http_error", status_code=resp.status_code, conversation_id=conversation_id, correlation_id=correlation_id)
        return {"ok": False, "error": f"status_{resp.status_code}", "status_code": resp.status_code}

    try:
        return resp.json()
    except ValueError:
        logger.error("graphiti_invalid_json", conversation_id=conversation_id, correlation_id=correlation_id)
        return {"ok": False, "error": "invalid_json"}
