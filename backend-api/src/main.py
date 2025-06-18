from contextlib import asynccontextmanager # Used to manage async app startup/shutdown events

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Enables frontend-backend communications via CORS

from src.database import sessionmanager, Base, init_redis

from src.auth import models  # noqa
from src.llm import models  # noqa
from LLM.LLM import LLM  # noqa
from LLM.RAG import RAG
from LLM.Environment import Environment

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router
from src.middleware import RateLimitMiddleware # Custom middleware for rate limiting

#TO DO: we want a sanity check that the llm and rag are initialized correctly
#       and that the redis client is connected before starting the app
#       This could be done in the lifespan function, but we need to ensure that
#       the app does not start if these checks fail.


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("STARTING LIFESPAN")

    try:
        print("Creating tables...")
        async with sessionmanager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("DB setup complete")
    except Exception as e:
        print("DB setup failed:", e)
        raise

    try:
        print("Initializing Redis...")
        app.state.redis_client = init_redis()
        print("Redis init complete")
    except Exception as e:
        print("Redis init failed:", e)
        raise

    try:
        print("Initializing LLM and RAG...")
        env = Environment()
        rag_instance = RAG(env)
        app.state.llm = LLM(env=env, RAG_instance=rag_instance)
        app.state.rag = rag_instance
        print("LLM and RAG init complete")
    except Exception as e:
        print("LLM/RAG init failed:", e)
        raise

    yield

    print("Shutting down lifespan")

    try:
        await sessionmanager.close()
        await app.state.redis_client.aclose()
        print("Cleanup complete")
    except Exception as e:
        print("Cleanup failed:", e)



def create_app():
    app = FastAPI(lifespan=lifespan)

    # TODO: add frontend url to origins
    origins = ["http://localhost:3000"]

    # Add CORS and Rate Limit Middleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routes from modules (auth, llm, admin)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    return app

app = create_app()

