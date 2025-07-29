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
from src.middleware import limiter
from src.settings import get_settings

from LLM.Constants.status_codes import StatusCode
from LLM.core import LLM
from LLM.Environment import Environment
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse

SUPABASE_DB_URL = "sqlite+aiosqlite:///:memory:"

# A global instance of the real llm instance so that tests don't re-initialize each time
_real_llm_instance = None


@pytest.fixture
def _user_headers(user_headers):
    """Alias the existing user_headers fixture for tests expecting _user_headers"""
    return user_headers


@pytest.fixture(scope="session", autouse=True)
def disable_rate_limiter():
    """Globally disable rate limiting for all tests"""
    limiter.enabled = False


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


class MockLLM:
    def __init__(self):
        self.called_with_history = None
        self.last_prompt = None

    async def run_conversation(
        self,
        user_prompt: str,
        user_onc_token: str,
        chat_history: list[dict] = [],
        obtained_params: ObtainedParamsDictionary = ObtainedParamsDictionary(),
        previous_vdb_ids: list[dict] = [],
    ) -> RunConversationResponse:
        self.called_with_history = chat_history
        self.last_prompt = user_prompt.lower()

        dummy_sources = ["source_1", "source_2"]
        dummy_point_ids = ["point_abc123", "point_def456"]
        dummy_obtained_params = ObtainedParamsDictionary()  # All fields empty/default

        # Simulate response based on prompt content
        if "onc" in self.last_prompt:
            return RunConversationResponse(
                status=StatusCode.REGULAR_MESSAGE,
                response="ONC is Ocean Networks Canada.",
                sources=dummy_sources,
                point_ids=dummy_point_ids,
                dummy_obtained_params=dummy_obtained_params,
            )

        elif "download" in self.last_prompt:
            if "scalar" in self.last_prompt and "data" in self.last_prompt:
                return RunConversationResponse(
                    status=StatusCode.PROCESSING_DATA_DOWNLOAD,
                    response="Download request submitted.",
                    dpRequestId=42,
                    baseUrl="https://data.oceannetworks.ca/api/scalar?",
                    urlParamsUsed={"sensor_id": "123", "start": "2020-01-01"},
                    sources=dummy_sources,
                    point_ids=dummy_point_ids,
                    dummy_obtained_params=dummy_obtained_params,
                )
            else:
                return RunConversationResponse(
                    status=StatusCode.PARAMS_NEEDED,
                    response="I need more info to download anything.",
                    sources=dummy_sources,
                    point_ids=dummy_point_ids,
                    dummy_obtained_params=dummy_obtained_params,
                )

        elif "interrupt" in self.last_prompt:
            return RunConversationResponse(
                status=StatusCode.DEPLOYMENT_ERROR,
                response="Tool call was interrupted. Please try again.",
                sources=dummy_sources,
                point_ids=dummy_point_ids,
                dummy_obtained_params=dummy_obtained_params,
            )

        elif "fail" in self.last_prompt:
            return RunConversationResponse(
                status=StatusCode.LLM_ERROR,
                response="Something went wrong while processing the message.",
                sources=dummy_sources,
                point_ids=dummy_point_ids,
                dummy_obtained_params=dummy_obtained_params,
            )

        elif "no data" in self.last_prompt:
            return RunConversationResponse(
                status=StatusCode.NO_DATA,
                response="No data was available for your request.",
                sources=dummy_sources,
                point_ids=dummy_point_ids,
                dummy_obtained_params=dummy_obtained_params,
            )

        else:
            return RunConversationResponse(
                status=StatusCode.REGULAR_MESSAGE,
                response=f"Default mock response to: '{user_prompt}'",
                sources=dummy_sources,
                point_ids=dummy_point_ids,
                dummy_obtained_params=dummy_obtained_params,
            )

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


@pytest.fixture(scope="session")
def real_llm() -> LLM:
    """Create and cache the real LLM once per session."""
    global _real_llm_instance
    if _real_llm_instance is None:
        _real_llm_instance = LLM(Environment())
    return _real_llm_instance


@pytest_asyncio.fixture(autouse=True)
async def _stub_llm_and_rag(
    client: AsyncClient, async_session: AsyncSession, request, real_llm
):
    if request.node.get_closest_marker("use_real_llm"):
        asgi_app = getattr(client, "app", None)
        if asgi_app is None:
            transport = getattr(client, "_transport", None)
            asgi_app = getattr(transport, "app", None) or getattr(
                transport, "_app", None
            )
        assert asgi_app is not None, "Could not locate ASGI app on AsyncClient"

        llm_instance = real_llm
        asgi_app.state.llm = llm_instance
        asgi_app.state.rag = llm_instance.RAG_instance
        yield
        return

    asgi_app = getattr(client, "app", None)
    if asgi_app is None:
        transport = getattr(client, "_transport", None)
        asgi_app = getattr(transport, "app", None) or getattr(transport, "_app", None)
    assert asgi_app is not None, "Could not locate ASGI app on AsyncClient"

    asgi_app.state.llm = MockLLM()
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
