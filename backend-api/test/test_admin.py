import pytest
from fastapi import status
from httpx import AsyncClient


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
        "onc_token": "token123"
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
        json={"username": "unauth", "password": "x", "onc_token": "y"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_admin_as_normal_user(client: AsyncClient, user_headers):
    response = await client.post(
        "/admin/create",
        json={"username": "baduser", "password": "x", "onc_token": "y"},
        headers=user_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_clustered_messages_returns_valid_json(
    client: AsyncClient, admin_headers
):
    response = await client.get("/admin/messages/clustered", headers=admin_headers)

    assert response.status_code == 200
    clusters = response.json()
    assert isinstance(clusters, dict)
