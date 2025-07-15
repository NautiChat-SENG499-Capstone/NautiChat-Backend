import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User
from src.llm.models import Conversation, Message
from src.llm.utils import get_context
from src.settings import get_settings


class TestConversationEndpoints:
    async def _create_conversation(
        self, client: AsyncClient, headers: dict, title: str = "Test"
    ):
        resp = await client.post(
            "/llm/conversations", json={"title": title}, headers=headers
        )

        assert resp.status_code == status.HTTP_201_CREATED
        return resp.json()

    @pytest.mark.asyncio
    async def test_create_conversation(self, client, user_headers):
        body = await self._create_conversation(client, user_headers)

        assert body["title"] == "Test"
        assert isinstance(body["conversation_id"], int)

    @pytest.mark.asyncio
    async def test_get_conversations_empty(self, client, user_headers):
        resp = await client.get("/llm/conversations", headers=user_headers)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_get_conversation_success(self, client, user_headers):
        body = await self._create_conversation(client, user_headers, title="C1")
        conv_id = body["conversation_id"]
        resp = await client.get(f"/llm/conversations/{conv_id}", headers=user_headers)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["conversation_id"] == conv_id

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, client, user_headers):
        resp = await client.get("/llm/conversations/9999", headers=user_headers)

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_conversation_unauthorized(self, client, user_headers):
        body = await self._create_conversation(client, user_headers, title="Private")
        conv_id = body["conversation_id"]

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


class TestDeleteConversation:
    async def _create_conversation(
        self, client: AsyncClient, headers: dict, title: str = "ToDelete"
    ) -> int:
        resp = await client.post(
            "/llm/conversations", json={"title": title}, headers=headers
        )
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.json()["conversation_id"]

    @pytest.mark.asyncio
    async def test_delete_conversation_success(self, client, user_headers):
        conv_id = await self._create_conversation(client, user_headers)

        delete_resp = await client.delete(
            f"/llm/conversations/{conv_id}", headers=user_headers
        )
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

        get_resp = await client.get(
            f"/llm/conversations/{conv_id}", headers=user_headers
        )
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_conversation_unauthorized(self, client, user_headers):
        conv_id = await self._create_conversation(client, user_headers)

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


class TestMessageEndpoints:
    async def _create_conversation(self, client, headers):
        body = await client.post(
            "/llm/conversations", json={"title": "Chat"}, headers=headers
        )
        return body.json()["conversation_id"]

    @pytest.mark.asyncio
    async def test_generate_and_retrieve_message(self, client, user_headers):
        conv_id = await self._create_conversation(client, user_headers)

        msg = (
            await client.post(
                "/llm/messages",
                json={"input": "Hi", "conversation_id": conv_id},
                headers=user_headers,
            )
        ).json()
        assert "LLM Response for" in msg["response"]

        got = await client.get(
            f"/llm/messages/{msg['message_id']}", headers=user_headers
        )
        assert got.status_code == status.HTTP_200_OK
        assert got.json()["message_id"] == msg["message_id"]


class TestFeedback:
    async def _get_message_id(self, client, headers):
        resp = await client.post(
            "/llm/conversations", json={"title": "FB"}, headers=headers
        )
        conv_id = resp.json()["conversation_id"]

        result = await client.post(
            "/llm/messages",
            json={"input": "Feedback?", "conversation_id": conv_id},
            headers=headers,
        )
        return result.json()["message_id"]

    @pytest.mark.asyncio
    async def test_feedback_create_and_update(self, client, user_headers):
        msg_id = await self._get_message_id(client, user_headers)

        for rating in [5, 2]:
            resp = await client.patch(
                f"/llm/messages/{msg_id}/feedback",
                json={"rating", rating},
                headers=user_headers,
            )
            assert resp.status_code == status.HTTP_200_OK


class TestContextUtils:
    @pytest.mark.asyncio
    async def test_get_context_no_messages(
        self, async_session: AsyncSession, _user_headers
    ):
        # When no messages in db, should return empty list

        # Add conversation
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
        await async_session.refresh(new_conversation)

    @pytest.mark.asyncio
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
            conversation_id=new_conversation.conversation_id,
            user_id=user_in_db.id,
            input=content_8,
            response=content_8,
        )  # 4 + 8 + 8 = 20 words
        message_15 = Message(
            conversation_id=new_conversation.conversation_id,
            user_id=user_in_db.id,
            input=content_8,
            response=content_3,
        )  # 4 + 8 + 3 = 15 words

        async_session.add(message_20)
        async_session.add(message_15)
        await async_session.commit()
        await async_session.refresh(message_20)
        await async_session.refresh(message_15)
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
        assert context_2[0]["content"] == message_15.input
        assert context_2[1]["role"] == "system"
        assert context_2[1]["content"] == message_15.response
