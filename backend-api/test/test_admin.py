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
