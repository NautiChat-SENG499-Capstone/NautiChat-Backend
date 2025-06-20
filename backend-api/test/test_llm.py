import pytest
from httpx import AsyncClient
from fastapi import status
from src.main import app

# Dummy LLM and RAG services for tests
class DummyLLM:
    async def run_conversation(self, user_prompt, startingPrompt, chatHistory, user_onc_token=None):
        return f"LLM Response for {user_prompt}"

class DummyRAG:
    pass

@pytest.fixture(autouse=True)
def stub_services():
    # Inject dummy services into FastAPI app state
    app.state.llm = DummyLLM()
    app.state.rag = DummyRAG()

@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, user_headers):
    post = await client.post(
        "/llm/conversations",
        json={"title": "Test Conversation"},
        headers=user_headers
    )
    assert post.status_code == status.HTTP_201_CREATED
    data = post.json()
    assert data["title"] == "Test Conversation"
    assert isinstance(data["conversation_id"], int)

@pytest.mark.asyncio
async def test_get_conversations_empty(client: AsyncClient, user_headers):
    get = await client.get(
        "/llm/conversations",
        headers=user_headers
    )
    assert get.status_code == status.HTTP_200_OK
    assert get.json() == []

@pytest.mark.asyncio
async def test_get_conversation_success(client: AsyncClient, user_headers):
    post = await client.post(
        "/llm/conversations",
        json={"title": "Conversation 1"},
        headers=user_headers
    )
    assert post.status_code == status.HTTP_201_CREATED
    conv_id = post.json()["conversation_id"]

    get = await client.get(
        f"/llm/conversations/{conv_id}",
        headers=user_headers
    )
    assert get.status_code == status.HTTP_200_OK
    data = get.json()
    assert data["conversation_id"] == conv_id
    assert data["title"] == "Conversation 1"

@pytest.mark.asyncio
async def test_get_conversation_not_found(client: AsyncClient, user_headers):
    get = await client.get(
        "/llm/conversations/9999",
        headers=user_headers
    )
    assert get.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_get_conversation_unauthorized(client: AsyncClient, user_headers):
    post = await client.post(
        "/llm/conversations",
        json={"title": "Private Conv"},
        headers=user_headers
    )
    conv_id = post.json()["conversation_id"]

    reg = await client.post(
        "/auth/register",
        json={"username": "otheruser", "password": "pass", "onc_token": "tok"}
    )
    token2 = reg.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    get = await client.get(
        f"/llm/conversations/{conv_id}",
        headers=headers2
    )
    assert get.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_generate_and_retrieve_message(client: AsyncClient, user_headers):
    post_conv = await client.post(
        "/llm/conversations",
        json={"title": "Chatting"},
        headers=user_headers
    )
    conv_id = post_conv.json()["conversation_id"]

    post_msg = await client.post(
        "/llm/messages",
        json={"input": "Hello ChatBot", "conversation_id": conv_id},
        headers=user_headers
    )
    assert post_msg.status_code == status.HTTP_201_CREATED
    msg = post_msg.json()
    assert msg["input"] == "Hello ChatBot"
    assert "LLM Response for" in msg["response"]

    get_msg = await client.get(
        f"/llm/messages/{msg['message_id']}",
        headers=user_headers
    )
    assert get_msg.status_code == status.HTTP_200_OK
    assert get_msg.json()["message_id"] == msg["message_id"]

@pytest.mark.asyncio
async def test_feedback_create_and_update(client: AsyncClient, user_headers):
    post_conv = await client.post(
        "/llm/conversations",
        json={"title": "Feedback Test"},
        headers=user_headers
    )
    conv_id = post_conv.json()["conversation_id"]

    post_msg = await client.post(
        "/llm/messages",
        json={"input": "Testing feedback?", "conversation_id": conv_id},
        headers=user_headers
    )
    msg = post_msg.json()

    create_fb = await client.patch(
        f"/llm/messages/{msg['message_id']}/feedback",
        json={"rating": 5, "comment": "Great response!"},
        headers=user_headers
    )
    assert create_fb.status_code == status.HTTP_200_OK

    update_fb = await client.patch(
        f"/llm/messages/{msg['message_id']}/feedback",
        json={"rating": 2, "comment": "Needs improvement."},
        headers=user_headers
    )
    assert update_fb.status_code == status.HTTP_200_OK
