import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth import schemas
from src.auth.service import get_user_by_token
from src.settings import get_settings


class TestAuthentication:
    @pytest.mark.asyncio
    async def test_admin_endpoint_unauthenticated(self, client: AsyncClient):
        """Test attempt at accessing admin endpoint"""
        response = await client.get("/admin/messages")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_admin_endpoint_as_user(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test attempt at accessing admin endpoint with user account"""
        response = await client.get("/admin/messages", headers=user_headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminCreation:
    async def _create_user_request(
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

    @pytest.mark.asyncio
    async def test_create_admin_success(self, client: AsyncClient, admin_headers: dict):
        """Test attempt at creating new admin"""
        new_admin = await self._create_user_request(
            username="newadmin", password="securepass123"
        )

        response = await client.post(
            "/admin/create", json=new_admin.model_dump(), headers=admin_headers
        )
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["username"] == new_admin.username
        assert data["is_admin"] is True

    @pytest.mark.asyncio
    async def test_create_admin_unauthenticated(self, client: AsyncClient):
        """Test attempt create admin without authentication"""
        bad_request = await self._create_user_request(username="unauth", password="x")
        response = await client.post(
            "/admin/create",
            json=bad_request.model_dump(),
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_admin_as_normal_user(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test attempt at creating admin as normal user"""
        bad_request = await self._create_user_request(username="baduser", password="x")
        response = await client.post(
            "/admin/create",
            json=bad_request.model_dump(),
            headers=user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_admin_invalid_onc_token(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test creating an admin with an invalid ONC token"""
        invalid_admin = await self._create_user_request(
            username="admin4", password="pass", token="invalid_token"
        )
        response = await client.post(
            "/admin/create",
            json=invalid_admin.model_dump(),
            headers=admin_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid ONC token"


class TestDeleteUsers:
    @pytest.mark.asyncio
    async def test_delete_admin_user_success(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test that deletes admin user from db"""
        target_admin_data = {
            "username": "deleteadmin",
            "password": "deletepass",
            "onc_token": get_settings().ONC_TOKEN,
        }

        create_response = await client.post(
            "/admin/create", json=target_admin_data, headers=admin_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        target_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/admin/users/{target_id}", headers=admin_headers
        )
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self(
        self, client: AsyncClient, async_session: AsyncSession, admin_headers: dict
    ):
        """Test that attempts for admin to delete themselves"""
        # Extract the token from headers
        token = admin_headers["Authorization"].split("Bearer ")[1]

        # Get user object
        admin_user = await get_user_by_token(token, get_settings(), async_session)

        response = await client.delete(
            f"/admin/users/{admin_user.id}", headers=admin_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            response.json()["detail"] == "Admins are not allowed to delete themselves"
        )


class TestMessageClustering:
    @pytest.mark.asyncio
    async def test_clustered_messages_returns_valid_json(
        self, client: AsyncClient, admin_headers: dict
    ):
        """Test that clusters messages"""
        response = await client.get("/admin/messages/clustered", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        clusters = response.json()
        assert isinstance(clusters, dict)
