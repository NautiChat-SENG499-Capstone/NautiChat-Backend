import pytest
from fastapi import status
from httpx import AsyncClient
from src.auth.service import get_user_by_token
from src.settings import get_settings


@pytest.mark.asyncio
async def test_admin_endpoint_unauthenticated(client: AsyncClient):
    response = await client.get("/admin/messages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_admin_endpoint_as_user(client: AsyncClient, user_headers):
    response = await client.get("/admin/messages", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_admin_success(client: AsyncClient, admin_headers):
    new_admin_data = {
        "username": "newadmin",
        "password": "securepass123",
        "onc_token": get_settings().ONC_TOKEN,
    }

    response = await client.post(
        "/admin/create", json=new_admin_data, headers=admin_headers
    )
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["username"] == new_admin_data["username"]
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_create_admin_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/admin/create",
        json={
            "username": "unauth",
            "password": "x",
            "onc_token": get_settings().ONC_TOKEN,
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_admin_as_normal_user(client: AsyncClient, user_headers):
    response = await client.post(
        "/admin/create",
        json={
            "username": "baduser",
            "password": "x",
            "onc_token": get_settings().ONC_TOKEN,
        },
        headers=user_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_admin_user_success(
    client: AsyncClient, async_session, admin_headers
):
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
    client: AsyncClient, async_session, admin_headers
):
    # Extract the token from headers
    token = admin_headers["Authorization"].split("Bearer ")[1]

    # Get user object
    admin_user = await get_user_by_token(token, get_settings(), async_session)

    response = await client.delete(
        f"/admin/users/{admin_user.id}", headers=admin_headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Admins are not allowed to delete themselves"


@pytest.mark.asyncio
async def test_clustered_messages_returns_valid_json(
    client: AsyncClient, admin_headers
):
    response = await client.get("/admin/messages/clustered", headers=admin_headers)

    assert response.status_code == 200
    clusters = response.json()
    assert isinstance(clusters, dict)
