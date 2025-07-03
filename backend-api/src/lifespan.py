import asyncio
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI

from LLM.core import LLM
from LLM.Environment import Environment

# Need to import the models in the same module that Base is defined to ensure they are registered with SQLAlchemy
from src.auth import models  # noqa
from src.database import DatabaseSessionManager, init_redis
from src.llm import models  # noqa
from src.settings import get_settings  # Settings management for environment variables

logger = logging.getLogger("nautichat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage async app startup/shutdown events"""
    logger.info("Starting up application...")

    # Connect to Supabase Postgres as async engine
    try:
        async with asyncio.timeout(20):
            # Setup up database session manager
            logger.info("Initializing Session Manager...")
            session_manager = DatabaseSessionManager(get_settings().SUPABASE_DB_URL)
            app.state.session_manager = session_manager
            logger.info("Database session manager initialized")
        async with asyncio.timeout(20):
            # Initialize Redis client
            logger.info("Initializing Redis client...")
            app.state.redis_client = await init_redis()
            logger.info("Redis client initialized successfully.")

        logger.info("Creating Environment instance...")
        app.state.env = Environment()
        logger.info("Environment instance created successfully.")

        logger.info("Initializing LLM (this may take a while)...")
        try:
            app.state.llm = LLM(app.state.env)
            logger.info("LLM instance initialized successfully.")
        except Exception as e:
            logger.error(f"LLM initialization failed: {e}")
            raise RuntimeError(f"LLM initialization failed: {e}")

        logger.info("Getting RAG instance...")
        app.state.rag = app.state.llm.RAG_instance
        logger.info("RAG instance initialized successfully.")

    except Exception as e:
        logger.error(f"Startup failed with error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise RuntimeError(f"Startup failed: {e}")

    logger.info("Running sanity checks...")
    if not app.state.redis_client:
        logger.error("Redis client initialization failed")
        raise RuntimeError("Failed to connect to Redis.")
    if not app.state.llm:
        logger.error("LLM initialization failed")
        raise RuntimeError("Failed to initialize LLM.")
    if not app.state.rag:
        logger.error("RAG initialization failed")
        raise RuntimeError("Failed to initialize RAG.")

    logger.info("App startup complete. All systems go!")
    yield

    # Teardown
    logger.info("Shutting down application...")
    if hasattr(app.state, "session_manager"):
        await app.state.session_manager.close()
    if hasattr(app.state, "redis_client"):
        await app.state.redis_client.aclose()
    logger.info("Resources cleaned up.")
