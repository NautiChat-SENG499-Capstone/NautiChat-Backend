import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_admin_endpoint_unauthenticated(client: AsyncClient):
    response = await client.get("/admin/messages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_admin_endpoint_as_user(client: AsyncClient, user_headers):
    response = await client.get("/admin/messages", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN




@pytest.mark.asyncio
async def test_clustered_messages_returns_valid_json(client: AsyncClient, admin_headers):
    response = await client.get("/admin/messages/clustered", headers=admin_headers)

    assert response.status_code == 200
    clusters = response.json()
    assert isinstance(clusters, dict)
    
@pytest.mark.asyncio
async def test_raw_text_upload(client: AsyncClient, user_headers):
    payload = {
        "source": "unit-test-source",
        "information": "This is some test information to upload to the vector DB."
    }

    response = await client.post(
        "/admin/data-upload",
        headers=user_headers,
        json=payload

    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
