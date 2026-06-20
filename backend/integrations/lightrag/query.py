from collections.abc import AsyncIterator
from typing import Any

import httpx

from backend.integrations.lightrag.errors import LightRAGError, LightRAGTimeoutError
from backend.logger import logger


class LightRAGQueryClient:
    def __init__(self, base_url: str, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def query(
        self,
        query_text: str,
        correlation_id: str,
        mode: str = "mix",
        include_references: bool | None = None,
        include_chunk_content: bool | None = None,
        only_need_prompt: bool | None = None,
        only_need_context: bool | None = None,
    ) -> dict:
        operation = "query"
        body: dict[str, Any] = {"query": query_text, "mode": mode}
        if include_references is not None:
            body["include_references"] = include_references
        if include_chunk_content is not None:
            body["include_chunk_content"] = include_chunk_content
        if only_need_prompt is not None:
            body["only_need_prompt"] = only_need_prompt
        if only_need_context is not None:
            body["only_need_context"] = only_need_context
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/query",
                    json=body,
                    headers={"X-Correlation-ID": correlation_id, "Content-Type": "application/json"},
                )
        except httpx.TimeoutException as exc:
            logger.error("lightrag_timeout", operation=operation, correlation_id=correlation_id)
            raise LightRAGTimeoutError("request timed out", operation=operation) from exc
        except httpx.RequestError as exc:
            logger.error("lightrag_request_error", operation=operation, error=str(exc), correlation_id=correlation_id)
            raise LightRAGError("request failed", operation=operation, response_text=str(exc)) from exc

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

    async def query_stream(self, query_text: str, correlation_id: str, mode: str = "mix") -> AsyncIterator[str]:
        operation = "query_stream"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/query/stream",
                    json={"query": query_text, "mode": mode},
                    headers={"X-Correlation-ID": correlation_id, "Content-Type": "application/json"},
                ) as response:
                    if not response.is_success:
                        text = await response.aread()
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
                            response_text=text.decode(errors="replace"),
                        )
                    async for chunk in response.aiter_text():
                        yield chunk
        except httpx.TimeoutException as exc:
            logger.error("lightrag_timeout", operation=operation, correlation_id=correlation_id)
            raise LightRAGTimeoutError("request timed out", operation=operation) from exc
        except httpx.RequestError as exc:
            logger.error("lightrag_request_error", operation=operation, error=str(exc), correlation_id=correlation_id)
            raise LightRAGError("request failed", operation=operation, response_text=str(exc)) from exc
