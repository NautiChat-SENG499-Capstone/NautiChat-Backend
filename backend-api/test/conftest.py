from datetime import timedelta
from typing import AsyncIterator

import pytest
import asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db_session
from src.auth import models
from src.auth.service import create_access_token
from src.auth.dependencies import get_settings
from src.main import app


DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture()
async def async_session() -> AsyncIterator[AsyncSession]:
    """Return the async test db session created for each test"""
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

@pytest.fixture()
async def client(async_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Return a test client which can be used to send api requests"""

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.fixture()
async def user_headers(async_session: AsyncSession):
    """Return headers for a simple user"""

    test_user = models.User(
        username="testuser", hashed_password="nothashedpassword", onc_token="onctoken", is_admin=False
    )

    async_session.add(test_user)
    await async_session.commit()
    await async_session.refresh(test_user)

    settings = get_settings()
    token = create_access_token(test_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)

    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
async def admin_headers(async_session: AsyncSession):
    """Return headers for an admin user"""

    admin_user = models.User(
        username="admin", hashed_password="nothashedpassword", onc_token="admintoken", is_admin=True
    )

    async_session.add(admin_user)
    await async_session.commit()
    await async_session.refresh(admin_user)

    settings = get_settings()
    token = create_access_token(admin_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)

    return {"Authorization": f"Bearer {token}"}

# @pytest.fixture()
# def session() -> Iterator[Session]:
#     """Return the test db session created for each test"""
#     test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

#     # foreign key constraints are not enforced by default
#     @event.listens_for(test_engine, "connect")
#     def _(dbapi_connection, _):
#         if isinstance(dbapi_connection, sqlite3.Connection):
#             cursor = dbapi_connection.cursor()
#             cursor.execute("PRAGMA foreign_keys=ON")
#             cursor.close()

#     Base.metadata.drop_all(bind=test_engine)
#     Base.metadata.create_all(bind=test_engine)

#     TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
#     db = TestingSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# @pytest.fixture()
# def client(session) -> Iterator[TestClient]:
#     """Return a test client which can be used to send api requests"""

#     def override_get_db():
#         try:
#             yield session
#         finally:
#             session.close()

#     app.dependency_overrides[get_db] = override_get_db
#     with TestClient(app) as test_client:
#         yield test_client


# @pytest.fixture()
# def user_headers(session):
#     """Return headers for a simple user"""

#     test_user = models.User(
#         username="testuser", hashed_password="nothashedpassword", onc_token="onctoken", is_admin=False
#     )
#     session.add(test_user)
#     session.commit()
#     session.refresh(test_user)

#     settings = get_settings()
#     token = create_access_token(test_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)
#     return {"Authorization": f"Bearer {token}"}


# @pytest.fixture()
# def admin_headers(session):
#     """Return headers for an admin user"""

#     admin_user = models.User(
#         username="admin", hashed_password="nothashedpassword", onc_token="admintoken", is_admin=True
#     )
#     session.add(admin_user)
#     session.commit()
#     session.refresh(admin_user)

#     settings = get_settings()
#     token = create_access_token(admin_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)
#     return {"Authorization": f"Bearer {token}"}
