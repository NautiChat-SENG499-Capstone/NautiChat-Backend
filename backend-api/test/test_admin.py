import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from typing import List

from src.auth.models import User
from src.llm import schemas
from src.llm.models import Conversation, Message

@pytest.mark.asyncio
async def test_admin_endpoint_unauthenticated(client: AsyncClient):
    response = await client.get("/admin/messages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_admin_endpoint_as_user(client: AsyncClient, user_headers):
    response = await client.get("/admin/messages", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_admin_endpoint_as_admin(client: AsyncClient, async_session: AsyncSession, admin_headers):
    # add 2 users
    user1 = User(username="user1", hashed_password="hpw1", onc_token="token1")
    user2 = User(username="user2", hashed_password="hpw2", onc_token="token2")
    async_session.add_all([user1, user2])
    await async_session.commit()
    await async_session.refresh(user1)
    await async_session.refresh(user2)

    # add 2 conversations
    conv1 = Conversation(user=user1, title="conv 1")
    conv2 = Conversation(user=user2, title="conv 2")
    async_session.add_all([conv1, conv2])
    await async_session.commit()
    await async_session.refresh(conv1)
    await async_session.refresh(conv2)

    # add 2 messages
    message1 = Message(conversation=conv1, user_id=user1.id, input="hello from 1", response="response 1")
    message2 = Message(conversation=conv2, user_id=user2.id, input="hello from 2", response="response 2")
    async_session.add_all([message1, message2])
    await async_session.commit()
    await async_session.refresh(message1)
    await async_session.refresh(message2)

    response = await client.get("/admin/messages", headers=admin_headers)
    assert response.status_code == 200
    data: List = response.json()
    assert len(data) == 2
    # recent messages first
    assert schemas.Message.model_validate(data[0]).conversation_id == message2.conversation_id
    assert schemas.Message.model_validate(data[1]).conversation_id == message1.conversation_id


@pytest.mark.asyncio
async def test_clustered_messages_returns_valid_json(client: AsyncClient, async_session: AsyncSession, admin_headers):
    # add 2 users
    user1 = User(username="user1", hashed_password="hpw1", onc_token="token1")
    user2 = User(username="user2", hashed_password="hpw2", onc_token="token2")
    async_session.add_all([user1, user2])
    await async_session.commit()
    await async_session.refresh(user1)
    await async_session.refresh(user2)

    # add 2 conversations
    conv1 = Conversation(user=user1, title="conv 1")
    conv2 = Conversation(user=user2, title="conv 2")
    async_session.add_all([conv1, conv2])
    await async_session.commit()
    await async_session.refresh(conv1)
    await async_session.refresh(conv2)

    # add 2 messages
    message1 = Message(conversation=conv1, user_id=user1.id, input="hello from 1", response="response 1")
    message2 = Message(conversation=conv2, user_id=user2.id, input="hello from 2", response="response 2")

    async_session.add_all([message1, message2])
    await async_session.commit()
    await async_session.refresh(message1)
    await async_session.refresh(message2)

    response = await client.get("/admin/messages/clustered", headers=admin_headers)

    assert response.status_code == 200
    clusters = response.json()
    assert isinstance(clusters, dict)

