import anyio
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger import logger
from src.settings import get_settings

TIMEOUT_SECONDS = 30


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle request timeouts.
    If a request takes longer than the specified timeout, it returns a 504 Gateway Timeout response.
    """

    def __init__(self, app):
        super().__init__(app)
        self.timeout_seconds = TIMEOUT_SECONDS

    async def dispatch(self, request: Request, call_next):
        response = None
        with anyio.move_on_after(self.timeout_seconds) as scope:
            response = await call_next(request)

        if scope.cancel_called or response is None:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out"},
            )

        return response


# Gloabal limiter class
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://default:{get_settings().REDIS_PASSWORD}@redis-13649.crce199.us-west-2-2.ec2.redns.redis-cloud.com:13649",
    default_limits=["80/minute"],
)


def init_middleware(app):
    """
    Initializes the middleware for the FastAPI application.
    This function is called during application startup.
    """

    origins = ["http://localhost:3000", "https://nautichat.vercel.app"]

    # Add CORS middleware  to enable frontend-backend communications
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware added.")

    # Add slowapi rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

    app.add_middleware(TimeoutMiddleware)

    logger.info("Middleware initialized successfully.")
