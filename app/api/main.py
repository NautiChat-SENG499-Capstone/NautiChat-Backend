from fastapi import FastAPI
from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.chat.router import router as llm_router
from src.lifespan import lifespan
from src.logger import logger
from src.middleware import init_middleware

logger.info("NAUTICHAT BACKEND STARTING")


def create_app():
    logger.info("Creating FastAPI app...")
    app = FastAPI(
        title="NautiChat Backend API",
        description="Backend API for NautiChat application",
        version="1.0.0",
        lifespan=lifespan,
    )

    init_middleware(app)

    # Add a root endpoint for testing
    @app.get("/")
    async def root():
        return {
            "message": "NautiChat Backend API is running!",
            "docs": "/docs",
            "health": "/health",
            "status": "ready",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
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
