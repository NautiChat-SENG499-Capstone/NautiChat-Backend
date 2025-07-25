import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import models, schemas
from src.auth.service import get_password_hash, get_user
from src.settings import get_settings


class TestRegistration:
    def _create_user_request(
        self,
        username: str = "tester",
        password: str = "password",
        token=get_settings().ONC_TOKEN,
    ) -> schemas.CreateUserRequest:
        """Create User Request schema"""
        user = schemas.CreateUserRequest(
            username=username, password=password, onc_token=token
        )
        return user

    def _create_user_model(
        self,
        username: str = "tester",
        password: str = "password",
        token=get_settings().ONC_TOKEN,
    ) -> models.User:
        """Create User Model"""
        user = models.User(username=username, hashed_password=password, onc_token=token)
        return user

    @pytest.mark.asyncio
    async def test_register_new_user(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Test registering a new user"""

        new_user = self._create_user_request(username="lebron", password="cavs")

        response = await client.post("/auth/register", json=new_user.model_dump())
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["token_type"] == "bearer"
        assert isinstance(response.json()["access_token"], str)

        # Get user after registration
        user = await get_user(new_user.username, async_session)

        assert user is not None
        assert user.username == "lebron"
        assert user.id == 1
        assert not user.is_admin

    @pytest.mark.asyncio
    async def test_register_existing_user(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Test adding a user that already exists"""

        # Add user that should exist in db first
        existing_user = self._create_user_model(username="lebron", password="cavs")
        async_session.add(existing_user)
        await async_session.commit()
        await async_session.refresh(existing_user)

        # Add another user with same username
        user_attempt = self._create_user_request(
            username=existing_user.username, password="differentpassword"
        )
        response = await client.post("/auth/register", json=user_attempt.model_dump())
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        result = await async_session.execute(select(models.User))
        users = result.scalars().all()
        assert len(users) == 1, "duplicate user was added"

    @pytest.mark.asyncio
    async def test_register_invalid_onc_token(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Test registering user with invalid onc token"""
        invalid = self._create_user_request(
            username="lebron", password="cavs", token="invalid_token"
        )

        response = await client.post("/auth/register", json=invalid.model_dump())

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid ONC token"

        # make sure user was not added to the db
        result = await async_session.execute(select(models.User))
        users = result.scalars().all()
        assert len(users) == 0, "user was added with invalid ONC token"


class TestAuthentication:
    def _create_user_model(
        self,
        username: str = "tester",
        password: str = "password",
        token=get_settings().ONC_TOKEN,
    ) -> models.User:
        """Returns User model"""
        user = models.User(username=username, hashed_password=password, onc_token=token)
        return user

    @pytest.mark.asyncio
    async def test_login_existing_user(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Login with existing user"""
        # Add user that should exist in database
        password = "supersecure"
        user = self._create_user_model(
            username="newUser", password=get_password_hash(password)
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Login with the user
        response = await client.post(
            "/auth/login",
            data={"username": user.username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["token_type"] == "bearer"
        assert isinstance(response.json()["access_token"], str)

    @pytest.mark.asyncio
    async def test_login_guest_user(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Login as a guest user"""
        response = await client.post("/auth/guest-login")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["token_type"] == "bearer"
        assert isinstance(response.json()["access_token"], str)

        # make sure a guest user was created in the db
        query = await async_session.execute(select(models.User))
        users = query.scalars().all()
        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_login_incorrect_credentials(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        """Attempt to log in with incorrect credentials"""
        password = "right"
        user = self._create_user_model("wrongpasswordtest", get_password_hash(password))
        async_session.add(user)
        await async_session.commit()

        resp = await client.post(
            "/auth/login",
            data={"username": user.username, "password": "WRONG"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.json()["detail"] == "Incorrect username or password"

    @pytest.mark.asyncio
    async def test_login_invalid_user(self, client: AsyncClient):
        """Test that attempts to login with invalid user"""
        response = await client.post(
            "/auth/login",
            data={"username": "invaliduser", "password": "somepassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserProfile:
    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """Test to get user without authorization (json token)"""
        unauthenticated_response = await client.get("/auth/me")
        assert unauthenticated_response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_me_endpoint(
        self, client: AsyncClient, async_session: AsyncSession, user_headers: dict
    ):
        """Test that gets user"""

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
    async def test_update_user_info_success(
        self, client: AsyncClient, async_session: AsyncSession, user_headers: dict
    ):
        """Test to update user info"""
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
        self, client: AsyncClient, async_session: AsyncSession, user_headers: dict
    ):
        """Test that attempts to update with invalid onc token"""
        new_info = {"username": "updated_user", "onc_token": "invalid_token"}

        response = await client.put("/auth/me", json=new_info, headers=user_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid ONC token"

    @pytest.mark.asyncio
    async def test_update_username_conflict(
        self, client: AsyncClient, async_session: AsyncSession, user_headers: dict
    ):
        """Test that updates username that already exists in db"""
        taken = models.User(
            username="existing_user",
            hashed_password=get_password_hash("irrelevant"),
            onc_token=get_settings().ONC_TOKEN,
        )

        async_session.add(taken)
        await async_session.commit()

        response = await client.put(
            "/auth/me", json={"username": "existing_user"}, headers=user_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Username already exists"


class TestPasswordChange:
    @pytest.mark.asyncio
    async def test_change_password_success(
        self, client: AsyncClient, user_headers: dict
    ):
        """Update password successfully"""
        body = {
            "current_password": "hashedpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        }

        resp = await client.put("/auth/me/password", json=body, headers=user_headers)
        assert resp.status_code == status.HTTP_200_OK

        # Login with new password
        login = await client.post(
            "/auth/login",
            data={"username": resp.json()["username"], "password": "newpassword123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that tries to change password but current password is incorrect"""
        body = {
            "current_password": "wrongpassword",
            "new_password": "somethingnew",
            "confirm_password": "somethingnew",
        }

        resp = await client.put("/auth/me/password", json=body, headers=user_headers)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.json()["detail"] == "Current password is incorrect"

    @pytest.mark.asyncio
    async def test_change_password_mismatch(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that attempts to change password with misamtch new password"""
        body = {
            "current_password": "hashedpassword",
            "new_password": "abc12345",
            "confirm_password": "def99999",
        }

        resp = await client.put("/auth/me/password", json=body, headers=user_headers)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "New password and confirmation do not match"


class TestUserDeletion:
    @pytest.mark.asyncio
    async def test_delete_me(
        self, client: AsyncClient, async_session: AsyncSession, user_headers: dict
    ):
        """Delete user from db"""
        delete_response = await client.delete("/auth/me/delete", headers=user_headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Confirm the user is gone
        query = await async_session.execute(
            select(models.User).where(models.User.username == "testuser")
        )
        user = query.scalar_one_or_none()
        assert user is None, "User was not deleted from the database"
