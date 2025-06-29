import asyncio
import logging
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from LLM.core import LLM
from LLM.Environment import Environment
from src.admin.router import router as admin_router

# Need to import the models in the same module that Base is defined to ensure they are registered with SQLAlchemy
from src.auth import models  # noqa
from src.auth.router import router as auth_router
from src.database import DatabaseSessionManager, init_redis
from src.llm import models  # noqa
from src.llm.router import router as llm_router
from src.settings import get_settings  # Settings management for environment variables

# Configure logging to work with uvicorn
logger = logging.getLogger("nautichat")
logger.setLevel(logging.DEBUG)

# Create console handler if it doesn't exist
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.info("NAUTICHAT BACKEND STARTING")


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


def create_app():
    logger.info("Creating FastAPI app...")
    app = FastAPI(
        title="NautiChat Backend API",
        description="Backend API for NautiChat application",
        version="1.0.0",
        lifespan=lifespan,
    )

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

    # Add a root endpoint for testing
    @app.get("/")
    async def root():
        logger.info("Root endpoint accessed")
        return {
            "message": "NautiChat Backend API is running!",
            "docs": "/docs",
            "health": "/health",
            "status": "ready",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        logger.info("Health check endpoint accessed")
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "llm": "initialized",
        }

    # Register Routes from modules (auth, llm, admin)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    logger.info("Routers registered.")

    return app


app = create_app()
