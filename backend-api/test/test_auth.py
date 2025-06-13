import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.auth import models, schemas
from src.auth.service import get_password_hash


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient, async_session: AsyncSession):
    new_user = schemas.CreateUserRequest(username="lebron", password="cavs", onc_token="lebrontoken")
    response = await client.post("/auth/register", json=new_user.model_dump())

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)

    # get created user in db
    query = await async_session.execute(
        select(models.User).where(models.User.username == "lebron")
    )
    users = query.scalars().all()
    assert len(users) == 1

    added_user = users[0]
    assert added_user is not None
    assert added_user.username == "lebron"
    assert added_user.id == 1
    assert not added_user.is_admin

@pytest.mark.asyncio
async def test_register_existing_user(client: AsyncClient, async_session: AsyncSession):
    # add a user
    existing_user = models.User(username="lebron", hashed_password="cavs", onc_token="lebrontoken")
    
    async_session.add(existing_user)
    await async_session.commit()
    await async_session.refresh(existing_user)

    user_attempt = schemas.CreateUserRequest(
        username=existing_user.username, password="differentpassword", onc_token="differenttoken"
    )
    response = await client.post("/auth/register", json=user_attempt.model_dump())
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    query = await async_session.execute(select(models.User))
    users = query.scalars().all()
    assert len(users) == 1, "duplicate user was added"

@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    unauthenticated_response = await client.get("/auth/me")
    assert unauthenticated_response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_get_me_endpoint(client: AsyncClient, async_session: AsyncSession, user_headers):
    # at this point only one user in db, so current user should be that one
    response = await client.get("/auth/me", headers=user_headers)

    assert response.status_code == status.HTTP_200_OK
    returned_user = schemas.UserOut.model_validate(response.json())


    query = await async_session.execute(select(models.User))
    db_user = query.scalar_one_or_none()
    assert db_user is not None

    # compare pydantic models
    assert returned_user == schemas.UserOut.model_validate(db_user)

@pytest.mark.asyncio
async def test_login_existing_user(client: AsyncClient, async_session: AsyncSession):
    # add user. since adding directly to db the password is not hashed which is easier for testing
    password = "supersecure"
    user = models.User(username="new user", hashed_password=get_password_hash(password), onc_token="newtoken")

    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    response = await client.post(
        "/auth/login",
        data={"username": user.username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)

@pytest.mark.asyncio
async def test_login_invalid_user(client: AsyncClient):
    # add user. since adding directly to db the password is not hashed which is easier for testing

    response = await client.post(
        "/auth/login",
        data={"username": "invaliduser", "password": "somepassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
