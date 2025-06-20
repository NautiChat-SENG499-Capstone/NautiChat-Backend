import pytest
from httpx import AsyncClient
from fastapi import status

# Dummy LLM and RAG services for tests
class DummyLLM:
    async def run_conversation(self, user_prompt, startingPrompt, chatHistory, user_onc_token=None):
        return f"LLM Response for {user_prompt}"

class DummyRAG:
    pass

# Stub services before any client fixture uses them
from src.main import app

@pytest.fixture(autouse=True)
def stub_services():
    # Inject dummy services into FastAPI app state
    app.state.llm = DummyLLM()
    app.state.rag = DummyRAG()

@pytest.fixture
async def create_conversation(client: AsyncClient, user_headers):
    """Helper to create a conversation and return its ID"""
    async def _create(title: str = "Test Conversation") -> int:
        resp = await client.post(
            "/llm/conversations",
            json={"title": title},
            headers=user_headers
        )
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.json()["conversation_id"]
    return _create

@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, user_headers):
    payload = {"title": "Test Conversation"}
    resp = await client.post(
        "/llm/conversations",
        json=payload,
        headers=user_headers
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["title"] == payload["title"]
    assert isinstance(data["conversation_id"], int)

@pytest.mark.asyncio
async def test_get_conversations_empty(client: AsyncClient, user_headers):
    resp = await client.get(
        "/llm/conversations",
        headers=user_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []

@pytest.mark.asyncio
async def test_get_conversation_success(client: AsyncClient, user_headers, create_conversation):
    conv_id = await create_conversation("Conversation 1")
    resp = await client.get(
        f"/llm/conversations/{conv_id}",
        headers=user_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["conversation_id"] == conv_id
    assert data["title"] == "Conversation 1"

@pytest.mark.asyncio
async def test_get_conversation_not_found(client: AsyncClient, user_headers):
    resp = await client.get(
        "/llm/conversations/9999",
        headers=user_headers
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_get_conversation_unauthorized(client: AsyncClient, user_headers, create_conversation):
    conv_id = await create_conversation("Private Conv")
    # Register another user
    r = await client.post(
        "/auth/register",
        json={"username": "otheruser", "password": "pass", "onc_token": "tok"}
    )
    token2 = r.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    resp = await client.get(
        f"/llm/conversations/{conv_id}",
        headers=headers2
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

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
        json={"input": "Testing feedback?", "conversation_id": conv_id},
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
    fb2 = {"rating": 2, "comment": "Needs improvement."}
    resp2 = await client.patch(
        f"/llm/messages/{msg['message_id']}/feedback",
        json=fb2,
        headers=user_headers
    )
    assert resp2.status_code == status.HTTP_200_OK
