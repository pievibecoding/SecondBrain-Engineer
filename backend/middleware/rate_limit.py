from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import time
import redis.asyncio as aioredis
from backend.config import settings
from backend.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str = settings.REDIS_URL):
        super().__init__(app)
        try:
            self.redis = aioredis.from_url(redis_url)
        except Exception:
            self.redis = None

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        token = request.headers.get("Authorization", "anonymous")
        key = f"rate_limit:mcp:{token}"
        now = int(time.time() * 1000)
        window_start = now - 60_000
        limit = settings.MCP_RATE_LIMIT_PER_MINUTE

        if not self.redis:
            logger.warning("Redis unavailable for rate limiting, allowing request", path=request.url.path)
            return await call_next(request)

        try:
            async with self.redis.pipeline() as pipe:
                await pipe.zremrangebyscore(key, 0, window_start)
                count = await pipe.zcard(key)
                await pipe.zadd(key, {str(now): now})
                await pipe.expire(key, 61)
                # The above pipeline usage may vary by redis lib; simplified for clarity
            if count >= limit:
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int((oldest[0][1] + 60_000 - now) / 1000) + 1
                else:
                    retry_after = 60
                return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded. Try again in {retry_after} seconds."})
        except Exception as e:
            logger.warning("Redis error in rate limiting, allowing request", error=str(e))

        return await call_next(request)
