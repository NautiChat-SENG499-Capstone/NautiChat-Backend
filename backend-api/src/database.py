import contextlib
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import Request
from redis.asyncio import Redis

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.settings import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for ORM models."""
    pass


class DatabaseSessionManager:
    """Manages async SQLAlchemy engine and session lifecycle."""

    def __init__(self, db_url: str, engine_kwargs: dict[str, Any] = {}):
        self._url = db_url
        self._engine = None
        self._sessionmaker = None

        url_obj = make_url(db_url)
        is_postgres = url_obj.drivername.startswith("postgresql")
        
        default_kwargs = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
        }

        if not is_postgres:
            default_kwargs["pool_class"] = AsyncAdaptedQueuePool
            connect_args = {
                "ssl": False,  # consider using ssl.create_default_context() in prod
                "prepared_statement_name_func": lambda _: f"__asyncpg_{uuid4()}",
                "timeout": 5,
                "server_settings": {"statement_timeout": 5000},
            }
        else:
            connect_args = {}

        self._engine = create_async_engine(
            db_url,
            connect_args=connect_args,
            **default_kwargs,
        )


        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def close(self):
        """Disposes the engine on app shutdown."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection, None]:
        """Yields a raw database connection."""
        if self._engine is None:
            raise RuntimeError("Database engine is not initialized")

        async with self._engine.begin() as conn:
            yield conn  # no rollback needed — connections don't manage transactions directly

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yields a database session."""
        if self._sessionmaker is None:
            raise RuntimeError("Sessionmaker is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session."""
    session_manager = request.app.state.session_manager
    async with session_manager.session() as session:
        yield session


async def init_redis() -> Redis:
    """Initializes a Redis client using settings."""
    settings = get_settings()
    redis = Redis(
        host="redis-13649.crce199.us-west-2-2.ec2.redns.redis-cloud.com",
        port=13649,
        decode_responses=True,
        username="default",
        password=settings.REDIS_PASSWORD,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    await redis.ping()
    return redis
