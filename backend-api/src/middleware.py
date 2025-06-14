from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, window_sec: int = 30, max_requests: int = 10):
        super().__init__(app)
        self.window_sec = window_sec
        self.max_requests = max_requests

    async def permit_request(self, redis: Redis, key: str):
        if await redis.setnx(key, self.max_requests):
            await redis.expire(key, self.window_sec)
        cache_val: Optional[bytes] = await redis.get(key)

        if cache_val is not None:
            requests_remaining = int(cache_val)
            if requests_remaining > 0:
                await redis.decr(key)
                return True

        return False

    async def dispatch(self, request: Request, call_next):
        if not request.client:
            raise ValueError("Client IP not found")

        client_ip = request.client.host
        redis: Redis = request.app.state.redis_client
        key = f"{client_ip}:RATELIMIT"

        if not await self.permit_request(redis, key):
            time_to_wait = await redis.ttl(key)
            retry_info = f" Retry after {int(time_to_wait)}" if time_to_wait is not None else ""
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": f"Rate limit exceeded.{retry_info}"}
            )

        response = await call_next(request)
        return response
