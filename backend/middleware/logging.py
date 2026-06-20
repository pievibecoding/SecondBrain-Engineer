from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from backend.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/health"):
            return await call_next(request)
        start = time.perf_counter()
        cid = getattr(request.state, "correlation_id", "")
        logger.info("request", method=request.method, path=request.url.path, correlation_id=cid)
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("response", status_code=response.status_code, elapsed_ms=int(elapsed_ms), correlation_id=cid)
            return response
        except Exception as e:
            logger.error("unhandled_exception", error=str(e), correlation_id=cid)
            raise
