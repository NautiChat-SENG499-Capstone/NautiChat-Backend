from pydantic import BaseModel, Field
from typing import Annotated, List, Optional

class Feedback(BaseModel):
    rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    comment: Optional[str] = None

class Message(BaseModel):
    message_id: int
    conversation_id: int
    user_id: int
    input: str
    response: str
    feedback: Optional[Feedback] = None

class Conversation(BaseModel):
    conversation_id: int
    user_id: int
    title: Optional[str] = None
    messages: List[Message] = []