from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from typing import List, Annotated, Optional

from src.auth.dependencies import get_current_user
from src.database import get_db_session

from src.auth.schemas import UserOut
from .schemas import Conversation, Message, Feedback, CreateLLMQuery, CreateConversationBody
from . import service


router = APIRouter()


@router.post("/conversations", status_code=201, response_model=Conversation)
async def create_conversation(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    CreateConversationBody: CreateConversationBody,
) -> Conversation:
    """Create a new conversation"""
    return await service.create_conversation(current_user, db, CreateConversationBody)


@router.get("/conversations", response_model=List[Conversation])
async def get_conversations(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[Conversation]:
    """Get a list of the users conversations in descending order"""
    return await service.get_conversations(current_user, db)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: int,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Conversation:
    """Get a conversation"""
    return await service.get_conversation(conversation_id, current_user, db)


@router.post("/messages", status_code=201, response_model=Message)
async def generate_response(
    LLMQuery: CreateLLMQuery,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Message:
    """Send message to LLM which will generate a response"""
    return await service.generate_response(LLMQuery, current_user, db)


@router.get("/messages/{message_id}", response_model=Message)
async def get_message(
    message_id: int,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Message:
    """Get a message"""
    return await service.get_message(message_id, current_user, db)


@router.patch("/messages/{message_id}/feedback", response_model=Message)
async def submit_feedback(
    message_id: int,
    feedback: Feedback,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Message:
    """Update the feedback in the Message model"""
    return await service.submit_feedback(message_id, feedback, current_user, db)
