import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import models, schemas
from src.auth.service import get_password_hash
from src.settings import get_settings


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient, async_session: AsyncSession):
    new_user = schemas.CreateUserRequest(
        username="lebron", password="cavs", onc_token=get_settings().ONC_TOKEN
    )
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
    valid_onc_token = get_settings().ONC_TOKEN
    existing_user = models.User(
        username="lebron", hashed_password="cavs", onc_token=valid_onc_token
    )

    async_session.add(existing_user)
    await async_session.commit()
    await async_session.refresh(existing_user)

    user_attempt = schemas.CreateUserRequest(
        username=existing_user.username,
        password="differentpassword",
        onc_token=valid_onc_token,
    )
    response = await client.post("/auth/register", json=user_attempt.model_dump())
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    query = await async_session.execute(select(models.User))
    users = query.scalars().all()
    assert len(users) == 1, "duplicate user was added"


@pytest.mark.asyncio
async def test_register_invalid_onc_token(
    client: AsyncClient, async_session: AsyncSession
):
    new_user = schemas.CreateUserRequest(
        username="lebron", password="cavs", onc_token="invalid_token"
    )
    response = await client.post("/auth/register", json=new_user.model_dump())

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"] == "Invalid ONC token"

    # make sure no user was added to the db
    query = await async_session.execute(select(models.User))
    users = query.scalars().all()
    assert len(users) == 0, "user was added with invalid ONC token"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    unauthenticated_response = await client.get("/auth/me")
    assert unauthenticated_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_me_endpoint(
    client: AsyncClient, async_session: AsyncSession, user_headers
):
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
    user = models.User(
        username="new user",
        hashed_password=get_password_hash(password),
        onc_token=get_settings().ONC_TOKEN,
    )

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
async def test_login_guest_user(client: AsyncClient, async_session: AsyncSession):
    response = await client.post("/auth/guest-login")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)

    # make sure a guest user was created in the db
    query = await async_session.execute(select(models.User))
    users = query.scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_login_invalid_user(client: AsyncClient):
    # add user. since adding directly to db the password is not hashed which is easier for testing

    response = await client.post(
        "/auth/login",
        data={"username": "invaliduser", "password": "somepassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_update_user_info_success(
    client: AsyncClient, async_session: AsyncSession, user_headers
):
    valid_onc_token = get_settings().ONC_TOKEN
    new_info = {"username": "updated_user", "onc_token": valid_onc_token}

    response = await client.put("/auth/me", json=new_info, headers=user_headers)
    assert response.status_code == status.HTTP_200_OK

    updated = response.json()
    assert updated["username"] == "updated_user"
    assert updated["onc_token"] == valid_onc_token

    result = await async_session.execute(
        select(models.User).where(models.User.username == "updated_user")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.onc_token == valid_onc_token


@pytest.mark.asyncio
async def test_update_invalid_onc_token(
    client: AsyncClient, async_session: AsyncSession, user_headers
):
    # get current user in db
    query = await async_session.execute(select(models.User))
    current_user = query.scalar_one_or_none()
    assert current_user is not None
    user_valid_onc_token = current_user.onc_token

    new_info = {"username": "updated_user", "onc_token": "invalid_token"}

    response = await client.put("/auth/me", json=new_info, headers=user_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Invalid ONC token"

    # make sure user onc token is still valid
    query = await async_session.execute(select(models.User))
    current_user = query.scalar_one_or_none()
    assert current_user is not None
    assert current_user.onc_token == user_valid_onc_token


@pytest.mark.asyncio
async def test_update_user_info_username_exists(
    client: AsyncClient, async_session: AsyncSession, user_headers
):
    other_user = models.User(
        username="existing_user",
        hashed_password=get_password_hash("irrelevant"),
        onc_token=get_settings().ONC_TOKEN,
    )

    async_session.add(other_user)
    await async_session.commit()

    response = await client.put(
        "/auth/me", json={"username": "existing_user"}, headers=user_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_change_password_success(
    client: AsyncClient, async_session: AsyncSession, user_headers
):
    body = {
        "current_password": "hashedpassword",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123",
    }

    resp = await client.put("/auth/me/password", json=body, headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK
    updated_user = resp.json()
    assert updated_user["username"]  # user still exists

    login = await client.post(
        "/auth/login",
        data={"username": updated_user["username"], "password": "newpassword123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, user_headers):
    body = {
        "current_password": "wrongpassword",
        "new_password": "somethingnew",
        "confirm_password": "somethingnew",
    }

    resp = await client.put("/auth/me/password", json=body, headers=user_headers)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["detail"] == "Current password is incorrect"


@pytest.mark.asyncio
async def test_delete_me(
    client: AsyncClient, async_session: AsyncSession, user_headers
):
    delete_response = await client.delete("/auth/me/delete", headers=user_headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    # Confirm the user is gone
    query = await async_session.execute(
        select(models.User).where(models.User.username == "testuser")
    )
    user = query.scalar_one_or_none()
    assert user is None, "User was not deleted from the database"
