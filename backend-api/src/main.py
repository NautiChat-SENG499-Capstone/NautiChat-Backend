from contextlib import asynccontextmanager # Used to manage async app startup/shutdown events

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Enables frontend-backend communications via CORS

from src.database import sessionmanager, Base, init_redis

from src.auth import models  # noqa
from src.llm import models  # noqa
from LLM.LLM import LLM
from LLM.Environment import Environment  # Importing Environment to initialize LLM

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router
from src.middleware import RateLimitMiddleware # Custom middleware for rate limiting
from starlette.concurrency import run_in_threadpool

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("nautichat")
logger.info("Logging initialized at INFO level.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")

    try:
        logger.info("Initializing database session manager...")
        async with sessionmanager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.state.db_session_factory = sessionmanager.session
        logger.info("Database tables created and session factory registered.")

        logger.info("Database session manager initialized.")

        app.state.redis_client = await init_redis()
        logger.info("Redis client initialized.")
        env = Environment()
        llm = await run_in_threadpool(LLM, env)

        app.state.llm = llm
        logger.info("LLM instance initialized.")
        app.state.rag = app.state.llm.RAG_instance

        logger.info("RAG instance initialized.")
    except Exception as e:
        logger.exception("Error during application startup.")
        raise RuntimeError(f"Startup failed: {e}")

    # Sanity checks
    if not app.state.redis_client:
        raise RuntimeError("Failed to connect to Redis.")
    if not app.state.llm or not app.state.rag:
        raise RuntimeError("Failed to initialize LLM or RAG.")

    logger.info("App startup complete. All systems go.")
    yield

    # Teardown
    logger.info("Shutting down application...")
    await sessionmanager.close()
    await app.state.redis_client.aclose()
    logger.info("Resources cleaned up.")

def create_app():
    logger.info("Creating FastAPI app...")
    app = FastAPI(lifespan=lifespan)

    # TODO: add frontend url to origins
    origins = ["http://localhost:3000"]

    # Add CORS and Rate Limit Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    logger.info("CORS and Rate Limit Middleware added.")

    # Register Routes from modules (auth, llm, admin)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    logger.info("Routers registered.")

    return app

app = create_app()

