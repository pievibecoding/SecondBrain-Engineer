import httpx
import uuid
from nas_connector.logger import logger


class Uploader:
    def __init__(self, backend_url: str):
        self._url = backend_url

    async def get_hash(self, nas_path: str) -> str | None:
        cid = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._url}/api/internal/nas/hash", params={"path": nas_path}, headers={"X-Correlation-ID": cid})
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json().get("hash")
        except httpx.ConnectError:
            logger.warning("Backend unreachable for hash lookup", nas_path=nas_path)
            return None
        except Exception as e:
            logger.error("Error in get_hash", nas_path=nas_path, error=str(e))
            return None

    async def get_known_paths(self) -> list[str]:
        cid = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._url}/api/internal/nas/paths", headers={"X-Correlation-ID": cid})
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                return resp.json().get("paths", [])
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Backend unreachable for known paths lookup", correlation_id=cid, error=str(e))
            return []
        except Exception as e:
            logger.error("Error in get_known_paths", correlation_id=cid, error=str(e))
            return []

    async def _report(self, payload: dict) -> None:
        cid = str(uuid.uuid4())
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{self._url}/api/internal/nas/report", json=payload, headers={"X-Correlation-ID": cid})
                if resp.status_code >= 400:
                    logger.error("Backend report failed", status=resp.status_code, nas_path=payload.get("nas_path"), correlation_id=cid)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning("Backend unreachable for report", nas_path=payload.get("nas_path"), correlation_id=cid, error=str(e))

    async def report_new(self, nas_path: str, file_hash: str, extension: str, ingest_content: bool) -> None:
        await self._report({
            "event": "new",
            "nas_path": nas_path,
            "file_hash": file_hash,
            "extension": extension,
            "ingest_content": ingest_content,
        })

    async def report_changed(self, nas_path: str, new_hash: str) -> None:
        await self._report({
            "event": "changed",
            "nas_path": nas_path,
            "file_hash": new_hash,
        })

    async def report_deleted(self, nas_path: str) -> None:
        await self._report({
            "event": "deleted",
            "nas_path": nas_path,
        })
