import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.auth.models import User
from src.llm.models import Conversation, Message
from src.llm.utils import get_context

class DummyLLM:
    async def run_conversation(self, user_prompt, *_, **__):
        return f"LLM Response for {user_prompt}"
        async def _noop(*_args, **_kwargs):
            return ""
        return _noop
    def __getattr__(self, _):
        async def _noop(*args, **kwargs):
            return ""
        return _noop

@pytest_asyncio.fixture(autouse=True)
async def _stub_llm_and_rag(client: AsyncClient):
    asgi_app = getattr(client, "app", None)
    if asgi_app is None:
        transport = getattr(client, "_transport", None)
        asgi_app = getattr(transport, "app", None) or getattr(transport, "_app", None)
    assert asgi_app is not None, "Could not locate ASGI app on AsyncClient"

    asgi_app.state.llm = DummyLLM()
    asgi_app.state.rag = DummyRAG()
    yield
    del asgi_app.state.llm
    del asgi_app.state.rag

@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, user_headers):
    resp = await client.post("/llm/conversations", json={"title": "Test"}, headers=user_headers)
    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["title"] == "Test" and isinstance(body["conversation_id"], int)


@pytest.mark.asyncio
async def test_get_conversations_empty(client: AsyncClient, user_headers):
    resp = await client.get("/llm/conversations", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK and resp.json() == []



@pytest.mark.asyncio
async def test_get_conversation_success(client: AsyncClient, user_headers):
    conv_id = (
        await client.post("/llm/conversations", json={"title": "C1"}, headers=user_headers)
    ).json()["conversation_id"]
    resp = await client.get(f"/llm/conversations/{conv_id}", headers=user_headers)
    assert resp.status_code == status.HTTP_200_OK and resp.json()["conversation_id"] == conv_id



@pytest.mark.asyncio
async def test_get_conversation_not_found(client: AsyncClient, user_headers):
    assert (await client.get("/llm/conversations/9999", headers=user_headers)).status_code == status.HTTP_404_NOT_FOUND



@pytest.mark.asyncio
async def test_get_conversation_unauthorized(client: AsyncClient, user_headers):
    conv_id = (
        await client.post("/llm/conversations", json={"title": "Private"}, headers=user_headers)
    ).json()["conversation_id"]

    reg = await client.post(
        "/auth/register", json={"username": "x", "password": "p", "onc_token": "tok"}
    )
    headers2 = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    assert (await client.get(f"/llm/conversations/{conv_id}", headers=headers2)).status_code == status.HTTP_404_NOT_FOUND


async def test_generate_and_retrieve_message(client: AsyncClient, user_headers):
    conv_id = (
        await client.post("/llm/conversations", json={"title": "Chat"}, headers=user_headers)
    ).json()["conversation_id"]

    msg = (
        await client.post(
            "/llm/messages",
            json={"input": "Hi", "conversation_id": conv_id},
            headers=user_headers,
        )
    ).json()
    assert "LLM Response for" in msg["response"]

    got = await client.get(f"/llm/messages/{msg['message_id']}", headers=user_headers)
    assert got.status_code == status.HTTP_200_OK
    assert got.json()["message_id"] == msg["message_id"]



@pytest.mark.asyncio
async def test_feedback_create_and_update(client: AsyncClient, user_headers):
    conv_id = (
        await client.post("/llm/conversations", json={"title": "FB"}, headers=user_headers)
    ).json()["conversation_id"]

    msg_id = (
        await client.post("/llm/messages", json={"input": "Feedback?", "conversation_id": conv_id}, headers=user_headers)
    ).json()["message_id"]

    assert (
        await client.patch(
            f"/llm/messages/{msg_id}/feedback", json={"rating": 5}, headers=user_headers
        )
    ).status_code == status.HTTP_200_OK
    assert (
        await client.patch(
            f"/llm/messages/{msg_id}/feedback", json={"rating": 2}, headers=user_headers
        )
    ).status_code == status.HTTP_200_OK

async def test_get_context_no_messages(async_session: AsyncSession, _user_headers):
    # When no messages in db, should return empty list

    # Add conversation
    users = await async_session.execute(select(User))
    user_in_db = users.scalars().first()
    assert user_in_db is not None
    new_conversation = Conversation(user_id=user_in_db.id)

    async_session.add(new_conversation)
    await async_session.commit()
    await async_session.refresh(new_conversation)

    context = await get_context(new_conversation.conversation_id, 500, async_session)
    assert len(context) == 0
    await async_session.refresh(new_conversation)

async def test_get_context(async_session: AsyncSession, _user_headers):
    # Add conversation
    users = await async_session.execute(select(User))
    user_in_db = users.scalars().first()
    assert user_in_db is not None
    new_conversation = Conversation(user_id=user_in_db.id)

    async_session.add(new_conversation)
    await async_session.commit()
    await async_session.refresh(new_conversation)

    content_8 = "one two three four five six seven eight"
    content_3 = "one two three"

    message_20 = Message(
        conversation_id=new_conversation.conversation_id, user_id=user_in_db.id, input=content_8, response=content_8
    )  # 4 + 8 + 8 = 20 words
    message_15 = Message(
        conversation_id=new_conversation.conversation_id, user_id=user_in_db.id, input=content_8, response=content_3
    )  # 4 + 8 + 3 = 15 words

    async_session.add(message_20)
    async_session.add(message_15)
    await async_session.commit()
    await async_session.refresh(message_20)
    await async_session.refresh(message_15)
    await async_session.refresh(new_conversation)

    context_1 = await get_context(new_conversation.conversation_id, 30, async_session)
    assert len(context_1) == 2  # 1 for input and 1 for response

    context_2 = await get_context(new_conversation.conversation_id, 100, async_session)
    assert len(context_2) == 4
    assert isinstance(context_2[0]["role"], str)
    # most recent message should be returned first
    assert context_2[0]["role"] == "user"
    assert context_2[0]["content"] == message_15.input
    assert context_2[1]["role"] == "system"
    assert context_2[1]["content"] == message_15.response
    assert context_2[0]["role"] == "user"
    assert context_2[0]["content"] == message_15.input
    assert context_2[1]["role"] == "system"
    assert context_2[1]["content"] == message_15.response
