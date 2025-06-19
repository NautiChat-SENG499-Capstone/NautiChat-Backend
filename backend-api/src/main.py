from contextlib import asynccontextmanager # Used to manage async app startup/shutdown events

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Enables frontend-backend communications via CORS

from src.database import DatabaseSessionManager, Base, init_redis

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
import sys
import traceback
import asyncio

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
    logger.info("Starting up application...")

    try:
        logger.info("Initializing database session manager...")
        from src.settings import get_settings
        
        # Create session manager in lifespan instead of globally
        session_manager = DatabaseSessionManager(get_settings().SUPABASE_DB_URL)
        app.state.session_manager = session_manager
        assert session_manager._engine is not None, "Session manager engine is not initialized"
        
        # Test database connection with timeout
        async with asyncio.timeout(30):  # 30 second timeout for DB init
            async with session_manager.connect() as conn:
                logger.info("Creating database tables...")
                await conn.run_sync(Base.metadata.create_all)
        
        app.state.db_session_factory = session_manager.session
        logger.info("Database tables created and session factory registered.")

        logger.info("Initializing Redis client...")
        async with asyncio.timeout(10):  # 10 second timeout for Redis
            app.state.redis_client = await init_redis()
        logger.info("Redis client initialized successfully.")

        logger.info("Creating Environment instance...")
        app.state.env = Environment()
        logger.info("Environment instance created successfully.")

        logger.info("Initializing LLM (this may take a while)...")
        try:
            # Add timeout to prevent infinite hanging
            llm = await asyncio.wait_for(
                run_in_threadpool(LLM, app.state.env), 
                timeout=300  # 5 minute timeout
            )
            app.state.llm = llm
            logger.info("LLM instance initialized successfully.")
        except asyncio.TimeoutError:
            logger.error("LLM initialization timed out after 5 minutes")
            raise RuntimeError("LLM initialization timed out")
        except Exception as e:
            logger.error(f"LLM initialization failed: {e}")
            raise RuntimeError(f"LLM initialization failed: {e}")

        logger.info("Step 5: Getting RAG instance...")
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
    if hasattr(app.state, 'session_manager'):
        await app.state.session_manager.close()
    if hasattr(app.state, 'redis_client'):
        await app.state.redis_client.aclose()
    logger.info("Resources cleaned up.")

def create_app():
    logger.info("Creating FastAPI app...")
    app = FastAPI(
        title="NautiChat Backend API",
        description="Backend API for NautiChat application",
        version="1.0.0",
        lifespan=lifespan
    )

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

    # Add a root endpoint for testing
    @app.get("/")
    async def root():
        logger.info("Root endpoint accessed")
        return {
            "message": "NautiChat Backend API is running!", 
            "docs": "/docs",
            "health": "/health",
            "status": "ready"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        logger.info("Health check endpoint accessed")
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "llm": "initialized"
        }

    # Register Routes from modules (auth, llm, admin)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    logger.info("Routers registered.")

    return app

app = create_app()

