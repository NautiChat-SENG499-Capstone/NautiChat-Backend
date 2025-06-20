import pytest
from httpx import AsyncClient
from fastapi import status

class DummyLLM:
    async def run_conversation(self, user_prompt, *_, **__):
        return f"LLM Response for {user_prompt}"

class DummyRAG:
    pass

@pytest.fixture(autouse=True)
async def _stub_llm_and_rag(client: AsyncClient):
    asgi_app = getattr(client, "app", None)
    if asgi_app is None:  # Fallback for transports without the attribute
        transport = getattr(client, "_transport", None)
        asgi_app = getattr(transport, "app", None) or getattr(transport, "_app", None)
    assert asgi_app is not None, "Could not locate ASGI app on AsyncClient"

    asgi_app.state.llm = DummyLLM()
    asgi_app.state.rag = DummyRAG()
    yield  # no teardown necessary

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


@pytest.mark.asyncio
async def test_generate_and_retrieve_message(client: AsyncClient, user_headers):
    conv_id = (
        await client.post("/llm/conversations", json={"title": "Chat"}, headers=user_headers)
    ).json()["conversation_id"]

    msg = (
        await client.post("/llm/messages", json={"input": "Hi", "conversation_id": conv_id}, headers=user_headers)
    ).json()
    assert "LLM Response for" in msg["response"]

    get_msg = await client.get(f"/llm/messages/{msg['message_id']}", headers=user_headers)
    assert get_msg.status_code == status.HTTP_200_OK and get_msg.json()["message_id"] == msg["message_id"]


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
