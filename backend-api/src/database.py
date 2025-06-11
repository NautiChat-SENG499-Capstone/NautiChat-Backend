import os
import contextlib
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# Load DATABASE_URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Base class for all ORM models
Base = declarative_base()

class DatabaseSessionManager:
    """
    Manages the async SQLAlchemy engine and session lifecycle.
    This allows consistent session creation and teardown across
    the FastAPI app. Can also be used for testing.
    """

    def __init__(self, db_url: str, engine_kwargs: dict[str, Any] = {}):
        # Create the async engine
        self._engine = create_async_engine(
            db_url,
            connect_args={"sslmode": "require"},  # Required for Supabase/Postgres
            **engine_kwargs
        )
        # Create the session bound to the engine
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def close(self):
        '''Disposes the engine on app shutdown'''
        if self._engine is None:
            raise Exception("Database engine is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        '''Context manager for DB connection'''
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
        '''Context manager for async DB session (use in endpoints)'''
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

# Global session manager instance
sessionmanager = DatabaseSessionManager(DATABASE_URL)

# For FastAPI Endpoints (Dependency)
async def get_db() -> AsyncIterator[AsyncSession]:
    """Get a new database session."""
    async with sessionmanager.session() as session:
        yield session