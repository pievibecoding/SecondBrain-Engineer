import httpx

from backend.integrations.lightrag.errors import LightRAGError, LightRAGTimeoutError
from backend.logger import logger


class LightRAGIngestClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def ingest_document(self, file_path: str, metadata: dict, correlation_id: str) -> dict:
        """Legacy path — gửi file_path để LightRAG tự parse (native parser)."""
        operation = "ingest_document"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/docs",
                    json={"file_path": file_path, "metadata": metadata},
                    headers={"X-Correlation-ID": correlation_id, "Content-Type": "application/json"},
                )
        except httpx.TimeoutException as exc:
            logger.error("lightrag_timeout", operation=operation, correlation_id=correlation_id)
            raise LightRAGTimeoutError("request timed out", operation=operation) from exc
        except httpx.RequestError as exc:
            logger.error("lightrag_request_error", operation=operation, error=str(exc), correlation_id=correlation_id)
            raise LightRAGError("request failed", operation=operation, response_text=str(exc)) from exc

        if not response.is_success:
            text = response.text
            logger.error(
                "lightrag_http_error",
                operation=operation,
                status_code=response.status_code,
                correlation_id=correlation_id,
            )
            raise LightRAGError("non-2xx response", operation=operation, status_code=response.status_code, response_text=text)

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise LightRAGError("invalid JSON response", operation=operation, response_text=response.text) from exc

    async def ingest_text(self, text: str, file_source: str, metadata: dict, correlation_id: str) -> dict:
        """
        Pre-processed path — gửi text đã parse sẵn qua POST /documents/text.
        Bypass native parser của LightRAG, tránh mất text với DOCX/PDF phức tạp.
        """
        operation = "ingest_text"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/documents/text",
                    json={
                        "text": text,
                        "file_source": file_source,
                        "metadata": metadata,
                    },
                    headers={"X-Correlation-ID": correlation_id, "Content-Type": "application/json"},
                )
        except httpx.TimeoutException as exc:
            logger.error("lightrag_timeout", operation=operation, correlation_id=correlation_id)
            raise LightRAGTimeoutError("request timed out", operation=operation) from exc
        except httpx.RequestError as exc:
            logger.error("lightrag_request_error", operation=operation, error=str(exc), correlation_id=correlation_id)
            raise LightRAGError("request failed", operation=operation, response_text=str(exc)) from exc

        if not response.is_success:
            text_resp = response.text
            logger.error(
                "lightrag_http_error",
                operation=operation,
                status_code=response.status_code,
                correlation_id=correlation_id,
            )
            raise LightRAGError("non-2xx response", operation=operation, status_code=response.status_code, response_text=text_resp)

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise LightRAGError("invalid JSON response", operation=operation, response_text=response.text) from exc

    async def delete_document(self, doc_id: str, correlation_id: str) -> dict:
        operation = "delete_document"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/docs/{doc_id}",
                    headers={"X-Correlation-ID": correlation_id},
                )
        except httpx.TimeoutException as exc:
            logger.error("lightrag_timeout", operation=operation, correlation_id=correlation_id)
            raise LightRAGTimeoutError("request timed out", operation=operation) from exc
        except httpx.RequestError as exc:
            logger.error("lightrag_request_error", operation=operation, error=str(exc), correlation_id=correlation_id)
            raise LightRAGError("request failed", operation=operation, response_text=str(exc)) from exc

        if not response.is_success:
            text = response.text
            logger.error(
                "lightrag_http_error",
                operation=operation,
                status_code=response.status_code,
                correlation_id=correlation_id,
            )
            raise LightRAGError("non-2xx response", operation=operation, status_code=response.status_code, response_text=text)

        if not response.content:
            return {"status": "deleted"}
        try:
            return response.json()
        except ValueError:
            return {"status": "deleted"}
