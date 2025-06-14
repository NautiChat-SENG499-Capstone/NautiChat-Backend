from fastapi.testclient import TestClient
from fastapi import status
import pytest


@pytest.mark.asyncio
async def test_non_rate_limit(client: TestClient, user_headers):
    # Send many requests back to back
    for _ in range(20):
        response = client.get("/auth/me", headers=user_headers)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@pytest.mark.use_middleware
async def test_get_rate_limited(client: TestClient, user_headers):
    # Send many requests back to back
    for _ in range(20):
        response = client.get("/auth/me", headers=user_headers)
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            return
    assert False, "Rate limiter didn't work"
