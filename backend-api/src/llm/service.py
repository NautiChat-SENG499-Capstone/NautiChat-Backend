from typing import List

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.auth.schemas import UserOut
from .schemas import Conversation, Message, Feedback, CreateLLMQuery, CreateConversationBody
from .models import Conversation as ConversationModel, Message as MessageModel, Feedback as FeedbackModel

async def create_conversation(
    current_user: UserOut,
    db: AsyncSession,
    create_conversation: CreateConversationBody,
) -> Conversation:
    """Create a conversation and store in db"""
    conversation = ConversationModel(user_id=current_user.id, title=create_conversation.title)
    
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
    """Get all conversations (of the user)"""
    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
    query = stmt.where(ConversationModel.user_id == current_user.id).order_by(ConversationModel.conversation_id.desc())
    result = await db.execute(query)
    return result.scalars().all()

async def get_conversation(
    conversation_id: int,
    current_user: UserOut,
    db: AsyncSession,
) -> Conversation:
    """Get a single conversation given a conv_id (of the user)"""
    stmt = select(ConversationModel).options(selectinload(ConversationModel.messages))
    query = stmt.where(ConversationModel.user_id == current_user.id).where(ConversationModel.conversation_id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation

async def generate_response(
    llm_query: CreateLLMQuery,
    current_user: UserOut,
    db: AsyncSession,
    request: Request,
) -> Message:
    """Validate user creating new Message that will be sent to LLM"""
    # Validate input
    LLM = request.app.state.llm
    if not LLM:
        raise HTTPException(
            status_code=500,
            detail="LLM service is not available"
        )
    RAG = request.app.state.rag
    if not RAG:
        raise HTTPException(
            status_code=500,
            detail="RAG service is not available"
        )
    if not llm_query.input or len(llm_query.input.strip()) == 0:
        raise HTTPException(
            status_code=400, 
            detail="Input cannot be empty"
        )
    if not llm_query.conversation_id:
        raise HTTPException(
            status_code=400, 
            detail="Conversation ID is required"
        )
    if len(llm_query.input) > 1000:
        raise HTTPException(
            status_code=400, 
            detail="Input exceeds maximum length of 1000 characters"
        )
    if not isinstance(llm_query.conversation_id, int):
        raise HTTPException(
            status_code=400, 
            detail="Conversation ID must be an integer"
        )
    if llm_query.conversation_id <= 0:
        raise HTTPException(
            status_code=400, 
            detail="Conversation ID must be a positive integer"
        )
    if not isinstance(llm_query.input, str):
        raise HTTPException(
            status_code=400, 
            detail="Input must be a string"
        )
    if len(llm_query.input) < 5:
        raise HTTPException(
            status_code=400, 
            detail="Input must be at least 5 characters long"
        )
    
    # Validate whether converstation exists or if current user has access to conversation
    result = await db.execute(select(ConversationModel).where(ConversationModel.conversation_id == llm_query.conversation_id))
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
        conversation_id=llm_query.conversation_id, 
        user_id=current_user.id, 
        input=llm_query.input, 
        response=f""
    )

    # Call LLM to generate response
    try:
        response = await LLM.run_conversation(
            user_prompt=llm_query.input,
            startingPrompt=None,
            chatHistory=[]
        )
        message.response = response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response from LLM: {str(e)}"
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
    #TODO: Must check if message belongs to current user
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
    """Create Feedback entry for Message (or update current Feedback)"""
    #TODO: Check that message belongs to current user
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