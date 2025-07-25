from typing import List

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from LLM.core import LLM
from LLM.schemas import ObtainedParamsDictionary, RunConversationResponse
from src.admin.service import increment_usage
from src.auth.schemas import UserOut

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
from .utils import get_context, get_llm

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
        previous_vdb_ids=[],  # New conversation has no vdb ids yet
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


async def populate_message_from_response(
    llm_response: RunConversationResponse, message: MessageModel, db: AsyncSession
) -> None:
    message.response = llm_response.response

    if llm_response.citation:
        message.citation = llm_response.citation

    if llm_response.baseUrl:
        onc_api_url = llm_response.baseUrl
        url_params = llm_response.urlParamsUsed or {}

        # LLM code is always adding ? to end of base url
        onc_api_url += "?" if not onc_api_url.endswith("?") else ""
        onc_api_url += "&".join([f"{key}={value}" for key, value in url_params.items()])

        message.onc_api_url = onc_api_url

    if llm_response.dpRequestId:
        message.request_id = llm_response.dpRequestId

    # Handle incrementing usage if sources are present
    if llm_response.sources:
        await increment_usage(llm_response.sources, db)
        message.sources = llm_response.sources


async def generate_response(
    llm_query: CreateLLMQuery,
    current_user: UserOut,
    db: AsyncSession,
    request: Request,
) -> Message:
    """Validate user creating new Message that will be sent to LLM"""

    # Verify conversation exists
    conversation_result = await db.execute(
        select(ConversationModel).where(
            ConversationModel.user_id == current_user.id,
            ConversationModel.conversation_id == llm_query.conversation_id,
        )
    )
    existing_conversation = conversation_result.scalar_one_or_none()
    if not existing_conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch up to MAX_CONTEXT_WORDS of prior messages for context
    chat_history = await get_context(
        conversation_id=llm_query.conversation_id,
        max_words=MAX_CONTEXT_WORDS,
        db=db,
    )

    # Create Message to send to LLM
    message = MessageModel(
        conversation_id=llm_query.conversation_id,
        user_id=current_user.id,
        input=llm_query.input,
        response="",
    )

    # Call LLM to generate response
    try:
        # Lazy Initialize the LLM (for first call)
        llm: LLM = get_llm(request.app)
        llm_result: RunConversationResponse = await llm.run_conversation(
            user_prompt=llm_query.input,
            chat_history=chat_history,
            user_onc_token=current_user.onc_token,
            obtained_params=ObtainedParamsDictionary(
                **existing_conversation.obtained_params
            ),
            previous_vdb_ids=existing_conversation.previous_vdb_ids,
        )

        await populate_message_from_response(llm_result, message, db)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating response from LLM: {str(e)}"
        )

    existing_conversation.obtained_params = llm_result.obtainedParams.model_dump()
    if llm_result.point_ids:
        existing_conversation.previous_vdb_ids = [
            llm_result.point_ids[0]
        ]  # Gets most relevant point

    db.add(message)
    await db.commit()

    await db.refresh(message)
    await db.refresh(existing_conversation)
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
