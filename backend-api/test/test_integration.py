import pytest
from fastapi import FastAPI, HTTPException, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.schemas import CreateUserRequest
from src.llm.models import Conversation
from src.llm.schemas import CreateLLMQuery
from src.llm.utils import get_context, get_llm
from src.settings import get_settings

from LLM.Constants.status_codes import StatusCode
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse


class TestGenerateMessageActualLLM:
    async def _create_conversation(
        self, client: AsyncClient, headers: dict, title: str = "Chat"
    ) -> int:
        """Helper to create a conversation and return its ID"""
        resp = await client.post(
            "/llm/conversations", json={"title": title}, headers=headers
        )
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.json()["conversation_id"]

    # @pytest.mark.asyncio
    # @pytest.mark.use_lifespan
    # @pytest.mark.use_real_llm
    # async def test_generate_message_with_real_llm(
    #     self, client: AsyncClient, user_headers: dict, async_session: AsyncSession
    # ):
    #     """Test that sends a real LLM query and verifies the flow end-to-end"""
    #     conv_id = await self._create_conversation(client, user_headers)

    #     # Post to LLM
    #     resp = await client.post(
    #         "/llm/messages",
    #         json={"input": "What is the temperature at Cambridge Bay?", "conversation_id": conv_id},
    #         headers=user_headers,
    #     )

    #     assert resp.status_code == 201
    #     message = resp.json()

    #     #Makes sure message comes back with call from actual LLM
    #     assert "response" in message and isinstance(message["response"], str) and len(message["response"]) > 0
    #     assert "conversation_id" in message
    #     assert "message_id" in message
    #     assert isinstance(message["message_id"], int)

    #     message_id = message["message_id"]
    #     get_resp = await client.get(f"/llm/messages/{message_id}", headers=user_headers)
    #     assert get_resp.status_code == 200
    #     msg = get_resp.json()
    #     assert msg["input"] == "What is the temperature at Cambridge Bay?"
    #     assert msg["response"] == message["response"]


class TestRunConversation:
    async def _create_conversation(
        self,
        client: AsyncClient,
        headers: dict,
    ) -> Conversation:
        """Helper to create a conversation"""
        resp = await client.post(
            "/llm/conversations", json={"title": "Chat"}, headers=headers
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        conversation = Conversation(**data)
        return conversation

    def _create_llm_query(self, conv_id: int, query: str) -> CreateLLMQuery:
        """Helper to Create an LLM query"""
        llm_query = CreateLLMQuery(input=query, conversation_id=conv_id)
        return llm_query

    async def _call_llm(self, app: FastAPI, prompt: str, chat_history=[], params=None):
        llm = get_llm(app)
        return await llm.run_conversation(
            user_prompt=prompt,
            chat_history=chat_history,
            user_onc_token=get_settings().ONC_TOKEN,
            obtained_params=params,
        )

    @pytest.mark.asyncio
    @pytest.mark.use_lifespan
    @pytest.mark.use_real_llm
    async def test_regular_message(
        self, client: AsyncClient, user_headers: dict, async_session: AsyncSession
    ):
        """Get regular message from LLM - NO Chat History"""

        conversation = await self._create_conversation(client, user_headers)

        llm_query = self._create_llm_query(
            conversation.conversation_id, "What was the temperature in Cambridge Bay?"
        )
        # Call LLM to generate response
        try:
            llm_result: RunConversationResponse = await self._call_llm(
                client._transport.app,
                llm_query.input,
                [],
                ObtainedParamsDictionary(**conversation.obtained_params),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating response from LLM: {str(e)}"
            )

        assert_valid_llm_response(llm_result)

    @pytest.mark.asyncio
    @pytest.mark.use_lifespan
    @pytest.mark.use_real_llm
    async def test_params_needed(
        self, client: AsyncClient, user_headers: dict, async_session: AsyncSession
    ):
        """Get response that requests for more params - NO Chat History"""

        conversation = await self._create_conversation(client, user_headers)

        llm_query = self._create_llm_query(
            conversation.conversation_id, "i want scalar FLUOROMETER data"
        )
        # Call LLM to generate response
        try:
            llm_result: RunConversationResponse = await self._call_llm(
                client._transport.app,
                llm_query.input,
                [],
                ObtainedParamsDictionary(**conversation.obtained_params),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating response from LLM: {str(e)}"
            )

        assert_valid_llm_response(llm_result)

        llm_query = self._create_llm_query(
            conversation.conversation_id,
            "i want scalar FLUOROMETER data from Cambridge Bay, from august 15th 2015 to august 16th 2015",
        )
        # Call LLM to generate response
        try:
            llm_result: RunConversationResponse = await self._call_llm(
                client._transport.app,
                llm_query.input,
                [],
                ObtainedParamsDictionary(**conversation.obtained_params),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating response from LLM: {str(e)}"
            )

        assert_valid_llm_response(llm_result)

    @pytest.mark.asyncio
    @pytest.mark.use_lifespan
    @pytest.mark.use_real_llm
    async def test_download_data(
        self, client: AsyncClient, user_headers: dict, async_session: AsyncSession
    ):
        """Get download request id - NO Chat History"""

        conversation = await self._create_conversation(client, user_headers)

        llm_query = self._create_llm_query(
            conversation.conversation_id,
            "I want to download dive computer data as a LF in txt from August 20th 2015",
        )
        # Call LLM to generate response
        try:
            llm_result: RunConversationResponse = await self._call_llm(
                client._transport.app,
                llm_query.input,
                [],
                ObtainedParamsDictionary(**conversation.obtained_params),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating response from LLM: {str(e)}"
            )

        assert_valid_llm_response(llm_result)
        print(llm_result)


class TestMockLLM:
    async def _create_user_and_login(
        self, client: AsyncClient, username="multiuser", password="multipass"
    ):
        user_data = CreateUserRequest(
            username=username, password=password, onc_token=get_settings().ONC_TOKEN
        )
        # Register
        await client.post("/auth/register", json=user_data.model_dump())
        # Login
        response = await client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == status.HTTP_200_OK
        access_token = response.json()["access_token"]
        return {"Authorization": f"Bearer {access_token}"}

    async def _create_conversation(
        self, client: AsyncClient, headers: dict, title: str
    ) -> int:
        response = await client.post(
            "/llm/conversations", json={"title": title}, headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["conversation_id"]

    async def _send_message(
        self,
        client: AsyncClient,
        headers: dict,
        conversation_id: int,
        message_input: str,
    ):
        resp = await client.post(
            "/llm/messages",
            json={"input": message_input, "conversation_id": conversation_id},
            headers=headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        return resp.json()

    @pytest.mark.asyncio
    async def test_multi_conversation_context_flow(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        # Register + login
        user_headers = await self._create_user_and_login(client)

        # Create conversation 1
        conv1_id = await self._create_conversation(
            client, user_headers, title="First Chat"
        )
        await self._send_message(client, user_headers, conv1_id, "Hello, how are you?")
        await self._send_message(
            client, user_headers, conv1_id, "What does ONC stand for?"
        )

        # Create conversation 2
        conv2_id = await self._create_conversation(
            client, user_headers, title="Second Chat"
        )
        await self._send_message(
            client,
            user_headers,
            conv2_id,
            "What tools are used to capture sound underwater?",
        )

        # Back to conv1
        await self._send_message(client, user_headers, conv1_id, "Tell me about ONC.")

        # Confirm messages are returned correctly from get_context
        context = await get_context(conv1_id, max_words=150, db=async_session)

        # Check that context returns user + system pairs and order is preserved
        assert len(context) >= 4, "Expected at least 2 message pairs in context"
        assert context[0]["role"] == "user"
        assert any("onc" in msg["content"].lower().strip() for msg in context)

        # Ensure messages from conv2 are not included
        context_conv2 = await get_context(conv2_id, max_words=150, db=async_session)
        assert all("ONC" not in msg["content"].lower() for msg in context_conv2)

    @pytest.mark.asyncio
    async def test_download_scalar_data_returns_dp_request_id(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        user_headers = await self._create_user_and_login(client)
        conv_id = await self._create_conversation(
            client, user_headers, title="Download Test"
        )

        # Send a message that should trigger a "download" tool call
        response_json = await self._send_message(
            client,
            user_headers,
            conv_id,
            "Can you download scalar data for sensor 123 since 2020-01-01?",
        )

        # The backend should have returned a response JSON that includes a dpRequestId
        assert "request_id" in response_json, "dp_request_id not found in response"
        assert isinstance(response_json["request_id"], int), (
            "dp_request_id should be an integer"
        )
        assert response_json["request_id"] > 0, "dp_request_id should be positive"

    @pytest.mark.asyncio
    async def test_params_needed_for_download(
        self, client: AsyncClient, async_session: AsyncSession
    ):
        user_headers = await self._create_user_and_login(client)
        conv_id = await self._create_conversation(
            client, user_headers, title="Download Test - Params Needed"
        )

        # Send a message that should trigger a "download" tool call
        response_json = await self._send_message(
            client, user_headers, conv_id, "Can you download something?"
        )

        assert "response" in response_json, "Response key missing in response"
        assert len(response_json["response"]) > 0, "Response message is empty"


# HELPER FUNCTION
def assert_valid_llm_response(response: RunConversationResponse):
    """Asserts that a RunConversationResponse is structured and consistent for its status."""

    assert isinstance(response, RunConversationResponse), "Invalid response type"
    assert isinstance(response.status, StatusCode), "Status must be a valid StatusCode"

    # Response string
    assert isinstance(response.response, str), "Response must be a string"
    assert response.response.strip(), "Response text should not be empty"

    # Always a valid obtainedParams object, even if empty
    assert isinstance(response.obtainedParams, ObtainedParamsDictionary)

    # Status-specific checks
    if response.status == StatusCode.REGULAR_MESSAGE:
        assert isinstance(response.sources, list)
        assert all(isinstance(src, str) for src in response.sources), (
            "Sources must be a list of strings"
        )
        # Optional fields: urlParamsUsed, baseUrl — not strictly required

    elif response.status == StatusCode.PROCESSING_DATA_DOWNLOAD:
        assert response.dpRequestId is not None, "Missing dpRequestId for download"
        assert response.doi is not None, "Missing DOI for download"
        assert response.citation is not None, "Missing citation for download"
        assert isinstance(response.baseUrl, str)
        assert response.baseUrl.startswith("http")
        assert isinstance(response.urlParamsUsed, dict)

    elif response.status == StatusCode.PARAMS_NEEDED:
        assert any(
            [
                response.obtainedParams.locationCode,
                response.obtainedParams.deviceCategoryCode,
                response.obtainedParams.dataProductCode,
                response.obtainedParams.propertyCode,
            ]
        ), "At least one param should be present when PARAMS_NEEDED"

    elif response.status in {
        StatusCode.ERROR_WITH_DATA_DOWNLOAD,
        StatusCode.SCALAR_REQUEST_ERROR,
        StatusCode.DEPLOYMENT_ERROR,
        StatusCode.NO_DATA,
    }:
        assert isinstance(response.response, str)
        assert isinstance(response.urlParamsUsed, dict)
        assert isinstance(response.baseUrl, str)

    elif response.status == StatusCode.LLM_ERROR:
        assert (
            "failed" in response.response.lower()
            or "error" in response.response.lower()
        )

    else:
        raise AssertionError(f"Unhandled LLM status: {response.status}")
