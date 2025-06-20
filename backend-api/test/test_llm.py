import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class DummyLLM:
    async def run_conversation(self, user_prompt, startingPrompt, chatHistory, user_onc_token=None):
        return f"LLM Response for {user_prompt}"

class DummyRAG:
    pass

from src.main import app as _app

@pytest.fixture(autouse=True)
def stub_services():
    _app.state.llm = DummyLLM()
    _app.state.rag = DummyRAG()

@pytest.fixture(autouse=True)
def stub_services(client):
    # Inject dummy services into app state
    client.app.state.llm = DummyLLM()
    client.app.state.rag = DummyRAG()


@pytest.mark.asyncio
async def test_create_converstation(client: AsyncClient, user_headers):
    # Payload for creating a conversation
    payload = {"title": "Test Conversation"}
    response = await client.post("/llm/conversations", json=payload, headers=user_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "conversation_id" in data
    assert isinstance(data["conversation_id"], int)

@pytest.mark.asyncio
async def test_get_conversations_empty(client: AsyncClient, user_headers):
    response = await client.get("/llm/conversations", headers=user_headers)
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_single_conversation(client: AsyncClient, user_headers):
    # Create a conversation
    post_response = await client.post("/llm/conversations", json={"title": "Conversation 1"}, headers=user_headers)
    conv_id = post_response.json()["conversation_id"]

    # Retrieve Conversation
    get_response = await client.get(f"/llm/conversations/{conv_id}", headers=user_headers)
    assert get_response.status_code == 200
    assert get_response.json()["conversation_id"] == conv_id
    assert get_response.json()["title"] == "Conversation 1"

@pytest.mark.asyncio
async def test_get_single_conversation_unauthorized(client: AsyncClient, user_headers):
    # Create user1 conversation
    response = await client.post("/llm/conversations", json={"title": "Conversation 2"}, headers=user_headers)
    conv_id = response.json()["conversation_id"]

    response2 = await client.post(
        "/auth/register", json={"username": "otheruser", "password": "pass", "onc_token": "abcdlmnop"}
    )
    token2 = response2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User2 tries to access user1's conversation
    response = await client.get(f"/llm/conversations/{conv_id}", headers=headers2)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_generate_and_retrieve_message(client: AsyncClient, user_headers, create_conversation):
    conv_id = await create_conversation("Chatting")
    payload = {"input": "Hello ChatBot", "conversation_id": conv_id}
    resp = await client.post(
        "/llm/messages",
        json=payload,
        headers=user_headers
    )
    assert resp.status_code == status.HTTP_201_CREATED
    msg = resp.json()
    assert msg["input"] == payload["input"]
    assert "LLM Response for" in msg["response"]

    # Retrieve the same message
    get_resp = await client.get(
        f"/llm/messages/{msg['message_id']}",
        headers=user_headers
    )
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["message_id"] == msg["message_id"]

@pytest.mark.asyncio
async def test_feedback_create_and_update(client: AsyncClient, user_headers, create_conversation):
    conv_id = await create_conversation("Feedback Test")
    msg = (await client.post(
        "/llm/messages",
        json={"input": "Test?", "conversation_id": conv_id},
        headers=user_headers
    )).json()

    # Create feedback
    fb1 = {"rating": 5, "comment": "Great response!"}
    resp1 = await client.patch(
        f"/llm/messages/{msg['message_id']}/feedback",
        json=fb1,
        headers=user_headers
    )
    assert resp1.status_code == status.HTTP_200_OK

    # Update feedback
    fb2 = {"rating": 1, "comment": "Actually not helpful."}
    resp2 = await client.patch(
        f"/llm/messages/{msg['message_id']}/feedback",
        json=fb2,
        headers=user_headers
    )
    assert resp2.status_code == status.HTTP_200_OK
