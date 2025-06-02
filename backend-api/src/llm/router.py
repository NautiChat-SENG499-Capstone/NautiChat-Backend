from fastapi import APIRouter, Depends
from src.auth.schemas import User
from src.auth.dependencies import get_current_user

from typing import List, Annotated, Optional

from .schemas import (
    Conversation,
    Message,
    Feedback
)

router = APIRouter()

@router.post("/conversations", status_code=201)
def create_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    title: Optional[str] = None,
) -> Conversation:
    """Create a new conversation"""
    return Conversation(
        conversation_id=1, user_id=current_user.user_id, title=title, messages=[]
    )


@router.get("/conversations")
def get_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Conversation]:
    """Get a list of the users conversations"""
    return [
        Conversation(
            conversation_id=1,
            user_id=current_user.user_id,
            title="Conversation 1",
            messages=[],
        ),
        Conversation(
            conversation_id=2,
            user_id=current_user.user_id,
            title="Conversation 2",
            messages=[],
        ),
    ]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Conversation:
    """Get a conversation"""
    return Conversation(
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        messages=[],
    )


@router.post("/messages", status_code=201)
def generate_response(
    input: str,
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Message:
    """Get a response from the LLM"""
    return Message(
        message_id=1,
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        input=input,
        response=f"Response for: {input}",
    )


@router.get("/messages/{message_id}")
def get_message(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Message:
    """Get a message"""
    return Message(
        message_id=message_id,
        conversation_id=1,
        user_id=current_user.user_id,
        input=f"Input for message {message_id}",
        response=f"Response for message {message_id}",
    )


@router.post("/messages/{message_id}/feedback")
def submit_feedback(
    message_id: int,
    feedback: Feedback,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Message:
    """Submit feedback for a message"""
    return Message(
        message_id=message_id,
        conversation_id=1,
        user_id=current_user.user_id,
        input=f"Input for message {message_id}",
        response=f"Response for message {message_id}",
        feedback=feedback,
    )