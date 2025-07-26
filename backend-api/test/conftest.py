import asyncio
from datetime import timedelta
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from src.auth import models
from src.auth.service import create_access_token, get_password_hash
from src.database import Base, get_db_session
from src.main import create_app
from src.settings import get_settings

from LLM.Constants.status_codes import StatusCode
from LLM.schemas import RunConversationResponse

SUPABASE_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def _user_headers(user_headers):
    """Alias the existing user_headers fixture for tests expecting _user_headers"""
    return user_headers


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Tests share same asyncio loop"""
    return asyncio.get_event_loop()


@pytest_asyncio.fixture()
async def async_session() -> AsyncIterator[AsyncSession]:
    """Creates async test db session per test and resets"""
    engine = create_async_engine(
        SUPABASE_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(async_session: AsyncSession, request) -> AsyncIterator[AsyncClient]:
    """Return a test client which can be used to send api requests"""

    async def override_get_db_session():
        yield async_session

    test_app = create_app()

    # Disable middleware unless @pytest.mark.use_middleware
    if request.node.get_closest_marker("use_middleware") is None:
        test_app.user_middleware = []

    test_app.dependency_overrides[get_db_session] = override_get_db_session

    if request.node.get_closest_marker("use_lifespan"):
        async with LifespanManager(test_app):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                yield c
    else:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture()
async def user_headers(async_session: AsyncSession):
    """Return headers for a simple user"""

    test_user = models.User(
        username="testuser",
        hashed_password=get_password_hash("hashedpassword"),
        onc_token=get_settings().ONC_TOKEN,
        is_admin=False,
    )

    async_session.add(test_user)
    await async_session.commit()
    await async_session.refresh(test_user)

    settings = get_settings()
    token = create_access_token(
        test_user.username,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
        settings,
    )

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def admin_headers(async_session: AsyncSession):
    """Return headers for an admin user"""

    admin_user = models.User(
        username="admin",
        hashed_password=get_password_hash("hashedpassword"),
        onc_token=get_settings().ONC_TOKEN,
        is_admin=True,
    )

    async_session.add(admin_user)
    await async_session.commit()
    await async_session.refresh(admin_user)

    settings = get_settings()
    token = create_access_token(
        admin_user.username,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
        settings,
    )

    return {"Authorization": f"Bearer {token}"}


class DummyLLM:
    async def run_conversation(self, user_prompt, *_, **__):
        return RunConversationResponse(
            status=StatusCode.REGULAR_MESSAGE,
            response=f"LLM Response for {user_prompt}",
        )

        async def _noop(*_args, **_kwargs):
            return ""

        return _noop

    def __getattr__(self, _):
        async def _noop(*args, **kwargs):
            return ""

        return _noop


class DummyRAG:
    """Returns an empty result for whatever method is called."""

    def __getattr__(self, _):
        async def _noop(*args, **kwargs):
            return ""

        return _noop


@pytest_asyncio.fixture(autouse=True)
async def _stub_llm_and_rag(client: AsyncClient):
    asgi_app = getattr(client, "app", None)
    if asgi_app is None:
        transport = getattr(client, "_transport", None)
        asgi_app = getattr(transport, "app", None) or getattr(transport, "_app", None)
    assert asgi_app is not None, "Could not locate ASGI app on AsyncClient"

    asgi_app.state.llm = DummyLLM()
    asgi_app.state.rag = DummyRAG()
    yield
    del asgi_app.state.llm
    del asgi_app.state.rag


@pytest.fixture(autouse=True)
def patch_onc_token_validation(request):
    async def mock_validate_onc_token(token: str):
        """Mock ONC token validation"""

        if token == get_settings().ONC_TOKEN:
            return

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ONC token"
        )

    with patch(
        "src.auth.service.validate_onc_token", new_callable=AsyncMock
    ) as mock_onc:
        mock_onc.side_effect = mock_validate_onc_token
        yield mock_onc
