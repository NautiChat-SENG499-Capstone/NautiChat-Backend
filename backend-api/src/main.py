from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.admin.router import router as admin_router
from src.auth import models  # noqa
from src.auth.router import router as auth_router
from src.database import Base, engine, init_redis
from src.llm import models  # noqa
from src.llm.router import router as llm_router
from src.middleware import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_client = init_redis()
    yield

    await app.state.redis_client.aclose()


def create_app():
    app = FastAPI(lifespan=lifespan)

    # TO DO: add frontend url to origins
    origins = ["http://localhost:3000"]

    # Middleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add routers
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    return app


app = create_app()

# Database set-up
Base.metadata.create_all(bind=engine)
