import httpx

from backend.integrations.lightrag.errors import LightRAGError, LightRAGNotFoundError, LightRAGTimeoutError
from backend.logger import logger


class LightRAGGraphClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_entity(self, entity_name: str, correlation_id: str) -> dict:
        response = await self._get(
            f"{self.base_url}/api/v1/graph/entity/{entity_name}",
            operation="get_entity",
            correlation_id=correlation_id,
        )
        return response

    async def get_edges(self, entity_name: str, correlation_id: str) -> list[dict]:
        response = await self._get(
            f"{self.base_url}/api/v1/graph/edges",
            operation="get_edges",
            correlation_id=correlation_id,
            params={"entity": entity_name},
        )
        return response if isinstance(response, list) else response.get("edges", [])

    async def _get(
        self,
        url: str,
        operation: str,
        correlation_id: str,
        params: dict | None = None,
    ) -> dict | list[dict]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers={"X-Correlation-ID": correlation_id})
        except httpx.TimeoutException as exc:
            logger.error("lightrag_timeout", operation=operation, correlation_id=correlation_id)
            raise LightRAGTimeoutError("request timed out", operation=operation) from exc
        except httpx.RequestError as exc:
            logger.error("lightrag_request_error", operation=operation, error=str(exc), correlation_id=correlation_id)
            raise LightRAGError("request failed", operation=operation, response_text=str(exc)) from exc

        if response.status_code == 404:
            raise LightRAGNotFoundError("entity not found", operation=operation, status_code=404, response_text=response.text)
        if not response.is_success:
            logger.error(
                "lightrag_http_error",
                operation=operation,
                status_code=response.status_code,
                correlation_id=correlation_id,
            )
            raise LightRAGError(
                "non-2xx response",
                operation=operation,
                status_code=response.status_code,
                response_text=response.text,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise LightRAGError("invalid JSON response", operation=operation, response_text=response.text) from exc
