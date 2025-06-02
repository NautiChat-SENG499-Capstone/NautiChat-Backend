from typing import Annotated, List

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_admin_user
from src.auth.schemas import User
from src.llm.schemas import Message

router = APIRouter()


@router.get("/messages")
def get_all_messages(
    current_user: Annotated[User, Depends(get_admin_user)],
) -> List[Message]:
    """Get all messages"""
    return [
        Message(
            message_id=1,
            conversation_id=1,
            user_id=current_user.user_id,
            input="Input for message 1",
            response="Response for message 1",
        ),
        Message(
            message_id=2,
            conversation_id=2,
            user_id=current_user.user_id,
            input="Input for message 2",
            response="Response for message 2",
        ),
    ]
