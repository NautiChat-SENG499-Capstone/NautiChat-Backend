import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User
from src.llm import schemas
from src.llm.models import Conversation, Message
from src.llm.utils import get_context
from src.settings import get_settings


class TestConversation:
    async def _create_conversation(
        self, client: AsyncClient, headers: dict, title: str = "Test"
    ) -> schemas.Conversation:
        """Helper to create a conversation"""
        resp = await client.post(
            "/llm/conversations", json={"title": title}, headers=headers
        )

        assert resp.status_code == status.HTTP_201_CREATED
        return schemas.Conversation.model_validate(resp.json())

    # ----------CREATE----------
    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient, user_headers: dict):
        """Test that creates a conversation using _create_conversation()"""
        conv = await self._create_conversation(client, user_headers)
        assert conv.title == "Test"
        assert isinstance(conv.conversation_id, int)

    @pytest.mark.asyncio
    async def test_create_conversation_missing_title(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that creates a conversation without a title"""
        resp = await client.post("/llm/conversations", json={}, headers=user_headers)
        assert resp.status_code == status.HTTP_201_CREATED

    # ----------GET LIST----------
    @pytest.mark.asyncio
    async def test_get_conversations_empty(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test where a user with no conversation gets an empty list response"""
        conv = await client.get("/llm/conversations", headers=user_headers)
        assert conv.status_code == status.HTTP_200_OK
        assert conv.json() == []

    @pytest.mark.asyncio
    async def test_get_conversations_multiple_descending(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that returns multple conversations"""
        titles = ["First", "Second", "Third"]
        for title in titles:
            await self._create_conversation(client, user_headers, title=title)

        resp = await client.get("/llm/conversations", headers=user_headers)
        assert resp.status_code == 200
        convs = [schemas.Conversation.model_validate(obj) for obj in resp.json()]
        titles_returned = [conv.title for conv in convs]
        assert set(titles_returned) == {"First", "Second", "Third"}

    # ----------GET BY ID----------
    @pytest.mark.asyncio
    async def test_get_conversation_by_id(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that gets an existing conversation from a user"""
        conv = await self._create_conversation(client, user_headers)
        conv_id = conv.conversation_id
        resp = await client.get(f"/llm/conversations/{conv_id}", headers=user_headers)

        assert resp.status_code == status.HTTP_200_OK
        data = schemas.Conversation.model_validate(resp.json())
        assert data.conversation_id == conv_id
        assert data.title == conv.title

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client: AsyncClient, user_headers):
        """Test that tries to get a conversation that doesn't exist"""
        resp = await client.get("/llm/conversations/9999", headers=user_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_conversation_invalid_id(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that attempts to get conversation with invalid id"""
        resp = await client.get("/llm/conversations/invalid", headers=user_headers)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_conversation_unauthorized_access(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that attempts to get a conversation that doesn't belong to user"""

        conv = await self._create_conversation(client, user_headers, title="Private")
        conv_id = conv.conversation_id

        # Register a new user
        reg = await client.post(
            "/auth/register",
            json={
                "username": "x",
                "password": "p",
                "onc_token": get_settings().ONC_TOKEN,
            },
        )
        headers2 = {"Authorization": f"Bearer {reg.json()['access_token']}"}

        resp = await client.get(f"/llm/conversations/{conv_id}", headers=headers2)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    # ----------DELETE----------
    @pytest.mark.asyncio
    async def test_delete_conversation_success(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that deletes a conversation of a user"""
        conv = await self._create_conversation(client, user_headers)
        conv_id = conv.conversation_id

        delete_resp = await client.delete(
            f"/llm/conversations/{conv_id}", headers=user_headers
        )
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

        get_resp = await client.get(
            f"/llm/conversations/{conv_id}", headers=user_headers
        )
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_conversation_unauthorized(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that attempts to delete someoneelse's conversation"""
        conv = await self._create_conversation(client, user_headers)
        conv_id = conv.conversation_id

        # Register new user
        reg = await client.post(
            "/auth/register",
            json={
                "username": "someoneelse",
                "password": "1234",
                "onc_token": get_settings().ONC_TOKEN,
            },
        )

        other_token = reg.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        delete_resp = await client.delete(
            f"/llm/conversations/{conv_id}", headers=other_headers
        )
        assert delete_resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_conversation_not_found(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that attempts to delete a non-existing conversation"""
        resp = await client.delete("/llm/conversations/9999", headers=user_headers)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    # ----------AUTH----------
    @pytest.mark.asyncio
    async def test_get_conversations_unauthenticated(self, client: AsyncClient):
        """Test that attempts to get conversation of unauthenticated user"""
        resp = await client.get("/llm/conversations")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_conversation_unauthenticated(self, client: AsyncClient):
        """Test that attempts to create conversation of unauthenticated user"""
        resp = await client.post("/llm/conversations", json={"title": "NoAuth"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_delete_conversation_unauthenticated(self, client: AsyncClient):
        """Test that attempts to delete conversation of unauthenticated user"""
        resp = await client.delete("/llm/conversations/1")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMessage:
    async def _create_conversation(
        self, client: AsyncClient, headers: dict, title: str = "Chat"
    ) -> int:
        """Helper to create a conversation and return its ID"""
        resp = await client.post(
            "/llm/conversations", json={"title": title}, headers=headers
        )
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.json()["conversation_id"]

    @pytest.mark.asyncio
    async def test_generate_and_retrieve_message(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that generates a message from the mock LLM and retrieves it"""
        conv_id = await self._create_conversation(client, user_headers)

        msg = (
            await client.post(
                "/llm/messages",
                json={"input": "Hi", "conversation_id": conv_id},
                headers=user_headers,
            )
        ).json()

        assert isinstance(msg["response"], str)
        assert len(msg["response"]) > 0
        assert "Hi" in msg["response"]  # checks that input is referenced
        assert isinstance(msg["message_id"], int)

        get_resp = await client.get(
            f"/llm/messages/{msg['message_id']}", headers=user_headers
        )
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["message_id"] == msg["message_id"]

    @pytest.mark.asyncio
    async def test_message_invalid_conversation_id(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test that attempts to generate response with invalid id"""
        resp = await client.post(
            "/llm/messages",
            json={"input": "Hi", "conversation_id": 999},
            headers=user_headers,
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_message_missing_input(self, client: AsyncClient, user_headers: dict):
        """Test that attempts to generate response without input"""
        conv_id = await self._create_conversation(client, user_headers)
        resp = await client.post(
            "/llm/messages",
            json={"conversation_id": conv_id},
            headers=user_headers,
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestFeedback:
    async def _create_message_and_get_message_id(
        self, client: AsyncClient, headers: dict
    ) -> int:
        """Create conversation and message, return message ID"""
        conv_resp = await client.post(
            "/llm/conversations", json={"title": "FB"}, headers=headers
        )
        assert conv_resp.status_code == status.HTTP_201_CREATED
        conv_id = conv_resp.json()["conversation_id"]

        msg_resp = await client.post(
            "/llm/messages",
            json={"input": "Feedback?", "conversation_id": conv_id},
            headers=headers,
        )
        assert msg_resp.status_code == status.HTTP_201_CREATED
        return msg_resp.json()["message_id"]

    @pytest.mark.asyncio
    async def test_feedback_create_and_update(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test creating and updating feedback on a message"""
        msg_id = await self._create_message_and_get_message_id(client, user_headers)

        for rating in [5, 2]:
            resp = await client.patch(
                f"/llm/messages/{msg_id}/feedback",
                json={"rating": rating},
                headers=user_headers,
            )
            assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_feedback_on_nonexistent_message(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test attempts giving feedback on nonexistant message"""
        resp = await client.patch(
            "/llm/messages/999/feedback",
            json={"rating": 4},
            headers=user_headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_feedback_invalid_rating(
        self, client: AsyncClient, user_headers: dict
    ):
        """Test attempts to give feedback outside of acceptable range"""
        msg_id = await self._create_message_and_get_message_id(client, user_headers)

        resp = await client.patch(
            f"/llm/messages/{msg_id}/feedback",
            json={"rating": 100},
            headers=user_headers,
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestContextUtils:
    @pytest.mark.asyncio
    async def test_get_context_no_messages(
        self, async_session: AsyncSession, _user_headers
    ):
        """Test for empty context if no messages in conversation"""
        users = await async_session.execute(select(User))
        user_in_db = users.scalars().first()
        assert user_in_db is not None

        new_conversation = Conversation(user_id=user_in_db.id)
        async_session.add(new_conversation)
        await async_session.commit()
        await async_session.refresh(new_conversation)

        context = await get_context(
            new_conversation.conversation_id, 500, async_session
        )
        assert context == []

    @pytest.mark.asyncio
    async def test_get_context(self, async_session: AsyncSession, _user_headers):
        """Test that grabs context when existing messages exist in conversation"""

        users = await async_session.execute(select(User))
        user_in_db = users.scalars().first()
        assert user_in_db is not None

        new_conversation = Conversation(user_id=user_in_db.id)
        async_session.add(new_conversation)
        await async_session.commit()
        await async_session.refresh(new_conversation)

        # Create two message with varying words
        content_8 = "one two three four five six seven eight"
        content_3 = "one two three"

        message_20_words = Message(
            conversation_id=new_conversation.conversation_id,
            user_id=user_in_db.id,
            input=content_8,
            response=content_8,
        )  # 4 + 8 + 8 = 20 words
        message_15_words = Message(
            conversation_id=new_conversation.conversation_id,
            user_id=user_in_db.id,
            input=content_8,
            response=content_3,
        )  # 4 + 8 + 3 = 15 words

        async_session.add_all([message_20_words, message_15_words])
        await async_session.commit()
        await async_session.refresh(message_20_words)
        await async_session.refresh(message_15_words)
        await async_session.refresh(new_conversation)

        context_1 = await get_context(
            new_conversation.conversation_id, 30, async_session
        )
        assert len(context_1) == 2  # 1 for input and 1 for response

        context_2 = await get_context(
            new_conversation.conversation_id, 100, async_session
        )
        assert len(context_2) == 4
        assert isinstance(context_2[0]["role"], str)
        # most recent message should be returned first
        assert context_2[0]["role"] == "user"
        assert context_2[0]["content"] == message_15_words.input
        assert context_2[1]["role"] == "system"
        assert context_2[1]["content"] == message_15_words.response
