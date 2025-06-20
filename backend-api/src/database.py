import contextlib

from typing import Any, AsyncIterator
from uuid import uuid4
from fastapi import Request

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine.url import make_url
from redis.asyncio import Redis

from src.settings import get_settings


# Building async engine & sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)

from fastapi import Request



# Base class for all ORM models (Helps with Lazy Loading)
class Base(AsyncAttrs, DeclarativeBase):
    pass


class DatabaseSessionManager:
    """
    Manages the async SQLAlchemy engine and session lifecycle.
    Supports both Postgres (e.g., Supabase) and SQLite for testing.
    """

    def __init__(self, db_url: str, engine_kwargs: dict[str, Any] = {}):
        self._url = db_url
        self._engine = None
        self._sessionmaker = None

        # Parse URL and detect DB type (postgres or sqlite)
        url_obj = make_url(db_url)
        is_postgres = url_obj.drivername.startswith("postgresql")

        if is_postgres:
            # TODO: Create an SSL context for asyncpg
            # ssl_context = ssl.create_default_context()
            # connect_args = {"ssl": ssl_context}

            connect_args = {
                "ssl": False,
                "statement_cache_size": 0,  # Disable asyncpg prepared statement cache
                "prepared_statement_cache_size": 0,  # Additional cache setting for async postgres
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
                "server_settings": {
                    "statement_timeout": "3000",  # Optional: Set statement timeout
                },
            }
        else:
            connect_args = {}

        # Default pool: 5 conns, no overflow, pre-ping, 30-min recycle
        default_kwargs = dict(
            pool_size=5,
            max_overflow=0,         # never exceed Supabase’s 10-conn limit
            pool_recycle=1800,
            pool_pre_ping=True, 
        )
        default_kwargs.update(engine_kwargs)

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
        """Disposes the engine on app shutdown"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        """Yields a raw database connection"""
        if self._engine is None:
            raise Exception("Database engine is not initialized")

        async with self._engine.begin() as conn:
            try:
                yield conn
            except Exception:
                await conn.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yields an ORM session for use in endpoints or services"""
        if self._sessionmaker is None:
            raise Exception("Sessionmaker is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# FastAPI dependency for Endpoints
async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Dependency that yields a database session"""
    session_manager = request.app.state.session_manager
    async with session_manager.session() as session:
        yield session


# Creates an async Redis Client
async def init_redis():
    redis = await Redis(
        host="redis-13649.crce199.us-west-2-2.ec2.redns.redis-cloud.com",
        port=13649,
        decode_responses=True,
        username="default",
        password=get_settings().REDIS_PASSWORD,
        socket_timeout=5,  # Prevents hanging forever
        socket_connect_timeout=5,
    )
    await redis.ping()

    return redis
