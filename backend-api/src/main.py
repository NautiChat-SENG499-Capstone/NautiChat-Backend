from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import sessionmanager, Base

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router

from src.llm import models  # noqa
from src.auth import models  # noqa


# Setup routes
app = FastAPI()

# TO DO: add frontend url to origins
origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.on_event("startup")
async def on_startup():
    '''Create tables on startup using async engine'''
    async with sessionmanager._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def on_shutdown():
    '''Close connection to database'''
    await sessionmanager.close()