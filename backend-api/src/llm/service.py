
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from typing import List

from src.auth.schemas import UserOut
from .schemas import Conversation, Message, Feedback, CreateLLMQuery, CreateConversationBody
from .models import Conversation as ConversationModel, Message as MessageModel, Feedback as FeedbackModel

async def create_conversation(
    current_user: UserOut,
    db: AsyncSession,
    CreateConversationBody: CreateConversationBody,
) -> Conversation:
    conversation = ConversationModel(user_id=current_user.id, title=CreateConversationBody.title)
    
    # Add conversation to DB
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Convert to Pydantic schema manually (Avoid Lazy Loading ERROR)
    return Conversation(
        conversation_id=conversation.conversation_id,
        user_id=conversation.user_id,
        title=conversation.title,
        messages=[]  # New conversation has no messages yet
    )

async def get_conversations(
    current_user: UserOut,
    db: AsyncSession,
) -> List[Conversation]:
    # Async db query
    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
    query = stmt.where(ConversationModel.user_id == current_user.id).order_by(ConversationModel.conversation_id.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_conversation(
    conversation_id: int,
    current_user: UserOut,
    db: AsyncSession,
) -> Conversation:
    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
    query = stmt.where(ConversationModel.user_id == current_user.id).where(ConversationModel.conversation_id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation

async def generate_response(
    LLMQuery: CreateLLMQuery,
    current_user: UserOut,
    db: AsyncSession,
) -> Message:  
    # Validate whether converstation exists or if current user has access to conversation
    result = await db.execute(select(ConversationModel).where(ConversationModel.conversation_id == LLMQuery.conversation_id))
    conversation = result.scalar_one_or_none()

    if not conversation: 
        raise HTTPException(
            status_code=404, 
            detail="Conversation not found"
        )
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to access this conversation"
        )

    # Create Message to send to LLM  
    message = MessageModel(
        conversation_id=LLMQuery.conversation_id, 
        user_id=current_user.id, 
        input=LLMQuery.input, 
        response=f"LLM Response for: {LLMQuery.input}"
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
    query = select(MessageModel).where(MessageModel.message_id == message_id)
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this message")
    
    return message

async def submit_feedback(
    message_id: int,
    feedback: Feedback,
    current_user: UserOut,
    db: AsyncSession,
) -> Message:
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
            raise HTTPException(status_code=400, detail="At least one feedback field must be provided.")
        
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