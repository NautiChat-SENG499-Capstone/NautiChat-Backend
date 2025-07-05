import asyncio
from typing import List

import httpx
from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.schemas import UserOut
from src.logger import logger

from .models import Conversation as ConversationModel
from .models import Feedback as FeedbackModel
from .models import Message as MessageModel
from .schemas import (
    Conversation,
    CreateConversationBody,
    CreateLLMQuery,
    Feedback,
    Message,
)
from .utils import get_context

MAX_CONTEXT_WORDS = 200


async def create_conversation(
    current_user: UserOut,
    db: AsyncSession,
    create_conversation: CreateConversationBody,
) -> Conversation:
    """Create a conversation and store in db"""
    conversation = ConversationModel(
        user_id=current_user.id, title=create_conversation.title
    )

    # Add conversation to DB
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Convert to Pydantic schema manually
    return Conversation(
        conversation_id=conversation.conversation_id,
        user_id=conversation.user_id,
        title=conversation.title,
        messages=[],  # New conversation has no messages yet
    )


async def get_conversations(
    current_user: UserOut,
    db: AsyncSession,
) -> List[Conversation]:
    """Get all conversations (of the user)"""
    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
    query = stmt.where(ConversationModel.user_id == current_user.id).order_by(
        ConversationModel.conversation_id.desc()
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_conversation(
    conversation_id: int,
    current_user: UserOut,
    db: AsyncSession,
) -> Conversation:
    """Get a single conversation given a conv_id (of the user)"""
    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
    query = stmt.where(ConversationModel.user_id == current_user.id).where(
        ConversationModel.conversation_id == conversation_id
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


async def delete_conversation(
    conversation_id: int,
    current_user: UserOut,
    db: AsyncSession,
):
    """Given conv_id (of the user), delete conversation"""
    query = select(ConversationModel).where(
        ConversationModel.user_id == current_user.id,
        ConversationModel.conversation_id == conversation_id,
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Don't have to worry about deleting messages
    # Because conversation model has cascading message deletion
    await db.delete(conversation)
    await db.commit()


async def get_data_download_link(request_id: str, onc_token: str) -> str:
    """Get a download link for the data associated with a request_id"""

    # Run the data download request
    async with httpx.AsyncClient() as client:
        for _ in range(10):
            url = f"https://data.oceannetworks.ca/api/dataProductDelivery/run?dpRequestId={request_id}&token={onc_token}"
            response = await client.get(url)
            data = response.json()[0]
            logger.info(response)
            logger.info(data)
            if "status" in data and data["status"] == "complete":
                # the request is complete, return the formed download link
                run_id = data["dpRunId"]

                # currently hardcoded (will download the first file available. there might be more than 1)
                index = 1
                return f"https://data.oceannetworks.ca/api/dataProductDelivery/download?dpRunId={run_id}&index={index}&token={onc_token}"
            else:
                await asyncio.sleep(2)
        # raise exception if we timeout in the range
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get download link for request_id {request_id}",
        )


async def generate_response(
    llm_query: CreateLLMQuery,
    current_user: UserOut,
    db: AsyncSession,
    request: Request,
) -> Message:
    """Validate user creating new Message that will be sent to LLM"""
    # Ensure LLM and RAG are initialized
    state = request.app.state
    if not state.llm or not state.rag:
        raise HTTPException(status_code=500, detail="LLM/RAG not initialized")

    # Verify conversation exists
    exists = await db.scalar(
        select(ConversationModel.conversation_id)
        .where(
            ConversationModel.user_id == current_user.id,
            ConversationModel.conversation_id == llm_query.conversation_id,
        )
        .limit(1)
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch up to MAX_CONTEXT_WORDS of prior messages for context
    try:
        chat_history = await get_context(
            conversation_id=llm_query.conversation_id,
            max_words=MAX_CONTEXT_WORDS,
            db=db,
        )
    except AssertionError:
        raise HTTPException(status_code=404, detail="Invalid conversation id")

    # Create Message to send to LLM
    message = MessageModel(
        conversation_id=llm_query.conversation_id,
        user_id=current_user.id,
        input=llm_query.input,
        response="",
    )

    # Call LLM to generate response
    try:
        response: dict = await state.llm.run_conversation(
            user_prompt=llm_query.input,
            startingPrompt=None,
            chatHistory=chat_history,
            user_onc_token=current_user.onc_token,
        )

        message.response = response["response"]
        # Handle queueing data download
        if "dpRequestId" in response:
            logger.info(
                f"Got a data product request id back from LLM {response['dpRequestId']['dpRequestId']}"
            )
            request_id = response["dpRequestId"]["dpRequestId"]
            message.request_id = request_id
            # Right now, backend is just waiting until the download is ready so we can return direct link to frontend
            # A better way would be for the request_id to be returned to frontend directly and they poll onc for the download link
            message.download_link = await get_data_download_link(
                request_id, current_user.onc_token
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating response from LLM: {str(e)}"
        )

    # Add message to DB
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_message(
    message_id: int,
    current_user: UserOut,
    db: AsyncSession,
) -> Message:
    """Get a single message given a message_id"""
    # TODO: Must check if message belongs to current user
    query = select(MessageModel).where(MessageModel.message_id == message_id)
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this message"
        )

    return message


async def submit_feedback(
    message_id: int,
    feedback: Feedback,
    current_user: UserOut,
    db: AsyncSession,
) -> Message:
    """Create Feedback entry for Message (or update current Feedback)"""
    # TODO: Check that message belongs to current user
    # Validate whether message exists or if current user has access to message
    query = select(MessageModel).where(MessageModel.message_id == message_id)
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message or message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Invalid message access")

    # Check if feedback exists for this message
    result = await db.execute(
        select(FeedbackModel).where(FeedbackModel.message_id == message_id)
    )
    existing_feedback = result.scalar_one_or_none()

    if existing_feedback:
        # Update only fields that are provided in the request
        update_data = feedback.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400, detail="At least one feedback field must be provided."
            )

        # Update feedback model with new data
        for key, value in update_data.items():
            setattr(existing_feedback, key, value)
    else:
        # Create new feedback entry
        new_feedback = FeedbackModel(message_id=message_id, **feedback.model_dump())
        db.add(new_feedback)

    await db.commit()
    await db.refresh(message)
    return message
